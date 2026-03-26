#!/usr/bin/env python3
"""
Optimization Loop — Main entry point for scheduled runs.

Usage:
  python -m evaluation.loop                 # Single optimization cycle
  python -m evaluation.loop --dry-run       # Analysis only, no patches
  python -m evaluation.loop --skill coinglass  # Target specific skill
  python -m evaluation.loop --report-only   # Just generate report from state
  python -m evaluation.loop --full-scan     # Score all skills, no patches

Designed to run via cron every 30 minutes.
"""

import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import sys  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.optimizer import (  # noqa: E402
    SkillAnalyzer, OptimizerState,
    REPORTS_DIR, TARGET_SKILLS, SKILLS_DIR,
)
from evaluation.patches import PatchGenerator, PatchApplier  # noqa: E402
from evaluation.config import ModelTier  # noqa: E402


def generate_report(
    scores: list,
    state: OptimizerState,
    patch_result=None,
    model_tier: ModelTier = ModelTier.SMALL,
) -> str:
    """Generate markdown optimization report."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    report = []
    report.append("# 🔬 Skill Optimization Report")
    report.append(f"**Generated:** {now}")
    report.append(f"**Model Tier:** {model_tier.value}")
    report.append(f"**Run #:** {state.run_count}")
    report.append(
        f"**Cumulative Δ:** {state.cumulative_improvement:+.4f}")
    report.append("")

    # ── Scoreboard ──
    report.append("## 📊 Skill Scoreboard")
    report.append("")
    report.append(
        "| Skill | Grade | L_total | L_task | L_eff | L_cost "
        "| L_density | Dominant | Findings |")
    report.append(
        "|-------|-------|---------|--------|-------|--------"
        "|-----------|----------|----------|")
    for s in scores:
        report.append(
            f"| {s.name} | **{s.grade}** "
            f"| {s.total_loss:.3f} "
            f"| {s.l_task:.3f} "
            f"| {s.l_efficiency:.3f} "
            f"| {s.l_cost:.3f} "
            f"| {s.l_density:.3f} "
            f"| {s.dominant_dimension} "
            f"| {len(s.findings)} |"
        )
    report.append("")

    # ── Top Issues ──
    report.append("## ⚠️ Top Issues (by weighted impact)")
    report.append("")
    all_findings = []
    for s in scores:
        for f in s.findings:
            all_findings.append((s, f))
    # Sort by severity * dimension weight
    dim_weights = {"task": 10, "efficiency": 3, "cost": 1, "density": 5}
    all_findings.sort(
        key=lambda sf: sf[1].severity * dim_weights.get(
            sf[1].dimension, 1),
        reverse=True
    )
    for s, f in all_findings[:15]:
        report.append(
            f"- **[{f.dimension.upper()}]** `{f.skill}/{f.file}` "
            f"L{f.line}: {f.description}"
        )
        if f.fix_suggestion:
            report.append(f"  - 💡 {f.fix_suggestion}")
    report.append("")

    # ── Patch Result ──
    if patch_result:
        report.append("## 🔧 Patch Applied This Cycle")
        report.append("")
        icon = "✅" if patch_result.kept else "❌"
        report.append(f"- {icon} **{patch_result.patch_desc}**")
        report.append(f"  - Skill: `{patch_result.skill}`")
        report.append(f"  - Dimension: {patch_result.dimension}")
        report.append(
            f"  - Loss: {patch_result.loss_before:.4f} → "
            f"{patch_result.loss_after:.4f} "
            f"(Δ = {patch_result.delta:+.4f})")
        report.append(
            f"  - Outcome: "
            f"{'Kept — improved' if patch_result.kept else 'Reverted — no improvement'}")
        report.append("")

    # ── Small Model Adaptation Notes ──
    report.append("## 🧠 Small Model Adaptation Analysis")
    report.append("")
    # Find skills with high density loss
    high_density = [
        s for s in scores if s.l_density > 0.3
    ]
    if high_density:
        report.append("### High Context Cost Skills")
        for s in high_density:
            report.append(
                f"- **{s.name}**: SKILL.md ~{s.skill_md_tokens} tokens, "
                f"density loss={s.l_density:.3f}")
            if s.skill_md_tokens > 3000:
                report.append(
                    "  - ⚠️ SKILL.md exceeds 3000 token budget. "
                    "Consider: split into core/advanced sections, "
                    "lazy-load advanced tools.")
    else:
        report.append("All skills within context budget. ✅")
    report.append("")

    # ── Historical Trend ──
    if state.history:
        report.append("## 📈 Optimization History (last 10)")
        report.append("")
        report.append(
            "| # | Skill | Patch | Δ Loss | Kept |")
        report.append(
            "|---|-------|-------|--------|------|")
        for h in state.history[-10:]:
            icon = "✅" if h.get("kept") else "❌"
            report.append(
                f"| {h.get('ts', '?')[:10]} "
                f"| {h.get('skill', '?')} "
                f"| {h.get('patch', '?')[:40]} "
                f"| {h.get('delta', 0):+.4f} "
                f"| {icon} |"
            )
        report.append("")

    # ── Recommendations ──
    report.append("## 🎯 Next Steps")
    report.append("")
    if scores:
        worst = scores[0]
        report.append(
            f"1. **Priority target:** `{worst.name}` "
            f"(grade {worst.grade}, loss={worst.total_loss:.3f})")
        report.append(
            f"   - Dominant issue: {worst.dominant_dimension}")
        report.append(
            f"   - Findings: {len(worst.findings)} anti-patterns")
        if worst.dominant_dimension == "density":
            report.append(
                "   - Action: Reduce SKILL.md size, add response "
                "truncation to high-volume endpoints")
        elif worst.dominant_dimension == "efficiency":
            report.append(
                "   - Action: Add error handling to API calls, "
                "reduce retry loops")
        elif worst.dominant_dimension == "task":
            report.append(
                "   - Action: Fix error paths, add fallback returns")
        elif worst.dominant_dimension == "cost":
            report.append(
                "   - Action: Compress docstrings, remove dead code")
    report.append("")

    return "\n".join(report)


def run_optimization_cycle(
    target_skill: str = None,
    dry_run: bool = False,
    model_tier: ModelTier = ModelTier.SMALL,
) -> str:
    """Execute one optimization cycle. Returns report path."""
    state = OptimizerState.load()
    state.run_count += 1
    state.last_run = datetime.utcnow().isoformat()

    analyzer = SkillAnalyzer(model_tier=model_tier)
    patch_gen = PatchGenerator()
    patch_applier = PatchApplier()

    # Step 1: Score all skills
    print(f"[Cycle #{state.run_count}] Scanning {len(TARGET_SKILLS)} skills...")
    scores = analyzer.analyze_all()
    print(f"  Scored {len(scores)} skills. "
          f"Worst: {scores[0].name} ({scores[0].total_loss:.3f})")

    # Step 2: Select target skill
    if target_skill:
        target = next((s for s in scores if s.name == target_skill), None)
        if not target:
            print(f"  Skill '{target_skill}' not found!")
            return None
    else:
        # ε-greedy: 80% worst skill, 20% random (exploration)
        if random.random() < 0.2 and len(scores) > 1:
            target = random.choice(scores)
            print(f"  [Explore] Random target: {target.name}")
        else:
            target = scores[0]
            print(f"  [Exploit] Worst target: {target.name}")

    state.last_skill = target.name

    # Step 3: Generate patch for worst finding
    # Strategy: prioritize findings matching the dominant dimension
    patch_result = None
    if not dry_run and target.findings:
        # Sort by: 1) matching dominant dimension or cross-cutting
        # patterns (missing_error_guard drives both task + efficiency),
        # 2) severity desc
        dominant = target.dominant_dimension
        # Patterns that cross dimensions
        cross_cut = {"missing_error_guard"}  # drives task + efficiency
        sorted_findings = sorted(
            target.findings,
            key=lambda f: (
                f.dimension == dominant
                or (dominant == "task"
                    and f.pattern_id in cross_cut),
                f.severity,
            ),
            reverse=True,
        )

        for finding in sorted_findings:
            filepath = SKILLS_DIR / finding.file
            if not filepath.exists():
                continue
            content = filepath.read_text()
            patch = patch_gen.generate_for_finding(finding, content)
            if patch and patch.confidence >= 0.7:
                print(f"  Patch: {patch.description} "
                      f"(confidence={patch.confidence})")

                # Apply
                if patch_applier.apply(patch):
                    # Re-score
                    new_score = analyzer.analyze_skill(target.name)
                    delta = new_score.total_loss - target.total_loss

                    kept = delta < -0.001  # Must improve
                    if not kept:
                        patch_applier.revert(patch)
                        reason = (
                            f"No improvement "
                            f"(Δ={delta:+.4f})")
                    else:
                        reason = f"Improved (Δ={delta:+.4f})"
                        state.cumulative_improvement += abs(delta)
                        # Update score in list
                        for i, s in enumerate(scores):
                            if s.name == target.name:
                                scores[i] = new_score
                                break

                    from evaluation.optimizer import PatchResult
                    patch_result = PatchResult(
                        skill=target.name,
                        patch_desc=patch.description,
                        dimension=patch.dimension,
                        file_changed=patch.file,
                        loss_before=target.total_loss,
                        loss_after=new_score.total_loss,
                        kept=kept,
                        reason=reason,
                        diff_summary=patch.diff_summary,
                        timestamp=datetime.utcnow().isoformat(),
                    )
                    state.history.append(patch_result.to_dict())
                    print(f"  Result: {reason}")
                    break

    # Step 4: Generate report
    report = generate_report(scores, state, patch_result, model_tier)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"optimization_{ts}.md"
    report_path.write_text(report)

    # Also write latest
    latest_path = REPORTS_DIR / "LATEST.md"
    latest_path.write_text(report)

    # Step 5: Save JSON scores for dashboarding
    scores_json = REPORTS_DIR / "scores.json"
    scores_json.write_text(json.dumps(
        [s.to_dict() for s in scores], indent=2))

    # Persist state
    state.save()

    print(f"  Report: {report_path}")
    return str(report_path)


def main():
    parser = argparse.ArgumentParser(
        description="Skill Optimization Loop")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Analyze only, no patches")
    parser.add_argument(
        "--skill", type=str, default=None,
        help="Target specific skill")
    parser.add_argument(
        "--report-only", action="store_true",
        help="Regenerate report from state")
    parser.add_argument(
        "--full-scan", action="store_true",
        help="Score all skills, generate report, no patches")
    parser.add_argument(
        "--tier", type=str, default="small",
        choices=["small", "medium", "large"],
        help="Model tier for weight selection")
    args = parser.parse_args()

    tier_map = {
        "small": ModelTier.SMALL,
        "medium": ModelTier.MEDIUM,
        "large": ModelTier.LARGE,
    }
    model_tier = tier_map[args.tier]

    if args.full_scan:
        args.dry_run = True

    report_path = run_optimization_cycle(
        target_skill=args.skill,
        dry_run=args.dry_run or args.report_only,
        model_tier=model_tier,
    )

    if report_path:
        print(f"\n{'='*60}")
        print(f"Report saved: {report_path}")
        # Print summary to stdout for scheduled task push
        latest = Path(report_path).read_text()
        # Extract scoreboard + patch result for compact push
        lines = latest.split("\n")
        sections_to_show = ["Skill Scoreboard", "Patch Applied",
                            "Next Steps"]
        current_section = False
        blank_count = 0
        for line in lines:
            if any(s in line for s in sections_to_show):
                current_section = True
                blank_count = 0
            if current_section:
                print(line)
                if line.strip() == "":
                    blank_count += 1
                else:
                    blank_count = 0
                if blank_count >= 2:
                    current_section = False
                    blank_count = 0


if __name__ == "__main__":
    main()
