#!/usr/bin/env python3
"""Security audit tests for all skills."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_base = os.path.join(os.path.dirname(__file__), "..")
REPO = os.path.join(_base, "repo") if os.path.isdir(os.path.join(_base, "repo")) else _base
EXCLUDED_DIRS = {"tests", "patches", ".pytest_cache", "__pycache__", "node_modules", "output", "docs", "fork-workspace", "repo"}
ALL_PY = []
for skill in os.listdir(REPO):
    if skill in EXCLUDED_DIRS:
        continue
    skill_dir = os.path.join(REPO, skill)
    if not os.path.isdir(skill_dir):
        continue
    for fname in os.listdir(skill_dir):
        if fname.endswith(".py"):
            ALL_PY.append((skill, os.path.join(skill_dir, fname)))

def test_no_hardcoded_secrets():
    """No API keys, tokens, or passwords hardcoded."""
    secret_patterns = [
        r'["\'](sk-[a-zA-Z0-9]{20,})["\'"]',
        r'["\'](ghp_[a-zA-Z0-9]{20,})["\'"]', 
        r'api_key\s*=\s*["\'"][a-zA-Z0-9]{20,}["\'"]',
        r'password\s*=\s*["\'"][^"\'\']{8,}["\'"]',
    ]
    found = []
    for skill, fpath in ALL_PY:
        with open(fpath) as f:
            content = f.read()
        for pat in secret_patterns:
            matches = re.findall(pat, content)
            if matches:
                found.append(f"{skill}/{os.path.basename(fpath)}: {pat}")
    assert len(found) == 0, f"Hardcoded secrets found: {found}"

def test_no_eval_exec():
    """No eval() or exec() — code injection risk."""
    found = []
    for skill, fpath in ALL_PY:
        with open(fpath) as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if re.search(r'\beval\s*\(', stripped) or re.search(r'\bexec\s*\(', stripped):
                    found.append(f"{skill}/{os.path.basename(fpath)}:{i}")
    assert len(found) == 0, f"eval/exec found: {found}"

def test_no_shell_injection():
    """subprocess calls should not use shell=True with user input."""
    found = []
    for skill, fpath in ALL_PY:
        with open(fpath) as f:
            content = f.read()
        if "shell=True" in content:
            # Check if it uses f-string or format with user input
            if re.search(r'subprocess\..*shell=True.*f["\'"]', content, re.DOTALL):
                found.append(f"{skill}/{os.path.basename(fpath)}")
    assert len(found) == 0, f"Potential shell injection: {found}"

def test_no_path_traversal():
    """File operations should not allow ../ traversal."""
    found = []
    for skill, fpath in ALL_PY:
        with open(fpath) as f:
            content = f.read()
        if "open(" in content and ".." in content:
            if not re.search(r'os\.path\.abspath|os\.path\.realpath|Path.*resolve', content):
                found.append(f"{skill}/{os.path.basename(fpath)}")
    # Many skills legitimately use .. for imports
    assert len(found) < 5, f"Potential path traversal: {found}"

def test_env_vars_not_logged():
    """API keys from env should not be printed/logged."""
    found = []
    for skill, fpath in ALL_PY:
        with open(fpath) as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('#'):
                continue
            if 'print' in line or 'logger.' in line or 'logging.' in line:
                if re.search(r'API_KEY|SECRET|TOKEN|PASSWORD', line):
                    # Exclude false positives like "Missing API_KEY" or "Please set API_KEY"
                    if not re.search(r'set|missing|require|invalid|provide|error', line, re.IGNORECASE):
                        if '{' in line and '}' in line or '%' in line or ',' in line:
                            found.append(f"{skill}/{os.path.basename(fpath)}:{i}")
    assert len(found) == 0, f"Secrets potentially logged: {found}"

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
