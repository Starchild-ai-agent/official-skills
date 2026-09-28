#!/usr/bin/env python3
"""Prove the egress path — exit IP matches the allowlist and the target answers.

    python3 verify.py --target db-prod.xxxx.rds.amazonaws.com:5432

Never report success without running this: it is the difference between
"configured" and "actually works".
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ServiceError, call, emit, fail  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the egress path end to end.")
    parser.add_argument("--target", required=True, help="host:port to verify")
    args = parser.parse_args()

    try:
        result = call("POST", "/v1/verify", {"target": args.target})
    except ServiceError as exc:
        return fail(exc.message, exc.code)

    lines = [f"target          : {result['target']}",
             f"egress seen     : {result['egress_ip_seen'] or '(unknown)'}",
             f"allowlisted     : {', '.join(result['egress_ip_allocated']) or '(none)'}",
             f"egress matches  : {'yes' if result['egress_matches_allowlist'] else 'NO'}"]
    if result["target_reachable"].get("ok"):
        lines.append(f"tcp handshake   : ok ({result['target_reachable']['latency_ms']} ms)")
    else:
        lines.append(f"tcp handshake   : FAILED ({result['target_reachable'].get('error')})")
        lines.append("  → check the firewall allowlist above, then re-run this command")
    emit(result, "\n".join(lines))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())