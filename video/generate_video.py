#!/usr/bin/env python3
"""Video generation script - one-stop submit → poll → download"""

import requests
import json
import time
import os
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXY_URL = 'http://sc-proxy.internal:8080'
PROXIES = {'http': PROXY_URL, 'https': PROXY_URL}

def generate_video(prompt, model="alibaba/happy-horse/text-to-video", duration=5, resolution="720p", image_url=None):
    """Generate video end-to-end. Returns dict with success/error/paths."""
    
    caller_id = f"video:{int(time.time())}"
    headers = {
        'Authorization': 'Key fake-falai-key-12345',
        'Content-Type': 'application/json',
        'SC-CALLER-ID': caller_id
    }
    
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
    response = requests.post(submit_url, headers=headers, json=body, proxies=PROXIES, verify=False, timeout=90)
    
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
    video_url = result_resp.json()['video']['url']
    
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

QUICK_MODELS = {
    "budget": "fal-ai/wan/v2.5/text-to-video",
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