#!/usr/bin/env python3
"""workroom rotate-key <room_id>

Rotates the AKM key for one room without leaving:
  1. POST /api/keys/<prefix>/rotate  → new secret, old one dead immediately
  2. PUT sc-chatroom/rooms/<id>/members/<USER_ID>/endpoint  → upload new key
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom rotate-key", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    prefix = C.get_key(room_id)
    if not prefix:
        C.die(f"no AKM key on record for {room_id}; run `workroom join` first")

    # 1. Rotate locally
    r = C.clawd_call("POST", f"/api/keys/{prefix}/rotate")
    if r.status_code != 200:
        C.die(f"clawd /keys/{prefix}/rotate returned {r.status_code}: {r.text}")
    resp = r.json()
    new_secret = resp["secret"]
    new_prefix = resp["key"]["prefix"]
    C.info(f"  ✓ rotated: {prefix} → {new_prefix}")

    # 2. Upload new key to sc-chatroom
    r = C.workroom_call(
        "PUT", f"/rooms/{room_id}/members/{C.USER_ID}/endpoint",
        json={"akm_key": new_secret},
    )
    if r.status_code != 200:
        C.die(
            f"sc-chatroom PUT /members/.../endpoint returned {r.status_code}: "
            f"{r.text}  (the new AKM key exists locally but isn't uploaded; "
            f"run this command again or the server will treat the member as stale)"
        )
    C.set_key(room_id, new_prefix)
    C.info(f"  ✓ sc-chatroom updated; fan-out will use new key on next message")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
