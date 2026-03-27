#!/usr/bin/env python3
"""
Polymarket Prepare Order — build EIP-712 payload for signing.

Usage:
  python3 prepare_order.py <token_id> BUY 0.76 13
  python3 prepare_order.py <token_id> SELL 0.76 13

Output: JSON with domain/types/message for wallet_sign_typed_data,
        plus meta for post_order.py. Saved to /tmp/poly_order.json.
"""
import sys, json, argparse, time, random
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import (
    BASE, GAMMA, CHAIN_ID, CTF_EXCHANGE, CTF_EXCHANGE_NEG, EOA,
    cred, ensure_credentials, clob_get, die, fmt_usd,
)
import requests

def get_market_info(token_id):
    """Get fee, neg_risk, tick_size for a token."""
    info = {"fee_bps": 0, "neg_risk": False, "tick_size": "0.01", "min_size": 5}
    
    # Gamma lookup: token → condition
    try:
        r = requests.get(f"{GAMMA}/markets", params={"clob_token_ids": str(token_id)}, timeout=20)
        if r.status_code == 200:
            arr = r.json()
            if isinstance(arr, list) and arr:
                cid = arr[0].get("conditionId")
                if cid:
                    # CLOB metadata
                    rc = clob_get(f"/markets/{cid}")
                    if rc.status_code == 200:
                        mk = rc.json()
                        info["tick_size"] = str(mk.get("minimum_tick_size", "0.01"))
                        info["fee_bps"] = int(mk.get("taker_base_fee", 0) or mk.get("maker_base_fee", 0) or 0)
                        info["neg_risk"] = bool(mk.get("neg_risk", False))
                        info["min_size"] = float(mk.get("minimum_order_size", 5))
    except Exception:
        pass
    return info

def get_orderbook(token_id):
    """Get best bid/ask."""
    r = clob_get(f"/book", params={"token_id": token_id})
    if r.status_code != 200:
        return None, None
    book = r.json()
    bids = sorted(book.get("bids", []), key=lambda x: float(x["price"]), reverse=True)
    asks = sorted(book.get("asks", []), key=lambda x: float(x["price"]))
    best_bid = float(bids[0]["price"]) if bids else None
    best_ask = float(asks[0]["price"]) if asks else None
    return best_bid, best_ask

def main():
    parser = argparse.ArgumentParser(description="Build Polymarket order")
    parser.add_argument("token_id", help="CLOB token ID")
    parser.add_argument("side", choices=["BUY", "SELL", "buy", "sell"])
    parser.add_argument("price", type=float, help="Limit price (0.01-0.99)")
    parser.add_argument("size", type=float, help="Number of shares")
    parser.add_argument("--out", default="/tmp/poly_order.json", help="Output file")
    args = parser.parse_args()

    ok, msg = ensure_credentials()
    if not ok:
        die(msg)

    side = args.side.upper()
    wallet = cred("POLY_WALLET")

    # Market info
    info = get_market_info(args.token_id)
    tick = float(info["tick_size"])
    price = round(round(args.price / tick) * tick, 4)
    size = round(args.size, 2)

    if size < info["min_size"]:
        die(f"Size {size} below minimum {info['min_size']}")

    # Orderbook check
    best_bid, best_ask = get_orderbook(args.token_id)
    
    exchange = CTF_EXCHANGE_NEG if info["neg_risk"] else CTF_EXCHANGE

    if side == "BUY":
        taker_amount = int(size * 1_000_000)
        maker_amount = round(round(size * price, 4) * 1_000_000)
        order_side = 0
    else:
        maker_amount = int(size * 1_000_000)
        taker_amount = int(price * size * 1_000_000)
        order_side = 1

    salt = round(time.time() * random.random())

    payload = {
        "domain": {
            "name": "Polymarket CTF Exchange",
            "version": "1",
            "chainId": CHAIN_ID,
            "verifyingContract": exchange,
        },
        "types": {
            "Order": [
                {"name": "salt", "type": "uint256"},
                {"name": "maker", "type": "address"},
                {"name": "signer", "type": "address"},
                {"name": "taker", "type": "address"},
                {"name": "tokenId", "type": "uint256"},
                {"name": "makerAmount", "type": "uint256"},
                {"name": "takerAmount", "type": "uint256"},
                {"name": "expiration", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "feeRateBps", "type": "uint256"},
                {"name": "side", "type": "uint8"},
                {"name": "signatureType", "type": "uint8"},
            ]
        },
        "primaryType": "Order",
        "message": {
            "salt": str(salt),
            "maker": wallet,
            "signer": wallet,
            "taker": "0x0000000000000000000000000000000000000000",
            "tokenId": str(args.token_id),
            "makerAmount": str(maker_amount),
            "takerAmount": str(taker_amount),
            "expiration": "0",
            "nonce": "0",
            "feeRateBps": str(info["fee_bps"]),
            "side": order_side,
            "signatureType": EOA,
        },
        "meta": {
            "token_id": args.token_id,
            "salt": salt,
            "maker_amount": maker_amount,
            "taker_amount": taker_amount,
            "order_side": order_side,
            "side_str": side,
            "price": price,
            "size": size,
            "fee_bps": info["fee_bps"],
            "neg_risk": info["neg_risk"],
            "exchange": exchange,
        },
    }

    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2)

    cost = maker_amount / 1_000_000 if side == "BUY" else size
    print(f"ORDER READY: {side} {size} shares @ {price} (cost ~${cost:.2f})")
    if best_bid is not None:
        print(f"  Orderbook: bid={best_bid} ask={best_ask}")
    print(f"  Saved to: {args.out}")
    print(f"  Next: wallet_sign_typed_data(domain, types, primaryType='Order', message)")

if __name__ == "__main__":
    main()
