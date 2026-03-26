"""
Skill Evaluation Framework — Loss-Function-Based Agent Performance Scoring

Applies reinforcement-learning reward concepts to measure and optimize
how well an Agent executes skill workflows.

Loss = ω₁·L_task + ω₂·L_efficiency + ω₃·L_cost

Where:
  L_task      = 0 (success), 0.4 (partial), 1.0 (failure)
  L_efficiency = (actual_steps - target_steps) / max_steps, clamped [0, 1]
  L_cost      = actual_tokens / token_budget, clamped [0, 1]

Weights: ω₁=10 (task is king), ω₂=2 (efficiency matters), ω₃=1 (cost is baseline)
"""

from evaluation.evaluator import SkillEvaluator, LossResult
from evaluation.tracker import ExecutionTracker, StepRecord
from evaluation.config import EvalConfig, GoalAnchor

__all__ = [
    "SkillEvaluator", "LossResult",
    "ExecutionTracker", "StepRecord",
    "EvalConfig", "GoalAnchor",
]
