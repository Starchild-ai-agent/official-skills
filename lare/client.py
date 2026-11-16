"""Per-tenant HTTP client for Lare (`/api/v1/*`) using SSO exchange + X-Tenant-Key."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_SESSION_CACHE: dict[str, Any] = {"token": "", "expires_at": 0.0}


def ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def err(status: int, message: str, hint: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "status": status, "error": message}
    if hint:
        out["hint"] = hint
    return out


def _workspace_env(key: str) -> str:
    """Read a key from workspace/.env (the agent mirrors the Lare config there)."""
    path = os.path.join(os.environ.get("WORKSPACE_DIR", "./workspace"), ".env")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                name, _, value = line.strip().partition("=")
                if name.strip() == key:
                    return value.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _cfg() -> tuple[str, str, str]:
    base = (
        os.environ.get("LARE_API_URL")
        or _workspace_env("LARE_API_URL")
        or "http://br-lare-api.internal:8000"
    ).strip().rstrip("/")
    tenant = (os.environ.get("LARE_TENANT_CODE") or _workspace_env("LARE_TENANT_CODE")).strip()
    tkey = (
        os.environ.get("LARE_TENANT_API_KEY") or _workspace_env("LARE_TENANT_API_KEY")
    ).strip()
    return base, tenant, tkey


def _raw_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> tuple[int, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"detail": raw}
        return exc.code, parsed
    except Exception as exc:
        return 502, {"detail": str(exc)}


def _ensure_staff_jwt(actor_id: str | None = None, br_role: str = "admin") -> tuple[str, str, str] | dict[str, Any]:
    base, tenant, tkey = _cfg()
    if not tenant or not tkey:
        return err(503, "LARE_TENANT_CODE and LARE_TENANT_API_KEY are required")
    now = time.time()
    ext_uid = (actor_id or os.environ.get("USER_ID") or "agent").strip()
    if _SESSION_CACHE["token"] and _SESSION_CACHE["expires_at"] > now + 30:
        return base, tenant, _SESSION_CACHE["token"]
    status, data = _raw_request(
        "POST",
        f"{base}/api/v1/platform/tenants/{urllib.parse.quote(tenant)}/sso-exchange",
        headers={"X-Tenant-Key": tkey},
        body={
            "external_user_id": ext_uid,
            "email": f"agent-{ext_uid}@starchild.local",
            "br_role": br_role,
        },
    )
    if status >= 400 or not isinstance(data, dict) or not data.get("token"):
        return err(status, f"Lare SSO exchange failed: {data}")
    _SESSION_CACHE["token"] = str(data["token"])
    _SESSION_CACHE["expires_at"] = now + max(60, int(data.get("expires_in") or 900) - 60)
    return base, tenant, _SESSION_CACHE["token"]


def call(
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    actor_id: str | None = None,
    br_role: str = "admin",
) -> dict[str, Any]:
    auth = _ensure_staff_jwt(actor_id=actor_id, br_role=br_role)
    if isinstance(auth, dict):
        return auth
    base, tenant, jwt_tok = auth
    url = f"{base}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v is not None and v != ""}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)
    status, data = _raw_request(
        method,
        url,
        headers={"Authorization": f"JWT {jwt_tok}", "tenant": tenant},
        body=body,
    )
    if status >= 400:
        msg = (data.get("error") or {}).get("message") if isinstance(data, dict) else str(data)
        return err(status, msg or str(data))
    return ok(data)
