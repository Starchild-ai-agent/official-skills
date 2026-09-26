#!/usr/bin/env python3
"""Issue a single test request through the proxy and report the exit IP.

Gateway provider:
    python3 test_proxy.py iproyal --country jp

Dedicated static IP:
    python3 test_proxy.py iproyal-isp --proxy-id jp-1
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import PROVIDERS, ProxyNotConfiguredError, test_proxy  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("provider", choices=sorted(PROVIDERS.keys()))
    ap.add_argument("--country", help="ISO-3166-1 alpha-2 code (gateway providers)")
    ap.add_argument("--proxy-id", dest="proxy_id", help="Registered ISP proxy id (isp providers)")
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args()

    kind = PROVIDERS[args.provider]["kind"]
    if kind == "gateway" and not args.country:
        ap.error(f"--country is required for provider {args.provider!r}")
    if kind == "isp" and not args.proxy_id:
        ap.error(f"--proxy-id is required for provider {args.provider!r}")

    try:
        result = test_proxy(args.provider, country=args.country,
                            proxy_id=args.proxy_id, timeout=args.timeout)
    except ProxyNotConfiguredError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if not result["ok"]:
        print(f"FAIL ({result['latency_ms']}ms): {result.get('error')}", file=sys.stderr)
        return 1

    if kind == "isp":
        print(f"OK  exit_ip={result['exit_ip']}  country={result['geo_country']}  "
              f"latency={result['latency_ms']}ms")
        print(f"  Dedicated IP — no rotation. Expected exit_ip matches your "
              f"registered proxy for {args.proxy_id!r}.")
        return 0

    requested = args.country.lower()
    actual = result["geo_country"]
    geo_match = "✅" if actual == requested else "⚠️ "
    print(f"OK  exit_ip={result['exit_ip']}  "
          f"country={actual} (requested {requested}) {geo_match}  "
          f"latency={result['latency_ms']}ms")
    if actual != requested:
        print(f"  Note: requested {requested!r} but got {actual!r}. "
              f"IPRoyal may rotate to a nearby country if the requested pool is depleted.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())