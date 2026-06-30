#!/usr/bin/env python3
"""verify_commitments — make the agent keep the promises it makes in chat.

The problem: the agent sometimes writes a FUTURE promise to come back to you —
"I'll let you know when the build finishes", "明早提醒你看 benchmark",
"完成后通知你" — but registers NOTHING to make that happen. Nothing wakes the
agent until you speak again, so the promise silently dies. (SOUL even forbids
the agent from making such empty promises — this guard enforces that rule.)

The fix: at the turn boundary, if the reply contains a future notify-promise
AND no follow-up primitive was registered to fulfil it, BLOCK once → the agent
is steered to actually register the right primitive before finishing:

  * a TIME-bound promise ("tomorrow morning", "in 2 hours", "by Friday")
      -> scheduled_task(once, deliver=origin)           (cheap, survives restart)
  * a COMPLETION-bound promise ("when the build is done", "once it finishes")
      -> sessions_spawn(...) running a single bash poll loop,
         announce_mode=followup                          (silent poll, notify once)

Wire BOTH legs to this same absolute path in workspace/config/shell_hooks.yaml:

  hooks:
    - event: on_stop
      matcher: "(let|I'?ll|I will|remind|notify|tell you|get back|follow up|report back|circle back|keep you posted|告诉你|通知你|提醒你|汇报|回头|稍后|待会|完成后|做完|跑完|好了|结束后|明天|明早|到时)"
      command: ./extensions/shell_hooks/examples/verify_commitments.py
      timeout: 10

DESIGN POLICY — conservative on purpose (a false block trains users to disable
the guard, and a wrongly-injected reminder is worse noise than a missed one):

  * Fires ONLY when the reply has BOTH a notify verb (tell/remind/notify you …)
    AND a future/conditional cue (tomorrow / when / once / after …). A bare
    "I'll tell you" with no time/condition does not fire.
  * IMMEDIATE delivery framing ("here's", "下面就是", "现在告诉你", "as follows")
    suppresses the guard — that's this message delivering, not a promise.
  * "Registered" is satisfied by ANY of: scheduled_task / sessions_spawn ran
    THIS turn, OR a recently-created active scheduled job, OR a recently-created
    subagent run (cross-round ground truth — the registration may have happened
    a round earlier while the agent was still talking).
  * At most MAX_BLOCKS nudges per session, a TTL'd state file, and
    stop_hook_active self-disarm. Past the cap it lets the turn through with a
    soft warning. Fail-open everywhere: any error prints "{}" and proceeds.

Self-test: templates/verify_commitments_selftest.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

# ─────────────────────────── tunables ──────────────────────────────────────
MAX_BLOCKS = 2              # block at most this many times per session
STATE_TTL_SEC = 2 * 3600   # forget a session's block count after 2h idle
RECENCY_SEC = 15 * 60      # how recent a job/spawn must be to back a promise

# A NOTIFY-the-user verb in a promise frame ("I'll tell you", "remind you", …).
NOTIFY_RX = re.compile(
    r"(?ix)(?:"
    r"\b(?:i'?ll|i\s+will|let\s+me|we'?ll)\b[^.?!]{0,40}?"
    r"\b(?:let\s+you\s+know|tell\s+you|notify\s+you|ping\s+you|remind\s+you|"
    r"update\s+you|get\s+back\s+to\s+you|report\s+back|follow\s+up|"
    r"circle\s+back|keep\s+you\s+posted)\b"
    r"|"
    r"\b(?:let\s+you\s+know|remind\s+you|notify\s+you|ping\s+you)\b"
    r"|"
    r"(?:告诉|通知|提醒|汇报|回复)你"
    r")"
)

# A FUTURE / CONDITIONAL cue — the promise is bound to a later time or event.
FUTURE_RX = re.compile(
    r"(?ix)(?:"
    r"\bwhen\b|\bonce\b|\bafter\b|\bas\s+soon\s+as\b|\bthe\s+moment\b|"
    r"\btomorrow\b|\btonight\b|\blater\b|\bsoon\b|\bin\s+(?:a|an|\d)\s+"
    r"(?:minute|min|hour|hr|day|week)s?\b|\bby\s+(?:monday|tuesday|wednesday|"
    r"thursday|friday|saturday|sunday|tomorrow|tonight|noon|eod|end\s+of)\b|"
    r"\bnext\s+(?:hour|day|week|morning)\b|"
    r"完成(?:后|了)?|做完(?:后|了)?|跑完(?:后|了)?|结束(?:后|了)?|搞定(?:后|了)?|"
    r"好了(?:之后|以后)?|之后|以后|稍后|待会|过会|回头|晚点|"
    r"明天|明早|今晚|到时(?:候)?|等(?:它|这|那)|一旦"
    r")"
)

# IMMEDIATE delivery framing -> this message IS the delivery, not a promise.
IMMEDIATE_RX = re.compile(
    r"(?ix)(?:"
    r"\bhere'?s\b|\bhere\s+is\b|\bhere\s+are\b|\bbelow\b|\bas\s+follows\b|"
    r"\bnow\s+showing\b|\battached\b|"
    r"下面(?:就)?是|如下|这就|现在(?:就)?(?:告诉|给你|是)|已(?:经)?(?:告诉|发给)你"
    r")"
)


def _read_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _workspace_base(ev: dict) -> str:
    base = os.environ.get("WORKSPACE_DIR")
    if not base:
        cwd = ev.get("cwd") or "."
        cand = os.path.join(cwd, "workspace")
        base = cand if os.path.isdir(cand) else cwd
    return base


def _state_file(ev: dict) -> str:
    out = os.path.join(_workspace_base(ev), "output")
    try:
        os.makedirs(out, exist_ok=True)
    except Exception:
        out = _workspace_base(ev)
    return os.path.join(out, ".commitment_guard.json")


def _has_recent_active_job() -> bool:
    """True if the scheduler holds an ACTIVE job created/updated within
    RECENCY_SEC — ground truth that a time-bound promise was just registered,
    even when scheduled_task ran in an earlier round (cross-round safe)."""
    path = os.environ.get("SCHEDULED_JOBS", "/data/scheduled_jobs.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        jobs = data.get("jobs") if isinstance(data, dict) else data
        now = time.time()
        for j in (jobs or []):
            if not isinstance(j, dict):
                continue
            status = str(j.get("status") or "").lower()
            if status and status != "active":
                continue
            ts = float(j.get("updated_at") or j.get("created_at") or 0)
            if ts and (now - ts) <= RECENCY_SEC:
                return True
    except Exception:
        pass
    return False


def _has_recent_subagent() -> bool:
    """True if a subagent run was created within RECENCY_SEC — ground truth
    that a completion-bound promise was just handed to a spawn watcher."""
    # env-exclusive when set (keeps the self-test isolated from any real
    # tasks.json on the host); otherwise probe the known default locations.
    env_path = os.environ.get("TASKS_STORAGE_PATH")
    candidates = [env_path] if env_path else [
        "/data/workspace/data/tasks.json", "/data/tasks.json", "./data/tasks.json",
    ]
    now = time.time()
    for p in candidates:
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        runs = data.get("runs") if isinstance(data, dict) else data
        for r in (runs or []):
            if not isinstance(r, dict):
                continue
            ts = float(r.get("created_at") or 0)
            if ts and (now - ts) <= RECENCY_SEC:
                return True
    return False


def _block_count(ev: dict, sid: str) -> int:
    try:
        with open(_state_file(ev), "r", encoding="utf-8") as f:
            rec = (json.load(f) or {}).get(sid)
        if not rec:
            return 0
        if time.time() - float(rec.get("ts", 0)) > STATE_TTL_SEC:
            return 0  # stale -> fresh
        return int(rec.get("n", 0))
    except Exception:
        return 0


def _bump_block(ev: dict, sid: str) -> None:
    path = _state_file(ev)
    try:
        st = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                st = json.load(f) or {}
        now = time.time()
        st = {k: v for k, v in st.items()
              if now - float((v or {}).get("ts", 0)) <= STATE_TTL_SEC}
        rec = st.get(sid) or {"n": 0}
        st[sid] = {"n": int(rec.get("n", 0)) + 1, "ts": now}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st, f)
    except Exception:
        pass


def _is_unkept_promise(reply: str, tools: list) -> bool:
    """A future notify-promise with no follow-up primitive registered."""
    if not reply:
        return False
    if not (NOTIFY_RX.search(reply) and FUTURE_RX.search(reply)):
        return False
    if IMMEDIATE_RX.search(reply):
        return False  # this message is delivering, not promising

    tools_l = [str(t).lower() for t in (tools or [])]
    registered_this_turn = any(
        ("scheduled_task" in t or "schedule" in t or "sessions_spawn" in t
         or "spawn" in t)
        for t in tools_l
    )
    if registered_this_turn:
        return False
    # cross-round ground truth: registration may have happened a round earlier
    if _has_recent_active_job() or _has_recent_subagent():
        return False
    return True


def main() -> None:
    ev = _read_event()
    event = ev.get("event") or ""
    reply = ev.get("response") or ev.get("summary") or ""
    tools = ev.get("tool_names") or []
    sid = str(ev.get("session_id") or "default")

    # on_stop is the only redo-capable event we honor; anything else -> no-op.
    if event != "on_stop":
        print("{}")
        return

    if not _is_unkept_promise(reply, tools):
        print("{}")
        return

    if bool(ev.get("stop_hook_active")):
        print("{}")  # a continuation is already in flight -> don't pile on
        return

    if _block_count(ev, sid) >= MAX_BLOCKS:
        print(json.dumps({
            "add_warning": ("You made a follow-up promise the guard couldn't "
                            "confirm was registered, but it already nudged twice "
                            "this session — letting it through. Double-check you "
                            "actually scheduled/spawned the follow-up."),
        }, ensure_ascii=False))
        return

    _bump_block(ev, sid)
    reason = (
        "[verify-commitment] You promised to follow up later (notify/remind the "
        "user) but registered nothing to make it happen — nothing will wake you "
        "until the user speaks again, so this promise will silently die. Register "
        "it now: a TIME-bound promise -> scheduled_task(once, deliver=origin); a "
        "COMPLETION-bound promise -> sessions_spawn running a single bash poll "
        "loop with announce_mode=followup. If you genuinely cannot fulfil it, say "
        "so plainly instead of promising. Then finish."
    )
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


if __name__ == "__main__":
    main()
