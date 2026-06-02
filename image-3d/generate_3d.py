#!/usr/bin/env python3
"""3D-style image generation script — 3D rendered 2D images for all 3D scenarios.

Generates 3D-style 2D images (NOT .glb/.obj 3D model files).
Covers: 3D characters, product renders, dioramas/isometric, icons, text,
interior design, architecture, scenes, and game assets.

Supports three models:
  - nano2    (fal-ai/gemini-3.1-flash-image-preview or /edit)   — fastest ~15s, good for drafts
  - nanopro  (fal-ai/gemini-3-pro-image-preview or /edit) — balanced ~25s, good quality (default)
  - gpt      (openai/gpt-image-2 or /edit)     — best quality, slow ~150s

Modes:
  - Text-to-image (primary): generates 3D-style images from text descriptions
  - Image-to-3D-style (edit): transforms a reference image into 3D-style rendering

Flow: resolve image → build prompt → submit to fal queue → poll → download.

Cost tracking: uses _cost_track.py to record per-call costs via sc-proxy
headers so the agent's per-turn cost_summary picks up this skill's cost.

Local testing: set FAL_KEY env var to call fal.ai directly (no sc-proxy).
"""

import requests
import json
import time
import os
import sys
import base64
import mimetypes
from datetime import datetime
from pathlib import Path
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Make _cost_track importable when this script is invoked from any CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from _cost_track import caller_headers, record_response  # noqa: E402

# Local testing: when FAL_KEY env var is set, call fal.ai directly
# (no sc-proxy). In production, sc-proxy injects the real key.
_FAL_KEY = os.environ.get("FAL_KEY")
_LOCAL_MODE = bool(_FAL_KEY)

PROXY_URL = 'http://sc-proxy.internal:8080'
PROXIES = {} if _LOCAL_MODE else {'http': PROXY_URL, 'https': PROXY_URL}

# ── Model configuration ──────────────────────────────────────────────
MODELS = {
    "nano2": {
        "edit": "fal-ai/gemini-3.1-flash-image-preview/edit",
        "generate": "fal-ai/gemini-3.1-flash-image-preview",
        "timeout": 90,        # nano2 faster
        "poll_interval": 2,
    },
    "nanopro": {
        "edit": "fal-ai/gemini-3-pro-image-preview/edit",
        "generate": "fal-ai/gemini-3-pro-image-preview",
        "timeout": 120,       # 2 min
        "poll_interval": 3,
    },
    "gpt": {
        "edit": "openai/gpt-image-2/edit",
        "generate": "openai/gpt-image-2",
        "timeout": 600,       # 10 min
        "poll_interval": 5,
    },
}
DEFAULT_MODEL = "nanopro"

# Supported image extensions for local file validation
SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

# ── 3D Category × Style prompt templates ─────────────────────────────
# Each category has multiple style presets. The prompt template encodes
# the 3D rendering keywords (materials, lighting, camera, engine style)
# that produce the best results with text-to-image models.
#
# Design sources:
#   - image-create 3D category (character, product, diorama, icon, text, scene)
#   - architecture-rendering skill (exterior/interior render prompts)
#   - interior-design-visualization skill (room styles, materials)
#   - 3d-model-generation skill (PBR materials, game assets)
#   - fal-regenerate-3d skill (character pipeline, Pixar/chibi styles)

CATEGORY_STYLES = {
    "character": {
        "chibi": (
            "3D chibi character design, cute stylized proportions, oversized head, "
            "Pixar-quality rendering, soft ambient occlusion, vibrant colors, "
            "clean studio lighting, white background"
        ),
        "realistic": (
            "3D realistic character model, detailed anatomy, PBR materials, "
            "studio lighting, neutral pose, game-ready quality, "
            "subsurface scattering on skin, high-detail textures"
        ),
        "cartoon": (
            "3D cartoon character, Disney/Pixar style, rounded features, "
            "bright colors, expressive face, clean background, "
            "smooth shading, appealing design, family-friendly aesthetic"
        ),
        "fantasy": (
            "3D fantasy character, detailed armor and weapons, epic pose, "
            "dramatic lighting, RPG game quality, PBR metallic materials, "
            "volumetric fog, cinematic composition"
        ),
        "default": (
            "3D character design, professional quality, clean rendering, "
            "studio lighting, appealing proportions, detailed materials"
        ),
    },
    "product": {
        "floating": (
            "3D product render, floating at 3/4 angle, studio lighting with "
            "soft reflections, gradient background, photorealistic materials, "
            "octane render quality, subtle shadow beneath"
        ),
        "exploded": (
            "3D exploded view product render, components separated showing "
            "internal structure, clean white background, technical illustration "
            "quality, precise engineering visualization"
        ),
        "turntable": (
            "3D product turntable view, multiple angles in one image, "
            "360 degree showcase, white background, commercial quality, "
            "consistent studio lighting across all angles"
        ),
        "default": (
            "3D product render, photorealistic materials, professional lighting, "
            "clean composition, commercial quality, subtle reflections"
        ),
    },
    "diorama": {
        "isometric": (
            "3D isometric diorama, miniature scene, warm lighting, tiny detailed "
            "elements, tilt-shift depth of field, clay render aesthetic, "
            "45-degree top-down camera angle, charming miniature world"
        ),
        "lowpoly": (
            "3D low-poly diorama, geometric shapes, flat shading, pastel colors, "
            "minimalist design, game art style, clean edges, "
            "stylized environment, indie game aesthetic"
        ),
        "realistic": (
            "3D realistic miniature scene, detailed textures, natural lighting, "
            "macro photography feel, photorealistic materials, "
            "depth of field, architectural model quality"
        ),
        "default": (
            "3D diorama scene, detailed miniature world, warm lighting, "
            "charming atmosphere, isometric perspective, clean rendering"
        ),
    },
    "icon": {
        "ios": (
            "3D app icon design, glossy material, rounded square shape, "
            "soft shadows, glass material with subtle gradient, "
            "clean white background, iOS style, skeuomorphic detail"
        ),
        "material": (
            "3D material design icon, flat colors with depth, subtle shadows, "
            "Google Material style, clean edges, geometric precision, "
            "modern UI icon, layered paper effect"
        ),
        "game": (
            "3D game icon, detailed rendering, fantasy style, glowing effects, "
            "dark background, RPG item icon quality, ornate border, "
            "magical particle effects"
        ),
        "default": (
            "3D icon design, clean rendering, professional quality, "
            "suitable for app or web, subtle shadows, modern aesthetic"
        ),
    },
    "text": {
        "chrome": (
            "3D text rendering, bold chrome letters, metallic reflections, "
            "volumetric lighting, cinematic composition, mirror-finish surface, "
            "dramatic studio lighting, dark background"
        ),
        "neon": (
            "3D neon text, glowing letters, dark background, colorful light effects, "
            "cyberpunk atmosphere, light bloom, reflective wet floor, "
            "futuristic urban setting"
        ),
        "wood": (
            "3D wooden text, natural wood texture, warm lighting, rustic feel, "
            "craft quality, visible wood grain, soft shadows, "
            "cozy atmosphere, handmade aesthetic"
        ),
        "candy": (
            "3D candy text, glossy colorful letters, sweet theme, playful design, "
            "fun atmosphere, sugar coating effect, sprinkles, "
            "bright pastel background, whimsical"
        ),
        "default": (
            "3D text rendering, bold letters, professional quality, "
            "clean composition, studio lighting, modern typography"
        ),
    },
    "interior": {
        "modern": (
            "3D interior design render, modern minimalist style, clean lines, "
            "natural light through large windows, Scandinavian aesthetic, "
            "architectural visualization quality, warm neutral palette, "
            "polished concrete and natural wood materials"
        ),
        "luxury": (
            "3D luxury interior render, high-end materials, marble and gold accents, "
            "dramatic lighting, penthouse quality, crystal chandelier, "
            "rich textures, velvet and silk fabrics, opulent atmosphere"
        ),
        "cozy": (
            "3D cozy interior render, warm lighting, soft textures, "
            "comfortable furniture, hygge atmosphere, warm color palette, "
            "plush rugs, ambient candlelight, inviting space"
        ),
        "industrial": (
            "3D industrial loft interior, exposed brick walls, metal beams, "
            "Edison bulbs, urban chic, raw concrete, reclaimed wood, "
            "open floor plan, warehouse conversion aesthetic"
        ),
        "default": (
            "3D interior design visualization, professional rendering, "
            "realistic materials and lighting, architectural quality, "
            "well-composed room view, natural daylight"
        ),
    },
    "architecture": {
        "modern": (
            "3D modern architecture render, clean geometric forms, glass and steel, "
            "dramatic sky, architectural visualization, photorealistic quality, "
            "landscaping context, golden hour lighting, professional archviz"
        ),
        "traditional": (
            "3D traditional architecture render, classical elements, stone and wood, "
            "warm lighting, heritage feel, ornate details, "
            "historical accuracy, mature landscaping"
        ),
        "futuristic": (
            "3D futuristic architecture, organic forms, sustainable design, "
            "green technology, sci-fi cityscape, parametric facade, "
            "bioluminescent accents, utopian atmosphere"
        ),
        "aerial": (
            "3D aerial architectural render, bird's eye view, masterplan perspective, "
            "45-degree angle, surrounding context visible, "
            "landscaping and roads, professional archviz quality"
        ),
        "night": (
            "3D architectural night render, dramatic nighttime scene, "
            "warm interior glow through windows, facade uplighting, "
            "wet pavement reflections, sophisticated atmosphere"
        ),
        "default": (
            "3D architectural visualization, professional rendering, "
            "realistic materials, environmental context, "
            "natural lighting, photorealistic quality"
        ),
    },
    "scene": {
        "fantasy": (
            "3D fantasy scene, magical environment, floating islands, "
            "crystal formations, ethereal lighting, concept art quality, "
            "volumetric god rays, enchanted atmosphere"
        ),
        "scifi": (
            "3D sci-fi scene, space station interior, holographic displays, "
            "futuristic technology, cinematic lighting, neon accents, "
            "high-tech environment, cyberpunk aesthetic"
        ),
        "nature": (
            "3D nature scene, lush forest, volumetric light rays, "
            "detailed foliage, photorealistic rendering, "
            "atmospheric perspective, serene mood"
        ),
        "urban": (
            "3D urban scene, city street, neon signs, rain reflections, "
            "cyberpunk atmosphere, dense urban environment, "
            "atmospheric fog, cinematic composition"
        ),
        "default": (
            "3D scene rendering, detailed environment, atmospheric lighting, "
            "professional quality, immersive composition"
        ),
    },
    "game_asset": {
        "weapon": (
            "3D game weapon render, detailed metallic materials, "
            "fantasy RPG style, glowing enchantment effects, "
            "dark background, item showcase, game-ready quality"
        ),
        "environment": (
            "3D game environment concept, stylized world design, "
            "vibrant colors, level design quality, "
            "atmospheric lighting, explorable space feel"
        ),
        "prop": (
            "3D game prop render, detailed object, stylized textures, "
            "clean presentation, game-ready quality, "
            "consistent art style, subtle wear and tear"
        ),
        "vehicle": (
            "3D game vehicle render, detailed model, dynamic angle, "
            "motion blur suggestion, studio lighting, "
            "polished materials, racing game quality"
        ),
        "default": (
            "3D game asset render, professional quality, "
            "game-ready presentation, clean lighting, "
            "detailed materials, stylized aesthetic"
        ),
    },
}

# ── Category aspect ratio defaults ────────────────────────────────────
# Auto-selected when user doesn't specify aspect_ratio.
CATEGORY_ASPECT_RATIOS = {
    "character": "3:4",      # Portrait orientation for characters
    "product": "1:1",        # Square for product showcase
    "diorama": "1:1",        # Square for isometric scenes
    "icon": "1:1",           # Square for icons
    "text": "16:9",          # Wide for text banners
    "interior": "16:9",      # Wide for room views
    "architecture": "16:9",  # Wide for building exteriors
    "scene": "16:9",         # Wide for environments
    "game_asset": "1:1",     # Square for asset showcase
}

# ── Constants ─────────────────────────────────────────────────────────
MAX_COUNT = 4  # fal.ai API supports up to 4 images per call
VALID_ASPECT_RATIOS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
}
DEFAULT_ASPECT_RATIO = "1:1"
VALID_OUTPUT_FORMATS = {"jpeg", "png", "webp"}
DEFAULT_OUTPUT_FORMAT = "png"
OUTPUT_DIR = "output/images"


def _get_auth_key():
    """Return the appropriate fal API key."""
    return _FAL_KEY if _LOCAL_MODE else 'fake-falai-key-12345'


def _get_model_config(model_key):
    """Return model config dict for the given key."""
    return MODELS.get(model_key, MODELS[DEFAULT_MODEL])


def _resolve_image(image_path=None, image_url=None):
    """Resolve an image input to a URL for the fal API.

    Accepts either a local file path or a public URL.
    Local files are base64-encoded as data URIs.

    Returns (url_string, error_string).
    """
    if not image_path and not image_url:
        return None, None  # No image = text-to-image mode

    if image_path:
        p = Path(image_path)
        if not p.exists():
            return None, f"File not found: {image_path}"
        if not p.is_file():
            return None, f"Not a file: {image_path}"

        ext = p.suffix.lower()
        if ext not in SUPPORTED_IMAGE_EXTS:
            return None, (
                f"Unsupported image format: {ext}. "
                f"Supported: {', '.join(sorted(SUPPORTED_IMAGE_EXTS))}"
            )

        size = p.stat().st_size
        if size > MAX_IMAGE_BYTES:
            return None, (
                f"Image too large: {size / 1024 / 1024:.1f} MB "
                f"(max {MAX_IMAGE_BYTES / 1024 / 1024:.0f} MB)"
            )

        mime_type = mimetypes.guess_type(str(p))[0] or "image/jpeg"
        with open(p, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
        return f"data:{mime_type};base64,{b64}", None

    # URL input
    if not image_url.startswith(("http://", "https://")):
        return None, (
            "image_url must be a public HTTP(S) URL. "
            "For local files, use the reference_path parameter instead."
        )
    return image_url, None


def _build_3d_prompt(prompt=None, category="character", style=None):
    """Construct the 3D generation prompt from category + style + user prompt.

    Priority:
      1. prompt + category/style → user prompt enhanced with 3D style template
      2. prompt only → use as-is with generic 3D enhancement
      3. category + style → use the built-in style template as the full prompt
      4. category only → use the default style for that category

    Returns the final prompt string.
    """
    # Get the style templates for this category
    cat_styles = CATEGORY_STYLES.get(category, CATEGORY_STYLES["character"])

    # Resolve style key
    if style and style in cat_styles:
        style_text = cat_styles[style]
    else:
        style_text = cat_styles.get("default", cat_styles[list(cat_styles.keys())[0]])

    if prompt:
        # User provided a custom prompt — enhance with 3D style context
        return (
            f"{prompt}. "
            f"Render style: {style_text}."
        )
    else:
        # No custom prompt — use style template as the full prompt
        return style_text


def _build_edit_prompt(prompt=None, category="character", style=None):
    """Build prompt for edit mode (with reference image input).

    Wraps the 3D prompt with instructions to transform the reference
    image into a 3D-style rendering while preserving key features.
    """
    base_prompt = _build_3d_prompt(prompt, category, style)

    return (
        f"Transform this image into a 3D rendered style. "
        f"Preserve the key subject, composition, and important details "
        f"while applying 3D rendering aesthetics. {base_prompt}"
    )


def _aspect_ratio_to_size(aspect_ratio):
    """Convert aspect ratio string to fal image_size dict.

    Sizes aligned with image_generate tool capabilities
    (core/image_models.py _STD_ASPECTS / _NANO2_ASPECTS).
    """
    mapping = {
        "1:1":  {"width": 1024, "height": 1024},
        "2:3":  {"width": 680,  "height": 1024},
        "3:2":  {"width": 1024, "height": 680},
        "3:4":  {"width": 768,  "height": 1024},
        "4:3":  {"width": 1024, "height": 768},
        "4:5":  {"width": 816,  "height": 1024},
        "5:4":  {"width": 1024, "height": 816},
        "9:16": {"width": 576,  "height": 1024},
        "16:9": {"width": 1024, "height": 576},
        "21:9": {"width": 1024, "height": 440},
    }
    return mapping.get(aspect_ratio, mapping["1:1"])


def _build_request_body(prompt, image_url=None, aspect_ratio="1:1", model_key="nanopro",
                        count=1, output_format="png"):
    """Build the request body for the fal API."""
    body = {
        "prompt": prompt,
        "num_images": count,
        "seed": int(time.time() * 1000) % (2**32),
        "output_format": output_format,
    }

    # Add image URL for edit mode
    if image_url:
        body["image_urls"] = [image_url]

    # nano2/nanopro use aspect_ratio string; gpt uses image_size object
    if aspect_ratio and aspect_ratio in VALID_ASPECT_RATIOS:
        if model_key != "gpt":
            body["aspect_ratio"] = aspect_ratio
        else:
            body["image_size"] = _aspect_ratio_to_size(aspect_ratio)
            body["quality"] = "high"

    return body


def _submit_request(prompt, image_url, model_key, headers, aspect_ratio="1:1",
                    count=1, output_format="png"):
    """Submit a request to the fal queue (edit or generate mode)."""
    cfg = _get_model_config(model_key)

    # Choose edit vs generate endpoint based on whether we have an image
    if image_url:
        model_id = cfg["edit"]
    else:
        model_id = cfg["generate"]

    submit_url = f"https://queue.fal.run/{model_id}"
    body = _build_request_body(prompt, image_url, aspect_ratio, model_key,
                               count=count, output_format=output_format)

    resp = requests.post(
        submit_url, headers=headers, json=body,
        proxies=PROXIES, verify=False, timeout=90,
    )

    record_response(resp, request_url=submit_url, request_payload=body)

    if resp.status_code != 200:
        return None, f"Submit failed: {resp.status_code} - {resp.text[:300]}"

    data = resp.json()
    cost = float(resp.headers.get('X-Credits-Used', 0))
    data['_cost'] = cost
    return data, None


def _poll_until_done(status_url, request_id, model_key):
    """Poll the fal queue until the request completes or fails."""
    cfg = _get_model_config(model_key)
    headers = {'Authorization': f'Key {_get_auth_key()}'}
    deadline = time.time() + cfg["timeout"]
    poll_interval = cfg["poll_interval"]

    while time.time() < deadline:
        try:
            poll_resp = requests.get(
                status_url, headers=headers,
                proxies=PROXIES, verify=False, timeout=60,
            )
            status_data = poll_resp.json()
            status = status_data.get('status')

            if status == 'COMPLETED':
                return "COMPLETED", None
            elif status in ('FAILED', 'CANCELLED'):
                return status, f"Generation {status}"
        except requests.RequestException:
            pass

        time.sleep(poll_interval)

    return "TIMEOUT", f"Generation timed out after {cfg['timeout'] // 60} minutes"


def _extract_image_urls(result_json):
    """Extract image URLs from fal response across model variants."""
    if not isinstance(result_json, dict):
        return []

    urls = []

    for key in ("images", "output", "outputs", "data"):
        arr = result_json.get(key)
        if isinstance(arr, list):
            for item in arr:
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    urls.append(item["url"])
                elif isinstance(item, dict) and isinstance(item.get("b64_json"), str):
                    urls.append(f"data:image/png;base64,{item['b64_json']}")
                elif isinstance(item, str) and item.startswith("http"):
                    urls.append(item)

    if not urls:
        for key in ("image", "output_image"):
            node = result_json.get(key)
            if isinstance(node, dict) and isinstance(node.get("url"), str):
                urls.append(node["url"])
            elif isinstance(node, str) and node.startswith("http"):
                urls.append(node)

    return urls


def _download_image(url, index, label, timestamp):
    """Download a single image from fal CDN to the output directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if url.startswith("data:"):
        ext = ".png"
        filename = f"{timestamp}_{label}_{index}{ext}"
        local_path = os.path.join(OUTPUT_DIR, filename)

        b64_data = url.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_data)

        with open(local_path, 'wb') as f:
            f.write(img_bytes)
        return local_path, len(img_bytes)

    ext = ".png"
    if ".jpg" in url or ".jpeg" in url:
        ext = ".jpg"
    elif ".webp" in url:
        ext = ".webp"

    filename = f"{timestamp}_{label}_{index}{ext}"
    local_path = os.path.join(OUTPUT_DIR, filename)

    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    with open(local_path, 'wb') as f:
        f.write(resp.content)

    return local_path, len(resp.content)


def generate_3d(
    prompt=None,
    reference_path=None,
    reference_url=None,
    category="character",
    style=None,
    model="nanopro",
    count=1,
    aspect_ratio=None,
    output_format=None,
):
    """Generate 3D-style 2D images.

    This is the primary function for all 3D image generation operations.
    Produces 3D-rendered 2D images (NOT .glb/.obj 3D model files).

    Supports both text-to-image (primary) and edit mode (reference → 3D style).

    Args:
        prompt: Text description of the desired 3D image.
            When provided with a category/style, enhances the style template.
            When provided alone, used as the primary instruction with 3D enhancement.
        reference_path: Local workspace file path to a reference image (optional).
            Used for image-to-3D-style transformation.
        reference_url: Public HTTPS URL of a reference image (optional).
            Used for image-to-3D-style transformation.
        category: 3D category preset — one of:
            character, product, diorama, icon, text, interior,
            architecture, scene, game_asset.
        style: Sub-style within the category (see CATEGORY_STYLES).
            If None, uses the "default" style for the category.
        model: Model key — "nanopro" (default, fast ~25s) or
            "gpt" (best quality ~150s).
        count: Number of images to generate (1-4).
            Uses fal.ai native num_images for efficient batch generation.
        aspect_ratio: Output ratio — "1:1", "3:4", "4:3", "9:16", "16:9".
            If None, auto-selected based on category.
        output_format: Output image format — "png" (default), "jpeg", or "webp".

    Returns:
        dict with keys:
            success (bool): Whether generation succeeded.
            images (list[dict]): List of generated images, each with:
                local_path (str): Path to downloaded file.
                url (str): Original fal CDN URL.
                size_bytes (int): File size.
            model (str): Model used.
            category (str): Category applied.
            style (str): Style applied.
            mode (str): "edit" or "generate".
            cost (float): Total credits used.
            error (str|None): Error message if failed.
    """
    # ── Validate model ────────────────────────────────────────────────
    model_key = model.lower() if model else DEFAULT_MODEL
    if model_key not in MODELS:
        return {
            "success": False,
            "error": f"Unknown model: {model}. Use 'nanopro' or 'gpt'.",
            "images": [],
        }

    # ── Validate category ─────────────────────────────────────────────
    if category not in CATEGORY_STYLES:
        return {
            "success": False,
            "error": (
                f"Unknown category: {category}. "
                f"Available: {', '.join(sorted(CATEGORY_STYLES.keys()))}"
            ),
            "images": [],
        }

    # ── Validate style ────────────────────────────────────────────────
    cat_styles = CATEGORY_STYLES[category]
    resolved_style = style or "default"
    if resolved_style not in cat_styles:
        return {
            "success": False,
            "error": (
                f"Unknown style '{resolved_style}' for category '{category}'. "
                f"Available: {', '.join(sorted(cat_styles.keys()))}"
            ),
            "images": [],
        }

    # ── Resolve aspect ratio ──────────────────────────────────────────
    if aspect_ratio is None:
        aspect_ratio = CATEGORY_ASPECT_RATIOS.get(category, DEFAULT_ASPECT_RATIO)

    if aspect_ratio not in VALID_ASPECT_RATIOS:
        return {
            "success": False,
            "error": f"Invalid aspect_ratio: {aspect_ratio}. Use: {', '.join(sorted(VALID_ASPECT_RATIOS))}",
            "images": [],
        }

    # ── Validate count and output format ──────────────────────────────
    count = max(1, min(MAX_COUNT, int(count)))
    fmt = output_format if output_format in VALID_OUTPUT_FORMATS else DEFAULT_OUTPUT_FORMAT

    # ── Resolve reference image ───────────────────────────────────────
    image_url, err = _resolve_image(reference_path, reference_url)
    if err:
        return {"success": False, "error": err, "images": []}

    # Determine mode: edit (with reference image) or generate (text-only)
    has_image = image_url is not None
    mode = "edit" if has_image else "generate"

    # ── Build prompt ──────────────────────────────────────────────────
    if has_image:
        final_prompt = _build_edit_prompt(prompt, category, resolved_style)
    else:
        if not prompt and resolved_style == "default":
            return {
                "success": False,
                "error": (
                    "A prompt is required for text-to-image generation. "
                    "Provide a prompt describing what you want, or specify "
                    "a category + style to use a built-in template."
                ),
                "images": [],
            }
        final_prompt = _build_3d_prompt(prompt, category, resolved_style)

    # ── Generate images ───────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_images = []
    total_cost = 0.0
    errors = []

    headers = {
        'Authorization': f'Key {_get_auth_key()}',
        'Content-Type': 'application/json',
    }
    headers.update(caller_headers(tool_default="image-3d"))

    # Single API call with num_images=count for efficient batch generation
    submit_data, submit_err = _submit_request(
        final_prompt, image_url, model_key, headers, aspect_ratio,
        count=count, output_format=fmt,
    )
    if submit_err:
        return {"success": False, "error": submit_err, "images": []}

    request_id = submit_data.get('request_id')
    status_url = submit_data.get('status_url')
    response_url = submit_data.get('response_url')
    total_cost += submit_data.get('_cost', 0)

    if not request_id or not status_url:
        return {"success": False, "error": "Missing request_id or status_url in response", "images": []}

    # Poll until done
    status, poll_err = _poll_until_done(status_url, request_id, model_key)
    if status != "COMPLETED":
        return {"success": False, "error": poll_err or status, "images": []}

    # Fetch result
    try:
        result_headers = {'Authorization': f'Key {_get_auth_key()}'}
        result_resp = requests.get(
            response_url, headers=result_headers,
            proxies=PROXIES, verify=False, timeout=60,
        )
        result_json = result_resp.json()
    except Exception as e:
        return {"success": False, "error": f"Failed to fetch result: {e}", "images": []}

    # Extract and download images
    img_urls = _extract_image_urls(result_json)
    if not img_urls:
        return {"success": False, "error": "No images in response", "images": []}

    for j, img_url in enumerate(img_urls):
        try:
            label = f"3d_{category}_{resolved_style}"
            local_path, size_bytes = _download_image(
                img_url, j, label, timestamp,
            )
            all_images.append({
                "local_path": local_path,
                "url": img_url if not img_url.startswith("data:") else "(base64)",
                "size_bytes": size_bytes,
            })
        except Exception as e:
            errors.append(f"Download failed: {e}")

    # ── Build result ──────────────────────────────────────────────────
    result = {
        "success": len(all_images) > 0,
        "images": all_images,
        "model": model_key,
        "category": category,
        "style": resolved_style,
        "mode": mode,
        "output_format": fmt,
        "count_requested": count,
        "count_generated": len(all_images),
        "cost": round(total_cost, 6),
    }

    if errors:
        result["error"] = "; ".join(errors)

    return result