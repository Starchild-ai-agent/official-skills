#!/usr/bin/env python3
"""Poll existing video by request_id

Cost tracking: status polls and result fetches return zero cost from
sc-proxy (they're free for already-submitted jobs), so the
record_response helper silently no-ops here. We still attach SC-CALLER-ID
via caller_headers so any future billing change is correctly attributed.
"""

import requests
import time
import os
import sys
from datetime import datetime
import urllib3
urllib3.disable_warnings()

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from _cost_track import caller_headers, record_response  # noqa: E402


def poll_video(request_id, download=True):
    """Poll video status and download if completed"""

    # Try common URL patterns
    patterns = [
        f"https://queue.fal.run/requests/{request_id}",
        f"https://queue.fal.run/alibaba/happy-horse/requests/{request_id}",
    ]

    headers = caller_headers({'Authorization': 'Key fake-falai-key-12345'}, tool_default='video')
    proxies = {'http': 'http://sc-proxy.internal:8080', 'https': 'http://sc-proxy.internal:8080'}
    
    status_url = None
    for pattern in patterns:
        try:
            test_resp = requests.get(f"{pattern}/status", headers=headers, proxies=proxies, verify=False, timeout=10)
            if test_resp.status_code == 200:
                status_url = f"{pattern}/status"
                result_url = pattern
                break
        except:
            continue
    
    if not status_url:
        return {"success": False, "error": f"Invalid request_id: {request_id}"}
    
    # Poll until complete
    for _ in range(180):  # 15min max
        resp = requests.get(status_url, headers=headers, proxies=proxies, verify=False, timeout=30)
        status = resp.json().get('status')
        
        if status == 'COMPLETED':
            break
        elif status in ('FAILED', 'CANCELLED'):
            return {"success": False, "status": status, "error": "Generation failed"}
        
        time.sleep(5)
    else:
        return {"success": False, "error": "Timeout"}
    
    if not download:
        return {"success": True, "status": "COMPLETED", "request_id": request_id}
    
    # Download result
    result_resp = requests.get(result_url, headers=headers, proxies=proxies, verify=False, timeout=60)
    record_response(result_resp, request_url=result_url)
    video_url = result_resp.json()['video']['url']
    
    os.makedirs('output/videos', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    local_path = f"output/videos/{timestamp}_{request_id}_result.mp4"
    
    video_data = requests.get(video_url, timeout=120).content
    open(local_path, 'wb').write(video_data)
    
    return {
        "success": True,
        "request_id": request_id,
        "video_url": video_url,
        "local_path": local_path,
        "file_size_mb": len(video_data) / 1024 / 1024
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python poll_status.py <request_id>")
        sys.exit(1)
    
    result = poll_video(sys.argv[1])
    print(result)