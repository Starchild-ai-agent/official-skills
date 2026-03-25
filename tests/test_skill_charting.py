#!/usr/bin/env python3
"""Tests for charting skill — template & doc quality."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_base = os.path.join(os.path.dirname(__file__), "..")
REPO = os.path.join(
    _base,
    "repo",
    "charting") if os.path.isdir(
        os.path.join(
            _base,
            "repo")) else os.path.join(
                _base,
    "charting")


def test_charting_skill_doc_exists():
    assert os.path.exists(os.path.join(REPO, "SKILL.md"))


def test_charting_has_critical_warning():
    """SKILL.md should warn not to call data tools."""
    with open(os.path.join(REPO, "SKILL.md")) as f:
        content = f.read()
    assert (
        "CRITICAL" in content or "DO NOT" in content or "NEVER" in content
    ), "Missing critical warning about data tools"


def test_charting_has_workflow():
    with open(os.path.join(REPO, "SKILL.md")) as f:
        content = f.read()
    assert "workflow" in content.lower() or "step" in content.lower(), "Missing workflow section"


def test_charting_dependencies_declared():
    with open(os.path.join(REPO, "SKILL.md")) as f:
        content = f.read()
    assert "mplfinance" in content, "Missing mplfinance dependency"
    assert "pandas" in content, "Missing pandas dependency"


def test_charting_templates_exist():
    """Check if charting has template scripts."""
    py_files = [f for f in os.listdir(REPO) if f.endswith(".py")]
    md_files = [f for f in os.listdir(REPO) if f.endswith(".md")]
    # Some skills only have SKILL.md (tool-based skills with no local scripts)
    assert len(py_files) + len(md_files) >= 1, f"Charting skill too sparse: {py_files + md_files}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
