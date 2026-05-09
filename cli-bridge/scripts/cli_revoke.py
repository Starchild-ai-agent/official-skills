#!/usr/bin/env python3
"""cli-revoke <code|prefix>

Revoke a CLI bundle. Two flavors:

  cli-revoke sc_xxxxxxxx          # default — kills the short code in
                                  # sc-chatroom; underlying AKM stays alive
                                  # (other bundles tied to the same AKM
                                  # are unaffected).

  cli-revoke --akm sk_xxxxxxxx    # also kills the AKM on local clawd —
                                  # ALL bundles backed by it stop working.

Use the short-code form unless you specifically want to nuke the AKM too.
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def _parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="cli-revoke")
    p.add_argument(
        "target",
        help="sc_… short code (default) or sk_… AKM prefix when used with --akm",
    )
    p.add_argument(
        "--akm", action="store_true",
        help="treat target as an AKM prefix and revoke the AKM directly on "
             "clawd (kills every bundle backed by it).",
    )
    return p.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = _parse(argv)
    target = args.target.strip()
    if not target:
        C.die("target is empty")
    C.require_env()

    if args.akm:
        # AKM-level revoke: only kill if scope matches the cli-bridge scope,
        # so a fat-fingered chatroom AKM prefix can't accidentally take out
        # someone's room key.
        lookup = C.clawd_call("GET", "/api/keys?include_expired=true")
        if lookup.status_code == 200:
            match = next(
                (k for k in lookup.json().get("keys", []) if k.get("prefix") == target),
                None,
            )
            if match is None:
                C.die(f"no AKM key with prefix {target!r} on this clawd")
            if match.get("scope") != C.CLI_BRIDGE_SCOPE:
                C.die(
                    f"refusing to revoke: key {target} has scope "
                    f"{match.get('scope')!r}, not {C.CLI_BRIDGE_SCOPE!r}. "
                    "Use the chatroom skill's revoke commands for room keys."
                )
        r = C.clawd_call("DELETE", f"/api/keys/{target}")
        if r.status_code in (200, 204):
            C.info(f"  ✓ revoked AKM {target} (all bundles using it now dead)")
            return 0
        if r.status_code == 404:
            C.die(f"AKM {target} not found")
        C.die(f"clawd DELETE returned {r.status_code}: {r.text}")

    # Short-code revoke: this is the default path.
    if not target.startswith("sc_"):
        C.die(
            f"expected sc_… short code (got {target!r}); use --akm if you "
            "intended to revoke an AKM prefix"
        )
    r = C.chatroom_call("DELETE", f"/cli-keys/{target}")
    if r.status_code in (200, 204):
        C.info(f"  ✓ revoked CLI bundle {target} on sc-chatroom")
        C.info("    (underlying AKM left alive; use --akm to revoke that too)")
        return 0
    if r.status_code == 404:
        C.die(f"code {target} not found, already revoked, or not yours")
    C.die(f"sc-chatroom DELETE /cli-keys/{target} returned {r.status_code}: {r.text}")
    return 1  # unreachable


if __name__ == "__main__":
    sys.exit(main(sys.argv))
