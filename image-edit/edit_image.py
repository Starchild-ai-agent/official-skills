#!/usr/bin/env python3
"""Image editing script — edit, enhance, and transform existing images.

Supports three models:
  - nano2    (fal-ai/gemini-3.1-flash-image-preview/edit)     — fastest ~15s, good for drafts
  - nanopro  (fal-ai/gemini-3-pro-image-preview/edit)   — balanced ~25s, good quality (default)
  - gpt      (openai/gpt-image-2/edit)       — best quality, slow ~150s

Covers: general editing, background replacement, upscaling, restoration,
colorization, inpainting, retouching, beauty enhancement, filters,
car customization, before/after comparison, outpainting, and more.

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
        "timeout": 90,
        "poll_interval": 2,
    },
    "nanopro": {
        "edit": "fal-ai/gemini-3-pro-image-preview/edit",
        "timeout": 120,
        "poll_interval": 3,
    },
    "gpt": {
        "edit": "openai/gpt-image-2/edit",
        "timeout": 600,
        "poll_interval": 5,
    },
}
DEFAULT_MODEL = "nanopro"

# Supported image extensions
SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

# ── Action definitions ────────────────────────────────────────────────
# Each action maps to an optimized prompt template that wraps the user's
# intent into a high-quality editing instruction.

ACTIONS = {
    # === F: Multi-image / general editing ===
    "edit": "General edit — modify the image according to the prompt",
    "blend": "Image blending — place a person into a new background/scene",
    "extend": "Outpainting — extend the image beyond its current boundaries",
    "local_edit": "Local edit — modify only a specific region of the image",
    "text_render": "Text rendering — add or modify text within the image",
    "multi_angle": "Multi-angle — generate different viewing angles from one photo",
    "before_after": "Before/after comparison — generate a side-by-side comparison",

    # === G: Professional editing ===
    "replace_bg": "Background replacement — swap the background while keeping the subject",
    "upscale": "Super-resolution — upscale and enhance image resolution",
    "restore": "Photo restoration — repair scratches, tears, fading in old photos",
    "colorize": "Colorization — add realistic colors to black-and-white photos",
    "remove_person": "Person removal — remove a specific person from the photo",

    # === V: Retouching / beauty ===
    "retouch": "Portrait retouching — skin smoothing, blemish removal, teeth whitening",
    "slim": "Slimming — adjust facial and body proportions subtly",
    "enhance": "Enhancement — color correction, lighting improvement, quality boost",
    "filter": "Artistic filter — apply a specific artistic style or filter effect",

    # === W: Medical / fitness ===
    "comparison": "Comparison — before/after for medical, fitness, or transformation",

    # === X: Automotive ===
    "car_color": "Car recolor — change the color of a vehicle",
    "car_wrap": "Car wrap preview — visualize a wrap or film on a vehicle",
}

# ── Action prompt templates ───────────────────────────────────────────
# These templates wrap the user's prompt to produce optimal results.
# {prompt} is replaced with the user's specific instruction.

ACTION_PROMPTS = {
    "edit": (
        "Edit this image: {prompt}. "
        "Maintain the overall composition and quality of the original image. "
        "Apply the requested changes precisely while preserving unaffected areas."
    ),
    "blend": (
        "Seamlessly blend the subject from this image into the described scene: {prompt}. "
        "Match lighting, perspective, and color temperature between the subject and "
        "the new environment. Ensure natural shadows and reflections. "
        "The result should look like a real photograph, not a composite."
    ),
    "extend": (
        "Extend this image beyond its current boundaries: {prompt}. "
        "Generate new content that seamlessly continues the existing scene. "
        "Match the style, lighting, perspective, and color palette of the original. "
        "Ensure no visible seams or discontinuities at the boundary."
    ),
    "local_edit": (
        "Make a local edit to this image: {prompt}. "
        "Only modify the specified region. Keep everything else exactly as in the original. "
        "Ensure the edited area blends naturally with the surrounding content."
    ),
    "text_render": (
        "Add or modify text in this image: {prompt}. "
        "Render the text clearly and legibly. Match the visual style of the image. "
        "Ensure proper font weight, color contrast, and placement. "
        "The text should look naturally integrated, not pasted on."
    ),
    "multi_angle": (
        "Generate a different viewing angle of the subject in this image: {prompt}. "
        "Maintain the subject's identity, proportions, and details. "
        "Adjust perspective, lighting, and shadows consistently for the new angle. "
        "The result should look like a real photo taken from the described viewpoint."
    ),
    "before_after": (
        "Create a before/after comparison: {prompt}. "
        "Generate a side-by-side image showing the transformation. "
        "Left side shows the original state, right side shows the result. "
        "Add a clean dividing line between the two halves. "
        "Ensure both halves have consistent framing and scale."
    ),
    "replace_bg": (
        "Replace the background of this image: {prompt}. "
        "Keep the foreground subject perfectly intact with clean edges. "
        "Match the lighting direction and color temperature of the new background "
        "to the subject. Add appropriate shadows and reflections. "
        "The result should look like the subject was photographed in the new setting."
    ),
    "upscale": (
        "Upscale and enhance this image to higher resolution: {prompt}. "
        "Increase detail and sharpness while preserving the original content. "
        "Enhance textures, reduce noise and compression artifacts. "
        "Maintain natural appearance without over-sharpening or hallucinating details."
    ),
    "restore": (
        "Restore this old or damaged photograph: {prompt}. "
        "Repair scratches, tears, creases, stains, and fading. "
        "Reconstruct missing or damaged areas based on surrounding context. "
        "Enhance clarity while preserving the authentic character of the original photo. "
        "Fix color shifts and restore proper tonal range."
    ),
    "colorize": (
        "Colorize this black-and-white photograph with realistic, natural colors: {prompt}. "
        "Apply historically and contextually appropriate colors. "
        "Use realistic skin tones for people, natural colors for landscapes and objects. "
        "Maintain the original detail and tonal range. "
        "The result should look like a naturally colored photograph, not artificially tinted."
    ),
    "remove_person": (
        "Remove the specified person from this photo: {prompt}. "
        "Fill the area where the person was with content that matches the surrounding "
        "background seamlessly. Reconstruct any occluded background elements. "
        "Ensure no ghosting, artifacts, or visible editing traces remain."
    ),
    "retouch": (
        "Professionally retouch this portrait: {prompt}. "
        "Apply natural skin smoothing that preserves texture and pores. "
        "Remove blemishes, acne, and skin imperfections. "
        "Subtly whiten teeth and brighten eyes if visible. "
        "Enhance skin tone evenness while maintaining a realistic, non-plastic look. "
        "Keep the person's natural features and character."
    ),
    "slim": (
        "Subtly adjust proportions in this portrait: {prompt}. "
        "Apply natural-looking slimming to the specified areas. "
        "Maintain realistic body proportions and avoid distortion. "
        "Ensure the background and surrounding elements are not warped. "
        "The result should look natural and unedited."
    ),
    "enhance": (
        "Enhance this image: {prompt}. "
        "Improve color vibrancy, contrast, and tonal balance. "
        "Optimize lighting and exposure. Reduce noise while preserving detail. "
        "Apply professional-grade color grading for a polished look. "
        "The result should look like a professionally edited photograph."
    ),
    "filter": (
        "Apply an artistic filter to this image: {prompt}. "
        "Transform the visual style while preserving the composition and subject. "
        "Ensure the filter effect is applied consistently across the entire image. "
        "Maintain recognizable content while achieving the desired artistic effect."
    ),
    "comparison": (
        "Create a transformation comparison image: {prompt}. "
        "Generate a professional before/after layout showing the change. "
        "Use clean framing with consistent scale and alignment. "
        "Add subtle labels or a dividing element if appropriate. "
        "The comparison should clearly communicate the transformation."
    ),
    "car_color": (
        "Change the color of the vehicle in this image: {prompt}. "
        "Apply the new color realistically with proper metallic/matte finish. "
        "Maintain reflections, highlights, and shadows appropriate for the new color. "
        "Keep all other elements (wheels, trim, background) unchanged. "
        "The result should look like a factory paint job, not a digital overlay."
    ),
    "car_wrap": (
        "Apply a vehicle wrap or film to the car in this image: {prompt}. "
        "Render the wrap material realistically following the car's body contours. "
        "Show proper material properties (matte, gloss, satin, chrome, carbon fiber). "
        "Maintain reflections and lighting consistent with the wrap material. "
        "Keep wheels, windows, and trim unaffected."
    ),
}

# ── Default prompts when user provides no specific instruction ─────────
ACTION_DEFAULT_PROMPTS = {
    "edit": "Enhance and improve this image while maintaining its original character",
    "blend": "Place the subject into a professional studio setting with soft lighting",
    "extend": "Extend the image naturally in all directions, continuing the scene",
    "local_edit": "Clean up and improve the central area of the image",
    "text_render": "Add elegant text overlay that complements the image",
    "multi_angle": "Show this subject from a three-quarter view angle",
    "before_after": "Show a before and after comparison of image enhancement",
    "replace_bg": "Replace the background with a clean, professional studio backdrop",
    "upscale": "Upscale to maximum quality with enhanced detail and sharpness",
    "restore": "Restore this photo by repairing all visible damage and improving clarity",
    "colorize": "Add natural, realistic colors appropriate to the era and content",
    "remove_person": "Remove the indicated person and fill with matching background",
    "retouch": "Apply professional portrait retouching with natural skin smoothing",
    "slim": "Apply subtle, natural-looking facial slimming",
    "enhance": "Enhance colors, lighting, contrast, and overall image quality",
    "filter": "Apply a cinematic color grading filter with warm tones",
    "comparison": "Create a professional before/after transformation comparison",
    "car_color": "Change the car color to a deep metallic blue",
    "car_wrap": "Apply a matte black wrap to the vehicle",
}

# ── Constants ─────────────────────────────────────────────────────────
MAX_COUNT = 4  # fal.ai API supports up to 4 images per call
DEFAULT_COUNT = 1
VALID_ASPECT_RATIOS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
}
DEFAULT_ASPECT_RATIO = None  # None = preserve original image ratio
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
        return None, "Either image_path or image_url must be provided for editing."

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
            "For local files, use the image_path parameter instead."
        )
    return image_url, None


def _build_edit_prompt(prompt=None, action="edit"):
    """Construct the editing prompt from action template and user instruction.

    Priority:
      1. prompt provided → wrap with action template
      2. no prompt → use action default prompt with template

    Returns the final prompt string.
    """
    user_prompt = prompt if prompt else ACTION_DEFAULT_PROMPTS.get(action, "")
    template = ACTION_PROMPTS.get(action, ACTION_PROMPTS["edit"])
    return template.format(prompt=user_prompt)


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


def _build_request_body(prompt, image_urls, aspect_ratio=None, model_key="nanopro",
                        count=1, output_format="png"):
    """Build the request body for the fal edit API."""
    body = {
        "prompt": prompt,
        "num_images": count,
        "seed": int(time.time() * 1000) % (2**32),
        "output_format": output_format,
    }

    # Pass all images via image_urls array (supports 1-3+ images)
    body["image_urls"] = image_urls

    # Only set output dimensions if aspect_ratio is explicitly provided
    # (otherwise the model preserves the original image dimensions)
    if aspect_ratio and aspect_ratio in VALID_ASPECT_RATIOS:
        if model_key != "gpt":
            body["aspect_ratio"] = aspect_ratio
        else:
            body["image_size"] = _aspect_ratio_to_size(aspect_ratio)
            body["quality"] = "high"

    return body


def _submit_request(prompt, image_urls, model_key, headers, aspect_ratio=None,
                    count=1, output_format="png"):
    """Submit an edit request to the fal queue."""
    cfg = _get_model_config(model_key)
    model_id = cfg["edit"]
    submit_url = f"https://queue.fal.run/{model_id}"
    body = _build_request_body(prompt, image_urls, aspect_ratio, model_key,
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
                return status, f"Edit {status}"
        except requests.RequestException:
            pass

        time.sleep(poll_interval)

    return "TIMEOUT", f"Edit timed out after {cfg['timeout'] // 60} minutes"


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


def edit_image(
    image_path=None,
    image_url=None,
    image2_path=None,
    image2_url=None,
    image3_path=None,
    image3_url=None,
    prompt="",
    action="edit",
    model=None,
    count=None,
    aspect_ratio=None,
    output_format=None,
):
    """Edit an existing image using AI models.

    This is the primary function for all image editing operations.
    Requires at least one image input (local path or URL).
    Supports up to 3 images for multi-image scenarios (blend, face swap,
    style transfer, group photo composition).

    Args:
        image_path: Local workspace file path to the source image.
        image_url: Public HTTPS URL of the source image.
        image2_path: Local path to a second image (for blend, face swap,
            style transfer, etc.).
        image2_url: Public URL of a second image.
        image3_path: Local path to a third image (for group photos, etc.).
        image3_url: Public URL of a third image.
        prompt: Editing instruction describing the desired changes.
        action: Operation type — one of the ACTIONS keys:
            edit, blend, extend, local_edit, text_render, multi_angle,
            before_after, replace_bg, upscale, restore, colorize,
            remove_person, retouch, slim, enhance, filter,
            comparison, car_color, car_wrap.
        model: Model key — "nanopro" (default, fast ~25s) or
            "gpt" (best quality ~150s).
        count: Number of output images to generate (1-4, default 1).
            Uses fal.ai native num_images for efficient batch generation.
        aspect_ratio: Output aspect ratio (1:1, 3:4, 4:3, 9:16, 16:9).
            None = preserve original image dimensions.
        output_format: Output image format — "png" (default), "jpeg", or "webp".

    Returns:
        dict with success status, edited image paths, and metadata.
    """
    # Validate action
    if action not in ACTIONS:
        return {
            "success": False,
            "error": (
                f"Unknown action: '{action}'. "
                f"Valid actions: {', '.join(sorted(ACTIONS.keys()))}"
            ),
        }

    # Resolve source image (required)
    src_url, err = _resolve_image(image_path, image_url)
    if err:
        return {"success": False, "error": err}

    # Build image_urls list (supports 1-3 images)
    all_image_urls = [src_url]

    # Resolve optional second image
    if image2_path or image2_url:
        img2_url, err = _resolve_image(image2_path, image2_url)
        if err:
            return {"success": False, "error": f"Second image error: {err}"}
        all_image_urls.append(img2_url)

    # Resolve optional third image
    if image3_path or image3_url:
        img3_url, err = _resolve_image(image3_path, image3_url)
        if err:
            return {"success": False, "error": f"Third image error: {err}"}
        all_image_urls.append(img3_url)

    # Validate and normalize parameters
    model_key = model if model in MODELS else DEFAULT_MODEL
    count = min(max(int(count or DEFAULT_COUNT), 1), MAX_COUNT)
    fmt = output_format if output_format in VALID_OUTPUT_FORMATS else DEFAULT_OUTPUT_FORMAT

    # Validate aspect_ratio if provided
    if aspect_ratio and aspect_ratio not in VALID_ASPECT_RATIOS:
        aspect_ratio = None  # Fall back to preserving original

    # Build the editing prompt
    final_prompt = _build_edit_prompt(prompt=prompt, action=action)

    # Build a label for filenames
    label = f"edit_{action}"

    headers = caller_headers({
        'Authorization': f'Key {_get_auth_key()}',
        'Content-Type': 'application/json',
    }, tool_default='image-edit')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Submit the edit request with all images and count
    submit_data, err = _submit_request(
        final_prompt, all_image_urls, model_key, headers, aspect_ratio,
        count=count, output_format=fmt,
    )
    if err:
        return {"success": False, "error": err}

    request_id = submit_data.get('request_id')
    status_url = submit_data.get('status_url')
    result_url = submit_data.get('response_url') or submit_data.get('result_url')
    cost = submit_data.get('_cost', 0)

    print(f"Submitted: {request_id} (action={action}, model={model_key}, "
          f"images={len(all_image_urls)}, count={count}, cost=${cost:.2f})")

    # Poll for completion
    status, poll_err = _poll_until_done(status_url, request_id, model_key)
    if status != "COMPLETED":
        return {
            "success": False,
            "request_id": request_id,
            "error": poll_err,
        }

    # Fetch result
    try:
        result_resp = requests.get(
            result_url,
            headers={'Authorization': f'Key {_get_auth_key()}'},
            proxies=PROXIES, verify=False, timeout=90,
        )
        result_json = result_resp.json()
    except Exception as e:
        return {
            "success": False,
            "request_id": request_id,
            "error": f"Failed to fetch result: {e}",
        }

    # Handle fal error responses
    if result_resp.status_code != 200:
        detail = result_json.get("detail", result_resp.text[:300])
        return {
            "success": False,
            "request_id": request_id,
            "error": f"fal error ({result_resp.status_code}): {detail}",
        }

    # Extract and download images
    image_urls = _extract_image_urls(result_json)
    if not image_urls:
        detail = result_json.get("detail")
        if detail:
            err_msg = f"fal error: {detail}"
        else:
            err_msg = (
                f"No image URL found in response. "
                f"Keys: {list(result_json.keys())}"
            )
        return {
            "success": False,
            "request_id": request_id,
            "error": err_msg,
        }

    results = []
    errors = []
    for img_url in image_urls:
        try:
            local_path, size_bytes = _download_image(
                img_url, len(results), label, timestamp,
            )
            results.append({
                "url": img_url if not img_url.startswith("data:") else "(base64)",
                "local_path": local_path,
                "size_bytes": size_bytes,
                "request_id": request_id,
            })
        except Exception as e:
            errors.append({
                "request_id": request_id,
                "error": f"Download failed: {e}",
            })

    if not results:
        return {
            "success": False,
            "error": "All download attempts failed",
            "errors": errors,
        }

    return {
        "success": True,
        "model": model_key,
        "action": action,
        "prompt": final_prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": fmt,
        "input_image_count": len(all_image_urls),
        "count_requested": count,
        "count_generated": len(results),
        "total_cost": round(cost, 4),
        "images": results,
        "errors": errors if errors else None,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python edit_image.py <image_path_or_url> [prompt] [action] [model]")
        print(f"\nActions: {', '.join(sorted(ACTIONS.keys()))}")
        print(f"\nModels: {', '.join(MODELS.keys())}")
        print("\nSet FAL_KEY env var for local testing (direct fal.ai access).")
        sys.exit(1)

    img_arg = sys.argv[1]
    prompt_arg = sys.argv[2] if len(sys.argv) > 2 else ""
    action_arg = sys.argv[3] if len(sys.argv) > 3 else "edit"
    model_arg = sys.argv[4] if len(sys.argv) > 4 else "nanopro"

    if _LOCAL_MODE:
        print("Local mode: using FAL_KEY directly (no sc-proxy)")

    # Determine if input is a URL or file path
    if img_arg.startswith(("http://", "https://")):
        result = edit_image(
            image_url=img_arg,
            prompt=prompt_arg,
            action=action_arg,
            model=model_arg,
        )
    else:
        result = edit_image(
            image_path=img_arg,
            prompt=prompt_arg,
            action=action_arg,
            model=model_arg,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))
