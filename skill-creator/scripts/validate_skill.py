#!/usr/bin/env python3
"""
Skill Validator - Validates a skill directory structure

Usage:
    python validate_skill.py <path/to/skill-folder>

Example:
    python validate_skill.py ./workspace/skills/my-skill
"""

import re
import sys
from pathlib import Path

# Try to import yaml, fallback to basic parsing if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def extract_frontmatter(content: str) -> tuple:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None, content

    # Find the closing ---
    end_match = re.search(r"\n---\n", content[3:])
    if not end_match:
        return None, content

    frontmatter_text = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3:]

    if HAS_YAML:
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            return {"_error": str(e)}, body
    else:
        # Basic parsing without yaml library
        frontmatter = {}
        for line in frontmatter_text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip()

    return frontmatter, body


def lint_warnings(frontmatter: dict, body: str) -> list:
    """
    Check for non-fatal issues and return warnings.
    These are suggestions, not errors — the skill is still valid.
    """
    warnings = []

    # emoji at top level instead of inside metadata.starchild
    if "emoji" in frontmatter:
        meta = frontmatter.get("metadata")
        has_starchild_emoji = (
            isinstance(meta, dict)
            and isinstance(meta.get("starchild"), dict)
            and meta["starchild"].get("emoji")
        )
        if not has_starchild_emoji:
            warnings.append(
                "emoji is at top level — move it to metadata.starchild.emoji "
                "so the loader picks it up correctly"
            )

    # requires at top level instead of inside metadata.starchild
    if "requires" in frontmatter:
        meta = frontmatter.get("metadata")
        has_starchild_requires = (
            isinstance(meta, dict)
            and isinstance(meta.get("starchild"), dict)
            and meta["starchild"].get("requires")
        )
        if not has_starchild_requires:
            warnings.append(
                "requires is at top level — move it to metadata.starchild.requires "
                "so the loader picks it up correctly"
            )

    # any_bins used instead of anyBins (camelCase)
    meta = frontmatter.get("metadata")
    if isinstance(meta, dict):
        sc = meta.get("starchild") or meta.get("openclaw")
        if isinstance(sc, dict):
            req = sc.get("requires")
            if isinstance(req, dict) and "any_bins" in req:
                warnings.append(
                    "requires.any_bins should be requires.anyBins (camelCase) "
                    "in metadata.starchild"
                )

    # Also check top-level requires for any_bins
    top_req = frontmatter.get("requires")
    if isinstance(top_req, dict) and "any_bins" in top_req:
        warnings.append(
            "requires.any_bins should be requires.anyBins (camelCase)"
        )

    # Description missing "Use when" trigger pattern
    desc = frontmatter.get("description", "")
    if desc and "[TODO" not in desc:
        desc_lower = desc.lower()
        if "use when" not in desc_lower and "use for" not in desc_lower:
            warnings.append(
                'description lacks a "Use when" trigger — consider adding '
                '"Use when <specific scenarios>" to help the agent decide '
                "when to activate this skill"
            )

    return warnings


def validate_skill(skill_path: Path) -> tuple:
    """
    Validate a skill directory.

    Returns:
        (is_valid, message, warnings)
    """
    skill_path = Path(skill_path).resolve()

    # Check directory exists
    if not skill_path.exists():
        return False, f"Directory not found: {skill_path}", []

    if not skill_path.is_dir():
        return False, f"Not a directory: {skill_path}", []

    # Check SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found", []

    # Read and parse SKILL.md
    try:
        content = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Error reading SKILL.md: {e}", []

    # Extract frontmatter
    frontmatter, body = extract_frontmatter(content)

    if frontmatter is None:
        return False, "SKILL.md must start with YAML frontmatter (---)", []

    if "_error" in frontmatter:
        return False, f"Invalid YAML frontmatter: {frontmatter['_error']}", []

    # Check required fields
    if not frontmatter.get("name"):
        return False, "Frontmatter missing required field: name", []

    if not frontmatter.get("description"):
        return False, "Frontmatter missing required field: description", []

    # Check description is not placeholder
    desc = frontmatter.get("description", "")
    if "[TODO" in desc or not desc.strip():
        return False, "Description contains TODO or is empty - please complete it", []

    # Check skill name format
    name = frontmatter.get("name", "")
    normalized = re.sub(r"[^a-z0-9-]", "", name.lower())
    if name != normalized:
        return False, f"Skill name should be lowercase hyphen-case: '{name}' -> '{normalized}'", []

    # Check body has content
    if len(body.strip()) < 50:
        return False, "SKILL.md body is too short (< 50 chars)", []

    # Collect lint warnings
    warns = lint_warnings(frontmatter, body)

    # Warn about TODOs in body
    todo_count = body.count("[TODO")
    if todo_count > 0:
        return True, f"Valid (but has {todo_count} TODO items remaining)", warns

    # Check line count
    line_count = len(content.split("\n"))
    if line_count > 500:
        return True, f"Valid (but {line_count} lines - consider splitting to references/)", warns

    return True, "Valid skill", warns


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_skill.py <path/to/skill-folder>")
        print("\nExample:")
        print("  python validate_skill.py ./workspace/skills/my-skill")
        sys.exit(1)

    skill_path = sys.argv[1]
    print(f"Validating skill: {skill_path}\n")

    is_valid, message, warnings = validate_skill(skill_path)

    if is_valid:
        print(f"[OK] {message}")
    else:
        print(f"[ERROR] {message}")

    # Print warnings
    for warn in warnings:
        print(f"[WARN] {warn}")

    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
