#!/usr/bin/env python3
"""Tell the model NOT to type its own model/cost footer — the companion to
append_runtime_footer.py.

The footer is the runtime's job, not the model's. append_runtime_footer.py
appends a TRUE footer (─ model · $cost) built from runtime data. But once that
footer is in the chat history on every prior turn, the model's autocomplete
starts imitating it and types its own footer too — and the model CANNOT know its
real cost/model id, so that self-typed one is fabricated. Result: two footers,
one of them a lie.

You can't fix imitation by hoping; you fix it by instruction, re-injected EVERY
turn (because the tempting examples are in the history every turn too). This hook
runs on `pre_llm_call` and appends a short directive to the system prompt for
each model request:

    Do not type a model/cost/token footer yourself. The lines like
    "─ model · $cost" at the end of prior messages are appended automatically by
    the runtime after you finish — they are NOT yours to write or imitate.

Pair it with append_runtime_footer.py on `on_response_end`:
  - suppress_model_footer  (pre_llm_call)     → stop the model writing a footer
  - append_runtime_footer  (on_response_end)  → append the one true footer

Wire it in workspace/config/shell_hooks.yaml (no matcher — every turn):

  hooks:
    - event: pre_llm_call
      command: /data/workspace/hooks/suppress_model_footer.py
      timeout: 10

Override the injected text with FOOTER_SUPPRESS_TEXT if you want different
wording. Safety: pure system-prompt append, never blocks, fail-open on error.
"""
from __future__ import annotations

import json
import os
import sys

DEFAULT_TEXT = (
    "FOOTER POLICY: Do NOT end your reply with a model/cost/token footer of any "
    "kind (e.g. \"\u2500 model \u00b7 $cost\", \"Model: \u2026 | Cost: \u2026\", "
    "\"N in / N out\"). You cannot know your own per-reply cost or model id \u2014 "
    "that data exists only in the runtime, which appends the single authoritative "
    "footer automatically AFTER you finish. Any footer-like lines at the end of "
    "earlier messages in this conversation were added by that runtime, NOT by "
    "you \u2014 do not copy, continue, or imitate them. Just end with your actual "
    "content."
)


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        print("")  # no payload → inject nothing
        return
    try:
        json.loads(raw)
    except Exception:
        print("")  # malformed payload → inject nothing (fail-open)
        return

    text = os.environ.get("FOOTER_SUPPRESS_TEXT") or DEFAULT_TEXT
    print(json.dumps({"context": text}, ensure_ascii=False))


if __name__ == "__main__":
    main()
