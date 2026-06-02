"""
Image Background Remove skill exports — script-mode skill.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/image-bg-remove")
    from exports import remove_bg
    result = remove_bg(image_path="uploads/photo.jpg")
    print(result)
    EOF
"""
import os
import sys

# Ensure the skill directory is importable regardless of cwd.
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
if _SKILL_DIR not in sys.path:
    sys.path.insert(0, _SKILL_DIR)

from remove_bg import (  # noqa: E402
    remove_bg,
    MODEL_ID,
    SUPPORTED_IMAGE_EXTS,
)

__all__ = [
    "remove_bg",
    "MODEL_ID",
    "SUPPORTED_IMAGE_EXTS",
]
