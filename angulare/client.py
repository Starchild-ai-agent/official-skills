"""
Angulare (Angular e-Commerce) REST client — auth, HTTP, dates, error mapping.

Angulare has NO public developer documentation. Everything here was
reverse-engineered from the manager dashboard SPA (`reservas.angulare.app`,
`dash.angulare.app`) and then verified against production. See
`references/api-reference.md` for the evidence trail.

AUTH — three steps:

    1. find the tenant (public, no auth)
       GET /api/v1/users/users/check-tenant/?email=<email>&is_staff=true
       -> {"tenants_allowed": [{"tenant_code": "numa", ...}], "tenants_blocked": []}

    2. exchange credentials for a JWT
       POST /api/v1/jwt/token-auth/
       headers: tenant: <tenant_code>, Content-Type: application/json
       body:    {"email": ..., "password": ...}
       -> {"token": "<JWT>", "refresh": "<JWT>"}      (TTL ~10 days)

    3. call the API with BOTH headers on every request
       Authorization: JWT <token>      <-- "JWT", NOT "Bearer"
       tenant: <tenant_code>

Env (collect with request_env_input, never ask for these in chat):
    ANGULARE_EMAIL       the manager's login e-mail
    ANGULARE_PASSWORD    the manager's password
    ANGULARE_TENANT      tenant code, e.g. "numa"
    ANGULARE_BASE_URL    optional; default is the production API host

Every public function returns the same envelope:
    {"ok": True,  "status": 200, "data": <payload>}
    {"ok": False, "status": 401, "error": "...", "hint": "..."}
"""

import base64
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

BASE = (os.environ.get("ANGULARE_BASE_URL") or "https://prd.angulare.app").rstrip("/")
TIMEOUT = 60

# Regional / alternate deployments. A tenant lives in exactly one of them;
# check-tenant is the only reliable way to find out which.
KNOWN_HOSTS = [
    "https://prd.angulare.app",
    "https://prd.europa.angulare.app",
    "https://europa.angularesmart.com",
    "https://brasil.angularesmart.com",
]

# Order statuses seen in production (GET /api/v1/sales/orders/)
ORDER_STATUS = {
    "paid": "paid",
    "waiting_payment": "awaiting payment (link sent, not settled)",
    "not_authorized": "payment refused by the card issuer",
    "canceled": "canceled",
}

# Booking / attendance statuses (GET /api/v1/events/reports/event-books/?status=)
ATTENDANCE_STATUS = [
    "checked-in", "booked", "waiting-list", "canceled", "no-show", "late-canceled",
]


class AngulareConfigError(RuntimeError):
    """Raised when credentials are not configured."""


# ── Envelope ─────────────────────────────────────────────────────────────────

def ok(data, status: int = 200) -> Dict[str, Any]:
    return {"ok": True, "status": status, "data": data}


def err(status: Optional[int], message: str, hint: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "status": status, "error": message}
    if hint:
        out["hint"] = hint
    return out


# ── Credentials ──────────────────────────────────────────────────────────────

def credentials() -> tuple:
    """Return (email, password, tenant) or raise AngulareConfigError."""
    email = (os.environ.get("ANGULARE_EMAIL") or "").strip()
    password = os.environ.get("ANGULARE_PASSWORD") or ""
    tenant = (os.environ.get("ANGULARE_TENANT") or "").strip()
    missing = [n for n, v in (("ANGULARE_EMAIL", email),
                              ("ANGULARE_PASSWORD", password),
                              ("ANGULARE_TENANT", tenant)) if not v]
    if missing:
        raise AngulareConfigError(
            "missing Angulare credential(s): " + ", ".join(missing)
            + ". The manager account must be created in the Angulare dashboard; "
              "the tenant code is what /api/v1/users/users/check-tenant/ returns "
              "for that e-mail. Collect them with request_env_input."
        )
    return email, password, tenant


# ── Transport ────────────────────────────────────────────────────────────────

def _proxied():
    try:
        from sidecar.proxy_client import proxied_get, proxied_post  # type: ignore
        return proxied_get, proxied_post
    except ImportError:
        pass
    try:
        from core.http_client import proxied_get, proxied_post  # type: ignore
        return proxied_get, proxied_post
    except ImportError:
        return None, None


def _direct(method: str, url: str, params=None, body=None, headers=None, timeout=TIMEOUT):
    try:
        import requests
    except ImportError:
        import urllib.parse
        import urllib.request

        full = url
        if params:
            full += ("&" if "?" in full else "?") + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(full, data=data, method=method, headers=headers or {})
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return _RawResponse(resp.status, resp.read().decode())

    return requests.request(method, url, params=params or None, json=body,
                            headers=headers or {}, timeout=timeout)


class _RawResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text) if self.text else None


def _clean_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = {}
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif isinstance(value, (list, tuple, set)):
            items = [str(v) for v in value if v is not None]
            if items:
                out[key] = ",".join(items)
        else:
            out[key] = value
    return out


def _request(method: str, path: str, params=None, body=None,
             headers: Optional[Dict[str, str]] = None, timeout: int = TIMEOUT):
    """Raw request against BASE. Returns (status, payload, raw_text)."""
    url = path if path.startswith("http") else BASE + path
    query = _clean_params(params)
    hdrs = {"Accept": "application/json", **(headers or {})}
    proxied_get, proxied_post = _proxied()

    try:
        if proxied_get is None:
            resp = _direct(method, url, query, body, hdrs, timeout)
        elif method == "GET":
            resp = proxied_get(url, params=query, headers=hdrs, timeout=timeout)
        elif method == "POST":
            resp = proxied_post(url, params=query, json=body or {}, headers=hdrs, timeout=timeout)
        else:
            resp = _direct(method, url, query, body, hdrs, timeout)
    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"

    status = getattr(resp, "status_code", None)
    try:
        payload = resp.json()
    except Exception:
        payload = None
    text = (getattr(resp, "text", "") or "")
    return status, payload, text


# ── Auth ─────────────────────────────────────────────────────────────────────

_token_cache: Dict[str, Any] = {"token": None, "exp": 0.0, "tenant": None}


def _jwt_exp(token: str) -> float:
    """Read `exp` out of a JWT without verifying it (we only need the clock)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return float(claims.get("exp") or 0)
    except Exception:
        return 0.0


def jwt_claims(token: str) -> Dict[str, Any]:
    """Decode a JWT payload (unverified) — handy for debugging permissions."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


def login(force: bool = False) -> Dict[str, Any]:
    """Authenticate and cache the JWT. Returns the envelope."""
    try:
        email, password, tenant = credentials()
    except AngulareConfigError as exc:
        return err(None, str(exc))

    now = time.time()
    if not force and _token_cache["token"] and _token_cache["tenant"] == tenant \
            and _token_cache["exp"] - 120 > now:
        return ok({"token": _token_cache["token"], "cached": True})

    status, payload, text = _request(
        "POST", "/api/v1/jwt/token-auth/",
        body={"email": email, "password": password},
        headers={"tenant": tenant, "Content-Type": "application/json"},
    )
    if status != 200 or not isinstance(payload, dict) or not payload.get("token"):
        message = _error_message(payload) if payload is not None else (text or "")[:200]
        return err(status, message, _hint(status, payload, text))

    _token_cache.update(token=payload["token"], exp=_jwt_exp(payload["token"]),
                        tenant=tenant)
    return ok({"token": payload["token"], "refresh": payload.get("refresh"),
               "claims": jwt_claims(payload["token"]), "cached": False})


def _auth_headers() -> Dict[str, str]:
    _, _, tenant = credentials()
    return {"Authorization": "JWT " + (_token_cache["token"] or ""), "tenant": tenant}


def _error_message(payload: Any) -> str:
    if isinstance(payload, dict):
        if payload.get("error"):
            e = payload["error"]
            if isinstance(e, dict):
                return f"{e.get('code')}: {e.get('message')}"
            return str(e)
        if payload.get("detail"):
            return str(payload["detail"])
        if payload.get("mensagens"):
            m = payload["mensagens"]
            return "; ".join(m) if isinstance(m, list) else str(m)
        if payload.get("non_field_errors"):
            return "; ".join(payload["non_field_errors"])
    if isinstance(payload, list):
        return "; ".join(str(x) for x in payload[:3])
    return json.dumps(payload, ensure_ascii=False)[:300] if payload is not None else ""


def _hint(status: Optional[int], payload: Any, text: str = "") -> Optional[str]:
    msg = (_error_message(payload) or text or "").lower()
    if status == 401:
        if "login expirado" in msg or "expirado" in msg:
            return ("The token was rejected. Angulare requires the scheme literal 'JWT' "
                    "(not 'Bearer') — 'Bearer' produces exactly this misleading error. "
                    "If the scheme is right, the token really expired; log in again.")
        if "email não encontrado" in msg or "email nao encontrado" in msg:
            return ("The 'tenant' header is missing or unknown. Angulare resolves the "
                    "account from the tenant header, not from the token alone.")
        if "não foram fornecidas" in msg or "nao foram fornecidas" in msg:
            return "No credentials were sent at all — Authorization header missing."
    if status == 403 and "open_api_key_scope" in msg:
        return ("That is an Open API Key, which is only valid under /api/open/v1/… "
                "This skill uses the panel API (/api/v1/…), which needs a JWT.")
    if status == 400 and "tenant_required" in msg:
        return "Add the tenant header."
    if status == 400 and "tenant_invalid" in msg:
        return "That tenant code does not exist on this host — check check-tenant()."
    if status == 500 and "server error" in msg:
        return ("Angulare returns 500 for a malformed Authorization value (their bug). "
                "Check the token string is well-formed.")
    return None


def call(method: str, path: str, params=None, body=None, timeout: int = TIMEOUT,
         retry_auth: bool = True) -> Dict[str, Any]:
    """Authenticated call returning the uniform envelope, with one auto re-login."""
    try:
        credentials()
    except AngulareConfigError as exc:
        return err(None, str(exc))

    if not _token_cache["token"] or _token_cache["exp"] - 120 < time.time():
        fresh = login()
        if not fresh["ok"]:
            return fresh

    status, payload, text = _request(method, path, params=params, body=body,
                                     headers=_auth_headers(), timeout=timeout)

    if status == 401 and retry_auth:
        message = (_error_message(payload) or text).lower()
        if "expirado" in message:
            again = login(force=True)
            if again["ok"]:
                status, payload, text = _request(method, path, params=params, body=body,
                                                 headers=_auth_headers(), timeout=timeout)

    if status is not None and 200 <= status < 300:
        return ok(payload, status)
    return err(status, _error_message(payload) or (text or "")[:200],
               _hint(status, payload, text))


def call_public(path: str, params=None, timeout: int = TIMEOUT) -> Dict[str, Any]:
    """Unauthenticated call (only /api/v1/users/users/check-tenant/ needs this)."""
    status, payload, text = _request("GET", path, params=params, timeout=timeout)
    if status is not None and 200 <= status < 300:
        return ok(payload, status)
    return err(status, _error_message(payload) or (text or "")[:200], _hint(status, payload, text))


# ── Result helpers ───────────────────────────────────────────────────────────

def page(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a DRF page/list payload into {count, results}."""
    data = result.get("data")
    if isinstance(data, dict) and "results" in data:
        return {"count": data.get("count"), "results": data.get("results") or [],
                "next": data.get("next")}
    if isinstance(data, list):
        return {"count": len(data), "results": data, "next": None}
    return {"count": None, "results": [], "next": None}


# ── Dates ────────────────────────────────────────────────────────────────────

def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip().replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            if fmt is None:
                dt = datetime.fromisoformat(text)
            else:
                dt = datetime.strptime(text, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def date_str(value: Any) -> Optional[str]:
    """Normalise anything reasonable to yyyy-MM-dd."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    if not text:
        return None
    low = text.lower()
    today = datetime.now(timezone.utc).date()
    if low in ("today", "hoje", "agora"):
        return today.isoformat()
    if low in ("tomorrow", "amanha", "amanhã"):
        return (today + timedelta(days=1)).isoformat()
    if low in ("yesterday", "ontem"):
        return (today - timedelta(days=1)).isoformat()
    delta = re.fullmatch(r"([+-])\s*(\d+)", text)
    if delta:
        days = int(delta.group(2)) * (1 if delta.group(1) == "+" else -1)
        return (today + timedelta(days=days)).isoformat()
    iso = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        return iso.group(0)
    br = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if br:
        return f"{br.group(3)}-{int(br.group(2)):02d}-{int(br.group(1)):02d}"
    return text


def class_end(row: Dict[str, Any]) -> Optional[datetime]:
    """When did the class in this attendance row end?

    `event_time` is the start; the row's own `end_time` is usually null, so the
    duration is taken from `event_info.duration_time` (minutes).
    """
    start = _parse_dt(row.get("event_time") or row.get("date"))
    if not start:
        return None
    info = row.get("event_info") if isinstance(row.get("event_info"), dict) else {}
    minutes = info.get("duration_time") or row.get("duration_time")
    try:
        if minutes:
            return start + timedelta(minutes=int(minutes))
    except (TypeError, ValueError):
        pass
    return _parse_dt(row.get("end_time")) or start


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _full_name(row: Dict[str, Any]) -> str:
    first = row.get("first_name") or row.get("register_name") or ""
    last = row.get("last_name") or ""
    return re.sub(r"\s+", " ", f"{first} {last}").strip()
