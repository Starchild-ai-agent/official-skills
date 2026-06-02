"""
Image 3D skill exports — script-mode skill.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/image-3d")
    from exports import generate_3d, CATEGORY_STYLES, CATEGORY_ASPECT_RATIOS
    result = generate_3d(
        prompt="a cute robot character",
        category="character",
        style="chibi",
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

from generate_3d import (  # noqa: E402
    generate_3d,
    CATEGORY_STYLES,
    CATEGORY_ASPECT_RATIOS,
    VALID_ASPECT_RATIOS,
    MODELS,
)

__all__ = [
    "generate_3d",
    "CATEGORY_STYLES",
    "CATEGORY_ASPECT_RATIOS",
    "VALID_ASPECT_RATIOS",
    "MODELS",
]
