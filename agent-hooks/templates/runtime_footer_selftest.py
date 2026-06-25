#!/usr/bin/env python3
"""Selftest for runtime_footer.py (one script, two events).
Run: python3 runtime_footer_selftest.py"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "runtime_footer.py")

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  \u2713 {name}")
    else:
        FAIL += 1
        print(f"  \u2717 {name} \u2014 {detail}")


def _run(ev, env_extra=None):
    env = dict(os.environ)
    for k in ("FOOTER_TEMPLATE", "FOOTER_SHOW_TOKENS", "FOOTER_STRIP",
              "FOOTER_SUPPRESS_TEXT", "FOOTER_SHOW_CREDIT", "FOOTER_CREDIT_URL"):
        env.pop(k, None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, SCRIPT], input=json.dumps(ev),
                       capture_output=True, text=True, env=env, timeout=15)
    out = (p.stdout or "").strip()
    return json.loads(out) if out else None


def resp(reply, model="z-ai/glm-5.2", cost=0.0211, toks=None, omit_cost=False,
         omit_tokens=False, env_extra=None):
    ev = {"event": "on_response_end", "response": reply, "model": model}
    if not omit_cost:
        ev["turn_cost_usd"] = cost
    if not omit_tokens:
        ev["tokens"] = toks if toks is not None else {"input": 900, "output": 120}
    r = _run(ev, env_extra)
    return r.get("response") if r else None


BODY = "Here is the answer you asked for.\nIt spans two lines."

# ── pre_llm_call (suppression) ──────────────────────────────────────────────
PRE = {"event": "pre_llm_call", "system": "You are helpful.", "messages": [{"role": "user", "content": "hi"}]}
r = _run(PRE)
check("pre_llm_call returns context", isinstance(r, dict) and "context" in r, repr(r))
check("directive forbids footer", r and "Do NOT end your reply with a model/cost" in r["context"], repr(r))
check("directive says don't imitate history", r and "imitate" in r["context"].lower(), repr(r))
r = _run(PRE, env_extra={"FOOTER_SUPPRESS_TEXT": "No footers."})
check("custom suppress text honored", r and r["context"] == "No footers.", repr(r))

# ── on_response_end (strip + append) ────────────────────────────────────────
# default: model + cost only, tokens hidden
r = resp(BODY)
check("default footer appended", r and "─ z-ai/glm-5.2 · $0.0211" in r, repr(r))
check("default hides tokens", r and "in / " not in r, repr(r))
check("body preserved verbatim", r and r.startswith(BODY), repr(r))

# show tokens opt-in
r = resp(BODY, env_extra={"FOOTER_SHOW_TOKENS": "1"})
check("show-tokens appends detail", r and "─ z-ai/glm-5.2 · $0.0211 · 900 in / 120 out" in r, repr(r))

# strip a verbose fabricated footer at the end
r = resp(f"{BODY}\n\nModel: claude-opus-4.5 | Cost: $9.99")
check("verbose fabricated footer stripped", r and "claude-opus-4.5" not in r and "$9.99" not in r, repr(r))
check("real footer replaces it", r and r.rstrip().endswith("$0.0211"), repr(r))

# strip a box-drawing fabricated footer (GLM-style imitation)
r = resp(f"{BODY}\n\n─ z-ai/glm-5.2 · $7.7777")
check("box fabricated footer stripped", r and "$7.7777" not in r, repr(r))
check("exactly one footer remains", r and r.count("─ z-ai/glm-5.2") == 1 and r.rstrip().endswith("$0.0211"), repr(r))

# stacked fabricated footers
r = resp(f"{BODY}\n\n─ a · $1.0000\n\n─ b · $2.0000")
check("stacked footers all stripped", r and "$1.0000" not in r and "$2.0000" not in r, repr(r))

# FALSE-POSITIVE GUARDS
prose = ("Our model pipeline is great.\nModel: see the docs for setup.\n"
         "The Cost: section explains pricing in detail below.\nFinal thoughts here.")
r = resp(prose)
check("mid-body prose untouched", r and prose in r, repr(r))
r = resp("Run this:\n\n    export PRICE=$VALUE  # set it")
check("trailing shell $VAR not stripped", r and "export PRICE=$VALUE" in r, repr(r))

# FOOTER_STRIP=0 disables strip
r = resp(f"{BODY}\n\nModel: x | Cost: $9.99", env_extra={"FOOTER_STRIP": "0"})
check("FOOTER_STRIP=0 keeps model footer", r and "$9.99" in r, repr(r))

# custom template
r = resp(BODY, env_extra={"FOOTER_TEMPLATE": "Model: {model} | Cost: {cost} | {input} in / {output} out"})
check("custom template applied", r and "Model: z-ai/glm-5.2 | Cost: $0.0211 | 900 in / 120 out" in r, repr(r))

# no usage, clean reply → no change
r = resp(BODY, omit_cost=True, omit_tokens=True)
check("no usage + clean: no change", r is None, repr(r))
# no usage but fabricated footer present → strip, emit cleaned body
r = resp(f"{BODY}\n\n─ glm-5.2 · $9.99", omit_cost=True, omit_tokens=True)
check("no usage + fake footer: cleaned", r is not None and "$9.99" not in r and r.strip() == BODY, repr(r))

# bridge zero-defaults → no footer
r = _run({"event": "on_response_end", "response": BODY, "model": "z-ai/glm-5.2",
          "turn_cost_usd": 0.0, "tokens": {}})
check("bridge zero-defaults: no footer", r is None, repr(r))
# cache-only usage → append
r = resp(BODY, toks={"input": 0, "output": 0, "cache_read": 1500})
check("cache-only usage: footer appended", r and "─ z-ai/glm-5.2" in r, repr(r))

# ── credit balance (FOOTER_SHOW_CREDIT / {credit}) ──────────────────────────
# A file:// URL is a deterministic, network-free stand-in for the credit API:
# curl reads the file and returns its JSON, exactly like the real endpoint.
import tempfile
_stub = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
_stub.write('{"credit_balance": 271.64}')
_stub.close()
STUB_URL = f"file://{_stub.name}"
BROKEN_URL = "http://127.0.0.1:1/nope"  # connection refused → fail-open

# default footer never fetches/shows credit
r = resp(BODY)
check("credit off by default", r and "💰" not in r, repr(r))

# FOOTER_SHOW_CREDIT=1 appends the balance to the default footer
r = resp(BODY, env_extra={"FOOTER_SHOW_CREDIT": "1", "FOOTER_CREDIT_URL": STUB_URL})
check("show-credit appends balance", r and r.rstrip().endswith("💰 $271.64"), repr(r))
check("credit keeps model+cost", r and "─ z-ai/glm-5.2 · $0.0211" in r, repr(r))

# fail-open: unreachable endpoint → footer still fires, no balance, no dangling sep
r = resp(BODY, env_extra={"FOOTER_SHOW_CREDIT": "1", "FOOTER_CREDIT_URL": BROKEN_URL})
check("credit fail-open: footer intact", r and r.rstrip().endswith("$0.0211"), repr(r))
check("credit fail-open: no emoji", r and "💰" not in r, repr(r))

# custom template {credit} renders the balance
r = resp(BODY, env_extra={"FOOTER_TEMPLATE": "{model} · {cost} · bal {credit}",
                          "FOOTER_CREDIT_URL": STUB_URL})
check("custom {credit} renders balance", r and r.rstrip().endswith("bal $271.64"), repr(r))

# custom template {credit} with unreachable endpoint → empty, no crash
r = resp(BODY, env_extra={"FOOTER_TEMPLATE": "{model} · {cost} · bal {credit}",
                          "FOOTER_CREDIT_URL": BROKEN_URL})
check("custom {credit} fail-open empty", r and r.rstrip().endswith("· bal"), repr(r))

# ── in-file CONFIG constants (no env) — the recommended config path ──────────
# Prove the script honours its top-of-file constants when NO env var is set,
# by writing a temp copy with the constants flipped and running it with a clean
# env. This mirrors the real deploy: user copies the template, edits constants.
def _run_variant(src_path, ev):
    env = dict(os.environ)
    for k in ("FOOTER_TEMPLATE", "FOOTER_SHOW_TOKENS", "FOOTER_STRIP",
              "FOOTER_SUPPRESS_TEXT", "FOOTER_SHOW_CREDIT", "FOOTER_CREDIT_URL"):
        env.pop(k, None)
    p = subprocess.run([sys.executable, src_path], input=json.dumps(ev),
                       capture_output=True, text=True, env=env, timeout=15)
    out = (p.stdout or "").strip()
    return json.loads(out)["response"] if out else None

_src = open(SCRIPT, encoding="utf-8").read()
EV = {"event": "on_response_end", "response": BODY, "model": "z-ai/glm-5.2",
      "turn_cost_usd": 0.0211, "tokens": {"input": 900, "output": 120}}

# SHOW_CREDIT constant flipped on (+ CREDIT_URL constant pointed at the stub)
_v = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
_v.write(_src.replace("SHOW_CREDIT = False", "SHOW_CREDIT = True")
              .replace("CREDIT_URL  = None", f'CREDIT_URL  = {STUB_URL!r}'))
_v.close()
r = _run_variant(_v.name, EV)
check("in-file SHOW_CREDIT constant works (no env)",
      r and r.rstrip().endswith("💰 $271.64"), repr(r))
os.unlink(_v.name)

# TEMPLATE constant honoured without env
_v = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
_v.write(_src.replace("TEMPLATE    = None", 'TEMPLATE    = "{model} :: {cost}"'))
_v.close()
r = _run_variant(_v.name, EV)
check("in-file TEMPLATE constant works (no env)",
      r and r.rstrip().endswith("z-ai/glm-5.2 :: $0.0211"), repr(r))
os.unlink(_v.name)

# env overrides the in-file constant when both are set (env wins)
_v = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
_v.write(_src.replace("SHOW_CREDIT = False", "SHOW_CREDIT = True")
              .replace("CREDIT_URL  = None", f'CREDIT_URL  = {STUB_URL!r}'))
_v.close()
_env = dict(os.environ); _env["FOOTER_SHOW_CREDIT"] = "0"
_p = subprocess.run([sys.executable, _v.name], input=json.dumps(EV),
                    capture_output=True, text=True, env=_env, timeout=15)
_r = json.loads(_p.stdout.strip())["response"] if _p.stdout.strip() else None
check("env overrides in-file constant (env wins)", _r and "💰" not in _r, repr(_r))
os.unlink(_v.name)

os.unlink(_stub.name)

# empty reply → no change
r = resp("")
check("empty reply: no footer", r is None, repr(r))

# ── dispatch safety ─────────────────────────────────────────────────────────
r = _run({"event": "post_tool_call", "tool_name": "bash"})
check("unknown event: no-op", r is None, repr(r))
p = subprocess.run([sys.executable, SCRIPT], input="", capture_output=True, text=True, timeout=15)
check("empty stdin: no-op", (p.stdout or "").strip() == "", repr(p.stdout))
p = subprocess.run([sys.executable, SCRIPT], input="{not json", capture_output=True, text=True, timeout=15)
check("bad json: no-op", (p.stdout or "").strip() == "", repr(p.stdout))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
