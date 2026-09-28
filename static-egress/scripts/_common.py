#!/usr/bin/env python3
"""Shared client for the sc-static-egress control plane.

The skill never holds a Fly token — only the service does. All this module needs
is the container's own JWT (injected by the platform) and the service URL.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "http://sc-static-egress.internal:8080"

# Deliberately no proxy resolution:
#  * correctness — this call goes over the private network and must NOT be
#    routed through the platform's paid-API proxy (HTTP_PROXY/sc-proxy), which
#    would rewrite the caller identity and bill the request;
#  * latency — on macOS, urllib's proxy lookup hits SystemConfiguration and can
#    add hundreds of milliseconds to a 2 ms request.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class ServiceError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def service_url() -> str:
    return (os.environ.get("SRE_URL") or DEFAULT_URL).rstrip("/")


def container_token() -> str:
    token = os.environ.get("CONTAINER_JWT", "").strip()
    if not token:
        raise ServiceError(
            401, "no_identity",
            "CONTAINER_JWT is not set. This skill only works inside the Starchild "
            "container, where the platform injects it.",
        )
    return token


def call(method: str, path: str, body: dict | None = None, timeout: int = 60) -> dict:
    url = f"{service_url()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {container_token()}")
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with _OPENER.open(request, timeout=timeout) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            error = json.loads(raw).get("error", {})
        except ValueError:
            error = {}
        # The service message is the remediation guide; surface it verbatim.
        raise ServiceError(exc.code, error.get("code", "http_error"),
                           error.get("message") or raw[:400]) from exc
    except urllib.error.URLError as exc:
        raise ServiceError(
            503, "unreachable",
            f"cannot reach the egress service at {url}: {exc.reason}. "
            f"It is only reachable from the platform's private network.",
        ) from exc


def emit(payload: dict, human: str | None = None) -> None:
    """Print for the agent: a one-line human summary plus machine-readable JSON."""
    if human:
        print(human)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def fail(message: str, code: str = "error", status: int = 2) -> int:
    print(f"ERROR [{code}]: {message}", file=sys.stderr)
    return status