#!/usr/bin/env python3
"""workroom archive <room_id>

Owner-only. Mark the room archived. Archived rooms are read-only:
no new messages, no fan-out, but all history remains queryable.
This is a soft delete — it cannot be undone via this skill (a manual
PATCH /rooms/{id} with archived=false would re-open it).
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom archive", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    r = C.workroom_call("PATCH", f"/rooms/{room_id}", json={"archived": True})
    if r.status_code != 200:
        C.die(f"sc-chatroom PATCH /rooms returned {r.status_code}: {r.text}")
    C.info(f"  ✓ room {room_id} archived (read-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
