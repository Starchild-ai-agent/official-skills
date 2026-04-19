"""
Jupiter native tools — callable by Starchild agent directly.
All HTTP via sc-proxy (proxied_get / proxied_post).
"""
from __future__ import annotations
import json

BASE = "https://lite-api.jup.ag"

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

DECIMALS = {
    "So11111111111111111111111111111111111111112":  9,
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 6,
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 6,
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": 6,
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": 5,
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": 6,
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": 6,
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL":  9,
    "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof":  8,
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R": 6,
}

CALLER = {"SC-CALLER-ID": "skill:jupiter"}


def _resolve(token: str) -> str:
    return KNOWN_TOKENS.get(token.upper(), token)


def _dec(mint: str) -> int:
    return DECIMALS.get(mint, 9)


def _fmt(raw_amount: str | int, mint: str) -> str:
    val = int(raw_amount) / (10 ** _dec(mint))
    return f"{val:,.6f}".rstrip("0").rstrip(".")


def _get(url, params=None):
    from core.http_client import proxied_get
    return proxied_get(url, params=params, headers=CALLER).json()


def _post(url, payload):
    from core.http_client import proxied_post
    return proxied_post(url, json=payload, headers=CALLER).json()


# ────────────────────────────────────────────────────────────────────────────
# Tool 1 — jupiter_price
# ────────────────────────────────────────────────────────────────────────────
def jupiter_price(token: str) -> dict:
    """
    Get USD price of a token by requesting a tiny swap quote to USDC via
    ultra/v1/order, then deriving price from inUsdValue/outUsdValue.

    Args:
        token: symbol (SOL, JUP, WIF…) or mint address

    Returns:
        {"token": str, "mint": str, "price_usd": float, "source": "jupiter-ultra"}
    """
    mint = _resolve(token)
    usdc = KNOWN_TOKENS["USDC"]
    # 1 unit in smallest denomination
    one_unit = str(10 ** _dec(mint))
    data = _get(f"{BASE}/ultra/v1/order", params={
        "inputMint":  mint,
        "outputMint": usdc,
        "amount":     one_unit,
    })
    in_usd = data.get("inUsdValue")
    price  = float(in_usd) if in_usd else None
    return {
        "token":     token.upper(),
        "mint":      mint,
        "price_usd": price,
        "source":    "jupiter-ultra",
    }


# ────────────────────────────────────────────────────────────────────────────
# Tool 2 — jupiter_quote
# ────────────────────────────────────────────────────────────────────────────
def jupiter_quote(
    input_token: str,
    output_token: str,
    amount: float,
) -> dict:
    """
    Get a swap quote via ultra/v1/order (includes USD values, no API key needed).

    Args:
        input_token:  symbol or mint (e.g. "SOL", "USDC")
        output_token: symbol or mint (e.g. "USDC", "JUP")
        amount:       human-readable amount (e.g. 1.0 for 1 SOL)

    Returns dict with keys:
        in_amount, out_amount, in_usd, out_usd, price_impact_pct,
        transaction (base64), request_id
    """
    in_mint  = _resolve(input_token)
    out_mint = _resolve(output_token)
    lamports = str(int(amount * (10 ** _dec(in_mint))))

    data = _get(f"{BASE}/ultra/v1/order", params={
        "inputMint":  in_mint,
        "outputMint": out_mint,
        "amount":     lamports,
    })

    return {
        "in_token":        input_token.upper(),
        "out_token":       output_token.upper(),
        "in_amount":       _fmt(data.get("inAmount", lamports), in_mint),
        "out_amount":      _fmt(data.get("outAmount", "0"), out_mint),
        "in_usd":          data.get("inUsdValue"),
        "out_usd":         data.get("outUsdValue"),
        "price_impact_pct": data.get("priceImpactPct"),
        "transaction":     data.get("transaction"),   # base64 — pass to wallet_sol_sign_transaction
        "request_id":      data.get("requestId"),
    }


# ────────────────────────────────────────────────────────────────────────────
# Tool 3 — jupiter_swap
# ────────────────────────────────────────────────────────────────────────────
def jupiter_swap(
    input_token: str,
    output_token: str,
    amount: float,
    wallet_pubkey: str,
) -> dict:
    """
    Full swap pipeline: ultra quote → return tx for signing.
    Agent MUST follow up with wallet_sol_sign_transaction(tx) then
    POST /ultra/v1/execute with signed tx + request_id.

    Args:
        input_token:   symbol or mint
        output_token:  symbol or mint
        amount:        human-readable amount
        wallet_pubkey: user's Solana public key

    Returns same as jupiter_quote plus next_step instructions.
    """
    quote = jupiter_quote(input_token, output_token, amount)
    quote["wallet"]    = wallet_pubkey
    quote["next_step"] = (
        "Call wallet_sol_sign_transaction(transaction=quote['transaction']), "
        "then POST /ultra/v1/execute with {signedTransaction, requestId}."
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
        making_amount: human-readable sell amount (e.g. 10.0 USDC)
        taking_amount: human-readable buy amount  (e.g. 0.1 SOL)
        maker:         wallet public key
        expired_at:    ISO-8601 string, or None (no expiry)

    Returns:
        {"code", "request_id", "order_pubkey", "transaction" (base64)}

    ⚠️  GOTCHAS (verified via live API):
        - makingAmount / takingAmount are sent as STRINGS in lamports
        - expiredAt must be omitted entirely if not used (not null)
        - feeBps must be omitted if not used (not 0)
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

    data = _post(f"{BASE}/trigger/v1/createOrder", payload)
    order = data.get("order", {})
    return {
        "code":        data.get("code"),
        "request_id":  data.get("requestId"),
        "order_pubkey": order.get("publicKey"),
        "transaction": data.get("transaction"),   # base64 — sign then broadcast
        "next_step":   "Sign with wallet_sol_sign_transaction(tx), then broadcast.",
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
        {"wallet", "count", "orders": [...]}
    """
    endpoint = "orderHistory" if history else "openOrders"
    data = _get(f"{BASE}/trigger/v1/{endpoint}", params={"wallet": wallet})
    orders = data if isinstance(data, list) else data.get("orders", [])
    result = []
    for o in orders:
        result.append({
            "pubkey":        o.get("publicKey"),
            "input_mint":    o.get("inputMint"),
            "output_mint":   o.get("outputMint"),
            "making_amount": o.get("makingAmount"),
            "taking_amount": o.get("takingAmount"),
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
        {"code", "request_id", "transaction" (base64)}
    """
    data = _post(f"{BASE}/trigger/v1/cancelOrder", {
        "order":            order_pubkey,
        "maker":            maker,
        "computeUnitPrice": "auto",
    })
    return {
        "code":       data.get("code"),
        "request_id": data.get("requestId"),
        "transaction": data.get("transaction"),
        "next_step":  "Sign with wallet_sol_sign_transaction(tx), then broadcast.",
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
