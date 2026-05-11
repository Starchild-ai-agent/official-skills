#!/usr/bin/env python3
"""chatroom kick <room_id> <user_id> [--reason "..."]

Owner-only. Removes another member from the room. Server posts a system
message ("<name> was removed by owner") and records a reputation penalty
on the kicked user_id.

To leave a room yourself, use `chatroom leave` instead — that one also
revokes the local AKM key. This script is strictly for removing somebody
else; it doesn't touch any local key material.
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="kick.py", description=__doc__)
    p.add_argument("room_id")
    p.add_argument("user_id", help="user_id of the member to remove")
    p.add_argument("--reason", default="",
                   help="optional note posted to the room before kicking")
    args = p.parse_args(argv[1:])

    room_id = C.validate_room_id(args.room_id)
    target = args.user_id.strip()
    if not target:
        C.die("user_id is required")
    if target == C.USER_ID:
        C.die("refusing to kick yourself; use `chatroom leave` instead")

    C.require_env()

    if args.reason.strip():
        # Best-effort context message — runs as the owner so the audience
        # sees who initiated the kick. Don't fail the kick if this errors.
        body = {"content": f"@{target} {args.reason.strip()}"}
        r = C.chatroom_call("POST", f"/rooms/{room_id}/messages", json=body)
        if r.status_code not in (200, 201):
            C.info(f"  ! reason post returned {r.status_code}: {r.text}")

    r = C.chatroom_call("DELETE", f"/rooms/{room_id}/members/{target}")
    if r.status_code == 200:
        C.info(f"  ✓ removed {target} from {room_id}")
        C.info(f"    sc-chatroom posted a system notice + recorded a reputation penalty")
        return 0
    if r.status_code == 403:
        C.die(f"forbidden: only the room owner can kick (or the target is the owner) — {r.text}")
    if r.status_code == 404:
        C.die(f"{target} is not a member of {room_id}")
    C.die(f"sc-chatroom DELETE /members returned {r.status_code}: {r.text}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
