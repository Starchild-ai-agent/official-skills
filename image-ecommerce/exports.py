"""
Image E-commerce skill exports — script-mode skill.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/image-ecommerce")
    from exports import product_photo, product_photo_set, STYLE_PROMPTS, BACKGROUND_PROMPTS, PLATFORM_PRESETS
    result = product_photo(
        product_path="uploads/product.jpg",
        style="hero",
        background="white",
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

from product_photo import (  # noqa: E402
    product_photo,
    product_photo_set,
    STYLE_PROMPTS,
    BACKGROUND_PROMPTS,
    PLATFORM_PRESETS,
    VALID_ASPECT_RATIOS,
    MODELS,
)

__all__ = [
    "product_photo",
    "product_photo_set",
    "STYLE_PROMPTS",
    "BACKGROUND_PROMPTS",
    "PLATFORM_PRESETS",
    "VALID_ASPECT_RATIOS",
    "MODELS",
]
