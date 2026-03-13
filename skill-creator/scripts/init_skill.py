#!/usr/bin/env python3
"""
Skill Initializer - Creates a new skill from template

Usage:
    init_skill.py <skill-name> --path <path> [--resources scripts,references,assets] [--examples]

Examples:
    python init_skill.py my-new-skill --path ./workspace/skills
    python init_skill.py api-helper --path ./workspace/skills --resources scripts,references
    python init_skill.py custom-skill --path ./workspace/skills --resources scripts --examples
"""

import argparse
import re
import sys
from pathlib import Path

MAX_SKILL_NAME_LENGTH = 64
ALLOWED_RESOURCES = {"scripts", "references", "assets"}

SKILL_TEMPLATE = """---
name: {skill_name}
description: "[TODO: What this skill does. Use when <specific trigger scenarios>.]"

metadata:
  starchild:
    emoji:
    skillKey: {skill_name}
    requires:
      env: []
      bins: []

user-invocable: true
---

# {skill_title}

[TODO: 1-2 sentences in direct voice. "You do X" not "This skill does X."
Explain what capability this gives the agent and why it matters.]

## Structuring This Skill

Pick the pattern that fits best, then delete this section:

- **Workflow-based** — Step-by-step process (fetch data -> process -> render -> output)
- **Task-based** — Organized by user request ("analyze X" / "compare Y" / "generate Z")
- **Reference/guidelines** — Rules, decision frameworks, core truths
- **Capabilities-based** — Organized by what the skill can do (tool group A / tool group B)

## [TODO: Main Section]

[TODO: Core instructions the agent needs every time this skill activates.
Focus on knowledge the agent doesn't already have:
- Domain-specific interpretation guides
- Decision trees ("when X, do Y; when Z, do W")
- Gotchas and edge cases
- Key parameters and thresholds]

## Resources

[TODO: Document scripts/, references/, assets/ if used.
Delete this section if no resource directories exist.]
"""

EXAMPLE_SCRIPT = '''#!/usr/bin/env python3
"""
{skill_title} - Helper Script

Usage:
    python scripts/example.py --input <path> [--output <path>]

This script handles [TODO: describe what this automates].
Scripts are for low-freedom operations: fragile API calls, exact rendering,
repetitive boilerplate. The agent executes these via bash, not by reading
them into context.
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="{skill_title} helper")
    parser.add_argument("--input", required=True, help="Input file path")
    parser.add_argument("--output", default=None, help="Output file path (default: stdout)")
    args = parser.parse_args()

    # TODO: Replace with actual implementation
    print(f"Processing: {{args.input}}")

    result = {{"status": "ok", "input": args.input}}

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Output written to: {{args.output}}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
'''

EXAMPLE_REFERENCE = """# {skill_title} — Reference Documentation

This reference is loaded on demand via `read_file` when the agent needs
detailed information beyond what's in the main SKILL.md.

## When to Load This Reference

- Agent needs full API endpoint details
- Agent needs to look up error codes or schema definitions
- Complex multi-step process requires detailed walkthrough

## API Reference

### Authentication

[TODO: How to authenticate — headers, tokens, env vars]

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/example` | GET | [TODO: Description] |
| `/api/example` | POST | [TODO: Description] |

### Error Codes

| Code | Meaning | Recovery |
|------|---------|----------|
| 401 | Invalid API key | Check env var is set |
| 429 | Rate limited | Wait and retry (backoff) |

## Troubleshooting

[TODO: Common issues and how to resolve them]
"""

EXAMPLE_ASSET = """{{
  "name": "{skill_name}",
  "version": "1.0",
  "description": "Template asset for {skill_title}",
  "TODO": "Replace this with actual asset content (templates, config, data files). Assets are NOT loaded into context — they're used in output generation."
}}
"""


def normalize_skill_name(skill_name: str) -> str:
    """Normalize skill name to lowercase hyphen-case."""
    normalized = skill_name.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized


def title_case_skill_name(skill_name: str) -> str:
    """Convert hyphenated skill name to Title Case."""
    return " ".join(word.capitalize() for word in skill_name.split("-"))


def parse_resources(raw_resources: str) -> list:
    if not raw_resources:
        return []
    resources = [item.strip() for item in raw_resources.split(",") if item.strip()]
    invalid = [item for item in resources if item not in ALLOWED_RESOURCES]
    if invalid:
        print(f"[ERROR] Unknown resource type(s): {', '.join(invalid)}")
        print(f"   Allowed: {', '.join(sorted(ALLOWED_RESOURCES))}")
        sys.exit(1)
    return list(dict.fromkeys(resources))  # dedupe while preserving order


def create_resource_dirs(skill_dir: Path, skill_name: str, skill_title: str,
                         resources: list, include_examples: bool):
    for resource in resources:
        resource_dir = skill_dir / resource
        resource_dir.mkdir(exist_ok=True)

        if resource == "scripts":
            if include_examples:
                example_script = resource_dir / "example.py"
                example_script.write_text(EXAMPLE_SCRIPT.format(
                    skill_name=skill_name, skill_title=skill_title))
                example_script.chmod(0o755)
                print(f"[OK] Created {resource}/example.py")
            else:
                print(f"[OK] Created {resource}/")

        elif resource == "references":
            if include_examples:
                example_ref = resource_dir / "reference.md"
                example_ref.write_text(EXAMPLE_REFERENCE.format(
                    skill_name=skill_name, skill_title=skill_title))
                print(f"[OK] Created {resource}/reference.md")
            else:
                print(f"[OK] Created {resource}/")

        elif resource == "assets":
            if include_examples:
                example_asset = resource_dir / "template.json"
                example_asset.write_text(EXAMPLE_ASSET.format(
                    skill_name=skill_name, skill_title=skill_title))
                print(f"[OK] Created {resource}/template.json")
            else:
                print(f"[OK] Created {resource}/")


def init_skill(skill_name: str, path: str, resources: list, include_examples: bool) -> Path:
    """
    Initialize a new skill directory with template SKILL.md.

    Returns:
        Path to created skill directory, or None if error
    """
    skill_dir = Path(path).resolve() / skill_name

    if skill_dir.exists():
        print(f"[ERROR] Skill directory already exists: {skill_dir}")
        return None

    try:
        skill_dir.mkdir(parents=True, exist_ok=False)
        print(f"[OK] Created skill directory: {skill_dir}")
    except Exception as e:
        print(f"[ERROR] Error creating directory: {e}")
        return None

    # Create SKILL.md
    skill_title = title_case_skill_name(skill_name)
    skill_content = SKILL_TEMPLATE.format(skill_name=skill_name, skill_title=skill_title)

    skill_md_path = skill_dir / "SKILL.md"
    try:
        skill_md_path.write_text(skill_content)
        print("[OK] Created SKILL.md")
    except Exception as e:
        print(f"[ERROR] Error creating SKILL.md: {e}")
        return None

    # Create resource directories
    if resources:
        try:
            create_resource_dirs(skill_dir, skill_name, skill_title, resources, include_examples)
        except Exception as e:
            print(f"[ERROR] Error creating resource directories: {e}")
            return None

    print(f"\n[OK] Skill '{skill_name}' initialized at {skill_dir}")
    print("\nNext steps:")
    print("1. Edit SKILL.md — complete the TODOs, write a strong description")
    print("2. Add resources to scripts/, references/, assets/ as needed")
    print("3. Run validate_skill.py to check for issues")
    print("4. Call skill_refresh() to make the skill available")

    return skill_dir


def main():
    parser = argparse.ArgumentParser(
        description="Create a new skill directory with SKILL.md template."
    )
    parser.add_argument("skill_name", help="Skill name (normalized to hyphen-case)")
    parser.add_argument("--path", required=True, help="Output directory for the skill")
    parser.add_argument(
        "--resources",
        default="",
        help="Comma-separated list: scripts,references,assets"
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Create example files in resource directories"
    )
    args = parser.parse_args()

    raw_name = args.skill_name
    skill_name = normalize_skill_name(raw_name)

    if not skill_name:
        print("[ERROR] Skill name must include at least one letter or digit.")
        sys.exit(1)

    if len(skill_name) > MAX_SKILL_NAME_LENGTH:
        print(f"[ERROR] Skill name too long ({len(skill_name)} > {MAX_SKILL_NAME_LENGTH})")
        sys.exit(1)

    if skill_name != raw_name:
        print(f"Note: Normalized '{raw_name}' to '{skill_name}'")

    resources = parse_resources(args.resources)

    if args.examples and not resources:
        print("[ERROR] --examples requires --resources to be set")
        sys.exit(1)

    print(f"Initializing skill: {skill_name}")
    print(f"   Location: {args.path}")
    if resources:
        print(f"   Resources: {', '.join(resources)}")
    print()

    result = init_skill(skill_name, args.path, resources, args.examples)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
