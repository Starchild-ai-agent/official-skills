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
            # Probe FIRST: preflight against the service's ACTUAL price and
            # ACTUAL accepted rails — max_usd is only a spend ceiling. Using
            # the cap as the amount would reject wallets that can afford the
            # real price; using all networks could pass on a rail the
            # service doesn't even accept.
            from bazaar import probe_402
            probe = probe_402(args.url, method=args.method, json_body=body)
            result["classification"] = probe.get("classification")
            if probe.get("payable"):
                price = int(probe.get("live_price_atomic") or 0) or cap
                result["live_price_usd"] = probe.get("live_price_usd")
                if price > cap:
                    result["error"] = (
                        f"price ${price / 1e6:.6g} exceeds --max-usd cap "
                        f"${args.max_usd:.6g}")
                    print(json.dumps(result, indent=2))
                    return 2
                nets = ([args.network] if args.network else
                        [r["network"] for r in probe.get("rails") or []
                         if r.get("network")] or None)
                from client import payment_preflight
                pf = payment_preflight(price, networks=nets)
                if not pf.get("ok"):
                    result["error"] = "preflight blocked"
                    result["blockers"] = pf.get("blockers")
                    result["balances"] = pf.get("balances")
                    print(json.dumps(result, indent=2))
                    return 2
            elif probe.get("classification") in ("tx-hash", "wrong-rail",
                                                 "non-standard",
                                                 "unreachable"):
                result["error"] = (f"not payable: "
                                   f"{probe.get('classification')} — "
                                   f"{probe.get('reason') or probe.get('error') or ''}")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 1
            # no-payment → free endpoint; fall through, bazaar_pay handles it

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
