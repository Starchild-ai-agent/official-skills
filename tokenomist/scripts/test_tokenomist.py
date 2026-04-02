#!/usr/bin/env python3
"""
Integration-style smoke test for tokenomist skill client.

Runs against live Tokenomist API through core/http_client proxied_get.
"""

from __future__ import annotations

import json
import traceback

from skills.tokenomist.tools.client import TokenomistClient, normalize_token_index, resolve_token_id


def main() -> int:
    report = {
        "ok": False,
        "tests": [],
        "errors": [],
    }

    def log_test(name: str, ok: bool, detail: str = ""):
        report["tests"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            report["errors"].append({"name": name, "detail": detail})

    try:
        c = TokenomistClient()

        # 1) token list v4
        tl = c.token_list_v4()
        data = tl.get("data") if isinstance(tl, dict) else None
        ok = isinstance(data, list) and len(data) > 0
        log_test("token_list_v4_non_empty", ok, f"count={len(data) if isinstance(data, list) else 'n/a'}")
        if not ok:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1

        idx = normalize_token_index(tl)
        log_test("normalize_index", len(idx) > 0, f"count={len(idx)}")

        # 2) resolve token using a known-ish query from first item
        first = idx[0]
        q = first.get("symbol") or first.get("id") or first.get("name")
        res = resolve_token_id(idx, q)
        ok = res.get("token") is not None
        log_test("resolve_token", ok, f"query={q} match_type={res.get('match_type')}")

        if not ok:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1

        token_id = res["token"]["id"]

        # 3) allocations v2
        alloc = c.allocations_v2(token_id)
        ok = isinstance(alloc, dict) and alloc.get("status") is True and "data" in alloc
        alloc_data = alloc.get("data", {}) if isinstance(alloc, dict) else {}
        alloc_rows = alloc_data.get("allocations", []) if isinstance(alloc_data, dict) else []
        tracked_fields = 0
        tracked_sum = 0.0
        if isinstance(alloc_rows, list):
            for row in alloc_rows:
                if isinstance(row, dict) and row.get("trackedAllocationPercentage") is not None:
                    tracked_fields += 1
                    try:
                        tracked_sum += float(row.get("trackedAllocationPercentage"))
                    except Exception:
                        pass
        log_test(
            "allocations_v2",
            ok and tracked_fields > 0,
            f"token_id={token_id} tracked_fields={tracked_fields} tracked_sum={tracked_sum:.4f}",
        )

        # 4) daily emission v2 (date window anchored to today to avoid historical-range rejects)
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        start_s = today.strftime("%Y-%m-%d")
        end_s = (today + timedelta(days=1)).strftime("%Y-%m-%d")

        de = c.daily_emission_v2(token_id, start=start_s, end=end_s)
        ok = isinstance(de, dict) and de.get("status") is True and "data" in de
        log_test("daily_emission_v2", ok, f"token_id={token_id} range={start_s}..{end_s}")

        # 5) unlock events v4
        ue = c.unlock_events_v4(token_id)
        ok = isinstance(ue, dict) and ue.get("status") is True and "data" in ue
        log_test("unlock_events_v4", ok, f"token_id={token_id}")

        report["ok"] = all(t["ok"] for t in report["tests"])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 2

    except Exception as e:
        report["errors"].append({"name": "exception", "detail": str(e), "traceback": traceback.format_exc()})
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
