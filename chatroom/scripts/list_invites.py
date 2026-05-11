#!/usr/bin/env python3
"""chatroom list-invites <room_id>

Show active (unrevoked, unexpired, remaining uses > 0) invite codes for
a room. Returns only each code's jti — not the full code — so you cannot
re-send a code from here. If you need a fresh code, `chatroom invite
<room_id>` mints one.

Permissions:
  - Room owner sees every active invite.
  - Other members see only the invites they themselves created.
  - Non-members get 403.
"""
from __future__ import annotations

import argparse
import datetime
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="chatroom list-invites", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    r = C.chatroom_call("GET", f"/rooms/{room_id}/invites")
    if r.status_code != 200:
        C.die(f"sc-chatroom GET /invites returned {r.status_code}: {r.text}")
    invites = r.json().get("invites", [])
    if not invites:
        C.info("no active invites")
        return 0

    C.info(f"{'JTI':<24} {'USES':<10} {'EXPIRES':<20} CREATED_BY")
    for inv in invites:
        uses_col = f"{inv['uses']}/{inv['max_uses']}"
        exp_col = datetime.datetime.fromtimestamp(inv["expires_at"]).isoformat()
        C.info(f"{inv['code_jti']:<24} {uses_col:<10} {exp_col:<20} {inv['created_by_user_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
