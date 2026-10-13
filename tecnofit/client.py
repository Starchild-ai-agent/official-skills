"""
Tecnofit REST client — auth, HTTP and error mapping.

Tecnofit's public API is deliberately small: **two endpoints**, documented as an
OpenAPI 3.0.0 spec on ReadMe.io. It is an access-control / entitlement API, not
a gym-operations API — there is no class schedule, no booking, no check-in write.

    POST /2024-09-01/auth                    {user, pass} -> {token}   (TTL 1 hour)
    GET  /2024-09-01/ticket-gate/{token}/{id} -> CustomerSummary

Auth is a per-tenant credential exchange, not OAuth: you trade the tenant's
`user`/`pass` for a bearer-style token and send it in the `Authorization`
header. The token expires after one hour, so this client caches it and re-mints
on demand.

Env (collect with request_env_input, never ask for these in chat):
    TECNOFIT_USER    tenant user
    TECNOFIT_PASS    tenant password
    TECNOFIT_BASE_URL  optional; defaults to the production host

Every public function returns the same envelope:
    {"ok": True,  "status": 200, "data": <payload>}
    {"ok": False, "status": 401, "error": "...", "hint": "..."}

Docs: https://tecnofit.readme.io
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

BASE = (os.environ.get("TECNOFIT_BASE_URL") or "https://rest.tecnofit.com.br").rstrip("/")
TIMEOUT = 45
TOKEN_TTL_SECONDS = 3600  # the docs state 1 hour

# Enums taken verbatim from the published spec.
STUDENT_STATUS = {
    1: "active", 2: "blocked", 3: "canceled", 4: "restricted",
    5: "on_leave", 6: "no_contract",
}
CONTRACT_STATUS = {
    1: "active", 2: "blocked", 3: "canceled", 5: "on_leave",
    6: "pending_payment", 7: "finished", 8: "awaiting_start",
}
# Statuses that mean "let them in" for an entitlement check.
CONTRACT_ENTITLED = {1}


class TecnofitConfigError(RuntimeError):
    """Raised when TECNOFIT_USER / TECNOFIT_PASS are not configured."""


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
    user = (os.environ.get("TECNOFIT_USER") or "").strip()
    password = os.environ.get("TECNOFIT_PASS") or ""
    missing = [n for n, v in (("TECNOFIT_USER", user), ("TECNOFIT_PASS", password)) if not v]
    if missing:
        raise TecnofitConfigError(
            "missing Tecnofit credential(s): " + ", ".join(missing)
            + ". These are the tenant's login, issued through Tecnofit's partner "
              "programme — collect them with request_env_input."
        )
    return user, password


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


def _direct(method: str, url: str, body=None, headers=None, timeout: int = TIMEOUT):
    """Off-platform transport.

    Tries `requests` first (it honours the environment's proxy settings, which
    is what we want inside the platform container), then falls back to the
    stdlib. Some corporate/desktop proxy setups accept one client and not the
    other, so a fallback is cheaper than an environment-specific guess.
    """
    notes = []
    try:
        import requests
        try:
            return requests.request(method, url, json=body, headers=headers or {},
                                    timeout=timeout)
        except Exception as exc:
            notes.append(f"requests: {type(exc).__name__}")
    except ImportError:
        notes.append("requests: not installed")

    import urllib.error
    import urllib.request

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return _RawResponse(resp.status, resp.read().decode())
    except urllib.error.HTTPError as exc:  # urllib raises on 4xx/5xx
        return _RawResponse(exc.code, exc.read().decode("utf-8", "replace"))
    except Exception as exc:
        raise RuntimeError(
            f"direct request failed ({'; '.join(notes)}; urllib: {type(exc).__name__})"
        ) from exc


class _RawResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text) if self.text else None


def _request(method: str, path: str, body=None, headers=None, timeout: int = TIMEOUT):
    url = path if path.startswith("http") else BASE + path
    hdrs = {"Accept": "application/json", **(headers or {})}
    proxied_get, proxied_post = _proxied()
    try:
        if proxied_get is None:
            resp = _direct(method, url, body, hdrs, timeout)
        elif method == "GET":
            resp = proxied_get(url, headers=hdrs, timeout=timeout)
        elif method == "POST":
            resp = proxied_post(url, json=body or {}, headers=hdrs, timeout=timeout)
        else:
            resp = _direct(method, url, body, hdrs, timeout)
    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"

    status = getattr(resp, "status_code", None)
    try:
        payload = resp.json()
    except Exception:
        payload = None
    return status, payload, (getattr(resp, "text", "") or "")


def _error_message(payload: Any, text: str = "") -> str:
    if isinstance(payload, dict):
        if payload.get("reason_phrase"):
            return str(payload["reason_phrase"])
        for key in ("detail", "error", "message", "non_field_errors"):
            if payload.get(key):
                value = payload[key]
                return "; ".join(value) if isinstance(value, list) else str(value)
    if text.strip():
        return text.strip()[:200]
    return "empty response body"


def _hint(status: Optional[int], payload: Any, path: str) -> Optional[str]:
    if status == 401:
        return ("Tecnofit rejected the credentials. The tenant user/password are issued "
                "through the partner programme — there is no self-service signup and no "
                "sandbox. A token also expires after 1 hour; this client re-mints it, so a "
                "persistent 401 means the credentials themselves are wrong.")
    if status == 404 and "ticket-gate" in path:
        return ("Tecnofit returns 404 (not 401) when the path token/id do not resolve. The "
                "{token} segment is a gate/aggregator token, not the auth token — verify "
                "both path values before blaming the credentials.")
    if status == 405:
        return "Wrong HTTP verb for this path (auth is POST-only)."
    return None


# ── Auth ─────────────────────────────────────────────────────────────────────

_token_cache: Dict[str, Any] = {"token": None, "expires_at": 0.0, "user": None}


def auth(force: bool = False) -> Dict[str, Any]:
    """Mint (and cache) an access token. TTL is 1 hour per the vendor's docs."""
    try:
        user, password = credentials()
    except TecnofitConfigError as exc:
        return err(None, str(exc))

    now = time.time()
    if not force and _token_cache["token"] and _token_cache["user"] == user \
            and _token_cache["expires_at"] - 60 > now:
        return ok({"token": _token_cache["token"], "cached": True,
                   "expires_in": int(_token_cache["expires_at"] - now)})

    status, payload, text = _request("POST", "/2024-09-01/auth",
                                     body={"user": user, "pass": password},
                                     headers={"Content-Type": "application/json"})
    if status != 200 or not isinstance(payload, dict) or not payload.get("token"):
        return err(status, _error_message(payload, text),
                   _hint(status, payload, "/2024-09-01/auth"))

    _token_cache.update(token=payload["token"], user=user,
                        expires_at=time.time() + TOKEN_TTL_SECONDS)
    return ok({"token": payload["token"], "cached": False,
               "expires_in": TOKEN_TTL_SECONDS,
               "expires_at": (datetime.now(timezone.utc)
                              + timedelta(seconds=TOKEN_TTL_SECONDS)).isoformat()})


def _auth_header(auth_token: Optional[str] = None) -> Dict[str, str]:
    """Build the Authorization header, minting a token when needed.

    Returns `{}` when authentication could not be established — callers should
    treat that as a hard stop, because the minting envelope carries the useful
    error/hint and we do not want to flatten it into a generic failure.
    """
    if auth_token:
        return {"Authorization": auth_token}
    if not _token_cache["token"] or _token_cache["expires_at"] - 60 < time.time():
        return {}
    return {"Authorization": _token_cache["token"]}


# ── API ──────────────────────────────────────────────────────────────────────

def ticket_gate(gate_token: str, member_id: str, auth_token: Optional[str] = None,
                retry_auth: bool = True) -> Dict[str, Any]:
    """Fetch a member summary through the ticket-gate endpoint.

    Two path values are required: `gate_token` (a gate/aggregator token, not the
    auth token) and `member_id`. Unknown values produce **404**, not 401.
    """
    if not gate_token or not member_id:
        return err(None, "ticket_gate needs both a gate token and a member id")

    if not auth_token:
        minted = auth()
        if not minted["ok"]:
            return minted  # propagate status/error/hint verbatim
    headers = _auth_header(auth_token)

    path = f"/2024-09-01/ticket-gate/{gate_token}/{member_id}"
    status, payload, text = _request("GET", path, headers=headers)

    if status == 401 and retry_auth and not auth_token:
        fresh = auth(force=True)
        if fresh["ok"]:
            status, payload, text = _request("GET", path, headers=_auth_header())

    if status is not None and 200 <= status < 300:
        return ok(payload)
    return err(status, _error_message(payload, text), _hint(status, payload, path))


def _label(mapping: Dict[int, str], value: Any) -> Optional[str]:
    try:
        return mapping.get(int(value))
    except (TypeError, ValueError):
        return None
