#!/usr/bin/env python3
"""Selftest for verify_publish_claims.py — feeds synthetic events, checks the
decision. Run: python3 verify_publish_claims_selftest.py

Uses a temp registry (PREVIEWS_REGISTRY) + temp WORKSPACE_DIR, so it NEVER
touches the real /data/previews.json or any real state.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "verify_publish_claims.py")

TMP = tempfile.mkdtemp(prefix="vpc_test_")
REG_PATH = os.path.join(TMP, "previews.json")
with open(REG_PATH, "w") as f:
    json.dump({"previews": [
        {"id": "2004-real-deck", "is_published": True},
        {"id": "2004-served-only", "is_published": False},
    ]}, f)

# agentx post ledger: agent really created post id "REAL777".
LEDGER_PATH = os.path.join(TMP, "agentx_posts.json")
with open(LEDGER_PATH, "w") as f:
    json.dump([{"id": "REAL777", "link": "/post/REAL777", "kind": "post"}], f)

# Scheduler registry: one fresh active job (backs a cross-round "scheduled"
# claim) and one old cancelled job (must NOT back a claim).
import time as _t
SCHED_PATH = os.path.join(TMP, "scheduled_jobs.json")
with open(SCHED_PATH, "w") as f:
    json.dump({"jobs": [
        {"job_id": "cron_fresh", "title": "daily report", "status": "active",
         "created_at": _t.time()},
        {"job_id": "cron_old", "title": "old", "status": "cancelled",
         "created_at": _t.time() - 99999},
    ]}, f)
# An EMPTY registry for the "nothing scheduled" cases.
SCHED_EMPTY = os.path.join(TMP, "scheduled_empty.json")
with open(SCHED_EMPTY, "w") as f:
    json.dump({"jobs": []}, f)

# Use the canonical override name the writer (agentx exports) honors, so this
# test also guards the env-name match (regression: hook read AGENTX_LEDGER while
# the writer used AGENTX_LEDGER_FILE).
ENV = {**os.environ, "WORKSPACE_DIR": TMP,
       "PREVIEWS_REGISTRY": REG_PATH, "AGENTX_LEDGER_FILE": LEDGER_PATH,
       "SCHEDULED_JOBS": SCHED_PATH}
# Env variant where the scheduler registry is empty.
ENV_NOSCHED = {**ENV, "SCHEDULED_JOBS": SCHED_EMPTY}


def run(ev, env=None):
    p = subprocess.run([sys.executable, SCRIPT], input=json.dumps(ev),
                       capture_output=True, text=True, timeout=15, env=env or ENV)
    out = (p.stdout or "").strip()
    try:
        return json.loads(out) if out else {}
    except Exception:
        return {"_raw": out, "_err": p.stderr}


def decision(d):
    if d.get("decision") == "block":
        return "block"
    if "response" in d:
        return "rewrite"
    if "add_warning" in d:
        return "warn"
    return "continue"


# (name, event, response, tool_names, expected)
CASES = [
    # should CONTINUE (no false positives)
    ("plain reply no claim", "on_response_end",
     "Here's the data you asked for.", [], "continue"),
    ("offer to publish (future)", "on_response_end",
     "I can publish this to the community if you want. Want me to publish?", [], "continue"),
    ("real published community url", "on_response_end",
     "Published! https://community.iamstarchild.com/2004-real-deck", ["publish_preview"], "continue"),
    ("real preview share link", "on_response_end",
     "Updated the preview: /preview/2004-real-deck/", ["preview"], "continue"),
    ("claim but no link at all", "on_response_end",
     "I've updated the file as requested.", ["write_file"], "continue"),
    ("agentx claim WITH bash this round", "on_response_end",
     "Posted to AgentX: /post/abc123", ["bash"], "continue"),
    ("agentx post id IN ledger", "on_response_end",
     "已发布到 AgentX: /post/REAL777", [], "continue"),
    ("agentx real post + reference to another", "on_response_end",
     "Posted: /post/REAL777 — also see /post/someone-else", [], "continue"),

    # should ACT (true positives)
    ("fake community url not in registry", "on_response_end",
     "Published! https://community.iamstarchild.com/2004-totally-fake", [], "rewrite"),
    ("community url for unpublished preview", "on_response_end",
     "It's live: https://community.iamstarchild.com/2004-served-only", [], "rewrite"),
    ("fake preview id", "on_response_end",
     "Done, updated the preview at /preview/2004-made-up-id/", [], "rewrite"),
    ("agentx claim NO tool ran, id not in ledger", "on_response_end",
     "已发布到 AgentX 论坛: /post/zzz999", [], "rewrite"),

    # on_completion_claim BLOCK path
    ("completion claim fake url -> block", "on_completion_claim",
     "Published! https://community.iamstarchild.com/2004-totally-fake", [], "block"),

    # on_stop BLOCK path (normal-chat redo) — must block, NOT rewrite, because the
    # host honors only `decision: block` on on_stop.
    ("on_stop fake url -> block", "on_stop",
     "Published! https://community.iamstarchild.com/2004-totally-fake", [], "block"),
    ("on_stop agentx fake id -> block", "on_stop",
     "已发布到 AgentX 论坛: /post/zzz999", [], "block"),
    ("on_stop clean real url -> continue", "on_stop",
     "Published! https://community.iamstarchild.com/2004-real-deck", ["publish_preview"], "continue"),
    ("on_stop agentx id in ledger -> continue", "on_stop",
     "已发布到 AgentX: /post/REAL777", [], "continue"),
]


def main():
    passed = failed = 0
    for name, event, resp, tools, expect in CASES:
        d = run({"event": event, "response": resp, "tool_names": tools,
                 "session_id": "selftest-" + name.replace(" ", "-")})
        got = decision(d)
        ok = got == expect
        passed += ok
        failed += (not ok)
        print(f"{'ok  ' if ok else 'FAIL'}  {name:42s} expect={expect:8s} got={got}")
        if not ok:
            print("      raw:", d)

    # --- scheduled task cases (some need the empty-registry env) ---
    # (name, response, tools, env, expected)
    SCHED = [
        ("sched: tool ran this round",
         "I've scheduled a daily report for you.", ["scheduled_task"], ENV, "continue"),
        ("sched: fresh active job, no tool (cross-round)",
         "已设置好定时任务，每天发送日报。", [], ENV, "continue"),
        ("sched: claim but no tool + empty registry -> rewrite",
         "已设置好定时任务，每天 9 点提醒你。", [], ENV_NOSCHED, "rewrite"),
        ("sched: english claim, no tool + empty -> rewrite",
         "Done — I've set up a reminder task for every morning.", [], ENV_NOSCHED, "rewrite"),
        ("sched: offer to schedule (not a claim)",
         "Want me to set up a daily reminder for this?", [], ENV_NOSCHED, "continue"),
        # Non-assertive context: a claim phrase inside a table row / quote / code
        # block is a reference, not the agent's own claim -> must NOT fire.
        ("strip: claim inside a markdown table row",
         "| 5 | 已设置好定时任务（test case） | block |", [], ENV_NOSCHED, "continue"),
        ("strip: claim inside quotes",
         "用户说\u201c已设置好定时任务\u201d但我没看到对应 job", [], ENV_NOSCHED, "continue"),
        ("strip: claim inside a fenced code block",
         "示例：\n```\n已设置好定时任务\n```", [], ENV_NOSCHED, "continue"),
        ("strip: real claim in plain prose still fires",
         "已设置好定时任务，每天 9 点提醒你。", [], ENV_NOSCHED, "rewrite"),
    ]
    for name, resp, tools, env, expect in SCHED:
        d = run({"event": "on_response_end", "response": resp, "tool_names": tools,
                 "session_id": "sched-" + name.replace(" ", "-")}, env=env)
        got = decision(d)
        ok = got == expect
        passed += ok
        failed += (not ok)
        print(f"{'ok  ' if ok else 'FAIL'}  {name:48s} expect={expect:8s} got={got}")
        if not ok:
            print("      raw:", d)

    print("--- loop cap (same session, 3x) ---")
    sid = "loopcap-test"
    seq = []
    for _ in range(3):
        d = run({"event": "on_completion_claim",
                 "response": "Published! https://community.iamstarchild.com/2004-totally-fake",
                 "tool_names": [], "session_id": sid})
        seq.append(decision(d))
    cap_ok = seq == ["block", "block", "warn"]
    passed += cap_ok
    failed += (not cap_ok)
    print(f"{'ok  ' if cap_ok else 'FAIL'}  loop cap {seq} (want block,block,warn)")

    print("--- on_stop loop cap (same session, 3x) ---")
    sid = "loopcap-onstop"
    seq = []
    for _ in range(3):
        d = run({"event": "on_stop",
                 "response": "Published! https://community.iamstarchild.com/2004-totally-fake",
                 "tool_names": [], "session_id": sid})
        seq.append(decision(d))
    cap_ok = seq == ["block", "block", "warn"]
    passed += cap_ok
    failed += (not cap_ok)
    print(f"{'ok  ' if cap_ok else 'FAIL'}  on_stop loop cap {seq} (want block,block,warn)")

    print("--- AGENTX_LEDGER legacy-name fallback ---")
    # The hook must still read the ledger via the legacy AGENTX_LEDGER name.
    env_legacy = {k: v for k, v in ENV.items() if k != "AGENTX_LEDGER_FILE"}
    env_legacy["AGENTX_LEDGER"] = LEDGER_PATH
    d = run({"event": "on_stop", "response": "已发布到 AgentX: /post/REAL777",
             "tool_names": [], "session_id": "legacy-env"}, env=env_legacy)
    legacy_ok = decision(d) == "continue"
    passed += legacy_ok
    failed += (not legacy_ok)
    print(f"{'ok  ' if legacy_ok else 'FAIL'}  legacy AGENTX_LEDGER read -> {decision(d)} (want continue)")

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
