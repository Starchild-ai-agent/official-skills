#!/usr/bin/env python3
"""Append a TRUE model + cost footer to every reply — the runtime knows, the
model doesn't.

Why this exists: a model **cannot know its own per-reply cost** — and often not
even its own model id. That data lives only in the runtime. If the model types a
footer itself (e.g. "Model: GLM-5.2 | Cost: $0.038"), the numbers are invented.

This hook does ONE thing: on `on_response_end` it appends a footer built from the
kernel-supplied `model` + `turn_cost_usd` + `tokens` — real values, every time:

    ... the assistant's reply ...

    ─ z-ai/glm-5.2 · $0.0211 · 900 in / 120 out

It does NOT remove or rewrite any of the model's own content. The right way to
stop a model from typing its own (fabricated) footer is to tell it not to in its
prompt / SOUL — the model controls what it generates, this hook controls the
single trustworthy footer that gets appended after.

Wire it on on_response_end (the once-per-turn finalize that can rewrite the
reply). Copy into workspace/config/shell_hooks.yaml — no matcher needed, it
should run every turn:

  hooks:
    - event: on_response_end
      command: /data/workspace/hooks/append_runtime_footer.py
      timeout: 10

By default the footer shows model + cost only, e.g.

    ─ z-ai/glm-5.2 · $0.0211

Token detail is HIDDEN by default. To show it, set FOOTER_SHOW_TOKENS=1:

    ─ z-ai/glm-5.2 · $0.0211 · 900 in / 120 out

Format override (optional): set FOOTER_TEMPLATE with {model} {cost} {input}
{output} placeholders (takes precedence over FOOTER_SHOW_TOKENS), e.g.
  FOOTER_TEMPLATE="Model: {model} | Cost: {cost} | {input} in / {output} out"

Safety net (FOOTER_STRIP, on by default): before appending, it removes any
model-typed footer the model emitted at the very END of the reply — recognised
only by a tight shape (a box-drawing "─ … · $N" line, or "Model: … Cost: $N"),
matched ONLY on trailing lines so the body is never touched. Set FOOTER_STRIP=0
to disable and fall back to pure-append. Companion suppress_model_footer.py
(pre_llm_call) stops the model writing one in the first place; this catches the
leftovers.

Safety: never blocks. If the event carries no cost data and nothing was stripped,
it emits nothing (no change); if a fabricated footer was stripped, it emits the
cleaned body even with no real footer to add. Fail-open on any error so a broken
hook can never break a reply.
"""
from __future__ import annotations

import json
import os
import re
import sys

# A model-typed footer is recognised ONLY when it matches one of these tight
# shapes — both REQUIRE a "$" followed by a digit, so prose containing the word
# "model" or shell "$VAR" never matches. Anchored per-line; applied ONLY to
# trailing lines (see _strip_trailing_footers), never the body.
_FOOTER_PATTERNS = (
    # box-drawing style: "─ model · $0.0211" / "— model · $0.02 · 900 in / 120 out"
    re.compile(r"^\s*[\u2500\u2014\u2013\-]{1,4}\s.*\s[·•]\s*\$\d"),
    # verbose style: "Model: claude-x | Cost: $0.04" / "Model: x · Cost: 0.04"
    re.compile(r"^\s*Model:\s.*\bCost:\s*\$?\d", re.IGNORECASE),
)


def _is_footer_line(line: str) -> bool:
    return any(p.match(line) for p in _FOOTER_PATTERNS)


def _strip_enabled() -> bool:
    # On by default; set FOOTER_STRIP=0 to disable the safety-net removal.
    return (os.environ.get("FOOTER_STRIP") or "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


def _strip_trailing_footers(reply: str) -> str:
    """Remove model-typed footer lines that appear at the very END of the reply.

    Walks lines from the bottom: drops trailing blank lines and any footer-shaped
    line, and STOPS at the first real content line. Only the tail is ever
    touched — a "Model: ... Cost: $5" sentence in the middle of the body is left
    untouched because we never look past the first non-footer line from the end.
    """
    lines = reply.split("\n")
    while lines:
        last = lines[-1]
        if last.strip() == "" or _is_footer_line(last):
            lines.pop()
            continue
        break
    return "\n".join(lines)

# Default footer shows model + cost only. Token detail is hidden unless the user
# opts in with FOOTER_SHOW_TOKENS=1 (or a custom FOOTER_TEMPLATE with token
# placeholders).
DEFAULT_TEMPLATE = "─ {model} · {cost}"
DEFAULT_TEMPLATE_WITH_TOKENS = "─ {model} · {cost} · {input} in / {output} out"


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


def _has_usage(ev: dict) -> bool:
    """True only when the event carries real usage to report.

    The bridge defaults turn_cost_usd to 0.0 and tokens to {}, so a turn with no
    usage attached looks like a $0 turn. Require either a positive cost or at
    least one positive token count before we append anything.
    """
    try:
        cost = float(ev.get("turn_cost_usd") or 0.0)
    except (TypeError, ValueError):
        cost = 0.0
    if cost > 0:
        return True
    toks = ev.get("tokens") or {}
    for key in ("input", "output", "cache_read", "cache_creation"):
        try:
            if int(toks.get(key) or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _show_tokens() -> bool:
    return (os.environ.get("FOOTER_SHOW_TOKENS") or "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _build_footer(ev: dict) -> str:
    model = ev.get("model") or "?"
    cost = _fmt_usd(ev.get("turn_cost_usd"))
    toks = ev.get("tokens") or {}
    # Precedence: explicit FOOTER_TEMPLATE > FOOTER_SHOW_TOKENS > default (cost only)
    tmpl = os.environ.get("FOOTER_TEMPLATE")
    if not tmpl:
        tmpl = DEFAULT_TEMPLATE_WITH_TOKENS if _show_tokens() else DEFAULT_TEMPLATE
    try:
        return tmpl.format(
            model=model,
            cost=cost,
            input=_fmt_int(toks.get("input")),
            output=_fmt_int(toks.get("output")),
        )
    except (KeyError, IndexError, ValueError):
        # bad custom template → fall back to the default rather than break
        return DEFAULT_TEMPLATE.format(
            model=model,
            cost=cost,
            input=_fmt_int(toks.get("input")),
            output=_fmt_int(toks.get("output")),
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

    # Safety net: strip any model-typed footer the model emitted at the END of
    # the reply (it can't know real cost/model id, so a self-typed footer is
    # fabricated). Companion suppress_model_footer.py tells the model not to write
    # one; this catches the cases where it does anyway. Narrow + tail-only, so the
    # body is never touched.
    body = _strip_trailing_footers(reply) if _strip_enabled() else reply.rstrip()
    body = body.rstrip()

    # Need a real cost source to append an honest footer. The clawd shell-hook
    # bridge ALWAYS sends turn_cost_usd (defaulting to 0.0) and tokens (default
    # {}), so a `is None` check never fires — instead treat "cost <= 0 AND no
    # positive token count" as missing data and append nothing. Otherwise a turn
    # with no usage attached would render "$0.0000 · 0 in / 0 out", disguising
    # missing data as a real zero-cost turn.
    if not _has_usage(ev):
        # No real footer to add. If we stripped a fabricated one, emit the
        # cleaned body; otherwise leave the reply untouched.
        if body != reply.rstrip():
            print(json.dumps({"response": body}, ensure_ascii=False))
        else:
            print("")
        return

    footer = _build_footer(ev)
    new_reply = f"{body}\n\n{footer}"
    print(json.dumps({"response": new_reply}, ensure_ascii=False))


if __name__ == "__main__":
    main()
