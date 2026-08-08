#!/usr/bin/env python3
"""Video generation script - one-stop submit → poll → download

Cost tracking: this script runs as a `bash` subprocess of the agent. The
agent injects `STARCHILD_TOOL_CALLER_ID` and `STARCHILD_USER_TURN_ID` into
the subprocess env. We pass them through to sc-proxy via the SC-CALLER-ID
header (caller_headers helper) and, after each paid call, write a ledger
row (record_response helper) so the agent can fold this skill's cost into
the per-user-turn `cost_summary` SSE event and persist it under the
assistant message's `metadata.cost_summary`.

Status polls and CDN downloads return zero cost from sc-proxy, so the
helper silently no-ops on them. Only the actual submit gets billed and
recorded.
"""

import requests
import json
import time
import os
import sys
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Make _cost_track importable when this script is invoked from any CWD
# (e.g. python -c "from skills.video.generate_video import generate_video").
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from _cost_track import caller_headers, record_response  # noqa: E402

PROXY_URL = 'http://sc-proxy.internal:8080'
PROXIES = {'http': PROXY_URL, 'https': PROXY_URL}

# Seedance 2.5 uses token-based billing in sc-proxy. Keep this contract local
# so estimates shown by the skill match the proxy's pre-charge calculation.
_SEEDANCE_25_TOKEN_RATE = 0.0000214  # USD per token ($0.0214 / 1K tokens)
_SEEDANCE_25_FPS = 24
_SEEDANCE_25_PIXELS = {
    ("480p", "21:9"): (992, 432), ("480p", "16:9"): (864, 496),
    ("480p", "4:3"): (752, 560), ("480p", "1:1"): (640, 640),
    ("480p", "3:4"): (560, 752), ("480p", "9:16"): (496, 864),
    ("720p", "21:9"): (1470, 630), ("720p", "16:9"): (1280, 720),
    ("720p", "4:3"): (1112, 834), ("720p", "1:1"): (960, 960),
    ("720p", "3:4"): (834, 1112), ("720p", "9:16"): (720, 1280),
}
_SEEDANCE_25_RESOLUTIONS = ("480p", "720p")
_SEEDANCE_25_ASPECT_RATIOS = ("21:9", "16:9", "4:3", "1:1", "3:4", "9:16")

def generate_video(prompt, model="alibaba/happy-horse/text-to-video", duration=5, resolution="720p", image_url=None, image_urls=None, aspect_ratio="16:9"):
    """Generate video end-to-end. Returns dict with success/error/paths.

    image_url:  single public HTTP(S) URL → image-to-video models.
    image_urls: list of 1-9 public HTTP(S) URLs → reference-to-video
                models. MiniMax H3 uses `reference_image_urls`; other
                registered reference-to-video models use `image_urls`.
    """

    headers = caller_headers({
        'Authorization': 'Key fake-falai-key-12345',
        'Content-Type': 'application/json',
    }, tool_default='video')

    if model.startswith('bytedance/seedance-2.5/'):
        if not isinstance(duration, int) or isinstance(duration, bool) or not (4 <= duration <= 30):
            return {"success": False, "error": "Seedance 2.5 requires an integer duration from 4 to 30 seconds; duration=auto is not priceable."}
        if resolution not in _SEEDANCE_25_RESOLUTIONS:
            return {"success": False, "error": f"Seedance 2.5 only supports resolution 480p or 720p (got {resolution!r})."}
        if aspect_ratio not in _SEEDANCE_25_ASPECT_RATIOS:
            return {"success": False, "error": f"Seedance 2.5 only supports aspect_ratio {', '.join(_SEEDANCE_25_ASPECT_RATIOS)} (got {aspect_ratio!r})."}

    body = {'prompt': prompt, 'duration': duration, 'aspect_ratio': aspect_ratio}
    if ('happy-horse' in model or 'kling' in model or 'seedance-2.0/mini' in model
            or 'seedance-2.5' in model or 'grok-imagine-video' in model):
        # Grok v1.5: proxy rejects (400) any resolution without a published
        # price — fail fast here instead of burning a pointless proxy request.
        if 'grok-imagine-video' in model and resolution not in ("480p", "720p"):
            return {"success": False, "error": f"grok-imagine-video v1.5 only supports resolution 480p or 720p (no published price for '{resolution}'; the proxy rejects it)."}
        body['resolution'] = resolution

    # Seedance 2.0 Mini has a strict duration schema: it requires a STRING
    # ('4', '5', '6', ... '15', 'auto'), NOT an int and NOT '5s'. Other
    # Seedance variants accept int or '5s'. Sending int 5 or '5s' to mini
    # returns HTTP 422 literal_error. Encode the format per-model.
    # Verified against fal upstream 2026-06-29.
    if 'seedance-2.0/mini' in model:
        body['duration'] = str(duration)
    
    # Handle image input — must be a public https URL.
    # Recommended: publish via skills/video/publish_asset.py + community preview slug `fal-assets`.
    if image_url:
        if image_url.startswith('data:') or not image_url.startswith(('http://', 'https://')):
            return {"success": False, "error": "image_url must be a public HTTP(S) URL. Use publish_asset.py + fal-assets preview to expose local files."}
        if not model.endswith('/image-to-video'):
            model = model.replace('/text-to-video', '/image-to-video')
        body['image_url'] = image_url

    # Reference-to-video endpoints accept 1-9 public HTTP(S) URLs. MiniMax H3
    # uses fal's distinct `reference_image_urls` field; other registered r2v
    # endpoints use `image_urls`.
    if image_urls is not None:
        if 'reference-to-video' not in model:
            return {"success": False, "error": "image_urls is only supported by reference-to-video models."}
        if not isinstance(image_urls, (list, tuple)) or not (1 <= len(image_urls) <= 9):
            return {"success": False, "error": "image_urls must be a list of 1-9 public HTTP(S) URLs."}
        for u in image_urls:
            if not isinstance(u, str) or u.startswith('data:') or not u.startswith(('http://', 'https://')):
                return {"success": False, "error": f"Invalid reference image URL (must be public HTTP(S), no data: URIs): {str(u)[:80]}"}
        body.pop('image_url', None)
        body['reference_image_urls' if 'minimax_h3' in model else 'image_urls'] = list(image_urls)
    elif 'reference-to-video' in model:
        return {"success": False, "error": "reference-to-video models require image_urls (list of 1-9 public HTTP(S) URLs)."}
    
    # Submit
    submit_url = f'https://queue.fal.run/{model}'
    response = requests.post(submit_url, headers=headers, json=body, proxies=PROXIES, verify=False, timeout=90)
    # Record the paid submit call to the cost ledger so the agent's
    # per-turn cost_summary picks up this video's cost (no-op if 0).
    record_response(response, request_url=submit_url, request_payload=body)

    if response.status_code != 200:
        return {"success": False, "error": f"Submit failed: {response.status_code} - {response.text[:200]}"}
    
    data = response.json()
    request_id = data['request_id']
    status_url = data['status_url']
    result_url = data.get('response_url', data.get('result_url'))
    cost = float(response.headers.get('X-Credits-Used', 0))
    
    print(f"✅ Submitted: {request_id}, cost=${cost:.2f}")
    
    # Poll
    deadline = time.time() + 900  # 15min timeout
    poll_count = 0
    while time.time() < deadline:
        poll_count += 1
        poll_resp = requests.get(status_url, headers={'Authorization': 'Key fake-falai-key-12345'}, proxies=PROXIES, verify=False, timeout=60)
        status = poll_resp.json().get('status')
        
        if status == 'COMPLETED':
            break
        elif status in ('FAILED', 'CANCELLED'):
            return {"success": False, "request_id": request_id, "cost": cost, "error": f"Generation {status}"}
        
        time.sleep(5)
    else:
        return {"success": False, "request_id": request_id, "cost": cost, "error": "Timeout"}
    
    # Get result & download
    result_resp = requests.get(result_url, headers={'Authorization': 'Key fake-falai-key-12345'}, proxies=PROXIES, verify=False, timeout=90)
    try:
        result_json = result_resp.json()
    except Exception:
        return {"success": False, "request_id": request_id, "cost": cost,
                "error": f"Result endpoint returned non-JSON (HTTP {result_resp.status_code}): {result_resp.text[:200]}",
                "polls": poll_count}

    # fal model response shapes vary. Try known shapes; if none match,
    # surface the actual top-level keys so the caller can see why parsing
    # failed (instead of a raw KeyError 200 lines deep).
    video_url = _extract_video_url(result_json)
    if not video_url:
        return {"success": False, "request_id": request_id, "cost": cost,
                "error": (f"Could not locate video URL in fal response. "
                          f"Top-level keys: {list(result_json.keys())}. "
                          f"Sample: {str(result_json)[:300]}"),
                "polls": poll_count}
    
    os.makedirs('output/videos', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_short = model.split('/')[-1]
    local_path = f"output/videos/{timestamp}_{model_short}_{duration}s_{resolution}.mp4"
    
    video_data = requests.get(video_url, timeout=120).content
    open(local_path, 'wb').write(video_data)
    
    return {
        "success": True,
        "request_id": request_id,
        "cost": cost,
        "video_url": video_url,
        "local_path": local_path,
        "file_size_mb": len(video_data) / 1024 / 1024
    }

def _extract_video_url(result_json):
    """Recover the video URL from fal's response across model variants.

    Known shapes (as of 2026-05):
      - happy-horse / kling / seedance:   {"video":  {"url": "..."}}
      - wan / some pipelines:             {"videos": [{"url": "..."}]}
      - some upscale/pipeline outputs:    {"output": [{"url": "..."}]}
      - voiceover/audio variants:         {"output_video": {"url": "..."}}

    Returns the URL string, or None if no recognised shape matches.
    """
    if not isinstance(result_json, dict):
        return None

    # Single-video object shapes
    for key in ("video", "output_video"):
        node = result_json.get(key)
        if isinstance(node, dict) and isinstance(node.get("url"), str):
            return node["url"]
        if isinstance(node, str) and node.startswith("http"):
            return node

    # Array shapes
    for key in ("videos", "output", "outputs"):
        arr = result_json.get(key)
        if isinstance(arr, list) and arr:
            first = arr[0]
            if isinstance(first, dict) and isinstance(first.get("url"), str):
                return first["url"]
            if isinstance(first, str) and first.startswith("http"):
                return first

    # Last resort: anything in top-level that looks like {"url": "...mp4"}
    for v in result_json.values():
        if isinstance(v, dict) and isinstance(v.get("url"), str) and ".mp4" in v["url"]:
            return v["url"]
    return None


def estimate_cost(model, duration, resolution="720p", aspect_ratio="16:9"):
    """Estimate generation cost in USD using the proxy's pricing contract."""
    if model.startswith('bytedance/seedance-2.5/'):
        if not isinstance(duration, int) or isinstance(duration, bool) or not (4 <= duration <= 30):
            raise ValueError("Seedance 2.5 requires an integer duration from 4 to 30 seconds; duration=auto is not priceable.")
        if resolution not in _SEEDANCE_25_RESOLUTIONS:
            raise ValueError(f"Seedance 2.5 only supports resolution 480p or 720p (got {resolution!r}).")
        dims = _SEEDANCE_25_PIXELS.get((resolution, aspect_ratio))
        if dims is None:
            raise ValueError(f"Seedance 2.5 does not support resolution/aspect_ratio={resolution!r}/{aspect_ratio!r}.")
        width, height = dims
        tokens = (width * height * float(duration) * _SEEDANCE_25_FPS) / 1024
        return round(tokens * _SEEDANCE_25_TOKEN_RATE, 4)
    prices = {
        "alibaba/happy-horse/text-to-video": 0.14,
        "fal-ai/wan/v2.5/text-to-video": 0.05,
        "fal-ai/kling-video/v2.6/pro/text-to-video": 0.07,
        "bytedance/seedance-2.0/fast/text-to-video": 0.2419,
        # Seedance 2.0 Mini — resolution-tiered. Base price below is 720p;
        # 480p is cheaper. No 1080p tier exists for mini.
        "bytedance/seedance-2.0/mini/text-to-video": 0.1547,  # 720p
        "fal-ai/hunyuanvideo": 0.40,  # flat rate
        # Grok Imagine Video v1.5 (image-to-video ONLY, requires image_url).
        # 480p $0.08/s, 720p $0.14/s + flat $0.01 per input image.
        "xai/grok-imagine-video/v1.5/image-to-video": 0.14,  # 720p base
        # Kling v3 Turbo / 4K — flat per-second, audio-independent.
        "fal-ai/kling-video/v3/turbo/standard/text-to-video": 0.112,
        "fal-ai/kling-video/v3/turbo/standard/image-to-video": 0.112,
        "fal-ai/kling-video/v3/turbo/pro/text-to-video": 0.14,
        "fal-ai/kling-video/v3/turbo/pro/image-to-video": 0.14,
        "fal-ai/kling-video/v3/4k/text-to-video": 0.42,
        "fal-ai/kling-video/v3/4k/image-to-video": 0.42,
        # Happy Horse v1.1 — own 1080p tier $0.18/s (NOT the v1.0 2x rule).
        "alibaba/happy-horse/v1.1/text-to-video": 0.14,
        "alibaba/happy-horse/v1.1/image-to-video": 0.14,
        "alibaba/happy-horse/v1.1/reference-to-video": 0.14,
    }

    if model == "fal-ai/hunyuanvideo":
        return 0.40

    unit_price = prices.get(model, 0.10)  # default fallback
    if 'happy-horse/v1.1' in model and resolution == "1080p":
        unit_price = 0.18  # v1.1 has its own 1080p tier, NOT the v1.0 2x rule
    elif 'happy-horse' in model and resolution == "1080p":
        unit_price *= 2
    # Grok Imagine v1.5: 480p discount tier + flat $0.01 per input image.
    # Only 480p/720p have published prices; anything else (e.g. 1080p,
    # schema-valid upstream) is rejected 400 by the proxy — refuse to quote
    # a price the proxy will never accept.
    if 'grok-imagine-video' in model:
        if resolution not in ("480p", "720p"):
            raise ValueError(
                f"grok-imagine-video v1.5: resolution '{resolution}' has no "
                "published price and is rejected by the proxy. Use 480p or 720p."
            )
        if resolution == "480p":
            unit_price = 0.08
        return round(unit_price * duration + 0.01, 4)
    # Seedance Mini 480p discount tier (720p is the base price above).
    if 'seedance-2.0/mini' in model and resolution == "480p":
        unit_price = 0.0721

    return round(unit_price * duration, 4)

# NOTE 2026-05-11: 'fal-ai/wan/v2.5/text-to-video' was removed from the
# fal proxy allowlist (returns 404). Until a cheap replacement is curated,
# 'budget' falls back to happy-horse (same as 'balanced'). Cost is still
# ~$0.14/s instead of $0.05/s — budget tier is effectively unavailable.
QUICK_MODELS = {
    "budget": "alibaba/happy-horse/text-to-video",
    "balanced": "alibaba/happy-horse/text-to-video",
    "premium": "bytedance/seedance-2.0/fast/text-to-video",
    "premium-25": "bytedance/seedance-2.5/text-to-video",
    "mini": "bytedance/seedance-2.0/mini/text-to-video",  # 480p $0.0721/s, 720p $0.1547/s
}

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python generate_video.py 'prompt' [model|tier] [duration]")
        print("Tiers: budget, balanced, premium")
        sys.exit(1)
    
    prompt = sys.argv[1]
    model_or_tier = sys.argv[2] if len(sys.argv) > 2 else "balanced"
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    model = QUICK_MODELS.get(model_or_tier, model_or_tier)
    print(f"Model: {model}, Est cost: ${estimate_cost(model, duration)}")
    
    result = generate_video(prompt, model, duration)
    print(json.dumps(result, indent=2))