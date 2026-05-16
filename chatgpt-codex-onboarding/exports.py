"""
ChatGPT / Codex OAuth skill — script-mode exports.

Mirrors the actions of the legacy `openai_oauth` tool:
  status | start | poll | logout | refresh | models | usage

Critical migration detail — file-backed pending state:
  The in-process tool kept device-code flows in a module-global dict
  (`_PENDING_FLOWS`). That works because `start` and `poll` ran in the same
  process. As a script subprocess we get spawned fresh for each call, so the
  dict is empty on `poll`. We persist the prompt to
  workspace/.openai_oauth_pending.json instead. Fields stored:
    - device_auth_id  — opaque, server-side flow id
    - user_code       — also used as `pending_id` in the legacy API
    - verification_url, verification_url_with_code
    - interval_seconds
    - expires_at      — absolute epoch seconds; poll() rejects expired entries

  The credential token itself stays in the existing CodexCredential file
  managed by core.openai_codex.store — we DO NOT touch its layout.

Wire model:
  - Read paths (status, models, usage): all in-process, no HTTP needed.
  - Write paths (start, poll, logout, refresh): may touch on-disk credential
    via core.openai_codex.store, then call /internal/runtime/flush_agent_cache
    on loopback so the AgentManager rebuilds providers next turn.
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
# sys.path bootstrap (same as byok-custom-model)
# --------------------------------------------------------------------------

def _bootstrap_clawd_path() -> None:
    candidates = []
    env_override = os.environ.get("STARCHILD_CLAWD_DIR")
    if env_override:
        candidates.append(env_override)
    candidates.extend(["/app", "/data/workspace/starchild-clawd"])
    for cand in candidates:
        if os.path.exists(os.path.join(cand, "core", "openai_codex", "__init__.py")):
            if cand not in sys.path:
                sys.path.insert(0, cand)
            return

_bootstrap_clawd_path()

from core.openai_codex import (  # noqa: E402
    OpenAICodexOAuthError,
    OAuthState,
    classify_state,
    delete_credential,
    exchange_authorization_code,
    load_credential,
    refresh_access_token,
    request_device_code,
)
from core.openai_codex.oauth import (  # noqa: E402
    DeviceCodePrompt,
    DeviceCodeTimeout,
    poll_authorization_code,
)
from core.openai_codex.protocol import VERIFY_URL  # noqa: E402
from core.openai_codex.models import (  # noqa: E402
    fetch_models_from_api,
    resolve_codex_models,
)
from core.openai_codex.usage import UsageSnapshot, fetch_account_usage  # noqa: E402
from core.openai_codex.store import save_credential  # noqa: E402


# --------------------------------------------------------------------------
# Loopback cache flush (same pattern as byok-custom-model)
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
    """Where we persist the device-code prompt between start() and poll()."""
    workspace = os.environ.get("WORKSPACE_DIR", "/data/workspace")
    return os.path.join(workspace, ".openai_oauth_pending.json")


def _save_pending(prompt: DeviceCodePrompt) -> None:
    """Atomically persist a DeviceCodePrompt so a later poll() can resume it.

    Atomic write protects against a partial file if the subprocess is killed
    mid-write. The OS-level rename(2) is atomic on POSIX filesystems.
    """
    expires_at = time.time() + prompt.expires_in_seconds
    payload = {
        "device_auth_id": prompt.device_auth_id,
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
    """Resurrect a DeviceCodePrompt from disk; None if missing/expired/wrong id.

    `pending_id` is the user_code (the same one shown to the user). When
    explicitly provided we cross-check it; that catches the rare case where
    the user runs start() twice before poll() and we want to be sure we're
    polling the right flow.
    """
    path = _pending_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if raw.get("expires_at", 0) < time.time():
        # Stale — clean it up so we don't keep serving an expired prompt.
        try:
            os.unlink(path)
        except OSError:
            pass
        return None
    if pending_id and raw.get("user_code") != pending_id:
        return None
    expires_in_seconds = max(1, int(raw.get("expires_at", 0) - time.time()))
    return DeviceCodePrompt(
        device_auth_id=raw["device_auth_id"],
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
# Tiny asyncio runner (so callers don't have to learn await)
# --------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine to completion. Each call gets its own event loop."""
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
            "hint": "Not connected. Run start() to log in.",
        }
    now = int(time.time())
    slugs = resolve_codex_models(cached_models=cred.available_models)
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
        "default_model_id": f"openai-codex/{slugs[0]}" if slugs else None,
        "available_models": [f"openai-codex/{s}" for s in slugs],
        "usage": cred.account_usage,
        "usage_fetched_at": (cred.account_usage or {}).get("fetched_at"),
    }


def start() -> Dict[str, Any]:
    """Step 1: ask OpenAI for a device-code prompt.

    Returns the verification URL + user code that the user pastes into a
    browser. The prompt is persisted to disk so the next subprocess can
    poll() it.
    """
    try:
        prompt = _run(request_device_code())
    except OpenAICodexOAuthError as e:
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
            f"Open {prompt.verification_url} in a browser, log in to your "
            f"ChatGPT/Codex account, and enter the user code: {prompt.user_code}. "
            "After approving, ask the agent to poll."
        ),
    }


def poll(pending_id: Optional[str] = None) -> Dict[str, Any]:
    """Step 2: poll OpenAI to see if the user finished authorizing.

    The pending_id is the user_code returned from start(); we cross-check it
    against the persisted state so two interleaved start() calls don't get
    crossed. Calling poll() with no pending_id falls back to the most recent
    persisted prompt — which is what callers usually want.

    Returns:
      - status='pending': call poll again later (user hasn't approved yet)
      - status='connected': credential saved, default model now selectable
      - ok=false: flow expired or vendor returned an error; restart with start()
    """
    prompt = _load_pending(pending_id)
    if prompt is None:
        return {
            "ok": False,
            "error": "Unknown or expired pending flow; restart with start().",
            "hint": "If the user hasn't run start() yet, do that first.",
        }

    try:
        codes = _run(poll_authorization_code(prompt, deadline=time.time() + 8.0))
    except DeviceCodeTimeout:
        # Still waiting — leave the pending file in place for the next poll.
        return {
            "ok": True,
            "status": "pending",
            "message": "Still waiting for the user to authorize. Call poll again.",
        }
    except OpenAICodexOAuthError as e:
        _clear_pending()
        return {"ok": False, "error": str(e)}

    try:
        cred = _run(exchange_authorization_code(
            authorization_code=codes["authorization_code"],
            code_verifier=codes["code_verifier"],
        ))
    except OpenAICodexOAuthError as e:
        _clear_pending()
        return {"ok": False, "error": str(e)}

    _clear_pending()

    # Warm caches inline. Both are best-effort — region restrictions or
    # rate limits should not block the connection from being usable.
    try:
        _run(_refresh_models_cache(cred))
    except Exception:
        pass
    try:
        _run(_refresh_usage_cache(cred))
    except Exception:
        pass

    cred = load_credential() or cred
    slugs = resolve_codex_models(cached_models=cred.available_models)
    flush_result = _flush_cache()
    return {
        "ok": True,
        "status": "connected",
        "email": cred.email,
        "account_id": cred.account_id,
        "expires_at": cred.expires_at,
        "models_count": len(slugs),
        "default_model_id": f"openai-codex/{slugs[0]}" if slugs else None,
        "available_models": [f"openai-codex/{s}" for s in slugs],
        "usage": cred.account_usage,
        "cache_flush": flush_result,
        "next_step": (
            "Connection successful. Switch with "
            f"`/model openai-codex/{slugs[0] if slugs else 'gpt-5.5'}` "
            "or ask the agent to use it."
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
    slugs = resolve_codex_models(cached_models=api_models)
    return {
        "ok": True,
        "source": "api" if force else "cache",
        "count": len(slugs),
        "available_models": [f"openai-codex/{s}" for s in slugs],
        "fetched_at": cred.models_fetched_at,
    }


def usage(force: bool = False) -> Dict[str, Any]:
    """Subscription usage stats (best-effort; region-restricted for some users)."""
    cred = load_credential()
    if cred is None:
        return {"ok": False, "error": "Not connected."}
    if not force and cred.account_usage:
        return {"ok": True, "source": "cache", "usage": cred.account_usage}
    try:
        snap = _run(_refresh_usage_cache(cred))
    except Exception as e:
        return {"ok": False, "error": f"fetch failed: {e}"}
    if snap is None:
        return {
            "ok": True,
            "source": "unavailable",
            "hint": "Account usage endpoint did not return data (may be region-restricted or rate-limited).",
            "usage": cred.account_usage,
        }
    return {"ok": True, "source": "api", "usage": snap.to_dict()}


# --------------------------------------------------------------------------
# Internal helpers (mirror the in-process tool's _refresh_*_cache methods)
# --------------------------------------------------------------------------

async def _refresh_models_cache(cred):
    api_models = await fetch_models_from_api(cred.access_token)
    if not api_models:
        return []
    cred.available_models = list(api_models)
    cred.models_fetched_at = int(time.time())
    save_credential(cred)
    return api_models


async def _refresh_usage_cache(cred):
    snap: Optional[UsageSnapshot] = await fetch_account_usage(cred.access_token, cred.account_id)
    if snap is None:
        return None
    cred.account_usage = snap.to_dict()
    save_credential(cred)
    return snap
