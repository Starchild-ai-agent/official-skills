"""Model capability catalog for the unified `image` skill.

Single source of truth for *which* models exist and *what each one can do*.
Everything the skill validates (allowed params, enum values, reference-image
limits, mask support) is derived from this file — nothing is hardcoded in the
call path. Adding a model = adding one entry here (or publishing it remotely).

Resolution order:
  1. Remote catalog (JSON) at IMAGE_CATALOG_URL, cached for CATALOG_TTL seconds
     in /tmp — lets the platform ship new/deprecated models without a skill
     release. The remote file must have the same shape as BUILTIN below.
  2. BUILTIN — the vetted fallback shipped with the skill.

Entry schema (per alias):
  id            physical endpoint id (fal route) for text-to-image, or None
  edit_id       physical endpoint id for image-to-image edit, or None
  status        "default" | "candidate" | "deprecated"
                default   → the skill may pick it automatically
                candidate → usable only when the caller names it explicitly
                deprecated→ rejected with a pointer to the replacement
  params        {param_name: spec}   spec = {"type": ..., "enum": [...]} or
                {"type": "int", "min": .., "max": ..} — only params listed here
                are forwarded; anything else is REJECTED (fail-closed), never
                silently dropped.
  refs_max      max number of reference images accepted by edit_id
  mask          True if edit_id accepts `mask_url` (real inpainting)
  timeout_s     poll deadline; poll_s poll interval
  notes         one-line guidance surfaced to the agent by list_models()

Every enum below was read from the fal API schema pages on 2026-09-09:
  fal-ai/gemini-3-pro-image-preview/edit, openai/gpt-image-2/edit,
  bytedance/seedream/v5/pro/edit, fal-ai/bria/background/remove.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

CATALOG_TTL = int(os.environ.get("IMAGE_CATALOG_TTL", "3600"))
_CACHE_PATH = "/tmp/starchild_image_catalog.json"

_ASPECT = ["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"]
_FMT3 = ["png", "jpeg", "webp"]
_GPT_SIZE = ["auto", "square_hd", "square", "portrait_4_3", "portrait_16_9",
             "landscape_4_3", "landscape_16_9"]

BUILTIN: Dict[str, Any] = {
    "version": "2026-09-09",
    "default_generate": "nanopro",
    "default_edit": "nanopro",
    "models": {
        "nano2": {
            "id": "fal-ai/gemini-3.1-flash-image-preview",
            "edit_id": "fal-ai/gemini-3.1-flash-image-preview/edit",
            "status": "default",
            "params": {
                "aspect_ratio": {"type": "enum", "enum": _ASPECT},
                "num_images": {"type": "int", "min": 1, "max": 4},
                "output_format": {"type": "enum", "enum": _FMT3},
                "seed": {"type": "int", "min": 0, "max": 2**32 - 1},
            },
            "refs_max": 4,
            "mask": False,
            "timeout_s": 90, "poll_s": 2,
            "notes": "Fastest/cheapest (~15s). Drafts, composition exploration, quick iterations.",
        },
        "nanopro": {
            "id": "fal-ai/gemini-3-pro-image-preview",
            "edit_id": "fal-ai/gemini-3-pro-image-preview/edit",
            "status": "default",
            "params": {
                "aspect_ratio": {"type": "enum", "enum": _ASPECT},
                "resolution": {"type": "enum", "enum": ["1K", "2K", "4K"]},
                "num_images": {"type": "int", "min": 1, "max": 4},
                "output_format": {"type": "enum", "enum": _FMT3},
                "seed": {"type": "int", "min": 0, "max": 2**32 - 1},
            },
            "refs_max": 6,
            "mask": False,
            "timeout_s": 150, "poll_s": 3,
            "notes": ("Balanced default (~25s). Strong instruction following, multi-reference. "
                      "Output is 1K unless `resolution` is set — pass 2K/4K to keep large sources."),
        },
        "gpt": {
            "id": "openai/gpt-image-2",
            "edit_id": "openai/gpt-image-2/edit",
            "status": "default",
            "params": {
                "image_size": {"type": "enum", "enum": _GPT_SIZE},
                "quality": {"type": "enum", "enum": ["auto", "low", "medium", "high"]},
                "background": {"type": "enum", "enum": ["auto", "transparent", "opaque"]},
                "num_images": {"type": "int", "min": 1, "max": 4},
                "output_format": {"type": "enum", "enum": _FMT3},
            },
            "refs_max": 16,
            "mask": True,
            "timeout_s": 600, "poll_s": 5,
            "notes": ("Highest fidelity, slow (~2 min). ONLY model with a real mask "
                      "(`mask_path`) — use it for region-locked edits; preserves source size."),
        },
        "seedream": {
            "id": None,
            "edit_id": "bytedance/seedream/v5/pro/edit",
            "status": "candidate",
            "params": {
                "image_size": {"type": "enum", "enum": ["square_hd", "square", "portrait_4_3",
                                                        "portrait_16_9", "landscape_4_3",
                                                        "landscape_16_9", "auto_1K", "auto_2K"]},
                "num_images": {"type": "int", "min": 1, "max": 4},
                "output_format": {"type": "enum", "enum": ["png", "jpeg"]},
            },
            "refs_max": 10,
            "mask": False,
            "timeout_s": 180, "poll_s": 3,
            "notes": "Candidate (not auto-selected). Up to 10 reference images; multi-asset composition.",
        },
        "bria-rmbg": {
            "id": None,
            "edit_id": "fal-ai/bria/background/remove",
            "status": "default",
            "params": {},
            "refs_max": 1,
            "mask": False,
            "no_prompt": True,
            "timeout_s": 60, "poll_s": 2,
            "notes": "Dedicated background removal → transparent PNG. No prompt.",
        },
    },
    "vision": {
        # Cheap-first chain for inspect(); override with IMAGE_VISION_MODELS.
        "chain": [
            "google/gemini-3.5-flash-lite",
            "deepseek/deepseek-v4-flash-vision-exp",
            "google/gemma-4-31b-it",
        ],
        "max_tokens": 1200,
    },
}


def _load_remote() -> Optional[Dict[str, Any]]:
    url = os.environ.get("IMAGE_CATALOG_URL", "").strip()
    if not url:
        return None
    try:
        st = os.stat(_CACHE_PATH)
        if time.time() - st.st_mtime < CATALOG_TTL:
            with open(_CACHE_PATH) as f:
                return json.load(f)
    except (OSError, ValueError):
        pass
    try:
        import requests  # local import: catalog must stay importable without network deps
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict) or "models" not in data:
            return None
        tmp = _CACHE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, _CACHE_PATH)
        return data
    except Exception:
        return None


def load() -> Dict[str, Any]:
    """Return the effective catalog (remote if configured and valid, else BUILTIN)."""
    return _load_remote() or BUILTIN


def get_model(alias: str, cat: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return the model entry or raise ValueError with actionable text (fail-closed)."""
    cat = cat or load()
    models = cat["models"]
    if alias not in models:
        raise ValueError(
            f"Unknown model '{alias}'. Available: {', '.join(sorted(models))}. "
            "Call list_models() for capabilities."
        )
    m = models[alias]
    if m.get("status") == "deprecated":
        raise ValueError(f"Model '{alias}' is deprecated. {m.get('notes', '')}".strip())
    return m


def validate_params(alias: str, params: Dict[str, Any],
                    cat: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate caller params against the model spec. Unknown/out-of-range → ValueError.

    Returns a clean dict of only the params to forward upstream.
    """
    m = get_model(alias, cat)
    spec = m.get("params", {})
    clean: Dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        if k not in spec:
            raise ValueError(
                f"Model '{alias}' does not support parameter '{k}'. "
                f"Supported: {', '.join(sorted(spec)) or 'none'}."
            )
        s = spec[k]
        if s["type"] == "enum":
            if v not in s["enum"]:
                raise ValueError(f"'{k}' must be one of {s['enum']} for '{alias}', got {v!r}.")
        elif s["type"] == "int":
            try:
                v = int(v)
            except (TypeError, ValueError):
                raise ValueError(f"'{k}' must be an integer for '{alias}', got {v!r}.")
            if v < s.get("min", v) or v > s.get("max", v):
                raise ValueError(f"'{k}' must be within [{s.get('min')}, {s.get('max')}] for '{alias}'.")
        clean[k] = v
    return clean


def describe(cat: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Agent-facing summary: one line per model plus capability flags."""
    cat = cat or load()
    out = {}
    for alias, m in cat["models"].items():
        out[alias] = {
            "status": m.get("status"),
            "generate": bool(m.get("id")),
            "edit": bool(m.get("edit_id")),
            "mask": bool(m.get("mask")),
            "refs_max": m.get("refs_max"),
            "params": {k: (v.get("enum") or f"int {v.get('min')}-{v.get('max')}")
                       for k, v in m.get("params", {}).items()},
            "notes": m.get("notes", ""),
        }
    return {"catalog_version": cat.get("version"),
            "default_generate": cat.get("default_generate"),
            "default_edit": cat.get("default_edit"),
            "models": out,
            "vision_chain": cat.get("vision", {}).get("chain", [])}
