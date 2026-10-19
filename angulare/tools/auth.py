"""Angulare credential check — prove the three-part handshake works.

Run this first: it logs in, reads the tenant settings and the authenticated
user, and reports what the account is allowed to do.
"""

import os
import sys

try:  # loaded by exports.py
    from _angulare_client import call, credentials, err, jwt_claims, login, ok
except ImportError:  # standalone
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_angulare_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_angulare_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _angulare_client import call, credentials, err, jwt_claims, login, ok  # noqa: E402,F811


def check_credentials():
    """Verify ANGULARE_EMAIL / ANGULARE_PASSWORD / ANGULARE_TENANT end to end.

    Returns the tenant, the authenticated user and their permission list — the
    cheapest way to tell "wrong password" apart from "wrong tenant".
    """
    try:
        email, _, tenant = credentials()
    except Exception as exc:
        return err(None, str(exc))

    auth = login()
    if not auth["ok"]:
        return auth

    claims = auth["data"].get("claims") or {}
    settings = call("GET", "/api/v1/core/settings/")
    me = call("GET", "/api/v1/users/users/", params={"search": email, "page_size": 5})

    user = None
    if me["ok"] and isinstance(me["data"], dict):
        for row in (me["data"].get("results") or []):
            if str(row.get("email", "")).lower() == email.lower():
                user = {"id": row.get("id"),
                        "name": " ".join(x for x in (row.get("first_name"), row.get("last_name")) if x),
                        "is_staff": row.get("is_staff"),
                        "permission_groups": row.get("permission_groups"),
                        "unit": row.get("unit_info")}
                break

    site = {}
    if settings["ok"] and isinstance(settings["data"], dict):
        s = settings["data"].get("site") or {}
        site = {"name": s.get("name"), "tenant": (s.get("tenant") or {}).get("code"),
                "is_production": s.get("is_production")}

    return ok({
        "credentials": "ok",
        "tenant_configured": tenant,
        "tenant_from_settings": site.get("tenant"),
        "site": site,
        "user": user,
        "jwt_tenant": claims.get("tenant"),
        "jwt_is_staff": claims.get("is_staff"),
        "jwt_permissions": claims.get("permissions"),
        "jwt_expires_at": claims.get("exp"),
        "warning": ("tenant mismatch between the header and the site settings — "
                    "the account may belong to another environment"
                    if site.get("tenant") and site["tenant"] != tenant else None),
    })
