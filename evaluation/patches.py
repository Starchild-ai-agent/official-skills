#!/usr/bin/env python3
"""
Atomic Patch Engine — generates and applies minimal improvements.

Each patch targets ONE dimension of the loss function.
Patches are reversible (git stash or backup).

Patch types (by dimension):
  density:    truncate outputs, add limit params, filter response fields
  efficiency: add error handling, reduce tool calls
  cost:       compress docstrings, remove dead code
  task:       fix error paths, add fallbacks
"""

import os
import re
import ast
import shutil
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class AtomicPatch:
    """Definition of a single atomic patch."""
    id: str
    skill: str
    file: str
    dimension: str
    description: str
    original_content: str
    patched_content: str
    confidence: float  # 0-1, how safe is this patch

    @property
    def diff_summary(self) -> str:
        orig_lines = self.original_content.count("\n")
        patch_lines = self.patched_content.count("\n")
        delta = patch_lines - orig_lines
        sign = "+" if delta >= 0 else ""
        return f"{self.file}: {sign}{delta} lines ({self.description})"


class PatchGenerator:
    """Generates safe atomic patches based on findings."""

    def generate_for_finding(self, finding, file_content: str
                             ) -> Optional[AtomicPatch]:
        """Try to generate a patch for a specific finding."""
        handlers = {
            "missing_error_guard": self._patch_add_try_except,
            "raw_json_return": self._patch_filter_return,
            "no_limit_param": self._patch_add_limit_param,
            "redundant_intermediate_var": self._patch_inline_return,
        }
        handler = handlers.get(finding.pattern_id)
        if not handler:
            return None
        return handler(finding, file_content)

    def _patch_add_try_except(self, finding, content: str
                              ) -> Optional[AtomicPatch]:
        """Wrap API calls in try/except."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return None

        lines = content.split("\n")
        # Find the function at the finding's line
        target_func = None
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef)
                    and node.lineno == finding.line):
                target_func = node
                break
        if not target_func:
            return None

        # Get function body's indentation
        body_start = target_func.body[0].lineno - 1
        if body_start >= len(lines):
            return None
        indent = len(lines[body_start]) - len(lines[body_start].lstrip())
        base_indent = " " * indent

        # Check if already has try/except
        func_text = "\n".join(
            lines[target_func.lineno - 1:target_func.end_lineno])
        if "try:" in func_text:
            return None

        # Build patched version: wrap body in try/except
        body_lines = lines[body_start:target_func.end_lineno]
        wrapped = []
        wrapped.append(f"{base_indent}try:")
        for bl in body_lines:
            wrapped.append(f"    {bl}" if bl.strip() else bl)
        wrapped.append(f"{base_indent}except Exception as e:")
        wrapped.append(
            f'{base_indent}    return {{"error": str(e), '
            f'"skill": "{finding.skill}", '
            f'"function": "{target_func.name}"}}'
        )

        new_lines = (
            lines[:body_start]
            + wrapped
            + lines[target_func.end_lineno:]
        )

        return AtomicPatch(
            id=f"try-except-{finding.skill}-{target_func.name}",
            skill=finding.skill,
            file=finding.file,
            dimension="efficiency",
            description=(
                f"Add error handling to {target_func.name}()"),
            original_content=content,
            patched_content="\n".join(new_lines),
            confidence=0.85,
        )

    def _patch_filter_return(self, finding, content: str
                             ) -> Optional[AtomicPatch]:
        """Replace raw 'return data' with filtered return."""
        lines = content.split("\n")
        line_idx = finding.line - 1
        if line_idx >= len(lines):
            return None

        line = lines[line_idx]
        match = re.match(r"(\s*)return\s+(data|response|result)\s*$", line)
        if not match:
            return None

        indent = match.group(1)
        var = match.group(2)

        # Add a truncation guard
        new_lines = lines.copy()
        new_lines[line_idx] = (
            f"{indent}# Truncate large responses for context efficiency\n"
            f"{indent}if isinstance({var}, list) and len({var}) > 50:\n"
            f"{indent}    {var} = {var}[:50]\n"
            f"{indent}return {var}"
        )

        return AtomicPatch(
            id=f"filter-return-{finding.skill}-L{finding.line}",
            skill=finding.skill,
            file=finding.file,
            dimension="density",
            description=f"Add response truncation at line {finding.line}",
            original_content=content,
            patched_content="\n".join(new_lines),
            confidence=0.7,
        )

    def _patch_add_limit_param(self, finding, content: str
                               ) -> Optional[AtomicPatch]:
        """Add limit parameter to function signature."""
        # This is tricky with AST rewriting; skip for now
        # and log as suggestion-only
        return None

    def _patch_inline_return(self, finding, content: str
                             ) -> Optional[AtomicPatch]:
        """Inline redundant intermediate variable before return."""
        lines = content.split("\n")
        line_idx = finding.line - 1
        if line_idx < 1 or line_idx >= len(lines):
            return None
        # Match pattern: var = expr\n return var
        prev = lines[line_idx - 1]
        curr = lines[line_idx]
        m = re.match(r"(\s*)(\w+)\s*=\s*(.+)$", prev)
        if not m:
            return None
        indent, var, expr = m.groups()
        if curr.strip() != f"return {var}":
            return None

        new_lines = lines.copy()
        new_lines[line_idx - 1] = f"{indent}return {expr}"
        new_lines.pop(line_idx)

        return AtomicPatch(
            id=f"inline-return-{finding.skill}-L{finding.line}",
            skill=finding.skill,
            file=finding.file,
            dimension="cost",
            description=f"Inline redundant variable at line {finding.line}",
            original_content=content,
            patched_content="\n".join(new_lines),
            confidence=0.9,
        )


class PatchApplier:
    """Safely applies and reverts atomic patches."""

    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.root = project_root
        self.backup_dir = project_root / "evaluation" / ".backups"

    def apply(self, patch: AtomicPatch) -> bool:
        """Apply patch, backing up original. Returns success."""
        filepath = self.root / patch.file
        if not filepath.exists():
            return False

        # Backup
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = (
            self.backup_dir / patch.file.replace("/", "__")
        )
        shutil.copy2(filepath, backup_path)

        # Write patched content
        filepath.write_text(patch.patched_content)
        return True

    def revert(self, patch: AtomicPatch) -> bool:
        """Revert patch from backup. Returns success."""
        filepath = self.root / patch.file
        backup_path = (
            self.backup_dir / patch.file.replace("/", "__")
        )
        if not backup_path.exists():
            return False
        shutil.copy2(backup_path, filepath)
        backup_path.unlink()
        return True

    def cleanup_backups(self):
        """Remove all backups."""
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
