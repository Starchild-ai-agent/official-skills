#!/usr/bin/env python3
"""Show the current allocation (never prints the credential).

    python3 status.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ServiceError, call, emit, fail  # noqa: E402


def main() -> int:
    try:
        payload = call("GET", "/v1/allocations/current")
    except ServiceError as exc:
        if exc.code == "not_found":
            return fail("no active allocation; run enable.py first", "not_found")
        return fail(exc.message, exc.code)

    ips = ", ".join(payload["allowlist"]) or "(none reported)"
    emit(
        payload,
        f"Allocation {payload['allocation_id']} in {payload['region']}\n"
        f"  egress allowlist: {ips}\n"
        f"  targets: {', '.join(':'.join(map(str, t)) for t in payload['targets'])}\n"
        f"  relay: {payload['relay']}\n"
        f"  allocation expires: {payload['expires_at']}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())