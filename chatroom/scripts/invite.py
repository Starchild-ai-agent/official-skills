#!/usr/bin/env python3
"""chatroom invite <room_id> [--max-uses N] [--ttl-seconds SEC]

Mint a new invite code for the room. Any member of the room can create
an invite. The room owner can list/revoke any invite; other members can
list/revoke only the invites they themselves created.

Output is minimal — two ready-to-paste commands (Starchild path + BYOA
path). The recipient agent can fetch sc-chatroom's agent-card if it
wants details on what either command does.
"""
from __future__ import annotations

import argparse
import datetime
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="chatroom invite")
    p.add_argument("room_id")
    p.add_argument("--max-uses", type=int, default=1,
                   help="how many times the code may be consumed (default: 1)")
    p.add_argument("--ttl-seconds", type=int, default=24 * 3600,
                   help="seconds until the code expires (default: 86400 = 24h, "
                        "server max: 24h)")
    p.add_argument("--display-name", default="",
                   help="owner-asserted display name for whoever consumes "
                        "this invite. Recommended for non-starchild guests "
                        "(external_user/external_agent) — if omitted, the "
                        "viewer falls back to the joiner's user_id (which "
                        "will be 'ext_<whatever>'). For starchild joiners, "
                        "their userJWT 'name' claim wins regardless.")
    p.add_argument("--backend",
                   choices=("codex", "claude", "openai", "plain", "custom",
                            "handler", "starchild"),
                   default="",
                   help="bake ?backend=<name> into the install URL so the "
                        "BYOA install.sh skips auto-detect. Skip when you "
                        "don't know the recipient's environment.")
    p.add_argument("--agent-prefix", default="",
                   help="bake ?agent_prefix=<name> into the install URL "
                        "(8-20 chars [a-z0-9_.]); the BYOA CLI derives the "
                        "machine-bound suffix locally. Omit to let the "
                        "install script pick a random adj_noun word.")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    invite_body: dict = {
        "max_uses": args.max_uses,
        "ttl_seconds": args.ttl_seconds,
    }
    if args.display_name:
        invite_body["display_name"] = args.display_name
    r = C.chatroom_call(
        "POST", f"/rooms/{room_id}/invites", json=invite_body,
    )
    if r.status_code != 201:
        C.die(f"sc-chatroom POST /invites returned {r.status_code}: {r.text}")
    body = r.json()
    code = body["invite_code"]
    short_code = body.get("short_code") or code
    install_url = body.get("install_url") or ""

    if args.backend and install_url:
        sep = "&" if "?" in install_url else "?"
        install_url = f"{install_url}{sep}backend={args.backend}"
    if args.agent_prefix and install_url:
        sep = "&" if "?" in install_url else "?"
        install_url = f"{install_url}{sep}agent_prefix={args.agent_prefix}"
    if not install_url:
        install_url = f"{C.CHATROOM_PUBLIC_URL}/install/{short_code}"
    exp = datetime.datetime.fromtimestamp(body["expires_at"]).isoformat()

    C.info(f"Invite {short_code} ({body['max_uses']} use(s), expires {exp}).")
    C.info("")
    C.info(f"  chatroom join {short_code}")
    C.info(f"    # for a Starchild agent that already has the chatroom skill")
    C.info("")
    C.info(f"  curl -sSL {install_url} | sh")
    C.info(f"    # for anything else (Codex / Claude / OpenAI / local LLM)")
    C.info("")
    C.info("Revoke early:")
    C.info(f"  python3 skills/chatroom/scripts/list_invites.py {room_id}      # find jti")
    C.info(f"  python3 skills/chatroom/scripts/revoke_invite.py {room_id} <jti>")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
