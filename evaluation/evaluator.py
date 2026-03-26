"""
SkillEvaluator — Core loss function computation engine.

Loss = ω₁·L_task + ω₂·L_efficiency + ω₃·L_cost

This is the "reward signal" that tells the Agent how well it performed.
Lower is better. 0 = perfect. High = needs optimization.
"""

from dataclasses import dataclass, field
from evaluation.config import EvalConfig
from evaluation.tracker import ExecutionTracker


@dataclass
class LossResult:
    """Complete evaluation result with loss breakdown."""
    skill_name: str
    run_id: str = ""

    # Raw losses (0-1 normalized)
    l_task: float = 0.0
    l_efficiency: float = 0.0
    l_cost: float = 0.0

    # Weighted losses
    wl_task: float = 0.0
    wl_efficiency: float = 0.0
    wl_cost: float = 0.0

    # Total
    total_loss: float = 0.0

    # Metadata for diagnosis
    task_score: float = 0.0       # 0-1, 1=perfect
    steps_used: int = 0
    steps_target: int = 0
    tokens_used: int = 0
    token_budget: int = 0
    goals_met: list = field(default_factory=list)
    goals_missed: list = field(default_factory=list)
    critical_failure: bool = False

    # Diagnosis
    dominant_loss: str = ""       # Which L_x is the biggest contributor
    recommendations: list = field(default_factory=list)

    @property
    def grade(self) -> str:
        """Letter grade based on total loss."""
        if self.total_loss < 0.5:
            return "A"
        elif self.total_loss < 1.5:
            return "B"
        elif self.total_loss < 3.0:
            return "C"
        elif self.total_loss < 5.0:
            return "D"
        return "F"

    @property
    def needs_refactor(self) -> bool:
        return self.total_loss > 0.5

    def to_dict(self) -> dict:
        return {
            "skill": self.skill_name,
            "run_id": self.run_id,
            "grade": self.grade,
            "total_loss": round(self.total_loss, 3),
            "breakdown": {
                "L_task": round(self.l_task, 3),
                "L_efficiency": round(self.l_efficiency, 3),
                "L_cost": round(self.l_cost, 3),
                "weighted": {
                    "W_task": round(self.wl_task, 3),
                    "W_efficiency": round(self.wl_efficiency, 3),
                    "W_cost": round(self.wl_cost, 3),
                }
            },
            "metadata": {
                "task_score": round(self.task_score, 3),
                "steps": f"{self.steps_used}/{self.steps_target}",
                "tokens": f"{self.tokens_used}/{self.token_budget}",
                "goals_met": self.goals_met,
                "goals_missed": self.goals_missed,
                "critical_failure": self.critical_failure,
            },
            "diagnosis": {
                "dominant_loss": self.dominant_loss,
                "needs_refactor": self.needs_refactor,
                "recommendations": self.recommendations,
            }
        }

    def report(self) -> str:
        """Human-readable markdown report."""
        lines = [
            f"## Evaluation: {self.skill_name} (Run: {self.run_id})",
            f"**Grade: {self.grade}** | Total Loss: **{self.total_loss:.3f}**",
            "",
            "| Component | Raw (0-1) | Weight | Weighted |",
            "|-----------|-----------|--------|----------|",
            f"| L_task | {self.l_task:.3f} | ×{10} | "
            f"{self.wl_task:.3f} |",
            f"| L_efficiency | {self.l_efficiency:.3f} | ×{2} | "
            f"{self.wl_efficiency:.3f} |",
            f"| L_cost | {self.l_cost:.3f} | ×{1} | "
            f"{self.wl_cost:.3f} |",
            "",
            f"**Steps**: {self.steps_used} used / "
            f"{self.steps_target} target",
            f"**Tokens**: {self.tokens_used:,} / "
            f"{self.token_budget:,} budget",
            "",
        ]
        if self.goals_met:
            lines.append(
                f"✅ Goals met: {', '.join(self.goals_met)}"
            )
        if self.goals_missed:
            lines.append(
                f"❌ Goals missed: {', '.join(self.goals_missed)}"
            )
        if self.recommendations:
            lines.append("")
            lines.append("### Recommendations")
            for r in self.recommendations:
                lines.append(f"- {r}")
        return "\n".join(lines)


class SkillEvaluator:
    """Computes loss scores from tracker data + benchmark config."""

    def __init__(self, config: EvalConfig):
        errors = config.validate()
        if errors:
            raise ValueError(
                f"Invalid config: {'; '.join(errors)}"
            )
        self.config = config

    def evaluate(
        self,
        tracker: ExecutionTracker,
        run_id: str = "baseline",
    ) -> LossResult:
        """Run full evaluation and return scored result."""
        result = LossResult(
            skill_name=self.config.skill_name,
            run_id=run_id,
            steps_target=self.config.target_steps,
            token_budget=self.config.token_budget,
        )

        # === L_task ===
        result.l_task, result.task_score = self._compute_task_loss(
            tracker
        )
        result.goals_met = sorted(tracker.goals_achieved)
        result.goals_missed = [
            g.id for g in self.config.goals
            if g.id not in tracker.goals_achieved
        ]

        # Check critical failures
        for goal in self.config.goals:
            if goal.critical and goal.id not in tracker.goals_achieved:
                result.critical_failure = True
                result.l_task = 1.0
                result.task_score = 0.0
                break

        # === L_efficiency ===
        result.steps_used = tracker.step_count
        result.l_efficiency = self._compute_efficiency_loss(
            tracker.step_count
        )

        # === L_cost ===
        result.tokens_used = tracker.total_tokens
        result.l_cost = self._compute_cost_loss(
            tracker.total_tokens
        )

        # === Weighted totals ===
        result.wl_task = self.config.w_task * result.l_task
        result.wl_efficiency = (
            self.config.w_efficiency * result.l_efficiency
        )
        result.wl_cost = self.config.w_cost * result.l_cost
        result.total_loss = (
            result.wl_task + result.wl_efficiency + result.wl_cost
        )

        # === Diagnosis ===
        result.dominant_loss = self._find_dominant(result)
        result.recommendations = self._generate_recommendations(
            result, tracker
        )

        return result

    def _compute_task_loss(
        self, tracker: ExecutionTracker
    ) -> tuple:
        """Returns (loss, score) where score is 0-1 achievement."""
        if not self.config.goals:
            return (0.0, 1.0)

        total_weight = 0.0
        achieved_weight = 0.0

        for goal in self.config.goals:
            total_weight += goal.weight
            if goal.id in tracker.goals_achieved:
                achieved_weight += goal.weight

        score = achieved_weight / total_weight if total_weight > 0 else 0
        loss = 1.0 - score
        return (loss, score)

    def _compute_efficiency_loss(self, steps: int) -> float:
        """L_eff = clamp((steps - target) / max_steps, 0, 1)"""
        target = self.config.target_steps
        max_s = self.config.max_steps

        if steps <= target:
            return 0.0

        raw = (steps - target) / max_s
        return min(1.0, max(0.0, raw))

    def _compute_cost_loss(self, tokens: int) -> float:
        """L_cost = clamp(tokens / budget, 0, 1)"""
        budget = self.config.token_budget
        if budget <= 0:
            return 0.0
        return min(1.0, max(0.0, tokens / budget))

    def _find_dominant(self, result: LossResult) -> str:
        """Which weighted loss contributes the most?"""
        losses = {
            "task": result.wl_task,
            "efficiency": result.wl_efficiency,
            "cost": result.wl_cost,
        }
        return max(losses, key=losses.get)

    def _generate_recommendations(
        self,
        result: LossResult,
        tracker: ExecutionTracker,
    ) -> list:
        """Auto-generate optimization hints based on loss profile."""
        recs = []

        # Task failures
        if result.l_task > 0:
            if result.critical_failure:
                recs.append(
                    "🔴 CRITICAL: A critical goal failed. "
                    "Fix the core workflow before optimizing."
                )
            for gid in result.goals_missed:
                reason = tracker.goals_failed.get(gid, "unknown")
                recs.append(
                    f"Goal '{gid}' missed: {reason}"
                )

        # Efficiency
        if result.l_efficiency > 0.3:
            failed = tracker.failed_steps
            if failed:
                recs.append(
                    f"🟡 {len(failed)} failed steps caused retries. "
                    f"Fix error handling to reduce step count."
                )
            if tracker.step_count > self.config.max_steps * 0.8:
                recs.append(
                    "🟡 Near max step limit. Consider merging "
                    "multiple queries into batch calls."
                )
            recs.append(
                f"Target: {self.config.target_steps} steps, "
                f"used: {tracker.step_count}. "
                f"Analyze which steps can be eliminated or merged."
            )

        # Cost
        if result.l_cost > 0.8:
            recs.append(
                "🟡 Token usage at >80% of budget. "
                "Consider adding field filters or response truncation."
            )
            # Find most expensive steps
            sorted_steps = sorted(
                tracker.steps,
                key=lambda s: s.total_tokens(),
                reverse=True,
            )
            if sorted_steps:
                top = sorted_steps[0]
                recs.append(
                    f"Most expensive step: '{top.tool_name}' "
                    f"({top.total_tokens()} tokens). "
                    f"Optimize this first."
                )

        if not recs:
            recs.append("✅ All metrics within target. No action needed.")

        return recs
