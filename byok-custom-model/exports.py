"""
BYOK custom-model skill — script-mode exports.

Mirrors the actions of the legacy `custom_models` tool. Functions return
plain dicts so the calling agent can JSON-encode them straight to chat.

Wire model:
  * Read-only operations (list, get, templates, parse_example, list_vendor_models)
    run entirely in this subprocess by importing core.* directly.
  * Mutating operations (add, add_template, remove) write the yaml registry,
    then hit two loopback endpoints to (a) flush the AgentManager cache so
    the next turn re-reads custom_models.yaml and (b) push the secure-input
    SSE event into the user's open chat session so they can submit the
    API key without it ever appearing in chat history.

  Both endpoints live in starchild-clawd/routes/internal_runtime.py and
  enforce client_host in 127.0.0.1/::1 — defense in depth on top of the
  AUTH_WHITELIST entry. We are already loopback (script subprocess inside
  the same container), so no auth headers are required.

Reachability:
  - core.* import: works because /app is on sys.path[1] in subprocesses
    (Docker base image installs the package into /app and Python pre-pends
    site-packages dirs that include it). If running locally where the repo
    lives at /data/workspace/starchild-clawd, we fall back to that path.
  - http://localhost:8000: the FastAPI port the agent runs on (PORT env
    overrides; default 8000). Auto-detected at call time.

Why this pattern (skill → loopback HTTP) instead of in-process:
  Tools used to call flush_agent_cache and streaming.action_request directly
  on in-process singletons. That broke the moment we wanted to remove the
  tool from the prompt schema (saves ~500-800 tokens/turn) — a skill script
  is a separate process with no access to those singletons. The two endpoints
  bridge the gap with a sub-millisecond round-trip on loopback.
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------
# sys.path bootstrap — find the starchild-clawd package
# --------------------------------------------------------------------------

def _bootstrap_clawd_path() -> None:
    """Ensure `core.custom_models` is importable from this subprocess.

    Order of search:
      1. STARCHILD_CLAWD_DIR env var (explicit override)
      2. /app                          (production Docker layout)
      3. /data/workspace/starchild-clawd (dev/leon's container layout)

    Stops at the first directory that contains core/custom_models.py.
    """
    candidates = []
    env_override = os.environ.get("STARCHILD_CLAWD_DIR")
    if env_override:
        candidates.append(env_override)
    candidates.extend(["/app", "/data/workspace/starchild-clawd"])
    for cand in candidates:
        if os.path.exists(os.path.join(cand, "core", "custom_models.py")):
            if cand not in sys.path:
                sys.path.insert(0, cand)
            return
    # No fallback works — let the import errors surface naturally below.

_bootstrap_clawd_path()

from core.custom_models import (  # noqa: E402
    CustomModelRegistry,
    CustomModelValidationError,
    build_custom_model,
    generate_api_key_env,
    parse_api_example,
    validate_base_url,
    validate_capabilities,
    validate_param_policy,
    validate_request_params,
    validate_thinking_mode,
    validate_upstream_model,
)
from core.custom_models_templates import (  # noqa: E402
    VENDOR_TEMPLATES,
    fetch_vendor_models,
    get_template,
    list_templates,
)


# --------------------------------------------------------------------------
# Loopback helpers (cache flush + secure-input dispatch)
# --------------------------------------------------------------------------

def _api_base() -> str:
    """Resolve the local FastAPI base URL.

    Production: PORT env is set by Fly. Local dev: defaults to 8000.
    """
    return f"http://localhost:{os.environ.get('PORT', '8000')}"


def _loopback_post(path: str, body: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
    """POST to a loopback /internal/* endpoint. Returns parsed JSON or {}.

    Best-effort: failures here never raise — they just return an `ok=False`
    diagnostic dict, which the caller folds into its own response. We don't
    want a transient cache-flush hiccup to mask a successful registry write.
    """
    import urllib.request
    import urllib.error
    url = _api_base() + path
    data = json.dumps(body or {}).encode()
    headers = {"Content-Type": "application/json"}
    # The agent loop injects STARCHILD_INTERNAL_SECRET into every bash
    # subprocess it spawns. The loopback endpoints require that header
    # to fail closed against processes the agent didn't start.
    _secret = os.environ.get("STARCHILD_INTERNAL_SECRET", "")
    if _secret:
        headers["X-Internal-Secret"] = _secret
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"ok": False, "reason": "non_json_response", "raw": raw[:200]}
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": f"http_{e.code}", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "reason": f"{type(e).__name__}", "detail": str(e)}


def _flush_cache() -> Dict[str, Any]:
    """Force AgentManager to rebuild providers next call (so new model appears)."""
    return _loopback_post("/internal/runtime/flush_agent_cache", {})


def _dispatch_env_input(*, key_env: str, key_label: str, model_id: str, base_url: str) -> Dict[str, Any]:
    """Pop the secure-input UI for an API key.

    Mirrors the action_request payload the in-process tool used to emit.
    The session_id comes from STARCHILD_TOOL_CALLER_ID which the agent loop
    injects into every subprocess env (see tools/bash.py subprocess_env).
    Format: 'chat:agent:main:thread:{user_id}:{thread_id}/tool:bash/use:{tool_use_id}'
    We extract the chat session prefix so the SSE event lands in the right stream.
    """
    caller = os.environ.get("STARCHILD_TOOL_CALLER_ID", "")
    session_id = ""
    if caller.startswith("chat:"):
        # 'chat:agent:main:thread:NNNN:HASH/tool:bash/use:XXX' → 'agent:main:thread:NNNN:HASH'
        session_id = caller[len("chat:"):].split("/", 1)[0]
    if not session_id:
        return {"ok": False, "reason": "no_session_id_in_caller_env"}

    action_id = f"custom_model_{int(time.time())}_{os.urandom(3).hex()}"
    return _loopback_post(
        "/internal/streaming/dispatch_action_request",
        {
            "session_id": session_id,
            "action": "env_input",
            "title": f"API key for {model_id}",
            "description": (
                f"Provide the API key for {model_id} (endpoint: {base_url}). "
                f"Saved to workspace/.env as {key_env} — never shown in chat."
            ),
            "payload": {
                "env_vars": [{
                    "key": key_env,
                    "label": key_label,
                    "required": True,
                }],
            },
            "require_signature": False,
            "action_id": action_id,
        },
    )


# --------------------------------------------------------------------------
# Public API — read operations
# --------------------------------------------------------------------------

def templates() -> Dict[str, Any]:
    """List the curated vendor presets for one-click registration.

    Each entry has: vendor id, label, base_url, default model, and supported
    capabilities. Use these as the first stop — the 9 known vendors should
    always go through add_template(vendor=...) rather than raw add().
    """
    return {
        "ok": True,
        "count": len(VENDOR_TEMPLATES),
        "templates": list_templates(),
        "note": (
            "Call add_template(vendor=<id>) to register one. The user only "
            "needs to provide the API key via the secure prompt."
        ),
    }


def list_models() -> Dict[str, Any]:
    """List all custom models currently registered in custom_models.yaml."""
    items = []
    for cm in CustomModelRegistry.list():
        items.append({
            "model_id": cm.id,
            "name": cm.name,
            "upstream_model": cm.upstream_model,
            "base_url": cm.base_url,
            "wire": cm.wire,
            "api_key_env": cm.api_key_env,
            "api_key_set": bool(os.environ.get(cm.api_key_env)),
            "thinking_mode": cm.thinking_mode,
            "request_params": cm.request_params,
            "capabilities": cm.capabilities,
            "param_policy": cm.param_policy,
        })
    return {
        "ok": True,
        "count": len(items),
        "models": items,
        "note": (
            "Entries with api_key_set=false need the key populated via the "
            "secure input flow before first use."
        ),
    }


def get(model_id: str) -> Dict[str, Any]:
    """Inspect a single registered custom model entry."""
    if not model_id:
        return {"ok": False, "error": "'model_id' is required"}
    cm = CustomModelRegistry.get(model_id)
    if not cm:
        return {"ok": False, "error": f"No custom model with id={model_id!r}"}
    return {
        "ok": True,
        "model_id": cm.id,
        "name": cm.name,
        "upstream_model": cm.upstream_model,
        "base_url": cm.base_url,
        "wire": cm.wire,
        "api_key_env": cm.api_key_env,
        "api_key_set": bool(os.environ.get(cm.api_key_env)),
        "thinking_mode": cm.thinking_mode,
        "request_params": cm.request_params,
        "capabilities": cm.capabilities,
        "param_policy": cm.param_policy,
    }


def parse_example(api_example: str) -> Dict[str, Any]:
    """Parse a vendor docs API example into a safe registration draft.

    The user is expected to paste a curl/Python/JS sample WITHOUT a real key.
    Output draft has base_url, upstream_model, wire, request_params auto-detected.
    Caller then runs `add(...)` with the vetted fields.
    """
    if not api_example:
        return {"ok": False, "error": "'api_example' is required"}
    draft = parse_api_example(api_example)
    return {
        "ok": True,
        "draft": draft,
        "note": (
            "Review the draft, then call add(...) with the vetted fields. "
            "The API key is NEVER passed here — secure input handles it."
        ),
    }


def list_vendor_models(vendor: str) -> Dict[str, Any]:
    """Fetch a vendor's live /models catalog with capability + pricing.

    Discovery flow: user asks 'what Venice models support vision?' → call
    this → filter the result client-side → user picks → add_template(...).
    Auth-required vendors (OpenAI, Gemini) need the key already in .env.
    """
    if not vendor:
        return {"ok": False, "error": "'vendor' is required"}
    tpl = get_template(vendor)
    if tpl is None:
        return {"ok": False, "error": f"No curated template for vendor={vendor!r}"}
    if tpl.model_discovery is None:
        return {"ok": False, "error": f"Vendor {vendor!r} has no live /models endpoint configured"}

    api_key: Optional[str] = None
    if tpl.model_discovery.auth_required:
        preferred_env = generate_api_key_env(tpl.default_model().upstream_model, tpl.base_url)
        api_key = os.environ.get(preferred_env)
        if not api_key:
            for fallback in (f"{vendor.upper()}_API_KEY", f"{vendor.upper()}_KEY"):
                api_key = os.environ.get(fallback)
                if api_key:
                    break

    result = fetch_vendor_models(tpl, api_key=api_key)
    if not result["ok"]:
        hint = ""
        if result.get("skipped_auth"):
            hint = (
                f" Run add_template(vendor='{vendor}') first to populate the "
                f"API key, then retry list_vendor_models."
            )
        return {
            "ok": False,
            "error": f"Failed to fetch live model list: {result['error']}{hint}",
            "url": result.get("url"),
            "skipped_auth": result.get("skipped_auth"),
        }

    installed_ids = {m.upstream_model for m in tpl.models}
    return {
        "ok": True,
        "vendor": vendor,
        "label": tpl.label,
        "url": result["url"],
        "count": result["count"],
        "in_curated_template": sorted(installed_ids),
        "models": result["models"],
        "note": (
            "Each model entry exposes: upstream_model, name, context_tokens, "
            "capabilities (vision, function_calling, reasoning, e2ee, "
            "web_search, tee), pricing (input_usd / output_usd per 1M tokens), "
            "privacy tier. To register one, call add_template(vendor=..., "
            "upstream_model=...)."
        ),
    }


# --------------------------------------------------------------------------
# Public API — write operations
# --------------------------------------------------------------------------

def add(
    upstream_model: str,
    base_url: str,
    *,
    name: Optional[str] = None,
    wire: Optional[str] = None,
    thinking_mode: Optional[str] = None,
    request_params: Optional[Dict[str, Dict[str, Any]]] = None,
    capabilities: Optional[Dict[str, Any]] = None,
    param_policy: Optional[Dict[str, Any]] = None,
    supports_image: Optional[bool] = None,
    supports_tools: Optional[bool] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Register a new custom model from explicit fields.

    Use this AFTER parse_example() has produced a vetted draft. For the 9
    curated vendors, prefer add_template(vendor=...) instead — it auto-fills
    everything from the registry.

    Side effects (in order):
      1. Validate every field — raises CustomModelValidationError on bad input.
      2. Write the entry to workspace/config/custom_models.yaml.
      3. Flush the agent cache so the next turn picks up the new model.
      4. If the API key env var is not yet set, dispatch the secure-input
         popup so the user can submit it without it appearing in chat.

    Step 2 happens BEFORE step 4 on purpose: if the user dismisses the popup,
    the entry still survives in the registry so they can retry the key later
    via the same flow.
    """
    if not upstream_model:
        return {"ok": False, "error": "'upstream_model' is required"}
    if not base_url:
        return {"ok": False, "error": "'base_url' is required"}

    try:
        cm = build_custom_model(
            upstream_model=validate_upstream_model(upstream_model),
            base_url=validate_base_url(base_url),
            name=name,
            wire=wire,
            thinking_mode=validate_thinking_mode(thinking_mode),
            request_params=validate_request_params(request_params),
            capabilities=validate_capabilities(capabilities),
            param_policy=validate_param_policy(param_policy),
            supports_image=supports_image,
            supports_tools=supports_tools,
            max_tokens=max_tokens,
        )
    except CustomModelValidationError as e:
        return {"ok": False, "error": f"validation: {e}"}

    CustomModelRegistry.upsert(cm)
    flush_result = _flush_cache()

    key_env = cm.api_key_env
    key_already_set = bool(os.environ.get(key_env))
    dispatch_result: Optional[Dict[str, Any]] = None
    if not key_already_set:
        dispatch_result = _dispatch_env_input(
            key_env=key_env,
            key_label=f"{cm.name} API Key",
            model_id=cm.id,
            base_url=cm.base_url,
        )

    return {
        "ok": True,
        "status": "registered",
        "model_id": cm.id,
        "name": cm.name,
        "upstream_model": cm.upstream_model,
        "base_url": cm.base_url,
        "wire": cm.wire,
        "api_key_env": key_env,
        "api_key_set": key_already_set,
        "thinking_mode": cm.thinking_mode,
        "request_params": cm.request_params,
        "capabilities": cm.capabilities,
        "param_policy": cm.param_policy,
        "action_request_sent": bool(dispatch_result and dispatch_result.get("delivered")),
        "dispatch_diagnostic": dispatch_result,
        "cache_flush": flush_result,
        "note": (
            "Entry registered. "
            + (
                "API key already present in .env — model is ready to use."
                if key_already_set
                else "Waiting for user to submit the API key via the secure input prompt."
            )
            + f" Switch to this model by selecting {cm.id!r} in the selector."
        ),
    }


def add_template(
    vendor: str,
    *,
    upstream_model: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """One-click vendor registration from a curated preset.

    Caller passes only `vendor` (e.g. 'qwen', 'deepseek', 'venice'). All
    other fields come from VENDOR_TEMPLATES. Optional `upstream_model`
    overrides the default model id within the same vendor.
    """
    if not vendor:
        return {"ok": False, "error": "'vendor' is required"}

    tpl = get_template(vendor)
    if tpl is None:
        return {
            "ok": False,
            "error": f"No curated template for vendor={vendor!r}",
            "hint": "Call templates() to list known vendors, or add(...) for a fully custom entry.",
        }

    chosen_upstream: Optional[str] = None
    if upstream_model:
        curated = [m.upstream_model for m in tpl.models]
        if upstream_model not in curated and tpl.model_discovery is None:
            return {
                "ok": False,
                "error": (
                    f"upstream_model={upstream_model!r} is not part of the "
                    f"{tpl.label} template. Allowed: {curated}"
                ),
            }
        chosen_upstream = upstream_model

    kwargs = tpl.build_kwargs(upstream_override=chosen_upstream)
    if name:
        kwargs["name"] = name

    return add(
        upstream_model=kwargs["upstream_model"],
        base_url=kwargs["base_url"],
        name=kwargs.get("name"),
        wire=kwargs.get("wire"),
        thinking_mode=kwargs.get("thinking_mode"),
        request_params=kwargs.get("request_params"),
        capabilities=kwargs.get("capabilities"),
        supports_image=kwargs.get("supports_image"),
        supports_tools=kwargs.get("supports_tools"),
        max_tokens=kwargs.get("max_tokens"),
    )


def remove(model_id: str) -> Dict[str, Any]:
    """Delete a registered custom model entry.

    Note: the API key env var is intentionally NOT removed from .env.
    Remove it manually if you no longer need it for any other model.
    """
    if not model_id:
        return {"ok": False, "error": "'model_id' is required"}
    removed = CustomModelRegistry.delete(model_id)
    if not removed:
        return {"ok": False, "error": f"No custom model with id={model_id!r}"}
    flush_result = _flush_cache()
    return {
        "ok": True,
        "status": "removed",
        "model_id": model_id,
        "cache_flush": flush_result,
        "note": (
            "Entry removed from custom_models.yaml. The env-var key is "
            "intentionally NOT deleted from .env — remove it manually if you "
            "no longer need it."
        ),
    }
