#!/usr/bin/env python3
"""Virtual try-on script — visualize clothing, accessories, hairstyles, and more on a person.

Supports three models:
  - nano2    (fal-ai/gemini-3.1-flash-image-preview/edit)     — fastest ~15s, good for drafts
  - nanopro  (fal-ai/gemini-3-pro-image-preview/edit)   — balanced ~25s, good quality (default)
  - gpt      (openai/gpt-image-2/edit)       — best quality, slow ~150s

Requires two images:
  - Person photo (the subject to dress/style)
  - Garment/item photo (the clothing, accessory, or style reference)

Both images are base64-encoded as data URIs and sent via the /edit endpoint.

Flow: resolve both images → build category prompt → submit to fal queue → poll → download.

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

# ── Category definitions ──────────────────────────────────────────────
CATEGORIES = {
    "clothing":  "Clothing try-on — shirts, dresses, jackets, pants, coats, full outfits",
    "accessory": "Accessory try-on — scarves, bags, belts, jewelry, necklaces, earrings",
    "hairstyle": "Hairstyle preview — haircuts, hair colors, styling changes",
    "makeup":    "Makeup preview — lipstick, eyeshadow, foundation, blush, full looks",
    "glasses":   "Eyewear try-on — prescription glasses, sunglasses, reading glasses",
    "hat":       "Hat try-on — caps, beanies, fedoras, sun hats, helmets",
    "shoes":     "Shoes try-on — sneakers, heels, boots, sandals, loafers",
    "watch":     "Watch try-on — analog watches, smartwatches, luxury watches, bracelets",
}

# ── Category prompt templates ─────────────────────────────────────────
# Each template instructs the model to combine the person image with the
# garment/item image for a realistic virtual try-on result.

CATEGORY_PROMPTS = {
    "clothing": (
        "The person in the first image is wearing the clothing from the second image. "
        "Keep the person's face, body shape, and pose exactly the same. "
        "Only change the outfit to match the garment shown in the second image. "
        "Natural fit, proper draping, realistic wrinkles and shadows. "
        "The clothing should follow the body contours naturally. "
        "Maintain the original background and lighting."
    ),
    "accessory": (
        "The person in the first image is wearing the accessory from the second image. "
        "Keep everything about the person the same — face, body, pose, clothing. "
        "Add the accessory naturally with proper positioning, scale, and perspective. "
        "Ensure realistic shadows and reflections where the accessory meets the body. "
        "The accessory should look like it belongs in the original photo."
    ),
    "hairstyle": (
        "Apply the hairstyle from the second image to the person in the first image. "
        "Keep the person's face, facial features, skin tone, and expression exactly the same. "
        "Only change the hair — style, length, volume, and color should match the reference. "
        "Ensure natural hairline transition and realistic hair texture. "
        "The hairstyle should suit the person's face shape and look natural."
    ),
    "makeup": (
        "Apply the makeup style from the second image to the person in the first image. "
        "Keep the person's facial features, face shape, and expression the same. "
        "Apply similar makeup colors, techniques, and intensity — including foundation, "
        "eye makeup, lip color, blush, and contouring as shown in the reference. "
        "The makeup should look professionally applied and natural on the person's skin tone."
    ),
    "glasses": (
        "The person in the first image is wearing the glasses from the second image. "
        "Keep everything about the person the same — face, expression, hair, clothing. "
        "Only add the glasses with proper fit and positioning on the face. "
        "The glasses should sit naturally on the nose bridge and ears. "
        "Add realistic lens reflections and shadows. "
        "Ensure the frame size is proportional to the person's face."
    ),
    "hat": (
        "The person in the first image is wearing the hat from the second image. "
        "Keep everything about the person the same — face, expression, clothing. "
        "Only add the hat with natural positioning on the head. "
        "The hat should sit at the correct angle and depth. "
        "Adjust hair visibility naturally around the hat. "
        "Add realistic shadows cast by the hat on the face and shoulders."
    ),
    "shoes": (
        "The person in the first image is wearing the shoes from the second image. "
        "Show a full-body or lower-body view with the new shoes naturally fitted. "
        "Keep the person's body, pose, and clothing exactly the same. "
        "Only change the footwear to match the shoes in the reference. "
        "Ensure proper scale, perspective, and ground contact. "
        "Add realistic shadows beneath the shoes."
    ),
    "watch": (
        "The person in the first image is wearing the watch from the second image. "
        "Keep everything about the person the same — face, body, clothing. "
        "Only add the watch on the wrist with proper fit and positioning. "
        "The watch should wrap naturally around the wrist with correct proportions. "
        "Show realistic metal/leather reflections and shadows. "
        "Ensure the watch face is visible and properly oriented."
    ),
}

# ── Constants ─────────────────────────────────────────────────────────
MAX_COUNT = 4  # fal.ai API supports up to 4 images per call
DEFAULT_COUNT = 1
VALID_ASPECT_RATIOS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
}
DEFAULT_ASPECT_RATIO = "3:4"  # Portrait orientation for try-on
VALID_OUTPUT_FORMATS = {"jpeg", "png", "webp"}
DEFAULT_OUTPUT_FORMAT = "png"
OUTPUT_DIR = "output/images"


def _get_auth_key():
    """Return the appropriate fal API key."""
    return _FAL_KEY if _LOCAL_MODE else 'fake-falai-key-12345'


def _get_model_config(model_key):
    """Return model config dict for the given key."""
    return MODELS.get(model_key, MODELS[DEFAULT_MODEL])


def _resolve_image(image_path=None, image_url=None, label="image"):
    """Resolve an image input to a URL for the fal API.

    Accepts either a local file path or a public URL.
    Local files are base64-encoded as data URIs.

    Returns (url_string, error_string).
    """
    if not image_path and not image_url:
        return None, f"Either {label}_path or {label}_url must be provided."

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
            f"{label}_url must be a public HTTP(S) URL. "
            "For local files, use the path parameter instead."
        )
    return image_url, None


def _build_tryon_prompt(prompt=None, category="clothing"):
    """Construct the try-on prompt from category template and optional override.

    Priority:
      1. prompt provided → use as-is (full override)
      2. no prompt → use category default prompt

    Returns the final prompt string.
    """
    if prompt:
        return prompt
    return CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["clothing"])


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
    return mapping.get(aspect_ratio, mapping["3:4"])


def _build_request_body(prompt, person_url, garment_url, aspect_ratio="3:4",
                        model_key="nanopro", count=1, output_format="png"):
    """Build the request body for the fal edit API with two images.

    Both images are passed via the image_urls array. The person image is
    the primary image, and the garment image is the style reference.
    """
    body = {
        "prompt": prompt,
        "num_images": count,
        "seed": int(time.time() * 1000) % (2**32),
        "output_format": output_format,
    }

    # Both images passed via image_urls array
    body["image_urls"] = [person_url, garment_url]

    # nano2/nanopro use aspect_ratio string; gpt uses image_size object
    if aspect_ratio and aspect_ratio in VALID_ASPECT_RATIOS:
        if model_key != "gpt":
            body["aspect_ratio"] = aspect_ratio
        else:
            body["image_size"] = _aspect_ratio_to_size(aspect_ratio)
            body["quality"] = "high"

    return body


def _submit_request(prompt, person_url, garment_url, model_key, headers,
                    aspect_ratio="3:4", count=1, output_format="png"):
    """Submit a try-on request to the fal queue."""
    cfg = _get_model_config(model_key)
    model_id = cfg["edit"]
    submit_url = f"https://queue.fal.run/{model_id}"
    body = _build_request_body(prompt, person_url, garment_url, aspect_ratio,
                               model_key, count=count, output_format=output_format)

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
                return status, f"Try-on {status}"
        except requests.RequestException:
            pass

        time.sleep(poll_interval)

    return "TIMEOUT", f"Try-on timed out after {cfg['timeout'] // 60} minutes"


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


def try_on(
    person_path=None,
    person_url=None,
    garment_path=None,
    garment_url=None,
    category="clothing",
    prompt=None,
    model="nanopro",
    count=None,
    aspect_ratio="3:4",
    output_format=None,
):
    """Virtual try-on — visualize an item on a person.

    Requires two images: a person photo and a garment/item photo.
    The model composites the item onto the person realistically.

    Args:
        person_path: Local workspace file path to the person's photo.
        person_url: Public HTTPS URL of the person's photo.
        garment_path: Local workspace file path to the garment/item photo.
        garment_url: Public HTTPS URL of the garment/item photo.
        category: Try-on category — one of:
            clothing, accessory, hairstyle, makeup, glasses, hat, shoes, watch.
        prompt: Custom prompt — overrides the category default when set.
        model: Model key — "nanopro" (default, fast ~25s) or
            "gpt" (best quality ~150s).
        count: Number of output images to generate (1-4, default 1).
            Uses fal.ai native num_images for efficient batch generation.
        aspect_ratio: Output aspect ratio (1:1, 3:4, 4:3, 9:16, 16:9).
            Default "3:4" (portrait orientation).
        output_format: Output image format — "png" (default), "jpeg", or "webp".

    Returns:
        dict with success status, try-on result image paths, and metadata.
    """
    # Validate category
    if category not in CATEGORIES:
        return {
            "success": False,
            "error": (
                f"Unknown category: '{category}'. "
                f"Valid categories: {', '.join(sorted(CATEGORIES.keys()))}"
            ),
        }

    # Resolve person image
    person_resolved, err = _resolve_image(person_path, person_url, label="person")
    if err:
        return {"success": False, "error": f"Person image error: {err}"}

    # Resolve garment/item image
    garment_resolved, err = _resolve_image(garment_path, garment_url, label="garment")
    if err:
        return {"success": False, "error": f"Garment/item image error: {err}"}

    # Validate and normalize parameters
    model_key = model if model in MODELS else DEFAULT_MODEL
    count = min(max(int(count or DEFAULT_COUNT), 1), MAX_COUNT)
    fmt = output_format if output_format in VALID_OUTPUT_FORMATS else DEFAULT_OUTPUT_FORMAT

    if aspect_ratio and aspect_ratio not in VALID_ASPECT_RATIOS:
        aspect_ratio = DEFAULT_ASPECT_RATIO

    # Build the try-on prompt
    final_prompt = _build_tryon_prompt(prompt=prompt, category=category)

    # Build a label for filenames
    label = f"tryon_{category}"

    headers = caller_headers({
        'Authorization': f'Key {_get_auth_key()}',
        'Content-Type': 'application/json',
    }, tool_default='image-tryon')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Submit the try-on request
    submit_data, err = _submit_request(
        final_prompt, person_resolved, garment_resolved,
        model_key, headers, aspect_ratio,
        count=count, output_format=fmt,
    )
    if err:
        return {"success": False, "error": err}

    request_id = submit_data.get('request_id')
    status_url = submit_data.get('status_url')
    result_url = submit_data.get('response_url') or submit_data.get('result_url')
    cost = submit_data.get('_cost', 0)

    print(f"Submitted: {request_id} (category={category}, model={model_key}, "
          f"count={count}, cost=${cost:.2f})")

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
        "category": category,
        "prompt": final_prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": fmt,
        "count_requested": count,
        "count_generated": len(results),
        "total_cost": round(cost, 4),
        "images": results,
        "errors": errors if errors else None,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python try_on.py <person_image> <garment_image> [category] [model]")
        print(f"\nCategories: {', '.join(sorted(CATEGORIES.keys()))}")
        print(f"\nModels: {', '.join(MODELS.keys())}")
        print("\nSet FAL_KEY env var for local testing (direct fal.ai access).")
        sys.exit(1)

    person_arg = sys.argv[1]
    garment_arg = sys.argv[2]
    category_arg = sys.argv[3] if len(sys.argv) > 3 else "clothing"
    model_arg = sys.argv[4] if len(sys.argv) > 4 else "nanopro"

    if _LOCAL_MODE:
        print("Local mode: using FAL_KEY directly (no sc-proxy)")

    # Determine if inputs are URLs or file paths
    person_kw = {}
    if person_arg.startswith(("http://", "https://")):
        person_kw["person_url"] = person_arg
    else:
        person_kw["person_path"] = person_arg

    garment_kw = {}
    if garment_arg.startswith(("http://", "https://")):
        garment_kw["garment_url"] = garment_arg
    else:
        garment_kw["garment_path"] = garment_arg

    result = try_on(
        **person_kw,
        **garment_kw,
        category=category_arg,
        model=model_arg,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
