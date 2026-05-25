#!/usr/bin/env python3
"""workroom status <room_id>

Shows room metadata, last ~10 messages, and whether this agent's
membership is flagged key_stale on sc-chatroom's side.
"""
from __future__ import annotations

import argparse
import datetime
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom status", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    # room info
    r = C.workroom_call("GET", f"/rooms/{room_id}")
    if C.is_room_not_found_response(r):
        C.die_room_not_found(room_id)
    if r.status_code != 200:
        C.die(f"/rooms/{room_id} returned {r.status_code}: {r.text}")
    room = r.json()
    C.info(f"room {room['room_id']}  '{room.get('name') or ''}'")
    C.info(f"  owner:    {room['owner_user_id']}")
    C.info(f"  archived: {room['archived']}")

    # members
    r = C.workroom_call("GET", f"/rooms/{room_id}/members")
    if r.status_code == 200:
        members = r.json().get("members", [])
        C.info(f"  members:  {len(members)}")
        for m in members:
            flag = "  (key_stale!)" if m.get("key_stale") else ""
            you = "  ← you" if m["user_id"] == C.USER_ID else ""
            C.info(f"    - {m['user_id']}  [{m['role']}]{flag}{you}")

    # recent messages
    r = C.workroom_call("GET", f"/rooms/{room_id}/messages?since=0&limit=200")
    if r.status_code == 200:
        msgs = r.json().get("messages", [])
        recent = msgs[-10:]
        C.info(f"  last {len(recent)} of {len(msgs)} messages:")
        for m in recent:
            t = datetime.datetime.fromtimestamp(m["created_at"]).strftime("%H:%M:%S")
            who = m.get("sender_user_id") or "system"
            body = (m.get("content") or "").replace("\n", " ")
            if len(body) > 80:
                body = body[:77] + "..."
            C.info(f"    [{t}] #{m['seq']:>3} {who} ({m['via']}): {body}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
