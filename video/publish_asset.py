#!/usr/bin/env python3
"""Publish a local image/video to output/fal_assets/ for fal.ai reference inputs.

Workflow:
  1. Drop file into output/fal_assets/
  2. Combine with the public preview base URL (see SKILL.md) to form the URL fal needs.

If the file is already a URL, it is downloaded first.
"""
from __future__ import annotations
import os, shutil, sys, mimetypes
from pathlib import Path
import requests

ASSETS_DIR = Path('output/fal_assets')
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
VIDEO_EXTS = {'.mp4', '.mov', '.webm', '.mkv', '.m4v'}
ALLOWED_EXTS = IMAGE_EXTS | VIDEO_EXTS

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024


def publish_local(src_path: str, rename: str | None = None) -> dict:
    p = Path(src_path)
    if not p.exists() or not p.is_file():
        return {"success": False, "error": f"file not found: {src_path}"}

    ext = p.suffix.lower()
    if ext not in ALLOWED_EXTS:
        return {"success": False, "error": f"unsupported extension: {ext}"}

    size = p.stat().st_size
    limit = MAX_IMAGE_BYTES if ext in IMAGE_EXTS else MAX_VIDEO_BYTES
    if size > limit:
        return {"success": False, "error": f"file too large: {size} > {limit} bytes"}

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    target_name = rename or p.name
    dst = ASSETS_DIR / target_name
    shutil.copy(p, dst)

    return {
        "success": True,
        "local_path": str(dst),
        "filename": target_name,
        "kind": "image" if ext in IMAGE_EXTS else "video",
        "size_bytes": size,
        "hint": "Combine with public preview base URL: <preview_base>/<filename>",
    }


def publish_from_url(src_url: str, rename: str | None = None) -> dict:
    if not src_url.startswith(('http://', 'https://')):
        return {"success": False, "error": "src_url must be http(s)"}

    try:
        r = requests.get(src_url, timeout=60)
        r.raise_for_status()
    except Exception as e:
        return {"success": False, "error": f"download failed: {e}"}

    name = rename or src_url.rstrip('/').split('/')[-1].split('?')[0]
    if '.' not in name:
        ct = (r.headers.get('Content-Type') or '').split(';')[0].strip()
        ext_guess = mimetypes.guess_extension(ct) or '.bin'
        name = f"{name}{ext_guess}"

    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTS:
        return {"success": False, "error": f"unsupported extension: {ext}"}

    size = len(r.content)
    limit = MAX_IMAGE_BYTES if ext in IMAGE_EXTS else MAX_VIDEO_BYTES
    if size > limit:
        return {"success": False, "error": f"file too large: {size} > {limit} bytes"}

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    dst = ASSETS_DIR / name
    dst.write_bytes(r.content)

    return {
        "success": True,
        "local_path": str(dst),
        "filename": name,
        "kind": "image" if ext in IMAGE_EXTS else "video",
        "size_bytes": size,
        "hint": "Combine with public preview base URL: <preview_base>/<filename>",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python skills/video/publish_asset.py <local_path|url> [rename]")
        sys.exit(1)
    src = sys.argv[1]
    rename = sys.argv[2] if len(sys.argv) > 2 else None
    fn = publish_from_url if src.startswith('http') else publish_local
    print(fn(src, rename))
