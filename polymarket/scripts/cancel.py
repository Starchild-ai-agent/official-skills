#!/usr/bin/env python3
"""
Polymarket Cancel — cancel one or all open orders.

Usage:
  python3 cancel.py --all
  python3 cancel.py --id 0xabc123...

Output: Cancellation result.
"""
import sys, json, argparse
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import BASE, cred, ensure_credentials, clob_delete, l2_headers, die

def main():
    parser = argparse.ArgumentParser(description="Cancel orders")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Cancel all open orders")
    group.add_argument("--id", help="Cancel specific order ID")
    args = parser.parse_args()

    ok, msg = ensure_credentials()
    if not ok:
        die(msg)

    if args.all:
        r = clob_delete("/cancel-all", headers=l2_headers("DELETE", "/cancel-all"))
        result = r.json() if r.text.strip() else {}
        canceled = result.get("canceled", [])
        not_canceled = result.get("not_canceled", {})
        print(f"✅ Canceled: {len(canceled)} orders")
        if not_canceled:
            print(f"⚠️  Not canceled: {json.dumps(not_canceled)}")
    else:
        body = json.dumps({"orderID": args.id})
        r = clob_delete("/order", headers=l2_headers("DELETE", "/order", body), data=body)
        result = r.json() if r.text.strip() else {}
        if r.status_code == 200:
            print(f"✅ Canceled: {args.id}")
        else:
            print(f"❌ Failed ({r.status_code}): {json.dumps(result)}")

if __name__ == "__main__":
    main()
