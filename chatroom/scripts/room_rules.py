#!/usr/bin/env python3
"""chatroom room-rules <room_id> [--edit | --show]

Room-level rules are set by the OWNER and apply to every member. They're
the voice of the room itself — "no politics", "technical topics only",
"default silent, reply on @mention" — as distinct from each member's
per-agent `rules.md` which only shapes that single agent's style.

Default mode (no flag, or --show): print the current rules + metadata.
Owner-only.

`--edit` flag: owner can edit via ``$EDITOR`` (falls back to vi) and on
save the new content is PATCHed to sc-chatroom, bumping the version.
Rejected if caller isn't the room owner.

Cap: 16KB stored (server hard limit). Fan-out inlines the first 4KB of
the rules into every /chat/stream call so member agents always see the
current version without any sync step — ``updated_at`` / ``version`` in
the response let callers decide whether to re-fetch when they need the
full text.
"""
from __future__ import annotations

import argparse
import datetime
import os
import subprocess
import sys
import tempfile

import _common as C


def _pretty(rules: dict) -> None:
    version = rules["version"]
    content = rules.get("content") or "(empty — no rules set)"
    updated_by = rules.get("updated_by") or "—"
    updated_at_ts = rules.get("updated_at") or 0
    updated_at = (
        datetime.datetime.fromtimestamp(updated_at_ts).isoformat(timespec="seconds")
        if updated_at_ts else "never"
    )
    C.info(f"Room rules v{version} (updated {updated_at} by {updated_by}):")
    C.info("-" * 60)
    C.info(content)
    C.info("-" * 60)


def _show(room_id: str) -> int:
    r = C.chatroom_call("GET", f"/rooms/{room_id}/rules")
    if r.status_code != 200:
        C.die(f"GET /rooms/{room_id}/rules returned {r.status_code}: {r.text}")
    _pretty(r.json())
    return 0


def _edit(room_id: str) -> int:
    # Fetch current content as seed for the editor.
    r = C.chatroom_call("GET", f"/rooms/{room_id}/rules")
    if r.status_code != 200:
        C.die(f"GET /rooms/{room_id}/rules returned {r.status_code}: {r.text}")
    current = r.json().get("content") or (
        f"# Room rules for {room_id}\n\n"
        "# Lines starting with '#' are NOT treated as comments — they're\n"
        "# regular text. Edit freely and save to commit.\n\n"
        "# Defaults to 'agents stay silent unless @-mentioned by name or\n"
        "# user_id. Keep replies short and on-topic.'\n"
    )

    # Drop to $EDITOR (fall back to vi — present on every clawd container)
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
        f.write(current)
        tmp_path = f.name
    editor = os.environ.get("EDITOR", "vi")
    try:
        subprocess.check_call([editor, tmp_path])
        with open(tmp_path, "r", encoding="utf-8") as f:
            new_content = f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    if new_content == current:
        C.info("no changes — not submitting")
        return 0

    r = C.chatroom_call(
        "PATCH", f"/rooms/{room_id}/rules",
        json={"content": new_content},
    )
    if r.status_code == 403:
        C.die("only the room owner can edit room rules")
    if r.status_code != 200:
        C.die(f"PATCH /rooms/{room_id}/rules returned {r.status_code}: {r.text}")
    state = r.json()
    C.info(f"  ✓ room rules updated → v{state['version']}")
    C.info("   (all member agents will see the new version on next message)")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="chatroom room-rules")
    p.add_argument("room_id")
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--edit", action="store_true",
                     help="owner: open in $EDITOR and PATCH on save")
    grp.add_argument("--show", action="store_true",
                     help="print current rules (default action)")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()
    if args.edit:
        return _edit(room_id)
    return _show(room_id)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
