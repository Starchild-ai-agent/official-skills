#!/usr/bin/env python3
"""Selftest for append_runtime_footer.py — feeds synthetic on_response_end
events and checks the appended footer. Run: python3 append_runtime_footer_selftest.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "append_runtime_footer.py")


def run(reply, model="z-ai/glm-5.2", cost=0.0211, toks=None, template=None,
        omit_cost=False, omit_tokens=False, show_tokens=False, env_extra=None):
    ev = {"event": "on_response_end", "response": reply, "model": model}
    if not omit_cost:
        ev["turn_cost_usd"] = cost
    if not omit_tokens:
        ev["tokens"] = toks if toks is not None else {"input": 900, "output": 120}
    env = dict(os.environ)
    for k in ("FOOTER_TEMPLATE", "FOOTER_SHOW_TOKENS", "FOOTER_STRIP"):
        env.pop(k, None)
    if template is not None:
        env["FOOTER_TEMPLATE"] = template
    if show_tokens:
        env["FOOTER_SHOW_TOKENS"] = "1"
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, SCRIPT], input=json.dumps(ev),
                       capture_output=True, text=True, env=env, timeout=15)
    out = (p.stdout or "").strip()
    return json.loads(out).get("response") if out else None


PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} — {detail}")


BODY = "Here is the answer you asked for.\nIt spans two lines."

# 1) DEFAULT: appends model + cost only, tokens HIDDEN
r = run(BODY)
check("default footer appended", r and "─ z-ai/glm-5.2 · $0.0211" in r, repr(r))
check("default hides tokens", r and "in / " not in r, repr(r))
check("body preserved verbatim", r and r.startswith(BODY), repr(r))

# 1b) FOOTER_SHOW_TOKENS=1 → tokens shown
r = run(BODY, show_tokens=True)
check("show-tokens appends token detail", r and "─ z-ai/glm-5.2 · $0.0211 · 900 in / 120 out" in r, repr(r))

# 2) [SAFETY NET] strips a model-typed footer at the END, replaces with the real one
fake = f"{BODY}\n\nModel: claude-opus-4.5 | Cost: $9.99"
r = run(fake)
check("verbose fabricated footer stripped", r and "claude-opus-4.5" not in r and "$9.99" not in r, repr(r))
check("body kept after strip", r and r.startswith(BODY), repr(r))
check("real footer appended after strip", r and r.rstrip().endswith("$0.0211"), repr(r))

# 2b) box-drawing fabricated footer (the GLM-style imitation) also stripped
fake2 = f"{BODY}\n\n─ z-ai/glm-5.2 · $7.7777"
r = run(fake2)
check("box-drawing fabricated footer stripped", r and "$7.7777" not in r, repr(r))
check("real footer replaces it (one footer)", r and r.count("─ z-ai/glm-5.2") == 1 and r.rstrip().endswith("$0.0211"), repr(r))

# 2c) multiple stacked fabricated footers all stripped
fake3 = f"{BODY}\n\n─ a · $1.0000\n\n─ b · $2.0000"
r = run(fake3)
check("stacked fabricated footers all stripped", r and "$1.0000" not in r and "$2.0000" not in r, repr(r))

# 2d) [FALSE-POSITIVE GUARD] prose with the word "model" and a "Cost:" sentence
#     in the MIDDLE of the body is NOT touched (only the trailing tail is).
prose = ("Our model pipeline is great.\nModel: see the docs for setup.\n"
         "The Cost: section explains pricing in detail below.\nFinal thoughts here.")
r = run(prose)
check("mid-body prose untouched", r and prose in r, repr(r))

# 2e) [FALSE-POSITIVE GUARD] a shell line with $VAR at the end is NOT a footer
shellish = f"Run this:\n\n    export PRICE=$VALUE  # set it"
r = run(shellish)
check("trailing shell $VAR not stripped", r and "export PRICE=$VALUE" in r, repr(r))

# 2f) FOOTER_STRIP=0 disables the safety net (append-only fallback)
fake4 = f"{BODY}\n\nModel: x | Cost: $9.99"
r = run(fake4, env_extra={"FOOTER_STRIP": "0"})
check("FOOTER_STRIP=0 keeps model footer", r and "$9.99" in r, repr(r))

# 2g) no real usage BUT a fabricated footer present → strip it, emit cleaned body
r = run(f"{BODY}\n\n─ glm-5.2 · $9.99", omit_cost=True, omit_tokens=True)
check("no usage + fake footer: cleaned", r is not None and "$9.99" not in r and r.strip() == BODY, repr(r))

# 3) Custom FOOTER_TEMPLATE honored
r = run(BODY, template="Model: {model} | Cost: {cost} | {input} in / {output} out")
check("custom template applied", r and "Model: z-ai/glm-5.2 | Cost: $0.0211 | 900 in / 120 out" in r, repr(r))

# 4) Bad custom template falls back to default (never breaks)
r = run(BODY, template="oops {nonexistent}")
check("bad template falls back", r and "─ z-ai/glm-5.2 ·" in r, repr(r))

# 5) Empty reply → no change
r = run("   ")
check("empty reply: no footer", r is None, repr(r))

# 6) No cost AND no tokens in event → append nothing (no $0.0000 lie)
r = run(BODY, omit_cost=True, omit_tokens=True)
check("no cost data: no footer", r is None, repr(r))

# 6b) [P2 REGRESSION] bridge defaults: cost=0.0 AND tokens={} explicitly
#     present (as the clawd bridge sends them) → still no footer, not $0.0000.
def run_raw(ev):
    import subprocess as _sp
    p = _sp.run([sys.executable, SCRIPT], input=json.dumps(ev),
                capture_output=True, text=True, timeout=15,
                env={k: v for k, v in os.environ.items() if k != "FOOTER_TEMPLATE"})
    out = (p.stdout or "").strip()
    return json.loads(out).get("response") if out else None

r = run_raw({"event": "on_response_end", "response": BODY, "model": "z-ai/glm-5.2",
             "turn_cost_usd": 0.0, "tokens": {}})
check("bridge zero-defaults: no footer (P2)", r is None, repr(r))

# 6c) [P2] cost=0.0 but tokens all explicitly 0 → still no footer.
r = run_raw({"event": "on_response_end", "response": BODY, "model": "z-ai/glm-5.2",
             "turn_cost_usd": 0.0,
             "tokens": {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}})
check("bridge zero tokens: no footer (P2)", r is None, repr(r))

# 6d) [P2] cost=0.0 but a positive cache_read token → real usage, DO append.
r = run_raw({"event": "on_response_end", "response": BODY, "model": "z-ai/glm-5.2",
             "turn_cost_usd": 0.0, "tokens": {"input": 0, "output": 0, "cache_read": 1500}})
check("cache-only usage: footer appended (P2)", r is not None and "─ z-ai/glm-5.2" in (r or ""), repr(r))

# 7) cost present but tokens missing → still appends (cost is the honest part)
r = run(BODY, omit_tokens=True)
check("cost only: footer appended", r and "$0.0211" in r, repr(r))
# with tokens shown, missing tokens render as 0
r = run(BODY, omit_tokens=True, show_tokens=True)
check("cost only + show-tokens: tokens show 0", r and "0 in / 0 out" in r, repr(r))

# 8) Separated from body by a blank line
r = run(BODY)
check("footer separated by blank line", r and "\n\n─ " in r, repr(r))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
