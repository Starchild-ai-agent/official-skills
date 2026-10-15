"""
Asaas REST client — shared HTTP, auth, error and normalisation layer.

Auth model — a single API key in a header:

    access_token: <key>

Not `Authorization: Bearer`. Keys are **per environment**, and the environments
share nothing — not accounts, not data, not keys. A production key sent to the
sandbox answers `401 Unauthorized`, and vice versa.

    sandbox     https://api-sandbox.asaas.com/v3
    production  https://api.asaas.com/v3

Env (collect with request_env_input, never ask for these in chat):
    ASAAS_API_KEY     the key, from the dashboard or sandbox.asaas.com
    ASAAS_ENV         "sandbox" (default) or "production"
    ASAAS_BASE_URL    optional override; wins over ASAAS_ENV

Defaults to **sandbox** on purpose: pointing at production should be a decision
someone typed out, not a default someone forgot to change.

Error shape — Asaas returns a list, and a 400 can carry several at once:

    {"errors": [{"code": "invalid_value", "description": "..."}]}

Every public function in this skill returns the same envelope:
    {"ok": True,  "status": 200, "data": <Asaas payload>}
    {"ok": False, "status": 400, "error": "...", "hint": "..."}

Docs:  https://docs.asaas.com/
Index: https://docs.asaas.com/reference/llms.txt
"""

import json
import os
import re
from typing import Any, Dict, Optional

BASE_SANDBOX = "https://api-sandbox.asaas.com/v3"
BASE_PRODUCTION = "https://api.asaas.com/v3"
TIMEOUT = 45

# ── Enumerations (from the endpoints' own OpenAPI fragments) ─────────────────

# What you may SEND when creating a charge. `UNDEFINED` lets the payer pick on
# the checkout page. Note this is narrower than what a charge may COME BACK as.
BILLING_TYPES = ("UNDEFINED", "BOLETO", "CREDIT_CARD", "PIX")

# What a charge may come back as. TRANSFER/DEPOSIT appear only on reads.
BILLING_TYPES_READ = BILLING_TYPES + ("DEBIT_CARD", "TRANSFER", "DEPOSIT")

PAYMENT_STATUS = {
    "PENDING": "waiting for payment",
    "AWAITING_RISK_ANALYSIS": "in risk analysis",
    "AWAITING_CHARGEBACK_REVERSAL": "awaiting chargeback reversal",
    "CONFIRMED": "payment confirmed, not yet credited",
    "RECEIVED": "credited to the balance",
    "RECEIVED_IN_CASH": "received in cash, confirmed manually",
    "OVERDUE": "past the due date",
    "DUNNING_REQUESTED": "dunning requested",
    "DUNNING_RECEIVED": "dunning paid",
    "REFUND_REQUESTED": "refund requested",
    "REFUND_IN_PROGRESS": "refund in progress",
    "REFUNDED": "refunded",
    "CHARGEBACK_REQUESTED": "chargeback requested",
    "CHARGEBACK_DISPUTE": "chargeback under dispute",
    "AWAITING_CHARGEBACK_REVERSAL": "awaiting chargeback reversal",
}

#: The two statuses that mean "the money is ours". Everything else is pending,
#: refused or reversed. `CONFIRMED` precedes `RECEIVED` by the settlement delay.
SETTLED_STATUS = ("CONFIRMED", "RECEIVED", "RECEIVED_IN_CASH")

WEBHOOK_SEND_TYPES = ("SEQUENTIALLY", "NON_SEQUENTIALLY")

#: The payment-family events worth subscribing to by default. Asaas exposes 112
#: events in total; these are the ones that move a sale forward or backwards.
WEBHOOK_EVENTS_CORE = (
    "PAYMENT_CREATED",
    "PAYMENT_CONFIRMED",
    "PAYMENT_RECEIVED",
    "PAYMENT_OVERDUE",
    "PAYMENT_REFUNDED",
    "PAYMENT_CHARGEBACK_REQUESTED",
    "PAYMENT_CHARGEBACK_DISPUTE",
)

_RATE_HINT = (
    "Asaas rate limits requests per account and per endpoint. On 429 back off "
    "and retry — do not loop. See docs.asaas.com/reference/rate-e-quota-limit."
)

_PAGINATION_HINT = (
    "Asaas pages with `offset` + `limit` (limit max 100). Read `hasMore` from the "
    "response and advance `offset` by `limit`; `totalCount` gives the full size."
)


class AsaasConfigError(RuntimeError):
    """Raised when ASAAS_API_KEY is not configured."""


# ── Envelope helpers ─────────────────────────────────────────────────────────

def ok(data, status: int = 200) -> Dict[str, Any]:
    return {"ok": True, "status": status, "data": data}


def err(status: Optional[int], message: str, hint: Optional[str] = None,
        **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "status": status, "error": message}
    if hint:
        out["hint"] = hint
    if extra:
        out.update(extra)
    return out


# ── Auth ─────────────────────────────────────────────────────────────────────

def environment() -> str:
    """Return "sandbox" or "production" (base URL override wins)."""
    explicit = (os.environ.get("ASAAS_BASE_URL") or "").strip()
    if explicit:
        return "production" if "sandbox" not in explicit else "sandbox"
    env = (os.environ.get("ASAAS_ENV") or "sandbox").strip().lower()
    return "production" if env.startswith("prod") else "sandbox"


def base_url() -> str:
    explicit = (os.environ.get("ASAAS_BASE_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")
    return BASE_PRODUCTION if environment() == "production" else BASE_SANDBOX


def credentials() -> str:
    """Return the API key or raise AsaasConfigError naming what is missing."""
    key = (os.environ.get("ASAAS_API_KEY") or "").strip()
    if not key:
        raise AsaasConfigError(
            "missing ASAAS_API_KEY. Create an account at https://sandbox.asaas.com/ "
            "(self-service, no CNPJ — but the signup form asks for a real full name, "
            "a personal mobile for the activation code, and a full address, so the "
            "user should be the one filling it in) and generate a key there, then "
            "call request_env_input. Set ASAAS_ENV=production to target production."
        )
    return key


def _auth_header() -> Dict[str, str]:
    return {"access_token": credentials(), "Content-Type": "application/json"}


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


class _RawResponse:
    """Minimal response shim for the urllib path."""

    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text) if self.text else None


def _direct(method: str, url: str, params: Dict[str, Any], body: Optional[Any],
            headers: Dict[str, str], timeout: int):
    """Non-proxied request, used for DELETE/PUT/PATCH and off-platform runs.

    Tries `requests` first (it honours the environment's proxy settings, which is
    what we want inside the platform container), then falls back to the stdlib.
    """
    try:
        import requests
        try:
            return requests.request(method, url, params=params or None, json=body,
                                    headers=headers, timeout=timeout)
        except Exception:
            pass
    except ImportError:
        pass

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
    except urllib.error.HTTPError as exc:
        return _RawResponse(exc.code, exc.read().decode("utf-8", "replace"))


def _clean_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Drop None; stringify booleans; join lists with commas."""
    out: Dict[str, Any] = {}
    for key, value in (params or {}).items():
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif isinstance(value, (list, tuple)):
            out[key] = ",".join(str(v) for v in value)
        else:
            out[key] = value
    return out


def _error_message(payload: Any) -> str:
    """Asaas returns {"errors":[{"code":..,"description":..}]}; flatten it."""
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            parts = []
            for item in errors:
                if isinstance(item, dict):
                    code = item.get("code") or ""
                    desc = item.get("description") or ""
                    parts.append(f"{code}: {desc}".strip(": ") or str(item))
                else:
                    parts.append(str(item))
            return "; ".join(parts)[:500]
        for key in ("message", "description", "detail"):
            if payload.get(key):
                return str(payload[key])[:500]
    return json.dumps(payload, ensure_ascii=False)[:500] if payload is not None else ""


def _hint(status: Optional[int], payload: Any) -> Optional[str]:
    text = _error_message(payload).lower()
    if status == 401:
        return ("The key is missing, wrong, or from the other environment. Sandbox and "
                "production keys are not interchangeable — check ASAAS_ENV and that "
                "ASAAS_API_KEY belongs to it.")
    if status == 403:
        return ("Authenticated but not allowed. On Asaas this usually means the account "
                "has not been approved for that operation, or the resource belongs to a "
                "different account.")
    if status == 404:
        return ("No such resource **in this account**. Sandbox and production hold "
                "entirely separate data, and ids are not portable between them.")
    if status == 429:
        return _RATE_HINT
    if status == 400 and ("cpfCnpj" in text or "cpf" in text):
        return ("Asaas requires a valid CPF/CNPJ on the customer — it is one of the two "
                "required fields. Fix the member's document before creating a charge.")
    if status == 400 and "billingType" in text:
        return "billingType must be one of: " + ", ".join(BILLING_TYPES)
    return None


def call(method: str, path: str, params: Optional[Dict[str, Any]] = None,
         body: Optional[Any] = None, timeout: int = TIMEOUT) -> Dict[str, Any]:
    """Perform one Asaas call and return the uniform envelope.

    `path` is relative to the versioned base (e.g. "/customers"), or an absolute
    URL. GETs are sent without a body — Asaas rejects a GET that carries one.
    """
    try:
        headers = _auth_header()
    except AsaasConfigError as exc:
        return err(None, str(exc))

    url = path if path.startswith("http") else base_url() + path
    clean = _clean_params(params)
    payload = None if method.upper() == "GET" else body

    proxied_get, proxied_post = _proxied()
    try:
        if proxied_get and method.upper() == "GET":
            response = proxied_get(url, params=clean, headers=headers, timeout=timeout)
        elif proxied_post and method.upper() == "POST":
            response = proxied_post(url, params=clean, json=payload, headers=headers,
                                    timeout=timeout)
        else:
            response = _direct(method.upper(), url, clean, payload, headers, timeout)
    except Exception as exc:
        return err(None, f"{type(exc).__name__}: {exc}",
                   hint="transport failed before Asaas answered; check network/proxy")

    status = getattr(response, "status_code", None)
    try:
        data = response.json()
    except Exception:
        data = getattr(response, "text", None)

    if status is not None and 200 <= status < 300:
        return ok(data, status)
    if status is None:
        return err(None, _error_message(data) or "no status returned")
    return err(status, _error_message(data), _hint(status, data))


# ── Argument normalisation ───────────────────────────────────────────────────

def _date_str(value: Any) -> Optional[str]:
    """Normalise anything reasonable to Asaas's YYYY-MM-DD."""
    if value is None or value == "":
        return None
    from datetime import date, datetime, timedelta

    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip().lower()
    if text in ("today", "hoje", "now"):
        return date.today().isoformat()
    if text in ("tomorrow", "amanha", "amanhã"):
        return (date.today() + timedelta(days=1)).isoformat()
    if text in ("yesterday", "ontem"):
        return (date.today() - timedelta(days=1)).isoformat()
    if re.fullmatch(r"[+-]\d+", text):
        return (date.today() + timedelta(days=int(text))).isoformat()
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", text)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return str(value).strip()   # let Asaas validate and report


def digits(value: Any) -> str:
    """CPF/CNPJ/phone as bare digits — Asaas rejects punctuation."""
    return re.sub(r"\D", "", str(value or ""))


def _status_label(code: Any) -> Optional[str]:
    return PAYMENT_STATUS.get(str(code or "").upper())


def _money(value: Any) -> Optional[float]:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None
