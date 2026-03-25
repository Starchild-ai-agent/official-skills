#!/usr/bin/env python3
"""Tests for twitter skill — code quality + structure."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_parent = os.path.join(os.path.dirname(__file__), "..")
REPO = os.path.join(_parent if os.path.isdir(os.path.join(_parent, "hyperliquid")) else os.path.join(_parent, "repo"), "twitter")

def test_twitter_has_tools():
    tools_py = os.path.join(REPO, "tools.py")
    assert os.path.exists(tools_py), "twitter/tools.py missing"
    with open(tools_py) as f:
        content = f.read()
    funcs = re.findall(r"def\s+(\w+)", content)
    assert len(funcs) >= 3, f"Only {len(funcs)} functions in tools.py"

def test_twitter_error_handling():
    tools_py = os.path.join(REPO, "tools.py")
    with open(tools_py) as f:
        content = f.read()
    bare = len(re.findall(r"except\s*:", content))
    assert bare == 0, f"Found {bare} bare except: clauses"

def test_twitter_client_exists():
    client_py = os.path.join(REPO, "client.py")
    assert os.path.exists(client_py), "twitter/client.py missing"

def test_twitter_has_rate_limit_awareness():
    for fname in ["client.py", "tools.py"]:
        fpath = os.path.join(REPO, fname)
        if os.path.exists(fpath):
            with open(fpath) as f:
                content = f.read()
            if "429" in content or "rate" in content.lower() or "retry" in content.lower() or "wait" in content.lower():
                return
    assert False, "No rate limit handling found in twitter skill"

def test_twitter_skill_doc_completeness():
    skill_md = os.path.join(REPO, "SKILL.md")
    with open(skill_md) as f:
        content = f.read()
    for tool in ["twitter_search_tweets", "twitter_user_info", "twitter_user_tweets"]:
        assert tool in content, f"SKILL.md missing {tool}"

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
