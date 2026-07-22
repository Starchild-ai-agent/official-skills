#!/usr/bin/env python3
"""x402 preset: ONE-SHOT purchase — probe → preflight → pay in one process.

Usage:
  python3 skills/x402/scripts/buy.py --url URL [--max-usd 0.05]
      [--method POST] [--json '{"q":"..."}'] [--network eip155:8453]
      [--skip-preflight]

Routing: explicit --network wins; otherwise funded rails first with Base
(eip155:8453) as the default chain (balance-aware sort in client.py).
Prints ONE JSON object: {success, status, paid, network, payer,
settlement{}, body, error}. Exit 0 = paid & 2xx. Exit 2 = preflight
blocked (nothing signed). Exit 1 = other failure.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True)
    p.add_argument("--max-usd", type=float, default=0.05,
                   help="Spend cap in USD (default 0.05, fail-closed)")
    p.add_argument("--method", default="GET")
    p.add_argument("--json", dest="json_body", default=None,
                   help="JSON request body string (implies POST unless set)")
    p.add_argument("--network", default="",
                   help="Preferred CAIP-2 network (optional; default = "
                        "funded-first with Base as default chain)")
    p.add_argument("--skip-preflight", action="store_true",
                   help="Skip the balance/policy preflight gate")
    args = p.parse_args()

    cap = int(round(args.max_usd * 1_000_000))
    result = {"success": False, "url": args.url, "max_usd": args.max_usd,
              "network": args.network or None, "error": None}

    body = None
    if args.json_body:
        try:
            body = json.loads(args.json_body)
        except ValueError as e:
            result["error"] = f"--json is not valid JSON: {e}"
            print(json.dumps(result))
            return 1
        if args.method == "GET":
            args.method = "POST"

    try:
        if not args.skip_preflight:
            from client import payment_preflight
            pf = payment_preflight(
                cap, networks=[args.network] if args.network else None)
            if not pf.get("ok"):
                result["error"] = "preflight blocked"
                result["blockers"] = pf.get("blockers")
                result["balances"] = pf.get("balances")
                print(json.dumps(result, indent=2))
                return 2

        from bazaar import bazaar_pay
        r = bazaar_pay(args.url, method=args.method, json_body=body,
                       max_usd=args.max_usd,
                       prefer_network=args.network)
        result.update({k: r.get(k) for k in
                       ("status", "paid", "network", "payer", "settlement",
                        "body", "error", "pricing_model", "resolution",
                        "signer_type", "signer_warning") if k in r})
        settled = bool((r.get("settlement") or {}).get("success")) \
            or bool(r.get("paid"))
        result["paid"] = settled
        result["tx_hash"] = (r.get("settlement") or {}).get("transaction")
        result["success"] = settled and 200 <= int(r.get("status") or 0) < 300
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
