"""
fiat-onramp skill exports — script-mode skill.

Lets the agent generate a fiat→USDC funding link (MoonPay hosted widget)
for its OWN Privy wallet, send it to the user in chat, and confirm arrival
by polling the wallet balance. No frontend integration required.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/fiat-onramp")
    from exports import create_funding_link, get_usdc_balance, wait_for_funds
    print(create_funding_link(amount_usd=20))
    EOF

Env (workspace/.env, read live on every call):
    MOONPAY_PUBLISHABLE_KEY  pk_live_... / pk_test_...
    MOONPAY_SECRET_KEY       sk_live_... / sk_test_...  (signs the URL)
    MOONPAY_SANDBOX          "1" -> buy-sandbox.moonpay.com (pairs with pk_test)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import sys
import time
import urllib.parse

_ENV_PATH = "/data/workspace/.env"


# Chain/asset the whole platform settles on (matches x402: USDC on Base).
DEFAULT_CURRENCY_CODE = "usdc_base"
BASE_CHAIN_ID = 8453
USDC_BASE_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def _env(key: str) -> str:
    """Live .env read — picks up keys added after process start."""
    try:
        with open(_ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return os.environ.get(key, "")


def _wallet():
    """The wallet skill module (same payer identity as x402)."""
    from core.skill_tools import wallet
    return wallet


def _agent_wallet_address() -> str:
    """The agent's Privy EVM wallet address."""
    info = _wallet().wallet_info()
    return next(w["wallet_address"] for w in info["wallets"]
                if w["chain_type"] == "ethereum")


def create_funding_link(amount_usd: float = 20.0,
                        currency_code: str = DEFAULT_CURRENCY_CODE,
                        base_currency_code: str = "usd",
                        redirect_url: str = "",
                        email: str = "") -> dict:
    """Build a SIGNED MoonPay hosted-widget URL that funds the agent wallet.

    The destination is ALWAYS the agent's own Privy wallet — there is no
    parameter to override it. The walletAddress is pinned server-side and
    covered by the HMAC signature, so neither the user nor a prompt can
    redirect funds elsewhere. A user who wants crypto in their own wallet
    should use MoonPay/an exchange directly.

    Returns {ok, url, wallet_address, amount_usd, currency_code, sandbox,
             baseline_balance} — send `url` to the user, keep
    `baseline_balance` for wait_for_funds().
    """
    pk = _env("MOONPAY_PUBLISHABLE_KEY")
    sk = _env("MOONPAY_SECRET_KEY")
    if not pk or not sk:
        return {"ok": False,
                "error": "MOONPAY_PUBLISHABLE_KEY / MOONPAY_SECRET_KEY not set "
                         "in workspace/.env — request them via secure input first."}

    if float(amount_usd) <= 0:
        return {"ok": False, "error": f"amount_usd must be > 0, got {amount_usd}"}

    addr = _agent_wallet_address()
    sandbox = _env("MOONPAY_SANDBOX") == "1" or pk.startswith("pk_test")
    host = "buy-sandbox.moonpay.com" if sandbox else "buy.moonpay.com"

    params = [
        ("apiKey", pk),
        ("currencyCode", currency_code),
        ("walletAddress", addr),
        ("baseCurrencyCode", base_currency_code),
        ("baseCurrencyAmount", f"{float(amount_usd):g}"),
    ]
    if redirect_url:
        params.append(("redirectURL", redirect_url))
    if email:
        params.append(("email", email))

    query = "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    sig = base64.b64encode(
        hmac.new(sk.encode(), query.encode(), hashlib.sha256).digest()
    ).decode()
    url = (f"https://{host}/{query}"
           f"&signature={urllib.parse.quote_plus(sig)}")

    baseline = get_usdc_balance(addr)
    if not baseline.get("ok"):
        # Without a baseline, arrival can never be confirmed — refuse to hand
        # out the link rather than break the "no arrival claim without
        # balance evidence" rule downstream.
        return {"ok": False,
                "error": "baseline balance read failed — cannot confirm arrival "
                         "later, so no funding link was issued. Fix the balance "
                         "read (wallet skill / RPC) and retry.",
                "baseline_error": baseline.get("error"),
                "wallet_address": addr}
    return {"ok": True, "url": url, "wallet_address": addr,
            "amount_usd": float(amount_usd), "currency_code": currency_code,
            "sandbox": sandbox,
            "baseline_balance": baseline.get("balance"),
            "note": "Send `url` to the user. After they pay, call "
                    "wait_for_funds(baseline=baseline_balance) to confirm arrival. "
                    "MoonPay card all-in cost is ~7-8% and min purchase ~$20 — "
                    "set user expectations."}


def get_usdc_balance(address: str = "") -> dict:
    """USDC balance (Base) of the agent wallet — via the wallet skill."""
    addr = address or _agent_wallet_address()
    try:
        res = _wallet().wallet_balance(chain="base", address=addr, asset="usdc")
        bal = None
        if isinstance(res, dict):
            # wallet skill returns debank shape: {"tokens": [{symbol, amount, ...}]}
            if isinstance(res.get("tokens"), list):
                bal = sum(float(t.get("amount", 0)) for t in res["tokens"]
                          if str(t.get("symbol", "")).upper() == "USDC")
            elif isinstance(res.get("balances"), list):
                for b in res["balances"]:
                    if str(b.get("asset", b.get("symbol", ""))).upper() == "USDC":
                        bal = float(b.get("balance", b.get("amount", 0))); break
            else:
                for k in ("balance", "amount", "formatted", "value"):
                    if k in res:
                        bal = float(res[k]); break
        if bal is None:
            return {"ok": False, "error": f"unrecognized balance shape: {res}",
                    "raw": res}
        return {"ok": True, "address": addr, "asset": "USDC", "chain": "base",
                "balance": bal}
    except Exception as e:
        return {"ok": False, "error": f"balance query failed: {e}", "address": addr}


def wait_for_funds(baseline: float,
                   address: str = "",
                   min_increase: float = 0.01,
                   timeout_sec: int = 900,
                   interval_sec: int = 30) -> dict:
    """Poll the wallet until USDC balance rises above baseline+min_increase.

    Blocking — for waits longer than ~2 min run this inside a background
    bash session, not a foreground call. Card payments usually land in
    1-10 min; bank transfers can take much longer than any sane timeout.
    """
    try:
        baseline = float(baseline)
    except (TypeError, ValueError):
        return {"ok": False, "funded": False,
                "error": f"invalid baseline {baseline!r} — must be the numeric "
                         "baseline_balance returned by create_funding_link()."}
    deadline = time.time() + timeout_sec
    last = baseline
    while time.time() < deadline:
        r = get_usdc_balance(address)
        if r.get("ok"):
            last = r["balance"]
            if last >= float(baseline) + float(min_increase):
                return {"ok": True, "funded": True, "baseline": float(baseline),
                        "balance": last, "received": round(last - float(baseline), 6)}
        time.sleep(interval_sec)
    return {"ok": True, "funded": False, "baseline": float(baseline),
            "balance": last,
            "note": "No arrival within timeout. Payment may still be processing "
                    "(KYC review / bank rails) — re-check later, do NOT assume failure."}
