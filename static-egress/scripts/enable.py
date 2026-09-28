#!/usr/bin/env python3
"""Open (or re-read) this agent's static egress allocation.

    python3 enable.py --target db-prod.xxxx.rds.amazonaws.com:5432 [--target ...]
                      [--region sjc]

Idempotent: re-running keeps the same egress IPs, so an allowlist entry the user
already added stays valid. A fresh token is minted and the previous one is
revoked, so it is also the "renew my credential" command.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ServiceError, call, emit, fail  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Enable static egress for this agent.")
    parser.add_argument("--target", action="append", required=True,
                        help="host:port the agent must reach (repeatable)")
    parser.add_argument("--region", default=None, help="relay region, e.g. sjc")
    args = parser.parse_args()

    body = {"targets": args.target}
    if args.region:
        body["region"] = args.region
    try:
        payload = call("POST", "/v1/allocations", body)
    except ServiceError as exc:
        return fail(exc.message, exc.code)

    ips = ", ".join(payload["allowlist"]) or "(none reported)"
    emit(
        payload,
        "Static egress enabled.\n"
        f"  add these to the target's firewall (once, permanently): {ips}\n"
        f"  relay: {payload['relay']}\n"
        f"  username: {payload['username']}   token: <in JSON above>\n"
        f"  token expires: {payload['token_expires_at']}\n"
        f"  one-time rule: {payload['sg_rule']}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())