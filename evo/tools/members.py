"""EVO member, service and plan lookups.

All responses use the envelope documented in client.py.
"""

import os
import sys

try:  # loaded by exports.py
    from _evo_client import (MEMBER_STATUS, MEMBERSHIP_CONTRACT_STATUS, _call,
                             _date_str, _digits, _full_name, _label, _norm, err,
                             ok)
except ImportError:  # standalone: python3 tools/members.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_evo_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_evo_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _evo_client import (MEMBER_STATUS, MEMBERSHIP_CONTRACT_STATUS, _call,  # noqa: E402,F811
                             _date_str, _digits, _full_name, _label, _norm, err,
                             ok)


def _normalize_member(row):
    """Trim EVO's 40-field MembersApiViewModel to what an agent needs."""
    if not isinstance(row, dict):
        return row
    status_code = row.get("status")
    contacts = [c.get("description") for c in (row.get("contacts") or []) if c.get("description")]
    memberships = [
        {
            "id_member_membership": m.get("idMemberMembership"),
            "id_membership": m.get("idMembership"),
            "plan": m.get("name"),
            "status": m.get("membershipStatus"),
            "start_date": _date_str(m.get("startDate")),
            "end_date": _date_str(m.get("endDate")),
            "cancel_date": _date_str(m.get("cancelDate")),
        }
        for m in (row.get("memberships") or [])
    ]
    return {
        "id_member": row.get("idMember"),
        "name": _full_name(row),
        "register_name": row.get("registerName"),
        "cpf": _digits(row.get("cpf") or row.get("document")),
        "document": row.get("document"),
        "email": next((c for c in contacts if "@" in str(c)), None),
        "phones": contacts,
        "birth_date": _date_str(row.get("birthDate")),
        "gender": row.get("gender"),
        "branch_id": row.get("idBranch"),
        "branch_name": row.get("branchName"),
        "status_code": status_code,
        "status": (MEMBER_STATUS.get(int(status_code)) if str(status_code).isdigit() else None),
        "membership_status": row.get("membershipStatus"),
        "access_blocked": row.get("accessBlocked"),
        "blocked_reason": row.get("blockedReason"),
        "last_access": _date_str(row.get("lastAccessDate")),
        "register_date": _date_str(row.get("registerDate")),
        "aggregator_ids": {"wellhub": row.get("gympassId"), "totalpass": row.get("codeTotalpass")},
        "memberships": memberships,
    }


def find_members(name=None, cpf=None, email=None, phone=None, id_member=None,
                 status=None, take=50, skip=0, id_branch=None,
                 show_memberships=False):
    """Search members on any single identifier (name is a substring match).

    `status` accepts 1/2 or "active"/"inactive".
    """
    if isinstance(status, str) and not status.isdigit():
        lookup = {v: k for k, v in MEMBER_STATUS.items()}
        status = lookup.get(status.strip().lower())
    result = _call("GET", "/api/v2/members", params={
        "name": name,
        "document": _digits(cpf) or None,
        "email": email,
        "phone": _digits(phone) or None,
        "idMember": id_member,
        "status": status,
        "take": take,
        "skip": skip,
        "idBranch": id_branch,
        "showMemberships": show_memberships,
    })
    if not result["ok"]:
        return result
    rows = result["data"] if isinstance(result["data"], list) else []
    return ok({"count": len(rows), "members": [_normalize_member(r) for r in rows]})


def resolve_member(query):
    """Turn one human identifier into exactly one member.

    Accepts a numeric idMember, a CPF/document, an e-mail, a phone number, or
    a name. Returns {member, candidates, matched_by}: `member` is None when the
    query matched nothing or more than one person.
    """
    if query is None or str(query).strip() == "":
        return err(None, "resolve_member needs an id, CPF, e-mail, phone or name")
    text = str(query).strip()
    digits = _digits(text)

    attempts = []
    if text.isdigit():
        attempts.append(("id", {"id_member": int(text)}))
    if len(digits) == 11:
        attempts.append(("cpf", {"cpf": digits}))
    if "@" in text:
        attempts.append(("email", {"email": text}))
    if 10 <= len(digits) <= 13:
        attempts.append(("phone", {"phone": digits}))
    attempts.append(("name", {"name": text}))

    candidates, matched_by, seen = [], None, set()
    for label, kwargs in attempts:
        found = find_members(**kwargs)
        if not found["ok"]:
            return found
        rows = found["data"]["members"]
        if not rows:
            continue
        matched_by, candidates = label, rows
        if label != "name" or len(rows) == 1:
            break
        # a name search may return many people; keep looking for a unique hit
        if len(rows) > 1:
            break
        for row in rows:
            seen.add(row.get("id_member"))

    member = candidates[0] if len(candidates) == 1 else None
    if member is None and matched_by == "name" and len(candidates) > 1:
        exact = [c for c in candidates if _norm(c.get("name")) == _norm(text)]
        if len(exact) == 1:
            member = exact[0]
    return ok({
        "member": member,
        "matched_by": matched_by,
        "candidates": candidates[:15],
        "count": len(candidates),
    })


def member(id_member, memberships=True, responsibles=False, access_qr_code=False):
    """Full member profile (GET /api/v2/members/{idMember})."""
    result = _call("GET", f"/api/v2/members/{id_member}", params={
        "showMemberships": memberships,
        "showsResponsibles": responsibles,
        "showAccessControlQRcode": access_qr_code,
    })
    if not result["ok"]:
        return result
    return ok(_normalize_member(result["data"]))


def member_services(id_member):
    """Services the member's contracts entitle them to."""
    result = _call("GET", "/api/v1/members/services", params={"idMember": id_member})
    if not result["ok"]:
        return result
    rows = result["data"] if isinstance(result["data"], list) else []
    return ok({
        "count": len(rows),
        "services": [{"id_service": r.get("idService"), "name": r.get("nameService")} for r in rows],
    })


def membership_plans(name=None, active=None, id_branch=None, take=25, skip=0):
    """Catalogue of plans (contracts) sold by the gym (GET /api/v3/membership)."""
    result = _call("GET", "/api/v3/membership", params={
        "name": name, "active": active, "idBranch": id_branch, "take": take, "skip": skip,
    })
    if not result["ok"]:
        return result
    rows = result["data"] if isinstance(result["data"], list) else []
    plans = [{
        "id_membership": r.get("idMembership"),
        "name": r.get("nameMembership") or r.get("displayName"),
        "type": r.get("membershipType"),
        "duration_type": r.get("durationType"),
        "duration": r.get("duration"),
        "value": r.get("value"),
        "inactive": r.get("inactive"),
        "branch_id": r.get("idBranch"),
        "entitlements": r.get("entries"),
    } for r in rows]
    return ok({"count": len(plans), "plans": plans})


def member_memberships(id_member=None, name=None, status=None, take=25, skip=0):
    """A member's contracts, active or cancelled (GET /api/v3/membermembership).

    `status` accepts 1..5 (active, canceled, expired, suspended, in_queue) or
    the matching label.
    """
    if isinstance(status, str) and not status.isdigit():
        lookup = {v: k for k, v in MEMBERSHIP_CONTRACT_STATUS.items()}
        status = lookup.get(status.strip().lower())
    result = _call("GET", "/api/v3/membermembership", params={
        "idMember": id_member, "memberName": name,
        "statusMemberMembership": status, "take": take, "skip": skip,
    })
    if not result["ok"]:
        return result
    rows = result["data"] if isinstance(result["data"], list) else []
    contracts = [{
        "id_member_membership": r.get("idMemberMemberShip"),
        "id_member": r.get("idMember"),
        "plan": r.get("nameMembership"),
        "branch_id": r.get("idBranch"),
        "start": _date_str(r.get("membershipStart")),
        "end": _date_str(r.get("membershipEnd")),
        "cancel_date": _date_str(r.get("cancelDate")),
        "status_code": r.get("statusMemberMembership"),
        "status": _label(MEMBERSHIP_CONTRACT_STATUS, r.get("statusMemberMembership")),
        "cancel_reason": r.get("reasonCancellation"),
        "sale_value": r.get("saleValue"),
        "remaining_value": r.get("remainingValue"),
    } for r in rows]
    return ok({"count": len(contracts), "contracts": contracts})