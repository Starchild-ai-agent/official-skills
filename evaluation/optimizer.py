#!/usr/bin/env python3
"""
Skill Optimizer — Scheduled loop for iterative skill improvement.

Runs every 30 minutes. Each cycle:
  1. Scan all skills → score against loss function
  2. Pick the worst-performing skill (or round-robin)
  3. Identify dominant loss dimension
  4. Apply ONE atomic patch
  5. Re-evaluate → keep if improved, revert if regressed
  6. Generate optimization report

Loss function (Aaron spec v2):
  L = 10·L_task + 2·L_eff + 1·L_cost + 5·L_density  (for small models)

Scheduling:
  python -m evaluation.optimizer              # Single run
  python -m evaluation.optimizer --dry-run    # Analyze only, no patches
  python -m evaluation.optimizer --skill X    # Target specific skill
"""

import ast
import json
import re
import sys
from dataclasses import dataclass, field

from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import ModelTier


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════
SKILLS_DIR = PROJECT_ROOT
REPORTS_DIR = PROJECT_ROOT / "evaluation" / "reports"
STATE_FILE = PROJECT_ROOT / "evaluation" / ".optimizer_state.json"
BENCHMARKS_DIR = PROJECT_ROOT / "evaluation" / "benchmarks"

# Skills to optimize (those with Python tooling)
TARGET_SKILLS = [
    "coinglass", "coingecko", "hyperliquid", "birdeye", "debank",
    "lunarcrush", "1inch", "aave", "polymarket", "taapi",
    "twelvedata", "twitter",
]

# Anti-pattern definitions for static analysis
ANTI_PATTERNS = {
    "raw_json_return": {
        "desc": "Function returns raw API data without field filtering",
        "regex": r"return\s+(data|response|result)\s*$",
        "dimension": "density",
        "severity": 3,
    },
    "no_limit_param": {
        "desc": "API call without max_results/limit parameter",
        "regex": r"def\s+\w+\([^)]*\)\s*(?:\->[^:]+)?:",
        "check": "no_limit_in_signature",
        "dimension": "density",
        "severity": 2,
    },
    "large_response_no_truncate": {
        "desc": "Returns list/dict without size cap",
        "regex": r"return\s+\[.*for\s+\w+\s+in",
        "dimension": "density",
        "severity": 2,
    },
    "verbose_format_string": {
        "desc": "Verbose f-string in tool output consuming tokens",
        "regex": r'f"[^"]{200,}"',
        "dimension": "cost",
        "severity": 1,
    },
    "missing_error_guard": {
        "desc": "API call without try/except (causes retry loops)",
        "regex": r"proxied_get|requests\.get|proxied_post",
        "check": "no_try_except_around",
        "dimension": "efficiency",
        "severity": 2,
    },
    "redundant_intermediate_var": {
        "desc": "Unnecessary intermediate variable before return",
        "regex": r"(\w+)\s*=\s*(.+)\n\s*return\s+\1\s*$",
        "dimension": "cost",
        "severity": 1,
    },
}


# ═══════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════

@dataclass
class Finding:
    """A single anti-pattern found in a skill file."""
    skill: str
    file: str
    line: int
    pattern_id: str
    description: str
    dimension: str      # task, efficiency, cost, density
    severity: int       # 1-3
    code_snippet: str = ""
    fix_suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "file": self.file,
            "line": self.line,
            "pattern": self.pattern_id,
            "desc": self.description,
            "dimension": self.dimension,
            "severity": self.severity,
            "snippet": self.code_snippet[:200],
            "fix": self.fix_suggestion,
        }


@dataclass
class SkillScore:
    """Aggregated score for a single skill."""
    name: str
    total_loss: float = 0.0
    l_task: float = 0.0
    l_efficiency: float = 0.0
    l_cost: float = 0.0
    l_density: float = 0.0
    findings: list = field(default_factory=list)
    dominant_dimension: str = ""
    file_count: int = 0
    total_lines: int = 0
    skill_md_tokens: int = 0

    @property
    def grade(self) -> str:
        if self.total_loss < 0.5:
            return "A"
        elif self.total_loss < 1.5:
            return "B"
        elif self.total_loss < 3.0:
            return "C"
        elif self.total_loss < 5.0:
            return "D"
        return "F"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "grade": self.grade,
            "total_loss": round(self.total_loss, 4),
            "breakdown": {
                "l_task": round(self.l_task, 4),
                "l_efficiency": round(self.l_efficiency, 4),
                "l_cost": round(self.l_cost, 4),
                "l_density": round(self.l_density, 4),
            },
            "dominant": self.dominant_dimension,
            "findings_count": len(self.findings),
            "file_count": self.file_count,
            "total_lines": self.total_lines,
            "skill_md_tokens": self.skill_md_tokens,
        }


@dataclass
class PatchResult:
    """Result of applying an atomic patch."""
    skill: str
    patch_desc: str
    dimension: str
    file_changed: str
    loss_before: float
    loss_after: float
    kept: bool
    reason: str
    diff_summary: str = ""
    timestamp: str = ""

    @property
    def delta(self) -> float:
        return self.loss_after - self.loss_before

    @property
    def improved(self) -> bool:
        return self.delta < -0.001

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "patch": self.patch_desc,
            "dimension": self.dimension,
            "file": self.file_changed,
            "loss_before": round(self.loss_before, 4),
            "loss_after": round(self.loss_after, 4),
            "delta": round(self.delta, 4),
            "kept": self.kept,
            "reason": self.reason,
            "diff": self.diff_summary[:500],
            "ts": self.timestamp,
        }


@dataclass
class OptimizerState:
    """Persisted state across scheduled runs."""
    run_count: int = 0
    last_run: str = ""
    last_skill: str = ""
    skill_rotation_idx: int = 0
    cumulative_improvement: float = 0.0
    history: list = field(default_factory=list)  # List[PatchResult dicts]
    best_scores: dict = field(default_factory=dict)  # skill -> best loss

    def save(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump({
                "run_count": self.run_count,
                "last_run": self.last_run,
                "last_skill": self.last_skill,
                "rotation_idx": self.skill_rotation_idx,
                "cumulative_improvement": self.cumulative_improvement,
                "history": self.history[-100:],  # Keep last 100
                "best_scores": self.best_scores,
            }, f, indent=2)

    @classmethod
    def load(cls) -> "OptimizerState":
        if not STATE_FILE.exists():
            return cls()
        with open(STATE_FILE) as f:
            d = json.load(f)
        state = cls()
        state.run_count = d.get("run_count", 0)
        state.last_run = d.get("last_run", "")
        state.last_skill = d.get("last_skill", "")
        state.skill_rotation_idx = d.get("rotation_idx", 0)
        state.cumulative_improvement = d.get("cumulative_improvement", 0.0)
        state.history = d.get("history", [])
        state.best_scores = d.get("best_scores", {})
        return state


# ═══════════════════════════════════════════════════════════════
# Static Analysis Engine
# ═══════════════════════════════════════════════════════════════

class SkillAnalyzer:
    """Static analysis of skill source code for anti-patterns."""

    def __init__(self, model_tier: ModelTier = ModelTier.SMALL):
        self.model_tier = model_tier
        # Aaron spec: ω₁=10, ω₂=3 (small), ω₃=1, ω₄=5 (small)
        from evaluation.config import MODEL_WEIGHT_PROFILES
        self.weights = MODEL_WEIGHT_PROFILES[model_tier]

    def analyze_skill(self, skill_name: str) -> SkillScore:
        """Full analysis of a single skill."""
        skill_dir = SKILLS_DIR / skill_name
        if not skill_dir.exists():
            return SkillScore(name=skill_name)

        score = SkillScore(name=skill_name)
        py_files = list(skill_dir.rglob("*.py"))
        py_files = [f for f in py_files if "__pycache__" not in str(f)]
        score.file_count = len(py_files)

        # Measure SKILL.md token load
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            chars = skill_md.stat().st_size
            score.skill_md_tokens = chars // 4  # rough estimate

        # Scan each Python file
        all_findings = []
        total_lines = 0
        for py_file in py_files:
            try:
                content = py_file.read_text()
                total_lines += content.count("\n")
                findings = self._scan_file(
                    skill_name, str(py_file.relative_to(SKILLS_DIR)),
                    content,
                )
                all_findings.extend(findings)
            except Exception:
                pass

        score.total_lines = total_lines
        score.findings = all_findings

        # Compute loss components from findings
        score.l_density = self._compute_density_loss(all_findings, score)
        score.l_efficiency = self._compute_efficiency_loss(all_findings, score)
        score.l_cost = self._compute_cost_loss(all_findings, score)
        score.l_task = self._compute_task_loss(all_findings, score)

        # Total weighted loss
        w = self.weights
        score.total_loss = (
            w[0] * score.l_task
            + w[1] * score.l_efficiency
            + w[2] * score.l_cost
            + w[3] * score.l_density
        )

        # Dominant dimension
        dims = {
            "task": w[0] * score.l_task,
            "efficiency": w[1] * score.l_efficiency,
            "cost": w[2] * score.l_cost,
            "density": w[3] * score.l_density,
        }
        score.dominant_dimension = max(dims, key=dims.get)

        return score

    def _scan_file(self, skill: str, filepath: str,
                   content: str) -> list:
        """Scan a single file for anti-patterns."""
        findings = []
        lines = content.split("\n")

        for pattern_id, pattern_def in ANTI_PATTERNS.items():
            regex = pattern_def.get("regex", "")
            check = pattern_def.get("check", "")

            if check == "no_limit_in_signature":
                findings.extend(
                    self._check_no_limit(skill, filepath, content, lines,
                                         pattern_id, pattern_def))
            elif check == "no_try_except_around":
                findings.extend(
                    self._check_no_error_handling(
                        skill, filepath, content,
                        lines, pattern_id, pattern_def))
            elif regex:
                for i, line in enumerate(lines, 1):
                    if re.search(regex, line):
                        findings.append(Finding(
                            skill=skill,
                            file=filepath,
                            line=i,
                            pattern_id=pattern_id,
                            description=pattern_def["desc"],
                            dimension=pattern_def["dimension"],
                            severity=pattern_def["severity"],
                            code_snippet=line.strip()[:100],
                        ))

        return findings

    def _check_no_limit(self, skill, filepath, content, lines,
                        pid, pdef) -> list:
        """Check functions that fetch data but lack limit params."""
        findings = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip non-API functions (CLI, helpers, private)
                    if node.name in ("main", "format_output") or \
                       node.name.startswith("_"):
                        continue
                    args = [a.arg for a in node.args.args]
                    has_limit = any(
                        kw in args for kw in
                        ["limit", "max_results", "max_items", "top_n",
                         "count"]
                    )
                    # Check if function body contains API calls
                    body_src = ast.get_source_segment(content, node) or ""
                    has_api = ("proxied_get" in body_src
                               or "requests.get" in body_src
                               or "fetch" in body_src)
                    if has_api and not has_limit:
                        findings.append(Finding(
                            skill=skill,
                            file=filepath,
                            line=node.lineno,
                            pattern_id=pid,
                            description=pdef["desc"],
                            dimension=pdef["dimension"],
                            severity=pdef["severity"],
                            code_snippet=f"def {node.name}({', '.join(args)})",
                            fix_suggestion=(
                                f"Add limit parameter to {node.name}()"),
                        ))
        except SyntaxError:
            pass
        return findings

    def _check_no_error_handling(self, skill, filepath, content, lines,
                                 pid, pdef) -> list:
        """Check API calls not wrapped in try/except."""
        findings = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    body_src = ast.get_source_segment(content, node) or ""
                    has_api = ("proxied_get" in body_src
                               or "requests.get" in body_src
                               or "proxied_post" in body_src)
                    has_try = "try:" in body_src
                    if has_api and not has_try:
                        findings.append(Finding(
                            skill=skill,
                            file=filepath,
                            line=node.lineno,
                            pattern_id=pid,
                            description=pdef["desc"],
                            dimension=pdef["dimension"],
                            severity=pdef["severity"],
                            code_snippet=f"def {node.name}() lacks try/except",
                            fix_suggestion="Wrap API call in try/except",
                        ))
        except SyntaxError:
            pass
        return findings

    def _compute_density_loss(self, findings, score) -> float:
        """L_density based on code patterns + SKILL.md size.

        Uses diminishing returns so each fix is measurable.
        """
        density_findings = [
            f for f in findings if f.dimension == "density"
        ]
        pattern_score = sum(f.severity for f in density_findings)
        k_pattern = max(score.file_count * 3, 5)
        pattern_loss = pattern_score / (pattern_score + k_pattern)

        # SKILL.md context cost (T_peak vs T_safe)
        t_safe = 6000
        t_limit = 32000
        md_penalty = max(0, (score.skill_md_tokens - t_safe) / t_limit)

        # Combined: 70% patterns, 30% doc size
        return pattern_loss * 0.7 + md_penalty * 0.3

    def _compute_efficiency_loss(self, findings, score) -> float:
        """L_efficiency based on error handling + tool call patterns.

        Diminishing returns: each fix matters.
        """
        eff_findings = [
            f for f in findings if f.dimension == "efficiency"
        ]
        pattern_score = sum(f.severity for f in eff_findings)
        k = max(score.file_count * 2, 5)
        return pattern_score / (pattern_score + k)

    def _compute_cost_loss(self, findings, score) -> float:
        """L_cost based on token waste patterns."""
        cost_findings = [
            f for f in findings if f.dimension == "cost"
        ]
        # Lines of code as proxy for output verbosity
        lines_penalty = max(0, (score.total_lines - 500) / 5000)
        pattern_score = sum(f.severity for f in cost_findings)
        max_score = max(score.file_count * 2, 1)
        return min(1.0, (pattern_score / max_score) * 0.5
                   + lines_penalty * 0.5)

    def _compute_task_loss(self, findings, score) -> float:
        """L_task — check functional correctness signals.

        Uses diminishing returns: each fix matters more when fewer
        issues remain. Formula: count / (count + k) where k=5.
        This means: 0 findings=0.0, 5=0.5, 10=0.67, 25=0.83.
        Each fix from 26→25 gives Δ=-0.0013, from 5→4 gives Δ=-0.022.
        """
        task_findings = [
            f for f in findings
            if f.pattern_id == "missing_error_guard" and f.severity >= 2
        ]
        n = len(task_findings)
        k = 5  # half-saturation constant
        return n / (n + k) if n > 0 else 0.0

    def analyze_all(self) -> list:
        """Analyze all target skills, return sorted by loss (worst first)."""
        scores = []
        for skill in TARGET_SKILLS:
            if (SKILLS_DIR / skill).exists():
                scores.append(self.analyze_skill(skill))
        scores.sort(key=lambda s: s.total_loss, reverse=True)
        return scores
