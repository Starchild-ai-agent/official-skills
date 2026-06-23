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

Format override (optional): set FOOTER_TEMPLATE with {model} {cost} {input}
{output} placeholders, e.g.
  FOOTER_TEMPLATE="Model: {model} | Cost: {cost} | {input} in / {output} out"

Safety: pure append, never blocks, never deletes. If the event carries no cost
data, or the reply is empty, it emits nothing (no change). Fail-open on any error
so a broken hook can never alter or break a reply.
"""
from __future__ import annotations

import json
import os
import sys

DEFAULT_TEMPLATE = "─ {model} · {cost} · {input} in / {output} out"


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


def _build_footer(ev: dict) -> str:
    model = ev.get("model") or "?"
    cost = _fmt_usd(ev.get("turn_cost_usd"))
    toks = ev.get("tokens") or {}
    tmpl = os.environ.get("FOOTER_TEMPLATE") or DEFAULT_TEMPLATE
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

    # Need a real cost source to append an honest footer; if the kernel didn't
    # supply one, append nothing (better silent than a $0.0000 lie).
    if ev.get("turn_cost_usd") is None and "tokens" not in ev:
        print("")
        return

    footer = _build_footer(ev)
    new_reply = f"{reply.rstrip()}\n\n{footer}"
    print(json.dumps({"response": new_reply}, ensure_ascii=False))


if __name__ == "__main__":
    main()
