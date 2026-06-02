"""
Image Create skill exports — script-mode skill.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/image-create")
    from exports import generate_image, CATEGORY_STYLES, MODELS
    result = generate_image(
        prompt="a cute cat astronaut floating in space",
        category="illustration",
        style="fantasy",
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

from generate_image import (  # noqa: E402
    generate_image,
    CATEGORY_STYLES,
    CATEGORY_ASPECT_RATIOS,
    VALID_ASPECT_RATIOS,
    MODELS,
)

__all__ = [
    "generate_image",
    "CATEGORY_STYLES",
    "CATEGORY_ASPECT_RATIOS",
    "VALID_ASPECT_RATIOS",
    "MODELS",
]
