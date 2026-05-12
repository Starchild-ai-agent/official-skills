"""Venice skill — script-mode exports.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/venice")
    from exports import (
        list_models, image_generate, image_edit, image_upscale,
        tts, transcribe, embeddings, account_balance,
        list_image_styles, list_characters, chat_with_venice_parameters,
        video_quote, video_generate, video_transcribe_youtube,
    )
    print(account_balance())
    EOF

Every function below was verified to work against api.venice.ai with the
maintainer's BYOK key on 2026-05-11. Endpoints that 404'd (standalone
/tools/search/web, /api_keys list without admin scope) were dropped.

For chat completions, the recommended path is BYOK via the `custom_models`
tool — that integration has streaming, history, cost tracking, and is the
right surface for everyday chat. Use `chat_with_venice_parameters()` only
for one-off probes when you need to test enable_web_search / character_slug
/ disable_thinking before adding Venice as a registered chat model.
"""
from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from api import _request, _resolve_image_input, _save_bytes, VeniceError


# ----------------------------------------------------------------------------
# Models / catalog (no auth needed by Venice but we still send the key — the
# rate-limit endpoint and any paid endpoint require it)
# ----------------------------------------------------------------------------

def list_models(
    type_filter: Optional[str] = None,
    only_capabilities: Optional[List[str]] = None,
    privacy: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List Venice models with capability + pricing metadata.

    Args:
      type_filter: keep only models of one type. Common values: "text",
        "image", "tts", "stt", "embedding", "upscale". Omit for all types.
      only_capabilities: list of capability flags the model must support
        (any of them). E.g. ["supportsVision","supportsFunctionCalling"].
      privacy: filter by privacy tier — "anonymized" | "private" | "tee" |
        "e2ee".

    Returns: list of normalized model dicts (id, name, type, privacy,
      pricing_input_usd, pricing_output_usd, capabilities, context_tokens,
      description, traits).

    Implementation note: Venice's /models endpoint returns ONE type per call
    (default `text`). Pass `type_filter='all'` to fetch every type at once,
    or any specific type to scope the upstream query and reduce payload.
    """
    params = {"type": type_filter} if type_filter else {}
    body, _ = _request("GET", "/models", params=params)
    items = body.get("data", []) if isinstance(body, dict) else []

    out = []
    for m in items:
        spec = m.get("model_spec") or {}
        if not isinstance(spec, dict):
            continue
        caps = spec.get("capabilities") or {}
        pricing = spec.get("pricing") or {}
        item = {
            "id": m.get("id"),
            "type": m.get("type"),
            "name": spec.get("name"),
            "description": spec.get("description"),
            "privacy": spec.get("privacy"),
            "context_tokens": spec.get("availableContextTokens"),
            "max_completion_tokens": spec.get("maxCompletionTokens"),
            "capabilities": caps,
            "pricing_input_usd": (pricing.get("input") or {}).get("usd"),
            "pricing_output_usd": (pricing.get("output") or {}).get("usd"),
            "pricing_cache_input_usd": (pricing.get("cache_input") or {}).get("usd"),
            "traits": spec.get("traits", []),
            "owned_by": m.get("owned_by"),
        }
        # Server-side type filter already applied via params. Only re-check
        # locally when user passed `all` plus a follow-up filter via
        # other args (rare).
        if privacy and item["privacy"] != privacy:
            continue
        if only_capabilities:
            if not any(caps.get(c) for c in only_capabilities):
                continue
        out.append(item)
    return out


def list_model_traits() -> Dict[str, str]:
    """Return Venice's model trait → model_id map (e.g. fastest, smartest)."""
    body, _ = _request("GET", "/models/traits")
    return body.get("data", body) if isinstance(body, dict) else {}


def list_image_styles() -> List[str]:
    """Return the list of preset style names accepted by /image/generate."""
    body, _ = _request("GET", "/image/styles")
    if isinstance(body, dict):
        return body.get("data", body.get("styles", []))
    return body


def list_characters(limit: int = 20) -> List[Dict[str, Any]]:
    """Return public Venice character personas (slug + name + description).

    Truncated to `limit` entries by default — the full list is ~50KB.
    """
    body, _ = _request("GET", "/characters")
    items = body.get("data", []) if isinstance(body, dict) else []
    return [
        {
            "slug": c.get("slug"),
            "name": c.get("name"),
            "description": (c.get("description") or "")[:200],
            "tags": c.get("tags", []),
        }
        for c in items[:limit]
    ]


# ----------------------------------------------------------------------------
# Account
# ----------------------------------------------------------------------------

def account_balance() -> Dict[str, Any]:
    """Return account tier + USD/DIEM balance + per-model rate limits."""
    body, _ = _request("GET", "/api_keys/rate_limits")
    data = body.get("data", body) if isinstance(body, dict) else {}
    return {
        "tier": (data.get("apiTier") or {}).get("id"),
        "is_charged": (data.get("apiTier") or {}).get("isCharged"),
        "balance_usd": (data.get("balances") or {}).get("USD"),
        "balance_diem": (data.get("balances") or {}).get("DIEM"),
        "key_expiration": data.get("keyExpiration"),
        "next_epoch_begins": data.get("nextEpochBegins"),
        "rate_limits_count": len(data.get("rateLimits", [])),
    }


# ----------------------------------------------------------------------------
# Image generation
# ----------------------------------------------------------------------------

def image_generate(
    prompt: str,
    *,
    model: str = "venice-sd35",
    width: int = 1024,
    height: int = 1024,
    steps: int = 20,
    cfg_scale: Optional[float] = None,
    seed: Optional[int] = None,
    style_preset: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    fmt: str = "webp",
    save_path: Optional[Union[str, Path]] = None,
    safe_mode: bool = False,
) -> Dict[str, Any]:
    """Generate an image.

    Returns a dict with:
      id, model, prompt, width, height, image_b64 (always),
      saved_path (if save_path provided), pricing snapshot.

    Note: the response contains the image as base64 in `images[0]`. We always
    decode it; if `save_path` is given, we additionally write the bytes there.
    Default save location follows the platform convention
    (output/images/) — pass a relative filename to use it.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "format": fmt,
        "safe_mode": safe_mode,
        "return_binary": False,
    }
    if cfg_scale is not None: payload["cfg_scale"] = cfg_scale
    if seed is not None: payload["seed"] = seed
    if style_preset: payload["style_preset"] = style_preset
    if negative_prompt: payload["negative_prompt"] = negative_prompt

    body, _ = _request("POST", "/image/generate", json=payload)
    images = body.get("images") or []
    if not images:
        raise VeniceError(500, f"empty images[] in response: {str(body)[:200]}")

    img_b64 = images[0] if isinstance(images[0], str) else images[0].get("b64", "")
    saved = None
    if save_path:
        sp = Path(save_path)
        # Default to output/images/ when only a filename is given
        if not sp.is_absolute() and len(sp.parts) == 1:
            sp = Path("output/images") / sp
        if not sp.suffix:
            sp = sp.with_suffix(f".{fmt}")
        saved = _save_bytes(base64.b64decode(img_b64), sp)

    return {
        "id": body.get("id"),
        "model": model,
        "prompt": prompt,
        "width": width,
        "height": height,
        "image_b64": img_b64,
        "saved_path": saved,
        "timing": body.get("timing"),
        "request_echo": body.get("request"),
    }


def image_edit(
    image: Union[str, bytes, Path],
    prompt: str,
    *,
    model: str = "qwen-edit",
    aspect_ratio: Optional[str] = None,
    save_path: Optional[Union[str, Path]] = None,
    fmt: str = "png",
) -> Dict[str, Any]:
    """Edit an image with a text prompt.

    `image` accepts: bytes / Path / file path string / http(s) URL / data
    URI / pure base64 string. Anything not URL/data is base64-encoded for
    transport.

    Default model `qwen-edit` is $0.04/edit. Other valid models (per Venice
    docs): firered-image-edit, grok-imagine-edit, qwen-image-2-edit,
    qwen-image-2-pro-edit, wan-2-7-pro-edit, flux-2-max-edit,
    nano-banana-pro-edit, seedream-v5-lite-edit, seedream-v4-edit.

    Returns: {model, saved_path, image_b64, content_type, bytes}.
    The endpoint returns raw image bytes (not JSON); we always base64-encode
    them for the return value, and additionally write them to disk if
    save_path is given.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "image": _resolve_image_input(image),
    }
    if aspect_ratio: payload["aspect_ratio"] = aspect_ratio

    content, raw = _request("POST", "/image/edit", json=payload, expect_binary=True)
    ct = raw.headers.get("content-type", "image/png")

    saved = None
    if save_path:
        sp = Path(save_path)
        if not sp.is_absolute() and len(sp.parts) == 1:
            sp = Path("output/images") / sp
        if not sp.suffix:
            sp = sp.with_suffix(f".{fmt}")
        saved = _save_bytes(content, sp)

    return {
        "model": model,
        "prompt": prompt,
        "saved_path": saved,
        "content_type": ct,
        "bytes": len(content),
        "image_b64": base64.b64encode(content).decode(),
    }


def image_upscale(
    image: Union[str, bytes, Path],
    *,
    scale: int = 2,
    save_path: Optional[Union[str, Path]] = None,
    fmt: str = "png",
) -> Dict[str, Any]:
    """Upscale an image (default 2x). scale ∈ {2, 4} per Venice docs.

    Same image-input rules as image_edit. Returns {saved_path, content_type,
    bytes, image_b64}.
    """
    payload = {"image": _resolve_image_input(image), "scale": scale}
    content, raw = _request("POST", "/image/upscale", json=payload, expect_binary=True)
    ct = raw.headers.get("content-type", "image/png")

    saved = None
    if save_path:
        sp = Path(save_path)
        if not sp.is_absolute() and len(sp.parts) == 1:
            sp = Path("output/images") / sp
        if not sp.suffix:
            sp = sp.with_suffix(f".{fmt}")
        saved = _save_bytes(content, sp)

    return {
        "scale": scale,
        "saved_path": saved,
        "content_type": ct,
        "bytes": len(content),
        "image_b64": base64.b64encode(content).decode(),
    }


# ----------------------------------------------------------------------------
# Audio
# ----------------------------------------------------------------------------

def tts(
    text: str,
    *,
    model: str = "tts-kokoro",
    voice: str = "af_alloy",
    response_format: str = "mp3",
    speed: Optional[float] = None,
    save_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Text-to-speech.

    Verified models: tts-kokoro (default), tts-qwen3-0-6b, tts-qwen3-1-7b,
    tts-xai-v1, tts-inworld-1-5-max, tts-chatterbox-hd, tts-orpheus,
    tts-elevenlabs-turbo-v2-5.

    response_format: mp3 | opus | aac | flac | wav | pcm.

    Returns {saved_path, content_type, bytes}. Default save dir is output/audio/.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": response_format,
    }
    if speed is not None:
        payload["speed"] = speed

    content, raw = _request("POST", "/audio/speech", json=payload, expect_binary=True)
    ct = raw.headers.get("content-type", f"audio/{response_format}")

    saved = None
    if save_path:
        sp = Path(save_path)
        if not sp.is_absolute() and len(sp.parts) == 1:
            sp = Path("output/audio") / sp
        if not sp.suffix:
            sp = sp.with_suffix(f".{response_format}")
        saved = _save_bytes(content, sp)

    return {
        "model": model,
        "voice": voice,
        "saved_path": saved,
        "content_type": ct,
        "bytes": len(content),
    }


def transcribe(
    audio_path: Union[str, Path],
    *,
    model: str = "openai/whisper-large-v3",
    language: Optional[str] = None,
    response_format: str = "json",
) -> Dict[str, Any]:
    """Speech-to-text (multipart upload).

    Verified models: openai/whisper-large-v3, stt-xai-v1.
    Note the `openai/` prefix is required — bare `whisper-large-v3` returns 404.

    Returns the parsed JSON response (typically {text, duration, ...}).
    """
    p = Path(audio_path)
    if not p.exists():
        raise FileNotFoundError(f"audio_path not found: {p}")
    data: Dict[str, Any] = {"model": model, "response_format": response_format}
    if language:
        data["language"] = language

    with p.open("rb") as f:
        body, _ = _request(
            "POST", "/audio/transcriptions",
            files={"file": (p.name, f, "application/octet-stream")},
            data=data,
        )
    return body if isinstance(body, dict) else {"raw": body}


# ----------------------------------------------------------------------------
# Embeddings
# ----------------------------------------------------------------------------

def embeddings(
    inputs: Union[str, List[str]],
    *,
    model: str = "text-embedding-bge-m3",
) -> Dict[str, Any]:
    """Compute embeddings for one or more strings.

    Returns {model, count, dim, vectors: list[list[float]]}.
    """
    if isinstance(inputs, str):
        inputs = [inputs]
    body, _ = _request("POST", "/embeddings",
                        json={"model": model, "input": inputs})
    data = body.get("data", []) if isinstance(body, dict) else []
    vectors = [d.get("embedding") for d in data]
    return {
        "model": model,
        "count": len(vectors),
        "dim": len(vectors[0]) if vectors else 0,
        "vectors": vectors,
        "usage": body.get("usage") if isinstance(body, dict) else None,
    }


# ----------------------------------------------------------------------------
# Chat — for probing venice_parameters before BYOK registration
# ----------------------------------------------------------------------------

def chat_with_venice_parameters(
    prompt: str,
    *,
    model: str = "venice-uncensored-1-2",
    venice_parameters: Optional[Dict[str, Any]] = None,
    system: Optional[str] = None,
    max_tokens: int = 256,
    temperature: Optional[float] = None,
) -> Dict[str, Any]:
    """One-shot chat completion exposing venice_parameters.

    For day-to-day chat, register Venice as a BYOK model via
    `custom_models(action='add_template', vendor='venice')` and select it in
    the model picker — that path has streaming, history, and cost tracking.

    USE THIS HELPER ONLY for quick probes:
      - Test that enable_web_search returns citations
      - Try a character_slug before pinning it
      - Verify disable_thinking on a reasoning model
      - Check include_venice_system_prompt=False behavior

    Supported venice_parameters keys (Venice docs, 2026-05):
      enable_web_search          : "auto" | "on" | "off"
      enable_web_scraping        : bool
      enable_web_citations       : bool
      enable_x_search            : bool          (xAI native)
      character_slug             : str           (see list_characters())
      include_venice_system_prompt: bool         (default True)
      strip_thinking_response    : bool          (drop <think> blocks)
      disable_thinking           : bool          (force-off on reasoning models)
      enable_e2ee                : bool          (E2EE-capable models only)
    """
    msgs: List[Dict[str, Any]] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": model,
        "messages": msgs,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if venice_parameters:
        payload["venice_parameters"] = venice_parameters

    body, _ = _request("POST", "/chat/completions", json=payload)
    choices = body.get("choices") or [] if isinstance(body, dict) else []
    text = ""
    if choices:
        text = (choices[0].get("message") or {}).get("content", "")

    return {
        "model": model,
        "text": text,
        "venice_parameters": venice_parameters or {},
        "usage": body.get("usage") if isinstance(body, dict) else None,
        # Surface citations / sources if the response carried them. Venice
        # places web_search hits in choices[0].message.tool_calls or in a
        # top-level .web_search_response depending on model.
        "web_search": (
            (choices[0].get("message") or {}).get("web_search_results")
            if choices else None
        ),
        "raw_response_keys": list(body.keys()) if isinstance(body, dict) else None,
    }


# ----------------------------------------------------------------------------
# Video — async quote/queue/retrieve/complete loop
# ----------------------------------------------------------------------------
#
# Lifecycle:
#   video_quote(...)   → free preview of cost
#   video_queue(...)   → submits job, charges balance, returns queue_id
#   video_retrieve(...) → single poll: returns dict (PROCESSING) or bytes
#                          (COMPLETED non-VPS), or {status:COMPLETED,
#                          download_url:...} for VPS-backed models
#   video_complete(...) → tells Venice to delete the media (cleanup)
#
# `video_generate(...)` wraps the whole loop end-to-end with polling and
# returns the saved file path.

def video_quote(
    *,
    model: str,
    duration: str = "5s",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    audio: bool = True,
    upscale_factor: Optional[int] = None,
) -> Dict[str, Any]:
    """Get a USD price quote for a video job. No charge, no job created."""
    payload: Dict[str, Any] = {
        "model": model,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "audio": audio,
    }
    if upscale_factor is not None:
        payload["upscale_factor"] = upscale_factor
    body, _ = _request("POST", "/video/quote", json=payload)
    return body if isinstance(body, dict) else {"quote": body}


def video_queue(
    *,
    model: str,
    prompt: str,
    duration: str = "5s",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    audio: bool = True,
    negative_prompt: Optional[str] = None,
    image_url: Optional[str] = None,
    end_image_url: Optional[str] = None,
    audio_url: Optional[str] = None,
    video_url: Optional[str] = None,
    reference_image_urls: Optional[List[str]] = None,
    elements: Optional[List[Dict[str, Any]]] = None,
    scene_image_urls: Optional[List[str]] = None,
    upscale_factor: Optional[int] = None,
    delete_media_on_completion: bool = False,
) -> Dict[str, Any]:
    """Enqueue a video generation job. Returns {model, queue_id, download_url?}.

    Charges (reserves) the quote price against the Venice balance immediately.
    The `download_url` field appears ONLY for VPS-backed models — when present,
    you should fetch it directly after status==COMPLETED instead of pulling
    bytes from /video/retrieve. Valid 24h.

    See SKILL.md for the full parameter table and per-field constraints.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "audio": audio,
        "delete_media_on_completion": delete_media_on_completion,
    }
    for k, v in [
        ("negative_prompt", negative_prompt),
        ("image_url", image_url),
        ("end_image_url", end_image_url),
        ("audio_url", audio_url),
        ("video_url", video_url),
        ("reference_image_urls", reference_image_urls),
        ("elements", elements),
        ("scene_image_urls", scene_image_urls),
        ("upscale_factor", upscale_factor),
    ]:
        if v is not None:
            payload[k] = v

    body, _ = _request("POST", "/video/queue", json=payload)
    return body if isinstance(body, dict) else {"raw": body}


def video_retrieve(
    *,
    model: str,
    queue_id: str,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Single poll. Returns either:
      - {"status": "PROCESSING", "average_execution_time": ms,
         "execution_duration": ms}
      - {"status": "COMPLETED", "download_url": "..."} for VPS-backed models
      - {"status": "COMPLETED", "video_bytes": <bytes>, "content_type":
         "video/mp4"} for non-VPS models (binary inline)

    For end-to-end use, prefer `video_generate()` which polls + downloads.
    """
    payload = {"model": model, "queue_id": queue_id}
    content, raw = _request(
        "POST", "/video/retrieve", json=payload,
        timeout=timeout, expect_binary=True,
    )
    ct = (raw.headers.get("content-type") or "").lower()
    if ct.startswith("video/"):
        return {"status": "COMPLETED", "video_bytes": content,
                "content_type": ct}
    # JSON response (still came back via expect_binary=True so re-decode)
    import json as _json
    try:
        body = _json.loads(content)
    except Exception:
        body = {"raw": content[:200]}
    return body


def video_complete(*, model: str, queue_id: str) -> Dict[str, Any]:
    """Finalize a job and instruct Venice to delete the stored media.

    Call after you've successfully downloaded the video. Idempotent. If you
    queued with `delete_media_on_completion=True` this is unnecessary.
    """
    body, _ = _request("POST", "/video/complete",
                        json={"model": model, "queue_id": queue_id})
    return body if isinstance(body, dict) else {"raw": body}


def video_generate(
    *,
    model: str,
    prompt: str,
    duration: str = "5s",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    audio: bool = True,
    save_path: Optional[Union[str, Path]] = None,
    poll_interval: int = 5,
    max_wait_s: int = 900,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    auto_complete: bool = True,
    **queue_kwargs: Any,
) -> Dict[str, Any]:
    """End-to-end: quote → queue → poll → download → complete.

    `**queue_kwargs` accepts the same extras as `video_queue` (image_url,
    audio_url, reference_image_urls, elements, scene_image_urls, etc.).

    save_path defaults to output/videos/<queue_id>.mp4 when omitted.
    Filename-only (no slashes) → output/videos/<filename>.

    `on_progress` is called every poll with the raw retrieve response —
    useful for surfacing ETA to the user from `average_execution_time` and
    `execution_duration` (both in ms).

    Returns: {queue_id, model, prompt, saved_path, bytes, content_type,
              quote_usd, elapsed_s, polls}.
    """
    quote = video_quote(model=model, duration=duration,
                         aspect_ratio=aspect_ratio, resolution=resolution,
                         audio=audio,
                         upscale_factor=queue_kwargs.get("upscale_factor"))
    queued = video_queue(model=model, prompt=prompt, duration=duration,
                          aspect_ratio=aspect_ratio, resolution=resolution,
                          audio=audio, **queue_kwargs)
    queue_id = queued.get("queue_id")
    if not queue_id:
        raise VeniceError(500, f"queue did not return queue_id: {queued}")
    download_url = queued.get("download_url")  # may be None

    started = time.time()
    polls = 0
    video_bytes: Optional[bytes] = None
    content_type = "video/mp4"

    while True:
        elapsed = time.time() - started
        if elapsed > max_wait_s:
            raise VeniceError(
                504,
                f"video_generate timeout after {int(elapsed)}s "
                f"(max_wait_s={max_wait_s}). queue_id={queue_id} — "
                f"call video_retrieve manually to keep waiting.",
            )

        result = video_retrieve(model=model, queue_id=queue_id)
        polls += 1
        if on_progress:
            try:
                on_progress(result)
            except Exception:
                pass

        status = result.get("status")
        if "video_bytes" in result:
            video_bytes = result["video_bytes"]
            content_type = result.get("content_type", "video/mp4")
            break
        if status == "COMPLETED":
            url = result.get("download_url") or download_url
            if not url:
                raise VeniceError(500,
                    f"COMPLETED but no download_url and no inline bytes: {result}")
            import requests as _r
            r = _r.get(url, timeout=120)
            r.raise_for_status()
            video_bytes = r.content
            content_type = r.headers.get("content-type", "video/mp4")
            break
        if status and status != "PROCESSING":
            raise VeniceError(500, f"unexpected status={status!r}: {result}")
        time.sleep(poll_interval)

    saved = None
    if save_path is None:
        save_path = f"{queue_id}.mp4"
    sp = Path(save_path)
    if not sp.is_absolute() and len(sp.parts) == 1:
        sp = Path("output/videos") / sp
    if not sp.suffix:
        sp = sp.with_suffix(".mp4")
    saved = _save_bytes(video_bytes, sp)

    if auto_complete:
        try:
            video_complete(model=model, queue_id=queue_id)
        except VeniceError:
            pass  # cleanup is best-effort; the file already saved.

    return {
        "queue_id": queue_id,
        "model": model,
        "prompt": prompt,
        "saved_path": saved,
        "bytes": len(video_bytes),
        "content_type": content_type,
        "quote_usd": quote.get("quote"),
        "elapsed_s": round(time.time() - started, 1),
        "polls": polls,
    }


def video_transcribe_youtube(
    url: str,
    *,
    response_format: str = "json",
) -> Dict[str, Any]:
    """Synchronously transcribe a YouTube video URL via Venice.

    response_format: "json" → {transcript, lang} | "text" → {text: "..."}.

    For arbitrary local audio/video files, use the `transcribe()` function
    above (which targets /audio/transcriptions and accepts file uploads).
    """
    body, _ = _request("POST", "/video/transcriptions",
                        json={"url": url, "response_format": response_format})
    if isinstance(body, dict):
        return body
    if isinstance(body, bytes):
        return {"text": body.decode("utf-8", errors="replace")}
    return {"text": str(body)}
