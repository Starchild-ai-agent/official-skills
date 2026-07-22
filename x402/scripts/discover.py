#!/usr/bin/env python3
"""x402 preset: FREE probe of a service's 402 rails — never pays.

Usage:
  python3 skills/x402/scripts/discover.py --url URL
  python3 skills/x402/scripts/discover.py --query "weather api" [--limit 5]

--url   → probe_402: classification + payable rails (funded-first order,
          Base default), plus which rail bazaar_pay would actually use.
--query → discover_services: marketplace + Bazaar catalog search.
Prints ONE JSON object. Exit 0 = payable / results found, 1 otherwise.
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
    p.add_argument("--url", default=None)
    p.add_argument("--query", default=None)
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--method", default="GET")
    args = p.parse_args()
    if not args.url and not args.query:
        p.error("need --url or --query")

    try:
        if args.url:
            from bazaar import probe_402
            out = probe_402(args.url, method=args.method)
            ok = out.get("classification") == "standard-v2"
        else:
            from bazaar import discover_services
            out = discover_services(args.query, limit=args.limit)
            ok = bool(out.get("results") or out.get("items"))
    except Exception as e:
        out, ok = {"error": f"{type(e).__name__}: {e}"}, False

    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
