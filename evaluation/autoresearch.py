"""
AutoResearch — Iterative self-improvement loop for skills.

Inspired by Karpathy's autoresearch method:
  1. Run skill under evaluation → measure loss
  2. Identify dominant loss dimension
  3. Generate a targeted patch (one change at a time)
  4. Re-evaluate → keep if improved, revert if regressed
  5. Repeat until convergence or max rounds

This module defines the loop controller and patch tracking.
Actual skill execution is delegated to the runner.
"""

import json
import copy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from evaluation.config import EvalConfig
from evaluation.evaluator import SkillEvaluator, LossResult


@dataclass
class Patch:
    """A single atomic change attempted during autoresearch."""
    round_num: int
    description: str
    target_dimension: str       # "task", "efficiency", "cost", "density"
    change_type: str            # "add_rule", "truncate", "batch", "filter"
    parameters: dict = field(default_factory=dict)

    # Results
    loss_before: float = 0.0
    loss_after: float = 0.0
    kept: bool = False
    reason: str = ""

    @property
    def delta(self) -> float:
        """Negative = improved, positive = regressed."""
        return self.loss_after - self.loss_before

    @property
    def improved(self) -> bool:
        return self.delta < 0

    def to_dict(self) -> dict:
        return {
            "round": self.round_num,
            "description": self.description,
            "target": self.target_dimension,
            "type": self.change_type,
            "params": self.parameters,
            "loss_before": round(self.loss_before, 4),
            "loss_after": round(self.loss_after, 4),
            "delta": round(self.delta, 4),
            "kept": self.kept,
            "reason": self.reason,
        }


@dataclass
class AutoResearchState:
    """Tracks the full autoresearch session state."""
    skill_name: str
    started_at: str = ""
    max_rounds: int = 10
    convergence_threshold: float = 0.01  # Stop if delta < this
    convergence_streak: int = 3          # Need N consecutive stable

    # History
    rounds: list = field(default_factory=list)  # List[Patch]
    loss_history: list = field(default_factory=list)  # float per round
    baseline_loss: float = 0.0
    current_loss: float = 0.0
    best_loss: float = float("inf")
    best_round: int = 0

    # Convergence tracking
    _stable_count: int = 0

    @property
    def total_improvement(self) -> float:
        if self.baseline_loss == 0:
            return 0.0
        return self.baseline_loss - self.current_loss

    @property
    def improvement_pct(self) -> float:
        if self.baseline_loss == 0:
            return 0.0
        return (self.total_improvement / self.baseline_loss) * 100

    @property
    def converged(self) -> bool:
        return self._stable_count >= self.convergence_streak

    def record_round(self, patch: Patch):
        self.rounds.append(patch)
        self.loss_history.append(patch.loss_after)
        self.current_loss = patch.loss_after

        if patch.loss_after < self.best_loss:
            self.best_loss = patch.loss_after
            self.best_round = patch.round_num

        # Check convergence
        if abs(patch.delta) < self.convergence_threshold:
            self._stable_count += 1
        else:
            self._stable_count = 0

    def summary(self) -> dict:
        return {
            "skill": self.skill_name,
            "started_at": self.started_at,
            "rounds_completed": len(self.rounds),
            "baseline_loss": round(self.baseline_loss, 4),
            "current_loss": round(self.current_loss, 4),
            "best_loss": round(self.best_loss, 4),
            "best_round": self.best_round,
            "improvement": f"{self.improvement_pct:.1f}%",
            "converged": self.converged,
            "patches_kept": sum(1 for p in self.rounds if p.kept),
            "patches_reverted": sum(
                1 for p in self.rounds if not p.kept
            ),
        }

    def changelog(self) -> str:
        """Markdown changelog of all attempted patches."""
        lines = [
            f"# AutoResearch Changelog: {self.skill_name}",
            f"**Baseline**: {self.baseline_loss:.4f} → "
            f"**Final**: {self.current_loss:.4f} "
            f"({self.improvement_pct:+.1f}%)",
            "",
            "| Round | Target | Change | Δ Loss | Kept? |",
            "|-------|--------|--------|--------|-------|",
        ]
        for p in self.rounds:
            icon = "✅" if p.kept else "❌"
            lines.append(
                f"| {p.round_num} | {p.target_dimension} | "
                f"{p.description[:40]} | {p.delta:+.4f} | "
                f"{icon} |"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        data = self.summary()
        data["loss_history"] = [
            round(x, 4) for x in self.loss_history
        ]
        data["patches"] = [p.to_dict() for p in self.rounds]
        return data


class AutoResearchLoop:
    """The core optimization loop.

    Takes a skill config + evaluation function, and iteratively
    applies patches to minimize loss.

    Usage:
        loop = AutoResearchLoop(config, evaluator, run_fn)
        state = loop.run(max_rounds=10)
        print(state.changelog())

    The `run_fn` callback signature:
        (config: EvalConfig, round_num: int) -> LossResult

    This allows the caller to control HOW the skill is actually
    executed (simulation vs real agent run).
    """

    # Patch strategies per loss dimension
    STRATEGIES = {
        "density": [
            ("truncate", "Add response truncation at {limit} tokens"),
            ("filter", "Add schema_filter: keep only {fields}"),
            ("compress", "Switch to summary-mode response format"),
        ],
        "efficiency": [
            ("batch", "Merge {tools} into single batch call"),
            ("cache", "Add caching for {tool} with {ttl}s TTL"),
            ("eliminate", "Remove redundant call to {tool}"),
        ],
        "cost": [
            ("limit", "Reduce token budget from {old} to {new}"),
            ("field_reduce", "Drop {fields} from response schema"),
            ("early_exit", "Add early-exit when {condition}"),
        ],
        "task": [
            ("add_rule", "Add validation: {rule}"),
            ("fallback", "Add fallback: if {tool} fails, try {alt}"),
            ("error_parse", "Parse error codes from {source}"),
        ],
    }

    def __init__(
        self,
        config: EvalConfig,
        evaluator: SkillEvaluator,
        run_fn: Callable,
        patch_fn: Callable = None,
    ):
        """
        Args:
            config: The skill's evaluation config
            evaluator: Evaluator instance for scoring
            run_fn: Callback to execute skill and return LossResult
            patch_fn: Optional callback to generate patches.
                      Signature: (state, result) -> Patch or None
                      If None, uses built-in strategy selector.
        """
        self.config = config
        self.evaluator = evaluator
        self.run_fn = run_fn
        self.patch_fn = patch_fn

    def run(
        self,
        max_rounds: int = 10,
        convergence_threshold: float = 0.01,
        convergence_streak: int = 3,
    ) -> AutoResearchState:
        """Execute the full autoresearch loop."""
        state = AutoResearchState(
            skill_name=self.config.skill_name,
            started_at=datetime.now().isoformat(),
            max_rounds=max_rounds,
            convergence_threshold=convergence_threshold,
            convergence_streak=convergence_streak,
        )

        # Phase 1: Baseline measurement
        baseline_result = self.run_fn(self.config, 0)
        state.baseline_loss = baseline_result.total_loss
        state.current_loss = baseline_result.total_loss
        state.best_loss = baseline_result.total_loss
        state.loss_history.append(baseline_result.total_loss)

        # Phase 2: Iterative optimization
        prev_config = copy.deepcopy(self.config)
        prev_result = baseline_result

        for round_num in range(1, max_rounds + 1):
            # Generate patch (targeted at dominant loss)
            if self.patch_fn:
                patch = self.patch_fn(state, prev_result)
            else:
                patch = self._default_patch(
                    state, prev_result, round_num
                )

            if patch is None:
                # No more patches to try
                break

            patch.loss_before = state.current_loss

            # Apply + evaluate
            new_result = self.run_fn(self.config, round_num)
            patch.loss_after = new_result.total_loss

            # Keep or revert
            if patch.improved:
                patch.kept = True
                patch.reason = (
                    f"Loss improved by {abs(patch.delta):.4f}"
                )
                prev_config = copy.deepcopy(self.config)
                prev_result = new_result
            else:
                patch.kept = False
                patch.reason = (
                    f"Loss regressed by {patch.delta:.4f}, "
                    f"reverting"
                )
                # Revert config to pre-patch state
                self.config = copy.deepcopy(prev_config)

            state.record_round(patch)

            # Check termination conditions
            if state.converged:
                break

        return state

    def _default_patch(
        self,
        state: AutoResearchState,
        result: LossResult,
        round_num: int,
    ) -> Patch:
        """Auto-generate a patch targeting the dominant loss."""
        target = result.dominant_loss
        strategies = self.STRATEGIES.get(target, [])

        # Cycle through strategies for this dimension
        idx = (round_num - 1) % len(strategies) if strategies else 0
        if not strategies:
            return None

        change_type, desc_template = strategies[idx]

        return Patch(
            round_num=round_num,
            description=desc_template.format(
                limit=self.config.density.t_safe,
                fields="price,change",
                tools="tool_a+tool_b",
                tool="main_tool",
                ttl=60,
                old=self.config.token_budget,
                new=int(self.config.token_budget * 0.8),
                condition="data.length == 0",
                rule="validate non-zero response",
                alt="fallback_tool",
                source="API response",
            ),
            target_dimension=target,
            change_type=change_type,
        )


def save_autoresearch_report(
    state: AutoResearchState,
    output_dir: str = None,
) -> tuple:
    """Save autoresearch results as JSON + Markdown."""
    out = Path(output_dir) if output_dir else Path("evaluation/reports")
    out.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = state.skill_name

    # JSON
    json_path = out / f"autoresearch_{name}_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(state.to_dict(), f, indent=2)

    # Markdown changelog
    md_path = out / f"autoresearch_{name}_{ts}.md"
    with open(md_path, "w") as f:
        f.write(state.changelog())

    return str(json_path), str(md_path)
