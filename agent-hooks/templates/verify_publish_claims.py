#!/usr/bin/env python3
"""Catch fabricated "published / posted / updated" claims for AgentX & previews.

The problem: an agent sometimes writes "Published! community.iamstarchild.com/..."
or "Posted to AgentX: /post/123" or "I've updated the preview" when it did NOT
actually run the publishing tool — a hallucinated success. This hook checks the
reply against ground truth and either forces a redo or rewrites the reply so the
user never sees a false success.

Wire under one or more events in workspace/config/shell_hooks.yaml. Prefer
on_stop — it makes the agent ACTUALLY redo in ordinary chat:

  hooks:
    # (A) PREFERRED, every chat turn. Can BLOCK -> the host steers the reason
    #     back and the agent keeps working, so it actually publishes/redoes
    #     instead of just printing a corrected note. Loop-capped (MAX_BLOCKS).
    - event: on_stop
      matcher: "publish|posted|preview|/post/|community\\.iamstarchild|已发布|已上线|已更新|发布成功"
      command: ./extensions/shell_hooks/examples/verify_publish_claims.py
      timeout: 10

    # (B) Goal/supervisor mode only. Can BLOCK -> forces the agent to actually
    #     publish, then re-confirm. Loop-capped so it can never trap the agent.
    - event: on_completion_claim
      matcher: "publish|posted|preview|/post/|community\\.iamstarchild|已发布|已上线|已更新|发布成功"
      command: ./extensions/shell_hooks/examples/verify_publish_claims.py
      timeout: 10

    # (C) Fallback if on_stop isn't available. REWRITE-only: appends an honest
    #     correction to the stored reply; it cannot make the agent redo.
    - event: on_response_end
      matcher: "publish|posted|preview|/post/|community\\.iamstarchild|已发布|已上线|已更新|发布成功"
      command: ./extensions/shell_hooks/examples/verify_publish_claims.py
      timeout: 10

Design priorities, in order:
  1. NEVER trap the agent. A hard per-session block cap (MAX_BLOCKS) means even a
     wrong guess lets the turn through after a couple of nudges.
  2. Minimise false positives. We engage only on a *past-tense success* claim
     that *cites a concrete link*, and verify previews against the real registry
     (not this round's tool list — which is per-round and would misfire when the
     publish happened in an earlier round).
  3. Be honest about limits. AgentX posts have no local registry, so that branch
     is a softer heuristic; the block cap keeps it safe.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

# tunables
MAX_BLOCKS = 2            # block at most this many times per session
STATE_TTL_SEC = 2 * 3600  # forget a session's block count after 2h idle

# A *success* claim in past / present-perfect — "I did it", not "I can do it".
CLAIM_RX = re.compile(
    r"(?:"
    r"\bpublished\b|\bposted\b|\b(?:is|are|now|went|it'?s)\s+live\b|"
    r"\bdeployed\b|\bshipped\b|\bupdated\s+(?:the|it|your)\b|"
    r"已发布|已上线|已发到|已经发布|已经发到|已经上线|发布成功|"
    r"已更新|已经更新|更新成功|已发布到|已经发布到|已部署"
    r")",
    re.IGNORECASE,
)

# Future / conditional / offer framing -> NOT a success claim.
FUTURE_RX = re.compile(
    r"(?:"
    r"\bcan\s+publish\b|\bwill\s+publish\b|\bto\s+publish\b|\bwould\s+you\b|"
    r"\bwant\s+me\s+to\b|\bshould\s+i\b|\bready\s+to\s+publish\b|"
    r"准备发布|打算发布|可以帮你|要不要|是否需要|要发布吗|能否发布|将要"
    r")",
    re.IGNORECASE,
)

# Hard ZH success verbs that override an offer frame appearing in the same reply.
HARD_ZH_RX = re.compile(r"已发布|已上线|发布成功|已更新|更新成功|已部署|已经发布")

# Exclusion set also covers CJK curly quotes (“ ” ‘ ’) + comma/、 so a URL wrapped
# in quotes (`已发布“…/x”`) doesn't glue the closing quote onto the captured id.
COMMUNITY_RX = re.compile(
    "https?://community\\.iamstarchild\\.com/[^\\s)\\]\"'>\u201c\u201d\u2018\u2019,\uff0c\u3001]+",
    re.I,
)
PREVIEW_RX = re.compile(r"/preview/([\w.\-]+)", re.I)
AGENTX_RX = re.compile(r"/post/([\w\-]+)")

# A *scheduling* success claim — "I set up the recurring task / reminder".
SCHED_CLAIM_RX = re.compile(
    r"(?:"
    r"\bscheduled\b|\bset\s+up\s+(?:a\s+)?(?:task|job|reminder|cron)\b|"
    r"\b(?:reminder|task|job|cron|alert)\s+is\s+(?:set|scheduled)\b|"
    r"\bI'?ve\s+(?:set|scheduled)\b|"
    r"已(?:设置|创建|安排|添加)(?:好)?(?:了)?(?:定时|提醒|任务|计划)|"
    r"定时任务(?:已|创建|设置)|已设好|已经设置(?:好)?(?:定时|提醒|任务)|"
    r"提醒(?:已|创建|设置好)"
    r")",
    re.IGNORECASE,
)
# How recent an active job must be to back a cross-round "scheduled" claim.
SCHED_RECENCY_SEC = 15 * 60


def _read_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _load_previews() -> tuple[set, set]:
    """Return (published_ids, all_ids) from the previews registry.

    published_ids = ids whose is_published is truthy (real community URL exists).
    all_ids       = every id (enough to validate a /preview/{id}/ share link).
    """
    pub, allids = set(), set()
    # Fixed real path; env override exists only so the selftest can point at a
    # temp registry without ever touching the real one.
    reg = os.environ.get("PREVIEWS_REGISTRY", "/data/previews.json")
    try:
        with open(reg, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else (data.get("previews") or [])
        for it in items:
            if not isinstance(it, dict):
                continue
            pid = str(it.get("id") or it.get("preview_id") or "").strip()
            if not pid:
                continue
            allids.add(pid)
            if it.get("is_published") or it.get("public_url"):
                pub.add(pid)
    except Exception:
        pass
    return pub, allids


def _has_recent_active_job() -> bool:
    """True if the scheduler registry holds an ACTIVE job created/updated within
    SCHED_RECENCY_SEC — ground truth that a "scheduled" claim is real even when
    the scheduled_task tool ran in an earlier round (cross-round safe).
    """
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
            if ts and (now - ts) <= SCHED_RECENCY_SEC:
                return True
    except Exception:
        pass
    return False


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
    return os.path.join(out, ".publish_claim_guard.json")


def _load_agentx_ids(ev: dict) -> set:
    """Real post/comment ids the agent actually created (agentx skill ledger).

    Written by agentx exports on every successful create_post/thread/comment
    (see $WORKSPACE_DIR/output/agentx_posts.json). Lets us EXACTLY confirm a
    cited /post/<id> was produced, instead of guessing from "did bash run".
    """
    ids = set()
    # Match the writer (agentx exports): it honors AGENTX_LEDGER_FILE. Read that
    # first; keep AGENTX_LEDGER as a legacy fallback so an override set per the
    # agentx SKILL.md doc is actually picked up (otherwise the guard reads the
    # default path, misses the real ledger, and false-flags a genuine /post/<id>).
    path = (os.environ.get("AGENTX_LEDGER_FILE")
            or os.environ.get("AGENTX_LEDGER")
            or os.path.join(_workspace_base(ev), "output", "agentx_posts.json"))
    try:
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        for it in (items if isinstance(items, list) else []):
            if isinstance(it, dict) and it.get("id"):
                ids.add(str(it["id"]))
    except Exception:
        pass
    return ids


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


def _strip_non_assertive(text: str, keep_quotes: bool = False) -> str:
    """Remove quoted / tabular / code content so claim regexes only fire on
    the agent's OWN assertions, not on text it's quoting or tabulating.

    Strips: markdown table rows (| ... |), inline code spans (`...`), fenced
    code blocks (```...```), and content inside quotation marks ("...", '...',
    '...'). This prevents false positives when the agent references a claim
    phrase inside a test report, a quote, or a code example instead of making
    the claim itself.

    keep_quotes=True KEEPS quoted content (only code blocks / tables / inline
    code are dropped). Used for URL/id verification: a real claim commonly puts
    the link in quotes — `Published: "https://…/x"` / `已发布 "/preview/x/"` —
    and stripping the quote would erase the very URL we must verify, letting a
    fabricated link slip through. Code blocks / tables stay stripped because
    those are genuinely test data / examples, not the agent asserting a link.
    """
    if not text:
        return ""
    # Drop fenced code blocks first (```...```)
    text = re.sub(r"```[\s\S]*?```", " ", text)
    # Drop markdown table rows (lines whose first non-space char is |)
    text = re.sub(r"(?m)^\s*\|.*$", " ", text)
    # Drop inline code spans
    text = re.sub(r"`[^`]*`", " ", text)
    if keep_quotes:
        return text
    # Drop content inside double/single/CJK quotes
    text = re.sub(r'"[^"]*"', " ", text)
    text = re.sub(r"'[^']*'", " ", text)
    text = re.sub(r"\u201c[^\u201d]*\u201d", " ", text)
    text = re.sub(r"\u2018[^\u2019]*\u2019", " ", text)
    return text


def _analyze(reply: str, tools: list, ev: dict) -> tuple | None:
    """Return (reason, detail) if the reply looks fabricated, else None."""
    if not reply:
        return None
    # Claim DETECTION uses fully-stripped text (quotes too) so referencing a
    # claim phrase (in a test report, quote, or example) doesn't trip the guard.
    assertive = _strip_non_assertive(reply)
    # URL/id VERIFICATION uses quote-preserving text so a real claim that puts
    # the link in quotes (`Published: "…/x"`) still gets its URL checked.
    url_scan = _strip_non_assertive(reply, keep_quotes=True)
    has_publish_claim = bool(CLAIM_RX.search(assertive))
    has_sched_claim = bool(SCHED_CLAIM_RX.search(assertive))
    if not has_publish_claim and not has_sched_claim:
        return None
    # An offer/plan frame with no hard success verb -> not a real claim.
    if FUTURE_RX.search(reply) and not HARD_ZH_RX.search(reply):
        return None

    tools_l = [str(t).lower() for t in (tools or [])]
    ran_bash = any("bash" in t for t in tools_l)
    ran_publish_tool = any(
        any(h in t for h in ("publish", "deploy", "preview",
                             "list_in_dashboard", "open_source"))
        for t in tools_l
    )

    # SCHEDULED TASK check runs independently of the publish claim gate.
    if has_sched_claim:
        ran_sched_tool = any("scheduled_task" in t or "schedule" in t
                             for t in tools_l)
        if not ran_sched_tool and not _has_recent_active_job():
            return ("Claimed a task is scheduled, but no scheduling tool ran and no "
                    "matching active job exists. Call scheduled_task, then confirm", None)

    if not has_publish_claim:
        return None

    pub_ids, all_ids = _load_previews()

    # COMMUNITY publish claim: id must exist AND be marked published.
    for url in COMMUNITY_RX.findall(url_scan):
        seg = re.sub(r"[?#].*$", "", url.rstrip("/").split("/")[-1])
        seg = seg.strip("\"'\u201c\u201d\u2018\u2019.,\uff0c\u3002\u3001 ")
        if seg and seg not in all_ids and seg not in pub_ids:
            return ("Claimed published but not in the registry. Run publish_preview, "
                    "use the URL it returns", url)
        if seg in all_ids and seg not in pub_ids:
            return ("This preview exists but isn't published yet. Publish it first", url)

    # /preview/{id}/ share link: id just has to exist (local serve, not publish).
    for pid in PREVIEW_RX.findall(url_scan):
        if pid and pid not in all_ids:
            return ("Preview id not in the registry — looks made up. Serve it first, "
                    "use the real id", "/preview/%s/" % pid)

    # AGENTX /post/{id}: verify against the agentx skill's durable post ledger
    # (exact id match — cross-round safe, like the preview registry above). Only
    # engage on a success claim that cites a /post/ link. Rule: if NONE of the
    # cited ids are in the ledger, it's fabricated. If even one IS in the ledger
    # the agent really posted, and any extra /post/ links are just references to
    # other agents' posts — don't flag those (avoids false positives on sharing).
    agentx_ids = AGENTX_RX.findall(url_scan)
    mentions_agentx = bool(re.search(r"agentx|/post/|论坛|发帖", url_scan, re.I))
    if agentx_ids and mentions_agentx:
        known = _load_agentx_ids(ev)
        if not any(pid in known for pid in agentx_ids):
            # None verified. Give the benefit of the doubt only if a tool ran
            # THIS round (the ledger write may lag) — otherwise it's invented.
            if not ran_bash and not ran_publish_tool:
                return ("AgentX post id not in the ledger and no tool created it — "
                        "looks invented. Call agentx.create_post, use the id it returns",
                        "/post/%s" % agentx_ids[0])

    return None


def main() -> None:
    ev = _read_event()
    event = ev.get("event") or ""
    reply = ev.get("response") or ev.get("summary") or ""
    tools = ev.get("tool_names") or []
    sid = str(ev.get("session_id") or "default")

    finding = _analyze(reply, tools, ev)
    if not finding:
        print("{}")  # nothing suspicious -> continue
        return

    reason, detail = finding
    full_reason = ("[verify-publish] %s: %s" % (reason, detail)) if detail \
        else ("[verify-publish] %s" % reason)

    # Redo-capable events -> BLOCK (force the agent to actually publish/redo),
    # capped so the agent can always finish. Past the cap, let it through with a
    # user-facing warning.
    #   on_stop             -> redo in NORMAL chat (host steers the reason back)
    #   on_completion_claim -> redo inside a /goal supervisor loop
    # Both only honor a `decision: block` from the host — a rewrite is silently
    # ignored on these events, so we must block here, never return a {"response"}.
    if event in ("on_stop", "on_completion_claim"):
        if _block_count(ev, sid) >= MAX_BLOCKS:
            print(json.dumps({
                "add_warning": ("A publish/post success claim couldn't be verified, "
                                "but the guard already nudged twice this session, so "
                                "it's letting this through. Double-check the link."),
            }, ensure_ascii=False))
            return
        _bump_block(ev, sid)
        print(json.dumps({"decision": "block", "reason": full_reason},
                         ensure_ascii=False))
        return

    # on_response_end (or anything else) -> can only REWRITE the stored reply.
    # Append an honest correction. No retry, so no loop risk.
    note = ("\n\n---\n> Unverified: I couldn't confirm this was actually "
            "published/posted (%s). Treat the link above as unconfirmed until "
            "the real publish tool has run." % (detail or reason))
    print(json.dumps({"response": reply.rstrip() + note}, ensure_ascii=False))


if __name__ == "__main__":
    main()
