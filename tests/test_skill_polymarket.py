#!/usr/bin/env python3
"""Tests for polymarket skill — code quality + structure."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "patches"))

_parent = os.path.join(os.path.dirname(__file__), "..")
REPO = os.path.join(_parent if os.path.isdir(os.path.join(_parent, "hyperliquid")) else os.path.join(_parent, "repo"), "polymarket")

def test_polymarket_has_tools():
    tools_py = os.path.join(REPO, "tools.py")
    assert os.path.exists(tools_py), "polymarket/tools.py missing"
    with open(tools_py) as f:
        content = f.read()
    assert len(content) > 100, "tools.py is too small"

def test_polymarket_has_error_handling():
    tools_py = os.path.join(REPO, "tools.py")
    with open(tools_py) as f:
        content = f.read()
    bare_except = len(re.findall(r"except\s*:", content))
    assert bare_except == 0, f"Found {bare_except} bare except: clauses"

def test_polymarket_skill_doc_has_tools():
    skill_md = os.path.join(REPO, "SKILL.md")
    with open(skill_md) as f:
        content = f.read()
    assert "polymarket_markets" in content, "SKILL.md missing tool reference"
    assert "polymarket_place" in content or "place_limit" in content, "Missing trading tools in doc"

def test_polymarket_has_init():
    init_py = os.path.join(REPO, "__init__.py")
    assert os.path.exists(init_py), "polymarket/__init__.py missing"

def test_polymarket_cli_wrapper_exists():
    cli = os.path.join(REPO, "cli_wrapper.py")
    assert os.path.exists(cli), "cli_wrapper.py missing"
    with open(cli) as f:
        content = f.read()
    assert "subprocess" in content or "Popen" in content or "run" in content, "CLI wrapper doesn't use subprocess"

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
