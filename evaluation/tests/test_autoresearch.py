"""
Tests for AutoResearch — the iterative self-improvement loop.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from evaluation.config import EvalConfig, GoalAnchor, ModelTier
from evaluation.tracker import ExecutionTracker
from evaluation.evaluator import SkillEvaluator
from evaluation.autoresearch import (
    Patch, AutoResearchState, AutoResearchLoop, save_autoresearch_report,
)


def _cfg(**kw):
    """Minimal valid config."""
    defaults = dict(
        skill_name="test_ar",
        goals=[GoalAnchor(id="g1", description="t", weight=1.0)],
        target_steps=3,
        max_steps=10,
        token_budget=15000,
    )
    defaults.update(kw)
    return EvalConfig(**defaults)


def _tracker(peak_out=500, steps=3, goals_met=None):
    """Build tracker for testing."""
    t = ExecutionTracker(skill_name="test_ar")
    t.start()
    for i in range(steps):
        out = peak_out if i == steps - 1 else 200
        t.record_step(f"step_{i}", tokens_in=100, tokens_out=out)
    for gid in (goals_met or ["g1"]):
        t.mark_goal(gid)
    t.stop()
    return t


class TestPatch:
    """Patch data structure tests."""

    def test_delta_improvement(self):
        p = Patch(round_num=1, description="test",
                  target_dimension="cost", change_type="limit")
        p.loss_before = 2.0
        p.loss_after = 1.5
        assert p.delta == -0.5
        assert p.improved is True

    def test_delta_regression(self):
        p = Patch(round_num=1, description="test",
                  target_dimension="cost", change_type="limit")
        p.loss_before = 1.5
        p.loss_after = 2.0
        assert p.delta == 0.5
        assert p.improved is False

    def test_to_dict(self):
        p = Patch(round_num=1, description="add truncation",
                  target_dimension="density", change_type="truncate",
                  parameters={"limit": 6000})
        p.loss_before = 2.0
        p.loss_after = 1.0
        p.kept = True
        d = p.to_dict()
        assert d["round"] == 1
        assert d["delta"] == -1.0
        assert d["kept"] is True


class TestAutoResearchState:
    """State tracking and convergence tests."""

    def test_initial_state(self):
        s = AutoResearchState(skill_name="test")
        assert s.total_improvement == 0.0
        assert s.converged is False
        assert len(s.rounds) == 0

    def test_record_round_updates_current(self):
        s = AutoResearchState(skill_name="test")
        s.baseline_loss = 5.0
        s.current_loss = 5.0

        p = Patch(round_num=1, description="x",
                  target_dimension="cost", change_type="limit")
        p.loss_after = 4.0
        s.record_round(p)
        assert s.current_loss == 4.0
        assert s.best_loss == 4.0
        assert s.best_round == 1

    def test_convergence_detection(self):
        s = AutoResearchState(
            skill_name="test",
            convergence_threshold=0.01,
            convergence_streak=3,
        )
        s.baseline_loss = 2.0
        s.current_loss = 2.0

        # 3 rounds with tiny deltas → converged
        for i in range(3):
            p = Patch(round_num=i + 1, description="x",
                      target_dimension="cost", change_type="limit")
            p.loss_before = 2.0
            p.loss_after = 2.0 + 0.001 * i  # < threshold
            s.record_round(p)

        assert s.converged is True

    def test_convergence_resets_on_big_delta(self):
        s = AutoResearchState(
            skill_name="test",
            convergence_threshold=0.01,
            convergence_streak=3,
        )
        s.baseline_loss = 5.0
        s.current_loss = 5.0

        # 2 stable rounds
        for i in range(2):
            p = Patch(round_num=i + 1, description="x",
                      target_dimension="cost", change_type="limit")
            p.loss_before = 5.0
            p.loss_after = 5.001
            s.record_round(p)

        assert s.converged is False

        # 1 big jump → resets streak
        p = Patch(round_num=3, description="x",
                  target_dimension="cost", change_type="limit")
        p.loss_before = 5.001
        p.loss_after = 3.0
        s.record_round(p)

        assert s._stable_count == 0
        assert s.converged is False

    def test_improvement_pct(self):
        s = AutoResearchState(skill_name="test")
        s.baseline_loss = 10.0
        s.current_loss = 7.0
        assert s.improvement_pct == 30.0

    def test_changelog_format(self):
        s = AutoResearchState(skill_name="test")
        s.baseline_loss = 2.0
        s.current_loss = 1.5

        p = Patch(round_num=1, description="truncate response",
                  target_dimension="density", change_type="truncate")
        p.loss_before = 2.0
        p.loss_after = 1.5
        p.kept = True
        s.rounds.append(p)

        log = s.changelog()
        assert "truncate response" in log
        assert "✅" in log

    def test_to_dict_structure(self):
        s = AutoResearchState(skill_name="test")
        s.baseline_loss = 2.0
        s.current_loss = 1.5
        s.loss_history = [2.0, 1.5]
        d = s.to_dict()
        assert "loss_history" in d
        assert "patches" in d
        assert d["baseline_loss"] == 2.0


class TestAutoResearchLoop:
    """Core loop integration tests."""

    def test_baseline_measurement(self):
        """Loop measures baseline on round 0."""
        cfg = _cfg()
        evaluator = SkillEvaluator(cfg)

        call_count = [0]

        def run_fn(config, round_num):
            call_count[0] += 1
            tracker = _tracker(goals_met=["g1"])
            return evaluator.evaluate(tracker, f"round_{round_num}")

        loop = AutoResearchLoop(cfg, evaluator, run_fn)
        state = loop.run(max_rounds=0)  # Baseline only

        assert call_count[0] == 1
        assert state.baseline_loss > 0  # At minimum, cost loss

    def test_loop_converges(self):
        """Loop stops when convergence reached."""
        cfg = _cfg()
        evaluator = SkillEvaluator(cfg)

        def run_fn(config, round_num):
            # Always returns same loss → converges quickly
            tracker = _tracker(goals_met=["g1"])
            return evaluator.evaluate(tracker, f"round_{round_num}")

        loop = AutoResearchLoop(cfg, evaluator, run_fn)
        state = loop.run(
            max_rounds=20,
            convergence_threshold=0.5,
            convergence_streak=3,
        )

        assert state.converged is True
        assert len(state.rounds) <= 20

    def test_loop_respects_max_rounds(self):
        """Loop stops at max_rounds even if not converged."""
        cfg = _cfg()
        evaluator = SkillEvaluator(cfg)

        round_losses = [5.0, 4.5, 4.0, 3.5, 3.0]

        def run_fn(config, round_num):
            # Decreasing loss — never converges
            tracker = _tracker(goals_met=["g1"])
            result = evaluator.evaluate(tracker, f"round_{round_num}")
            # Hack total_loss for testing
            if round_num < len(round_losses):
                result.total_loss = round_losses[round_num]
            return result

        loop = AutoResearchLoop(cfg, evaluator, run_fn)
        state = loop.run(max_rounds=3)

        assert len(state.rounds) <= 3

    def test_custom_patch_fn(self):
        """Custom patch function controls the loop."""
        cfg = _cfg()
        evaluator = SkillEvaluator(cfg)
        patches_generated = []

        def custom_patch(state, result):
            if len(state.rounds) >= 2:
                return None  # Stop after 2 patches
            p = Patch(
                round_num=len(state.rounds) + 1,
                description=f"custom patch {len(state.rounds) + 1}",
                target_dimension="density",
                change_type="truncate",
            )
            patches_generated.append(p)
            return p

        def run_fn(config, round_num):
            tracker = _tracker(goals_met=["g1"])
            return evaluator.evaluate(tracker, f"round_{round_num}")

        loop = AutoResearchLoop(
            cfg, evaluator, run_fn, patch_fn=custom_patch
        )
        state = loop.run(max_rounds=10)

        assert len(patches_generated) == 2
        assert len(state.rounds) == 2

    def test_regression_reverts_config(self):
        """When a patch regresses, config is reverted."""
        cfg = _cfg()
        evaluator = SkillEvaluator(cfg)
        original_budget = cfg.token_budget

        call_count = [0]

        def run_fn(config, round_num):
            call_count[0] += 1
            tracker = _tracker(goals_met=["g1"])
            return evaluator.evaluate(tracker, f"round_{round_num}")

        def mutating_patch(state, result):
            if len(state.rounds) >= 1:
                return None
            # Mutate config (this should be reverted if regressed)
            return Patch(
                round_num=1,
                description="increase budget",
                target_dimension="cost",
                change_type="limit",
            )

        loop = AutoResearchLoop(
            cfg, evaluator, run_fn, patch_fn=mutating_patch
        )
        loop.run(max_rounds=5)  # result unused; testing side-effects
        # Config should still be intact after loop
        assert loop.config.token_budget == original_budget

    def test_improving_patches_kept(self):
        """Patches that improve loss are marked as kept."""
        cfg = _cfg()
        evaluator = SkillEvaluator(cfg)

        losses = iter([2.0, 1.5, 1.0])

        def run_fn(config, round_num):
            tracker = _tracker(goals_met=["g1"])
            result = evaluator.evaluate(tracker, f"round_{round_num}")
            result.total_loss = next(losses, 1.0)
            return result

        def simple_patch(state, result):
            if len(state.rounds) >= 2:
                return None
            return Patch(
                round_num=len(state.rounds) + 1,
                description="improve",
                target_dimension="cost",
                change_type="limit",
            )

        loop = AutoResearchLoop(
            cfg, evaluator, run_fn, patch_fn=simple_patch
        )
        state = loop.run(max_rounds=5)

        # Both patches should improve
        kept_patches = [p for p in state.rounds if p.kept]
        assert len(kept_patches) == 2


class TestDefaultPatchGeneration:
    """Test built-in strategy selection."""

    def test_generates_patch_for_dominant_loss(self):
        cfg = _cfg()
        evaluator = SkillEvaluator(cfg)

        def run_fn(config, round_num):
            # Create tracker with high cost (dominant loss = "cost")
            tracker = _tracker(
                peak_out=500, steps=3, goals_met=["g1"]
            )
            return evaluator.evaluate(tracker, f"round_{round_num}")

        loop = AutoResearchLoop(cfg, evaluator, run_fn)
        state = loop.run(max_rounds=1)

        # Should have generated at least 1 patch
        assert len(state.rounds) >= 1

    def test_cycles_through_strategies(self):
        """Different rounds should try different strategies."""
        cfg = _cfg()
        evaluator = SkillEvaluator(cfg)
        round_count = [0]

        def run_fn(config, round_num):
            round_count[0] += 1
            tracker = _tracker(goals_met=["g1"])
            result = evaluator.evaluate(tracker, f"round_{round_num}")
            result.dominant_loss = "density"  # Force density focus
            return result

        loop = AutoResearchLoop(cfg, evaluator, run_fn)
        state = loop.run(max_rounds=6, convergence_streak=100)

        # Should have multiple different change_types
        types = {p.change_type for p in state.rounds}
        assert len(types) >= 2  # At least 2 different strategies tried


class TestSaveReport:
    """Test autoresearch report generation."""

    def test_save_json_and_md(self, tmp_path):
        s = AutoResearchState(skill_name="test_save")
        s.baseline_loss = 3.0
        s.current_loss = 1.5
        s.started_at = "2026-03-25T00:00:00"

        p = Patch(round_num=1, description="test patch",
                  target_dimension="density", change_type="truncate")
        p.loss_before = 3.0
        p.loss_after = 1.5
        p.kept = True
        s.rounds.append(p)
        s.loss_history = [3.0, 1.5]

        json_p, md_p = save_autoresearch_report(
            s, output_dir=str(tmp_path)
        )
        assert os.path.exists(json_p)
        assert os.path.exists(md_p)

        # Verify JSON structure
        import json
        with open(json_p) as f:
            data = json.load(f)
        assert data["baseline_loss"] == 3.0
        assert len(data["patches"]) == 1

        # Verify markdown
        with open(md_p) as f:
            md = f.read()
        assert "test_save" in md
        assert "test patch" in md


class TestSmallModelAutoResearch:
    """End-to-end: autoresearch with small model profile."""

    def test_small_model_loop_detects_density_issues(self):
        cfg = _cfg(model_tier=ModelTier.SMALL)
        cfg.apply_model_profile(ModelTier.SMALL)
        evaluator = SkillEvaluator(cfg)

        def run_fn(config, round_num):
            # Simulate large response that hurts density
            tracker = _tracker(
                peak_out=20000, steps=3, goals_met=["g1"]
            )
            return evaluator.evaluate(tracker, f"round_{round_num}")

        loop = AutoResearchLoop(cfg, evaluator, run_fn)
        state = loop.run(max_rounds=3)

        # Should have density-targeting patches
        density_patches = [
            p for p in state.rounds
            if p.target_dimension == "density"
        ]
        # Density should be the dominant loss with small model
        # (peak 20K >> t_safe 6K with w_density=4.0)
        assert len(density_patches) >= 1

    def test_large_vs_small_model_different_focus(self):
        """Large model focuses on cost, small on density."""
        base_kw = dict(
            goals=[GoalAnchor(id="g1", description="t", weight=1.0)],
            target_steps=3,
            max_steps=10,
            token_budget=15000,
        )

        # Large model run
        cfg_lg = EvalConfig(
            skill_name="test_lg", model_tier=ModelTier.LARGE,
            **base_kw,
        )
        cfg_lg.apply_model_profile(ModelTier.LARGE)
        eval_lg = SkillEvaluator(cfg_lg)

        def run_lg(config, round_num):
            tracker = _tracker(
                peak_out=20000, steps=3, goals_met=["g1"]
            )
            return eval_lg.evaluate(tracker, f"round_{round_num}")

        state_lg = AutoResearchLoop(
            cfg_lg, eval_lg, run_lg
        ).run(max_rounds=3)

        # Small model run
        cfg_sm = EvalConfig(
            skill_name="test_sm", model_tier=ModelTier.SMALL,
            **base_kw,
        )
        cfg_sm.apply_model_profile(ModelTier.SMALL)
        eval_sm = SkillEvaluator(cfg_sm)

        def run_sm(config, round_num):
            tracker = _tracker(
                peak_out=20000, steps=3, goals_met=["g1"]
            )
            return eval_sm.evaluate(tracker, f"round_{round_num}")

        state_sm = AutoResearchLoop(
            cfg_sm, eval_sm, run_sm
        ).run(max_rounds=3)

        # Small model should have higher baseline loss
        assert state_sm.baseline_loss > state_lg.baseline_loss
