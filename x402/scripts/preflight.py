#!/usr/bin/env python3
"""x402 preset: ONE-SHOT wallet preflight — no LLM reasoning needed.

Usage:
  python3 skills/x402/scripts/preflight.py [--usd 0.05] [--network eip155:8453]

Wraps client.payment_preflight (signer capability + wallet policy + live
USDC balances per rail, fail-closed). Prints ONE JSON object:
  {ok, payer{}, balances{}, funded_rails[], recommended_rail,
   blockers[], warnings[]}
Exit 0 = ok (at least one signable + funded rail). Exit 2 = blocked.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)

BASE = "eip155:8453"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--usd", type=float, default=0.05,
                   help="Purchase amount in USD (default 0.05)")
    p.add_argument("--amount-atomic", type=int, default=None,
                   help="Amount in atomic units (overrides --usd)")
    p.add_argument("--network", default=None,
                   help="Restrict check to one CAIP-2 network (optional)")
    args = p.parse_args()

    amount = args.amount_atomic or int(round(args.usd * 1_000_000))
    try:
        from client import payment_preflight
        out = payment_preflight(
            amount, networks=[args.network] if args.network else None)
    except Exception as e:
        print(json.dumps({"ok": False, "blockers":
                          [f"{type(e).__name__}: {e}"]}))
        return 2

    funded = out.get("funded_rails") or []
    # Base is the default rail; otherwise first funded.
    out["recommended_rail"] = (BASE if BASE in funded
                               else (funded[0] if funded else None))
    out["amount_atomic"] = amount
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
