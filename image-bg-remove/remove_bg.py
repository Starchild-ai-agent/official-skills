#!/usr/bin/env python3
"""Background removal script — remove backgrounds using Bria RMBG 2.0.

Uses the dedicated model: fal-ai/bria/background/remove
  - No prompt needed — pure tool, just input an image
  - Outputs transparent PNG
  - Fast (~3s) and cheap ($0.01/call)

Flow: resolve image → submit to fal queue → poll → download transparent PNG.

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
# This skill uses a single dedicated model — no model selection needed.
MODEL_ID = "fal-ai/bria/background/remove"
TIMEOUT = 120       # 2 min (usually completes in ~3s)
POLL_INTERVAL = 2   # seconds between polls

# Supported image extensions for local file validation
SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

# Output directory
OUTPUT_DIR = "output/images"


def _get_auth_key():
    """Get the fal.ai auth key from env or return empty for sc-proxy."""
    return _FAL_KEY or ""


def _resolve_image(image_path=None, image_url=None):
    """Resolve image input to a URL or data URI.

    Returns (url_or_data_uri, error_string).
    Exactly one of the two must be non-None.
    """
    if not image_path and not image_url:
        return None, "Either image_path or image_url must be provided."

    # Local file input
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


def _submit_request(image_url, headers):
    """Submit a background removal request to the fal queue.

    The Bria RMBG 2.0 model only needs an image_url — no prompt.
    """
    submit_url = f"https://queue.fal.run/{MODEL_ID}"
    body = {
        "image_url": image_url,
    }

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


def _poll_until_done(status_url, request_id):
    """Poll the fal queue until the request completes or fails."""
    headers = {'Authorization': f'Key {_get_auth_key()}'}
    deadline = time.time() + TIMEOUT

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
                return status, f"Background removal {status}"
        except requests.RequestException:
            pass

        time.sleep(POLL_INTERVAL)

    return "TIMEOUT", f"Background removal timed out after {TIMEOUT // 60} minutes"


def _extract_image_url(result_json):
    """Extract the output image URL from fal response.

    The Bria RMBG 2.0 model returns:
      {"image": {"url": "https://..."}}
    """
    if not isinstance(result_json, dict):
        return None

    # Primary: {"image": {"url": "..."}}
    image_node = result_json.get("image")
    if isinstance(image_node, dict) and isinstance(image_node.get("url"), str):
        return image_node["url"]

    # Fallback: check other common response shapes
    for key in ("images", "output", "outputs", "data"):
        arr = result_json.get(key)
        if isinstance(arr, list):
            for item in arr:
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    return item["url"]
                elif isinstance(item, str) and item.startswith("http"):
                    return item

    # Fallback: {"output_image": {"url": "..."}}
    for key in ("output_image", "result"):
        node = result_json.get(key)
        if isinstance(node, dict) and isinstance(node.get("url"), str):
            return node["url"]
        elif isinstance(node, str) and node.startswith("http"):
            return node

    return None


def _download_image(url, timestamp):
    """Download the transparent PNG result to the output directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Background removal always outputs PNG (transparent)
    filename = f"{timestamp}_bg_removed.png"
    local_path = os.path.join(OUTPUT_DIR, filename)

    if url.startswith("data:"):
        b64_data = url.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_data)
        with open(local_path, 'wb') as f:
            f.write(img_bytes)
        return local_path, len(img_bytes)

    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    with open(local_path, 'wb') as f:
        f.write(resp.content)

    return local_path, len(resp.content)


def remove_bg(
    image_path=None,
    image_url=None,
    output_path=None,
):
    """Remove the background from an image using Bria RMBG 2.0.

    This is a pure tool — no prompt needed. Just provide an image and
    get back a transparent PNG.

    Args:
        image_path: Local workspace file path to the source image.
        image_url: Public HTTPS URL of the source image.
        output_path: Custom output file path (optional). If not provided,
            saves to output/images/ with a timestamped filename.

    Returns:
        dict with:
        {
            "success": True,
            "image": {"url": "...", "local_path": "output/images/..."},
            "cost": 0.01,
            "duration_s": 3.2,
        }
    """
    start_time = time.time()

    # Resolve source image
    src_url, err = _resolve_image(image_path, image_url)
    if err:
        return {"success": False, "error": err}

    # Build headers with cost tracking
    headers = caller_headers({
        'Authorization': f'Key {_get_auth_key()}',
        'Content-Type': 'application/json',
    }, tool_default='image-bg-remove')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Submit the background removal request
    submit_data, err = _submit_request(src_url, headers)
    if err:
        return {"success": False, "error": err}

    request_id = submit_data.get('request_id')
    status_url = submit_data.get('status_url')
    result_url = submit_data.get('response_url') or submit_data.get('result_url')
    cost = submit_data.get('_cost', 0)

    print(f"Submitted: {request_id} (model={MODEL_ID}, cost=${cost:.2f})")

    # Poll for completion
    status, poll_err = _poll_until_done(status_url, request_id)
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

    # Extract image URL
    img_url = _extract_image_url(result_json)
    if not img_url:
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

    # Download the transparent PNG
    try:
        if output_path:
            # Custom output path
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            if img_url.startswith("data:"):
                b64_data = img_url.split(",", 1)[1]
                img_bytes = base64.b64decode(b64_data)
                with open(output_path, 'wb') as f:
                    f.write(img_bytes)
                local_path = output_path
                size_bytes = len(img_bytes)
            else:
                resp = requests.get(img_url, timeout=120)
                resp.raise_for_status()
                with open(output_path, 'wb') as f:
                    f.write(resp.content)
                local_path = output_path
                size_bytes = len(resp.content)
        else:
            local_path, size_bytes = _download_image(img_url, timestamp)
    except Exception as e:
        return {
            "success": False,
            "request_id": request_id,
            "error": f"Download failed: {e}",
        }

    duration_s = round(time.time() - start_time, 1)

    return {
        "success": True,
        "image": {
            "url": img_url if not img_url.startswith("data:") else "(base64)",
            "local_path": local_path,
            "size_bytes": size_bytes,
            "request_id": request_id,
        },
        "cost": round(cost, 4),
        "duration_s": duration_s,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remove_bg.py <image_path_or_url> [output_path]")
        print("\nModel: fal-ai/bria/background/remove (Bria RMBG 2.0)")
        print("Output: transparent PNG with background removed")
        print("\nSet FAL_KEY env var for local testing (direct fal.ai access).")
        sys.exit(1)

    img_arg = sys.argv[1]
    out_arg = sys.argv[2] if len(sys.argv) > 2 else None

    if _LOCAL_MODE:
        print("Local mode: using FAL_KEY directly (no sc-proxy)")

    # Determine if input is a URL or file path
    if img_arg.startswith(("http://", "https://")):
        result = remove_bg(image_url=img_arg, output_path=out_arg)
    else:
        result = remove_bg(image_path=img_arg, output_path=out_arg)

    print(json.dumps(result, indent=2, ensure_ascii=False))
