#!/usr/bin/env python3
"""Interactive credential setup for a gateway proxy provider.

Usage:
    python3 setup_provider.py iproyal

`iproyal-isp` has per-IP credentials — use add_isp_proxy.py for it.
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import ENV_FILE, PROVIDERS, save_credentials  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Register a gateway proxy provider.")
    ap.add_argument("provider", choices=sorted(PROVIDERS.keys()))
    args = ap.parse_args()

    if PROVIDERS[args.provider]["kind"] == "isp":
        print(
            f"Provider {args.provider!r} has per-IP credentials; register each proxy with:\n"
            f"  python3 scripts/add_isp_proxy.py <proxy-id> --host <host> --port <port> "
            f"--username <user> --password <pass>",
            file=sys.stderr,
        )
        return 2

    cfg = PROVIDERS[args.provider]
    print(f"{args.provider} proxy setup")
    print(f"  Find credentials at: {cfg['dashboard_url']}")
    print(f"  {cfg['credential_hint']}")
    print()
    username = input(f"{args.provider} proxy username: ").strip()
    if not username:
        print("ERROR: username is required", file=sys.stderr)
        return 2
    password = getpass.getpass(f"{args.provider} proxy password: ").strip()
    if not password:
        print("ERROR: password is required", file=sys.stderr)
        return 2
    save_credentials(args.provider, username=username, password=password)
    print(f"\nSaved to {ENV_FILE}:")
    print(f"  {cfg['env_user']}=***")
    print(f"  {cfg['env_pass']}=***")
    print(f"\nNext: python3 scripts/test_proxy.py {args.provider} --country us")
    return 0


if __name__ == "__main__":
    sys.exit(main())