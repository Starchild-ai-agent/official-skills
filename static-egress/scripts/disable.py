#!/usr/bin/env python3
"""Disable the allocation: revoke this agent's credential.

    python3 disable.py

The credential is revoked immediately. The egress address itself is app-scoped:
in shared-app mode it is **kept** (releasing it would break every other user's
allowlist entry) and is only released in per-user-app mode. An unreleased
address keeps billing — that is the operator's call, not this command's.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ServiceError, call, emit, fail  # noqa: E402


def main() -> int:
    try:
        payload = call("DELETE", "/v1/allocations/current")
    except ServiceError as exc:
        if exc.code == "not_found":
            emit({"disabled": False}, "Nothing to disable: no active allocation.")
            return 0
        return fail(exc.message, exc.code)

    released = ", ".join(payload.get("released") or []) or "(none)"
    retained = ", ".join(payload.get("retained") or []) or "(none)"
    emit(payload, f"Disabled. Credential revoked.\n"
                  f"  released: {released}\n"
                  f"  retained (app-scoped, still allowlisted): {retained}")
    return 0


if __name__ == "__main__":
    sys.exit(main())