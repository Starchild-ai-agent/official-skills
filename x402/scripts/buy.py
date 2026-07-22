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
        from bazaar import bazaar_pay, probe_402, resolve_marketplace, \
            _canon_network, _amount_int

        # Resolve FIRST so probe/preflight/pay all use the SAME URL.
        # bazaar_pay() pays the community proxy pay_url, not the raw URL —
        # probing the raw URL could classify "no-payment" (free upstream)
        # while the proxy returns 402, silently skipping preflight.
        pay_url = args.url
        _listed = True
        try:
            res = resolve_marketplace(args.url)
            if res.get("ok") and res.get("pay_url"):
                pay_url = res["pay_url"]
            _listed = res.get("via") != "direct"
        except Exception:
            _listed = False
        _direct_ok = os.environ.get("X402_INTERNAL_DIRECT_PAY") == "1"

        pay_network = args.network  # rail actually validated & paid
        if not args.skip_preflight and (_listed or _direct_ok):
            probe = probe_402(pay_url, method=args.method, json_body=body)
            result["classification"] = probe.get("classification")
            if probe.get("payable"):
                # Select the FINAL rail first, then preflight with that
                # rail's own amount+network (rails may differ in price;
                # bazaar_pay must not fall back to an unvalidated chain).
                rails = [r for r in probe.get("rails") or []
                         if r.get("network")]
                if args.network:
                    want = _canon_network(args.network)
                    rails = [r for r in rails
                             if _canon_network(r["network"]) == want]
                    if not rails:
                        result["error"] = (
                            f"--network {args.network} not in service "
                            f"accepts; accepted: "
                            f"{[r['network'] for r in probe.get('rails') or []]}")
                        print(json.dumps(result, indent=2))
                        return 2
                if not rails:
                    result["error"] = "payable but no usable rail in probe"
                    print(json.dumps(result, indent=2))
                    return 1
                rail = min(rails, key=_amount_int)  # cheapest on chosen chain
                price = _amount_int(rail)
                if price >= (1 << 62):
                    result["error"] = (f"malformed amount on rail "
                                       f"{rail.get('network')}: "
                                       f"{rail.get('amount')!r}")
                    print(json.dumps(result, indent=2))
                    return 1
                pay_network = str(rail["network"])
                result["network"] = pay_network
                result["live_price_usd"] = price / 1e6
                if price > cap:
                    result["error"] = (
                        f"price ${price / 1e6:.6g} exceeds --max-usd cap "
                        f"${args.max_usd:.6g}")
                    print(json.dumps(result, indent=2))
                    return 2
                from client import payment_preflight
                pf = payment_preflight(
                    price, networks=[_canon_network(pay_network)])
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
        # unlisted+no gate: skip prep, let bazaar_pay emit canonical refusal

        # Pay the SAME resolved pay_url; pin the preflighted rail so
        # bazaar_pay cannot fall back to a chain that skipped validation.
        r = bazaar_pay(pay_url, method=args.method, json_body=body,
                       max_usd=args.max_usd,
                       prefer_network=pay_network)
        result.update({k: r.get(k) for k in
                       ("status", "paid", "network", "payer", "settlement",
                        "body", "error", "pricing_model", "resolution",
                        "signer_type", "signer_warning") if k in r})
        settled = bool((r.get("settlement") or {}).get("success")) \
            or bool(r.get("paid"))
        result["paid"] = settled
        result["tx_hash"] = (r.get("settlement") or {}).get("transaction")
        # Post-pay audit: the paid rail must be the preflighted rail.
        if (pay_network and r.get("network")
                and _canon_network(r["network"])
                != _canon_network(pay_network)):
            result["network_mismatch"] = (
                f"paid on {r['network']} but preflight validated "
                f"{pay_network} — service accepts changed mid-flight")
        result["success"] = settled and 200 <= int(r.get("status") or 0) < 300
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
