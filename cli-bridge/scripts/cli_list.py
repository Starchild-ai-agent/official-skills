#!/usr/bin/env python3
"""cli-list [--include-revoked]

List the CLI bundles this user has minted on sc-chatroom (sc_… short
codes). Each row: code, label, created, expires, last_used, use_count.

The underlying AKM secrets are NOT shown — sc-chatroom holds them server-
side and never returns them. To see the AKM rows themselves, use the
chatroom skill's `list_room_keys` style introspection on clawd directly.
"""
from __future__ import annotations

import argparse
import datetime
import sys

import _common as C


def _ts(v) -> str:
    if not v:
        return "-"
    return datetime.datetime.fromtimestamp(v).isoformat(timespec="minutes")


def _parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="cli-list",
        description="Show CLI short-code bundles minted on sc-chatroom.",
    )
    p.add_argument(
        "--include-revoked", action="store_true",
        help="Also show codes the user has already revoked.",
    )
    return p.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = _parse(argv)
    C.require_env()

    qs = "?include_revoked=true" if args.include_revoked else ""
    r = C.chatroom_call("GET", f"/cli-keys{qs}")
    if r.status_code != 200:
        C.die(f"sc-chatroom GET /cli-keys returned {r.status_code}: {r.text}")
    keys = r.json().get("keys", [])
    if not keys:
        C.info("no CLI bundles on sc-chatroom for this user")
        if not args.include_revoked:
            C.info("  (re-run with --include-revoked to see revoked ones)")
        return 0

    hdr = f"{'CODE':<14} {'ISSUED':<18} {'EXPIRES':<18} {'USES':<6} LABEL"
    C.info(hdr)
    C.info("-" * len(hdr))
    for k in keys:
        flags = " ✗revoked" if k.get("revoked") else ""
        C.info(
            f"{k.get('code', '?'):<14} "
            f"{_ts(k.get('created_at')):<18} "
            f"{_ts(k.get('expires_at')):<18} "
            f"{str(k.get('use_count') or 0):<6} "
            f"{k.get('label') or ''}{flags}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
