"""Cost tracking helper for skill subprocesses.

Skills that call sc-proxy via plain `requests` need to:
  1. Tag every paid call with a SC-CALLER-ID that ties it back to the user
     turn that triggered the skill (so the agent's per-turn cost summary
     shows the cost in the right cost card).
  2. After each call, parse the sc-proxy response headers
     (`X-Credits-Used`, `X-Credits-Api-Type`) and write a row to the cost
     ledger that the agent reads back when it builds the SSE
     `cost_summary` event.

This file is intentionally zero-dependency (stdlib only) so it can be
dropped into any skill folder without coupling to starchild-clawd internals.

Env vars consumed (set by the agent before dispatching the bash subprocess):
  - STARCHILD_TOOL_CALLER_ID  — opaque tag for the current tool call
  - STARCHILD_USER_TURN_ID    — uuid of the current user turn
  - STARCHILD_COST_LEDGER_DIR — optional override for ledger directory

When env vars are absent (e.g. running the script outside an agent), the
helpers degrade gracefully: caller-id falls back to a synthetic string so
the call still goes through, and ledger writes still happen for audit but
the user-turn reader will skip them.
"""
from __future__ import annotations

import fcntl
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


_DEFAULT_LEDGER_DIR = "/data/.starchild/cost_ledger"

# Allowlisted request payload keys we forward into the ledger row's
# `details` field. MUST stay in sync with starchild-clawd's
# core/http_client._record_cost_to_ledger allowlist — anything not in
# that allowlist won't be picked up by the agent and won't render in
# the frontend cost card.
_PAYLOAD_ALLOWLIST = (
    # Identity
    "model", "provider",
    # Image geometry
    "aspect_ratio", "quality", "resolution", "image_size", "size",
    # Video / motion
    "duration", "duration_s", "fps", "motion_strength",
    # Quantity
    "n", "count",
    # Generation knobs
    "seed", "steps", "guidance_scale", "cfg_scale", "strength",
    "scheduler", "sampler",
    # Reference / mode hints
    "image_to_image", "image_to_video", "use_reference", "reference_count",
)


def caller_headers(extra: Optional[Dict[str, str]] = None,
                   tool_default: str = "skill") -> Dict[str, str]:
    """Return an HTTP-headers dict with SC-CALLER-ID filled in.

    Resolution order:
      1. `extra["SC-CALLER-ID"]` (case-insensitive) — caller wins.
      2. STARCHILD_TOOL_CALLER_ID env (set by the agent)
      3. Synthetic `f"{tool_default}:{int(time.time())}"` — tags the call so
         charges are attributable to *some* identifier even when the agent
         didn't inject one (standalone CLI runs, tests, cron).
    """
    merged: Dict[str, str] = dict(extra or {})
    has_caller = any(k.lower() == "sc-caller-id" for k in merged)
    if not has_caller:
        cid = os.environ.get("STARCHILD_TOOL_CALLER_ID") \
            or f"{tool_default}:{int(time.time())}"
        merged["SC-CALLER-ID"] = cid
    return merged


def record_response(response,
                    request_url: str,
                    request_payload: Optional[Dict[str, Any]] = None,
                    api_type_hint: Optional[str] = None) -> None:
    """Inspect a sc-proxy response and append a ledger row when paid.

    Best-effort. Silently no-ops when:
      - response carries no X-Credits-Used / X-Credits-Api-Type
      - cost is 0 or unparseable
      - file write fails
    Never raises — must not break a real request flow.
    """
    try:
        headers = getattr(response, "headers", None) or {}
        used = headers.get("X-Credits-Used") or headers.get("x-credits-used")
        api_type = (headers.get("X-Credits-Api-Type")
                    or headers.get("x-credits-api-type")
                    or api_type_hint)
        if not used or not api_type:
            return
        try:
            cost_f = float(used)
        except (TypeError, ValueError):
            return
        if cost_f <= 0:
            return

        turn_id = os.environ.get("STARCHILD_USER_TURN_ID") or ""
        caller_id = os.environ.get("STARCHILD_TOOL_CALLER_ID") or ""

        host = ""
        try:
            host = urlparse(request_url).netloc or ""
        except Exception:
            pass

        details: Dict[str, Any] = {}
        if isinstance(request_payload, dict):
            for k in _PAYLOAD_ALLOWLIST:
                v = request_payload.get(k)
                if v not in (None, "", []):
                    details[k] = v

        # fal.ai puts the model in the URL path, not the body.
        if "model" not in details and api_type == "falai":
            try:
                path = urlparse(request_url).path or ""
                model_path = path.lstrip("/")
                if "/requests/" in model_path:
                    model_path = model_path.split("/requests/", 1)[0]
                if model_path and not model_path.startswith("requests/"):
                    details["model"] = model_path
                    details["provider"] = "fal"
            except Exception:
                pass

        _append_ledger(
            turn_id=turn_id,
            caller_id=caller_id,
            api_type=api_type,
            cost_usd=cost_f,
            url_host=host,
            details=details or None,
        )
    except Exception:
        # Never let cost tracking break the actual request.
        pass


def _ledger_dir() -> Path:
    base = os.environ.get("STARCHILD_COST_LEDGER_DIR") or _DEFAULT_LEDGER_DIR
    p = Path(base)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        p = Path("/tmp/starchild_cost_ledger")
        p.mkdir(parents=True, exist_ok=True)
    return p


def _today_path() -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _ledger_dir() / f"{today}.jsonl"


def _derive_tool(caller_id: str, api_type: str) -> str:
    """Match starchild-clawd's _derive_tool_from_caller fallback."""
    if not caller_id:
        return api_type or "unknown"
    # chat:{sid}/tool:{name} → name
    if "/tool:" in caller_id:
        return caller_id.rsplit("/tool:", 1)[-1] or api_type
    # skill:{name} | job:{id} | video:{ts}
    head = caller_id.split(":", 1)[0]
    return head or api_type or "unknown"


def _append_ledger(*, turn_id: str, caller_id: str, api_type: str,
                   cost_usd: float, url_host: str,
                   details: Optional[Dict[str, Any]]) -> None:
    row = {
        "ts": round(time.time(), 3),
        "turn_id": turn_id,
        "caller_id": caller_id,
        "tool": _derive_tool(caller_id, api_type),
        "api_type": api_type or "unknown",
        "cost_usd": round(cost_usd, 8),
        "url_host": url_host or "",
    }
    if details:
        row["details"] = details

    line = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
    path = _today_path()
    try:
        with open(path, "ab") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            except OSError:
                pass
            try:
                f.write(line.encode("utf-8"))
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            finally:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
    except OSError:
        pass
