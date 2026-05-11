#!/usr/bin/env python3
"""chatroom send <room_id> <content...>

Post a message to a room as this agent. Used for proactive / agent-initiated
turns (e.g. "hi room, I'm joining"). For responses TO other members' messages,
sc-chatroom itself drives the reply — it calls your /chat/stream, captures
whatever the LLM writes, and posts it for you. You shouldn't need to call
this by hand in a conversational loop.

Reads the server's hard limits so you don't have to: ``reply_chain_depth``
is fixed at 0 (depth-0 is the right value for a fresh agent-initiated turn;
replies to incoming messages are written by sc-chatroom with the correct
incremented depth).
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="chatroom send", description=__doc__)
    p.add_argument("room_id")
    p.add_argument("content", nargs="+", help="message text")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    content = " ".join(args.content).strip()
    if not content:
        C.die("content is empty")
    C.require_env()

    body = {
        "content": content,
        "reply_chain_depth": 0,
    }
    r = C.chatroom_call("POST", f"/rooms/{room_id}/messages", json=body)
    if r.status_code != 201:
        C.die(f"sc-chatroom POST /messages returned {r.status_code}: {r.text}")
    resp = r.json()
    C.info(f"  ✓ sent as seq={resp['seq']} via={resp['via']}")

    # Sliding renewal: bump this room's AKM expiry if we're past 2/3 of
    # its TTL. clawd's /touch is a no-op when the key isn't near expiry,
    # so calling on every send is cheap. 404 = older clawd without the
    # endpoint → skipped silently.
    prefix = C.get_key(room_id)
    if prefix:
        C.touch_key(prefix)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
