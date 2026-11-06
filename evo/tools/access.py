"""EVO check-ins: gym entries, aggregator (Wellhub/TotalPass) check-in report,
turnstiles, manual entry authorisation, and API-Pro usage/cost.

Note: Wellhub and TotalPass traffic flows into EVO through their own
per-branch integration cards, not through this API. What this API gives you is
the *report* surface (aggregator check-ins) plus the raw entry log.
"""

import os
import sys

try:  # loaded by exports.py
    from _evo_client import _call, _date_str, err, ok
except ImportError:  # standalone: python3 tools/access.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_evo_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_evo_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _evo_client import _call, _date_str, err, ok  # noqa: E402,F811


def entries(start=None, end=None, id_member=None, id_prospect=None, id_employee=None,
            entry_id=None, take=100, skip=0):
    """Raw attendance/entry log for a period (GET /api/v1/entries)."""
    result = _call("GET", "/api/v1/entries", params={
        "registerDateStart": _date_str(start),
        "registerDateEnd": _date_str(end),
        "idMember": id_member,
        "idProspect": id_prospect,
        "idEmployee": id_employee,
        "IdEntry": entry_id,
        "take": take,
        "skip": skip,
    })
    if not result["ok"]:
        return result
    rows = result["data"] if isinstance(result["data"], list) else []
    return ok({"count": len(rows), "entries": [{
        "date": _date_str(r.get("date")),
        "time": r.get("dateTurn"),
        "id_member": r.get("idMember"),
        "member": r.get("nameMember"),
        "id_prospect": r.get("idProspect"),
        "id_employee": r.get("idEmployee"),
        "type": r.get("entryType"),
        "action": r.get("entryAction"),
        "device": r.get("device"),
        "turnstile_id": r.get("idTurnstile"),
        "branch_id": r.get("idBranch"),
        "blocked_reason": r.get("blockReason"),
    } for r in rows]})


def aggregator_checkins(start, end, id_branch=None, aggregators=None,
                        checkin_branch_ids=None, take=100, skip=0):
    """Wellhub / TotalPass check-in report (GET /api/v1/management/aggregators/checkins/search).

    `aggregators` and `checkin_branch_ids` are lists of ids. Rows carry the
    aggregator name, product, member and both origin and check-in branch.
    """
    result = _call("GET", "/api/v1/management/aggregators/checkins/search", params={
        "DtStart": _date_str(start),
        "DtEnd": _date_str(end),
        "IdBranch": id_branch,
        "Aggregators": aggregators,
        "CheckinBranchIds": checkin_branch_ids,
        "Take": take,
        "Skip": skip,
    })
    if not result["ok"]:
        return result
    payload = result["data"] or {}
    rows = payload.get("list") or []
    return ok({
        "total": payload.get("total"),
        "count": len(rows),
        "checkins": [{
            "id_member": r.get("idMember"),
            "id_prospect": r.get("idProspect"),
            "name": r.get("name"),
            "aggregator": r.get("aggregator"),
            "product": r.get("product"),
            "status": r.get("status"),
            "checkin_date": _date_str(r.get("checkinDate")),
            "checkin_time": r.get("checkinTime"),
            "checkin_branch_id": r.get("checkinBranchId"),
            "origin_branch_id": r.get("originBranchId"),
            "token_used": r.get("tokenUsed"),
        } for r in rows],
    })


def turnstiles(id_branch=None, serial_number=None):
    """Physical turnstiles/door controllers registered in EVO."""
    result = _call("GET", "/api/v2/accessControl/turnstiles", params={
        "idBranch": id_branch, "serialNumber": serial_number,
    })
    if not result["ok"]:
        return result
    rows = result["data"] if isinstance(result["data"], list) else []
    return ok({"count": len(rows), "turnstiles": [{
        "id_turnstile": r.get("idTurnstile"),
        "name": r.get("name"),
        "serial_number": r.get("serialNumber"),
        "branch_id": r.get("idBranch"),
    } for r in rows]})


def authorize_entry(id_turnstile, person_type=None, record_id=None, device=None,
                    climate_id=None, temperature=None, id_manual_entry=None):
    """Authorize one entry at a turnstile (POST /api/v2/accessControl/entryAuthorize).

    `person_type` / `device` / `climate_id` are EVO-side enums whose labels are
    not published; pass what EVO's integration team gave you. `record_id` maps
    to the body's `id` (member, prospect or employee, per `person_type`).
    """
    body = {
        "id": record_id,
        "personType": person_type,
        "device": device,
        "idManualEntry": id_manual_entry,
        "temperature": temperature,
        "climateId": climate_id,
        "idTurnstile": id_turnstile,
    }
    result = _call("POST", "/api/v2/accessControl/entryAuthorize", body=body)
    if not result["ok"]:
        return result
    return ok(result["data"])


def api_usage():
    """This token's API Pro usage and cost for the current month.

    Also the only way to see consumption on API Plus (which has no usage
    endpoint of its own — Plus resets monthly at 1,000 calls / 100 per day).
    """
    result = _call("GET", "/api/v1/configuration/api-usage")
    if not result["ok"]:
        return result
    payload = result["data"] or {}
    usage = payload.get("usage") or {}
    return ok({
        "period": payload.get("period"),
        "currency": payload.get("currency"),
        "cost_limit": payload.get("costLimit"),
        "usage": {
            bucket: {
                "hits": (usage.get(bucket) or {}).get("hits"),
                "cost": (usage.get(bucket) or {}).get("cost"),
            }
            for bucket in ("daytime", "nighttime", "total")
        },
        "raw": payload,
    })