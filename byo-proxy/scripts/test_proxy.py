#!/usr/bin/env python3
"""Issue a single test request through the proxy and report exit IP/country.

Usage:
    python3 test_proxy.py iproyal --country jp
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import test_proxy, ProxyNotConfiguredError  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("provider")
    ap.add_argument("--country", required=True)
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args()

    try:
        result = test_proxy(args.provider, args.country, timeout=args.timeout)
    except ProxyNotConfiguredError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if not result["ok"]:
        print(f"FAIL ({result['latency_ms']}ms): {result.get('error')}", file=sys.stderr)
        return 1

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
