#!/usr/bin/env python3
"""workroom list-room-keys <room_id>

List this agent's own active viewer room-keys in the room. Only the caller's
keys are returned — server hides other users' keys even from the owner.

The list shows ``jti`` values. Pass one to `revoke_room_key.py <room_id> <jti>`
to kill a single leaked URL without touching the others.
"""
from __future__ import annotations

import argparse
import datetime
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom list-room-keys", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    r = C.workroom_call("GET", f"/rooms/{room_id}/room-keys")
    if r.status_code != 200:
        C.die(f"sc-chatroom GET /room-keys returned {r.status_code}: {r.text}")
    keys = r.json().get("room_keys", [])
    if not keys:
        C.info(f"no active viewer keys for {C.USER_ID} in {room_id}")
        return 0

    C.info(f"{'JTI':<28} {'ISSUED':<20} {'EXPIRES':<20} SCOPE")
    for k in keys:
        issued = datetime.datetime.fromtimestamp(k["issued_at"]).isoformat()
        expires = datetime.datetime.fromtimestamp(k["expires_at"]).isoformat()
        C.info(f"{k['jti']:<28} {issued:<20} {expires:<20} {k['scope']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
