"""Low-level fal queue client shared by every action in the `image` skill.

Responsibilities (and nothing else):
  * resolve local files / URLs into request inputs (data URIs for local files)
  * submit → persist request_id immediately → poll → fetch → download
  * one UUID output directory per job (no same-second overwrites)
  * cost accounting via _cost_track (SC-CALLER-ID + ledger rows)

Prompt construction and model selection live in image_skill.py; capability
validation lives in catalog.py. Keep this file free of model-specific logic.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from _cost_track import caller_headers, record_response  # noqa: E402

_FAL_KEY = os.environ.get("FAL_KEY")          # local testing only
_LOCAL_MODE = bool(_FAL_KEY)
PROXY_URL = "http://sc-proxy.internal:8080"
PROXIES = {} if _LOCAL_MODE else {"http": PROXY_URL, "https": PROXY_URL}

OUTPUT_ROOT = os.environ.get("IMAGE_OUTPUT_DIR", "output/images")
JOBS_DIR = os.path.join(OUTPUT_ROOT, ".jobs")   # request_id persistence
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _auth() -> str:
    return _FAL_KEY if _LOCAL_MODE else "fake-falai-key-12345"


def _headers(tool: str) -> Dict[str, str]:
    return caller_headers({"Authorization": f"Key {_auth()}",
                           "Content-Type": "application/json"}, tool_default=tool)


# ── inputs ───────────────────────────────────────────────────────────────────

def resolve_input(path: Optional[str] = None, url: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Local path → data URI; http(s) URL passes through. Returns (value, error)."""
    if not path and not url:
        return None, "an image path or URL is required"
    if path:
        p = Path(path)
        if not p.is_file():
            return None, f"file not found: {path}"
        if p.suffix.lower() not in SUPPORTED_EXTS:
            return None, f"unsupported format {p.suffix}; use {sorted(SUPPORTED_EXTS)}"
        if p.stat().st_size > MAX_IMAGE_BYTES:
            return None, f"file too large ({p.stat().st_size // 1024 // 1024} MB > 10 MB): {path}"
        mime = mimetypes.guess_type(str(p))[0] or "image/png"
        return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}", None
    if not str(url).startswith(("http://", "https://")):
        return None, "image URL must be http(s); pass local files as a path"
    return url, None


def image_dims(path: str) -> Optional[Tuple[int, int]]:
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


# ── job lifecycle ────────────────────────────────────────────────────────────

def new_job_dir(label: str) -> Tuple[str, str]:
    """Unique per-job directory: output/images/<YYYYmmdd>_<label>_<uuid8>/"""
    job_id = uuid.uuid4().hex[:8]
    d = os.path.join(OUTPUT_ROOT, f"{datetime.now():%Y%m%d}_{label}_{job_id}")
    os.makedirs(d, exist_ok=True)
    return job_id, d


def _persist(job_id: str, payload: Dict[str, Any]) -> None:
    os.makedirs(JOBS_DIR, exist_ok=True)
    with open(os.path.join(JOBS_DIR, f"{job_id}.json"), "w") as f:
        json.dump(payload, f, indent=1, default=str)


def load_job(job_id: str) -> Optional[Dict[str, Any]]:
    p = os.path.join(JOBS_DIR, f"{job_id}.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def submit(endpoint: str, body: Dict[str, Any], tool: str, job_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """POST to the fal queue. Persists request_id BEFORE returning so a later
    network failure can be recovered with fetch_result() instead of paying twice."""
    url = f"https://queue.fal.run/{endpoint}"
    try:
        resp = requests.post(url, headers=_headers(tool), json=body,
                             proxies=PROXIES, verify=False, timeout=90)
    except requests.RequestException as e:
        return None, f"submit failed (network): {e}"
    # never log data URIs
    safe_body = {k: (f"<{len(v)} inputs>" if k in ("image_urls",) else ("<data>" if isinstance(v, str) and v.startswith("data:") else v))
                 for k, v in body.items()}
    record_response(resp, request_url=url, request_payload=safe_body)
    if resp.status_code != 200:
        return None, f"submit failed: HTTP {resp.status_code} — {resp.text[:300]}"
    data = resp.json()
    data["_cost"] = float(resp.headers.get("X-Credits-Used", 0) or 0)
    data["_endpoint"] = endpoint
    _persist(job_id, {"job_id": job_id, "endpoint": endpoint, "request_id": data.get("request_id"),
                      "status_url": data.get("status_url"),
                      "response_url": data.get("response_url") or data.get("result_url"),
                      "submitted_at": datetime.utcnow().isoformat() + "Z",
                      "cost": data["_cost"], "body": safe_body})
    return data, None


def poll(status_url: str, timeout_s: int, poll_s: int) -> Tuple[str, Optional[str]]:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        try:
            r = requests.get(status_url, headers={"Authorization": f"Key {_auth()}"},
                             proxies=PROXIES, verify=False, timeout=60)
            last = r.json().get("status")
            if last == "COMPLETED":
                return "COMPLETED", None
            if last in ("FAILED", "CANCELLED"):
                return last, f"upstream reported {last}"
        except (requests.RequestException, ValueError):
            pass
        time.sleep(poll_s)
    return "TIMEOUT", f"no result after {timeout_s}s (last status: {last}); recover later with fetch_result(job_id)"


def fetch_result(response_url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        r = requests.get(response_url, headers={"Authorization": f"Key {_auth()}"},
                         proxies=PROXIES, verify=False, timeout=90)
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        return None, f"fetch failed: {e}"
    if r.status_code != 200:
        return None, f"upstream error {r.status_code}: {data.get('detail', str(data))[:300]}"
    return data, None


def extract_urls(result: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    for key in ("images", "output", "outputs", "data"):
        arr = result.get(key)
        if isinstance(arr, list):
            for it in arr:
                if isinstance(it, dict) and isinstance(it.get("url"), str):
                    urls.append(it["url"])
                elif isinstance(it, dict) and isinstance(it.get("b64_json"), str):
                    urls.append("data:image/png;base64," + it["b64_json"])
                elif isinstance(it, str) and it.startswith("http"):
                    urls.append(it)
    if not urls:
        for key in ("image", "output_image"):
            node = result.get(key)
            if isinstance(node, dict) and isinstance(node.get("url"), str):
                urls.append(node["url"])
    return urls


def download_all(urls: List[str], job_dir: str, fmt: str = "png") -> Tuple[List[Dict[str, Any]], List[str]]:
    files, errors = [], []
    for i, u in enumerate(urls):
        try:
            if u.startswith("data:"):
                raw = base64.b64decode(u.split(",", 1)[1])
                ext = ".png"
            else:
                r = requests.get(u, timeout=120)
                r.raise_for_status()
                raw = r.content
                ext = ".jpg" if ".jpg" in u or ".jpeg" in u else ".webp" if ".webp" in u else f".{fmt if fmt != 'jpeg' else 'jpg'}"
            path = os.path.join(job_dir, f"{i}{ext}")
            with open(path, "wb") as f:
                f.write(raw)
            files.append({"local_path": path, "size_bytes": len(raw), "dims": image_dims(path),
                          "url": None if u.startswith("data:") else u})
        except Exception as e:  # noqa: BLE001
            errors.append(f"download {i} failed: {e}")
    return files, errors


def run_job(endpoint: str, body: Dict[str, Any], *, tool: str, label: str,
            timeout_s: int, poll_s: int, fmt: str = "png") -> Dict[str, Any]:
    """submit → poll → fetch → download. Always returns a dict with `success`."""
    job_id, job_dir = new_job_dir(label)
    data, err = submit(endpoint, body, tool, job_id)
    if err:
        return {"success": False, "job_id": job_id, "error": err}
    status_url = data.get("status_url")
    response_url = data.get("response_url") or data.get("result_url")
    print(f"[image] job={job_id} request={data.get('request_id')} endpoint={endpoint} cost=${data['_cost']:.3f}")
    status, err = poll(status_url, timeout_s, poll_s)
    if status != "COMPLETED":
        return {"success": False, "job_id": job_id, "request_id": data.get("request_id"),
                "status": status, "error": err}
    result, err = fetch_result(response_url)
    if err:
        return {"success": False, "job_id": job_id, "request_id": data.get("request_id"), "error": err}
    urls = extract_urls(result)
    if not urls:
        return {"success": False, "job_id": job_id, "request_id": data.get("request_id"),
                "error": f"no image in response: {result.get('detail') or list(result)}"}
    files, errors = download_all(urls, job_dir, fmt)
    if not files:
        return {"success": False, "job_id": job_id, "error": "all downloads failed", "errors": errors}
    return {"success": True, "job_id": job_id, "request_id": data.get("request_id"),
            "endpoint": endpoint, "job_dir": job_dir, "images": files,
            "cost_usd": round(data["_cost"], 4), "errors": errors or None}


def recover(job_id: str) -> Dict[str, Any]:
    """Re-fetch a previously submitted job by job_id — no new charge."""
    job = load_job(job_id)
    if not job or not job.get("response_url"):
        return {"success": False, "error": f"no persisted job '{job_id}'"}
    status, err = poll(job["status_url"], timeout_s=30, poll_s=3)
    if status != "COMPLETED":
        return {"success": False, "job_id": job_id, "status": status, "error": err}
    result, err = fetch_result(job["response_url"])
    if err:
        return {"success": False, "job_id": job_id, "error": err}
    job_dir = os.path.join(OUTPUT_ROOT, f"recovered_{job_id}")
    os.makedirs(job_dir, exist_ok=True)
    files, errors = download_all(extract_urls(result), job_dir)
    return {"success": bool(files), "job_id": job_id, "job_dir": job_dir, "images": files, "errors": errors or None}
