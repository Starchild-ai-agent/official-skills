#!/usr/bin/env python3
"""workroom whois <room_id>

Single round-trip room snapshot meant for agents: who is in the room,
which of them are humans vs other agents, how many of each, and the
last N messages with crisp role attribution. Answers the questions
"how many real people are here?" and "who said what?" without having
to stitch together /members + /messages + /rooms client-side.

Hits ``GET /rooms/{id}/state`` server-side; the JSON it prints back is
the same shape the viewer sidebar consumes, so an LLM-driven agent
that learns to read it once stays consistent across UI + skill paths.

Options:
  --json              dump the raw JSON instead of the formatted view
  --recent N          fetch the last N messages (default 20, max 100)

Common patterns:
  workroom whois rm_abc123             # human-readable summary
  workroom whois rm_abc123 --json      # for pipelines / scripted parsing
  workroom whois rm_abc123 --recent 5  # cheaper, just the latest 5 lines
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys

import _common as C


def _fmt_member(m: dict, *, you: str) -> str:
    """One member row. Marks current agent with ← you, owner with [OWNER],
    flags fan-out problems (key_stale) inline so the agent immediately
    sees if a peer's delivery is broken."""
    name = m.get("user_name") or m["user_id"]
    role_class = m.get("role_class") or "unknown"
    badges = []
    if m.get("role") == "owner":
        badges.append("OWNER")
    if m.get("online"):
        badges.append("online")
    if m.get("key_stale"):
        badges.append("key_stale!")
    if m["user_id"] == you:
        badges.append("← you")
    badge_str = f"  [{', '.join(badges)}]" if badges else ""
    return f"    {name}  ({m['user_id']} / {m['member_kind']} → {role_class}){badge_str}"


def _fmt_message(m: dict) -> str:
    t = datetime.datetime.fromtimestamp(m["created_at"]).strftime("%H:%M:%S")
    who = m.get("sender_user_name") or m.get("sender_user_id") or "system"
    role = m.get("sender_role_class") or "unknown"
    role_tag = "[HUMAN]" if role == "human" else ("[AGENT]" if role == "agent" else "")
    body = (m.get("content") or "").replace("\n", " ")
    if len(body) > 100:
        body = body[:97] + "..."
    return f"    [{t}] #{m['seq']:>3} {who} {role_tag} ({m['via']}): {body}"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom whois", description=__doc__)
    p.add_argument("room_id")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="emit the raw room-state JSON (pipe-friendly)")
    p.add_argument("--recent", type=int, default=20,
                   help="how many recent messages to include (default 20, max 100)")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    recent = max(1, min(int(args.recent), 100))
    r = C.workroom_call("GET", f"/rooms/{room_id}/state?recent_limit={recent}")
    if r.status_code != 200:
        C.die(f"/rooms/{room_id}/state returned {r.status_code}: {r.text}")
    state = r.json()

    if args.as_json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0

    room = state["room"]
    counts = state["member_counts"]
    members = state["members"]
    msgs = state["recent_messages"]

    C.info(f"room {room['room_id']}  '{room.get('name') or ''}'")
    C.info(f"  owner:      {room['owner_user_id']}")
    C.info(f"  visibility: {room['visibility']}  type={room.get('room_type', 'casual')}"
           f"{'  (archived)' if room['archived'] else ''}")
    C.info("")
    C.info(f"members: {counts['total']} total · "
           f"{counts['humans']} humans ({counts['online_humans']} online) · "
           f"{counts['agents']} agents ({counts['agents_with_endpoint']} attached)")

    humans = [m for m in members if m.get("role_class") == "human"]
    agents = [m for m in members if m.get("role_class") == "agent"]
    other = [m for m in members
             if m.get("role_class") not in ("human", "agent")]
    if humans:
        C.info("  HUMANS:")
        for m in humans:
            C.info(_fmt_member(m, you=C.USER_ID))
    if agents:
        C.info("  AGENTS:")
        for m in agents:
            C.info(_fmt_member(m, you=C.USER_ID))
    if other:
        C.info("  OTHER:")
        for m in other:
            C.info(_fmt_member(m, you=C.USER_ID))

    if msgs:
        C.info("")
        C.info(f"last {len(msgs)} messages (oldest → newest):")
        for m in msgs:
            C.info(_fmt_message(m))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
