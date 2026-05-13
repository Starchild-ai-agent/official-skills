"""community-publish skill exports.

Two independent kinds of sharing:

  Open source side (any code, GitHub-backed):
    open_source, remove_open_source, list_open_source,
    get_open_source, fork, validate_open_source

  Preview public-URL side (preview type only, in-memory route table):
    publish_preview, unpublish_preview, list_published_previews

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/community-publish")
    from exports import open_source, fork, list_open_source
    print(list_open_source())
    EOF
"""
from __future__ import annotations
import base64
import os
import re
import shutil
from typing import Any

# Make sibling lib/ importable
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
import sys
if _SKILL_DIR not in sys.path:
    sys.path.insert(0, _SKILL_DIR)

from lib import gateway, manifest as M, validate as V, install as I  # noqa: E402


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")


# ── Helpers ──

def _user_id() -> str:
    uid = os.environ.get("USER_ID", "")
    if not uid:
        raise RuntimeError("USER_ID not set in environment — cannot publish")
    return uid


def _machine_id() -> str:
    mid = os.environ.get("FLY_MACHINE_ID", "")
    if not mid:
        raise RuntimeError(
            "FLY_MACHINE_ID not set — preview publish only works inside "
            "the Starchild Fly container."
        )
    return mid


def _public_url_base() -> str:
    return os.environ.get(
        "COMMUNITY_PUBLIC_URL", "https://community.iamstarchild.com"
    ).rstrip("/")


def _abspath(p: str) -> str:
    if os.path.isabs(p):
        return p
    return os.path.abspath(os.path.join("/data/workspace", p))


def _parse_source(source: str) -> tuple[str, str, str | None]:
    """Parse 'user_id/slug' or 'user_id/slug@version'."""
    s = source.strip()
    version = None
    if "@" in s:
        s, version = s.rsplit("@", 1)
    if "/" not in s:
        raise ValueError(f"Invalid source: {source!r} — expected 'user_id/slug[@version]'")
    user_id, slug = s.split("/", 1)
    return user_id.strip(), slug.strip(), version


def _read_preview_registry(preview_id: str) -> dict[str, Any] | None:
    """Read /data/previews.json to find a preview's port + status."""
    import json as _json
    path = "/data/previews.json"
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = _json.load(f)
    except Exception:
        return None
    items = data.get("previews") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return None
    for p in items:
        if p.get("id") == preview_id or p.get("preview_id") == preview_id:
            return p
    return None


# ════════════════════════════════════════════════════════════════════════
# OPEN SOURCE — push code to GitHub. Works for any project type.
# ════════════════════════════════════════════════════════════════════════

def validate_open_source(project_dir: str) -> dict[str, Any]:
    """Pre-flight check: validates manifest + files. Returns ok/errors/warnings."""
    pd = _abspath(project_dir)
    if not os.path.isdir(pd):
        return {"ok": False, "errors": [f"Directory not found: {pd}"], "warnings": []}
    try:
        manifest = M.load_manifest(pd)
    except Exception as e:
        return {"ok": False, "errors": [f"Failed to load project.yaml: {e}"], "warnings": []}
    errors, warnings = V.validate(pd, manifest)
    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "manifest": manifest,
    }


def open_source(project_dir: str, version_bump: str = "patch") -> dict[str, Any]:
    """Validate, bump version, and push project source to the community GitHub repo.

    version_bump: "patch" | "minor" | "major" | "none" (use existing version)
    """
    pd = _abspath(project_dir)
    if not os.path.isdir(pd):
        return {"ok": False, "error": f"Directory not found: {pd}"}

    try:
        manifest = M.load_manifest(pd)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load project.yaml: {e}"}

    current = manifest.get("version", "0.0.0")
    if version_bump != "none":
        try:
            new_version = M.bump_semver(current, version_bump)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        manifest["version"] = new_version
        M.save_manifest(pd, manifest)
    else:
        new_version = current

    uid = _user_id()
    if not manifest.get("author") or manifest.get("author", "").startswith("user-XXXX"):
        manifest["author"] = f"user-{uid}"
        M.save_manifest(pd, manifest)

    errors, warnings = V.validate(pd, manifest)
    if errors:
        return {"ok": False, "error": "Local validation failed", "errors": errors, "warnings": warnings}

    files = V.collect_files(pd)
    payload_files = [
        {"path": rel, "content_base64": base64.b64encode(content).decode("ascii")}
        for rel, content in files
    ]
    body = {
        "user_id": uid,
        "slug": manifest["name"],
        "type": manifest["type"],
        "version": new_version,
        "manifest": manifest,
        "files": payload_files,
    }

    status, resp = gateway.publish(body)
    if status != 200 or not resp.get("ok"):
        return {
            "ok": False,
            "error": resp.get("error", f"Gateway returned HTTP {status}"),
            "validation_errors": resp.get("validation_errors"),
            "http_status": status,
        }
    result = {
        "ok": True,
        "user_id": uid,
        "slug": manifest["name"],
        "type": manifest["type"],
        "version": new_version,
        "github_url": resp.get("github_url"),
        "commit_sha": resp.get("commit_sha"),
        "warnings": warnings,
    }

    # Best-effort: if the matching listing exists but auto-link didn't fire
    # (gateway's auto-link runs at publish-time but only catches the convention
    # `{user_id}-{slug}`. If the listing was created LATER or auto-link missed,
    # we manually wire the link here so the frontend shows "View Source").
    link_result = _try_link_to_listing(
        listing_slug=f"{uid}-{manifest['name']}",
        code_user_id=uid,
        code_slug=manifest["name"],
        version=new_version,
        github_url=resp.get("github_url", ""),
    )
    result["linked_listing"] = link_result
    return result


def _try_link_to_listing(listing_slug: str, code_user_id: str, code_slug: str,
                         version: str, github_url: str) -> dict[str, Any]:
    """Best-effort: link a code project to its public listing. Non-fatal."""
    try:
        status, body = gateway.link_listing(
            public_slug=listing_slug,
            code_user_id=code_user_id,
            code_slug=code_slug,
            latest_version=version,
            github_url=github_url,
        )
        if status == 200 and body.get("ok"):
            return {"ok": True, "listing_slug": listing_slug}
        if status == 404:
            return {"ok": False, "skipped": True,
                    "reason": f"Listing {listing_slug} doesn't exist yet — publish_preview first to enable cross-link."}
        return {"ok": False, "error": body.get("error", f"HTTP {status}")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def remove_open_source(slug: str) -> dict[str, Any]:
    """Remove ALL versions of YOUR project from the community GitHub repo.

    Cannot remove someone else's project.
    """
    uid = _user_id()
    status, resp = gateway.unpublish(uid, slug, uid)
    if status != 200 or not resp.get("ok"):
        return {"ok": False, "error": resp.get("error", f"HTTP {status}"), "http_status": status}
    return resp


def list_open_source(type: str | None = None, tag: str | None = None,
                     user: str | None = None, q: str | None = None) -> dict[str, Any]:
    """Browse open-sourced projects in the community GitHub repo.

    Filters: type ('task'|'preview'|'service'|'script'), tag, user_id, free-text q.
    """
    status, resp = gateway.list_(type=type, tag=tag, user_id=user, q=q)
    if status != 200:
        return {"ok": False, "error": resp.get("error", f"HTTP {status}")}
    if isinstance(resp, dict):
        resp.setdefault("source", "community-projects (github-backed code repo)")
    return resp


def get_open_source(source: str) -> dict[str, Any]:
    """Get one open-sourced project's full detail (manifest + readme).

    source: 'user_id/slug' or 'user_id/slug@version'.
    """
    user_id, slug, version = _parse_source(source)
    status, resp = gateway.get(user_id, slug, version)
    if status != 200:
        return {"ok": False, "error": resp.get("error", f"HTTP {status}"), "http_status": status}
    return resp


def fork(source: str, dest_dir: str | None = None) -> dict[str, Any]:
    """Fork an open-sourced project into output/projects/{slug}/.

    source: 'user_id/slug' or 'user_id/slug@version' (default: latest)
    dest_dir: where to install (default: output/projects/{slug}/)

    Returns project metadata + missing_envs (caller should request_env_input these)
    + next_step (instructions for type-specific install).
    """
    user_id, slug, version = _parse_source(source)
    detail_status, detail = gateway.get(user_id, slug, version)
    if detail_status != 200 or not detail.get("ok"):
        return {"ok": False, "error": detail.get("error", f"HTTP {detail_status}"), "http_status": detail_status}

    project = detail["project"]
    raw_url_prefix = project["raw_url_prefix"]
    manifest_dict = project.get("manifest") or {}

    target_version = project["latest_version"]
    file_list = _enumerate_project_files(user_id, slug, target_version)

    if dest_dir is None:
        dest_dir = f"output/projects/{slug}"
    dest_abs = _abspath(dest_dir)

    if os.path.exists(dest_abs):
        if os.listdir(dest_abs):
            return {
                "ok": False,
                "error": f"Destination not empty: {dest_abs}. Remove it or pick a different dest_dir.",
            }
    else:
        os.makedirs(dest_abs, exist_ok=True)

    downloaded: list[str] = []
    for rel_path in file_list:
        try:
            content = gateway.fetch_raw_file(raw_url_prefix, rel_path)
        except Exception as e:
            shutil.rmtree(dest_abs, ignore_errors=True)
            return {"ok": False, "error": f"Failed to fetch {rel_path}: {e}"}
        target = os.path.join(dest_abs, rel_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(content)
        downloaded.append(rel_path)

    try:
        manifest = M.load_manifest(dest_abs)
    except Exception:
        manifest = manifest_dict

    missing_envs = I.diff_env_required(manifest)
    install_result = I.install(dest_abs, manifest)

    return {
        "ok": True,
        "source": f"{user_id}/{slug}@{target_version}",
        "type": project["type"],
        "installed_at": dest_abs,
        "files_downloaded": downloaded,
        "manifest": manifest,
        "missing_envs": missing_envs,
        "next_step": install_result.get("next_step"),
        "install_plan": install_result,
        "env_action_required": (
            f"Call request_env_input with: {missing_envs}"
            if missing_envs else "All required env vars already set."
        ),
    }


def _enumerate_project_files(user_id: str, slug: str, version: str) -> list[str]:
    """Enumerate files in a project version via GitHub Trees API."""
    import urllib.request
    import json

    repo = "Starchild-ai-agent/community-projects"
    status, detail = gateway.get(user_id, slug, version)
    if status != 200 or not detail.get("ok"):
        return ["project.yaml", "PROJECT.md", ".env.example"]
    project_type = detail["project"]["type"]

    type_folder = project_type + "s"
    prefix = f"projects/{type_folder}/{user_id}/{slug}/{version}/"

    url = f"https://api.github.com/repos/{repo}/git/trees/main?recursive=1"
    req = urllib.request.Request(url, headers={"User-Agent": "community-publish-skill"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        tree = json.loads(resp.read())
    items = tree.get("tree", [])
    files = []
    for item in items:
        if item.get("type") == "blob" and item["path"].startswith(prefix):
            files.append(item["path"][len(prefix):])
    return files


# ════════════════════════════════════════════════════════════════════════
# PREVIEW PUBLISH — map a running preview to a public URL.
# Only applies to type=preview projects. Lives in an in-memory route table.
# ════════════════════════════════════════════════════════════════════════

def publish_preview(preview_id: str, slug: str = "",
                    title: str = "") -> dict[str, Any]:
    """Expose a running preview at a public URL.

    Maps preview to https://community.iamstarchild.com/{user_id}-{slug}.
    Stays online while the publisher's container is running; visitors see
    an offline page if the container is down.

    Args:
        preview_id: ID returned by `preview(action='serve')`. Must be running.
        slug: URL suffix (lowercase alphanumeric + hyphens, 3-50 chars).
              Pass only the suffix — user_id prefix is added automatically.
              If omitted, preview_id is used as fallback.
        title: Display name for the community listing.

    Returns:
        {"ok": True, "url": ..., "slug": ..., "port": ...} on success
        {"ok": False, "error": ...} on failure
    """
    user_id = _user_id()
    try:
        machine_id = _machine_id()
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}

    preview = _read_preview_registry(preview_id)
    if not preview:
        return {
            "ok": False,
            "error": f"Preview not found: {preview_id}. "
                     f"Check /data/previews.json for valid IDs.",
        }
    port = preview.get("port")
    if not port:
        return {"ok": False, "error": f"Preview {preview_id} has no port recorded."}
    # Liveness: probe the port. If the preview was stopped, the port is closed.
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    try:
        sock.connect(("127.0.0.1", int(port)))
        sock.close()
    except Exception:
        return {
            "ok": False,
            "error": f"Preview {preview_id} is registered but port {port} "
                     f"is not accepting connections. Restart it via "
                     f"preview(action='serve') first.",
        }

    slug_suffix = slug if slug else preview_id
    prefix = f"{user_id}-"
    if slug_suffix.startswith(prefix):
        slug_suffix = slug_suffix[len(prefix):]
    final_slug = f"{user_id}-{slug_suffix}"

    if not SLUG_RE.match(final_slug):
        return {
            "ok": False,
            "error": f"Invalid slug '{final_slug}': must be 3-50 chars, "
                     f"lowercase alphanumeric + hyphens, "
                     f"cannot start or end with a hyphen.",
        }

    title_final = title or preview.get("title", "")
    try:
        status, body = gateway.preview_register(
            slug=final_slug, machine_id=machine_id, port=int(port),
            owner_user_id=user_id, title=title_final,
        )
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status == 429:
        return {"ok": False, "error": body.get("error", "Too many published previews.")}
    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned {status}")}

    public_url = f"{_public_url_base()}/{final_slug}"
    result = {
        "ok": True,
        "slug": final_slug,
        "url": public_url,
        "port": port,
        "message": f"Published! Anyone can view at: {public_url}",
    }

    # Best-effort reverse-link: if user already open-sourced a code project
    # with the matching slug, wire the cross-reference so the frontend shows
    # "View Source" on this listing. Gateway auto-link only fires on the
    # open_source side at publish-time, so if the user did open_source FIRST
    # and publish_preview SECOND, the listing wouldn't have been linked.
    suffix_only = final_slug[len(f"{user_id}-"):]  # strip "{user_id}-" prefix
    code_match = _lookup_code_project(user_id, suffix_only)
    if code_match:
        link_result = _try_link_to_listing(
            listing_slug=final_slug,
            code_user_id=user_id,
            code_slug=suffix_only,
            version=code_match["latest_version"],
            github_url=code_match["github_url"],
        )
        result["linked_code"] = link_result
    return result


def _lookup_code_project(user_id: str, slug: str) -> dict | None:
    """Check if a code project with this user_id+slug exists. Returns None if not."""
    try:
        status, body = gateway.get(user_id, slug)
        if status == 200 and body.get("ok"):
            return body.get("project")
    except Exception:
        pass
    return None


def unpublish_preview(slug: str) -> dict[str, Any]:
    """Remove a preview's public URL.

    Args:
        slug: The full slug as listed by list_published_previews()
              (e.g. '1463-my-dashboard'). User_id prefix may be omitted —
              it will be added if missing.

    Returns:
        {"ok": True, "message": ...} on success
        {"ok": False, "error": ...} on failure
    """
    user_id = _user_id()
    final_slug = slug if slug.startswith(f"{user_id}-") else f"{user_id}-{slug}"

    try:
        status, body = gateway.preview_unregister(
            slug=final_slug, owner_user_id=user_id,
        )
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status == 404:
        return {
            "ok": False,
            "error": body.get("error", f"Slug '{final_slug}' not found or not owned by you."),
        }
    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned {status}")}

    return {
        "ok": True,
        "slug": final_slug,
        "message": f"Unpublished '{final_slug}'. The URL is no longer accessible.",
    }


def list_published_previews() -> dict[str, Any]:
    """List current user's published preview URLs.

    Returns:
        {"ok": True, "previews": [...], "count": N} on success
        {"ok": False, "error": ...} on failure
    """
    user_id = _user_id()
    try:
        status, body = gateway.preview_list(owner_user_id=user_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned {status}")}
    return {"ok": True, **body}
