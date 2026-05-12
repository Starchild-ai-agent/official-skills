"""Internal HTTP helpers for the Venice skill.

Direct connection to api.venice.ai (NOT through sc-proxy — Venice is a BYOK
vendor, costs are billed against the user's own Venice balance via the
VENICE_API_KEY).

All public functions in `exports.py` go through `_request()` so we have a
single place to handle auth, timeouts, error normalization, and content-type
sniffing (Venice returns JSON for most endpoints, raw bytes for image/edit
and audio/speech).
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import requests

BASE_URL = "https://api.venice.ai/api/v1"
DEFAULT_TIMEOUT = 120  # seconds — image/upscale can be slow

# ----------------------------------------------------------------------------


class VeniceError(RuntimeError):
    """Raised when Venice returns 4xx/5xx or the request fails locally."""

    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(f"Venice API error {status}: {message}")
        self.status = status
        self.message = message
        self.body = body


def _api_key() -> str:
    """Resolve the Venice API key from .env / environment.

    Search order:
      1. VENICE_API_KEY                  (canonical)
      2. CUSTOM_KEY_VENICE_*             (BYOK custom-model entries — agent
                                          may have set this when registering
                                          venice for chat completions)
    """
    direct = os.environ.get("VENICE_API_KEY")
    if direct:
        return direct
    # Scan BYOK custom-model env vars in case the user only configured chat
    # via the custom_models tool (which auto-generates an env name like
    # CUSTOM_KEY_VENICE_UNCENSORED_AB12).
    for k, v in os.environ.items():
        if k.startswith("CUSTOM_KEY_VENICE") and v:
            return v
    raise VeniceError(
        401,
        "VENICE_API_KEY not set. Get a key at https://venice.ai/settings/api "
        "and ask the agent to add it (the agent will dispatch a secure-input "
        "popup; never paste keys in chat).",
    )


def _request(
    method: str,
    path: str,
    *,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    expect_binary: bool = False,
) -> Tuple[Union[bytes, Dict[str, Any]], requests.Response]:
    """Call Venice API and return (parsed_body, raw_response).

    expect_binary=True returns the body as raw bytes (for image edit / TTS
    audio / image upscale). Otherwise the body is parsed as JSON; if the
    server returns binary anyway, we still return raw bytes — caller can
    inspect `raw.headers["content-type"]`.
    """
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {_api_key()}"}

    # When sending JSON, requests sets the content-type for us. Don't set it
    # manually for multipart (files=) calls or requests will overwrite the
    # boundary.
    if json is not None and not files:
        headers["Content-Type"] = "application/json"

    try:
        r = requests.request(
            method, url,
            headers=headers,
            json=json if not files else None,
            data=data,
            files=files,
            params=params,
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise VeniceError(0, f"network error: {e}") from e

    if r.status_code >= 400:
        # Venice returns {"error": "..."} on failures
        try:
            err_body = r.json()
            err_msg = err_body.get("error") or r.text[:300]
        except Exception:
            err_body = r.text[:500]
            err_msg = err_body
        raise VeniceError(r.status_code, err_msg, body=err_body)

    ct = (r.headers.get("content-type") or "").lower()
    if expect_binary or not ct.startswith("application/json"):
        return r.content, r

    return r.json(), r


# ----------------------------------------------------------------------------
# Image-bytes ↔ base64 helpers, since Venice accepts both URL/base64/file
# ----------------------------------------------------------------------------

def _resolve_image_input(image: Union[str, bytes, Path]) -> str:
    """Normalize an image input into base64 (Venice accepts data URIs too).

    Accepts:
      - bytes                       → base64-encoded
      - str starting with http(s):// → returned unchanged (Venice fetches it)
      - str starting with data:     → returned unchanged
      - str path / Path that exists → read + base64-encoded
      - str of pure base64          → returned unchanged
    """
    if isinstance(image, bytes):
        return base64.b64encode(image).decode()
    if isinstance(image, Path):
        return base64.b64encode(image.read_bytes()).decode()
    if not isinstance(image, str):
        raise TypeError(f"image must be str/bytes/Path, got {type(image).__name__}")
    if image.startswith(("http://", "https://", "data:")):
        return image
    p = Path(image)
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    # Assume it's already base64
    return image


def _save_bytes(content: bytes, save_path: Union[str, Path]) -> str:
    """Write content to save_path (creating parent dirs). Returns the path."""
    p = Path(save_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return str(p)
