"""x402 monetization gateway — reverse-proxy sidecar for any local HTTP service.

Config-driven (JSON path in X402_CONFIG env or argv[1]). Three billing modes:

  payperuse    every request to a protected route requires an x402 payment
  subscription x402-paid top-up mints credits on an API key; each call costs 1 credit
  metered      like subscription but each route can cost N units (config: route weights)
  timepass     x402-paid pass grants unlimited access for N days (monthly plan etc.)

Error contract (all JSON, machine-readable `code`):
  402 payment_required          -> x402 challenge (PAYMENT-REQUIRED header)
  401 invalid_key               -> missing/unknown/revoked API key
  402 insufficient_credits      -> balance too low; body includes topup hint
  502 upstream_error            -> upstream unreachable (credits auto-refunded)
  502 facilitator_error         -> facilitator down/unreachable
"""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import time

# --- outbound proxy for facilitator calls (Starchild sc-proxy) -------------
_ca = os.environ.get("STARCHILD_API_PROXY_CA_BASE64")
if _ca and not os.environ.get("X402_NO_PROXY"):
    _caf = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    _caf.write(base64.b64decode(_ca))
    _caf.close()
    os.environ.setdefault("SSL_CERT_FILE", _caf.name)
    _h = os.environ["STARCHILD_API_PROXY_HOST"]
    _p = os.environ["STARCHILD_API_PROXY_PORT"]
    _url = f"http://[{_h}]:{_p}" if ":" in _h else f"http://{_h}:{_p}"
    os.environ.setdefault("HTTPS_PROXY", _url)
    os.environ.setdefault("HTTP_PROXY", _url)
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",127.0.0.1,localhost"

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from x402 import x402ResourceServer
from x402.http import HTTPFacilitatorClient
from x402.http.middleware.fastapi import payment_middleware
from x402.mechanisms.evm.exact.register import register_exact_evm_server

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger import Ledger  # noqa: E402
from platform_modes import PLATFORM_MODES, PlatformBilling, decode_payment_header  # noqa: E402

# --------------------------------------------------------------------------
CONFIG_PATH = os.environ.get("X402_CONFIG") or (sys.argv[1] if len(sys.argv) > 1 else "x402.config.json")
with open(CONFIG_PATH) as f:
    CFG = json.load(f)

MODE = CFG["mode"]                      # payperuse | subscription | metered
UPSTREAM = CFG["upstream"].rstrip("/")  # http://127.0.0.1:PORT
PAY_TO = CFG["pay_to"]
NETWORK = CFG.get("network", "eip155:8453")
FACILITATOR_URL = CFG.get("facilitator") or None
# bearer token for facilitators that enforce caller auth (X402_GATEWAY_TOKENS
# on the self-hosted facilitator). Config key `facilitator_token`, env fallback.
FACILITATOR_TOKEN = CFG.get("facilitator_token") or os.environ.get("X402_FACILITATOR_TOKEN", "")
ROUTES = CFG.get("routes", {})          # pattern -> {price | units}
TOPUP = CFG.get("topup", {})            # {price_per_credit_usd, min_credits}
STATE_DIR = CFG.get("state_dir") or os.path.join(os.path.dirname(os.path.abspath(CONFIG_PATH)), ".x402_state")

app = FastAPI(title=f"x402 gateway ({MODE})")

def _fac_client() -> HTTPFacilitatorClient:
    if not FACILITATOR_URL:
        return HTTPFacilitatorClient()
    fc: dict = {"url": FACILITATOR_URL}
    if FACILITATOR_TOKEN:
        _auth = {"Authorization": f"Bearer {FACILITATOR_TOKEN}"}
        fc["create_headers"] = lambda: {"verify": _auth, "settle": _auth, "supported": _auth}
    return HTTPFacilitatorClient(fc)


fac = _fac_client()
server = x402ResourceServer(fac)
register_exact_evm_server(server)

ledger = Ledger(os.path.join(STATE_DIR, "ledger.db")) if MODE in ("subscription", "metered", "timepass") else None
platform_billing = PlatformBilling(CFG) if MODE in PLATFORM_MODES else None


def _err(status: int, code: str, message: str, **extra) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message, **extra}}, status_code=status)


# --------------------------------------------------------------------------
# x402-protected routes
# --------------------------------------------------------------------------
x402_routes: dict = {}

if MODE in PLATFORM_MODES:
    pass  # platform modes bypass the SDK middleware — handled in proxy()
elif MODE == "payperuse":
    for pattern, rc in ROUTES.items():
        x402_routes[pattern] = {
            "accepts": {"scheme": "exact", "payTo": PAY_TO,
                        "price": rc["price"], "network": NETWORK},
            "description": rc.get("description", ""),
        }
elif MODE == "timepass":
    _p = str(TOPUP.get("price_usd", "5"))
    topup_price = _p if _p.startswith("$") else f"${_p}"
    pass_days = float(TOPUP.get("pass_days", 30))
    x402_routes["POST /x402/topup"] = {
        "accepts": {"scheme": "exact", "payTo": PAY_TO,
                    "price": topup_price, "network": NETWORK},
        "description": f"Buy {pass_days:g}-day unlimited access pass",
    }
else:
    # credits are bought through one x402-protected top-up endpoint
    ppc = float(TOPUP.get("price_per_credit_usd", 0.01))
    min_credits = int(TOPUP.get("min_credits", 100))
    topup_price = f"${ppc * min_credits:.6f}".rstrip("0").rstrip(".")
    x402_routes[f"POST /x402/topup"] = {
        "accepts": {"scheme": "exact", "payTo": PAY_TO,
                    "price": topup_price, "network": NETWORK},
        "description": f"Buy {min_credits} credits",
    }

_pending_settles: list = []


def _on_after_settle(ctx):
    """Credit the ledger after a successful on-chain settlement of a top-up."""
    if ledger is None:
        # payperuse mode: settlements need no ledger action
        return
    try:
        # in subscription/metered/timepass modes the ONLY x402-protected route
        # is POST /x402/topup, so every settlement here IS a top-up.
        res = ctx.result
        if MODE == "timepass":
            out = ledger.credit_payment(
                tx_hash=res.transaction or f"no-tx-{time.time()}",
                payer=res.payer or "unknown",
                amount_atomic=str(getattr(res, "amount", "") or ""),
                credits=0,
                network=str(res.network or ""),
                pass_days=float(TOPUP.get("pass_days", 30)),
            )
        else:
            credits = int(TOPUP.get("min_credits", 100))
            out = ledger.credit_payment(
                tx_hash=res.transaction or f"no-tx-{time.time()}",
                payer=res.payer or "unknown",
                amount_atomic=str(getattr(res, "amount", "") or ""),
                credits=credits,
                network=str(res.network or ""),
            )
        _pending_settles.append(out)
    except Exception as e:  # never break settlement on ledger errors; log loudly
        print(f"[x402-gateway] LEDGER CREDIT FAILED: {e}", flush=True)


server.on_after_settle(_on_after_settle)

_mw = payment_middleware(x402_routes, server) if x402_routes else None


@app.middleware("http")
async def x402_mw(request: Request, call_next):
    if _mw is None:
        return await call_next(request)
    try:
        return await _mw(request, call_next)
    except httpx.HTTPError as e:
        return _err(502, "facilitator_error", f"payment facilitator unreachable: {e}")


# --------------------------------------------------------------------------
# abuse protection (outermost middleware — added last so it runs first)
#   - sliding-window rate limit per caller (X-API-Key if present, else IP)
#   - invalid-key brute-force lockout (repeated 401s -> temporary ban)
# --------------------------------------------------------------------------
RATE_LIMIT_PER_MIN = int(CFG.get("rate_limit_per_min", 120))
BAN_AFTER_401 = int(CFG.get("ban_after_invalid_keys", 20))
BAN_SECONDS = int(CFG.get("ban_seconds", 300))
_hits: dict = {}          # caller -> [timestamps within window]
_bad_keys: dict = {}      # ip -> [401 timestamps]
_banned: dict = {}        # ip -> banned_until


def _caller_id(request: Request) -> tuple[str, str]:
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "?"))
    key = request.headers.get("X-API-Key", "")
    return (f"k:{key}" if key else f"ip:{ip}"), ip


@app.middleware("http")
async def abuse_guard(request: Request, call_next):
    now = time.time()
    caller, ip = _caller_id(request)

    until = _banned.get(ip, 0)
    if until > now:
        return _err(429, "temporarily_banned",
                    f"too many invalid keys; retry after {int(until - now)}s")

    window = [t for t in _hits.get(caller, []) if now - t < 60]
    if len(window) >= RATE_LIMIT_PER_MIN:
        return _err(429, "rate_limited",
                    f"limit {RATE_LIMIT_PER_MIN} req/min", retry_after=60)
    window.append(now)
    _hits[caller] = window
    if len(_hits) > 10000:  # bound memory
        _hits.clear()

    response = await call_next(request)

    if response.status_code == 401:
        bad = [t for t in _bad_keys.get(ip, []) if now - t < 60]
        bad.append(now)
        _bad_keys[ip] = bad
        if len(bad) >= BAN_AFTER_401:
            _banned[ip] = now + BAN_SECONDS
    return response


# --------------------------------------------------------------------------
# management + billing endpoints
# --------------------------------------------------------------------------
@app.get("/x402/info")
async def info():
    body = {"mode": MODE, "network": NETWORK, "pay_to": PAY_TO,
            "facilitator": FACILITATOR_URL or "https://x402.org/facilitator",
            "routes": ROUTES}
    if platform_billing is not None:
        body["pricingModel"] = MODE
        body["price_usd"] = CFG.get("price_usd", "0.01")
    elif MODE != "payperuse":
        body["topup"] = {"endpoint": "POST /x402/topup", **TOPUP}
    return body


@app.post("/x402/topup")
async def topup(request: Request):
    """Reached only AFTER x402 middleware verified payment; settlement happens
    after this response, and the ledger is credited in the settle hook.
    The API key is derived deterministically from the payer address, so we
    can hand it out immediately."""
    if ledger is None:
        return _err(404, "not_applicable", "payperuse mode has no top-up")
    hdr = request.headers.get("PAYMENT-SIGNATURE") or request.headers.get("X-PAYMENT") or ""
    payer = ""
    try:
        payload = json.loads(base64.b64decode(hdr))
        payer = (payload.get("payload", {}).get("authorization", {}) or {}).get("from", "")
    except Exception:
        pass
    if not payer:
        return _err(400, "bad_payment_payload", "cannot extract payer address")
    acct = ledger.get_or_create_account(payer)
    return {"ok": True, "api_key": acct["api_key"],
            "note": f"{TOPUP.get('min_credits', 100)} credits will be added once payment settles (same request).",
            "balance_endpoint": "GET /x402/balance"}


@app.get("/x402/balance")
async def balance(request: Request):
    if ledger is None:
        return _err(404, "not_applicable", "payperuse mode has no credits")
    key = request.headers.get("X-API-Key", "")
    acct = ledger.lookup_key(key)
    if not acct:
        return _err(401, "invalid_key", "missing or unknown API key")
    out = {"credits": acct["credits"], "payer": acct["payer"]}
    if MODE == "timepass":
        exp = acct.get("pass_expires_at") or 0
        out.update(pass_expires_at=exp, pass_active=exp > time.time())
    return out


@app.get("/x402/stats")
async def stats(request: Request):
    admin = CFG.get("admin_token")
    if not admin:
        # deny-by-default: stats stay closed until an admin_token is configured
        return _err(503, "stats_disabled", "set admin_token in config to enable /x402/stats")
    if request.headers.get("X-Admin-Token") != admin:
        return _err(401, "unauthorized", "admin token required")
    return ledger.stats() if ledger else {"mode": MODE}


@app.get("/x402/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{UPSTREAM}/", follow_redirects=True)
            up = r.status_code < 500
    except Exception:
        up = False
    return {"gateway": "ok", "upstream": "ok" if up else "down", "mode": MODE}


# --------------------------------------------------------------------------
# reverse proxy (catch-all, must be registered last)
# --------------------------------------------------------------------------
def _route_units(method: str, path: str) -> int:
    for pattern, rc in ROUTES.items():
        try:
            m, p = pattern.split(" ", 1)
        except ValueError:
            m, p = "*", pattern
        if m not in ("*", method):
            continue
        if p.endswith("*"):
            if path.startswith(p[:-1]):
                return int(rc.get("units", 1))
        elif p == path:
            return int(rc.get("units", 1))
    return 0  # unmatched -> free


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(path: str, request: Request):
    full = "/" + path
    units = _route_units(request.method, full)
    key = request.headers.get("X-API-Key", "")

    if full in ("/.well-known/x402", "/.well-known/x402/"):
        # discovery endpoint (Coinbase Bazaar / Cloudflare-style price discovery)
        return {
            "x402Version": 2,
            "kind": "http",
            "mode": MODE,
            "network": NETWORK,
            "payTo": PAY_TO,
            "facilitator": FACILITATOR_URL or "default",
            "resources": [
                {"resource": route, **{k: v for k, v in spec.items() if k != "accepts"},
                 "accepts": spec.get("accepts")}
                for route, spec in x402_routes.items()
            ],
            "routes": CFG.get("routes", {}),
        }

    # ---- platform pricing modes (community-gateway contract) -------------
    if platform_billing is not None and units > 0:
        pb = platform_billing
        raw = request.headers.get("X-PAYMENT") or request.headers.get("PAYMENT-SIGNATURE") or ""
        if not raw:
            return JSONResponse(pb.challenge_body(full), status_code=402)
        payload, payer = decode_payment_header(raw)
        if not payer:
            return JSONResponse(pb.challenge_body(full, error="malformed X-PAYMENT header"),
                                status_code=402)
        try:
            v = await pb.verify(payload, full)
        except Exception as e:
            return _err(502, "facilitator_error", f"payment facilitator unreachable: {e}")
        if not v.get("isValid"):
            return JSONResponse(pb.challenge_body(
                full, error=v.get("invalidReason", "payment verification failed")),
                status_code=402)
        payer = v.get("payer") or payer

        if not await pb.already_paid(payer):
            try:
                s = await pb.settle(payload, full)
            except Exception as e:
                return _err(502, "facilitator_error", f"settle failed: {e}")
            if not s.get("success"):
                return JSONResponse(pb.challenge_body(
                    full, error=s.get("errorReason", "payment settlement failed")),
                    status_code=402)
            if MODE != "pay_per_use":
                pb.grant_cache(payer)

    if MODE == "timepass" and units > 0:
        if not key:
            return _err(401, "invalid_key", "X-API-Key header required",
                        topup="POST /x402/topup (x402 payment)")
        p = ledger.check_pass(key)
        if not p["ok"]:
            if p["error"] == "pass_expired":
                return _err(402, "pass_expired", "access pass expired",
                            expired_at=p.get("pass_expires_at"),
                            topup="POST /x402/topup (x402 payment)")
            return _err(401, "invalid_key", "unknown or revoked API key")

    if MODE in ("subscription", "metered") and units > 0:
        if not key:
            return _err(401, "invalid_key", "X-API-Key header required",
                        topup="POST /x402/topup (x402 payment)")
        d = ledger.deduct(key, units, route=full)
        if not d["ok"]:
            if d["error"] == "insufficient_credits":
                return _err(402, "insufficient_credits",
                            f"balance {d.get('credits', 0)} < required {units}",
                            topup="POST /x402/topup (x402 payment)")
            return _err(401, "invalid_key", "unknown or revoked API key")

    body = await request.body()
    # strip gateway-only headers before forwarding: the upstream service must
    # never see API keys, payment signatures, or admin tokens (log-leak risk).
    _GATEWAY_HEADERS = ("host", "content-length", "x-api-key", "x-admin-token")
    fwd_headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in _GATEWAY_HEADERS
                   and not k.lower().startswith("payment-")}
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.request(request.method, f"{UPSTREAM}{full}",
                                params=dict(request.query_params),
                                content=body, headers=fwd_headers)
    except Exception as e:
        if MODE in ("subscription", "metered") and units > 0:
            ledger.refund(key, units, route=full)  # don't charge for our failure
        return _err(502, "upstream_error", f"upstream unreachable: {e}")

    if r.status_code >= 500 and MODE in ("subscription", "metered") and units > 0:
        ledger.refund(key, units, route=full)

    resp_headers = {k: v for k, v in r.headers.items()
                    if k.lower() not in ("content-length", "transfer-encoding", "content-encoding")}
    return Response(content=r.content, status_code=r.status_code,
                    headers=resp_headers, media_type=r.headers.get("content-type"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(CFG.get("port", 8402)), log_level="warning")
