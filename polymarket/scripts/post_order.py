#!/usr/bin/env python3
"""
Polymarket Post Order — submit a signed order to CLOB and verify.

Usage:
  python3 post_order.py <signature> [--order /tmp/poly_order.json]

Output: Order ID, fill status, updated position.
"""
import sys, json, argparse
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import (
    BASE, EOA, cred, ensure_credentials,
    clob_post, l2_headers, die, fmt_usd,
)

def main():
    parser = argparse.ArgumentParser(description="Post signed order")
    parser.add_argument("signature", help="EIP-712 signature (0x...)")
    parser.add_argument("--order", default="/tmp/poly_order.json", help="Order JSON file")
    args = parser.parse_args()

    ok, msg = ensure_credentials()
    if not ok:
        die(msg)

    try:
        with open(args.order) as f:
            payload = json.load(f)
    except Exception as e:
        die(f"Cannot read {args.order}: {e}")

    meta = payload["meta"]
    message = payload["message"]
    wallet = cred("POLY_WALLET")
    api_key = cred("POLY_API_KEY")
    side_str = "BUY" if meta["order_side"] == 0 else "SELL"

    order_body = {
        "order": {
            "salt": meta["salt"],
            "maker": wallet,
            "signer": wallet,
            "taker": "0x0000000000000000000000000000000000000000",
            "tokenId": str(meta["token_id"]),
            "makerAmount": str(meta["maker_amount"]),
            "takerAmount": str(meta["taker_amount"]),
            "expiration": "0",
            "nonce": "0",
            "feeRateBps": str(meta.get("fee_bps", 0)),
            "side": side_str,
            "signatureType": EOA,
            "signature": args.signature,
        },
        "owner": api_key,
        "orderType": "GTC",
    }

    body_str = json.dumps(order_body, separators=(",", ":"))
    headers = l2_headers("POST", "/order", body_str)
    r = clob_post("/order", headers=headers, data=body_str)

    result = r.json() if r.text.strip() else {}
    
    if r.status_code != 200:
        print(f"FAILED ({r.status_code}): {json.dumps(result, indent=2)}")
        sys.exit(1)

    order_id = result.get("orderID", "?")
    taking = result.get("takingAmount", "")
    making = result.get("makingAmount", "")
    status = result.get("status", "")
    tx_hashes = result.get("transactionsHashes", [])

    print(f"✅ ORDER POSTED")
    print(f"  ID: {order_id}")
    print(f"  Side: {side_str} {meta['size']} @ {meta['price']}")
    if taking:
        print(f"  Filled: taking={taking} making={making}")
    if status:
        print(f"  Status: {status}")
    if tx_hashes:
        for tx in tx_hashes:
            print(f"  TX: https://polygonscan.com/tx/{tx}")

if __name__ == "__main__":
    main()
