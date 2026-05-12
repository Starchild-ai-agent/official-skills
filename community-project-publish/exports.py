"""community-project-publish skill exports.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/community-project-publish")
    from exports import publish_project, fork_project, list_projects
    print(list_projects())
    EOF
"""
from __future__ import annotations
import base64
import os
import shutil
from typing import Any

# Make sibling lib/ importable
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
import sys
if _SKILL_DIR not in sys.path:
    sys.path.insert(0, _SKILL_DIR)

from lib import gateway, manifest as M, validate as V, install as I  # noqa: E402


# ── Helpers ──

def _user_id() -> str:
    uid = os.environ.get("USER_ID", "")
    if not uid:
        raise RuntimeError("USER_ID not set in environment — cannot publish")
    return uid


def _abspath(p: str) -> str:
    if os.path.isabs(p):
        return p
    return os.path.abspath(os.path.join("/data/workspace", p))


# ── Public API ──

def validate_project(project_dir: str) -> dict[str, Any]:
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


def publish_project(project_dir: str, version_bump: str = "patch") -> dict[str, Any]:
    """Validate, bump version, and publish to gateway.

    version_bump: "patch" | "minor" | "major" | "none" (use existing version)
    """
    pd = _abspath(project_dir)
    if not os.path.isdir(pd):
        return {"ok": False, "error": f"Directory not found: {pd}"}

    try:
        manifest = M.load_manifest(pd)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load project.yaml: {e}"}

    # Bump version
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

    # Set author from USER_ID if blank or "user-XXXX"-style placeholder
    uid = _user_id()
    if not manifest.get("author") or manifest.get("author", "").startswith("user-XXXX"):
        manifest["author"] = f"user-{uid}"
        M.save_manifest(pd, manifest)

    # Validate locally first
    errors, warnings = V.validate(pd, manifest)
    if errors:
        return {"ok": False, "error": "Local validation failed", "errors": errors, "warnings": warnings}

    # Build publish payload
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
    return {
        "ok": True,
        "user_id": uid,
        "slug": manifest["name"],
        "type": manifest["type"],
        "version": new_version,
        "github_url": resp.get("github_url"),
        "commit_sha": resp.get("commit_sha"),
        "warnings": warnings,
    }


def update_project(project_dir: str, version_bump: str = "patch") -> dict[str, Any]:
    """Alias for publish_project — semantically clearer when bumping an existing project."""
    return publish_project(project_dir, version_bump)


def list_projects(type: str | None = None, tag: str | None = None,
                  user: str | None = None, q: str | None = None) -> dict[str, Any]:
    """Browse the catalog. Filters: type, tag, user_id, free-text query."""
    status, resp = gateway.list_(type=type, tag=tag, user_id=user, q=q)
    if status != 200:
        return {"ok": False, "error": resp.get("error", f"HTTP {status}")}
    return resp


def get_project(source: str) -> dict[str, Any]:
    """Get project detail (manifest + readme). source: 'user_id/slug' or 'user_id/slug@version'."""
    user_id, slug, version = _parse_source(source)
    status, resp = gateway.get(user_id, slug, version)
    if status != 200:
        return {"ok": False, "error": resp.get("error", f"HTTP {status}"), "http_status": status}
    return resp


def fork_project(source: str, dest_dir: str | None = None) -> dict[str, Any]:
    """Fork a project from the catalog into output/projects/{slug}/.

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

    # Determine which files to fetch — list contents via GitHub Trees API by hitting raw URLs
    # We don't have an API to list files; rely on the manifest's entry + standard files
    target_version = project["latest_version"]
    file_list = _enumerate_project_files(user_id, slug, target_version)

    # Decide destination
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

    # Download files
    downloaded: list[str] = []
    for rel_path in file_list:
        try:
            content = gateway.fetch_raw_file(raw_url_prefix, rel_path)
        except Exception as e:
            # Cleanup on failure
            shutil.rmtree(dest_abs, ignore_errors=True)
            return {"ok": False, "error": f"Failed to fetch {rel_path}: {e}"}
        target = os.path.join(dest_abs, rel_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(content)
        downloaded.append(rel_path)

    # Re-load manifest from disk (more authoritative than gateway-parsed dict)
    try:
        manifest = M.load_manifest(dest_abs)
    except Exception:
        manifest = manifest_dict

    # Diff env
    missing_envs = I.diff_env_required(manifest)

    # Type-specific install plan
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


def unpublish_project(slug: str) -> dict[str, Any]:
    """Unpublish ALL versions of YOUR own project. Cannot unpublish someone else's."""
    uid = _user_id()
    status, resp = gateway.unpublish(uid, slug, uid)
    if status != 200 or not resp.get("ok"):
        return {"ok": False, "error": resp.get("error", f"HTTP {status}"), "http_status": status}
    return resp


# ── Internal helpers ──

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


def _enumerate_project_files(user_id: str, slug: str, version: str) -> list[str]:
    """Enumerate files in a project version via GitHub Trees API.

    The community-projects repo is public; we hit:
      https://api.github.com/repos/Starchild-ai-agent/community-projects/git/trees/main?recursive=1
    and filter to the project version dir.

    We use the project type from gateway response to know the folder.
    """
    import urllib.request
    import json

    repo = "Starchild-ai-agent/community-projects"
    # Get the type from gateway since we don't know it locally
    status, detail = gateway.get(user_id, slug, version)
    if status != 200 or not detail.get("ok"):
        # Fallback to standard file list
        return ["project.yaml", "PROJECT.md", ".env.example"]
    project_type = detail["project"]["type"]

    type_folder = project_type + "s"  # task → tasks
    prefix = f"projects/{type_folder}/{user_id}/{slug}/{version}/"

    url = f"https://api.github.com/repos/{repo}/git/trees/main?recursive=1"
    req = urllib.request.Request(url, headers={"User-Agent": "community-project-publish-skill"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        tree = json.loads(resp.read())
    items = tree.get("tree", [])
    files = []
    for item in items:
        if item.get("type") == "blob" and item["path"].startswith(prefix):
            files.append(item["path"][len(prefix):])
    return files
