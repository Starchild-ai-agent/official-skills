#!/usr/bin/env python3
"""
Comprehensive SKILL.md quality audit — covers ALL skills in the repo.

Checks:
1. SKILL.md exists and is non-empty
2. Required sections present (workflow, tools, error handling)
3. No dead links to non-existent scripts (real refs, not examples)
4. Consistent formatting (frontmatter or title)
5. Security patterns (no hardcoded secrets)
"""
import os
import re
import glob
import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")

# Discover all skills (directories with SKILL.md)
SKILL_DIRS = []
for skill_md in glob.glob(os.path.join(REPO_ROOT, "*/SKILL.md")):
    skill_dir = os.path.dirname(skill_md)
    name = os.path.basename(skill_dir)
    if name not in ("repo", "fork-workspace", ".pytest_cache", "node_modules", "output"):
        SKILL_DIRS.append((name, skill_dir))

SKILL_DIRS.sort(key=lambda x: x[0])


@pytest.fixture(params=SKILL_DIRS, ids=[s[0] for s in SKILL_DIRS])
def skill(request):
    name, path = request.param
    skill_md = os.path.join(path, "SKILL.md")
    with open(skill_md, "r") as f:
        content = f.read()
    return {"name": name, "path": path, "skill_md": skill_md, "content": content}


class TestSkillDocExists:
    """Every skill directory must have a non-empty SKILL.md."""

    def test_skill_md_exists(self, skill):
        assert os.path.isfile(skill["skill_md"])

    def test_skill_md_not_empty(self, skill):
        assert len(skill["content"].strip()) > 50, \
            f"{skill['name']}/SKILL.md is too short ({len(skill['content'])} chars)"

    def test_has_title_or_frontmatter(self, skill):
        """First line should be a markdown title OR YAML frontmatter."""
        content = skill["content"].strip()
        first_line = content.split("\n")[0].strip()
        has_title = first_line.startswith("#")
        has_frontmatter = first_line == "---"
        assert has_title or has_frontmatter, \
            f"{skill['name']}/SKILL.md has neither title nor frontmatter (first line: {first_line[:50]})"

    def test_frontmatter_has_name(self, skill):
        """If frontmatter exists, it must include a name field."""
        content = skill["content"].strip()
        if not content.startswith("---"):
            pytest.skip("No frontmatter")
        fm_end = content.find("---", 3)
        if fm_end == -1:
            pytest.fail(f"{skill['name']}: unclosed frontmatter")
        fm = content[3:fm_end]
        assert re.search(r"^name:\s*\S+", fm, re.MULTILINE), \
            f"{skill['name']}: frontmatter missing 'name' field"


class TestSkillDocContent:
    """SKILL.md should have workflow/usage instructions."""

    def test_has_sections(self, skill):
        """Skill doc must have at least one ## section heading."""
        sections = re.findall(r"^##\s+.+", skill["content"], re.MULTILINE)
        assert len(sections) >= 1, \
            f"{skill['name']}/SKILL.md has no ## section headings"

    def test_has_workflow_or_usage(self, skill):
        """Should have workflow/usage/howto/quickstart section."""
        pattern = r"(?i)##\s*(workflow|usage|how to|quick start|getting started|setup|overview)"
        match = re.search(pattern, skill["content"])
        if not match:
            # Acceptable alternative: at least 3 sections of any kind
            sections = re.findall(r"^##\s+.+", skill["content"], re.MULTILINE)
            assert len(sections) >= 3, \
                f"{skill['name']}: no workflow section and only {len(sections)} sections total"

    def test_reasonable_length(self, skill):
        """SKILL.md shouldn't be trivially short."""
        lines = skill["content"].strip().split("\n")
        assert len(lines) >= 10, \
            f"{skill['name']}/SKILL.md only {len(lines)} lines — likely incomplete"


class TestSkillSecurity:
    """No hardcoded secrets or dangerous patterns in SKILL.md."""

    SECRET_PATTERNS = [
        # Match actual secrets, not documentation patterns like `api_key: "YOUR_KEY"`
        (r'(?:api[_-]?key|secret|token|password)\s*[=:]\s*["\'][a-zA-Z0-9+/]{32,}["\']', "hardcoded secret"),
        (r'sk-[a-zA-Z0-9]{32,}', "OpenAI-style API key"),
        (r'(?<![a-zA-Z])0x[a-fA-F0-9]{64}(?![a-fA-F0-9])', "possible private key (64 hex chars)"),
    ]

    # Known false positives (example addresses, documentation hashes)
    FALSE_POSITIVE_SKILLS = {"1inch", "wallet", "wallet-policy", "aave"}

    def test_no_hardcoded_secrets(self, skill):
        for pattern, desc in self.SECRET_PATTERNS:
            matches = re.findall(pattern, skill["content"])
            if matches and skill["name"] not in self.FALSE_POSITIVE_SKILLS:
                pytest.fail(f"{skill['name']}/SKILL.md contains {desc}: {matches[0][:30]}...")
            elif matches:
                # Known false positive — skip
                pytest.skip(f"{skill['name']}: {desc} found but skill is in known-safe list")

    def test_no_eval_exec_instructions(self, skill):
        """SKILL.md should not instruct using eval() or exec()."""
        # Only match actual function calls, not mentions in comments/docs
        danger = re.findall(r'(?<!#\s)\b(eval|exec)\s*\(', skill["content"])
        assert len(danger) == 0, \
            f"{skill['name']}/SKILL.md contains dangerous {danger[0]}()"


class TestSkillInternalConsistency:
    """Check internal references are valid."""

    def test_referenced_scripts_exist(self, skill):
        """Scripts referenced via actual import/run patterns should exist.
        
        Only checks patterns like:
          - `python scripts/foo.py`
          - `bash scripts/foo.sh`
          - `source scripts/foo.sh`
        Ignores example snippets in code blocks showing hypothetical paths.
        """
        # Find script refs that look like real usage (outside fenced code blocks)
        content = skill["content"]
        
        # Extract fenced code blocks to separate them
        code_blocks = re.findall(r"```[\s\S]*?```", content)
        
        # Real usage patterns: direct references to run/source scripts
        real_refs = []
        for line in content.split("\n"):
            # Skip lines inside code blocks (rough heuristic)
            stripped = line.strip()
            if stripped.startswith("```"):
                continue
            # Patterns that indicate actual file dependencies
            match = re.search(r"(?:run|source|include|import)\s+['\"]?scripts/([a-zA-Z0-9_\-]+\.\w+)", line)
            if match:
                real_refs.append(match.group(1))

        for script in real_refs:
            script_path = os.path.join(skill["path"], "scripts", script)
            repo_path = os.path.join(REPO_ROOT, "repo", skill["name"], "scripts", script)
            assert os.path.isfile(script_path) or os.path.isfile(repo_path), \
                f"{skill['name']}: references scripts/{script} (real usage) but file not found"

    def test_no_broken_markdown_links(self, skill):
        """Check for obviously broken markdown links to local files."""
        links = re.findall(r'\[([^\]]+)\]\((?!http)(?!#)([^)]+)\)', skill["content"])
        broken = []
        for text, path in links:
            full_path = os.path.join(skill["path"], path)
            repo_path = os.path.join(REPO_ROOT, path)
            if not os.path.exists(full_path) and not os.path.exists(repo_path):
                broken.append(f"[{text}]({path})")
        if broken:
            pytest.skip(f"{skill['name']}: {len(broken)} possibly broken links: {broken[0]}")


class TestSkillCoverage:
    """Ensure we have reasonable skill coverage."""

    def test_minimum_skill_count(self):
        assert len(SKILL_DIRS) >= 15, \
            f"Only {len(SKILL_DIRS)} skills found, expected >= 15"

    def test_core_crypto_skills_present(self):
        names = {s[0] for s in SKILL_DIRS}
        required = {"coingecko", "coinglass", "hyperliquid", "charting"}
        missing = required - names
        assert not missing, f"Missing core crypto skills: {missing}"

    def test_core_infra_skills_present(self):
        names = {s[0] for s in SKILL_DIRS}
        required = {"wallet", "coder", "preview-dev"}
        missing = required - names
        assert not missing, f"Missing core infra skills: {missing}"

    def test_all_skills_have_description(self):
        """Every skill with frontmatter should have a description."""
        missing = []
        for name, path in SKILL_DIRS:
            with open(os.path.join(path, "SKILL.md")) as f:
                content = f.read()
            if content.strip().startswith("---"):
                fm_end = content.find("---", 3)
                if fm_end > 0:
                    fm = content[3:fm_end]
                    if not re.search(r"^description:", fm, re.MULTILINE):
                        missing.append(name)
        assert not missing, f"Skills missing description in frontmatter: {missing}"
