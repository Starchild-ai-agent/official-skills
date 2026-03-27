#!/usr/bin/env python3
"""
Polymarket Status — balance + positions + open orders in one shot.

Usage:
  python3 status.py
  python3 status.py --json

Output: Human-readable summary or raw JSON.
"""
import sys, json, argparse
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import (
    BASE, DATA_API, cred, ensure_credentials,
    clob_get, l2_headers, fmt_usd, die,
)
import requests

def get_balance():
    r = clob_get("/balance-allowance",
        headers=l2_headers("GET", "/balance-allowance"),
        params={"asset_type": "COLLATERAL", "signature_type": 0},
    )
    return r.json() if r.status_code == 200 else {}

def get_positions():
    wallet = cred("POLY_WALLET")
    r = requests.get(f"{DATA_API}/positions", params={"user": wallet}, timeout=30)
    return r.json() if r.status_code == 200 else []

def get_open_orders():
    r = clob_get("/data/orders", headers=l2_headers("GET", "/data/orders"))
    return r.json() if r.status_code == 200 else {}

def get_trades(limit=5):
    wallet = cred("POLY_WALLET")
    r = requests.get(f"{DATA_API}/trades", params={"user": wallet, "limit": limit}, timeout=30)
    return r.json() if r.status_code == 200 else []

def main():
    parser = argparse.ArgumentParser(description="Polymarket Status")
    parser.add_argument("--json", action="store_true", help="Raw JSON output")
    args = parser.parse_args()

    ok, msg = ensure_credentials()
    if not ok:
        die(msg)

    balance = get_balance()
    positions = get_positions()
    orders = get_open_orders()
    trades = get_trades(5)

    if args.json:
        print(json.dumps({
            "balance": balance,
            "positions": positions,
            "orders": orders,
            "recent_trades": trades,
        }, indent=2))
        return

    # Human-readable
    bal = fmt_usd(balance.get("balance", "0"))
    print(f"💰 Balance: ${bal:.2f}")

    # Positions
    pos_list = positions if isinstance(positions, list) else positions.get("data", [])
    if pos_list:
        print(f"\n📊 Positions ({len(pos_list)}):")
        for p in pos_list:
            token = p.get("asset", "?")[:12] + "..."
            size = p.get("size", 0)
            avg = p.get("avgPrice", "?")
            cur = p.get("curPrice", "?")
            title = p.get("title") or p.get("market", "?")
            side = p.get("proxyOutcome") or ("YES" if p.get("outcome", "") == "Yes" else "NO")
            print(f"  {side} {size} @ avg={avg} cur={cur} — {title}")
    else:
        print("\n📊 Positions: none")

    # Open orders  
    order_list = orders.get("data", []) if isinstance(orders, dict) else orders
    if order_list:
        print(f"\n📋 Open Orders ({len(order_list)}):")
        for o in order_list:
            side = o.get("side", "?")
            price = o.get("price", "?")
            size_matched = o.get("size_matched", "0")
            original = o.get("original_size", "?")
            oid = o.get("id", "?")[:16] + "..."
            print(f"  {side} {original} @ {price} (filled={size_matched}) [{oid}]")
    else:
        print("\n📋 Open Orders: none")

    # Recent trades
    if trades:
        print(f"\n🔄 Recent Trades:")
        for t in trades[:5]:
            side = t.get("side", "?")
            size = t.get("size", "?")
            price = t.get("price", "?")
            title = t.get("title") or t.get("market", "?")
            print(f"  {side} {size} @ {price} — {title}")

if __name__ == "__main__":
    main()
