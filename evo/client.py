"""
EVO (ABC Evo / W12) REST client — shared HTTP, auth, date and error layer.

Auth model — HTTP Basic:
    username = the gym DNS you use to sign into EVO
    password = the token ("secret key") generated inside EVO at
               Configuracoes > Integracoes > card EVO > Tokens > NOVO TOKEN

Tokens live for 2 years, are scoped per branch (or multi-branch for ADM keys,
which then REQUIRE `idBranch` on calls that accept it) and per endpoint.
GET endpoints are the "read" permissions; POST/PUT/PATCH/DELETE are "write".
A 401 on one endpoint while others work means the token lacks that endpoint's
permission — regenerate it with the permission ticked.

Env (collect with request_env_input, never ask for these in chat):
    EVO_DNS        gym DNS, e.g. "minhaacademia"
    EVO_API_TOKEN  the token string
    EVO_BASE_URL   optional override (default: production host below)

Every public function in this skill returns the same envelope:
    {"ok": True,  "status": 200, "data": <EVO payload>}
    {"ok": False, "status": 401, "error": "...", "hint": "..."}

Spec:  https://evo-integracao.w12app.com.br/swagger/v1/swagger.json
Docs:  https://api.abcevo.com/
"""

import base64
import json
import os
import re
import unicodedata
from datetime import date as _date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

BASE = (os.environ.get("EVO_BASE_URL") or "https://evo-integracao-api.w12app.com.br").rstrip("/")
TIMEOUT = 60

# ── Enumerations (labels come from the spec's own parameter/schema docs) ──────

MEMBER_STATUS = {1: "active", 2: "inactive"}

MEMBERSHIP_CONTRACT_STATUS = {
    1: "active", 2: "canceled", 3: "expired", 4: "suspended", 5: "in_queue",
}

MEMBER_MEMBERSHIP_STATUS = {
    1: "active", 2: "blocked", 3: "canceled", 5: "on_leave",
    6: "pending_payment", 7: "finished", 8: "awaiting_start",
}

ATTENDANCE_STATUS = {0: "attending", 1: "absent", 2: "justified_absence"}

_RATE_HINT = (
    "EVO rate limits: 5 req/s and 40 req/min per IP, 10,000 req/h per token, "
    "20,000 req/h per gym DNS. Back off ~1s (or 1min) and retry; the hourly "
    "limits are lifted between 00:00 and 05:59."
)


class EvoConfigError(RuntimeError):
    """Raised when EVO_DNS / EVO_API_TOKEN are not configured."""


# ── Envelope helpers ─────────────────────────────────────────────────────────

def ok(data, status: int = 200) -> Dict[str, Any]:
    return {"ok": True, "status": status, "data": data}


def err(status: Optional[int], message: str, hint: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "status": status, "error": message}
    if hint:
        out["hint"] = hint
    return out


# ── Auth ─────────────────────────────────────────────────────────────────────

def credentials() -> tuple:
    """Return (dns, token) or raise EvoConfigError naming what is missing."""
    dns = (os.environ.get("EVO_DNS") or "").strip()
    token = (os.environ.get("EVO_API_TOKEN") or "").strip()
    missing = [name for name, value in (("EVO_DNS", dns), ("EVO_API_TOKEN", token)) if not value]
    if missing:
        raise EvoConfigError(
            "missing EVO credential(s): " + ", ".join(missing)
            + ". Generate them in EVO at Configuracoes > Integracoes > EVO > "
              "Tokens, then call request_env_input."
        )
    return dns, token


def _auth_header() -> Dict[str, str]:
    dns, token = credentials()
    blob = base64.b64encode(f"{dns}:{token}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {blob}"}


# ── Transport ────────────────────────────────────────────────────────────────

def _proxied():
    """Return (proxied_get, proxied_post) or (None, None) off-platform."""
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


def _direct(method: str, url: str, params: Dict[str, Any], body: Optional[Any],
            headers: Dict[str, str], timeout: int):
    """Non-proxied request, used for DELETE/PUT/PATCH and off-platform runs.

    Tries `requests` first (it honours the environment's proxy settings, which
    is what we want inside the platform container), then falls back to the
    stdlib. Some proxy setups accept one client and not the other, so a fallback
    beats an environment-specific guess.
    """
    notes = []
    try:
        import requests
        try:
            return requests.request(method, url, params=params or None, json=body,
                                    headers=headers, timeout=timeout)
        except Exception as exc:
            notes.append(f"requests: {type(exc).__name__}")
    except ImportError:
        notes.append("requests: not installed")

    import urllib.error
    import urllib.parse
    import urllib.request

    full = url
    if params:
        full += ("&" if "?" in full else "?") + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(full, data=data, method=method)
    for key, value in headers.items():
        req.add_header(key, value)
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
    """Minimal response shim for the urllib path."""

    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text) if self.text else None


def _clean_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Drop None, stringify booleans (ASP.NET wants lowercase), join lists."""
    out: Dict[str, Any] = {}
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif isinstance(value, (list, tuple, set)):
            items = [str(v) for v in value if v is not None]
            if items:
                out[key] = ",".join(items)
        elif isinstance(value, (_date, datetime)):
            out[key] = _date_str(value)
        else:
            out[key] = value
    return out


def _error_message(payload: Any) -> str:
    if isinstance(payload, dict):
        if payload.get("error"):
            return str(payload["error"])
        if payload.get("message"):
            return str(payload["message"])
        if payload.get("mensagens"):
            msg = payload["mensagens"]
            return "; ".join(msg) if isinstance(msg, list) else str(msg)
    return json.dumps(payload, ensure_ascii=False)[:400]


def _hint(status: Optional[int], payload: Any) -> Optional[str]:
    text = _error_message(payload)
    lowered = text.lower()
    if status == 429:
        return _RATE_HINT
    if status == 401:
        if "daily request limit" in lowered or "monthly" in lowered:
            return ("EVO API Plus quota exhausted (1,000 requests/month, 100/day per "
                    "branch). It resets next period; upgrade to API Pro for unlimited "
                    "volume, or call GET /api/v1/configuration/api-usage to track usage.")
        if "api_cost_limit_reached" in lowered or "cost limit" in lowered:
            return ("The API Pro cost limit configured for this token was reached, so EVO "
                    "paused the key. Raise the limit in EVO or wait for the new billing "
                    "period.")
        if "unauthorized" in lowered:
            return ("Check EVO_DNS (gym DNS, not e-mail) and EVO_API_TOKEN. If other "
                    "endpoints work, this token is missing the permission for THIS "
                    "endpoint — regenerate it with that permission enabled.")
    return None


def _call(method: str, path: str, params: Optional[Dict[str, Any]] = None,
          body: Optional[Any] = None, timeout: int = TIMEOUT) -> Dict[str, Any]:
    """Perform one EVO API call and return the uniform envelope."""
    try:
        headers = _auth_header()
    except EvoConfigError as exc:
        return err(None, str(exc))

    url = BASE + path
    query = _clean_params(params)
    proxied_get, proxied_post = _proxied()

    try:
        if proxied_get is None:
            response = _direct(method, url, query, body, {**headers, "Accept": "application/json"}, timeout)
        elif method == "GET":
            response = proxied_get(url, params=query, headers=headers, timeout=timeout)
        elif method == "POST":
            response = proxied_post(url, params=query, json=body or {},
                                    headers=headers, timeout=timeout)
        else:
            # proxied_get/proxied_post cannot express other verbs.
            response = _direct(method, url, query, body, {**headers, "Accept": "application/json"}, timeout)
    except Exception as exc:  # network / proxy failures
        return err(None, f"{type(exc).__name__}: {exc}")

    status = getattr(response, "status_code", None)
    try:
        payload = response.json()
    except Exception:
        payload = None

    if payload is None:
        text = (getattr(response, "text", "") or "")[:400]
        return err(status, f"non-JSON response from EVO: {text}")

    if status is not None and 200 <= status < 300:
        return ok(payload, status)
    return err(status, _error_message(payload), _hint(status, payload))


# ── Argument normalisation ───────────────────────────────────────────────────

def _date_str(value: Any) -> Optional[str]:
    """Normalise anything reasonable to EVO's yyyy-MM-dd."""
    if value is None:
        return None
    if isinstance(value, (datetime, _date)):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    today = _date.today()
    if lowered in ("today", "hoje", "agora"):
        return today.isoformat()
    if lowered in ("tomorrow", "amanha", "amanhã"):
        return (today + timedelta(days=1)).isoformat()
    if lowered in ("yesterday", "ontem"):
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
    return text  # let EVO validate and report


def _norm(value: Any) -> str:
    """Lowercase, accent-free text for fuzzy matching ('Pilates' == 'Pilátes')."""
    if value is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped).strip().lower()


def _only_digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _label(mapping: Dict[int, str], code: Any) -> Optional[str]:
    try:
        return mapping.get(int(code))
    except (TypeError, ValueError):
        return None


def _digits(value: Any) -> str:
    return _only_digits(value)


def _full_name(row: Dict[str, Any]) -> str:
    first = row.get("registerName") or row.get("firstName") or ""
    last = row.get("registerLastName") or row.get("lastName") or ""
    return re.sub(r"\s+", " ", f"{first} {last}").strip()