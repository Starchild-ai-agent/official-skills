"""Shared helpers for the cli-bridge skill scripts.

Mirror the conventions of skills/workroom/scripts/_common.py but slimmer —
cli-bridge needs loopback access to clawd's /api/keys plus authed access
to sc-chatroom's /cli-keys for the short-code exchange.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Env
# ---------------------------------------------------------------------------

USER_ID = os.environ.get("USER_ID", "").strip()
CLAWD_BASE_URL = os.environ.get("CLAWD_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# Public URL of the sc-chatroom gateway. The bundle hands this to the CLI
# as the dial target — it MUST be reachable from the user's laptop, not
# the .internal one.
CHATROOM_PUBLIC_URL = os.environ.get(
    "CHATROOM_PUBLIC_URL", "https://workroom.iamstarchild.com",
).rstrip("/")

# Internal URL the skill uses for its own server-side calls (POST /cli-keys).
# Defaults to .internal so the call stays inside Fly; falls back to public.
CHATROOM_SERVER_URL = os.environ.get(
    "CHATROOM_SERVER_URL", "http://sc-chatroom.internal:8080",
).rstrip("/")

# Fly machine id for this clawd — replayed by sc-chatroom as the
# `fly-force-instance-id` header so the proxy lands on this exact machine.
CONTAINER_ID = (
    os.environ.get("CONTAINER_ID")
    or os.environ.get("FLY_MACHINE_ID")
    or ""
).strip()

CLI_BRIDGE_SCOPE = "chat:bridge:cli"


def require_env() -> None:
    if not USER_ID:
        die("USER_ID env var is not set")
    if not CONTAINER_ID:
        die(
            "no CONTAINER_ID/FLY_MACHINE_ID — sc-chatroom needs the Fly machine "
            "id so /agent/chat/stream can route to this exact clawd. Set "
            "FLY_MACHINE_ID (Fly auto-injects this on every machine) or CONTAINER_ID."
        )


def get_user_jwt() -> str:
    """Return the JWT clawd uses to identify itself to other Starchild
    internal services. Same logic as the chatroom skill: prefer USER_JWT
    env override, fall back to CONTAINER_JWT (the long-lived token Fly
    injects into every clawd container)."""
    override = os.environ.get("USER_JWT", "").strip()
    if override:
        return override
    container = os.environ.get("CONTAINER_JWT", "").strip()
    if container:
        return container
    die(
        "no identity JWT available — expected CONTAINER_JWT env (production) "
        "or USER_JWT env (dev)."
    )
    return ""  # unreachable


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(msg)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def clawd_call(method: str, path: str, **kwargs) -> httpx.Response:
    """Loopback to this agent's own clawd — middleware recognizes 127.0.0.1
    and treats it as `auth_type=internal`, so no bearer required."""
    url = CLAWD_BASE_URL + path
    with httpx.Client(timeout=10.0) as c:
        return c.request(method, url, **kwargs)


def chatroom_call(method: str, path: str, *, user_jwt: Optional[str] = None,
                  **kwargs) -> httpx.Response:
    """Authed call to sc-chatroom server (Fly-internal). Bearer is the
    container JWT unless overridden — sc-chatroom's auth.py treats it as
    a starchild user identity."""
    headers = dict(kwargs.pop("headers", {}))
    if "authorization" not in {k.lower() for k in headers}:
        jwt = user_jwt or get_user_jwt()
        headers["Authorization"] = f"Bearer {jwt}"
    url = CHATROOM_SERVER_URL + path
    with httpx.Client(timeout=15.0) as c:
        return c.request(method, url, headers=headers, **kwargs)
