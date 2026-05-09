#!/usr/bin/env python3
"""Interactive credential setup for a residential-proxy provider.

Usage:
    python3 setup_provider.py iproyal
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import PROVIDERS, save_credentials, ENV_FILE  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Register a residential-proxy provider.")
    ap.add_argument("provider", choices=sorted(PROVIDERS.keys()))
    args = ap.parse_args()

    if args.provider == "iproyal":
        print("IPRoyal residential proxy setup")
        print("  Find credentials at: https://dashboard.iproyal.com/  →  Residential  →  Access")
        print("  These are NOT your IPRoyal account login — they are the proxy username/password.")
        print()
        username = input("IPRoyal proxy username: ").strip()
        if not username:
            print("ERROR: username is required", file=sys.stderr)
            return 2
        password = getpass.getpass("IPRoyal proxy password: ").strip()
        if not password:
            print("ERROR: password is required", file=sys.stderr)
            return 2
        save_credentials("iproyal", username=username, password=password)
        print(f"\nSaved to {ENV_FILE}:")
        print("  IPROYAL_USERNAME=***")
        print("  IPROYAL_PASSWORD=***")
        print("\nNext: python3 scripts/test_proxy.py iproyal --country us")
        return 0

    print(f"Provider {args.provider!r} not implemented yet", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
