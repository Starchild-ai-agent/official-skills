#!/usr/bin/env python3
"""Runtime footer — the model/cost footer policy. Default: on_response_end only.

A model **cannot know its own per-reply cost** — and often not even its own model
id. That data lives only in the runtime. So if the model types a footer itself
(e.g. "Model: GLM-5.2 | Cost: $0.038"), the numbers are invented. And once a real
footer sits in the chat history, the model's autocomplete imitates it and types a
second, fabricated one. The footer is the runtime's job, not the model's.

This script dispatches on `event` and carries two handlers:

  • on_response_end → (DEFAULT) fires ONCE per turn on the final reply: strip any
                      model-typed footer left at the END, then append the ONE true
                      footer from runtime model + cost. This is the whole
                      guarantee — wire just this.
  • pre_llm_call    → (OPTIONAL) inject a directive: don't type your own footer,
                      don't imitate the footers in history. NOTE: pre_llm_call
                      fires before EVERY model request (N times/turn when tools
                      are used) and can't know which call is the final one, so it
                      injects the directive repeatedly. It's also redundant — the
                      on_response_end strip already removes the footer. Wire it
                      only if you want the extra nudge and accept the per-call
                      injection.

Recommended wiring (workspace/config/shell_hooks.yaml, no matcher):

  hooks:
    - event: on_response_end
      command: /data/workspace/hooks/runtime_footer.py
      timeout: 10
    # optional extra nudge (fires per model-request):
    # - event: pre_llm_call
    #   command: /data/workspace/hooks/runtime_footer.py
    #   timeout: 10

Env knobs:
  FOOTER_SHOW_TOKENS=1   show token counts (default: hidden, model + cost only)
  FOOTER_SHOW_CREDIT=1   append remaining credit balance (default: hidden). This
                         adds ONE internal HTTP call per turn to the credit API
                         (~2s timeout, fail-open: if it errors/times out the
                         balance is silently omitted and the footer still fires).
                         Off by default so a footer never costs a network round-
                         trip unless you opt in.
  FOOTER_TEMPLATE=...    custom format, {model} {cost} {input} {output} {credit}
                         (takes precedence over FOOTER_SHOW_TOKENS /
                         FOOTER_SHOW_CREDIT). {credit} renders the balance only
                         when the fetch succeeds, else an empty string.
  FOOTER_CREDIT_URL=...  override the credit-balance endpoint (default: the
                         internal credit API). Mostly for self-hosted setups and
                         tests.
  FOOTER_STRIP=0         disable the safety-net strip (pure append-only)
  FOOTER_SUPPRESS_TEXT   override the optional pre_llm_call directive

Safety: never blocks. on_response_end appends nothing when there's no real cost
data (and emits the cleaned body if it stripped a fabricated footer); pre_llm_call
injects nothing on a missing/malformed payload. Fail-open on any error so a broken
hook can never break a turn.
"""
from __future__ import annotations

import json
import os
import re
import sys

# ── shared ────────────────────────────────────────────────────────────────
DEFAULT_SUPPRESS_TEXT = (
    "FOOTER POLICY: Do NOT end your reply with a model/cost/token footer of any "
    "kind (e.g. \"\u2500 model \u00b7 $cost\", \"Model: \u2026 | Cost: \u2026\", "
    "\"N in / N out\"). You cannot know your own per-reply cost or model id \u2014 "
    "that data exists only in the runtime, which appends the single authoritative "
    "footer automatically AFTER you finish. Any footer-like lines at the end of "
    "earlier messages in this conversation were added by that runtime, NOT by "
    "you \u2014 do not copy, continue, or imitate them. Just end with your actual "
    "content."
)

# Default footer shows model + cost only. Token detail hidden unless opted in.
DEFAULT_TEMPLATE = "─ {model} · {cost}"
DEFAULT_TEMPLATE_WITH_TOKENS = "─ {model} · {cost} · {input} in / {output} out"

# Internal credit-balance endpoint. Authenticated automatically by source IPv6
# (same mechanism the `credit` tool uses) — no headers/keys needed. Reachable
# from any in-container subprocess. Only hit when FOOTER_SHOW_CREDIT is on.
CREDIT_API_URL = "http://starchild-credit-api.internal:8080/api/credits"
CREDIT_TIMEOUT_SECS = 2  # a footer must never hang the turn waiting on this

# A model-typed footer is recognised ONLY by one of these tight shapes — both
# REQUIRE a "$" then a digit, so prose with the word "model" or shell "$VAR"
# never matches. Applied ONLY to trailing lines, never the body.
_FOOTER_PATTERNS = (
    # box-drawing: "─ model · $0.0211" / "— model · $0.02 · 900 in / 120 out"
    re.compile(r"^\s*[\u2500\u2014\u2013\-]{1,4}\s.*\s[·•]\s*\$\d"),
    # verbose: "Model: claude-x | Cost: $0.04"
    re.compile(r"^\s*Model:\s.*\bCost:\s*\$?\d", re.IGNORECASE),
)


def _env_on(name: str, default: bool) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    if v == "":
        return default
    return v not in ("0", "false", "no", "off")


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


def _fmt_credit(x) -> str:
    """Balance with thousands separators + 2 decimals, e.g. '$1,234.56'."""
    try:
        return f"${float(x):,.2f}"
    except (TypeError, ValueError):
        return ""


def _fetch_credit_balance() -> str:
    """Return the formatted remaining credit (e.g. '$271.64'), or '' on any
    failure. Fail-open by design: a footer must never break or stall a turn, so
    every error path (no curl, network down, timeout, bad JSON, missing field)
    silently yields an empty string and the footer renders without a balance."""
    try:
        import subprocess
        url = os.environ.get("FOOTER_CREDIT_URL") or CREDIT_API_URL
        out = subprocess.run(
            ["curl", "-s", "-X", "GET", url],
            capture_output=True, text=True, timeout=CREDIT_TIMEOUT_SECS,
        )
        if out.returncode != 0 or not out.stdout:
            return ""
        bal = json.loads(out.stdout).get("credit_balance")
        return _fmt_credit(bal) if bal is not None else ""
    except Exception:
        return ""


# ── pre_llm_call: suppress the model from typing its own footer ─────────────
def handle_pre_llm_call(ev: dict) -> None:
    text = os.environ.get("FOOTER_SUPPRESS_TEXT") or DEFAULT_SUPPRESS_TEXT
    print(json.dumps({"context": text}, ensure_ascii=False))


# ── on_response_end: strip a fabricated footer, append the true one ─────────
def _is_footer_line(line: str) -> bool:
    return any(p.match(line) for p in _FOOTER_PATTERNS)


def _strip_trailing_footers(reply: str) -> str:
    """Drop footer-shaped lines at the very END of the reply, stopping at the
    first real content line — so a "Model: ... Cost: $5" sentence mid-body is
    never touched."""
    lines = reply.split("\n")
    while lines:
        last = lines[-1]
        if last.strip() == "" or _is_footer_line(last):
            lines.pop()
            continue
        break
    return "\n".join(lines)


def _has_usage(ev: dict) -> bool:
    """True only when the event carries real usage. The bridge defaults
    turn_cost_usd to 0.0 and tokens to {}, so require a positive cost or at least
    one positive token count before appending anything."""
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


def _build_footer(ev: dict) -> str:
    model = ev.get("model") or "?"
    cost = _fmt_usd(ev.get("turn_cost_usd"))
    toks = ev.get("tokens") or {}
    tmpl = os.environ.get("FOOTER_TEMPLATE")

    # Fetch the balance ONLY when it will actually render: a custom template that
    # references {credit}, or FOOTER_SHOW_CREDIT on a default template. This
    # keeps the extra HTTP call strictly opt-in — the default footer stays a
    # zero-network operation.
    want_credit = (bool(tmpl) and "{credit}" in tmpl) or _env_on("FOOTER_SHOW_CREDIT", False)
    credit_str = _fetch_credit_balance() if want_credit else ""

    if not tmpl:
        tmpl = DEFAULT_TEMPLATE_WITH_TOKENS if _env_on("FOOTER_SHOW_TOKENS", False) else DEFAULT_TEMPLATE
        # Append to the default footer only when the fetch succeeded, so a failed
        # lookup never leaves a dangling " · 💰 " separator.
        if _env_on("FOOTER_SHOW_CREDIT", False) and credit_str:
            tmpl = tmpl + " · 💰 {credit}"

    fmt_kwargs = dict(
        model=model, cost=cost,
        input=_fmt_int(toks.get("input")),
        output=_fmt_int(toks.get("output")),
        credit=credit_str,
    )
    try:
        return tmpl.format(**fmt_kwargs)
    except (KeyError, IndexError, ValueError):
        return DEFAULT_TEMPLATE.format(**fmt_kwargs)


def handle_on_response_end(ev: dict) -> None:
    reply = ev.get("response") or ""
    if not reply.strip():
        print("")
        return

    body = (_strip_trailing_footers(reply) if _env_on("FOOTER_STRIP", True)
            else reply.rstrip()).rstrip()

    if not _has_usage(ev):
        # No real footer to add. Emit the cleaned body only if we stripped a
        # fabricated footer; otherwise leave the reply untouched.
        if body != reply.rstrip():
            print(json.dumps({"response": body}, ensure_ascii=False))
        else:
            print("")
        return

    print(json.dumps({"response": f"{body}\n\n{_build_footer(ev)}"}, ensure_ascii=False))


# ── dispatch ───────────────────────────────────────────────────────────────
HANDLERS = {
    "pre_llm_call": handle_pre_llm_call,
    "on_response_end": handle_on_response_end,
}


def main() -> None:
    try:
        raw = sys.stdin.read()
        ev = json.loads(raw) if raw.strip() else {}
    except Exception:
        print("")  # fail-open
        return
    handler = HANDLERS.get(ev.get("event"))
    if handler is None:
        print("")  # unknown event → no-op
        return
    try:
        handler(ev)
    except Exception:
        print("")  # fail-open: a broken hook must never break a turn


if __name__ == "__main__":
    main()
