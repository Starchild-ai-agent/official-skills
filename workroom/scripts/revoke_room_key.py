#!/usr/bin/env python3
"""workroom revoke-room-key <room_id> [<jti>]

Revoke viewer room-key(s) for this user in this room.

Modes:
  no jti  → revoke ALL of this user's active room-keys in the room (bulk)
  with jti → revoke just that one (use `list-room-keys` to find the jti)

If you're rotating because a URL leaked, prefer `room-key <room_id> --rotate`
which bulk-revokes AND mints a fresh URL in one step.
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom revoke-room-key", description=__doc__)
    p.add_argument("room_id")
    p.add_argument("jti", nargs="?", default=None,
                   help="optional: revoke only this jti (default: revoke all)")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    jti = args.jti.strip() if args.jti else None
    C.require_env()

    if jti:
        r = C.workroom_call("DELETE", f"/rooms/{room_id}/room-keys/{jti}")
        if r.status_code == 200:
            C.info(f"  ✓ revoked room-key {jti}")
            return 0
        if r.status_code == 404:
            C.die(f"key {jti} not found or already revoked")
        C.die(f"sc-chatroom DELETE returned {r.status_code}: {r.text}")
    else:
        r = C.workroom_call("DELETE", f"/rooms/{room_id}/room-keys")
        if r.status_code != 200:
            C.die(f"sc-chatroom DELETE returned {r.status_code}: {r.text}")
        n = r.json().get("revoked", 0)
        C.info(f"  ✓ revoked {n} room-key(s) for {C.USER_ID} in {room_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
