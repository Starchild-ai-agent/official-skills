#!/usr/bin/env python3
"""workroom revoke-invite <room_id> <code_jti>

Immediately invalidate one outstanding invite code. Use
`workroom list-invites <room_id>` to see the jtis.

Permissions: the room owner can revoke any invite; other members can
revoke only the invites they themselves created. Anyone else gets 403.
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom revoke-invite", description=__doc__)
    p.add_argument("room_id")
    p.add_argument("code_jti", help="invite jti from `workroom list-invites`")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    jti = args.code_jti.strip()
    if not jti:
        C.die("code_jti is empty")
    C.require_env()

    r = C.workroom_call("DELETE", f"/rooms/{room_id}/invites/{jti}")
    if r.status_code == 200:
        C.info(f"  ✓ invite {jti} revoked")
        return 0
    if r.status_code == 404:
        C.die(f"invite {jti} not found in room {room_id} (already revoked?)")
    C.die(f"sc-chatroom DELETE /invites returned {r.status_code}: {r.text}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
