"""
Image Try-On skill exports — script-mode skill.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/image-tryon")
    from exports import try_on, CATEGORIES, CATEGORY_PROMPTS, MODELS
    result = try_on(
        person_path="uploads/person.jpg",
        garment_path="uploads/dress.jpg",
        category="clothing",
    )
    print(result)
    EOF
"""
import os
import sys

# Ensure the skill directory is importable regardless of cwd.
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
if _SKILL_DIR not in sys.path:
    sys.path.insert(0, _SKILL_DIR)

from try_on import (  # noqa: E402
    try_on,
    CATEGORIES,
    CATEGORY_PROMPTS,
    VALID_ASPECT_RATIOS,
    MODELS,
)

__all__ = [
    "try_on",
    "CATEGORIES",
    "CATEGORY_PROMPTS",
    "VALID_ASPECT_RATIOS",
    "MODELS",
]
