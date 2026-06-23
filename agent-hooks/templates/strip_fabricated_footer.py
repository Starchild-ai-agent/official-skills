#!/usr/bin/env python3
"""Strip a model-typed "Model: … | Cost: …" footer the agent invented.

The problem: a model CANNOT know its own per-reply cost — and often not even its
own model id. That data lives only in the runtime. Yet some agents append a line
like::

    Model: GLM-5.2 | Cost: $0.038

at the end of every reply, pattern-matching a footer format from memory. The
numbers (and sometimes the model name) are fabricated. Worse, once the footer is
in the agent's own context on every turn, autocomplete locks it in — a one-line
"I'll stop" never wins against dozens of self-reinforcing examples. You can't fix
this by asking the model to behave; you fix it structurally, here.

What this hook does, once per turn, on the assembled reply:
  1. Detect a TRAILING footer block that looks self-typed (model / cost / token
     lines, with their separators), and remove it.
  2. Depending on FOOTER_MODE, either leave no footer (default) or re-append the
     REAL runtime footer built from the kernel-supplied model + turn_cost_usd +
     tokens — true numbers, model out of the loop.

Wire it on on_response_end (the once-per-turn finalize that can rewrite the
reply). Copy into workspace/config/shell_hooks.yaml:

  hooks:
    - event: on_response_end
      # perf gate: only run when a footer-ish line is present
      matcher: "Model:|Cost:|💰|· \\$|\\$[0-9].*(in|out|tokens)"
      command: ./extensions/shell_hooks/examples/strip_fabricated_footer.py
      timeout: 10

Modes (env var FOOTER_MODE, read at run time):
  - "strip"  (default) — remove the fabricated footer, append nothing. Use when
    the agent should NOT show a footer at all.
  - "real"   — remove the fabricated footer, then append the real runtime footer
    `─ <model> · $<cost> · <in> in / <out> out`. Use when you WANT a footer but
    with true numbers.

  ⚠ If FOOTER_MODE=real, do NOT also enable the `turn_footer` extension
  (STARCHILD_TURN_FOOTER=1) — both append a real footer and you'd get two. Pick
  one path. With the default "strip" mode you can safely pair this hook with
  turn_footer (or Telegram's tg_show_usage): this hook removes the model's fake
  footer, the runtime appends the true one.

Safety: pure text rewrite, never blocks. Strips ONLY a trailing block that
contains at least one real footer line — a plain `---` separator with no footer
underneath is left untouched. On any error it emits nothing (continue), so a
broken hook can never alter or break a reply.
"""
from __future__ import annotations

import json
import os
import re
import sys

# ── A single line that is clearly a self-typed usage/cost/model footer ───────
# Each alternative is anchored to the line start (after optional separator/
# bullet glyphs) and carries a cost / model / token signal, so ordinary prose
# never matches.
FOOTER_LINE_RX = re.compile(
    r"""^\s*(?:[-─—*•·]+\s*)?(?:
        Model\s*[:：]                              # "Model: ..."  (dominant case)
      | Cost\s*[:：]\s*\$?\s*[\d.]                  # "Cost: $0.038"
      | (?:Session\s+cost|Tokens?|Usage)\s*[:：]    # "Session cost: ...", "Tokens: ..."
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Runtime-footer MIMIC: a line led by a dash/bullet that carries a $-amount,
# e.g. "─ glm-5.2 · $0.0123 · 1,240 in / 380 out" or "- Cost $0.04".
FOOTER_MIMIC_RX = re.compile(r"^\s*[-─—*•]+\s*\S.*\$\s*[\d.]", re.IGNORECASE)

# A bare token/cost line with no leading glyph: "1,240 in / 380 out",
# "$0.038 · 1.2k in / 380 out", "💰 $0.04".
FOOTER_BARE_RX = re.compile(
    r"""^\s*(?:
        💰
      | \$\s*[\d.]+ \s* (?:USD)? \s* [·|].*\b(?:in|out|tokens?)\b   # "$0.04 · 1.2k in / .."
      | [\d,]+\s*(?:in|tokens?)\b.*\bout\b                          # "1,240 in / 380 out"
    )\s*$""",
    re.IGNORECASE | re.VERBOSE,
)

SEPARATOR_RX = re.compile(r"^\s*[-─—*=_~]{2,}\s*$")


def _is_footer_line(line: str) -> bool:
    return bool(
        FOOTER_LINE_RX.search(line)
        or FOOTER_MIMIC_RX.search(line)
        or FOOTER_BARE_RX.search(line)
    )


def _is_skippable(line: str) -> bool:
    """Part of a footer block we may absorb: footer line, separator, or blank."""
    return _is_footer_line(line) or SEPARATOR_RX.match(line) is not None or line.strip() == ""


def strip_footer(reply: str) -> str:
    """Return reply with a trailing self-typed footer block removed.

    Walks up from the bottom over footer/separator/blank lines; if that trailing
    block contains at least one real FOOTER line, the whole block (incl. its
    leading separator) is dropped. Otherwise the reply is returned unchanged.
    """
    if not reply:
        return reply
    lines = reply.split("\n")
    j = len(lines)
    while j > 0 and _is_skippable(lines[j - 1]):
        j -= 1
    suffix = lines[j:]
    if not any(_is_footer_line(l) for l in suffix):
        return reply  # no genuine footer at the tail — leave it alone
    return "\n".join(lines[:j]).rstrip()


def _fmt_usd(x) -> str:
    try:
        return f"${float(x):.4f}"
    except (TypeError, ValueError):
        return "$0.0000"


def _fmt_int(x) -> str:
    try:
        return f"{int(x):,}"
    except (TypeError, ValueError):
        return "0"


def _real_footer(ev: dict) -> str:
    """Build the true runtime footer from the kernel-supplied event fields."""
    model = ev.get("model") or "?"
    cost = _fmt_usd(ev.get("turn_cost_usd"))
    toks = ev.get("tokens") or {}
    return (
        f"─ {model} · {cost} · "
        f"{_fmt_int(toks.get('input'))} in / {_fmt_int(toks.get('output'))} out"
    )


def main() -> None:
    try:
        raw = sys.stdin.read()
        ev = json.loads(raw) if raw.strip() else {}
    except Exception:
        print("")  # fail-open: no change
        return

    reply = ev.get("response") or ""
    if not reply.strip():
        print("")
        return

    stripped = strip_footer(reply)

    mode = (os.environ.get("FOOTER_MODE") or "strip").strip().lower()
    if mode == "real":
        stripped = f"{stripped.rstrip()}\n\n{_real_footer(ev)}"

    # Only emit a rewrite if we actually changed something.
    if stripped == reply:
        print("")
        return
    print(json.dumps({"response": stripped}, ensure_ascii=False))


if __name__ == "__main__":
    main()
