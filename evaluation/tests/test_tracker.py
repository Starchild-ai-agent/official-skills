"""Tests for ExecutionTracker."""

import sys
import os
import time
import pytest

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from evaluation.tracker import ExecutionTracker, StepRecord


class TestStepRecord:
    def test_total_tokens(self):
        step = StepRecord(step_num=1, tool_name="test", tokens_in=500, tokens_out=300)
        assert step.total_tokens() == 800

    def test_to_dict_truncates_result(self):
        step = StepRecord(step_num=1, tool_name="test", result_summary="x" * 300)
        d = step.to_dict()
        assert len(d["result"]) == 200

    def test_to_dict_structure(self):
        step = StepRecord(step_num=1, tool_name="funding_rate", args_summary="BTC")
        d = step.to_dict()
        assert d["step"] == 1
        assert d["tool"] == "funding_rate"
        assert d["args"] == "BTC"
        assert d["success"] is True
        assert "tokens" in d


class TestExecutionTracker:
    def test_start_stop(self):
        t = ExecutionTracker(skill_name="coinglass")
        t.start()
        assert t._running is True
        time.sleep(0.01)
        t.stop()
        assert t._running is False
        assert t.wall_time_ms > 0

    def test_record_step(self):
        t = ExecutionTracker(skill_name="test")
        t.start()
        step = t.record_step("tool_a", args="arg1", tokens_in=100, tokens_out=200)
        assert step.step_num == 1
        assert t.step_count == 1
        assert t.total_tokens == 300

    def test_multiple_steps(self):
        t = ExecutionTracker(skill_name="test")
        t.start()
        t.record_step("tool_a", tokens_in=100, tokens_out=200)
        t.record_step("tool_b", tokens_in=150, tokens_out=250)
        t.record_step("tool_c", tokens_in=50, tokens_out=100, success=False, error="timeout")
        t.stop()

        assert t.step_count == 3
        assert t.total_tokens == 850
        assert t.total_tokens_in == 300
        assert t.total_tokens_out == 550
        assert len(t.failed_steps) == 1

    def test_goals(self):
        t = ExecutionTracker(skill_name="test")
        t.start()
        t.mark_goal("goal_a")
        t.mark_goal("goal_b")
        t.fail_goal("goal_c", "API returned 500")
        t.stop()

        assert "goal_a" in t.goals_achieved
        assert "goal_b" in t.goals_achieved
        assert "goal_c" in t.goals_failed
        assert t.goals_failed["goal_c"] == "API returned 500"

    def test_summary_structure(self):
        t = ExecutionTracker(skill_name="coinglass")
        t.start()
        t.record_step("funding_rate", args="BTC", tokens_in=500, tokens_out=800)
        t.mark_goal("fetch_data")
        t.stop()

        s = t.summary()
        assert s["skill"] == "coinglass"
        assert s["steps"] == 1
        assert s["total_tokens"] == 1300
        assert "fetch_data" in s["goals_achieved"]
        assert len(s["step_details"]) == 1

    def test_idempotent_goals(self):
        """Marking the same goal twice shouldn't duplicate."""
        t = ExecutionTracker(skill_name="test")
        t.start()
        t.mark_goal("goal_a")
        t.mark_goal("goal_a")
        assert len(t.goals_achieved) == 1

    def test_wall_time_while_running(self):
        """wall_time_ms should work even before stop()."""
        t = ExecutionTracker(skill_name="test")
        t.start()
        time.sleep(0.01)
        assert t.wall_time_ms > 0
