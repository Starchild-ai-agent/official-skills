"""HTTP client for community-projects gateway endpoints."""
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from typing import Any


def _gateway_url() -> str:
    return os.environ.get(
        "COMMUNITY_GATEWAY_URL",
        os.environ.get("COMMUNITY_PUBLIC_URL", "https://community.iamstarchild.com"),
    ).rstrip("/")


def _gateway_key() -> str:
    key = os.environ.get("COMMUNITY_GATEWAY_KEY", "")
    if not key:
        raise RuntimeError("COMMUNITY_GATEWAY_KEY not set in environment")
    return key


def _request(method: str, path: str, body: dict | None = None, timeout: int = 60) -> tuple[int, dict]:
    url = f"{_gateway_url()}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"X-Internal-Key": _gateway_key()}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}


def publish(req_body: dict) -> tuple[int, dict]:
    return _request("POST", "/api/code-projects/publish", req_body)


def unpublish(user_id: str, slug: str, requesting_user_id: str) -> tuple[int, dict]:
    return _request("POST", "/api/code-projects/unpublish", {
        "user_id": user_id,
        "slug": slug,
        "requesting_user_id": requesting_user_id,
    })


def list_(type: str | None = None, tag: str | None = None, user_id: str | None = None, q: str | None = None) -> tuple[int, dict]:
    qs = []
    if type: qs.append(f"type={type}")
    if tag: qs.append(f"tag={tag}")
    if user_id: qs.append(f"user_id={user_id}")
    if q:
        from urllib.parse import quote
        qs.append(f"q={quote(q)}")
    qstr = "?" + "&".join(qs) if qs else ""
    return _request("GET", f"/api/code-projects/list{qstr}")


def get(user_id: str, slug: str, version: str | None = None) -> tuple[int, dict]:
    qstr = f"?version={version}" if version else ""
    return _request("GET", f"/api/code-projects/{user_id}/{slug}{qstr}")


def fetch_raw_file(raw_url_prefix: str, file_path: str) -> bytes:
    """Fetch a single file from raw.githubusercontent.com — no auth needed for public repo."""
    url = f"{raw_url_prefix.rstrip('/')}/{file_path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"User-Agent": "community-publish-skill"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


# ── Stage 1: Service URL Publish (preview registry on community gateway) ──
# These hit /api/register, /api/unregister, /api/list — the in-memory
# preview-slug ↔ machine ↔ port routing table on sc-community-gateway.
# Distinct from /api/code-projects/* which is GitHub-backed code archive.

def preview_register(slug: str, machine_id: str, port: int,
                     owner_user_id: str, title: str = "") -> tuple[int, dict]:
    return _request("POST", "/api/register", {
        "slug": slug,
        "machine_id": machine_id,
        "port": port,
        "owner_user_id": owner_user_id,
        "title": title,
    }, timeout=10)


def preview_unregister(slug: str, owner_user_id: str) -> tuple[int, dict]:
    return _request("POST", "/api/unregister", {
        "slug": slug,
        "owner_user_id": owner_user_id,
    }, timeout=10)


def preview_list(owner_user_id: str) -> tuple[int, dict]:
    from urllib.parse import quote
    return _request("GET", f"/api/list?owner_user_id={quote(owner_user_id)}", timeout=10)
