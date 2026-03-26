"""
Tests for L_density computation and small-model adaptation.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from evaluation.config import (  # noqa: E402
    EvalConfig, GoalAnchor, ModelTier, DensityConfig,
    MODEL_WEIGHT_PROFILES,
)
from evaluation.tracker import ExecutionTracker  # noqa: E402
from evaluation.evaluator import SkillEvaluator  # noqa: E402


def _make_config(tier=ModelTier.LARGE, density=None):
    """Helper: minimal valid config for density testing."""
    cfg = EvalConfig(
        skill_name="test_density",
        goals=[GoalAnchor(id="g1", description="test", weight=1.0)],
        target_steps=3,
        max_steps=10,
        token_budget=15000,
        model_tier=tier,
    )
    if density:
        cfg.density = density
    return cfg


def _make_tracker(
    peak_out_tokens=500,
    num_steps=3,
    goals_met=None
):
    """Helper: build tracker with controllable peak response."""
    tracker = ExecutionTracker(skill_name="test_density")
    tracker.start()
    for i in range(num_steps):
        # Last step has peak tokens
        out = peak_out_tokens if i == num_steps - 1 else 200
        tracker.record_step(
            tool_name=f"step_{i}",
            tokens_in=100,
            tokens_out=out,
        )
    for gid in (goals_met or ["g1"]):
        tracker.mark_goal(gid)
    tracker.stop()
    return tracker


class TestDensityLoss:
    """Test L_density computation at different response sizes."""

    def test_zero_when_below_threshold(self):
        cfg = _make_config(density=DensityConfig(
            t_safe=6000, t_limit=32000
        ))
        evaluator = SkillEvaluator(cfg)
        tracker = _make_tracker(peak_out_tokens=5000)
        result = evaluator.evaluate(tracker)
        assert result.l_density == 0.0

    def test_zero_at_exact_threshold(self):
        cfg = _make_config(density=DensityConfig(
            t_safe=6000, t_limit=32000
        ))
        evaluator = SkillEvaluator(cfg)
        tracker = _make_tracker(peak_out_tokens=6000)
        result = evaluator.evaluate(tracker)
        assert result.l_density == 0.0

    def test_positive_above_threshold(self):
        cfg = _make_config(density=DensityConfig(
            t_safe=6000, t_limit=32000
        ))
        evaluator = SkillEvaluator(cfg)
        tracker = _make_tracker(peak_out_tokens=10000)
        result = evaluator.evaluate(tracker)
        expected = (10000 - 6000) / 32000  # 0.125
        assert abs(result.l_density - expected) < 0.001

    def test_capped_at_one(self):
        cfg = _make_config(density=DensityConfig(
            t_safe=6000, t_limit=32000
        ))
        evaluator = SkillEvaluator(cfg)
        tracker = _make_tracker(peak_out_tokens=100000)
        result = evaluator.evaluate(tracker)
        assert result.l_density == 1.0

    def test_disabled_returns_zero(self):
        cfg = _make_config(density=DensityConfig(
            t_safe=6000, t_limit=32000, enabled=False
        ))
        evaluator = SkillEvaluator(cfg)
        tracker = _make_tracker(peak_out_tokens=50000)
        result = evaluator.evaluate(tracker)
        assert result.l_density == 0.0

    def test_density_contributes_to_total_loss(self):
        cfg = _make_config(
            density=DensityConfig(t_safe=6000, t_limit=32000)
        )
        cfg.w_density = 4.0
        evaluator = SkillEvaluator(cfg)
        tracker = _make_tracker(peak_out_tokens=10000)
        result = evaluator.evaluate(tracker)
        assert result.wl_density == 4.0 * result.l_density
        assert result.total_loss >= result.wl_density


class TestModelProfiles:
    """Test tier-based weight profiles."""

    def test_small_model_has_highest_density_weight(self):
        w_large = MODEL_WEIGHT_PROFILES[ModelTier.LARGE]
        w_small = MODEL_WEIGHT_PROFILES[ModelTier.SMALL]
        assert w_small[3] > w_large[3]  # density weight

    def test_small_model_has_higher_efficiency_weight(self):
        w_large = MODEL_WEIGHT_PROFILES[ModelTier.LARGE]
        w_small = MODEL_WEIGHT_PROFILES[ModelTier.SMALL]
        assert w_small[1] > w_large[1]  # efficiency weight

    def test_task_weight_constant_across_tiers(self):
        for tier in ModelTier:
            assert MODEL_WEIGHT_PROFILES[tier][0] == 10.0

    def test_apply_model_profile(self):
        cfg = _make_config()
        cfg.apply_model_profile(ModelTier.SMALL)
        assert cfg.w_density == 5.0
        assert cfg.w_efficiency == 3.0
        assert cfg.density.t_safe == 6000
        assert cfg.density.t_limit == 32000

    def test_apply_model_profile_medium(self):
        cfg = _make_config()
        cfg.apply_model_profile(ModelTier.MEDIUM)
        assert cfg.w_density == 3.0
        assert cfg.w_efficiency == 2.5

    def test_density_config_for_tier(self):
        small = DensityConfig.for_tier(ModelTier.SMALL)
        large = DensityConfig.for_tier(ModelTier.LARGE)
        assert small.t_safe < large.t_safe
        assert small.t_limit < large.t_limit


class TestSmallModelScenarios:
    """End-to-end: same execution, different model tiers."""

    def test_small_model_penalizes_large_responses_more(self):
        base = dict(
            goals=[GoalAnchor(id="g1", description="t", weight=1.0)],
            target_steps=3,
            max_steps=10,
            token_budget=15000,
        )
        cfg_large = EvalConfig(
            skill_name="test",
            model_tier=ModelTier.LARGE,
            **base,
        )
        cfg_large.apply_model_profile(ModelTier.LARGE)

        cfg_small = EvalConfig(
            skill_name="test",
            model_tier=ModelTier.SMALL,
            **base,
        )
        cfg_small.apply_model_profile(ModelTier.SMALL)

        # Same execution: peak 20K tokens (way above small safe)
        tracker = _make_tracker(peak_out_tokens=20000)

        r_large = SkillEvaluator(cfg_large).evaluate(tracker)
        r_small = SkillEvaluator(cfg_small).evaluate(tracker)

        # Small model should have HIGHER total loss
        assert r_small.total_loss > r_large.total_loss
        # And specifically, density weighted loss should be higher
        assert r_small.wl_density > r_large.wl_density

    def test_efficient_execution_benefits_small_model(self):
        """Small responses + few steps = low loss on small model."""
        cfg = _make_config(tier=ModelTier.SMALL)
        cfg.apply_model_profile(ModelTier.SMALL)

        # Lean execution: 2 steps, 2000 token peak
        tracker = _make_tracker(
            peak_out_tokens=2000, num_steps=2
        )
        result = SkillEvaluator(cfg).evaluate(tracker)
        assert result.l_density == 0.0  # Below safe threshold
        assert result.grade in ("A", "B")


class TestDensityInReport:
    """Verify L_density shows up in output formats."""

    def test_density_in_to_dict(self):
        cfg = _make_config(
            density=DensityConfig(t_safe=6000, t_limit=32000)
        )
        cfg.w_density = 4.0
        evaluator = SkillEvaluator(cfg)
        tracker = _make_tracker(peak_out_tokens=10000)
        result = evaluator.evaluate(tracker)
        d = result.to_dict()
        assert "L_density" in d["breakdown"]
        assert "W_density" in d["breakdown"]["weighted"]
        assert d["metadata"]["peak_tokens"] == 10000

    def test_density_in_report_markdown(self):
        cfg = _make_config(
            density=DensityConfig(t_safe=6000, t_limit=32000)
        )
        evaluator = SkillEvaluator(cfg)
        tracker = _make_tracker(peak_out_tokens=10000)
        result = evaluator.evaluate(tracker)
        report = result.report()
        assert "L_density" in report
        assert "Peak response" in report

    def test_model_tier_in_report(self):
        cfg = _make_config(tier=ModelTier.SMALL)
        evaluator = SkillEvaluator(cfg)
        tracker = _make_tracker(peak_out_tokens=100)
        result = evaluator.evaluate(tracker)
        assert result.model_tier == "small"
        assert "small" in result.report()


class TestTrackerDensityMetrics:
    """Verify tracker correctly tracks peak/avg response sizes."""

    def test_peak_response_tokens(self):
        tracker = ExecutionTracker(skill_name="test")
        tracker.start()
        tracker.record_step("a", tokens_in=100, tokens_out=500)
        tracker.record_step("b", tokens_in=100, tokens_out=8000)
        tracker.record_step("c", tokens_in=100, tokens_out=300)
        tracker.stop()
        assert tracker.peak_response_tokens == 8000

    def test_avg_response_tokens(self):
        tracker = ExecutionTracker(skill_name="test")
        tracker.start()
        tracker.record_step("a", tokens_in=100, tokens_out=300)
        tracker.record_step("b", tokens_in=100, tokens_out=600)
        tracker.record_step("c", tokens_in=100, tokens_out=900)
        tracker.stop()
        assert tracker.avg_response_tokens == 600.0

    def test_empty_tracker(self):
        tracker = ExecutionTracker(skill_name="test")
        assert tracker.peak_response_tokens == 0
        assert tracker.avg_response_tokens == 0.0

    def test_summary_includes_density(self):
        tracker = ExecutionTracker(skill_name="test")
        tracker.start()
        tracker.record_step("a", tokens_in=100, tokens_out=5000)
        tracker.stop()
        s = tracker.summary()
        assert "peak_response_tokens" in s
        assert s["peak_response_tokens"] == 5000


class TestDensityConfigSerialization:
    """Test save/load roundtrip with density fields."""

    def test_config_roundtrip(self, tmp_path):
        cfg = _make_config(tier=ModelTier.SMALL)
        cfg.apply_model_profile(ModelTier.SMALL)

        path = str(tmp_path / "test.json")
        cfg.save(path)

        loaded = EvalConfig.load(path)
        assert loaded.model_tier == ModelTier.SMALL
        assert loaded.w_density == 5.0
        assert loaded.density.t_safe == 6000
        assert loaded.density.t_limit == 32000

    def test_legacy_config_loads_defaults(self, tmp_path):
        """Old configs without density fields still load."""
        import json
        legacy = {
            "skill_name": "old_skill",
            "goals": [{"id": "g1", "description": "t",
                       "weight": 1.0}],
            "weights": {"task": 10, "efficiency": 2, "cost": 1},
        }
        path = str(tmp_path / "legacy.json")
        with open(path, "w") as f:
            json.dump(legacy, f)

        loaded = EvalConfig.load(path)
        assert loaded.w_density == 1.0  # Default
        assert loaded.density.t_safe == 6000
        assert loaded.model_tier == ModelTier.LARGE
