"""Self-hosted x402 facilitator — /verify, /settle, /supported, /facilitator/stats.

Implements the facilitator role of x402 V2 for `exact` on EVM (Base) without
any external dependency (no CDP, no KYC). Compatible with the standard x402
SDK HTTPFacilitatorClient wire format.

Run locally:   python3 skills/x402/facilitator/server.py            (port 8410)
Platform mode: uvicorn server:app  with X402_SETTLER_PRIVATE_KEY set.
"""
from __future__ import annotations

import base64 as _b64
import os
import sys
import tempfile as _tf
import time

# outbound proxy for RPC calls (Starchild sc-proxy); no-op outside Starchild
_ca = os.environ.get("STARCHILD_API_PROXY_CA_BASE64")
if _ca and not os.environ.get("X402_NO_PROXY"):
    _caf = _tf.NamedTemporaryFile(suffix=".pem", delete=False)
    _caf.write(_b64.b64decode(_ca)); _caf.close()
    os.environ.setdefault("SSL_CERT_FILE", _caf.name)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _caf.name)
    _h, _p = os.environ["STARCHILD_API_PROXY_HOST"], os.environ["STARCHILD_API_PROXY_PORT"]
    _u = f"http://[{_h}]:{_p}" if ":" in _h else f"http://{_h}:{_p}"
    os.environ.setdefault("HTTPS_PROXY", _u); os.environ.setdefault("HTTP_PROXY", _u)
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",127.0.0.1,localhost"

from eth_account import Account
from eth_account.messages import encode_typed_data
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger import FacilitatorLedger  # noqa: E402
from settler import Settler  # noqa: E402

STATE_DIR = os.environ.get("X402_FACILITATOR_STATE",
                           "/data/workspace/.x402/facilitator")
MAX_SETTLES_PER_PAYER_PER_MIN = int(os.environ.get("X402_PAYER_RATE_LIMIT", "30"))

# ---- caller controls (anti gas-drain: the settler pays gas for every settle) ----
# X402_PAYTO_ALLOWLIST: comma-separated recipient addresses. If set, verify &
#   settle are refused for any requirements.payTo outside the list.
# X402_GATEWAY_TOKENS: comma-separated bearer tokens. If set, callers must send
#   Authorization: Bearer <token> (registered gateways only).
PAYTO_ALLOWLIST = {a.strip().lower() for a in
                   os.environ.get("X402_PAYTO_ALLOWLIST", "").split(",") if a.strip()}
GATEWAY_TOKENS = {t.strip() for t in
                  os.environ.get("X402_GATEWAY_TOKENS", "").split(",") if t.strip()}


def _caller_allowed(request: Request, requirements: dict) -> str | None:
    """Returns an error reason, or None if the caller may use this facilitator."""
    if GATEWAY_TOKENS:
        tok = request.headers.get("authorization", "")
        if not (tok.startswith("Bearer ") and tok[7:] in GATEWAY_TOKENS):
            return "gateway_auth_required"
    if PAYTO_ALLOWLIST:
        if str(requirements.get("payTo", "")).lower() not in PAYTO_ALLOWLIST:
            return "pay_to_not_allowed"
    return None

app = FastAPI(title="starchild x402 facilitator")
ledger = FacilitatorLedger(os.path.join(STATE_DIR, "facilitator.db"))
settler = Settler(STATE_DIR)

KNOWN_ASSETS = {  # network -> {asset_address: (name, version)}
    "eip155:8453": {"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": ("USD Coin", "2")},
    "eip155:84532": {"0x036cbd53842c5426634e7929541ec2318f3dcf7e": ("USDC", "2")},
}

EIP3009_TYPES = {
    "TransferWithAuthorization": [
        {"name": "from", "type": "address"}, {"name": "to", "type": "address"},
        {"name": "value", "type": "uint256"}, {"name": "validAfter", "type": "uint256"},
        {"name": "validBefore", "type": "uint256"}, {"name": "nonce", "type": "bytes32"},
    ]
}


def _extract(body: dict) -> tuple[dict, dict]:
    return body.get("paymentPayload") or body.get("payload") or {}, \
           body.get("paymentRequirements") or body.get("requirements") or {}


def _verify_core(payload: dict, requirements: dict) -> tuple[bool, str, dict]:
    """Returns (valid, reason, auth). Pure + on-chain read checks, no spending."""
    inner = payload.get("payload", {})
    auth = inner.get("authorization", {})
    sig = inner.get("signature", "")
    network = str(requirements.get("network", ""))
    asset = str(requirements.get("asset", "")).lower()

    if network not in KNOWN_ASSETS:
        return False, "unsupported_network", auth
    if asset not in KNOWN_ASSETS[network]:
        return False, "unsupported_asset", auth

    # amount / recipient must match requirements
    try:
        if int(auth.get("value", 0)) < int(requirements.get("amount") or
                                           requirements.get("maxAmountRequired", 0)):
            return False, "amount_below_required", auth
    except (TypeError, ValueError):
        return False, "bad_amount", auth
    if auth.get("to", "").lower() != str(requirements.get("payTo", "")).lower():
        return False, "recipient_mismatch", auth

    # time window
    now = int(time.time())
    try:
        if now < int(auth["validAfter"]) or now > int(auth["validBefore"]):
            return False, "outside_validity_window", auth
    except (KeyError, ValueError):
        return False, "bad_validity_window", auth

    # signature recovery
    name, version = KNOWN_ASSETS[network][asset]
    extra = requirements.get("extra") or {}
    name, version = extra.get("name", name), extra.get("version", version)
    chain_id = int(network.split(":")[1])
    typed = {
        "domain": {"name": name, "version": version, "chainId": chain_id,
                   "verifyingContract": asset},
        "types": {**EIP3009_TYPES, "EIP712Domain": [
            {"name": "name", "type": "string"}, {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"}]},
        "primaryType": "TransferWithAuthorization",
        "message": {"from": auth["from"], "to": auth["to"], "value": int(auth["value"]),
                    "validAfter": int(auth["validAfter"]),
                    "validBefore": int(auth["validBefore"]), "nonce": auth["nonce"]},
    }
    try:
        recovered = Account.recover_message(encode_typed_data(full_message=typed),
                                            signature=sig)
    except Exception as e:
        return False, f"signature_recovery_failed: {e}", auth
    if recovered.lower() != auth["from"].lower():
        return False, "invalid_signature", auth

    # on-chain: balance + authorization unused
    try:
        ok, reason = settler.check_onchain(network, asset, auth["from"],
                                           int(auth["value"]),
                                           bytes.fromhex(auth["nonce"][2:]))
    except Exception as e:
        return False, f"rpc_error: {e}", auth
    if not ok:
        return False, reason, auth
    return True, "", auth


@app.post("/verify")
async def verify(request: Request):
    body = await request.json()
    payload, requirements = _extract(body)
    denied = _caller_allowed(request, requirements)
    if denied:
        return {"isValid": False, "payer": "", "invalidReason": denied}
    valid, reason, auth = _verify_core(payload, requirements)
    ledger.record_verify(auth.get("from", ""), auth.get("to", ""),
                         str(auth.get("value", "")),
                         str(requirements.get("network", "")), valid, reason)
    resp = {"isValid": valid, "payer": auth.get("from", "")}
    if not valid:
        resp["invalidReason"] = f"invalid_exact_evm_{reason}" if "_" in reason else reason
    return resp


@app.post("/settle")
async def settle(request: Request):
    body = await request.json()
    payload, requirements = _extract(body)

    denied = _caller_allowed(request, requirements)
    if denied:
        return {"success": False, "payer": "", "transaction": "",
                "network": str(requirements.get("network", "")),
                "errorReason": denied}

    # re-verify at settle time (state may have changed since /verify)
    valid, reason, auth = _verify_core(payload, requirements)
    network = str(requirements.get("network", ""))
    asset = str(requirements.get("asset", "")).lower()
    fail_base = {"success": False, "payer": auth.get("from", ""),
                 "network": network, "transaction": ""}
    if not valid:
        return {**fail_base, "errorReason": f"invalid_exact_evm_{reason}"}

    payer = auth["from"].lower()
    # rate limit per payer (gas-drain protection)
    if ledger.payer_recent_count(payer) >= MAX_SETTLES_PER_PAYER_PER_MIN:
        return {**fail_base, "errorReason": "rate_limited"}

    # idempotency on (payer, nonce, asset, network) — EIP-3009 nonce is per-payer
    resource = str(requirements.get("resource", ""))
    if not ledger.begin_settlement(auth["nonce"], payer, auth["to"].lower(),
                                   str(auth["value"]), asset, network,
                                   resource=resource):
        prev = ledger.get_settlement(payer, auth["nonce"], asset, network)
        if prev and prev["status"] == "confirmed":
            # Echo success ONLY if every binding field matches the original —
            # otherwise a caller could replay a public on-chain nonce to spoof
            # payment for a different recipient/amount/resource.
            same = (prev["pay_to"] == auth["to"].lower()
                    and prev["amount_atomic"] == str(auth["value"])
                    and (prev["resource"] or "") == resource)
            if same:
                return {"success": True, "payer": payer, "network": network,
                        "transaction": prev["tx_hash"]}
            return {**fail_base, "errorReason": "nonce_reuse_mismatch"}
        return {**fail_base, "errorReason": "settlement_in_progress_or_failed"}

    result = settler.settle(network, asset, auth, payload.get("payload", {}).get("signature", ""))
    if result["success"]:
        ledger.update_settlement(payer, auth["nonce"], asset, network,
                                 status="confirmed", tx_hash=result["tx_hash"],
                                 gas_used=result["gas_used"], confirmed_at=time.time())
        return {"success": True, "payer": payer, "network": network,
                "transaction": result["tx_hash"]}
    ledger.update_settlement(payer, auth["nonce"], asset, network,
                             status="failed", error=result["error"],
                             tx_hash=result.get("tx_hash"))
    return {**fail_base, "errorReason": result["error"] or "settle_failed"}


@app.get("/supported")
async def supported():
    kinds = [{"x402Version": 2, "scheme": "exact", "network": n}
             for n in KNOWN_ASSETS]
    return {"kinds": kinds}


@app.get("/facilitator/stats")
async def stats(request: Request):
    admin = os.environ.get("X402_ADMIN_TOKEN")
    if not admin:
        # deny-by-default: never expose stats on an unconfigured deployment
        return JSONResponse({"error": "stats_disabled_no_admin_token"}, status_code=503)
    if request.headers.get("X-Admin-Token") != admin:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    out = ledger.stats()
    out["settler_address"] = settler.address
    for net in KNOWN_ASSETS:
        try:
            out[f"gas_balance_{net.replace(':', '_')}"] = settler.gas_balance(net)
        except Exception:
            out[f"gas_balance_{net.replace(':', '_')}"] = "rpc_error"
    return out


@app.get("/facilitator/health")
async def health():
    return {"ok": True, "settler": settler.address}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0",
                port=int(os.environ.get("X402_FACILITATOR_PORT", "8410")),
                log_level="warning")
