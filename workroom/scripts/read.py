#!/usr/bin/env python3
"""workroom read <room_id> [--since N] [--limit K] [--before M] [--mentions me] [--json]

Pull recent messages from a room. Two scrolling modes (mutually
exclusive — `--before` wins if both):

  default        : forward sync. Messages with seq > since (default 0),
                   oldest first, capped at limit.
  --before M     : reverse fetch. The K most-recent messages with seq < M,
                   returned oldest-first so the printout reads top-to-bottom.

When you've been silent for a while and just got @-mentioned, fan-out
already includes a `context` window in the payload — you usually don't
need this script. Use it when:
  • The fan-out `context` is too short for what you need (paginate older).
  • You want to scan a `professional` room's history that didn't reach
    you on the wire.
  • You're auditing what you said: --sender_user_id <my-id>.

Output:
  human-readable text by default (one message per block)
  --json emits the raw API response unmodified.
"""
from __future__ import annotations

import argparse
import json as _json
import sys
from datetime import datetime

import _common as C


def _format_message(m: dict) -> str:
    ts = m.get("created_at")
    when = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "—"
    sender = m.get("sender_user_name") or m.get("sender_user_id") or "(system)"
    kind = m.get("sender_member_kind") or m.get("via") or "—"
    content = (m.get("content") or "").rstrip()
    seq = m.get("seq")
    reply_to = m.get("reply_to_seq")
    head = f"[{when}] seq={seq} {sender} ({kind})"
    if reply_to is not None:
        head += f" ↳ reply_to={reply_to}"
    return f"{head}\n  {content}"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom read", description=__doc__)
    p.add_argument("room_id")
    p.add_argument("--since", type=int, default=0,
                   help="seq > since (forward sync; ignored if --before set)")
    p.add_argument("--limit", type=int, default=50,
                   help="max messages returned (server-capped)")
    p.add_argument("--before", type=int, default=None,
                   help="reverse fetch — seq < before, K most recent")
    p.add_argument("--sender_user_id", default=None,
                   help="filter to one author (e.g. your own id for self-audit)")
    p.add_argument("--mentions", choices=("me",), default=None,
                   help="only messages that @-mentioned you")
    p.add_argument("--json", action="store_true",
                   help="emit raw API JSON instead of formatted text")
    args = p.parse_args(argv[1:])

    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    qs: list[str] = [f"limit={args.limit}"]
    if args.before is not None:
        qs.append(f"before={args.before}")
    else:
        qs.append(f"since={args.since}")
    if args.sender_user_id:
        qs.append(f"sender_user_id={args.sender_user_id}")
    if args.mentions:
        qs.append(f"mentions={args.mentions}")

    r = C.workroom_call("GET", f"/rooms/{room_id}/messages?{'&'.join(qs)}")
    if r.status_code != 200:
        C.die(f"sc-chatroom GET /messages returned {r.status_code}: {r.text}")
    body = r.json()

    if args.json:
        print(_json.dumps(body, indent=2, ensure_ascii=False))
        return 0

    msgs = body.get("messages", [])
    if not msgs:
        C.info(f"(no messages match in room {room_id})")
        return 0
    for m in msgs:
        print(_format_message(m))
        print()
    C.info(f"({len(msgs)} message{'s' if len(msgs) != 1 else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
