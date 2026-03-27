#!/usr/bin/env python3
"""
Polymarket Close Positions — build SELL orders for all open positions.

Usage:
  python3 close_positions.py              # close all positions
  python3 close_positions.py --token_id X # close specific position

Output: One or more EIP-712 JSON files (/tmp/poly_close_N.json) for signing.
        Prints the signing instructions for the agent.
"""
import sys, json, argparse, time, random
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import (
    BASE, DATA_API, GAMMA, CHAIN_ID, CTF_EXCHANGE, CTF_EXCHANGE_NEG, EOA,
    cred, ensure_credentials, clob_get, die,
)
import requests

def get_positions():
    wallet = cred("POLY_WALLET")
    r = requests.get(f"{DATA_API}/positions", params={"user": wallet}, timeout=30)
    if r.status_code != 200:
        return []
    data = r.json()
    return data if isinstance(data, list) else data.get("data", [])

def get_orderbook(token_id):
    r = clob_get("/book", params={"token_id": token_id})
    if r.status_code != 200:
        return None, None
    book = r.json()
    bids = sorted(book.get("bids", []), key=lambda x: float(x["price"]), reverse=True)
    asks = sorted(book.get("asks", []), key=lambda x: float(x["price"]))
    return (float(bids[0]["price"]) if bids else None,
            float(asks[0]["price"]) if asks else None)

def get_market_info(token_id):
    info = {"fee_bps": 0, "neg_risk": False, "tick_size": "0.01"}
    try:
        r = requests.get(f"{GAMMA}/markets", params={"clob_token_ids": str(token_id)}, timeout=20)
        if r.status_code == 200:
            arr = r.json()
            if arr:
                cid = arr[0].get("conditionId")
                if cid:
                    rc = clob_get(f"/markets/{cid}")
                    if rc.status_code == 200:
                        mk = rc.json()
                        info["tick_size"] = str(mk.get("minimum_tick_size", "0.01"))
                        info["fee_bps"] = int(mk.get("taker_base_fee", 0) or 0)
                        info["neg_risk"] = bool(mk.get("neg_risk", False))
    except Exception:
        pass
    return info

def build_sell_payload(token_id, size, price, info, wallet):
    exchange = CTF_EXCHANGE_NEG if info["neg_risk"] else CTF_EXCHANGE
    tick = float(info["tick_size"])
    price = round(round(price / tick) * tick, 4)
    
    maker_amount = int(size * 1_000_000)
    taker_amount = int(price * size * 1_000_000)
    salt = round(time.time() * random.random())

    return {
        "domain": {
            "name": "Polymarket CTF Exchange", "version": "1",
            "chainId": CHAIN_ID, "verifyingContract": exchange,
        },
        "types": {"Order": [
            {"name": "salt", "type": "uint256"}, {"name": "maker", "type": "address"},
            {"name": "signer", "type": "address"}, {"name": "taker", "type": "address"},
            {"name": "tokenId", "type": "uint256"}, {"name": "makerAmount", "type": "uint256"},
            {"name": "takerAmount", "type": "uint256"}, {"name": "expiration", "type": "uint256"},
            {"name": "nonce", "type": "uint256"}, {"name": "feeRateBps", "type": "uint256"},
            {"name": "side", "type": "uint8"}, {"name": "signatureType", "type": "uint8"},
        ]},
        "primaryType": "Order",
        "message": {
            "salt": str(salt), "maker": wallet, "signer": wallet,
            "taker": "0x0000000000000000000000000000000000000000",
            "tokenId": str(token_id), "makerAmount": str(maker_amount),
            "takerAmount": str(taker_amount), "expiration": "0", "nonce": "0",
            "feeRateBps": str(info["fee_bps"]), "side": 1, "signatureType": EOA,
        },
        "meta": {
            "token_id": token_id, "salt": salt,
            "maker_amount": maker_amount, "taker_amount": taker_amount,
            "order_side": 1, "side_str": "SELL",
            "price": price, "size": size,
            "fee_bps": info["fee_bps"], "neg_risk": info["neg_risk"],
            "exchange": exchange,
        },
    }

def main():
    parser = argparse.ArgumentParser(description="Close Polymarket positions")
    parser.add_argument("--token_id", help="Specific token to close (default: all)")
    args = parser.parse_args()

    ok, msg = ensure_credentials()
    if not ok:
        die(msg)

    wallet = cred("POLY_WALLET")
    positions = get_positions()

    if not positions:
        print("No open positions.")
        return

    # Filter if specific token
    if args.token_id:
        positions = [p for p in positions if p.get("asset") == args.token_id]
        if not positions:
            die(f"No position found for token {args.token_id}")

    files = []
    for i, pos in enumerate(positions):
        token_id = pos.get("asset")
        size = float(pos.get("size", 0))
        if size <= 0:
            continue

        title = pos.get("title") or pos.get("market") or "?"
        info = get_market_info(token_id)
        best_bid, _ = get_orderbook(token_id)

        if best_bid is None or best_bid <= 0:
            print(f"⚠️  Skip {title}: no bid available")
            continue

        payload = build_sell_payload(token_id, size, best_bid, info, wallet)
        outfile = f"/tmp/poly_close_{i}.json"
        with open(outfile, "w") as f:
            json.dump(payload, f, indent=2)

        files.append(outfile)
        print(f"CLOSE #{i}: SELL {size} @ {best_bid} — {title}")
        print(f"  File: {outfile}")

    if files:
        print(f"\n📝 {len(files)} order(s) ready for signing.")
        print(f"For each file, sign with wallet_sign_typed_data, then run:")
        print(f"  python3 scripts/post_order.py <signature> --order <file>")
    else:
        print("No positions to close.")

if __name__ == "__main__":
    main()
