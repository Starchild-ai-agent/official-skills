"""
ExecutionTracker — Records step-by-step Agent execution metadata.

Tracks:
  - Tool calls (name, args, result summary, latency)
  - Token consumption per step
  - Goal completion flags
  - Wall clock time
"""

import time
from dataclasses import dataclass


@dataclass
class StepRecord:
    """One atomic tool call or reasoning step."""
    step_num: int
    tool_name: str
    args_summary: str = ""
    result_summary: str = ""
    success: bool = True
    error: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    timestamp: float = 0.0

    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out

    def to_dict(self) -> dict:
        return {
            "step": self.step_num,
            "tool": self.tool_name,
            "args": self.args_summary,
            "result": self.result_summary[:200],  # Truncate
            "success": self.success,
            "error": self.error,
            "tokens": {"in": self.tokens_in, "out": self.tokens_out},
            "latency_ms": round(self.latency_ms, 1),
        }


class ExecutionTracker:
    """Accumulates execution metadata during a skill run.

    Usage:
        tracker = ExecutionTracker(skill_name="coinglass")
        tracker.start()

        # Record each tool call
        tracker.record_step("funding_rate", args="BTC",
                            result="success", tokens_in=500, tokens_out=800)

        # Mark goals as achieved
        tracker.mark_goal("fetch_funding_data")

        tracker.stop()
        summary = tracker.summary()
    """

    def __init__(self, skill_name: str):
        self.skill_name = skill_name
        self.steps: list = []
        self.goals_achieved: set = set()
        self.goals_failed: dict = {}  # goal_id -> error reason
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self._running = False

    def start(self):
        self._start_time = time.time()
        self._running = True
        self.steps = []
        self.goals_achieved = set()
        self.goals_failed = {}

    def stop(self):
        self._end_time = time.time()
        self._running = False

    def record_step(
        self,
        tool_name: str,
        args: str = "",
        result: str = "",
        success: bool = True,
        error: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> StepRecord:
        t_start = time.time()
        step = StepRecord(
            step_num=len(self.steps) + 1,
            tool_name=tool_name,
            args_summary=args,
            result_summary=result,
            success=success,
            error=error,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            timestamp=t_start,
        )
        self.steps.append(step)
        return step

    def mark_goal(self, goal_id: str):
        self.goals_achieved.add(goal_id)

    def fail_goal(self, goal_id: str, reason: str = ""):
        self.goals_failed[goal_id] = reason

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def total_tokens(self) -> int:
        return sum(s.total_tokens() for s in self.steps)

    @property
    def total_tokens_in(self) -> int:
        return sum(s.tokens_in for s in self.steps)

    @property
    def total_tokens_out(self) -> int:
        return sum(s.tokens_out for s in self.steps)

    @property
    def wall_time_ms(self) -> float:
        end = self._end_time if self._end_time else time.time()
        return (end - self._start_time) * 1000

    @property
    def failed_steps(self) -> list:
        return [s for s in self.steps if not s.success]

    def summary(self) -> dict:
        return {
            "skill": self.skill_name,
            "steps": self.step_count,
            "total_tokens": self.total_tokens,
            "tokens_in": self.total_tokens_in,
            "tokens_out": self.total_tokens_out,
            "wall_time_ms": round(self.wall_time_ms, 1),
            "goals_achieved": sorted(self.goals_achieved),
            "goals_failed": dict(self.goals_failed),
            "failed_steps": len(self.failed_steps),
            "step_details": [s.to_dict() for s in self.steps],
        }
