"""Angulare members (users) — search, resolve, profile.

Verified working filters on GET /api/v1/users/users/:
    search   (name / e-mail substring)   -> verified
    cpf      (digits)                    -> verified
    is_staff (true|false)                -> verified
    active   (true|false)                -> verified
NOT supported (silently ignored — the count does not change):
    email, document, name, id, status, unit, first_name, ordering
"""

import os
import sys

try:  # loaded by exports.py
    from _angulare_client import _digits, _full_name, call, date_str, err, ok, page
except ImportError:  # standalone: python3 tools/members.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_angulare_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_angulare_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _angulare_client import _digits, _full_name, call, date_str, err, ok, page  # noqa: E402,F811


def _normalize(row):
    if not isinstance(row, dict):
        return row
    phones = []
    for contact in (row.get("contacts") or []):
        value = contact.get("description") if isinstance(contact, dict) else contact
        if value:
            phones.append(value)
    return {
        "id": row.get("id"),
        "name": _full_name(row),
        "email": row.get("email"),
        "cpf": _digits(row.get("cpf")),
        "phones": phones,
        "mobile_phone": row.get("mobile_phone"),
        "birth_date": date_str(row.get("date_of_birth") or row.get("birth_date")),
        "gender": row.get("gender"),
        "active": row.get("is_active"),
        "is_staff": row.get("is_staff"),
        "unit": row.get("unit"),
        "unit_info": row.get("unit_info"),
        "register_date": date_str(row.get("created_at") or row.get("register_date")),
        "last_login": date_str(row.get("last_login")),
        "aggregator_ids": {
            "wellhub": row.get("gympass_id") or row.get("gympassId"),
            "totalpass": row.get("code_totalpass") or row.get("codeTotalpass"),
        },
        "permission_groups": row.get("permission_groups"),
    }


def find_members(search=None, cpf=None, is_staff=None, active=None,
                 take=50, skip=0):
    """Search members. `search` matches name or e-mail (substring).

    ⚠️ Unsupported filters are ignored silently — always check that the
    returned `count` actually narrowed before trusting a filter.
    """
    result = call("GET", "/api/v1/users/users/", params={
        "search": search,
        "cpf": _digits(cpf) or None,
        "is_staff": is_staff,
        "active": active,
        "page_size": take,
        "page": (int(skip) // int(take) + 1) if take else 1,
    })
    if not result["ok"]:
        return result
    p = page(result)
    return ok({"count": p["count"], "members": [_normalize(r) for r in p["results"]]})


def member(user_id):
    """One member by id."""
    result = call("GET", f"/api/v1/users/users/{user_id}/")
    if not result["ok"]:
        return result
    return ok(_normalize(result["data"]))


def resolve_member(query):
    """Turn one human identifier into exactly one member.

    Accepts an id, a CPF, an e-mail or a name. Returns
    {member, candidates, matched_by, count}; `member` is None when the query
    matched nothing or more than one person.
    """
    if query is None or str(query).strip() == "":
        return err(None, "resolve_member needs an id, CPF, e-mail or name")

    text = str(query).strip()
    digits = _digits(text)

    # A numeric id goes to the detail endpoint — the list endpoint has no `id`
    # filter and `search=<number>` happily matches unrelated fields (phones,
    # zip codes), which is how you end up with a pile of false candidates.
    if text.isdigit():
        direct = member(int(text))
        if direct["ok"] and isinstance(direct["data"], dict) and direct["data"].get("id"):
            return ok({"member": direct["data"], "matched_by": "id",
                       "candidates": [direct["data"]], "count": 1})

    attempts = []
    if len(digits) == 11:
        attempts.append(("cpf", {"cpf": digits}))
    if "@" in text:
        attempts.append(("email", {"search": text}))
    attempts.append(("name", {"search": text}))

    candidates, matched_by = [], None
    for label, kwargs in attempts:
        found = find_members(**kwargs)
        if not found["ok"]:
            return found
        rows = found["data"]["members"]
        if rows:
            candidates, matched_by = rows, label
            if len(rows) == 1:
                break
    member_row = candidates[0] if len(candidates) == 1 else None
    return ok({"member": member_row, "matched_by": matched_by,
               "candidates": candidates[:15], "count": len(candidates)})


def quick_register_member(email, first_name, last_name, confirm=False):
    """[WARN] WRITE — create a member with the minimum set of fields.

    `POST /api/v1/users/users/quick-registration/` takes exactly three fields —
    verified by letting the API report its own validation errors: no CPF, no
    phone and no unit are required, and the response is `201` with the new id.

    Requires the `users:user-quick-registration` permission (the director
    account we tested holds it, along with `users:user-manage`).

    This is the cheap way to get a throwaway member for end-to-end tests, so
    you never have to place test orders against a real customer.
    """
    if not confirm:
        return err(None, "quick_register_member is a write and requires "
                         "confirm=True (it creates a real member record)")
    if not email:
        return err(None, "quick_register_member needs an email")
    result = call("POST", "/api/v1/users/users/quick-registration/",
                  body={"email": email, "first_name": first_name,
                        "last_name": last_name})
    if not result["ok"]:
        return result
    data = result["data"]
    return ok({"member": _normalize(data) if isinstance(data, dict) else data,
               "raw": data})


def tenant_settings():
    """Tenant configuration: site, checkouts, events, payments, users, domains."""
    result = call("GET", "/api/v1/core/settings/")
    if not result["ok"]:
        return result
    data = result["data"] or {}
    site = data.get("site") or {}
    checkouts = data.get("checkouts") or {}
    return ok({
        "site_name": site.get("name"),
        "tenant": (site.get("tenant") or {}).get("code"),
        "domains": [d.get("domain") for d in (data.get("domains") or [])],
        "is_production": site.get("is_production"),
        "enabled_payment_methods": checkouts.get("enabled_payment_methods"),
        "allow_cart_sharing": checkouts.get("allow_cart_sharing"),
        "user_required_fields": (data.get("users") or {}).get("user_required_fields"),
        "cpf_strategy": (data.get("users") or {}).get("cpf_strategy"),
        "raw": data,
    })


def discover_tenants(email=None):
    """Public lookup: which tenants does this e-mail have access to?

    No credentials needed — this is the only unauthenticated endpoint we use,
    and the only reliable way to learn the tenant code required by every call.
    """
    import os as _os

    target = email or _os.environ.get("ANGULARE_EMAIL")
    if not target:
        return err(None, "discover_tenants needs an e-mail")
    from _angulare_client import call_public  # local import keeps the top tidy
    result = call_public("/api/v1/users/users/check-tenant/",
                         params={"email": target, "is_staff": "true"})
    if not result["ok"]:
        return result
    data = result["data"] or {}
    return ok({"tenants_allowed": data.get("tenants_allowed") or [],
               "tenants_blocked": data.get("tenants_blocked") or []})
