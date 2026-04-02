#!/usr/bin/env python3
"""
Integration test for tokenomist tool wrappers (not just raw client).

Validates:
- tokenomist_allocations normalized output exists
- trackedAllocationPercentage is consumed correctly
- coverage flags are present
"""

from __future__ import annotations

import asyncio
import json
import traceback

from core.tool import ToolContext
from skills.tokenomist.tools.tokenomist_tools import (
    TokenomistResolveTokenTool,
    TokenomistAllocationsTool,
    TokenomistAllocationsSummaryTool,
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


async def main() -> int:
    report = {"ok": False, "tests": [], "errors": []}

    def t(name: str, ok: bool, detail: str = ""):
        report["tests"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            report["errors"].append({"name": name, "detail": detail})

    try:
        ctx = _ctx()

        # Resolve token
        r = await TokenomistResolveTokenTool().execute(ctx, query="ARB")
        t("resolve_success", r.success, str(r.error or ""))
        if not r.success:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1

        token = (r.output or {}).get("token")
        token_id = (token or {}).get("id")
        t("resolve_token_id_present", bool(token_id), f"token_id={token_id}")
        if not token_id:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1

        # Allocations normalized output
        a = await TokenomistAllocationsTool().execute(ctx, token_id=token_id)
        t("allocations_success", a.success, str(a.error or ""))
        if not a.success:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1

        out = a.output or {}
        norm = out.get("normalized") if isinstance(out, dict) else None
        t("allocations_normalized_present", isinstance(norm, dict), "normalized dict expected")

        top = norm.get("top_allocations") if isinstance(norm, dict) else None
        cov = norm.get("coverage") if isinstance(norm, dict) else None

        t("top_allocations_present", isinstance(top, list), f"type={type(top).__name__}")
        t("coverage_present", isinstance(cov, dict), f"type={type(cov).__name__}")

        if isinstance(cov, dict):
            tracked_fields = cov.get("tracked_percentage_fields", 0)
            tracked_sum = cov.get("tracked_percentage_sum", 0)
            t("tracked_fields_positive", isinstance(tracked_fields, int) and tracked_fields > 0, str(tracked_fields))
            t(
                "tracked_sum_reasonable",
                isinstance(tracked_sum, (int, float)) and 80 <= float(tracked_sum) <= 120,
                str(tracked_sum),
            )

        # Allocations summary wrapper
        s = await TokenomistAllocationsSummaryTool().execute(ctx, query="ARB", top_n=5)
        t("allocations_summary_success", s.success, str(s.error or ""))
        s_out = s.output or {}
        s_summary = s_out.get("summary") if isinstance(s_out, dict) else None
        s_top = (s_summary or {}).get("top_allocations") if isinstance(s_summary, dict) else None
        s_quality = (s_summary or {}).get("quality") if isinstance(s_summary, dict) else None
        t("allocations_summary_top_present", isinstance(s_top, list) and len(s_top) > 0, f"len={len(s_top) if isinstance(s_top, list) else -1}")
        t("allocations_summary_quality_present", isinstance(s_quality, dict), f"type={type(s_quality).__name__}")

        # Overview includes normalized allocations
        ov = await TokenomistTokenOverviewTool().execute(
            ctx,
            query="ARB",
            include_allocations=True,
            include_daily_emission=False,
            include_unlock_events=False,
        )
        t("overview_success", ov.success, str(ov.error or ""))
        ov_alloc = ((ov.output or {}).get("allocations") or {}).get("normalized") if isinstance(ov.output, dict) else None
        t("overview_allocations_normalized", isinstance(ov_alloc, dict), "overview normalized expected")

        report["ok"] = all(x["ok"] for x in report["tests"])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 2

    except Exception as e:
        report["errors"].append({"name": "exception", "detail": str(e), "traceback": traceback.format_exc()})
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
