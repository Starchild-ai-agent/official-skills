#!/usr/bin/env python3
"""chatroom members <room_id>

Lists every member of a room: user_id, display name, role, member_kind,
online (browser SSE active), and key_stale.

Use this when you need to know "who's actually in this room right now" —
e.g. the LLM is hosting a game and wants the participant roster, or
deciding who to @-mention.
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="chatroom members", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    r = C.chatroom_call("GET", f"/rooms/{room_id}/members")
    if r.status_code != 200:
        C.die(f"/rooms/{room_id}/members returned {r.status_code}: {r.text}")
    members = r.json().get("members", [])

    C.info(f"room {room_id} — {len(members)} member(s):")
    if not members:
        return 0

    # Sort: online first, owners next, then by user_name for stable output.
    members.sort(key=lambda m: (
        not m.get("online"),
        m.get("role") != "owner",
        (m.get("user_name") or m.get("user_id") or "").lower(),
    ))

    for m in members:
        uid = m["user_id"]
        name = m.get("user_name") or "—"
        role = m.get("role", "member")
        kind = m.get("member_kind") or "?"
        marks = []
        if m.get("online"):
            marks.append("🟢 online")
        if m.get("key_stale"):
            marks.append("⚠ key_stale")
        if uid == C.USER_ID:
            marks.append("← you")
        tail = ("  " + " ".join(marks)) if marks else ""
        C.info(f"  - {name}  ({uid})  [{role}/{kind}]{tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
