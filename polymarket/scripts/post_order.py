#!/usr/bin/env python3
"""
Polymarket Post Order — submit a signed order to CLOB and verify.

Usage:
  python3 post_order.py <signature> [--order /tmp/poly_order.json]

Output: Order ID, fill status, updated position.
"""
import sys, json, argparse, re
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

    sig = (args.signature or "").strip()
    if not re.fullmatch(r"0x[0-9a-fA-F]+", sig):
        die("Invalid signature format: expected 0x-prefixed hex from wallet_sign_typed_data")
    if len(sig) < 130:
        die("Invalid signature length: expected full ECDSA signature from wallet_sign_typed_data")

    try:
        with open(args.order) as f:
            payload = json.load(f)
    except Exception as e:
        die(f"Cannot read {args.order}: {e}")

    meta = payload["meta"]
    message = payload["message"]
    wallet = cred("POLY_WALLET")
    api_key = cred("POLY_API_KEY")
    side_str = "BUY" if int(message.get("side", meta.get("order_side", 0))) == 0 else "SELL"

    # CLOB V2 wire format: salt MUST be int, taker/nonce/feeRateBps removed
    order_body = {
        "order": {
            "salt": int(message["salt"]),
            "maker": wallet,
            "signer": wallet,
            "tokenId": str(message["tokenId"]),
            "makerAmount": str(message["makerAmount"]),
            "takerAmount": str(message["takerAmount"]),
            "side": side_str,
            "signatureType": int(message.get("signatureType", EOA)),
            "timestamp": str(message["timestamp"]),
            "metadata": str(message.get("metadata", "0x" + "0" * 64)),
            "builder": str(message.get("builder", "0x" + "0" * 64)),
            "expiration": "0",
            "signature": args.signature,
        },
        "owner": api_key,
        "orderType": "GTC",
        "deferExec": False,
        "postOnly": False,
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
