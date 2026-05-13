"""community-publish skill exports.

Two independent kinds of sharing, optionally cross-linked via project.yaml's
`publisher:` block:

  Open-source side (any code, GitHub-backed):
    open_source, remove_open_source, list_open_source,
    get_open_source, fork, validate_open_source

  Public URL side (any running HTTP service, in-memory route table):
    publish_preview, unpublish_preview, list_published_previews

Cross-link binding lives in project.yaml under `publisher:`. Either side can
register the binding first; the gateway holds a pending entry until the
counterpart arrives. No manual link step needed in the typical flow.

Manual escape hatch (for repair scenarios after rename):
    link_to_listing(listing_slug, code_slug)

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/community-publish")
    from exports import open_source, publish_preview
    print(open_source("output/projects/my-app"))
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


def _parse_source(source: str) -> tuple[str, str]:
    """Parse 'user_id/slug'.

    NOTE: 'user_id/slug@version' is no longer supported — only the latest
    state of a project lives on disk. To inspect or fork an older snapshot,
    look at the GitHub commit history for the project directory and check
    out the desired commit manually.
    """
    s = source.strip()
    if "@" in s:
        raise ValueError(
            f"Invalid source: {source!r} — versioned references are no longer supported. "
            "Only the latest state of a project is published; use 'user_id/slug' and "
            "consult GitHub history for older snapshots."
        )
    if "/" not in s:
        raise ValueError(f"Invalid source: {source!r} — expected 'user_id/slug'")
    user_id, slug = s.split("/", 1)
    return user_id.strip(), slug.strip()


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


def open_source(project_dir: str, version_bump: str = "patch",
                message: str = "") -> dict[str, Any]:
    """Validate, bump version, and push project source to the community GitHub repo.

    Args:
        project_dir: path to the project (e.g. "output/projects/my-app")
        version_bump: "patch" | "minor" | "major" | "none" (use existing version)
        message: free-form commit message describing what this version
                 changed. The agent should compose this based on actual
                 code changes in the session — it becomes the body of the
                 GitHub commit and is what people read when browsing
                 history. If blank, gateway uses a generic template.
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
    if message and message.strip():
        body["commit_message"] = message.strip()

    status, resp = gateway.publish(body)
    if status != 200 or not resp.get("ok"):
        return {
            "ok": False,
            "error": resp.get("error", f"Gateway returned HTTP {status}"),
            "validation_errors": resp.get("validation_errors"),
            "http_status": status,
        }
    # Surface the binding back to the caller so the agent can show what was
    # wired (or what's pending).
    publisher = manifest.get("publisher") or {}
    return {
        "ok": True,
        "user_id": uid,
        "slug": manifest["name"],
        "type": manifest["type"],
        "version": new_version,
        "github_url": resp.get("github_url"),
        "commit_sha": resp.get("commit_sha"),
        "warnings": warnings,
        "publisher": {
            "code_slug": publisher.get("code_slug") or manifest["name"],
            "public_slug": publisher.get("public_slug"),
        },
        "hint": _publisher_hint_for_open_source(uid, manifest, publisher),
    }


def _publisher_hint_for_open_source(uid: str, manifest: dict, publisher: dict) -> str:
    """Tell the user what cross-link state to expect after open_source."""
    public_slug = publisher.get("public_slug")
    if public_slug:
        full = public_slug if public_slug.startswith(f"{uid}-") else f"{uid}-{public_slug}"
        return (
            f"Cross-link binding declared: publisher.public_slug='{public_slug}'. "
            f"If a public listing '{full}' exists, it's now linked. "
            f"If not, the link is pending and will wire automatically when you "
            f"publish_preview() with publisher.code_slug='{manifest['name']}' in project.yaml."
        )
    return (
        "No publisher.public_slug set in project.yaml. To pair this code with a "
        "public preview URL, add `publisher: { public_slug: \"<your-slug>\" }` "
        "to project.yaml and re-run open_source(), OR call publish_preview() "
        f"with publisher.code_slug='{manifest['name']}' in your project.yaml so "
        "the listing-side picks up this code."
    )


def link_to_listing(listing_slug: str, code_slug: str) -> dict[str, Any]:
    """Manual escape hatch: directly wire a code project to a listing.

    Normally not needed — cross-link happens automatically via the
    publisher binding in project.yaml. Use this only for repair scenarios
    (e.g. relinking after a manual rename).

    Args:
        listing_slug: full preview listing slug (e.g. '2004-my-dashboard').
                     User_id prefix is added if missing.
        code_slug:   open-sourced code project slug (no user_id prefix).
    """
    uid = _user_id()
    final_listing = listing_slug if listing_slug.startswith(f"{uid}-") else f"{uid}-{listing_slug}"

    status, body = gateway.get(uid, code_slug)
    if status != 200 or not body.get("ok"):
        return {
            "ok": False,
            "error": (f"Code project '{uid}/{code_slug}' not found. "
                      f"Open-source it first with open_source(project_dir)."),
        }
    project = body.get("project") or {}

    try:
        st, b = gateway.link_listing(
            public_slug=final_listing,
            code_user_id=uid,
            code_slug=code_slug,
            version=project.get("version", ""),
            github_url=project["github_url"],
        )
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if st == 200 and b.get("ok"):
        return {
            "ok": True,
            "listing_slug": final_listing,
            "code_slug": code_slug,
            "message": f"Linked '{final_listing}' → code '{uid}/{code_slug}'.",
        }
    return {"ok": False, "error": b.get("error", f"HTTP {st}")}


def remove_open_source(slug: str) -> dict[str, Any]:
    """Remove your open-sourced project from the community GitHub repo.

    Deletes the entire slug directory in one commit. Cannot remove someone
    else's project. Git history of the deletion + prior versions stays in
    the repo's commit log — only the working tree is cleaned.
    """
    uid = _user_id()
    status, resp = gateway.unpublish(uid, slug, uid)
    if status != 200 or not resp.get("ok"):
        return {"ok": False, "error": resp.get("error", f"HTTP {status}"), "http_status": status}
    return resp


def list_open_source(type: str | None = None, tag: str | None = None,
                     user: str | None = None, q: str | None = None) -> dict[str, Any]:
    """Browse open-sourced projects in the community GitHub repo.

    Filters: type ('task'|'service'|'script'), tag, user_id, free-text q.
    """
    status, resp = gateway.list_(type=type, tag=tag, user_id=user, q=q)
    if status != 200:
        return {"ok": False, "error": resp.get("error", f"HTTP {status}")}
    if isinstance(resp, dict):
        resp.setdefault("source", "community-projects (github-backed code repo)")
    return resp


def get_open_source(source: str) -> dict[str, Any]:
    """Get one open-sourced project's full detail (manifest + readme).

    source: 'user_id/slug'. Always returns the current state — historical
    snapshots are not addressable through this skill (use GitHub history).
    """
    user_id, slug = _parse_source(source)
    status, resp = gateway.get(user_id, slug)
    if status != 200:
        return {"ok": False, "error": resp.get("error", f"HTTP {status}"), "http_status": status}
    return resp


def fork(source: str, dest_dir: str | None = None) -> dict[str, Any]:
    """Fork an open-sourced project into output/projects/{slug}/.

    source: 'user_id/slug' (always pulls current state — for older snapshots
            check the GitHub commit history yourself)
    dest_dir: where to install (default: output/projects/{slug}/)

    Returns project metadata + missing_envs (caller should request_env_input these)
    + next_step (instructions for type-specific install).
    """
    user_id, slug = _parse_source(source)
    detail_status, detail = gateway.get(user_id, slug)
    if detail_status != 200 or not detail.get("ok"):
        return {"ok": False, "error": detail.get("error", f"HTTP {detail_status}"), "http_status": detail_status}

    project = detail["project"]
    raw_url_prefix = project["raw_url_prefix"]
    manifest_dict = project.get("manifest") or {}

    file_list = _enumerate_project_files(user_id, slug, project["type"])

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
        "source": f"{user_id}/{slug}",
        "version": project.get("version", ""),
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


def _enumerate_project_files(user_id: str, slug: str, project_type: str) -> list[str]:
    """Enumerate files in a project's current state via GitHub Trees API."""
    import urllib.request
    import json

    repo = "Starchild-ai-agent/community-projects"
    type_folder = project_type + "s"
    prefix = f"projects/{type_folder}/{user_id}/{slug}/"

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
# PUBLISH PREVIEW — map a running HTTP service to a public URL.
# Works for any service (regardless of project type). Lives in an in-memory
# route table on the gateway.
# ════════════════════════════════════════════════════════════════════════

def publish_preview(preview_id: str, slug: str = "",
                    title: str = "",
                    publisher_code_slug: str = "") -> dict[str, Any]:
    """Expose a running service at a public URL.

    Maps the preview to https://community.iamstarchild.com/{user_id}-{slug}.
    Stays online while your container is running; visitors see an offline
    page if the container is down.

    Args:
        preview_id: ID returned by preview(action='serve'). Must be running.
        slug: URL suffix (lowercase alphanumeric + hyphens, 3-50 chars).
              Pass only the suffix — user_id prefix is added automatically.
              If omitted, preview_id is used as fallback.
        title: Display name for the community listing.
        publisher_code_slug: Optional binding to a code project (when the
              source code lives under a different slug than the URL). The
              gateway either links immediately if the code is already
              open-sourced, or holds a pending entry that wires up when
              the code is later open-sourced.
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
    binding_code_slug = publisher_code_slug.strip() or None
    try:
        status, body = gateway.preview_register(
            slug=final_slug, machine_id=machine_id, port=int(port),
            owner_user_id=user_id, title=title_final,
            publisher_code_slug=binding_code_slug,
        )
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status == 429:
        return {"ok": False, "error": body.get("error", "Too many published previews.")}
    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned {status}")}

    public_url = f"{_public_url_base()}/{final_slug}"
    return {
        "ok": True,
        "slug": final_slug,
        "url": public_url,
        "port": port,
        "publisher": {"code_slug": binding_code_slug},
        "hint": (
            f"Cross-link binding declared (publisher.code_slug='{binding_code_slug}'). "
            f"If that code project is already open-sourced, it's now linked. "
            f"If not, the link is pending and will wire when you "
            f"open_source() the code."
        ) if binding_code_slug else (
            "No publisher.code_slug binding set. To pair this URL with "
            "open-source code, pass publisher_code_slug='<code-slug>' on the "
            "next call, OR add publisher: { public_slug: '" + final_slug[len(f"{user_id}-"):] + "' } "
            "to the code project's project.yaml and run open_source()."
        ),
        "message": f"Published! Anyone can view at: {public_url}",
    }


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
