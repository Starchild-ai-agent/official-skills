"""
Jupiter operations — quote, swap (ultra), limit orders on Solana.
Usage: python scripts/jupiter_ops.py <action> [args]
Actions:
  quote <input> <output> <amount_lamports>   — Ultra quote (price + USD value)
  swap  <input> <output> <amount> <pubkey>   — Ultra order tx (quote+tx in one call)
  limit <input> <output> <making> <taking> <maker>  — Create limit/trigger order
  orders <wallet>                            — List open trigger orders
  cancel <order_pubkey> <maker>              — Cancel a trigger order
  tokens [query]                             — Show known token mints
"""
import sys
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
    "So11111111111111111111111111111111111111112":  9,   # SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 6,  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 6,  # USDT
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": 6,  # JUP
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": 5, # BONK
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": 6, # WIF
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": 6, # PYTH
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL":  9, # JTO
    "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof":  8, # RNDR
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R": 6, # RAY
}


def resolve_mint(token: str) -> str:
    upper = token.upper()
    return KNOWN_TOKENS.get(upper, token)


def fmt(raw: str, mint: str) -> str:
    dec = DECIMALS.get(mint, 9)
    val = int(raw) / (10 ** dec)
    return f"{val:,.6f}".rstrip("0").rstrip(".")


# ── sc-proxy aware HTTP ──────────────────────────────────────────────────────
try:
    from core.http_client import proxied_get, proxied_post
    CALLER = {"SC-CALLER-ID": "skill:jupiter"}

    def _get(url, params=None):
        return proxied_get(url, params=params, headers=CALLER).json()

    def _post(url, payload):
        return proxied_post(url, json=payload, headers=CALLER).json()

except ImportError:
    # local dev fallback
    import requests

    def _get(url, params=None):
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def _post(url, payload):
        r = requests.post(url, json=payload, timeout=20)
        r.raise_for_status()
        return r.json()


# ── Actions ──────────────────────────────────────────────────────────────────

def ultra_quote(input_mint: str, output_mint: str, amount: str):
    """Ultra /order — returns quote + transaction + USD values in one call."""
    data = _get(f"{BASE}/ultra/v1/order", params={
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
    })
    in_amt  = fmt(data.get("inAmount",  amount), input_mint)
    out_amt = fmt(data.get("outAmount", "0"),    output_mint)
    in_usd  = data.get("inUsdValue",  "N/A")
    out_usd = data.get("outUsdValue", "N/A")
    impact  = data.get("priceImpactPct", "N/A")
    request_id = data.get("requestId", "")

    print("Ultra Quote:")
    print(f"  In:         {in_amt}  (~${in_usd})")
    print(f"  Out:        {out_amt} (~${out_usd})")
    print(f"  Price Impact: {impact}%")
    print(f"  Request ID: {request_id}")
    print()
    print("TRANSACTION_BASE64:")
    print(data.get("transaction", ""))
    print(f"REQUEST_ID:{request_id}")
    return data


def ultra_execute(signed_tx: str, request_id: str):
    """Execute a signed ultra transaction."""
    data = _post(f"{BASE}/ultra/v1/execute", {
        "signedTransaction": signed_tx,
        "requestId": request_id,
    })
    print(json.dumps(data, indent=2))
    return data


def create_limit_order(input_mint: str, output_mint: str,
                       making_amount: str, taking_amount: str,
                       maker: str, expired_at: str = None):
    """Create a trigger/limit order. Amounts MUST be strings."""
    payload = {
        "inputMint":  input_mint,
        "outputMint": output_mint,
        "maker":      maker,
        "payer":      maker,
        "params": {
            "makingAmount": str(making_amount),   # MUST be string
            "takingAmount": str(taking_amount),   # MUST be string
        },
        "computeUnitPrice": "auto",
    }
    # expiredAt: omit entirely if not set (do NOT pass null)
    if expired_at:
        payload["params"]["expiredAt"] = expired_at

    data = _post(f"{BASE}/trigger/v1/createOrder", payload)
    print("Limit Order Created:")
    print(f"  Code:       {data.get('code')}")
    print(f"  Request ID: {data.get('requestId')}")
    order = data.get("order", {})
    print(f"  Order:      {order.get('publicKey', 'N/A')}")
    print()
    print("TRANSACTION_BASE64:")
    print(data.get("transaction", ""))
    print(f"REQUEST_ID:{data.get('requestId', '')}")
    return data


def list_open_orders(wallet: str):
    """List open trigger orders for a wallet."""
    data = _get(f"{BASE}/trigger/v1/openOrders", params={"wallet": wallet})
    orders = data if isinstance(data, list) else data.get("orders", [])
    print(f"Open orders for {wallet[:8]}...:")
    if not orders:
        print("  (none)")
    for o in orders:
        pub  = o.get("publicKey", "N/A")
        in_m = o.get("inputMint", "")[:8]
        out_m= o.get("outputMint", "")[:8]
        mk   = o.get("makingAmount", "?")
        tk   = o.get("takingAmount", "?")
        print(f"  {pub} | {in_m}→{out_m} | making={mk} taking={tk}")
    return data


def cancel_order(order_pubkey: str, maker: str):
    """Cancel a trigger order."""
    data = _post(f"{BASE}/trigger/v1/cancelOrder", {
        "order": order_pubkey,
        "maker": maker,
        "computeUnitPrice": "auto",
    })
    print("Cancel Order:")
    print(json.dumps(data, indent=2))
    return data


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    try:
        if action == "quote":
            if len(sys.argv) < 5:
                print("Usage: quote <input> <output> <amount_lamports>")
                sys.exit(1)
            ultra_quote(resolve_mint(sys.argv[2]),
                        resolve_mint(sys.argv[3]),
                        sys.argv[4])

        elif action == "swap":
            # Returns the tx — agent will sign via wallet_sol_sign_transaction
            if len(sys.argv) < 5:
                print("Usage: swap <input> <output> <amount> <pubkey>")
                sys.exit(1)
            ultra_quote(resolve_mint(sys.argv[2]),
                        resolve_mint(sys.argv[3]),
                        sys.argv[4])

        elif action == "limit":
            if len(sys.argv) < 7:
                print("Usage: limit <input> <output> <making> <taking> <maker>")
                sys.exit(1)
            expired = sys.argv[7] if len(sys.argv) > 7 else None
            create_limit_order(
                resolve_mint(sys.argv[2]),
                resolve_mint(sys.argv[3]),
                sys.argv[4], sys.argv[5], sys.argv[6],
                expired_at=expired,
            )

        elif action == "orders":
            if len(sys.argv) < 3:
                print("Usage: orders <wallet>")
                sys.exit(1)
            list_open_orders(sys.argv[2])

        elif action == "cancel":
            if len(sys.argv) < 4:
                print("Usage: cancel <order_pubkey> <maker>")
                sys.exit(1)
            cancel_order(sys.argv[2], sys.argv[3])

        elif action == "tokens":
            query = sys.argv[2].upper() if len(sys.argv) > 2 else None
            print("Known tokens:")
            for sym, addr in KNOWN_TOKENS.items():
                if query is None or query in sym:
                    print(f"  {sym}: {addr}")

        else:
            print(f"Unknown action: {action}")
            sys.exit(1)

    except (ValueError, RuntimeError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
