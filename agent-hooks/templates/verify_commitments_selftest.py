#!/usr/bin/env python3
"""Self-test for verify_commitments.py — focus on FALSE-POSITIVE safety.

Runs the guard as a subprocess (real stdin/stdout, like the bridge does) over
scripted on_stop events. Each scenario uses a fresh session id and isolated
SCHEDULED_JOBS / TASKS_STORAGE_PATH env paths so neither host state nor prior
cases leak in. Exits non-zero on any failure.

Run:  python3 verify_commitments_selftest.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUARD = HERE / "verify_commitments.py"
TMP = Path(tempfile.mkdtemp(prefix="commit_guard_test_"))
EMPTY_JOBS = str(TMP / "no_such_jobs.json")      # nonexistent -> no recent job
EMPTY_TASKS = str(TMP / "no_such_tasks.json")    # nonexistent -> no recent spawn

_fail = 0
_pass = 0


def _run(payload: dict, env_extra: dict | None = None) -> dict:
    """Pipe one event to the guard, return its parsed decision ({} if empty)."""
    env = dict(os.environ)
    # default: isolate from host so BLOCK cases are deterministic
    env["SCHEDULED_JOBS"] = EMPTY_JOBS
    env["TASKS_STORAGE_PATH"] = EMPTY_TASKS
    env["WORKSPACE_DIR"] = str(TMP)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=30, env=env,
    )
    out = (proc.stdout or "").strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"__nonjson__": out, "__stderr__": proc.stderr}


def _stop(sid, response, tool_names=None, stop_active=False):
    return {"event": "on_stop", "session_id": sid, "response": response,
            "tool_names": tool_names or [], "stop_hook_active": stop_active,
            "model": "test"}


def check(name: str, decision: dict, expect_block: bool):
    global _fail, _pass
    if "__nonjson__" in decision:
        print(f"  ✗ {name}: NON-JSON output: {decision['__nonjson__'][:100]} "
              f"| stderr={decision.get('__stderr__','')[:100]}")
        _fail += 1
        return
    blocked = decision.get("decision") == "block"
    ok = blocked == expect_block
    tag = "✓" if ok else "✗"
    want = "BLOCK" if expect_block else "ALLOW"
    got = "BLOCK" if blocked else "ALLOW"
    print(f"  {tag} {name}: want {want}, got {got}")
    if ok:
        _pass += 1
    else:
        _fail += 1


def sid() -> str:
    return "selftest-" + uuid.uuid4().hex[:12]


def _write_recent_jobs(path: str):
    Path(path).write_text(json.dumps({"jobs": [
        {"id": "j1", "status": "active", "created_at": time.time()},
    ]}))


def _write_recent_tasks(path: str):
    Path(path).write_text(json.dumps({"runs": [
        {"run_id": "r1", "created_at": time.time()},
    ]}))


# ───────────────────────────── scenarios ───────────────────────────────────
print("verify_commitments self-test\n" + "=" * 60)

# --- TRUE POSITIVES: a future notify-promise with nothing registered → BLOCK
check("EN time promise, no tool",
      _run(_stop(sid(), "Sounds good — I'll remind you tomorrow morning to "
                        "check the benchmark results.")),
      expect_block=True)

check("EN completion promise, no tool",
      _run(_stop(sid(), "Kicking off the build. I'll let you know once it "
                        "finishes.")),
      expect_block=True)

check("ZH time promise, no tool",
      _run(_stop(sid(), "好的,我明早提醒你看 benchmark 结果。")),
      expect_block=True)

check("ZH completion promise, no tool",
      _run(_stop(sid(), "构建已经开始,跑完后通知你。")),
      expect_block=True)

# --- REGISTERED THIS TURN → ALLOW
check("time promise + scheduled_task ran",
      _run(_stop(sid(), "I'll remind you tomorrow morning.",
                 tool_names=["scheduled_task"])),
      expect_block=False)

check("completion promise + sessions_spawn ran",
      _run(_stop(sid(), "I'll let you know once the build finishes.",
                 tool_names=["sessions_spawn"])),
      expect_block=False)

check("ZH promise + scheduled_task ran",
      _run(_stop(sid(), "明早提醒你看结果。", tool_names=["scheduled_task"])),
      expect_block=False)

# --- CROSS-ROUND GROUND TRUTH → ALLOW
jobs_f = str(TMP / "recent_jobs.json"); _write_recent_jobs(jobs_f)
check("promise + recent active scheduled job (cross-round)",
      _run(_stop(sid(), "I'll remind you tomorrow."),
           env_extra={"SCHEDULED_JOBS": jobs_f}),
      expect_block=False)

tasks_f = str(TMP / "recent_tasks.json"); _write_recent_tasks(tasks_f)
check("promise + recent subagent run (cross-round)",
      _run(_stop(sid(), "I'll let you know when it's done."),
           env_extra={"TASKS_STORAGE_PATH": tasks_f}),
      expect_block=False)

# --- FALSE-POSITIVE GUARDS → ALLOW
check("bare notify, no future/condition cue",
      _run(_stop(sid(), "I'll tell you what I think: this approach is solid.")),
      expect_block=False)

check("immediate delivery (here's), not a promise",
      _run(_stop(sid(), "Here's the benchmark result you asked for: 92%. "
                        "Let me know if you want a deeper cut.")),
      expect_block=False)

check("ZH immediate delivery (下面就是)",
      _run(_stop(sid(), "下面就是你要的结果,我现在告诉你:准确率 92%。")),
      expect_block=False)

check("plain answer, no promise at all",
      _run(_stop(sid(), "The funding rate is negative, which favors longs. "
                        "Here are the levels.")),
      expect_block=False)

check("future cue but no notify-the-user verb",
      _run(_stop(sid(), "When the build finishes it will produce a binary in "
                        "dist/. You can run it directly.")),
      expect_block=False)

# --- LOOP / CAP SAFETY
check("stop_hook_active self-disarm",
      _run(_stop(sid(), "I'll remind you tomorrow morning.", stop_active=True)),
      expect_block=False)

# nag once only, then allow (same session, MAX_BLOCKS=2 → block twice then allow)
s = sid()
b = 0
for _ in range(5):
    d = _run(_stop(s, "I'll remind you tomorrow morning."))
    if d.get("decision") == "block":
        b += 1
cap_ok = b <= 2
print(f"  {'✓' if cap_ok else '✗'} per-session block cap: {b} blocks (cap 2)")
_pass += int(cap_ok); _fail += int(not cap_ok)

# --- FAIL-OPEN / DISPATCH
for bad in ["", "not json", "[]", "{}"]:
    proc = subprocess.run([sys.executable, str(GUARD)], input=bad,
                          capture_output=True, text=True, timeout=30)
    out = (proc.stdout or "").strip()
    ok = out in ("{}", "") or (out.startswith("{") and "block" not in out)
    print(f"  {'✓' if ok else '✗'} fail-open on payload {bad!r:12}: out={out[:40]!r}")
    _pass += int(ok); _fail += int(not ok)

check("unknown event no-op (on_response_end)",
      _run({"event": "on_response_end", "session_id": sid(),
            "response": "I'll remind you tomorrow."}),
      expect_block=False)

# ───────────────────────────── cleanup + summary ───────────────────────────
try:
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
except Exception:
    pass

print("=" * 60)
print(f"PASS {_pass} | FAIL {_fail}")
sys.exit(1 if _fail else 0)
