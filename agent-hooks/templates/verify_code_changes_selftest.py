#!/usr/bin/env python3
"""Self-test for verify_code_changes.py — focus on FALSE-POSITIVE safety.

Runs the guard as a subprocess (real stdin/stdout, like the bridge does) over
scripted event sequences. Each scenario uses a fresh session id so state never
leaks between cases. Exits non-zero on any failure.

Run:  python3 verify_code_changes_selftest.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUARD = HERE / "verify_code_changes.py"
STATE_DIR = Path("/data/workspace/.verify_guard")

_fail = 0
_pass = 0


def _run(event_payload: dict) -> dict:
    """Pipe one event to the guard, return its parsed decision ({} if empty)."""
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(event_payload),
        capture_output=True, text=True, timeout=30,
    )
    out = (proc.stdout or "").strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"__nonjson__": out, "__stderr__": proc.stderr}


def _pre(sid, tool, **inp):
    return {"event": "pre_tool_call", "session_id": sid, "tool_name": tool,
            "tool_input": inp}


def _stop(sid, stop_active=False, tool_names=None):
    return {"event": "on_stop", "session_id": sid,
            "stop_hook_active": stop_active, "tool_names": tool_names or [],
            "response": "Done.", "model": "test"}


def check(name: str, decision: dict, expect_block: bool):
    global _fail, _pass
    if "__nonjson__" in decision:
        print(f"  ✗ {name}: NON-JSON output: {decision['__nonjson__'][:120]} "
              f"| stderr={decision.get('__stderr__','')[:120]}")
        _fail += 1
        return
    blocked = decision.get("decision") == "block"
    ok = blocked == expect_block
    tag = "✓" if ok else "✗"
    want = "BLOCK" if expect_block else "ALLOW"
    got = "BLOCK" if blocked else "ALLOW"
    extra = ""
    if blocked:
        extra = f"  reason={decision.get('reason','')[:70]!r}"
    print(f"  {tag} {name}: want {want}, got {got}{extra}")
    if ok:
        _pass += 1
    else:
        _fail += 1


def sid() -> str:
    return "selftest-" + uuid.uuid4().hex[:12]


# ───────────────────────────── scenarios ───────────────────────────────────
print("verify_code_changes self-test\n" + "=" * 60)

# 1. Core positive: edit .py, run nothing → BLOCK
s = sid()
_run(_pre(s, "edit_file", path="core/foo.py"))
check("edit code, no verify", _run(_stop(s)), expect_block=True)

# 2. Edit .py, then pytest → ALLOW
s = sid()
_run(_pre(s, "edit_file", path="core/foo.py"))
_run(_pre(s, "bash", command="pytest tests/test_foo.py -q"))
check("edit code + pytest", _run(_stop(s)), expect_block=False)

# 3. FALSE-POSITIVE GUARD: edit only a .md → ALLOW
s = sid()
_run(_pre(s, "write_file", path="docs/README.md"))
check("edit README only", _run(_stop(s)), expect_block=False)

# 4. FALSE-POSITIVE GUARD: edit .json config → ALLOW
s = sid()
_run(_pre(s, "edit_file", path="config/agent.yaml"))
_run(_pre(s, "edit_file", path="data/x.json"))
check("edit yaml+json only", _run(_stop(s)), expect_block=False)

# 5. Read-only turn (no edits at all) → ALLOW
s = sid()
_run(_pre(s, "read_file", path="core/foo.py"))
_run(_pre(s, "bash", command="ls -la"))
check("read-only turn", _run(_stop(s)), expect_block=False)

# 6. Edit code + smoke-run the script (python foo.py) → ALLOW
s = sid()
_run(_pre(s, "edit_file", path="scripts/foo.py"))
_run(_pre(s, "bash", command="python scripts/foo.py --check"))
check("edit + smoke run script", _run(_stop(s)), expect_block=False)

# 7. NO INFINITE LOOP: edit code, stop_hook_active=True → ALLOW (self-disarm)
s = sid()
_run(_pre(s, "edit_file", path="core/foo.py"))
check("edit + already continuing", _run(_stop(s, stop_active=True)),
      expect_block=False)

# 8. NAG ONCE ONLY: block once, then next stop (no new verify) → ALLOW
s = sid()
_run(_pre(s, "edit_file", path="core/foo.py"))
check("first stop (nag)", _run(_stop(s)), expect_block=True)
check("second stop (no re-nag)", _run(_stop(s)), expect_block=False)

# 9. Mixed edit: code + docs together, no verify → BLOCK (code present)
s = sid()
_run(_pre(s, "edit_file", path="README.md"))
_run(_pre(s, "edit_file", path="core/bar.py"))
check("mixed code+docs, no verify", _run(_stop(s)), expect_block=True)

# 10. Verify clears BOTH files (edit two .py, run one test) → ALLOW
s = sid()
_run(_pre(s, "edit_file", path="a.py"))
_run(_pre(s, "edit_file", path="b.py"))
_run(_pre(s, "bash", command="npm run test"))
check("two edits, one test run clears all", _run(_stop(s)), expect_block=False)

# 11. ruff / tsc / go test recognized
for cmd in ["ruff check .", "tsc --noEmit", "go test ./...",
            "cargo test", "make test", "npx vitest run", "mypy core/"]:
    s = sid()
    _run(_pre(s, "edit_file", path="core/foo.py"))
    _run(_pre(s, "bash", command=cmd))
    check(f"verify via: {cmd}", _run(_stop(s)), expect_block=False)

# 12. TTL: an edit older than the window must NOT block.
#     We simulate by writing a stale state file directly.
s = sid()
STATE_DIR.mkdir(parents=True, exist_ok=True)
stale = {"pending": [{"path": "old.py", "ts": time.time() - 3600, "nagged": False}],
         "nags": 0}
import re as _re
safe = _re.sub(r"[^A-Za-z0-9._-]", "_", s)[:120]
(STATE_DIR / f"{safe}.json").write_text(json.dumps(stale))
check("stale edit beyond TTL", _run(_stop(s)), expect_block=False)

# 12b. bash writes code (heredoc) but runs nothing → BLOCK
s = sid()
_run(_pre(s, "bash", command="cat > app.py <<'EOF'\nprint(1)\nEOF"))
check("bash heredoc writes code, no verify", _run(_stop(s)), expect_block=True)

# 12c. bash sed -i on code, no verify → BLOCK
s = sid()
_run(_pre(s, "bash", command="sed -i 's/a/b/' core/handler.py"))
check("bash sed -i code, no verify", _run(_stop(s)), expect_block=True)

# 12d. bash writes code then runs it in the SAME command → ALLOW (verified)
s = sid()
_run(_pre(s, "bash", command="cat > t.py <<'EOF'\nprint(1)\nEOF\npython t.py"))
check("bash write-then-run one-liner", _run(_stop(s)), expect_block=False)

# 12e. bash writes code, THEN a separate verify command → ALLOW
s = sid()
_run(_pre(s, "bash", command="cat > m.py <<'EOF'\nx=1\nEOF"))
_run(_pre(s, "bash", command="python m.py"))
check("bash write then separate verify", _run(_stop(s)), expect_block=False)

# 12f. bash redirects to NON-code (log/json) → ALLOW (no false positive)
s = sid()
_run(_pre(s, "bash", command="echo done > out.log && cat data >> report.json"))
check("bash writes non-code only", _run(_stop(s)), expect_block=False)

# 13. Per-session cap: after MAX_NAGS distinct edit sets, stop nagging.
s = sid()
blocked_count = 0
for i in range(6):
    _run(_pre(s, "edit_file", path=f"f{i}.py"))   # fresh un-nagged edit each round
    d = _run(_stop(s))
    if d.get("decision") == "block":
        blocked_count += 1
cap_ok = blocked_count <= 3
print(f"  {'✓' if cap_ok else '✗'} per-session nag cap: {blocked_count} blocks (cap 3)")
_pass += int(cap_ok); _fail += int(not cap_ok)

# 14. Garbage / empty payload → ALLOW (fail-open), valid JSON out
for bad in ["", "not json", "[]", "{}"]:
    proc = subprocess.run([sys.executable, str(GUARD)], input=bad,
                          capture_output=True, text=True, timeout=30)
    out = (proc.stdout or "").strip()
    ok = out in ("{}", "") or (out.startswith("{") and "block" not in out)
    print(f"  {'✓' if ok else '✗'} fail-open on payload {bad!r:14}: out={out[:40]!r}")
    _pass += int(ok); _fail += int(not ok)

# 15. Unknown event → no-op
s = sid()
d = _run({"event": "on_response_end", "session_id": s, "response": "x"})
check("unknown event no-op", d, expect_block=False)

# ───────────────────────────── cleanup + summary ───────────────────────────
try:
    for f in STATE_DIR.glob("selftest-*.json"):
        f.unlink()
except Exception:
    pass

print("=" * 60)
print(f"PASS {_pass} | FAIL {_fail}")
sys.exit(1 if _fail else 0)
