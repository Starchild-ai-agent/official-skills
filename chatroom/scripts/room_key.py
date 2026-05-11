#!/usr/bin/env python3
"""chatroom room-key <room_id> [--rotate] [--revoke-first]

Mint a short-lived viewer URL for the user (not the agent).

Flags:
  --rotate       First revoke all of THIS AGENT's existing active room-keys
                 for the room, then mint a fresh one. Use when a URL was
                 sent to the wrong person or may be compromised.
  --revoke-first Alias of --rotate (same behavior).

Per server policy an agent can only sign a key for its own user_id. Server
enforces a hard cap of 3 active keys per user per room. If hit, use
--rotate to clear the slate.
"""
from __future__ import annotations

import argparse
import datetime
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="chatroom room-key")
    p.add_argument("room_id")
    p.add_argument("--rotate", "--revoke-first", action="store_true",
                   dest="rotate",
                   help="revoke all existing room-keys for this user+room "
                        "before minting a fresh one")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    if args.rotate:
        r = C.chatroom_call("DELETE", f"/rooms/{room_id}/room-keys")
        if r.status_code != 200:
            C.die(f"DELETE /room-keys returned {r.status_code}: {r.text}")
        n = r.json().get("revoked", 0)
        C.info(f"  ✓ revoked {n} previous room-key(s) for this user")

    r = C.chatroom_call(
        "POST", f"/rooms/{room_id}/room-keys",
        json={"for_user_id": C.USER_ID},
    )
    if r.status_code != 201:
        C.die(f"POST /room-keys returned {r.status_code}: {r.text}")
    body = r.json()
    exp = datetime.datetime.fromtimestamp(body["expires_at"])
    C.info("Room key minted. Share this URL with your user:")
    C.info("")
    C.info(f"  {body['viewer_url']}")
    C.info("")
    C.info(f"  expires: {exp.isoformat()}")
    C.info(f"  scope:   {body['scope']}")
    if body.get("code"):
        C.info(f"  code:    {body['code']}  (server-resolves to the JWT; "
               "kill with `chatroom revoke-room-key {room_id} --code …`)")
    if body.get("direct_url"):
        C.info("")
        C.info("(If a script needs the JWT inline rather than the short")
        C.info(" URL, the legacy direct form is:)")
        C.info(f"  {body['direct_url']}")
    if args.rotate:
        C.info("")
        C.info("(The previous URL is now invalid — share the new one only.)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
