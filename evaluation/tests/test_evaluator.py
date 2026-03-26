"""Tests for SkillEvaluator — the core loss function engine."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from evaluation.config import EvalConfig, GoalAnchor
from evaluation.tracker import ExecutionTracker
from evaluation.evaluator import SkillEvaluator, LossResult


def make_config(**overrides) -> EvalConfig:
    """Helper: create a valid EvalConfig with defaults."""
    defaults = dict(
        skill_name="test_skill",
        goals=[
            GoalAnchor(id="goal_a", description="Primary", weight=0.6, critical=True),
            GoalAnchor(id="goal_b", description="Secondary", weight=0.4, critical=False),
        ],
        target_steps=3,
        max_steps=10,
        token_budget=15000,
    )
    defaults.update(overrides)
    return EvalConfig(**defaults)


def make_tracker(skill: str = "test_skill") -> ExecutionTracker:
    return ExecutionTracker(skill_name=skill)


class TestPerfectRun:
    """All goals met, under step target, under token budget."""

    def test_perfect_score(self):
        config = make_config()
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        tracker.record_step("tool_1", tokens_in=500, tokens_out=500)
        tracker.record_step("tool_2", tokens_in=500, tokens_out=500)
        tracker.mark_goal("goal_a")
        tracker.mark_goal("goal_b")
        tracker.stop()

        result = evaluator.evaluate(tracker, run_id="perfect")

        assert result.l_task == 0.0
        assert result.task_score == 1.0
        assert result.l_efficiency == 0.0  # 2 steps < 3 target
        assert result.l_cost < 1.0
        assert result.total_loss < 1.0
        assert result.grade == "A"
        assert not result.critical_failure
        assert not result.needs_refactor

    def test_perfect_run_recommendations(self):
        config = make_config()
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        tracker.record_step("tool_1", tokens_in=100, tokens_out=100)
        tracker.mark_goal("goal_a")
        tracker.mark_goal("goal_b")
        tracker.stop()

        result = evaluator.evaluate(tracker)
        assert any("No action needed" in r for r in result.recommendations)


class TestCriticalFailure:
    """Critical goal missed = total task failure."""

    def test_critical_goal_missed(self):
        config = make_config()
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        tracker.record_step("tool_1", tokens_in=500, tokens_out=500)
        # goal_a is critical — NOT achieved
        tracker.mark_goal("goal_b")
        tracker.fail_goal("goal_a", "API returned 0")
        tracker.stop()

        result = evaluator.evaluate(tracker)

        assert result.critical_failure is True
        assert result.l_task == 1.0
        assert result.task_score == 0.0
        assert result.total_loss >= 10.0  # w_task=10 * l_task=1.0
        assert result.grade == "F"
        assert "goal_a" in result.goals_missed

    def test_non_critical_miss_partial_loss(self):
        config = make_config()
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        tracker.record_step("tool_1", tokens_in=500, tokens_out=500)
        tracker.mark_goal("goal_a")  # Critical, achieved
        # goal_b NOT achieved (non-critical)
        tracker.stop()

        result = evaluator.evaluate(tracker)

        assert result.critical_failure is False
        assert result.l_task == pytest.approx(0.4, abs=0.01)  # missed 40% weight
        assert result.task_score == pytest.approx(0.6, abs=0.01)


class TestEfficiencyLoss:
    """Step count optimization."""

    def test_under_target_is_zero(self):
        config = make_config(target_steps=5, max_steps=15)
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        for i in range(3):
            tracker.record_step(f"tool_{i}", tokens_in=100, tokens_out=100)
        tracker.mark_goal("goal_a")
        tracker.mark_goal("goal_b")
        tracker.stop()

        result = evaluator.evaluate(tracker)
        assert result.l_efficiency == 0.0

    def test_over_target_increases_loss(self):
        config = make_config(target_steps=3, max_steps=10)
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        for i in range(7):
            tracker.record_step(f"tool_{i}", tokens_in=100, tokens_out=100)
        tracker.mark_goal("goal_a")
        tracker.mark_goal("goal_b")
        tracker.stop()

        result = evaluator.evaluate(tracker)
        # (7 - 3) / 10 = 0.4
        assert result.l_efficiency == pytest.approx(0.4, abs=0.01)

    def test_clamped_at_1(self):
        config = make_config(target_steps=3, max_steps=5)
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        for i in range(20):  # Way over
            tracker.record_step(f"tool_{i}", tokens_in=10, tokens_out=10)
        tracker.mark_goal("goal_a")
        tracker.mark_goal("goal_b")
        tracker.stop()

        result = evaluator.evaluate(tracker)
        assert result.l_efficiency == 1.0


class TestCostLoss:
    """Token budget optimization."""

    def test_low_cost(self):
        config = make_config(token_budget=15000)
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        tracker.record_step("tool_1", tokens_in=500, tokens_out=500)
        tracker.mark_goal("goal_a")
        tracker.mark_goal("goal_b")
        tracker.stop()

        result = evaluator.evaluate(tracker)
        # 1000 / 15000 ≈ 0.067
        assert result.l_cost == pytest.approx(0.067, abs=0.01)

    def test_high_cost_clamped(self):
        config = make_config(token_budget=1000)
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        tracker.record_step("tool_1", tokens_in=5000, tokens_out=5000)
        tracker.mark_goal("goal_a")
        tracker.mark_goal("goal_b")
        tracker.stop()

        result = evaluator.evaluate(tracker)
        assert result.l_cost == 1.0


class TestGrading:
    def test_grade_scale(self):
        r = LossResult(skill_name="test")
        r.total_loss = 0.3
        assert r.grade == "A"
        r.total_loss = 1.0
        assert r.grade == "B"
        r.total_loss = 2.5
        assert r.grade == "C"
        r.total_loss = 4.0
        assert r.grade == "D"
        r.total_loss = 6.0
        assert r.grade == "F"


class TestReport:
    def test_report_contains_key_sections(self):
        config = make_config()
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        tracker.record_step("tool_1", tokens_in=500, tokens_out=500)
        tracker.mark_goal("goal_a")
        tracker.stop()

        result = evaluator.evaluate(tracker)
        report = result.report()

        assert "## Evaluation" in report
        assert "Grade:" in report
        assert "L_task" in report
        assert "L_efficiency" in report
        assert "L_cost" in report
        assert "Steps" in report
        assert "Tokens" in report

    def test_to_dict_structure(self):
        config = make_config()
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        tracker.record_step("tool_1", tokens_in=100, tokens_out=100)
        tracker.mark_goal("goal_a")
        tracker.mark_goal("goal_b")
        tracker.stop()

        result = evaluator.evaluate(tracker)
        d = result.to_dict()

        assert "breakdown" in d
        assert "metadata" in d
        assert "diagnosis" in d
        assert d["grade"] in ("A", "B", "C", "D", "F")


class TestConfigValidation:
    def test_invalid_config_raises(self):
        bad_config = EvalConfig(
            skill_name="bad",
            goals=[],  # No goals
            target_steps=10,
            max_steps=5,  # target >= max
        )
        with pytest.raises(ValueError, match="Invalid config"):
            SkillEvaluator(bad_config)

    def test_weights_not_summing_to_1(self):
        bad_config = EvalConfig(
            skill_name="bad",
            goals=[
                GoalAnchor(id="a", description="test", weight=0.3),
                GoalAnchor(id="b", description="test", weight=0.3),
            ],
        )
        errors = bad_config.validate()
        assert any("weights sum" in e for e in errors)


class TestDominantLoss:
    def test_dominant_is_task_when_failed(self):
        config = make_config()
        evaluator = SkillEvaluator(config)

        tracker = make_tracker()
        tracker.start()
        tracker.record_step("tool_1", tokens_in=100, tokens_out=100)
        tracker.fail_goal("goal_a", "failed")
        # goal_a critical, not achieved
        tracker.stop()

        result = evaluator.evaluate(tracker)
        assert result.dominant_loss == "task"
