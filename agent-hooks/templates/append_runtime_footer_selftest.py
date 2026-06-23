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
        omit_cost=False, omit_tokens=False):
    ev = {"event": "on_response_end", "response": reply, "model": model}
    if not omit_cost:
        ev["turn_cost_usd"] = cost
    if not omit_tokens:
        ev["tokens"] = toks if toks is not None else {"input": 900, "output": 120}
    env = dict(os.environ)
    if template is not None:
        env["FOOTER_TEMPLATE"] = template
    else:
        env.pop("FOOTER_TEMPLATE", None)
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

# 1) Appends the real footer with true model + cost + tokens
r = run(BODY)
check("footer appended", r and "─ z-ai/glm-5.2 · $0.0211 · 900 in / 120 out" in r, repr(r))
check("body preserved verbatim", r and r.startswith(BODY), repr(r))

# 2) Does NOT remove or alter the model's own content (even a self-typed footer)
fake = f"{BODY}\n\nModel: claude-opus-4.5 | Cost: $9.99"
r = run(fake)
check("existing content untouched (no deletion)", r and "Model: claude-opus-4.5 | Cost: $9.99" in r, repr(r))
check("real footer still appended after it", r and r.rstrip().endswith("900 in / 120 out"), repr(r))

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
check("cost only: tokens show 0", r and "0 in / 0 out" in r, repr(r))

# 8) Separated from body by a blank line
r = run(BODY)
check("footer separated by blank line", r and "\n\n─ " in r, repr(r))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
