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

def generate_video(prompt, model="alibaba/happy-horse/text-to-video", duration=5, resolution="720p", image_url=None):
    """Generate video end-to-end. Returns dict with success/error/paths."""

    headers = caller_headers({
        'Authorization': 'Key fake-falai-key-12345',
        'Content-Type': 'application/json',
    }, tool_default='video')

    body = {'prompt': prompt, 'duration': duration, 'aspect_ratio': "16:9"}
    if 'happy-horse' in model or 'kling' in model:
        body['resolution'] = resolution
    
    # Handle image input — must be a public https URL.
    # Recommended: publish via skills/video/publish_asset.py + community preview slug `fal-assets`.
    if image_url:
        if image_url.startswith('data:') or not image_url.startswith(('http://', 'https://')):
            return {"success": False, "error": "image_url must be a public HTTP(S) URL. Use publish_asset.py + fal-assets preview to expose local files."}
        if not model.endswith('/image-to-video'):
            model = model.replace('/text-to-video', '/image-to-video')
        body['image_url'] = image_url
    
    # Submit
    submit_url = f'https://queue.fal.run/{model}'
response = requests.post(submit_url, headers=headers, json=body, proxies=PROXIES, verify=True, timeout=90)
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
    while time.time() < deadline:
poll_resp = requests.get(status_url, headers={'Authorization': 'Key fake-falai-key-12345'}, proxies=PROXIES, verify=Fals
        status = poll_resp.json().get('status')
        
        if status == 'COMPLETED':
            break
        elif status in ('FAILED', 'CANCELLED'):
            return {"success": False, "request_id": request_id, "cost": cost, "error": f"Generation {status}"}
        
        time.sleep(5)
    else:
        return {"success": False, "request_id": request_id, "cost": cost, "error": "Timeout"}
    
    # Get result & download
result_resp = requests.get(result_url, headers={'Authorization': 'Key fake-falai-key-12345'}, proxies=PROXIES, verify=Fa
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


def estimate_cost(model, duration, resolution="720p"):
    """Estimate generation cost in USD"""
    prices = {
        "alibaba/happy-horse/text-to-video": 0.14,
        "fal-ai/wan/v2.5/text-to-video": 0.05,
        "fal-ai/kling-video/v2.6/pro/text-to-video": 0.07,
        "bytedance/seedance-2.0/fast/text-to-video": 0.2419,
        "fal-ai/hunyuanvideo": 0.40,  # flat rate
    }
    
    if model == "fal-ai/hunyuanvideo":
        return 0.40
    
    unit_price = prices.get(model, 0.10)  # default fallback
    if 'happy-horse' in model and resolution == "1080p":
        unit_price *= 2
    
    return round(unit_price * duration, 4)

# NOTE 2026-05-11: 'fal-ai/wan/v2.5/text-to-video' was removed from the
# fal proxy allowlist (returns 404). Until a cheap replacement is curated,
# 'budget' falls back to happy-horse (same as 'balanced'). Cost is still
# ~$0.14/s instead of $0.05/s — budget tier is effectively unavailable.
QUICK_MODELS = {
    "budget": "alibaba/happy-horse/text-to-video",
    "balanced": "alibaba/happy-horse/text-to-video",
    "premium": "bytedance/seedance-2.0/fast/text-to-video"
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