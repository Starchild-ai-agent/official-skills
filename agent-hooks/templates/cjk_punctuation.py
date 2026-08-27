#!/usr/bin/env python3
"""CJK punctuation — half-width ASCII punctuation → full-width in Chinese text.

Chinese typography wants 全角 punctuation (，；：？！), but models emit the ASCII
half-width forms (,;:?!) constantly — especially in a context saturated with
English: code, logs, identifiers, tool output. That is not a comprehension
failure the prompt can fix. The model knows the rule; punctuation is simply
chosen at token level where a single line of instruction thousands of tokens
away loses to the local distribution. Asking for it in the prompt has been
tried and it still returns half-width commas.

So this is done deterministically, after the text exists.

This script dispatches on `event` and carries two handlers:

  • on_response_end → (DEFAULT) fires ONCE per turn on the final reply: rewrite
                      CJK-adjacent ASCII punctuation to its full-width form.
  • pre_tool_call   → (OPTIONAL) same rewrite applied to prose the agent is
                      about to WRITE TO A FILE (write_file / edit_file). Wire
                      this if you ask the agent to draft Chinese copy —
                      READMEs, posts, slide text. Gated to prose extensions
                      (see PROSE_EXTENSIONS) so it can never corrupt code,
                      YAML or JSON.

Recommended wiring (workspace/config/shell_hooks.yaml):

  hooks:
    - event: on_response_end
      matcher: "[\\u4e00-\\u9fff]"        # perf gate — only spawn when the reply has CJK
      command: /data/workspace/hooks/cjk_punctuation.py
      timeout: 10
    # optional — also normalize Chinese copy written into files:
    # - event: pre_tool_call
    #   matcher: "write_file|edit_file"
    #   command: /data/workspace/hooks/cjk_punctuation.py
    #   timeout: 10

The `matcher` on on_response_end is what keeps this free: the bridge tests it
against the reply body and does not spawn the process at all when it misses, so
an English-only user pays nothing.

⚠️ KNOWN LIMIT — the live web stream. `on_response_end` rewrites the STORED and
FORWARDED reply. Characters already streamed to an open web client cannot be
unsent, so on web you may see half-width punctuation live and full-width after a
refresh. Telegram / WeChat pushes are rewritten before delivery and are correct
immediately.

What is converted, and only when a CJK character sits immediately before, or is
the next non-space character after, the mark:

    ,  →  ，        ;  →  ；        :  →  ：
    ?  →  ？        !  →  ！

A run of spaces following a converted mark is removed, because the full-width
form already carries its own trailing width (`中文, foo` → `中文，foo`).

Deliberately NOT converted:

  • `.` → `。` — a period is indistinguishable from a decimal point, a version
    number, a file extension or a domain without real parsing. Too costly to get
    wrong; left alone.
  • Parentheses — off by default (PAREN_PAIRS), because `(` and `)` need to be
    converted as a matched pair to look right, and markdown link syntax and
    inline math make naive pairing unsafe.

Never touched: fenced code blocks, inline code spans, URLs, markdown link
targets, HTML tags. Numbers keep their separators (`1,000` has no CJK
neighbour, so it is not a candidate in the first place).

Safety: never blocks, and returns the text unchanged on any error — a broken
hook can never break a turn or corrupt a file.
"""
from __future__ import annotations

import json
import os
import re
import sys

# ═══════════════════════════ CONFIG — edit your copy ═══════════════════════
# Copy this file to /data/workspace/hooks/cjk_punctuation.py and edit it THERE,
# then point your hook command at that path. Editing it inside skills/ is
# pointless — the next skill update overwrites it. Each constant can also be
# overridden by the matching env var (env wins when set).
PAREN_PAIRS = False   # True → also convert ( ) to （ ）    env CJK_PUNCT_PARENS
EAT_SPACE = True      # True → drop spaces after a mark     env CJK_PUNCT_EAT_SPACE
# Only these file extensions are rewritten on pre_tool_call. Prose only: a colon
# is load-bearing syntax in YAML/JSON and a comma is in CSV, so code and data
# files are never candidates.       env CJK_PUNCT_EXTENSIONS (comma-separated)
PROSE_EXTENSIONS = [".md", ".markdown", ".txt", ".rst"]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


PAREN_PAIRS = _env_bool("CJK_PUNCT_PARENS", PAREN_PAIRS)
EAT_SPACE = _env_bool("CJK_PUNCT_EAT_SPACE", EAT_SPACE)
if os.environ.get("CJK_PUNCT_EXTENSIONS"):
    PROSE_EXTENSIONS = [
        e if e.startswith(".") else "." + e
        for e in (x.strip() for x in os.environ["CJK_PUNCT_EXTENSIONS"].split(","))
        if e
    ]

# ═══════════════════════════ core rewrite ══════════════════════════════════
# CJK ideographs + CJK symbols/punctuation (、。「」…) + full-width forms.
# Existing full-width punctuation counts as CJK context on purpose: in
# "中文，foo, bar" the second comma sits in a Chinese sentence and should follow.
CJK_CLASS = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef"
CJK_RE = re.compile(f"[{CJK_CLASS}]")

MAP = {",": "，", ";": "；", ":": "：", "?": "？", "!": "！"}
PAREN_MAP = {"(": "（", ")": "）"}

# Spans that must survive byte-for-byte. Order matters: fenced blocks first so a
# stray backtick inside one cannot start an inline span.
PROTECTED = re.compile(
    r"```.*?```"                     # fenced code block
    r"|~~~.*?~~~"                    # alternate fence
    r"|`[^`\n]*`"                    # inline code span
    r"|<[^<>\n]+>"                   # html tag / autolink
    r"|\]\([^)\s]*\)"                # markdown link target — label stays editable
    r"|\b[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s)]+",   # bare URL
    re.S,
)


def _is_cjk(ch: str) -> bool:
    return bool(ch) and bool(CJK_RE.match(ch))


def _convert_segment(text: str) -> str:
    """Rewrite one span of ordinary prose (never a protected span)."""
    table = dict(MAP)
    if PAREN_PAIRS:
        table.update(PAREN_MAP)

    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch not in table:
            out.append(ch)
            i += 1
            continue

        # Neighbour test. "before" is the character immediately to the left —
        # no space skipping, so "foo , bar" is left alone. "after" skips spaces
        # so "PR #1117, 修复" still counts as Chinese context.
        before = text[i - 1] if i > 0 else ""
        j = i + 1
        while j < n and text[j] == " ":
            j += 1
        after = text[j] if j < n else ""

        if _is_cjk(before) or _is_cjk(after):
            out.append(table[ch])
            i = j if EAT_SPACE else i + 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def convert(text):
    """Rewrite `text`, leaving protected spans untouched. Returns (text, n_changed)."""
    if not text or not isinstance(text, str):
        return text, 0
    if not CJK_RE.search(text):
        return text, 0

    pieces = []
    last = 0
    for m in PROTECTED.finditer(text):
        pieces.append(_convert_segment(text[last:m.start()]))
        pieces.append(m.group(0))
        last = m.end()
    pieces.append(_convert_segment(text[last:]))
    out = "".join(pieces)
    return out, (0 if out == text else 1)


# ═══════════════════════════ event handlers ════════════════════════════════
# tool_input keys that carry writable prose, per tool.
CONTENT_KEYS = ("content", "new_string")


def _handle_response_end(payload):
    out, changed = convert(payload.get("response", ""))
    return {"response": out} if changed else {}


def _handle_pre_tool_call(payload):
    tool = payload.get("tool_name") or ""
    if tool not in ("write_file", "edit_file"):
        return {}
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return {}

    path = str(tool_input.get("path") or "")
    ext = os.path.splitext(path)[1].lower()
    if ext not in PROSE_EXTENSIONS:
        return {}

    patch = {}
    for key in CONTENT_KEYS:
        if isinstance(tool_input.get(key), str):
            out, changed = convert(tool_input[key])
            if changed:
                patch[key] = out
    return {"tool_input": patch} if patch else {}


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:  # noqa: BLE001
        print("{}")
        return
    try:
        event = payload.get("event", "")
        if event == "on_response_end":
            print(json.dumps(_handle_response_end(payload), ensure_ascii=False))
        elif event == "pre_tool_call":
            print(json.dumps(_handle_pre_tool_call(payload), ensure_ascii=False))
        else:
            print("{}")
    except Exception:  # noqa: BLE001 — fail open, never break a turn
        print("{}")


if __name__ == "__main__":
    main()
