"""
Pendle operations — discover markets, get quotes, build swap/LP transactions.
Usage: python scripts/pendle_ops.py <action> [args]
Actions:
  markets [chain_id]                           — List top markets by TVL
  convert <chain_id> <token_in> <token_out> <amount_wei> <receiver> [slippage]
"""
import sys
import json
import requests

BASE = "https://api-v2.pendle.finance/core"
DEFAULT_SLIPPAGE = 0.01  # 1%

# Pendle API rejects ETH sentinel — auto-replace with WETH
ETH_SENTINEL = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
WETH = {
    1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",      # Ethereum
    42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # Arbitrum
    8453: "0x4200000000000000000000000000000000000006",     # Base
    10: "0x4200000000000000000000000000000000000006",       # Optimism
}


def list_markets(chain_id: int = 1, limit: int = 10):
    url = f"{BASE}/v1/{chain_id}/markets"
    params = {"limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Pendle API error: {e}") from e
    data = resp.json()
    markets = data.get("results", data) if isinstance(data, dict) else data
    if isinstance(markets, dict):
        markets = markets.get("results", [markets])
    for m in (markets if isinstance(markets, list) else []):
        name = m.get("name", m.get("proName", "Unknown"))
        tvl = float(m.get("tvl", m.get("liquidity", {}).get("usd", 0)))
        implied_apy = float(m.get("impliedApy", m.get("aggregatedApy", 0))) * 100
        expiry = m.get("expiry", "N/A")
        pt = m.get("pt") or {}
        yt = m.get("yt") or {}
        pt_addr = pt.get("address", "N/A") if isinstance(pt, dict) else pt
        yt_addr = yt.get("address", "N/A") if isinstance(yt, dict) else yt
        market_addr = m.get("address", "N/A")
        print(f"  {name}")
        print(f"    Market: {market_addr}")
        print(f"    PT: {pt_addr}")
        print(f"    YT: {yt_addr}")
        print(f"    TVL: ${tvl:,.0f} | Implied APY: {implied_apy:.2f}%")
        print(f"    Expiry: {expiry}")
        print()
    return markets


def get_convert(chain_id: int, token_in: str, token_out: str,
                amount_wei: str, receiver: str,
                slippage: float = DEFAULT_SLIPPAGE):
    """Call the universal convert endpoint — works for all Pendle ops."""
    # Auto-replace ETH sentinel with WETH
    if token_in.lower() == ETH_SENTINEL:
        token_in = WETH.get(chain_id, WETH[1])
    if token_out.lower() == ETH_SENTINEL:
        token_out = WETH.get(chain_id, WETH[1])

    url = f"{BASE}/v2/sdk/{chain_id}/convert"
    params = {
        "receiver": receiver,
        "slippage": slippage,
        "tokensIn": token_in,
        "tokensOut": token_out,
        "amountsIn": amount_wei,
        "enableAggregator": "true",
    }
    try:
        resp = requests.get(url, params=params, timeout=20)
    except requests.RequestException as e:
        raise RuntimeError(f"Pendle API error: {e}") from e
    if resp.status_code != 200:
        raise RuntimeError(
            f"Pendle convert error {resp.status_code}: {resp.text}")
    result = resp.json()

    # tx lives inside routes[0].tx
    routes = result.get("routes", [])
    tx = routes[0].get("tx", {}) if routes else result.get("tx", {})

    print("Convert Result:")
    print(f"  Action: {result.get('action', 'N/A')}")
    for inp in result.get("inputs", []):
        print(f"  Input: {inp.get('amount', 'N/A')} of "
              f"{inp.get('token', 'N/A')[:10]}...")
    for out in result.get("outputs", []):
        print(f"  Output: {out.get('amount', 'N/A')} of "
              f"{out.get('token', 'N/A')[:10]}...")
    approvals = result.get("requiredApprovals", [])
    if approvals:
        print(f"  Approvals: {len(approvals)} required")
    print()
    if tx and tx.get("to"):
        print("Transaction to sign:")
        print(json.dumps({
            "to": tx.get("to"),
            "data": tx.get("data", "")[:80] + "...",
            "value": tx.get("value", "0"),
            "chain_id": chain_id,
        }, indent=2))
    else:
        print("No executable tx — check approvals or route parameters.")
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    try:
        if action == "markets":
            chain = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            print(f"Top Pendle Markets (chain {chain}):")
            list_markets(chain)
        elif action in ("quote", "convert"):
            if len(sys.argv) < 7:
                print("Usage: convert <chain_id> <token_in> <token_out>"
                      " <amount_wei> <receiver> [slippage]")
                sys.exit(1)
            chain_id = int(sys.argv[2])
            token_in = sys.argv[3]
            token_out = sys.argv[4]
            amount_wei = sys.argv[5]
            receiver = sys.argv[6]
            slippage = (float(sys.argv[7])
                        if len(sys.argv) > 7 else DEFAULT_SLIPPAGE)
            get_convert(chain_id, token_in, token_out,
                        amount_wei, receiver, slippage)
        else:
            print(f"Unknown action: {action}")
            print(__doc__)
            sys.exit(1)

    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
