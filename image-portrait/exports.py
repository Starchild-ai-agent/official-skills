"""
Image Portrait skill exports — script-mode skill.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/image-portrait")
    from exports import generate_portrait, generate_series, STYLE_PROMPTS
    result = generate_portrait(
        face_image_url="https://example.com/photo.jpg",
        style="professional",
        count=1,
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

from generate_portrait import (  # noqa: E402
    generate_portrait,
    generate_series,
    STYLE_PROMPTS,
    VALID_ASPECT_RATIOS,
    MODELS,
)

__all__ = [
    "generate_portrait",
    "generate_series",
    "STYLE_PROMPTS",
    "VALID_ASPECT_RATIOS",
    "MODELS",
]
