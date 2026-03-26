"""
BenchmarkRunner — Execute skill benchmarks and generate reports.

This is the CLI entrypoint for running evaluations against
real Starchild skill executions.

Usage:
    python -m evaluation.runner --skill coinglass --scenario funding_rate
    python -m evaluation.runner --all --output reports/
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from evaluation.config import EvalConfig
from evaluation.tracker import ExecutionTracker
from evaluation.evaluator import SkillEvaluator, LossResult


BENCHMARKS_DIR = Path(__file__).parent / "benchmarks"
REPORTS_DIR = Path(__file__).parent / "reports"


def load_benchmark(skill_name: str) -> EvalConfig:
    """Load benchmark config from JSON file."""
    path = BENCHMARKS_DIR / f"{skill_name}_benchmark.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No benchmark found for '{skill_name}'. "
            f"Available: {list_benchmarks()}"
        )
    return EvalConfig.load(str(path))


def list_benchmarks() -> list:
    """List all available benchmark skill names."""
    if not BENCHMARKS_DIR.exists():
        return []
    return [
        f.stem.replace("_benchmark", "")
        for f in BENCHMARKS_DIR.glob("*_benchmark.json")
    ]


def simulate_run(
    config: EvalConfig,
    goals_met: list,
    goals_failed: Optional[dict] = None,
    steps: int = 3,
    tokens_per_step: tuple = (500, 500),
    failed_step_indices: Optional[list] = None,
) -> ExecutionTracker:
    """Simulate a skill execution for testing.

    In production, this would be replaced by actual Agent execution recording.
    """
    tracker = ExecutionTracker(skill_name=config.skill_name)
    tracker.start()

    failed_set = set(failed_step_indices or [])

    for i in range(steps):
        success = i not in failed_set
        tracker.record_step(
            tool_name=f"step_{i+1}",
            args=f"simulated_arg_{i}",
            result="ok" if success else "error",
            success=success,
            error="" if success else "simulated_error",
            tokens_in=tokens_per_step[0],
            tokens_out=tokens_per_step[1],
        )

    for gid in goals_met:
        tracker.mark_goal(gid)

    if goals_failed:
        for gid, reason in goals_failed.items():
            tracker.fail_goal(gid, reason)

    tracker.stop()
    return tracker


def run_baseline(skill_name: str) -> LossResult:
    """Run a baseline evaluation using simulated perfect execution."""
    config = load_benchmark(skill_name)
    evaluator = SkillEvaluator(config)

    # Simulate all goals met, at target step count
    all_goals = [g.id for g in config.goals]
    tracker = simulate_run(
        config,
        goals_met=all_goals,
        steps=config.target_steps,
        tokens_per_step=(400, 400),
    )

    return evaluator.evaluate(tracker, run_id="baseline")


def run_worst_case(skill_name: str) -> LossResult:
    """Run worst-case scenario: critical failure, max steps, max tokens."""
    config = load_benchmark(skill_name)
    evaluator = SkillEvaluator(config)

    # Only non-critical goals met
    critical_goals = [g for g in config.goals if g.critical]
    non_critical = [g.id for g in config.goals if not g.critical]

    tracker = simulate_run(
        config,
        goals_met=non_critical,
        goals_failed={g.id: "simulated failure" for g in critical_goals},
        steps=config.max_steps,
        tokens_per_step=(2000, 2000),
        failed_step_indices=[0, 2, 4],
    )

    return evaluator.evaluate(tracker, run_id="worst_case")


def save_report(results: list, output_dir: str = None):
    """Save evaluation results as JSON + markdown."""
    out = Path(output_dir) if output_dir else REPORTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON report
    json_path = out / f"eval_report_{ts}.json"
    with open(json_path, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)

    # Markdown report
    md_path = out / f"eval_report_{ts}.md"
    lines = [
        f"# Evaluation Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"**Skills evaluated:** {len(results)}",
        "",
        "## Summary",
        "",
        "| Skill | Run | Grade | Total Loss | L_task | L_eff | L_cost |",
        "|-------|-----|-------|------------|--------|-------|--------|",
    ]
    for r in results:
        lines.append(
            f"| {r.skill_name} | {r.run_id} | **{r.grade}** | "
            f"{r.total_loss:.3f} | {r.l_task:.3f} | "
            f"{r.l_efficiency:.3f} | {r.l_cost:.3f} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    for r in results:
        lines.append(r.report())
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    return str(json_path), str(md_path)


def main():
    """CLI entrypoint."""
    import argparse

    parser = argparse.ArgumentParser(description="Run skill evaluations")
    parser.add_argument("--skill", help="Skill name to evaluate")
    parser.add_argument("--all", action="store_true", help="Evaluate all benchmarks")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--scenario", default="both",
                        choices=["baseline", "worst", "both"],
                        help="Which scenario to run")
    args = parser.parse_args()

    if not args.skill and not args.all:
        print(f"Available benchmarks: {list_benchmarks()}")
        parser.print_help()
        sys.exit(1)

    skills = list_benchmarks() if args.all else [args.skill]
    results = []

    for skill in skills:
        print(f"\n{'='*60}")
        print(f"  Evaluating: {skill}")
        print(f"{'='*60}")

        try:
            if args.scenario in ("baseline", "both"):
                r = run_baseline(skill)
                results.append(r)
                print(f"  Baseline: Grade {r.grade} | Loss {r.total_loss:.3f}")

            if args.scenario in ("worst", "both"):
                r = run_worst_case(skill)
                results.append(r)
                print(f"  Worst:    Grade {r.grade} | Loss {r.total_loss:.3f}")

        except Exception as e:
            print(f"  ERROR: {e}")

    if results:
        json_p, md_p = save_report(results, args.output)
        print(f"\n📊 Reports saved:")
        print(f"  JSON: {json_p}")
        print(f"  MD:   {md_p}")


if __name__ == "__main__":
    main()
