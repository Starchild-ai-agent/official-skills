"""
Jupiter operations — quote and build swap transactions on Solana.
Usage: python scripts/jupiter_ops.py <action> [args]
Actions:
  quote <input_mint> <output_mint> <amount_lamports> [slippage_bps] — Get swap quote
  swap <input_mint> <output_mint> <amount_lamports> <user_pubkey> [slippage_bps]
  tokens [query]                                                    — Search token mints
"""
import sys
import json
import requests

BASE = "https://lite-api.jup.ag"

KNOWN_TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "JTO": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
    "RNDR": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
}

DECIMALS = {
    "So11111111111111111111111111111111111111112": 9,   # SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 6,  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 6,  # USDT
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": 6,  # JUP
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": 5,  # BONK
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": 6,  # WIF
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": 6,  # PYTH
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL": 9,   # JTO
    "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof": 8,   # RNDR
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R": 6,  # RAY
}


def resolve_mint(token: str) -> str:
    """Resolve symbol or address to mint address."""
    upper = token.upper()
    if upper in KNOWN_TOKENS:
        return KNOWN_TOKENS[upper]
    return token  # assume it's already a mint address


def format_amount(raw: str, mint: str) -> str:
    decimals = DECIMALS.get(mint, 9)
    val = int(raw) / (10 ** decimals)
    return f"{val:,.6f}".rstrip('0').rstrip('.')


def get_quote(input_mint: str, output_mint: str, amount: str,
              slippage_bps: int = 50):
    """Get a swap quote from Jupiter."""
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
        "slippageBps": slippage_bps,
        "restrictIntermediateTokens": "true",
    }
    try:
        resp = requests.get(
            f"{BASE}/swap/v1/quote", params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Jupiter quote error: {e}") from e
    quote = resp.json()
    in_amt = format_amount(quote.get("inAmount", amount), input_mint)
    out_amt = format_amount(quote.get("outAmount", "0"), output_mint)
    impact = quote.get("priceImpactPct", "N/A")
    routes = quote.get("routePlan", [])
    print("Quote:")
    print(f"  In:  {in_amt} ({input_mint[:8]}...)")
    print(f"  Out: {out_amt} ({output_mint[:8]}...)")
    print(f"  Price Impact: {impact}%")
    print(f"  Route Steps: {len(routes)}")
    for i, r in enumerate(routes):
        swap_info = r.get("swapInfo", {})
        label = swap_info.get("label", "Unknown")
        pct = r.get("percent", 100)
        print(f"    Step {i+1}: {label} ({pct}%)")
    print()
    return quote


def build_swap(input_mint: str, output_mint: str, amount: str,
               user_pubkey: str, slippage_bps: int = 50):
    """Get quote then build a swap transaction."""
    quote = get_quote(input_mint, output_mint, amount, slippage_bps)
    payload = {
        "quoteResponse": quote,
        "userPublicKey": user_pubkey,
        "dynamicComputeUnitLimit": True,
        "dynamicSlippage": True,
        "prioritizationFeeLamports": {
            "priorityLevelWithMaxLamports": {
                "maxLamports": 1000000,
                "priorityLevel": "medium",
            }
        },
    }
    try:
        resp = requests.post(
            f"{BASE}/swap/v1/swap", json=payload, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Jupiter swap error: {e}") from e
    result = resp.json()
    swap_tx = result.get("swapTransaction", "")
    if swap_tx:
        print("Swap Transaction (base64):")
        print(f"  {swap_tx[:80]}...")
        print(f"  Length: {len(swap_tx)} chars")
        print()
        print("To execute, call:")
        print(f'  wallet_sol_transfer(transaction="{swap_tx[:40]}...")')
    else:
        print("Error: No swap transaction returned")
        print(json.dumps(result, indent=2))
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    try:
        if action == "quote":
            if len(sys.argv) < 5:
                print("Usage: quote <input> <output>"
                      " <amount_lamports> [slippage_bps]")
                sys.exit(1)
            in_mint = resolve_mint(sys.argv[2])
            out_mint = resolve_mint(sys.argv[3])
            amount = sys.argv[4]
            slippage = int(sys.argv[5]) if len(sys.argv) > 5 else 50
            get_quote(in_mint, out_mint, amount, slippage)
        elif action == "swap":
            if len(sys.argv) < 6:
                print("Usage: swap <input> <output>"
                      " <amount> <pubkey> [slippage_bps]")
                sys.exit(1)
            in_mint = resolve_mint(sys.argv[2])
            out_mint = resolve_mint(sys.argv[3])
            amount = sys.argv[4]
            pubkey = sys.argv[5]
            slippage = int(sys.argv[6]) if len(sys.argv) > 6 else 50
            build_swap(in_mint, out_mint, amount, pubkey, slippage)
        elif action == "tokens":
            query = sys.argv[2] if len(sys.argv) > 2 else None
            print("Known tokens:")
            for sym, addr in KNOWN_TOKENS.items():
                if query is None or query.upper() in sym:
                    print(f"  {sym}: {addr}")
        else:
            print(f"Unknown action: {action}")
            print(__doc__)
            sys.exit(1)

    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
