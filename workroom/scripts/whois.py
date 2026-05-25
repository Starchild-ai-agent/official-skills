#!/usr/bin/env python3
"""workroom whois <room_id> [<member_id>]

Single round-trip room snapshot meant for agents: who is in the room,
which of them are humans vs other agents, how many of each, and the
last N messages with crisp role attribution. Answers the questions
"how many real people are here?" and "who said what?" without having
to stitch together /members + /messages + /rooms client-side.

Hits ``GET /rooms/{id}/state`` server-side; the JSON it prints back is
the same shape the viewer sidebar consumes, so an LLM-driven agent
that learns to read it once stays consistent across UI + skill paths.

Positional args:
  room_id              the room to introspect (required)
  member_id            optional — narrow the formatted output to just
                       this one member's row (still fetches /state once
                       under the hood; --recent is ignored in this mode
                       so no message list is printed). Exit 1 if the
                       member is not in the room. Pairs with --json to
                       emit only that member's structured entry.

Options:
  --json              dump the raw JSON instead of the formatted view
  --recent N          fetch the last N messages (default 20, max 100;
                      ignored when member_id is supplied)

Common patterns:
  workroom whois rm_abc123              # whole-room human-readable summary
  workroom whois rm_abc123 --json       # for pipelines / scripted parsing
  workroom whois rm_abc123 --recent 5   # cheaper, just the latest 5 lines
  workroom whois rm_abc123 u_2048       # one member only
  workroom whois rm_abc123 u_2048 --json
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
    # Optional 2nd positional — filter the formatted output to a single
    # member. Kept as a plain positional (not --member) so the common
    # `whois <room> <member>` shape matches how humans talk about it
    # ("who is u_2048 in rm_abc?"). When supplied, we still fetch
    # /state once and slice the response in memory — there's no
    # per-member endpoint and adding one for one CLI use would be
    # gold-plating.
    p.add_argument("member_id", nargs="?", default=None,
                   help="optional — print only this member's row")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="emit the raw room-state JSON (pipe-friendly)")
    p.add_argument("--recent", type=int, default=20,
                   help="how many recent messages to include (default 20, max 100)")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    # When filtering to one member, recent messages aren't useful — the
    # user is asking about a person, not the conversation. Suppress
    # the message fetch to keep the response cheap and the rendered
    # output focused.
    recent = (0 if args.member_id
              else max(1, min(int(args.recent), 100)))
    qs = f"?recent_limit={recent}" if recent > 0 else "?recent_limit=1"
    r = C.workroom_call("GET", f"/rooms/{room_id}/state{qs}")
    if C.is_room_not_found_response(r):
        C.die_room_not_found(room_id)
    if r.status_code != 200:
        C.die(f"/rooms/{room_id}/state returned {r.status_code}: {r.text}")
    state = r.json()

    # Member-filter branch — exits early after rendering one row (or
    # the one-member JSON entry). Stays exit-1 on "member not in room"
    # so scripts that pipe `whois rm u_x || …` can detect missing
    # members the same way they detect missing rooms.
    if args.member_id:
        target = args.member_id.strip()
        match = next(
            (m for m in state.get("members", []) if m.get("user_id") == target),
            None,
        )
        if match is None:
            C.die(f"member {target} not found in room {room_id}")
        if args.as_json:
            print(json.dumps(match, indent=2, ensure_ascii=False))
            return 0
        C.info(f"room {room_id} · member {target}")
        C.info(_fmt_member(match, you=C.USER_ID))
        return 0

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
