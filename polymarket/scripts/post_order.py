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

try:
    import os as _o
    sys.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))
    from _trade_report import report_trade_events
except Exception:
    def report_trade_events(events):  # noqa: ARG001
        pass

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

    try:
        _size = float(meta.get("size") or 0) or None
        _price = float(meta.get("price") or 0) or None
        report_trade_events([{
            "source": "polymarket",
            "venue": "polymarket",
            "event_type": "order",
            "dedupe_key": f"polymarket:{order_id}",
            "wallet_address": wallet,
            "symbol": str(message.get("tokenId", ""))[:64],
            "side": side_str.lower(),
            "price": _price,
            "size": _size,
            "notional_usd": round(_size * _price, 6) if (_size and _price) else None,
            "order_id": str(order_id),
            "tx_hash": tx_hashes[0] if tx_hashes else None,
            "raw": {"status": status, "taking": taking, "making": making},
        }])
    except Exception:  # noqa: BLE001 — reporting must never break trading
        pass

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
