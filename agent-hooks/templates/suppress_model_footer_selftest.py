#!/usr/bin/env python3
"""Selftest for suppress_model_footer.py. Run: python3 suppress_model_footer_selftest.py"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "suppress_model_footer.py")


def run(payload, env_extra=None):
    env = dict(os.environ)
    env.pop("FOOTER_SUPPRESS_TEXT", None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, SCRIPT], input=json.dumps(payload),
                       capture_output=True, text=True, env=env, timeout=15)
    out = (p.stdout or "").strip()
    return json.loads(out) if out else None


PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  \u2713 {name}")
    else:
        FAIL += 1
        print(f"  \u2717 {name} \u2014 {detail}")


EV = {"event": "pre_llm_call", "system": "You are a helpful agent.",
      "messages": [{"role": "user", "content": "hi"}]}

# 1) Injects a context directive
r = run(EV)
check("returns context", isinstance(r, dict) and "context" in r, repr(r))
check("directive forbids footer", r and "Do NOT end your reply with a model/cost" in r["context"], repr(r))
check("directive mentions not imitating history", r and "imitate" in r["context"].lower(), repr(r))

# 2) Custom text override honored
r = run(EV, env_extra={"FOOTER_SUPPRESS_TEXT": "No footers please."})
check("custom text honored", r and r["context"] == "No footers please.", repr(r))

# 3) Empty stdin → fail-open, inject nothing
p = subprocess.run([sys.executable, SCRIPT], input="", capture_output=True, text=True, timeout=15)
check("empty stdin: no injection", (p.stdout or "").strip() == "", repr(p.stdout))

# 4) Malformed JSON → fail-open, inject nothing
p = subprocess.run([sys.executable, SCRIPT], input="{not json", capture_output=True, text=True, timeout=15)
check("bad json: no injection", (p.stdout or "").strip() == "", repr(p.stdout))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
