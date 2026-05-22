"""xAI Grok OAuth skill — script-mode exports.

Mirrors skills/chatgpt-codex-onboarding/exports.py:
    status | start | poll | logout | refresh | models

File-backed pending state:
    Each script subprocess starts fresh, so the DeviceCodePrompt from start()
    must be persisted to workspace/.xai_oauth_pending.json before poll() can
    resume it. Mirrors the codex skill exactly.

Wire model:
  - Read paths (status, models): in-process, no HTTP needed
  - Write paths (start, poll, logout, refresh): touch on-disk credential via
    core.xai_grok.store, then call /internal/runtime/flush_agent_cache on
    loopback so AgentManager rebuilds providers next turn
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time
from typing import Any, Dict, Optional


# --------------------------------------------------------------------------
# sys.path bootstrap (same as codex skill)
# --------------------------------------------------------------------------

def _bootstrap_clawd_path() -> None:
    candidates = []
    env_override = os.environ.get("STARCHILD_CLAWD_DIR")
    if env_override:
        candidates.append(env_override)
    candidates.extend(["/app", "/data/workspace/starchild-clawd"])
    for cand in candidates:
        if os.path.exists(os.path.join(cand, "core", "xai_grok", "__init__.py")):
            if cand not in sys.path:
                sys.path.insert(0, cand)
            return

_bootstrap_clawd_path()

from core.xai_grok import (  # noqa: E402
    AccountAccessDenied,
    DeviceCodePrompt,
    DeviceCodeTimeout,
    OAuthState,
    ReauthRequired,
    VERIFY_URL,
    XaiGrokOAuthError,
    classify_state,
    delete_credential,
    fetch_models_from_api,
    load_credential,
    poll_authorization,
    refresh_access_token,
    request_device_code,
    resolve_xai_models,
    save_credential,
)


# --------------------------------------------------------------------------
# Cache-flush helper
# --------------------------------------------------------------------------

def _api_base() -> str:
    return f"http://localhost:{os.environ.get('PORT', '8000')}"


def _flush_cache() -> Dict[str, Any]:
    """Force AgentManager to rebuild providers next call."""
    import urllib.request
    import urllib.error
    url = _api_base() + "/internal/runtime/flush_agent_cache"
    req = urllib.request.Request(
        url, data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            try:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                return {"ok": False, "reason": "non_json_response"}
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": f"http_{e.code}", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "reason": type(e).__name__, "detail": str(e)}


# --------------------------------------------------------------------------
# File-backed pending-flow store
# --------------------------------------------------------------------------

def _pending_path() -> str:
    workspace = os.environ.get("WORKSPACE_DIR", "/data/workspace")
    return os.path.join(workspace, ".xai_oauth_pending.json")


def _save_pending(prompt: DeviceCodePrompt) -> None:
    expires_at = time.time() + prompt.expires_in_seconds
    payload = {
        "device_code": prompt.device_code,
        "user_code": prompt.user_code,
        "verification_url": prompt.verification_url,
        "verification_url_with_code": prompt.verification_url_with_code,
        "interval_seconds": prompt.interval_seconds,
        "expires_at": expires_at,
    }
    path = _pending_path()
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".oauth_pending_")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(payload, f)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _load_pending(pending_id: Optional[str]) -> Optional[DeviceCodePrompt]:
    path = _pending_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if raw.get("expires_at", 0) < time.time():
        try:
            os.unlink(path)
        except OSError:
            pass
        return None
    if pending_id and raw.get("user_code") != pending_id:
        return None
    expires_in_seconds = max(1, int(raw.get("expires_at", 0) - time.time()))
    return DeviceCodePrompt(
        device_code=raw["device_code"],
        user_code=raw["user_code"],
        verification_url=raw["verification_url"],
        verification_url_with_code=raw["verification_url_with_code"],
        interval_seconds=int(raw.get("interval_seconds", 5)),
        expires_in_seconds=expires_in_seconds,
    )


def _clear_pending() -> None:
    try:
        os.unlink(_pending_path())
    except OSError:
        pass


# --------------------------------------------------------------------------
# Tiny asyncio runner
# --------------------------------------------------------------------------

def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def status() -> Dict[str, Any]:
    """Inspect the current OAuth credential state."""
    cred = load_credential()
    st = classify_state(cred)
    if cred is None:
        return {
            "ok": True,
            "state": st.value,
            "connected": False,
            "verification_url_root": VERIFY_URL,
            "hint": "Not connected. Run start() to log in with your SuperGrok / X Premium subscription.",
        }
    now = int(time.time())
    slugs = resolve_xai_models(cached_models=cred.available_models)
    return {
        "ok": True,
        "state": st.value,
        "connected": st in {OAuthState.CONNECTED, OAuthState.EXPIRING},
        "email": cred.email,
        "account_id": cred.account_id,
        "expires_at": cred.expires_at,
        "expires_in_seconds": max(0, cred.expires_at - now),
        "updated_at": cred.updated_at,
        "models_count": len(slugs),
        "models_fetched_at": cred.models_fetched_at,
        "default_model_id": f"xai-grok/{slugs[0]}" if slugs else None,
        "available_models": [f"xai-grok/{s}" for s in slugs],
    }


def start() -> Dict[str, Any]:
    """Step 1: ask xAI for a device-code prompt."""
    try:
        prompt = _run(request_device_code())
    except XaiGrokOAuthError as e:
        return {"ok": False, "error": str(e)}

    _save_pending(prompt)
    return {
        "ok": True,
        "status": "pending",
        "pending_id": prompt.user_code,
        "user_code": prompt.user_code,
        "verification_url": prompt.verification_url,
        "verification_url_with_code": prompt.verification_url_with_code,
        "interval_seconds": prompt.interval_seconds,
        "expires_in_seconds": prompt.expires_in_seconds,
        "instructions": (
            f"Open {prompt.verification_url_with_code} in a browser already "
            f"logged in to your xAI / SuperGrok account, click Approve. "
            f"User code is pre-filled ({prompt.user_code}) — no need to type it. "
            "After approving, ask the agent to poll."
        ),
    }


def poll(pending_id: Optional[str] = None) -> Dict[str, Any]:
    """Step 2: poll xAI to see if the user finished authorizing.

    Returns:
      - status='pending': call poll again later
      - status='connected': credential saved, model now selectable
      - ok=false with error mentioning access_denied: account gated by xAI
        (suggest BYOK API key fallback)
      - ok=false with expired: device code timed out (15 min); restart with start()
    """
    prompt = _load_pending(pending_id)
    if prompt is None:
        return {
            "ok": False,
            "error": "Unknown or expired pending flow; restart with start().",
            "hint": "If the user hasn't run start() yet, do that first.",
        }

    try:
        cred = _run(poll_authorization(
            prompt, deadline=time.time() + 8.0
        ))
    except DeviceCodeTimeout:
        # xAI returned authorization_pending several times within our short
        # poll window — keep the prompt for next call.
        return {
            "ok": True,
            "status": "pending",
            "message": "Still waiting for the user to authorize. Call poll again.",
        }
    except AccountAccessDenied as e:
        _clear_pending()
        return {
            "ok": False,
            "error": f"access_denied: {e}",
            "hint": (
                "xAI rejected the OAuth grant. This is usually an account-level "
                "gate (xAI does not whitelist every SuperGrok account for "
                "third-party OAuth). Confirm subscription is active, try the "
                "verification URL in your already-logged-in browser, or fall "
                "back to BYOK API key via the byok-custom-model skill "
                "(key from https://console.x.ai)."
            ),
        }
    except XaiGrokOAuthError as e:
        _clear_pending()
        return {"ok": False, "error": str(e)}

    _clear_pending()

    # Warm models cache inline — best effort, never blocks connection.
    try:
        _run(_refresh_models_cache(cred))
    except Exception:
        pass

    cred = load_credential() or cred
    slugs = resolve_xai_models(cached_models=cred.available_models)
    flush_result = _flush_cache()
    return {
        "ok": True,
        "status": "connected",
        "email": cred.email,
        "account_id": cred.account_id,
        "expires_at": cred.expires_at,
        "models_count": len(slugs),
        "default_model_id": f"xai-grok/{slugs[0]}" if slugs else None,
        "available_models": [f"xai-grok/{s}" for s in slugs],
        "cache_flush": flush_result,
        "next_step": (
            "Connection successful. Switch with "
            f"`/model xai-grok/{slugs[0] if slugs else 'grok-4.3'}` "
            "or use the model picker."
        ),
    }


def logout() -> Dict[str, Any]:
    """Disconnect — delete the on-disk credential file and flush cache."""
    existed = delete_credential()
    flush_result = _flush_cache()
    return {
        "ok": True,
        "status": "disconnected" if existed else "not_connected",
        "removed": existed,
        "cache_flush": flush_result,
    }


def refresh() -> Dict[str, Any]:
    """Force-refresh the access token. Normally automatic — debug only."""
    cred = load_credential()
    if cred is None:
        return {"ok": False, "error": "Not connected; nothing to refresh."}
    try:
        updated = _run(refresh_access_token(cred))
    except ReauthRequired as e:
        return {"ok": False, "error": f"reauth required: {e}",
                "hint": "Run logout() then start() to re-authenticate."}
    except Exception as e:
        return {"ok": False, "error": f"refresh failed: {e}"}
    return {
        "ok": True,
        "status": "refreshed",
        "expires_at": updated.expires_at,
        "expires_in_seconds": max(0, updated.expires_at - int(time.time())),
    }


def models(force: bool = False) -> Dict[str, Any]:
    """List the OAuth subscription's available models.

    Cached on the credential file; pass force=True to bypass the TTL.
    """
    cred = load_credential()
    if cred is None:
        return {"ok": False, "error": "Not connected."}
    if force or not cred.available_models:
        try:
            api_models = _run(_refresh_models_cache(cred))
        except Exception as e:
            return {"ok": False, "error": f"fetch failed: {e}"}
    else:
        api_models = cred.available_models
    slugs = resolve_xai_models(cached_models=api_models)
    return {
        "ok": True,
        "source": "api" if force else "cache",
        "count": len(slugs),
        "available_models": [f"xai-grok/{s}" for s in slugs],
        "fetched_at": cred.models_fetched_at,
    }


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------

async def _refresh_models_cache(cred):
    api_models = await fetch_models_from_api(cred.access_token)
    if not api_models:
        return []
    cred.available_models = list(api_models)
    cred.models_fetched_at = int(time.time())
    save_credential(cred)
    return api_models
