"""
Jupiter native tools — callable by Starchild agent directly.
All HTTP via sc-proxy (proxied_get / proxied_post).
"""
from __future__ import annotations
import json

VERSION = "1.1.1"
BASE    = "https://lite-api.jup.ag"

KNOWN_TOKENS = {
    "SOL":  "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "JUP":  "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF":  "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "JTO":  "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
    "RNDR": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
    "RAY":  "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
}

# B2 fix: JTO decimals is 6, NOT 9 (verified on-chain)
DECIMALS = {
    "So11111111111111111111111111111111111111112":  9,   # SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 6,  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 6,  # USDT
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": 6,  # JUP
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": 5, # BONK
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": 6, # WIF
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": 6, # PYTH
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL":  6, # JTO — 6 NOT 9 (B2)
    "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof":  8, # RNDR
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R": 6, # RAY
}

# L1 fix: version-tagged caller ID for per-version usage tracking
CALLER = {"SC-CALLER-ID": f"skill:jupiter:{VERSION}"}

TIMEOUT = 15  # L3: explicit timeout for all HTTP calls


def _resolve(token: str) -> str:
    return KNOWN_TOKENS.get(token.upper(), token)


def _dec(mint: str) -> int:
    return DECIMALS.get(mint, 9)


def _fmt(raw_amount: str | int, mint: str) -> str:
    """M1 fix: always keep at least 2 decimal places."""
    val  = int(raw_amount) / (10 ** _dec(mint))
    s    = f"{val:,.6f}"
    # strip trailing zeros but keep minimum 2 decimal places
    int_part, dec_part = s.split(".")
    dec_part = dec_part.rstrip("0")
    if len(dec_part) < 2:
        dec_part = dec_part.ljust(2, "0")
    return f"{int_part}.{dec_part}"


def _fmt_order_amount(raw: str | int | None, mint: str) -> str:
    """M3 fix: API already returns human-readable strings for openOrders.
    If raw looks like a float string (contains '.'), return as-is.
    Only apply lamports conversion for raw integer lamport values.
    """
    if raw is None:
        return "?"
    s = str(raw)
    if "." in s:
        # already human-readable (e.g. "0.01")
        return s
    return _fmt(int(s), mint)


def _get(url, params=None):
    from core.http_client import proxied_get
    return proxied_get(url, params=params, headers=CALLER, timeout=TIMEOUT).json()


def _post(url, payload):
    from core.http_client import proxied_post
    return proxied_post(url, json=payload, headers=CALLER, timeout=TIMEOUT).json()


# ────────────────────────────────────────────────────────────────────────────
# Tool 1 — jupiter_price
# ────────────────────────────────────────────────────────────────────────────
def jupiter_price(token: str) -> dict:
    """
    Get USD price of a token via ultra/v1/order (tiny quote → USDC).

    Args:
        token: symbol (SOL, JUP, WIF, PYTH, JTO, RNDR, RAY…) or mint address

    Returns:
        {"token", "mint", "price_usd", "source"}
    """
    mint  = _resolve(token)
    usdc  = KNOWN_TOKENS["USDC"]
    one   = str(10 ** _dec(mint))
    data  = _get(f"{BASE}/ultra/v1/order", params={
        "inputMint":  mint,
        "outputMint": usdc,
        "amount":     one,
    })
    in_usd = data.get("inUsdValue")
    return {
        "token":     token.upper(),
        "mint":      mint,
        "price_usd": float(in_usd) if in_usd else None,
        "source":    "jupiter-ultra",
    }


# ────────────────────────────────────────────────────────────────────────────
# Tool 2 — jupiter_quote
# ────────────────────────────────────────────────────────────────────────────
def jupiter_quote(
    input_token: str,
    output_token: str,
    amount: float,
    taker: str = None,   # M2: optional taker pubkey to lock route
) -> dict:
    """
    Get a swap quote via ultra/v1/order.

    Args:
        input_token:  symbol or mint (e.g. "SOL")
        output_token: symbol or mint (e.g. "USDC")
        amount:       human-readable amount (e.g. 1.0 for 1 SOL)
        taker:        (optional) wallet pubkey — locks routing to this taker

    Returns dict with keys:
        in_amount, out_amount, in_usd, out_usd, price_impact_pct,
        transaction (base64), request_id
    """
    in_mint  = _resolve(input_token)
    out_mint = _resolve(output_token)
    lamports = str(int(amount * (10 ** _dec(in_mint))))

    params = {
        "inputMint":  in_mint,
        "outputMint": out_mint,
        "amount":     lamports,
    }
    if taker:
        params["taker"] = taker  # M2

    data = _get(f"{BASE}/ultra/v1/order", params=params)

    return {
        "in_token":         input_token.upper(),
        "out_token":        output_token.upper(),
        "in_amount":        _fmt(data.get("inAmount", lamports), in_mint),
        "out_amount":       _fmt(data.get("outAmount", "0"), out_mint),
        "in_usd":           data.get("inUsdValue"),
        "out_usd":          data.get("outUsdValue"),
        "price_impact_pct": data.get("priceImpactPct"),
        "transaction":      data.get("transaction"),   # base64 → wallet_sol_sign_transaction
        "request_id":       data.get("requestId"),
    }


# ────────────────────────────────────────────────────────────────────────────
# Tool 3 — jupiter_swap
# ────────────────────────────────────────────────────────────────────────────
def jupiter_swap(
    input_token: str,
    output_token: str,
    amount: float,
    wallet_pubkey: str,
    slippage_bps: int = None,  # L4: optional explicit slippage (default ultra auto = 50bps = 0.5%)
) -> dict:
    """
    Full swap pipeline: ultra quote → return tx for signing + execute.

    B3 fix: next_step now includes the exact execute payload structure
    so agent doesn't miss the POST /ultra/v1/execute step.

    Args:
        input_token:   symbol or mint
        output_token:  symbol or mint
        amount:        human-readable amount
        wallet_pubkey: user's Solana public key
        slippage_bps:  (optional) slippage in bps, e.g. 100 = 1%. Default: ultra auto (50bps)

    Returns quote dict + next_step with exact execute instructions.
    """
    quote = jupiter_quote(input_token, output_token, amount, taker=wallet_pubkey)
    quote["wallet"]    = wallet_pubkey
    quote["slippage"]  = f"{slippage_bps/100:.2f}%" if slippage_bps else "auto (~0.5%)"
    # B3 fix: explicit execute instructions with payload template
    quote["next_step"] = (
        "1. Call wallet_sol_sign_transaction(transaction=result['transaction'])\n"
        "2. POST https://lite-api.jup.ag/ultra/v1/execute\n"
        "   Body: {\"signedTransaction\": \"<signed_base64>\", \"requestId\": \""
        + (quote.get("request_id") or "<request_id>") + "\"}\n"
        "3. Call wallet_sol_balance() to verify balances changed."
    )
    return quote


# ────────────────────────────────────────────────────────────────────────────
# Tool 4 — jupiter_limit_create
# ────────────────────────────────────────────────────────────────────────────
def jupiter_limit_create(
    input_token: str,
    output_token: str,
    making_amount: float,
    taking_amount: float,
    maker: str,
    expired_at: str = None,
) -> dict:
    """
    Create a trigger/limit order on Jupiter.

    Args:
        input_token:   token you're selling (symbol or mint)
        output_token:  token you're buying  (symbol or mint)
        making_amount: human-readable sell amount (e.g. 10.0 USDC). Min ~$5 USD.
        taking_amount: human-readable buy amount  (e.g. 0.1 SOL)
        maker:         wallet public key
        expired_at:    ISO-8601 string, or None (no expiry)

    Returns:
        {"code", "request_id", "order_pubkey", "transaction" (base64), "next_step"}

    ⚠️  GOTCHAS (verified via live API):
        - makingAmount / takingAmount sent as STRINGS in lamports (int → ZodError)
        - expiredAt must be omitted entirely if not used (not null)
        - feeBps must be omitted entirely if not used (not 0)
        - Minimum order size ≈ $5 USD — smaller orders return error
    """
    in_mint  = _resolve(input_token)
    out_mint = _resolve(output_token)

    making_lam = str(int(making_amount * (10 ** _dec(in_mint))))
    taking_lam = str(int(taking_amount * (10 ** _dec(out_mint))))

    payload: dict = {
        "inputMint":  in_mint,
        "outputMint": out_mint,
        "maker":      maker,
        "payer":      maker,
        "params": {
            "makingAmount": making_lam,
            "takingAmount": taking_lam,
        },
        "computeUnitPrice": "auto",
    }
    if expired_at:
        payload["params"]["expiredAt"] = expired_at

    data  = _post(f"{BASE}/trigger/v1/createOrder", payload)
    # API returns "order" as a plain pubkey string, not a dict
    order = data.get("order")
    order_pubkey = order if isinstance(order, str) else (order or {}).get("orderKey") or (order or {}).get("publicKey")
    return {
        "code":         data.get("code"),
        "request_id":   data.get("requestId"),
        "order_pubkey": order_pubkey,
        "transaction":  data.get("transaction"),
        "next_step": (
            "1. Call wallet_sol_sign_transaction(transaction=result['transaction'])\n"
            "2. Broadcast signed tx\n"
            "3. Call jupiter_limit_orders(wallet) to confirm order appears."
        ),
    }


# ────────────────────────────────────────────────────────────────────────────
# Tool 5 — jupiter_limit_orders
# ────────────────────────────────────────────────────────────────────────────
def jupiter_limit_orders(wallet: str, history: bool = False) -> dict:
    """
    List open (or historical) trigger orders for a wallet.

    Args:
        wallet:  Solana wallet public key
        history: if True, query orderHistory instead of openOrders

    Returns:
        {"wallet", "count", "orders": [...]} — amounts in human-readable form (M3)
    """
    endpoint = "orderHistory" if history else "openOrders"
    data     = _get(f"{BASE}/trigger/v1/{endpoint}", params={"wallet": wallet})
    orders   = data if isinstance(data, list) else data.get("orders", [])
    result   = []
    for o in orders:
        in_mint  = o.get("inputMint", "")
        out_mint = o.get("outputMint", "")
        result.append({
            "pubkey":        o.get("publicKey"),
            "input_mint":    in_mint,
            "output_mint":   out_mint,
            # M3 fix: convert raw lamports to human-readable
            "making_amount": _fmt_order_amount(o.get("makingAmount"), in_mint),
            "taking_amount": _fmt_order_amount(o.get("takingAmount"), out_mint),
            "filled_making": _fmt_order_amount(o.get("filledMakingAmount"), in_mint),
            "filled_taking": _fmt_order_amount(o.get("filledTakingAmount"), out_mint),
            "status":        o.get("status"),
        })
    return {"wallet": wallet, "count": len(result), "orders": result}


# ────────────────────────────────────────────────────────────────────────────
# Tool 6 — jupiter_limit_cancel
# ────────────────────────────────────────────────────────────────────────────
def jupiter_limit_cancel(order_pubkey: str, maker: str) -> dict:
    """
    Cancel an open trigger/limit order.

    Args:
        order_pubkey: the order's public key (from jupiter_limit_orders)
        maker:        wallet public key

    Returns:
        {"code", "request_id", "transaction" (base64), "next_step"}
    """
    data = _post(f"{BASE}/trigger/v1/cancelOrder", {
        "order":            order_pubkey,
        "maker":            maker,
        "computeUnitPrice": "auto",
    })
    return {
        "code":        data.get("code"),
        "request_id":  data.get("requestId"),
        "transaction": data.get("transaction"),
        "next_step":   "Sign with wallet_sol_sign_transaction(tx), then broadcast.",
    }


# ── Tool registry ─────────────────────────────────────────────────────────────
TOOLS = [
    jupiter_price,
    jupiter_quote,
    jupiter_swap,
    jupiter_limit_create,
    jupiter_limit_orders,
    jupiter_limit_cancel,
]
