#!/usr/bin/env python3
"""Selftest for strip_fabricated_footer.py — feeds synthetic on_response_end
events and checks the rewrite. Run: python3 strip_fabricated_footer_selftest.py

No external state touched; everything is in-memory via subprocess stdin.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "strip_fabricated_footer.py")


def run(reply, mode=None, model="z-ai/glm-5.2", cost=0.038, toks=None):
    ev = {
        "event": "on_response_end",
        "response": reply,
        "model": model,
        "turn_cost_usd": cost,
        "tokens": toks or {"input": 1240, "output": 380},
    }
    env = dict(os.environ)
    if mode:
        env["FOOTER_MODE"] = mode
    else:
        env.pop("FOOTER_MODE", None)
    p = subprocess.run(
        [sys.executable, SCRIPT], input=json.dumps(ev),
        capture_output=True, text=True, env=env, timeout=15,
    )
    out = (p.stdout or "").strip()
    if not out:
        return None  # continue / no change
    return json.loads(out).get("response")


PASS, FAIL = 0, 0


def check(name, got, want_contains=None, want_absent=None, want_nochange=None, original=None):
    global PASS, FAIL
    ok = True
    detail = ""
    if want_nochange is not None:
        # expect no rewrite (None) OR identical to original
        if not (got is None or got == original):
            ok, detail = False, f"expected no change, got: {got!r}"
    if want_contains is not None:
        body = got or ""
        if want_contains not in body:
            ok, detail = False, f"missing {want_contains!r} in {body!r}"
    if want_absent is not None:
        body = got if got is not None else (original or "")
        if want_absent in body:
            ok, detail = False, f"should have removed {want_absent!r}; got {body!r}"
    if ok:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} — {detail}")


BODY = "Here is the answer you asked for.\nIt spans two lines."

# 1) The exact real-world case: "Model: GLM-5.2 | Cost: $0.038"
r = run(f"{BODY}\n\nModel: GLM-5.2 | Cost: $0.038")
check("pipe footer removed", r, want_contains="two lines.", want_absent="Cost: $0.038")
check("pipe footer: body intact", r, want_contains="Here is the answer")

# 2) Footer with a leading separator line ("---\nModel: ...")
r = run(f"{BODY}\n\n---\nModel: claude-opus-4.5 | Cost: $0.12")
check("separator + footer removed", r, want_absent="Model: claude-opus-4.5")
check("separator line also gone", r, want_absent="---")

# 3) Model-only footer (no cost)
r = run(f"{BODY}\n\nModel: claude-opus-4.5")
check("model-only footer removed", r, want_absent="Model: claude-opus")

# 4) Runtime-mimic footer the model imitated
r = run(f"{BODY}\n\n─ glm-5.2 · $0.0123 · 1,240 in / 380 out")
check("runtime-mimic footer removed", r, want_absent="$0.0123")

# 5) "Session cost" + token footer variant
r = run(f"{BODY}\n\nSession cost: $0.81 · 1,240 in / 380 out")
check("session-cost footer removed", r, want_absent="Session cost")

# 6) FOOTER_MODE=real → strip fake, append REAL numbers from the event
r = run(f"{BODY}\n\nModel: GLM-5.2 | Cost: $0.038", mode="real",
        model="z-ai/glm-5.2", cost=0.0211, toks={"input": 900, "output": 120})
check("real mode: fake cost gone", r, want_absent="0.038")
check("real mode: true cost present", r, want_contains="$0.0211")
check("real mode: true model present", r, want_contains="z-ai/glm-5.2")
check("real mode: true tokens present", r, want_contains="900 in / 120 out")

# 7) FALSE-POSITIVE GUARD: reply with no footer must be untouched
plain = "Just a normal reply.\nNo footer here at all."
r = run(plain)
check("no footer: no change", r, want_nochange=True, original=plain)

# 8) FALSE-POSITIVE GUARD: a trailing separator with NO footer line stays
sep_only = "Some content.\n\n---"
r = run(sep_only)
check("bare separator kept", r, want_nochange=True, original=sep_only)

# 9) FALSE-POSITIVE GUARD: 'model' as ordinary prose must NOT be stripped
prose = "The model you chose is great.\nLet me know if you want to switch."
r = run(prose)
check("prose mentioning 'model' kept", r, want_nochange=True, original=prose)

# 10) FALSE-POSITIVE GUARD: a code block line with $ must not trigger mimic
code = "Run this:\n\n    echo $PATH"
r = run(code)
check("shell $VAR line kept", r, want_nochange=True, original=code)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
