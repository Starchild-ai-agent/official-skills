#!/usr/bin/env python3
"""E-commerce product photography script — professional product images for all platforms.

Supports three models:
  - nano2    (fal-ai/gemini-3.1-flash-image-preview/edit or /generate)   — fastest ~15s, good for drafts
  - nanopro  (fal-ai/gemini-3-pro-image-preview/edit or /generate) — balanced ~25s, good quality (default)
  - gpt      (openai/gpt-image-2/edit or /generate)     — best quality, slow ~150s

Modes:
  - With product image (edit): transforms existing product photo with new background/style
  - Without product image (text-to-image): generates product photo from description only

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

# ── Style prompt templates ───────────────────────────────────────────
# Each style produces a distinct product photography aesthetic.
# Derived from: product-photography skill (shot types, lighting, composition),
# eachlabs-product-visuals (workflow patterns), image-create product category.

STYLE_PROMPTS = {
    "hero": (
        "professional product hero shot, clean composition, studio lighting, "
        "commercial quality, e-commerce ready, product fills 80% of frame, "
        "slight 15-30 degree angle for dimension, one hero light plus fill, "
        "sharp focus on product, magazine advertisement quality"
    ),
    "lifestyle": (
        "product lifestyle photography, in-use context, natural setting, "
        "warm lighting, aspirational feel, shallow depth of field, "
        "editorial style, product naturally integrated into scene, "
        "authentic atmosphere, storytelling composition"
    ),
    "flat_lay": (
        "flat lay product photography, top-down bird's eye view, "
        "organized arrangement on clean surface, Instagram-worthy composition, "
        "soft overhead lighting, minimal props, coordinated color palette, "
        "negative space for text overlay, catalog quality"
    ),
    "detail": (
        "product detail close-up, macro photography, texture and material visible, "
        "sharp focus, high resolution, extreme close-up showing craftsmanship, "
        "soft directional lighting highlighting texture, luxury product photography, "
        "shallow depth of field, editorial quality"
    ),
    "packaging": (
        "product packaging photography, box and product together, unboxing feel, "
        "clean presentation, slight angle showing depth, "
        "studio lighting with subtle shadows, premium unboxing experience, "
        "brand packaging visible, commercial catalog quality"
    ),
    "group": (
        "product group shot, multiple items arranged together, cohesive styling, "
        "catalog quality, triangle composition for balance, "
        "soft overhead lighting, coordinated brand aesthetic, "
        "odd number arrangement, clean background, collection display"
    ),
    "scale": (
        "product with scale reference, size comparison with everyday object, "
        "clear proportions visible, product held in hand or next to known object, "
        "clean blurred background, natural lighting, "
        "lifestyle tech photography, informative composition"
    ),
    "seasonal_spring": (
        "product in spring setting, cherry blossoms, fresh green leaves, "
        "soft pastel colors, seasonal marketing, gentle natural light, "
        "floral elements, renewal theme, bright airy atmosphere, "
        "spring campaign photography"
    ),
    "seasonal_summer": (
        "product in summer setting, beach vibes, bright sunshine, "
        "tropical elements, summer campaign, vivid saturated colors, "
        "outdoor lifestyle, vacation aesthetic, warm golden light, "
        "energetic summer mood"
    ),
    "seasonal_autumn": (
        "product in autumn setting, fall leaves in warm golden tones, "
        "cozy atmosphere, harvest theme, warm amber lighting, "
        "rustic natural elements, comfortable seasonal mood, "
        "autumn campaign photography, rich earth tones"
    ),
    "seasonal_winter": (
        "product in winter setting, snow, holiday decorations, "
        "warm indoor lighting, festive mood, cozy winter atmosphere, "
        "soft warm glow, seasonal marketing, winter wonderland aesthetic, "
        "holiday campaign photography"
    ),
    "360_view": (
        "product 360 degree view, multiple angles shown in one image, "
        "turntable style presentation, pure white background, "
        "consistent studio lighting across all angles, "
        "front side back views, product rotation display, "
        "e-commerce multi-angle showcase"
    ),
    "comparison": (
        "product comparison layout, side by side arrangement, "
        "before and after or feature highlight, clean dividing line, "
        "consistent lighting and scale, informative composition, "
        "clear visual differentiation, comparison marketing image"
    ),
    "infographic": (
        "product infographic style, features labeled with callout arrows, "
        "clean design, informative layout, key specifications highlighted, "
        "dimensions and measurements shown, what's included display, "
        "professional technical illustration, marketing infographic"
    ),
}

# ── Background prompt templates ───────────────────────────────────────
# Derived from product-photography skill background guide.

BACKGROUND_PROMPTS = {
    "white": "pure white background #FFFFFF, clean, e-commerce standard, no shadows",
    "gradient": "soft gradient background, subtle color transition from white to light grey, modern feel",
    "studio": "professional studio setup, controlled lighting, neutral tones, subtle contact shadow",
    "natural": "natural environment, outdoor setting, organic feel, soft natural light",
    "lifestyle": "lifestyle context, home or office setting, in-use scenario, warm atmosphere",
    "colored": "solid colored background, vibrant, brand-matching, clean and bold",
    "textured": "textured background surface, marble or wood or fabric, premium feel, subtle texture",
    "transparent": "transparent background, product cutout, PNG ready, clean edges",
}

# ── Platform-specific presets ─────────────────────────────────────────
# E-commerce platform image requirements derived from product-photography skill.

PLATFORM_PRESETS = {
    "amazon": {
        "aspect_ratio": "1:1",
        "background": "white",
        "style": "hero",
        "notes": "Pure white bg (RGB 255,255,255), product fills 85%+, no props/text/watermarks, min 1000px (1600px+ recommended)",
    },
    "shopify": {
        "aspect_ratio": "1:1",
        "background": "white",
        "style": "hero",
        "notes": "Square format preferred, consistent style across catalog, 2048x2048 recommended",
    },
    "taobao": {
        "aspect_ratio": "1:1",
        "background": "white",
        "style": "hero",
        "notes": "800x800 minimum, white background for main image, lifestyle for secondary",
    },
    "instagram": {
        "aspect_ratio": "1:1",
        "background": "lifestyle",
        "style": "lifestyle",
        "notes": "1080x1080 for feed, lifestyle context preferred, visually appealing",
    },
    "xiaohongshu": {
        "aspect_ratio": "3:4",
        "background": "lifestyle",
        "style": "flat_lay",
        "notes": "1080x1440 vertical format, aesthetic flat lay or lifestyle, text overlay space",
    },
    "etsy": {
        "aspect_ratio": "4:3",
        "background": "natural",
        "style": "lifestyle",
        "notes": "Handmade/artisan feel, natural backgrounds, show craftsmanship",
    },
    "ebay": {
        "aspect_ratio": "1:1",
        "background": "white",
        "style": "hero",
        "notes": "White background, clear product view, 1600px minimum for zoom",
    },
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
            "For local files, use the product_path parameter instead."
        )
    return image_url, None


def _build_product_prompt(prompt=None, style="hero", background="white"):
    """Construct the product photography prompt from style + background + user prompt.

    Priority:
      1. prompt provided → use as primary, enhance with style/background context
      2. no prompt → combine style template + background template

    Returns the final prompt string.
    """
    style_text = STYLE_PROMPTS.get(style, STYLE_PROMPTS["hero"])
    bg_text = BACKGROUND_PROMPTS.get(background, BACKGROUND_PROMPTS["white"])

    if prompt:
        # User provided a custom prompt — enhance with style and background context
        return (
            f"{prompt}. "
            f"Photography style: {style_text}. "
            f"Background: {bg_text}."
        )
    else:
        # No custom prompt — use style + background templates
        return f"{style_text}, {bg_text}"


def _build_edit_prompt(prompt=None, style="hero", background="white"):
    """Build prompt for edit mode (with product image input).

    Wraps the product prompt with instructions to preserve the product
    while applying the desired style and background.
    """
    base_prompt = _build_product_prompt(prompt, style, background)

    return (
        f"Transform this product image into a professional e-commerce photo. "
        f"Keep the product exactly as it is — preserve its shape, color, details, "
        f"and branding. {base_prompt}"
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


def product_photo(
    product_path=None,
    product_url=None,
    prompt=None,
    style="hero",
    background="white",
    model="nanopro",
    count=1,
    aspect_ratio="1:1",
    platform=None,
    output_format=None,
):
    """Generate professional e-commerce product photography.

    This is the primary function for all product photography operations.
    Supports both edit mode (with product image) and generate mode (text-only).

    Args:
        product_path: Local workspace file path to the product image.
        product_url: Public HTTPS URL of the product image.
        prompt: Custom prompt describing the desired product photo.
            When provided with a style, enhances the style template.
            When provided alone, used as the primary instruction.
        style: Photography style preset — one of:
            hero, lifestyle, flat_lay, detail, packaging, group, scale,
            seasonal_spring, seasonal_summer, seasonal_autumn, seasonal_winter,
            360_view, comparison, infographic.
        background: Background type — one of:
            white, gradient, studio, natural, lifestyle, colored, textured, transparent.
        model: Model key — "nanopro" (default, fast ~25s) or
            "gpt" (best quality ~150s).
        count: Number of images to generate (1-4).
            Uses fal.ai native num_images for efficient batch generation.
        aspect_ratio: Output ratio — "1:1", "3:4", "4:3", "9:16", "16:9".
        platform: E-commerce platform preset — "amazon", "shopify", "taobao",
            "instagram", "xiaohongshu", "etsy", "ebay".
            When set, overrides style, background, and aspect_ratio with
            platform-optimized defaults (unless explicitly provided).
        output_format: Output image format — "png" (default), "jpeg", or "webp".

    Returns:
        dict with keys:
            success (bool): Whether generation succeeded.
            images (list[dict]): List of generated images, each with:
                local_path (str): Path to downloaded file.
                url (str): Original fal CDN URL.
                size_bytes (int): File size.
            model (str): Model used.
            style (str): Style applied.
            background (str): Background applied.
            platform (str|None): Platform preset used.
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

    # ── Apply platform preset ─────────────────────────────────────────
    platform_info = None
    if platform:
        platform_key = platform.lower()
        if platform_key in PLATFORM_PRESETS:
            preset = PLATFORM_PRESETS[platform_key]
            platform_info = preset
            # Platform overrides defaults but not explicit user choices
            if style == "hero":  # default value = not explicitly set
                style = preset["style"]
            if background == "white":  # default value = not explicitly set
                background = preset["background"]
            if aspect_ratio == "1:1":  # default value = not explicitly set
                aspect_ratio = preset["aspect_ratio"]

    # ── Validate style and background ─────────────────────────────────
    if style not in STYLE_PROMPTS:
        return {
            "success": False,
            "error": f"Unknown style: {style}. Available: {', '.join(sorted(STYLE_PROMPTS.keys()))}",
            "images": [],
        }
    if background not in BACKGROUND_PROMPTS:
        return {
            "success": False,
            "error": f"Unknown background: {background}. Available: {', '.join(sorted(BACKGROUND_PROMPTS.keys()))}",
            "images": [],
        }

    # ── Validate aspect ratio ─────────────────────────────────────────
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        return {
            "success": False,
            "error": f"Invalid aspect_ratio: {aspect_ratio}. Use: {', '.join(sorted(VALID_ASPECT_RATIOS))}",
            "images": [],
        }

    # ── Validate count and output format ──────────────────────────────
    count = max(1, min(MAX_COUNT, int(count)))
    fmt = output_format if output_format in VALID_OUTPUT_FORMATS else DEFAULT_OUTPUT_FORMAT

    # ── Resolve product image ─────────────────────────────────────────
    image_url, err = _resolve_image(product_path, product_url)
    if err:
        return {"success": False, "error": err, "images": []}

    # Determine mode: edit (with image) or generate (text-only)
    has_image = image_url is not None
    mode = "edit" if has_image else "generate"

    # ── Build prompt ──────────────────────────────────────────────────
    if has_image:
        final_prompt = _build_edit_prompt(prompt, style, background)
    else:
        if not prompt:
            return {
                "success": False,
                "error": "Either a product image (product_path/product_url) or a prompt describing the product is required.",
                "images": [],
            }
        final_prompt = _build_product_prompt(prompt, style, background)

    # ── Generate images ───────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_images = []
    total_cost = 0.0
    errors = []

    headers = {
        'Authorization': f'Key {_get_auth_key()}',
        'Content-Type': 'application/json',
    }
    headers.update(caller_headers(tool_default="image-ecommerce"))

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
            label = f"product_{style}"
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
        "style": style,
        "background": background,
        "platform": platform,
        "mode": mode,
        "output_format": fmt,
        "count_requested": count,
        "count_generated": len(all_images),
        "cost": round(total_cost, 6),
    }

    if errors:
        result["error"] = "; ".join(errors)
    if platform_info:
        result["platform_notes"] = platform_info.get("notes", "")

    return result


def product_photo_set(
    product_path=None,
    product_url=None,
    prompt=None,
    platform="amazon",
    model="nanopro",
):
    """Generate a complete e-commerce product image set (7-9 images).

    Creates a full set of product images following e-commerce best practices:
    1. Hero / packshot (white background)
    2. Lifestyle (product in use)
    3. Detail close-up (material/texture)
    4. Scale reference (size comparison)
    5. Alternate angle (side/back view)
    6. Packaging (unboxing)
    7. Group/collection (if applicable)

    Args:
        product_path: Local file path to the product image.
        product_url: Public URL of the product image.
        prompt: Description of the product (used to enhance all shots).
        platform: Target platform for image specs.
        model: Model key — "nanopro" or "gpt".

    Returns:
        dict with keys:
            success (bool): Whether at least some images were generated.
            sets (list[dict]): Each set item has shot_type, style, result.
            platform (str): Target platform.
            total_images (int): Total images generated.
            total_cost (float): Total credits used.
            errors (list[str]): Any errors encountered.
    """
    # Define the shot sequence
    shots = [
        {"shot_type": "hero", "style": "hero", "background": "white",
         "desc": "Primary listing image"},
        {"shot_type": "lifestyle", "style": "lifestyle", "background": "lifestyle",
         "desc": "Product in use/context"},
        {"shot_type": "detail", "style": "detail", "background": "studio",
         "desc": "Material/texture close-up"},
        {"shot_type": "scale", "style": "scale", "background": "studio",
         "desc": "Size reference"},
        {"shot_type": "alternate_angle", "style": "hero", "background": "white",
         "desc": "Side/back view"},
        {"shot_type": "packaging", "style": "packaging", "background": "studio",
         "desc": "Packaging/unboxing"},
        {"shot_type": "flat_lay", "style": "flat_lay", "background": "textured",
         "desc": "Flat lay arrangement"},
    ]

    # Get platform preset for aspect ratio
    platform_key = (platform or "amazon").lower()
    preset = PLATFORM_PRESETS.get(platform_key, PLATFORM_PRESETS["amazon"])
    ar = preset["aspect_ratio"]

    results = []
    total_cost = 0.0
    total_images = 0
    errors = []

    for shot in shots:
        # Build shot-specific prompt
        shot_prompt = prompt
        if prompt:
            shot_prompt = f"{prompt}, {shot['desc']}"

        # For alternate angle, add specific angle instruction
        if shot["shot_type"] == "alternate_angle":
            angle_extra = "three-quarter back view, showing the product from a different angle"
            shot_prompt = f"{shot_prompt}, {angle_extra}" if shot_prompt else angle_extra

        result = product_photo(
            product_path=product_path,
            product_url=product_url,
            prompt=shot_prompt,
            style=shot["style"],
            background=shot["background"],
            model=model,
            count=1,
            aspect_ratio=ar,
        )

        shot_result = {
            "shot_type": shot["shot_type"],
            "description": shot["desc"],
            "style": shot["style"],
            "background": shot["background"],
            "result": result,
        }
        results.append(shot_result)

        if result.get("success"):
            total_images += len(result.get("images", []))
            total_cost += result.get("cost", 0)
        else:
            errors.append(f"{shot['shot_type']}: {result.get('error', 'Unknown error')}")

    return {
        "success": total_images > 0,
        "sets": results,
        "platform": platform,
        "total_images": total_images,
        "total_cost": round(total_cost, 6),
        "errors": errors if errors else None,
    }