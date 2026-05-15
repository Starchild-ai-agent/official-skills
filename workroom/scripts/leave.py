#!/usr/bin/env python3
"""workroom leave <room_id>

Revokes the local AKM key for the room (so sc-chatroom immediately fails
any further fan-out with 401), then removes membership server-side.
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom leave", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    # 1. Revoke the AKM key first so any in-flight fan-out fails before we
    #    disappear server-side (optional — server will drop member row anyway).
    prefix = C.pop_key(room_id)
    if prefix:
        r = C.clawd_call("DELETE", f"/api/keys/{prefix}")
        if r.status_code in (200, 404):
            C.info(f"  ✓ local AKM key revoked ({prefix}…)")
        else:
            C.info(f"  ! clawd /api/keys DELETE returned {r.status_code}: {r.text}")
    else:
        C.info(f"  · no local AKM key recorded for {room_id}")

    # 2. Remove membership
    r = C.workroom_call("DELETE", f"/rooms/{room_id}/members/{C.USER_ID}")
    if r.status_code == 200:
        C.info(f"  ✓ left room {room_id}")
    elif r.status_code == 404:
        C.info(f"  · not a member of {room_id} anyway")
    else:
        C.die(f"sc-chatroom DELETE /members returned {r.status_code}: {r.text}")

    ws = C.room_workspace_dir(room_id)
    if ws.exists():
        C.info(f"  · workspace at {ws} left intact (delete manually to forget)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
