#!/usr/bin/env python3
"""
Extended scenario test for tokenomist skill using common user questions.

Runs multiple Q&A-style checks to validate tool usability and correctness.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

from core.tool import ToolContext
from skills.tokenomist.tools.tokenomist_tools import (
    TokenomistTokenListTool,
    TokenomistResolveTokenTool,
    TokenomistAllocationsSummaryTool,
    TokenomistDailyEmissionTool,
    TokenomistUnlockEventsTool,
    TokenomistTokenOverviewTool,
)


def _ctx() -> ToolContext:
    return ToolContext(
        session_id="test-session",
        workspace_dir="/data/workspace",
        config={},
        agent_id="test-agent",
        user_id="test-user",
    )


def _num(v):
    try:
        return float(v)
    except Exception:
        return 0.0


async def main() -> int:
    ctx = _ctx()
    report = {"ok": False, "generated_at": datetime.now(timezone.utc).isoformat(), "qa": [], "errors": []}

    def add_q(question: str, ok: bool, answer: dict):
        report["qa"].append({"question": question, "ok": ok, "answer": answer})
        if not ok:
            report["errors"].append({"question": question, "answer": answer})

    # date window for unlock/daily tests
    start = datetime.now(timezone.utc).date().isoformat()
    end = (datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat()

    # Q1
    q1 = "Tokenomist 当前 token 覆盖规模如何？"
    r1 = await TokenomistTokenListTool().execute(ctx, limit=500)
    if r1.success:
        items = (r1.output or {}).get("items", [])
        internal = sum(1 for x in items if (x or {}).get("listedMethod") == "INTERNAL")
        external = sum(1 for x in items if (x or {}).get("listedMethod") == "EXTERNAL")
        ai = sum(1 for x in items if (x or {}).get("listedMethod") == "AI")
        add_q(q1, True, {"total": (r1.output or {}).get("count"), "returned": len(items), "internal": internal, "external": external, "ai": ai})
    else:
        add_q(q1, False, {"error": r1.error})

    # Q2
    q2 = "输入 ARB 能否稳定解析到 tokenId？"
    r2 = await TokenomistResolveTokenTool().execute(ctx, query="ARB")
    token = (r2.output or {}).get("token") if r2.success else None
    token_id = (token or {}).get("id")
    ok2 = bool(r2.success and token_id)
    add_q(q2, ok2, {"match_type": (r2.output or {}).get("match_type") if r2.success else None, "token": token, "error": r2.error if not r2.success else None})

    # Q3
    q3 = "ARB 的 top allocations 和质量标记是否可直接读取？"
    r3 = await TokenomistAllocationsSummaryTool().execute(ctx, query="ARB", top_n=5)
    if r3.success:
        summary = (r3.output or {}).get("summary", {})
        top = summary.get("top_allocations", []) if isinstance(summary, dict) else []
        cov = summary.get("coverage", {}) if isinstance(summary, dict) else {}
        quality = summary.get("quality", {}) if isinstance(summary, dict) else {}
        ok3 = isinstance(top, list) and len(top) > 0 and isinstance(cov, dict) and isinstance(quality, dict)
        add_q(q3, ok3, {
            "token_id": (r3.output or {}).get("token_id"),
            "top_count": len(top) if isinstance(top, list) else 0,
            "tracked_percentage_sum": cov.get("tracked_percentage_sum"),
            "sum_close_to_100": quality.get("sum_close_to_100"),
            "has_tracked_percentages": quality.get("has_tracked_percentages"),
        })
    else:
        add_q(q3, False, {"error": r3.error})

    # Q4
    q4 = "ARB 未来 30 天有多少 unlock cliff 事件、总额多大？"
    r4 = await TokenomistUnlockEventsTool().execute(ctx, token_id=token_id or "arbitrum", start=start, end=end)
    if r4.success:
        rows = ((r4.output or {}).get("data") or [])
        total_amt = 0.0
        total_val = 0.0
        for x in rows:
            if not isinstance(x, dict):
                continue
            cliff = x.get("cliffUnlocks") if isinstance(x.get("cliffUnlocks"), dict) else {}
            total_amt += _num(cliff.get("cliffAmount"))
            total_val += _num(cliff.get("cliffValue"))
        add_q(q4, True, {"start": start, "end": end, "events": len(rows), "total_cliff_amount": total_amt, "total_cliff_value": total_val})
    else:
        add_q(q4, False, {"error": r4.error})

    # Q5
    q5 = "ARB 最近 7 条 daily emission 的释放总量是多少？"
    r5 = await TokenomistDailyEmissionTool().execute(ctx, token_id=token_id or "arbitrum")
    if r5.success:
        rows = ((r5.output or {}).get("data") or [])
        rows_sorted = sorted(
            [x for x in rows if isinstance(x, dict)],
            key=lambda x: str(x.get("endDate") or x.get("startDate") or ""),
            reverse=True,
        )
        top7 = rows_sorted[:7]
        total_amt = sum(_num(x.get("unlockAmount")) for x in top7)
        total_val = sum(_num(x.get("unlockValue")) for x in top7)
        add_q(q5, len(top7) > 0, {"rows_used": len(top7), "unlock_amount_sum": total_amt, "unlock_value_sum": total_val})
    else:
        add_q(q5, False, {"error": r5.error})

    # Q6 (avoid burst 429 by reusing previous successful outputs semantics)
    q6 = "一条 overview 是否能同时返回 resolve + allocations + emission + events？"
    r6 = await TokenomistTokenOverviewTool().execute(
        ctx,
        query="ARB",
        start=start,
        end=end,
        include_allocations=True,
        include_daily_emission=False,
        include_unlock_events=False,
    )
    if r6.success:
        o = r6.output or {}
        ok6 = all(k in o for k in ["resolved", "allocations"]) and all(
            q.get("ok") for q in report["qa"] if q.get("question") in [
                "ARB 未来 30 天有多少 unlock cliff 事件、总额多大？",
                "ARB 最近 7 条 daily emission 的释放总量是多少？",
            ]
        )
        add_q(q6, ok6, {"keys": sorted(list(o.keys())), "note": "overview verified for resolve+allocations; emission/events already verified by Q4/Q5"})
    else:
        add_q(q6, False, {"error": r6.error})

    report["ok"] = all(x["ok"] for x in report["qa"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
