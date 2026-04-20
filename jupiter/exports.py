"""
Jupiter native tools — callable by Starchild agent directly.
All HTTP via sc-proxy (proxied_get / proxied_post).

VERIFIED LIVE (2026-04-20):
- Swap: ultra/v1/order (with taker) → sign → ultra/v1/execute → ✅
- Limit: trigger/v1/createOrder → sign → Solana RPC sendTransaction → ✅
- Gas: always paid from wallet SOL balance (no gas sponsorship on Solana)
- Limit order broadcast uses raw Solana RPC, NOT Jupiter /execute
- blockhash expires in ~90s — sign and broadcast immediately
- openOrders returns orderKey (not publicKey) as the order pubkey
- makingAmount / takingAmount in openOrders are already human-readable floats
- Min limit order size: ~$5 USD
- Keepers may fill a limit order immediately if implied price ≤ market
"""
from __future__ import annotations
import json

VERSION = "1.2.0"
BASE    = "https://lite-api.jup.ag"
SOL_RPC = "https://api.mainnet-beta.solana.com"

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
    "So11111111111111111111111111111111111111112":  9,   # SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 6,  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 6,  # USDT
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": 6,  # JUP
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": 5, # BONK
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": 6, # WIF
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": 6, # PYTH
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL":  6, # JTO (NOT 9)
    "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof":  8, # RNDR
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R": 6, # RAY
}

CALLER  = {"SC-CALLER-ID": f"skill:jupiter:{VERSION}"}
TIMEOUT = 15


def _resolve(token: str) -> str:
    return KNOWN_TOKENS.get(token.upper(), token)

def _dec(mint: str) -> int:
    return DECIMALS.get(mint, 9)

def _fmt(raw_amount: str | int, mint: str) -> str:
    """Convert lamports → human-readable, min 2 decimal places."""
    val      = int(raw_amount) / (10 ** _dec(mint))
    s        = f"{val:,.6f}"
    int_part, dec_part = s.split(".")
    dec_part = dec_part.rstrip("0").ljust(2, "0")
    return f"{int_part}.{dec_part}"

def _get(url, params=None):
    from core.http_client import proxied_get
    return proxied_get(url, params=params, headers=CALLER, timeout=TIMEOUT).json()

def _post(url, payload, timeout=TIMEOUT):
    from core.http_client import proxied_post
    return proxied_post(url, json=payload, headers=CALLER, timeout=timeout).json()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 — jupiter_price
# ─────────────────────────────────────────────────────────────────────────────
def jupiter_price(token: str) -> dict:
    """
    Get USD price of a Solana token (uses ultra/v1/order with 1-unit quote → USDC).

    Args:
        token: symbol (SOL, JUP, WIF…) or mint address

    Returns:
        {"token", "mint", "price_usd", "source"}
    """
    mint = _resolve(token)
    usdc = KNOWN_TOKENS["USDC"]
    one  = str(10 ** _dec(mint))
    data = _get(f"{BASE}/ultra/v1/order", params={
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


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 — jupiter_execute_swap   ← HIGH-LEVEL: replaces manual /execute call
# ─────────────────────────────────────────────────────────────────────────────
def jupiter_execute_swap(
    signed_transaction: str,
    request_id:         str,
    in_mint:            str = None,
    out_mint:           str = None,
) -> dict:
    """
    Broadcast a signed Jupiter Ultra swap to the network.

    Call this AFTER wallet_sol_sign_transaction(). Returns on-chain result with
    human-readable amounts when in_mint/out_mint are provided.
    Gas (SOL) is paid from the wallet balance — no gas sponsorship on Solana.

    Args:
        signed_transaction: base64 signed tx from wallet_sol_sign_transaction()
        request_id:         requestId from jupiter_swap()
        in_mint:            (optional) pass result["in_mint"] from jupiter_swap() for fmt
        out_mint:           (optional) pass result["out_mint"] from jupiter_swap() for fmt

    Returns:
        {"status", "signature", "slot", "in_amount_fmt", "out_amount_fmt", "error"}
        status == "Success" means the swap landed on-chain.
    """
    data    = _post(
        f"{BASE}/ultra/v1/execute",
        {"signedTransaction": signed_transaction, "requestId": request_id},
        timeout=30,
    )
    raw_in  = data.get("inputAmountResult")
    raw_out = data.get("outputAmountResult")
    return {
        "status":         data.get("status"),
        "signature":      data.get("signature"),
        "slot":           data.get("slot"),
        "in_amount_fmt":  _fmt(raw_in,  in_mint)  if (raw_in  and in_mint)  else raw_in,
        "out_amount_fmt": _fmt(raw_out, out_mint) if (raw_out and out_mint) else raw_out,
        "error":          data.get("error"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3 — jupiter_broadcast_tx   ← HIGH-LEVEL: broadcast via Solana RPC
# ─────────────────────────────────────────────────────────────────────────────
def jupiter_broadcast_tx(signed_transaction: str) -> dict:
    """
    Broadcast a signed Solana transaction via the mainnet RPC.

    Use this for LIMIT ORDERS (trigger API). Do NOT use jupiter_execute_swap
    for limit orders — /ultra/v1/execute only works for Ultra swaps.

    Gas (SOL) is paid from the wallet balance — no gas sponsorship on Solana.

    Args:
        signed_transaction: base64 signed tx from wallet_sol_sign_transaction()

    Returns:
        {"success", "signature", "error"}
        success=True means the tx was accepted by the network (not yet confirmed).
    """
    data = _post(SOL_RPC, {
        "jsonrpc": "2.0",
        "id":      1,
        "method":  "sendTransaction",
        "params":  [
            signed_transaction,
            {"encoding": "base64", "skipPreflight": False, "preflightCommitment": "confirmed"},
        ],
    }, timeout=30)

    if "result" in data:
        return {"success": True, "signature": data["result"], "error": None}
    err = data.get("error", {})
    return {"success": False, "signature": None, "error": err.get("message", str(err))}


# ─────────────────────────────────────────────────────────────────────────────
# Tool 4 — jupiter_swap  (unified: quote + taker, returns tx ready to sign)
# ─────────────────────────────────────────────────────────────────────────────
def jupiter_swap(
    input_token:   str,
    output_token:  str,
    amount:        float,
    wallet_pubkey: str = None,
) -> dict:
    """
    Get a swap quote, and optionally prepare a signable transaction.

    - wallet_pubkey omitted: returns quote only (price info, no transaction).
      Use this when the user just wants to check rates without committing.
    - wallet_pubkey provided: returns quote + transaction ready to sign and execute.

    Workflow when wallet_pubkey is provided:
        1. Show user: in_amount, out_amount, in_usd, out_usd, price_impact_pct
        2. Wait for user confirmation
        3. signed = wallet_sol_sign_transaction(result["transaction"])
        4. jupiter_execute_swap(signed["signed_transaction"], result["request_id"],
                                in_mint=result["in_mint"], out_mint=result["out_mint"])
        5. wallet_sol_balance() to verify

    Gas is paid from wallet SOL balance (no sponsorship on Solana).

    Args:
        input_token:   symbol (SOL/USDC/JUP...) or full mint address
        output_token:  symbol or mint
        amount:        human-readable sell amount (e.g. 0.01 for 0.01 SOL)
        wallet_pubkey: (optional) Solana wallet public key.
                       Required to get a signable transaction.
                       Omit for quote-only (price check, no tx).

    Returns:
        {in_token, out_token, in_mint, out_mint,
         in_amount, out_amount, in_usd, out_usd, price_impact_pct,
         transaction (base64 or None), request_id,
         quote_only (True if wallet_pubkey was omitted)}
    """
    in_mint  = _resolve(input_token)
    out_mint = _resolve(output_token)
    lamports = str(int(amount * (10 ** _dec(in_mint))))

    params = {"inputMint": in_mint, "outputMint": out_mint, "amount": lamports}
    if wallet_pubkey:
        params["taker"] = wallet_pubkey

    data = _get(f"{BASE}/ultra/v1/order", params=params)
    return {
        "in_token":         input_token.upper(),
        "out_token":        output_token.upper(),
        "in_mint":          in_mint,
        "out_mint":         out_mint,
        "in_amount":        _fmt(data.get("inAmount", lamports), in_mint),
        "out_amount":       _fmt(data.get("outAmount", "0"), out_mint),
        "in_usd":           data.get("inUsdValue"),
        "out_usd":          data.get("outUsdValue"),
        "price_impact_pct": data.get("priceImpactPct"),
        "transaction":      data.get("transaction"),   # None if wallet_pubkey omitted
        "request_id":       data.get("requestId"),
        "quote_only":       wallet_pubkey is None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 5 — jupiter_limit_create
# ─────────────────────────────────────────────────────────────────────────────
def jupiter_limit_create(
    input_token:   str,
    output_token:  str,
    making_amount: float,
    taking_amount: float,
    maker:         str,
    expired_at:    str = None,
) -> dict:
    """
    Create a Jupiter trigger/limit order.

    Workflow after this call:
        1. signed = wallet_sol_sign_transaction(result["transaction"])
        2. jupiter_broadcast_tx(signed["signed_transaction"])   ← Solana RPC, NOT /execute
        3. jupiter_limit_orders(maker) to confirm it appears

    Gas is paid from wallet SOL balance (no sponsorship on Solana).
    IMPORTANT: sign and broadcast immediately — blockhash expires in ~90s.

    Args:
        input_token:   token you're selling (symbol or mint)
        output_token:  token you're buying  (symbol or mint)
        making_amount: human-readable sell amount. Min ~$5 USD.
        taking_amount: human-readable buy amount (sets your target price)
        maker:         wallet public key
        expired_at:    ISO-8601 expiry string, or None (no expiry)

    Returns:
        {"code", "order_pubkey", "transaction" (base64), "implied_price", "next_step"}

    Verified gotchas:
        - makingAmount/takingAmount sent as STRING lamports (int → ZodError 400)
        - expiredAt must be omitted entirely if not used (NOT null)
        - feeBps must be omitted entirely if not used (NOT 0)
        - Minimum order size ≈ $5 USD
        - Keepers fill instantly if implied price ≤ market price
        - Broadcast via Solana RPC sendTransaction, NOT /ultra/v1/execute
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

    # API returns order pubkey as "order" (plain string), not nested
    order_pubkey = data.get("order")
    if isinstance(order_pubkey, dict):
        order_pubkey = order_pubkey.get("orderKey") or order_pubkey.get("publicKey")

    # Compute implied price for display
    try:
        implied = making_amount / taking_amount
        implied_price = f"1 {output_token.upper()} = {implied:.4f} {input_token.upper()}"
    except Exception:
        implied_price = "n/a"

    if data.get("code", -1) != 0 and not data.get("transaction"):
        return {"error": data.get("error", str(data)), "code": data.get("code")}

    return {
        "code":          data.get("code"),
        "order_pubkey":  order_pubkey,
        "transaction":   data.get("transaction"),
        "implied_price": implied_price,
        "next_step": (
            "1. signed = wallet_sol_sign_transaction(result['transaction'])\n"
            "2. jupiter_broadcast_tx(signed['signed_transaction'])  # Solana RPC — NOT /execute\n"
            "3. jupiter_limit_orders(maker) to confirm order appears\n"
            "⚠️  Sign and broadcast within ~90s — blockhash expires."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 6 — jupiter_limit_orders
# ─────────────────────────────────────────────────────────────────────────────
def jupiter_limit_orders(wallet: str, history: bool = False) -> dict:
    """
    List open (or historical) trigger orders for a wallet.

    Args:
        wallet:  Solana wallet public key
        history: if True, query orderHistory instead of openOrders

    Returns:
        {"wallet", "count", "orders": [...]}
        Each order includes order_pubkey (needed to cancel), amounts, status.

    Note: openOrders amounts (makingAmount, takingAmount) are returned by the
    API as human-readable floats (e.g. "0.06"), not raw lamports.
    """
    endpoint = "orderHistory" if history else "openOrders"
    data     = _get(f"{BASE}/trigger/v1/{endpoint}", params={"wallet": wallet})
    orders   = data if isinstance(data, list) else data.get("orders", [])
    result   = []
    for o in orders:
        # API verified: open orders use "orderKey", history uses "orderKey" too
        pubkey = o.get("orderKey") or o.get("publicKey")
        result.append({
            "order_pubkey":    pubkey,
            "input_mint":      o.get("inputMint"),
            "output_mint":     o.get("outputMint"),
            "making_amount":   o.get("makingAmount"),    # already human-readable
            "taking_amount":   o.get("takingAmount"),    # already human-readable
            "remaining_making": o.get("remainingMakingAmount"),
            "remaining_taking": o.get("remainingTakingAmount"),
            "status":          o.get("status"),
            "created_at":      o.get("createdAt"),
            "open_tx":         o.get("openTx"),
            "close_tx":        o.get("closeTx"),
        })
    return {"wallet": wallet, "count": len(result), "orders": result}


# ─────────────────────────────────────────────────────────────────────────────
# Tool 7 — jupiter_limit_cancel
# ─────────────────────────────────────────────────────────────────────────────
def jupiter_limit_cancel(order_pubkey: str, maker: str) -> dict:
    """
    Cancel an open Jupiter trigger/limit order.

    Workflow after this call:
        1. signed = wallet_sol_sign_transaction(result["transaction"])
        2. jupiter_broadcast_tx(signed["signed_transaction"])   ← Solana RPC

    Args:
        order_pubkey: order's pubkey from jupiter_limit_orders() → order["order_pubkey"]
        maker:        wallet public key

    Returns:
        {"code", "transaction" (base64), "next_step"}
    """
    data = _post(f"{BASE}/trigger/v1/cancelOrder", {
        "order":            order_pubkey,
        "maker":            maker,
        "computeUnitPrice": "auto",
    })
    return {
        "code":        data.get("code"),
        "transaction": data.get("transaction"),
        "next_step": (
            "1. signed = wallet_sol_sign_transaction(result['transaction'])\n"
            "2. jupiter_broadcast_tx(signed['signed_transaction'])  # Solana RPC"
        ),
    }


# ── Tool registry ─────────────────────────────────────────────────────────────
TOOLS = [
    jupiter_price,
    jupiter_swap,
    jupiter_execute_swap,
    jupiter_broadcast_tx,
    jupiter_limit_create,
    jupiter_limit_orders,
    jupiter_limit_cancel,
]
