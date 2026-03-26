"""
EvalConfig — Benchmark definitions and hyperparameters.

Each skill gets a benchmark config with:
  - Goal anchors (atomic success criteria with weights)
  - Target step count and max tolerance
  - Token budget
  - Loss weight overrides (optional)
  - Model profile for environment-aware adaptation (v2)
"""

from dataclasses import dataclass, field
from enum import Enum
import json


class ModelTier(Enum):
    """Model size tiers — determines loss weight profiles."""
    LARGE = "large"       # GPT-4o, Claude Opus, Gemini Pro
    MEDIUM = "medium"     # GPT-4o Mini, Claude Sonnet
    SMALL = "small"       # Gemini Flash, Claude Haiku


# Pre-tuned weight profiles per model tier
# Format: (w_task, w_efficiency, w_cost, w_density)
MODEL_WEIGHT_PROFILES = {
    ModelTier.LARGE: (10.0, 2.0, 1.0, 1.0),
    ModelTier.MEDIUM: (10.0, 2.5, 1.0, 2.5),
    ModelTier.SMALL: (10.0, 3.0, 1.0, 4.0),
}


@dataclass
class DensityConfig:
    """Parameters for L_density — attention budget management.

    Controls how aggressively the evaluator penalizes large responses
    that exceed a small model's effective attention window.
    """
    t_safe: int = 6000        # Tokens: safe attention threshold
    t_limit: int = 32000      # Tokens: absolute upper bound
    enabled: bool = True       # Set False to skip density checks

    def to_dict(self) -> dict:
        return {
            "t_safe": self.t_safe,
            "t_limit": self.t_limit,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DensityConfig":
        return cls(
            t_safe=data.get("t_safe", 6000),
            t_limit=data.get("t_limit", 32000),
            enabled=data.get("enabled", True),
        )

    @classmethod
    def for_tier(cls, tier: ModelTier) -> "DensityConfig":
        """Factory: tier-appropriate density thresholds."""
        presets = {
            ModelTier.LARGE: cls(t_safe=16000, t_limit=128000),
            ModelTier.MEDIUM: cls(t_safe=8000, t_limit=64000),
            ModelTier.SMALL: cls(t_safe=6000, t_limit=32000),
        }
        return presets[tier]


@dataclass
class GoalAnchor:
    """A single atomic success criterion for a skill."""
    id: str                     # e.g. "fetch_funding_rate"
    description: str            # Human-readable
    weight: float               # 0.0-1.0, all weights must sum to 1.0
    critical: bool = False      # If True, failure = total task failure
    validator: str = ""         # Python expression or function name to check success

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "weight": self.weight,
            "critical": self.critical,
            "validator": self.validator,
        }


@dataclass
class EvalConfig:
    """Complete evaluation configuration for one skill."""
    skill_name: str
    version: str = "1.0"

    # Goal anchors
    goals: list = field(default_factory=list)

    # Efficiency parameters
    target_steps: int = 3       # Ideal tool call count
    max_steps: int = 10         # Absolute ceiling before force-stop
    step_penalty_start: int = 0  # Steps below this are "free"

    # Cost parameters
    token_budget: int = 15000   # Token ceiling for the task
    input_token_weight: float = 0.3   # Input tokens are cheaper
    output_token_weight: float = 1.0  # Output tokens are expensive

    # Model environment
    model_tier: ModelTier = ModelTier.LARGE

    # Density parameters (v2: small-model adaptation)
    density: DensityConfig = field(default_factory=DensityConfig)

    # Loss weights (RL hyperparameters)
    w_task: float = 10.0        # ω₁: Task completion (dominant)
    w_efficiency: float = 2.0   # ω₂: Step count optimization
    w_cost: float = 1.0         # ω₃: Token usage optimization
    w_density: float = 1.0      # ω₄: Attention density (v2)

    # Optimization triggers
    loss_threshold: float = 0.5   # Above this → force Refactor Mode
    rollback_on_regression: bool = True
    regression_tolerance: float = 0.1  # Allow 10% noise before rollback

    def apply_model_profile(self, tier: ModelTier = None):
        """Apply pre-tuned weight profile for a model tier.

        This is the key mechanism for environment-aware adaptation:
        small models get higher density + efficiency penalties.
        """
        tier = tier or self.model_tier
        self.model_tier = tier
        weights = MODEL_WEIGHT_PROFILES[tier]
        self.w_task = weights[0]
        self.w_efficiency = weights[1]
        self.w_cost = weights[2]
        self.w_density = weights[3]
        self.density = DensityConfig.for_tier(tier)

    def total_goal_weight(self) -> float:
        return sum(g.weight for g in self.goals)

    def validate(self) -> list:
        """Return list of validation errors, empty = valid."""
        errors = []
        w = self.total_goal_weight()
        if abs(w - 1.0) > 0.01:
            errors.append(f"Goal weights sum to {w:.2f}, expected 1.0")
        if self.target_steps >= self.max_steps:
            errors.append(
                f"target_steps ({self.target_steps}) >= "
                f"max_steps ({self.max_steps})"
            )
        if self.token_budget <= 0:
            errors.append(f"token_budget must be > 0, got {self.token_budget}")
        if not self.goals:
            errors.append("No goal anchors defined")
        return errors

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "version": self.version,
            "model_tier": self.model_tier.value,
            "goals": [g.to_dict() for g in self.goals],
            "target_steps": self.target_steps,
            "max_steps": self.max_steps,
            "token_budget": self.token_budget,
            "weights": {
                "task": self.w_task,
                "efficiency": self.w_efficiency,
                "cost": self.w_cost,
                "density": self.w_density,
            },
            "density": self.density.to_dict(),
            "optimization": {
                "loss_threshold": self.loss_threshold,
                "rollback_on_regression": self.rollback_on_regression,
                "regression_tolerance": self.regression_tolerance,
            }
        }

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "EvalConfig":
        with open(path) as f:
            data = json.load(f)

        goals = [
            GoalAnchor(**g) for g in data.get("goals", [])
        ]
        weights = data.get("weights", {})
        opt = data.get("optimization", {})
        density_data = data.get("density", {})
        tier_str = data.get("model_tier", "large")
        tier = ModelTier(tier_str)

        return cls(
            skill_name=data["skill_name"],
            version=data.get("version", "1.0"),
            model_tier=tier,
            goals=goals,
            target_steps=data.get("target_steps", 3),
            max_steps=data.get("max_steps", 10),
            token_budget=data.get("token_budget", 15000),
            density=DensityConfig.from_dict(density_data),
            w_task=weights.get("task", 10.0),
            w_efficiency=weights.get("efficiency", 2.0),
            w_cost=weights.get("cost", 1.0),
            w_density=weights.get("density", 1.0),
            loss_threshold=opt.get("loss_threshold", 0.5),
            rollback_on_regression=opt.get("rollback_on_regression", True),
            regression_tolerance=opt.get("regression_tolerance", 0.1),
        )
