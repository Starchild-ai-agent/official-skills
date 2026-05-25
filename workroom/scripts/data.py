#!/usr/bin/env python3
"""workroom data <room_id> [--edit | --show]

Read or edit the room's owner-curated reference scope — the
"what may I draw from?" text every agent in the room sees in its
prompt automatically (no per-agent file required).

Replaces the legacy per-agent local ``data.md`` (still on disk on
older agents but no longer consulted by the runtime). The
authoritative copy lives server-side at ``GET /rooms/{id}/data``;
edits are owner-only and bump a version stamp that triggers a
prompt refresh on the very next fan-out turn to every member.

Modes:
  (default) / --show   Print current content + version + author.
  --edit               Open in $EDITOR; on save, PATCH the server.

Examples:
  workroom data rm_abc123
  workroom data rm_abc123 --edit
  workroom data rm_abc123 --json   # raw payload, pipe-friendly
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

import _common as C


def _get(room_id: str) -> dict:
    r = C.workroom_call("GET", f"/rooms/{room_id}/data")
    if r.status_code != 200:
        C.die(f"GET /rooms/{room_id}/data returned {r.status_code}: {r.text}")
    return r.json()


def _patch(room_id: str, content: str) -> dict:
    r = C.workroom_call(
        "PATCH", f"/rooms/{room_id}/data",
        json={"content": content},
    )
    if r.status_code != 200:
        # 403 owner-only is the common loud case; surface it clearly so
        # non-owners don't think the field silently rejected them.
        if r.status_code == 403:
            C.die("only the room owner can edit the reference scope")
        C.die(f"PATCH /rooms/{room_id}/data returned {r.status_code}: {r.text}")
    return r.json()


def _open_editor(initial: str) -> str:
    editor = (os.environ.get("EDITOR") or "").strip() or "vi"
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".md", delete=False, encoding="utf-8",
    ) as f:
        f.write(initial)
        path = f.name
    try:
        rc = subprocess.call([editor, path])
        if rc != 0:
            C.die(f"editor {editor!r} exited with status {rc}")
        with open(path, encoding="utf-8") as f:
            return f.read()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom data", description=__doc__)
    p.add_argument("room_id")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--show", action="store_true",
                      help="(default) print current reference scope")
    mode.add_argument("--edit", action="store_true",
                      help="open in $EDITOR; saving uploads to the server")
    p.add_argument("--json", action="store_true",
                   help="emit the raw API payload as JSON (pipe-friendly)")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    cur = _get(room_id)

    if args.edit:
        new_text = _open_editor(cur.get("content") or "")
        if new_text == (cur.get("content") or ""):
            C.info("(no changes)")
            return 0
        updated = _patch(room_id, new_text)
        if args.json:
            print(json.dumps(updated, indent=2, ensure_ascii=False))
        else:
            C.info(f"  ✓ saved as v{updated['version']}")
        return 0

    # default == --show
    if args.json:
        print(json.dumps(cur, indent=2, ensure_ascii=False))
        return 0
    version = cur.get("version") or 0
    updated_by = cur.get("updated_by") or "—"
    content = cur.get("content") or ""
    C.info(f"room {room_id} reference scope (v{version}, by {updated_by})")
    C.info("─" * 60)
    if content.strip():
        C.info(content)
    else:
        C.info("(empty — owner has not set a reference scope yet)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
