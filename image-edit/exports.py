"""
Image Edit skill exports — script-mode skill.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/image-edit")
    from exports import edit_image, ACTIONS, MODELS
    result = edit_image(
        image_path="uploads/photo.jpg",
        prompt="remove the background and replace with a beach sunset",
        action="replace_bg",
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

from edit_image import (  # noqa: E402
    edit_image,
    ACTIONS,
    ACTION_PROMPTS,
    ACTION_DEFAULT_PROMPTS,
    VALID_ASPECT_RATIOS,
    MODELS,
)

__all__ = [
    "edit_image",
    "ACTIONS",
    "ACTION_PROMPTS",
    "ACTION_DEFAULT_PROMPTS",
    "VALID_ASPECT_RATIOS",
    "MODELS",
]
