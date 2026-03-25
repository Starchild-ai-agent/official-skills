#!/usr/bin/env python3
"""Tests for charting skill — template & doc quality."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_parent = os.path.join(os.path.dirname(__file__), "..")
REPO = os.path.join(_parent if os.path.isdir(os.path.join(_parent, "hyperliquid")) else os.path.join(_parent, "repo"), "charting")

def test_charting_skill_doc_exists():
    assert os.path.exists(os.path.join(REPO, "SKILL.md"))

def test_charting_has_critical_warning():
    """SKILL.md should warn not to call data tools."""
    with open(os.path.join(REPO, "SKILL.md")) as f:
        content = f.read()
    assert "CRITICAL" in content or "DO NOT" in content or "NEVER" in content, "Missing critical warning about data tools"

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
    """Check if charting has template scripts (may be in scripts/ subdir)."""
    all_py = []
    all_md = []
    for root, dirs, files in os.walk(REPO):
        for f in files:
            if f.endswith(".py"): all_py.append(f)
            if f.endswith(".md"): all_md.append(f)
    assert len(all_py) + len(all_md) >= 2, f"Charting skill too sparse: {all_py + all_md}"

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
