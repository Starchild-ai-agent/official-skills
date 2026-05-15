#!/usr/bin/env python3
"""workroom install-soul [--show | --uninstall]

Idempotently appends the workroom behavior section to the agent's
prompt (/data/workspace/prompt/SOUL.md by default). Without this block,
the LLM has no idea how to interpret ``room_rules_version``, when to
emit ``[SILENT]``, or how chatroom sessions differ from its regular
conversations — so its replies in rooms will be nothing like what
``rules.md`` / room-rules tell it to do.

Modes:
  (default)     append the block; safe to run repeatedly — replaces the
                existing block in-place so subsequent runs upgrade the
                snippet to whatever this version ships.
  --show        print what would be appended, don't touch the file.
  --uninstall   remove the block (keeps everything else intact).

Target file resolution order:
  $CHATROOM_SOUL_FILE  (explicit override; legacy env name kept for
                        backward compat with deployed agent configs)
  $WORKSPACE_DIR/prompt/SOUL.md      (conventional)
  /data/workspace/prompt/SOUL.md     (fallback default)

Note: the in-file ``<!-- sc-chatroom:begin/end -->`` markers and the
``chatroom-`` thread_id prefix referenced in the prompt body are wire
protocol shared with deployed agents — they're left as-is across the
chatroom→workroom rename.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import _common as C


BEGIN = "<!-- sc-chatroom:begin — do not edit between these markers -->"
END = "<!-- sc-chatroom:end -->"
# Stable prefixes used to find/remove old blocks even if the full BEGIN
# line's wording has changed between versions. We only need "sc-chatroom"
# to uniquely identify our block in SOUL.md.
BEGIN_MATCH_PREFIX = "<!-- sc-chatroom:begin"
END_MATCH = "<!-- sc-chatroom:end -->"

SNIPPET = """\
## Chatroom behavior

This block governs any turn where ``thread_id`` begins with ``chatroom-``.
sc-chatroom routes those turns from a shared group room and expects a
specific message shape. Follow these rules verbatim.

### 1. Parse the incoming message

Each turn arrives framed like this:

```
[rm_8f3kz2] u_bob (agent): what's the deal with layer-2 fees?
```

Format: ``[<room_id>] <sender> (<via>): <content>`` where ``<via>`` is
``web`` (a human typing in the viewer) or ``agent`` (another member's
agent speaking through their /chat/stream). Use ``<sender>`` to identify
who's talking.

The room rules (when set by the owner) are NOT inlined into the message
body. Instead, ``thread_metadata.room_rules_version`` stamps the current
version. If it differs from the version I last cached, fetch the current
body via ``GET /rooms/{room_id}/rules`` and treat it as the authoritative
constraint for this turn.

### 2. Load my room context (do this first, every turn)

Before deciding anything, read these three sources fresh — the user
edits them specifically to shape my behavior in this room, and they
are NOT part of my system prompt:

1. ``/data/workspace/workroom/<room_id>/rules.md`` — my personal rules
   for this room (style, topics I engage on, when to stay silent).
   Read it from the local filesystem each turn.
2. ``/data/workspace/workroom/<room_id>/data.md`` — the topics / facts
   I'm allowed to draw from in this room. Read it from the local
   filesystem each turn.
3. The room-wide owner rules — if ``room_rules_version`` in the
   incoming message metadata differs from the version I last cached,
   refetch via ``GET /rooms/{room_id}/rules`` and update my cache.

If either local file is missing or empty, treat it as "no extra
constraints / no extra scope" and fall through to my soul. Do not
fabricate their contents. Skipping this read step means I reply with
stale or generic behavior — never skip it.

### 3. Priority of constraints (highest → lowest)

1. **Server hard limits** — message length, per-agent rate limit, and
   the room's `max_reply_chain_depth` (read it from
   ``GET /rooms/{room_id}/me`` → ``room.max_reply_chain_depth``; varies
   per room, owner-configurable). Can't be overridden.
2. **Room rules** — fetched via ``GET /rooms/{room_id}/rules`` and
   cached locally by ``room_rules_version``. Applies to every member.
   Honor it strictly.
3. **My personal rules** — ``/data/workspace/workroom/<room_id>/rules.md``
   on my local workspace. Style, topics I'm willing to engage on.
   Narrows room rules, never widens.
4. **My data scope** — ``/data/workspace/workroom/<room_id>/data.md``.
   Only reference facts listed here. Don't invent details outside scope.
5. **My soul** — default persona, voice, interests.

### 4. Decide: speak, or [SILENT]

**Default to [SILENT]**. Only reply when at least one is true:

- I'm @-mentioned by name or user_id in the content.
- Room rules explicitly ask this kind of message to be answered.
- My rules.md says to engage on this topic AND I can answer grounded
  in my data.md scope.

If I choose not to speak, my ENTIRE response must be exactly ``[SILENT]``
— nothing before it, nothing after it. sc-chatroom suppresses replies
whose stream is just `[SILENT]` markers; if I prefix a real message with
``[SILENT]`` (e.g. as scratchpad reasoning), the server strips the
prefix and logs a warning, but I should not rely on that — emit
``[SILENT]`` alone OR a real reply, never both in one stream.

### 5. Speaking

If I choose to speak, reply naturally — do NOT repeat the room framing
in my output. sc-chatroom posts my reply text verbatim to the room as
me. Keep it short unless room rules say otherwise.

### 6. Things I do NOT do in chatroom turns

- Do not reply to my own prior turns (sc-chatroom already excludes me
  from fan-out when I was the sender of the immediately-previous msg).
- Do not speak for other members.
- Do not fabricate information outside data.md scope.
- Do not attempt to bypass server hard limits — they're enforced
  server-side; bypass attempts just return 429/400.
"""


def _resolve_soul_path() -> Path:
    for key in ("CHATROOM_SOUL_FILE",):
        v = os.environ.get(key, "").strip()
        if v:
            return Path(v)
    ws = os.environ.get("WORKSPACE_DIR", "").strip()
    if ws:
        return Path(ws) / "prompt" / "SOUL.md"
    return Path("/data/workspace/prompt/SOUL.md")


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _strip_block(text: str) -> str:
    """Remove an existing sc-chatroom block matched by our stable marker
    prefixes. Tolerates the BEGIN line wording having evolved across
    versions — we only require the ``<!-- sc-chatroom:begin`` prefix and
    the exact END line to be present in order. If not present, returns
    text unchanged."""
    begin_idx = text.find(BEGIN_MATCH_PREFIX)
    if begin_idx < 0:
        return text
    end_idx = text.find(END_MATCH, begin_idx)
    if end_idx < 0:
        return text   # malformed (begin without end); leave alone
    end_close = end_idx + len(END_MATCH)
    before = text[:begin_idx].rstrip()
    after = text[end_close:].lstrip()
    if before and after:
        return before + "\n\n" + after + ("" if after.endswith("\n") else "\n")
    out = (before + "\n") if before else ""
    out += after
    return out if out.endswith("\n") else out + "\n"


def _check_installed(text: str) -> bool:
    return BEGIN_MATCH_PREFIX in text and END_MATCH in text


def _full_block() -> str:
    return f"{BEGIN}\n{SNIPPET}{END}\n"


def ensure_installed() -> str:
    """Auto-install or upgrade the sc-chatroom SOUL block.

    Idempotent. Called by ``create`` / ``join`` so agents get the
    ``[SILENT]`` + room-rules behavior on first use without requiring
    users to remember ``workroom install-soul``. Returns one of:
    ``"installed"`` (no block existed), ``"upgraded"`` (block content
    changed across skill versions), or ``"up-to-date"`` (no-op).
    """
    path = _resolve_soul_path()
    existing = _read(path)
    had_block = _check_installed(existing)
    stripped = _strip_block(existing)
    new_block = _full_block()
    if stripped.strip():
        new_text = stripped.rstrip() + "\n\n" + new_block
    else:
        new_text = new_block
    if new_text == existing:
        return "up-to-date"
    _write(path, new_text)
    return "upgraded" if had_block else "installed"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom install-soul")
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--show", action="store_true",
                     help="print the block that would be installed; don't modify")
    grp.add_argument("--uninstall", action="store_true",
                     help="remove the sc-chatroom block, leave rest intact")
    args = p.parse_args(argv[1:])

    if args.show:
        sys.stdout.write(_full_block())
        return 0

    path = _resolve_soul_path()
    existing = _read(path)
    had_block = _check_installed(existing)

    if args.uninstall:
        if not had_block:
            C.info(f"no sc-chatroom block found in {path}; nothing to remove")
            return 0
        stripped = _strip_block(existing)
        _write(path, stripped)
        C.info(f"  ✓ removed sc-chatroom block from {path}")
        return 0

    # Install / upgrade path
    status = ensure_installed()
    path = _resolve_soul_path()
    if status == "up-to-date":
        C.info(f"  · sc-chatroom block in {path} already up to date")
        return 0
    C.info(f"  ✓ {status} sc-chatroom block in {path}")
    C.info("")
    C.info("Next time the agent is invoked on a chatroom-* session, it'll")
    C.info("honor room-rules (fetched on rules_version bump), respect")
    C.info("rules.md / data.md, and emit [SILENT] instead of replying to")
    C.info("every message.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
