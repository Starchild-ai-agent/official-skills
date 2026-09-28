"""Programmatic versions of the CLI operations.

`exports.py` re-exports these so another skill can wire the egress in-process
instead of shelling out. Each returns the control plane's JSON and raises
`ServiceError` when refused — the message is the user's remediation guide.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import call  # noqa: E402


def enable_egress(targets, region=None) -> dict:
    """Open or renew this agent's static egress for `targets`.

    `targets` is a list of "host:port" strings (external destinations only).
    Returns the allocation: relay address, credential, the allowlist addresses
    and a ready-to-paste firewall rule. Idempotent — the egress IPs are stable,
    so an allowlist entry already installed stays valid.
    """
    body = {"targets": list(targets)}
    if region:
        body["region"] = region
    return call("POST", "/v1/allocations", body)


def egress_status() -> dict:
    """The current allocation (read-only; never contains the credential)."""
    return call("GET", "/v1/allocations/current")


def verify_egress(target: str) -> dict:
    """Prove the path: the exit address the target sees, plus a real TCP handshake.

    Call this before claiming the egress works; `target_reachable.ok` is the
    handshake, `egress_matches_allowlist` is whether the target sees the address
    you allowlisted.
    """
    return call("POST", "/v1/verify", {"target": target})


def disable_egress() -> dict:
    """Revoke this agent's credential.

    The egress address is app-scoped: in shared mode it is retained (releasing it
    would break every other user's allowlist entry) and reported under
    `retained`; it is released only in per-user-app mode.
    """
    return call("DELETE", "/v1/allocations/current")