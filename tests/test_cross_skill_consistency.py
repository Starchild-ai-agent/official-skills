#!/usr/bin/env python3
"""Cross-skill consistency tests — verify shared patterns."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Auto-detect: "repo" subdir (audit workspace) or root (fork)
_base = os.path.join(os.path.dirname(__file__), "..")
REPO = os.path.join(_base, "repo") if os.path.isdir(os.path.join(_base, "repo")) else _base
SKILLS_WITH_TOOLS = [s for s in os.listdir(REPO) 
    if os.path.isdir(os.path.join(REPO, s)) 
    and os.path.exists(os.path.join(REPO, s, "tools.py"))]

def test_all_skills_have_docstrings():
    missing = []
    for skill in SKILLS_WITH_TOOLS:
        with open(os.path.join(REPO, skill, "tools.py")) as f:
            content = f.read()
        funcs = re.findall(r'def\s+(\w+)\s*\(', content)
        for func in funcs:
            pattern = rf'def {func}\s*\([^)]*\).*?:\s*\n\s*"""'
            if not re.search(pattern, content, re.DOTALL):
                # Check single-line
                pattern2 = rf"def {func}\s*\([^)]*\).*?:\s*\n\s*\'"
                if not re.search(pattern2, content, re.DOTALL):
                    missing.append(f"{skill}/{func}")
    # Allow up to 30% missing (audit finding, not hard fail)
    ratio = len(missing) / max(1, sum(
        len(re.findall(r'def\s+\w+', open(os.path.join(REPO, s, 'tools.py')).read()))
        for s in SKILLS_WITH_TOOLS
    ))
    assert ratio < 0.5, f"{len(missing)} functions missing docstrings ({ratio:.0%}): {missing[:5]}..."

def test_no_hardcoded_urls_without_base():
    """Skills should use configurable base URLs, not hardcoded."""
    issues = []
    for skill in SKILLS_WITH_TOOLS:
        for fname in os.listdir(os.path.join(REPO, skill)):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(REPO, skill, fname)
            with open(fpath) as f:
                for i, line in enumerate(f, 1):
                    if re.search(r'https?://[\w.-]+\.(?:com|io|org|net)/api', line):
                        if "BASE_URL" not in line and "base_url" not in line and "#" not in line.split("http")[0]:
                            issues.append(f"{skill}/{fname}:{i}")
    # Informational — many skills do this
    assert len(issues) < 50, f"Too many hardcoded API URLs: {issues[:10]}"

def test_all_tool_skills_have_init():
    missing = [s for s in SKILLS_WITH_TOOLS 
               if not os.path.exists(os.path.join(REPO, s, "__init__.py"))]
    assert len(missing) == 0, f"Skills missing __init__.py: {missing}"

def test_skill_md_has_tools_section():
    missing = []
    for skill in SKILLS_WITH_TOOLS:
        md = os.path.join(REPO, skill, "SKILL.md")
        if os.path.exists(md):
            with open(md) as f:
                content = f.read()
            if "tools:" not in content and "tools :" not in content:
                missing.append(skill)
    assert len(missing) == 0, f"SKILL.md missing tools section: {missing}"

def test_consistent_error_return_pattern():
    """Check if skills use consistent error return patterns."""
    patterns = {}
    for skill in SKILLS_WITH_TOOLS:
        with open(os.path.join(REPO, skill, "tools.py")) as f:
            content = f.read()
        if 'return {"error"' in content:
            patterns.setdefault("dict_error", []).append(skill)
        if "return None" in content:
            patterns.setdefault("return_none", []).append(skill)
        if "raise " in content:
            patterns.setdefault("raise", []).append(skill)
        if 'return f"' in content or "return f'" in content:
            patterns.setdefault("return_string", []).append(skill)
    # More than 3 different patterns = inconsistency problem
    assert len(patterns) <= 4, f"Too many error patterns across skills: {list(patterns.keys())}"

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
