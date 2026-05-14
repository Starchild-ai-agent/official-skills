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


_LOCAL_AGENT_BASE = os.environ.get("STARCHILD_LOCAL_API_BASE", "http://127.0.0.1:8000")


def _notify_local_publish(port: int, preview_id: str | None) -> tuple[bool, str | None]:
    """Tell the local agent process to whitelist this port for /community/{port}/.

    Calls the loopback-only /community/_internal/publish endpoint that lives in
    the same process as CommunityRegistry. Without this call, the agent's
    `/community/{port}/` proxy returns 403 "Port not published" until the next
    container restart re-syncs from the gateway via populate_from_gateway.

    Best-effort: returns (ok, error_message). Caller should treat failure as a
    soft warning, not a hard publish failure (gateway DB has the slug, restart
    will eventually self-heal).
    """
    import json as _json
    import urllib.request
    import urllib.error
    payload = {"port": int(port)}
    if preview_id:
        payload["preview_id"] = preview_id
    try:
        req = urllib.request.Request(
            f"{_LOCAL_AGENT_BASE}/community/_internal/publish",
            data=_json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = _json.loads(resp.read())
            return (bool(body.get("ok")), None)
    except urllib.error.HTTPError as e:
        try:
            detail = _json.loads(e.read()).get("detail", "")
        except Exception:
            detail = ""
        return (False, f"HTTP {e.code}: {detail}")
    except Exception as e:
        return (False, str(e))


def _notify_local_unpublish(port: int) -> tuple[bool, str | None]:
    """Tell the local agent process to remove this port from the whitelist."""
    import json as _json
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(
            f"{_LOCAL_AGENT_BASE}/community/_internal/unpublish",
            data=_json.dumps({"port": int(port)}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = _json.loads(resp.read())
            return (bool(body.get("ok")), None)
    except urllib.error.HTTPError as e:
        try:
            detail = _json.loads(e.read()).get("detail", "")
        except Exception:
            detail = ""
        return (False, f"HTTP {e.code}: {detail}")
    except Exception as e:
        return (False, str(e))


def _verify_public_url(url: str, attempts: int = 5, delay: float = 2.0) -> tuple[bool, int | None]:
    """Post-flight: HEAD the public URL to confirm it actually serves traffic.

    Returns (success, last_status). success=True if any attempt returns < 500.
    """
    import time
    import urllib.request
    import urllib.error
    last_status: int | None = None
    for i in range(max(1, attempts)):
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as resp:
                last_status = resp.status
                if last_status < 500:
                    return (True, last_status)
        except urllib.error.HTTPError as e:
            last_status = e.code
            if last_status < 500 and last_status != 403:
                # Anything that isn't a 403 (whitelist issue) or 5xx is "alive"
                return (True, last_status)
        except Exception:
            last_status = None
        if i < attempts - 1:
            time.sleep(delay)
    return (False, last_status)


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
    """Enumerate files in a project's current state via GitHub Trees API.

    `project_type` is accepted for signature stability but no longer affects
    the path. The community-projects layout was flattened in 2026-05-14:
    `projects/{user_id}/{slug}/...`, with type kept only as runtime metadata
    inside project.yaml. Old `projects/{type}s/...` paths are migrated
    in-place by the gateway.
    """
    import urllib.request
    import json

    repo = "Starchild-ai-agent/community-projects"
    prefix = f"projects/{user_id}/{slug}/"

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

    # Gateway DB has the slug now. Two more steps must succeed for the public
    # URL to actually serve traffic:
    #   (1) Local agent process must whitelist this port in CommunityRegistry,
    #       otherwise its /community/{port}/ proxy returns 403 "Port not
    #       published" until the next container restart.
    #   (2) The full path public URL → gateway → agent should round-trip.
    sync_ok, sync_err = _notify_local_publish(int(port), preview_id)

    public_url = f"{_public_url_base()}/{final_slug}"

    # Post-flight verify: HEAD the public URL with retries. Skip if local sync
    # failed — no point waiting 10s for something we know will 403.
    verify_ok: bool | None = None
    verify_status: int | None = None
    if sync_ok:
        verify_ok, verify_status = _verify_public_url(public_url, attempts=4, delay=2.0)

    # If either local sync or post-flight failed, roll back the gateway
    # registration and surface a clear error. We DO NOT want a half-published
    # state where the gateway points at a port the agent rejects.
    if not sync_ok or verify_ok is False:
        try:
            gateway.preview_unregister(slug=final_slug, owner_user_id=user_id)
        except Exception:
            pass
        if not sync_ok:
            return {
                "ok": False,
                "error": (
                    "Gateway registered the slug but the local agent process could not "
                    "whitelist port "
                    f"{port} (sync error: {sync_err}). Rolled back. "
                    "If this persists, restart the container — the registry will "
                    "re-sync from the gateway on startup."
                ),
            }
        return {
            "ok": False,
            "error": (
                f"Gateway registered the slug and the local agent whitelisted port {port}, "
                f"but the public URL still returns HTTP {verify_status} after 4 attempts. "
                "Rolled back. This usually means the gateway routing or upstream is "
                "misconfigured — check community.iamstarchild.com health."
            ),
        }

    return {
        "ok": True,
        "slug": final_slug,
        "url": public_url,
        "port": port,
        "verified_status": verify_status,
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

    # Mirror the publish-side fix: tell the local agent process to drop the
    # port from its in-memory CommunityRegistry too. The gateway response
    # carries the deleted port — we reuse it instead of re-querying.
    deleted = body.get("deleted") or {}
    deleted_port = deleted.get("port")
    sync_note = ""
    if isinstance(deleted_port, int) and deleted_port > 0:
        sync_ok, sync_err = _notify_local_unpublish(deleted_port)
        if not sync_ok:
            sync_note = (
                f" (note: local registry sync failed: {sync_err}; "
                "port will be removed from the in-process whitelist on next restart)"
            )

    return {
        "ok": True,
        "slug": final_slug,
        "message": f"Unpublished '{final_slug}'. The URL is no longer accessible.{sync_note}",
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


# ─── Dashboard listing (third action — discoverability) ─────────────
#
# These are the third independent share action, distinct from
# publish_preview (URL access) and open_source (code release):
#
#   publish_preview  → Audience can VISIT if they know the URL
#   list_in_dashboard→ Audience can DISCOVER via the public Project
#                      Dashboard (browseable gallery)
#   open_source      → Audience can FORK the code
#
# A preview is created with a private listing by default
# (publish_preview's ensureDefaultListing). The user must explicitly
# call list_in_dashboard() to make it discoverable. We do NOT
# auto-list — keeping the three actions orthogonal so users always
# know exactly what they're sharing.

def list_in_dashboard(
    slug: str,
    name: str | None = None,
    description: str = "",
    cover_url: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Show this preview on the public Project Dashboard.

    Requires publish_preview() to have run for `slug` first — gateway
    rejects with 404 if no listing row exists yet.

    Args:
        slug: Public slug (the same one returned by publish_preview).
        name: Display name on the dashboard card. Defaults to slug.
        description: Short description shown on the card (≤500 chars).
        cover_url: Optional cover image URL. Must be on an allowed
            domain (storage.googleapis.com, image.thum.io, api.microlink.io)
            — gateway rejects others with 400. If omitted, gateway
            captures a screenshot of the live preview asynchronously.
        tags: Up to 5 short tags (≤20 chars each).

    Returns:
        {"ok": True, "listing": {...}, "url": "https://..."} on success
        {"ok": False, "error": ...} on failure
    """
    user_id = _user_id()
    if not name:
        name = slug
    try:
        status, body = gateway.listing_publish(
            slug=slug,
            owner_user_id=user_id,
            name=name,
            description=description,
            cover_url=cover_url,
            tags=tags,
            is_public=True,
        )
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status == 404:
        return {
            "ok": False,
            "error": (
                f"No preview found for slug '{slug}'. "
                f"Call publish_preview() first to allocate the URL, "
                f"then list_in_dashboard() to make it discoverable."
            ),
        }
    if status == 403:
        return {
            "ok": False,
            "error": f"You don't own slug '{slug}'.",
        }
    if status != 200:
        return {
            "ok": False,
            "error": body.get("error", f"Gateway returned {status}"),
        }

    listing = body.get("listing", {})
    return {
        "ok": True,
        "listing": listing,
        "url": f"{_public_url_base()}/{slug}",
        "dashboard_url": f"{_public_url_base()}/projects",
    }


def unlist_from_dashboard(slug: str) -> dict[str, Any]:
    """Remove this preview from the Project Dashboard.

    The preview URL keeps working — only the dashboard listing row
    is deleted, along with view/favorite counts. To temporarily hide
    instead, use list_in_dashboard with a separate is_public toggle
    (currently always publishes; use the lower-level
    gateway.listing_publish(is_public=False) if needed).

    Args:
        slug: Public slug to unlist.

    Returns:
        {"ok": True} on success
        {"ok": False, "error": ...} on failure (404 if not listed)
    """
    user_id = _user_id()
    try:
        status, body = gateway.listing_unlist(slug=slug, owner_user_id=user_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status == 404:
        return {
            "ok": False,
            "error": f"Slug '{slug}' is not listed on the dashboard.",
        }
    if status != 200:
        return {
            "ok": False,
            "error": body.get("error", f"Gateway returned {status}"),
        }
    return {"ok": True}


def get_listing_status(slug: str) -> dict[str, Any]:
    """Return current dashboard listing state for a slug.

    Used to answer 'is this on the dashboard yet?' before deciding
    whether to call list_in_dashboard() or unlist_from_dashboard().

    Returns:
        {"ok": True, "exists": True, "is_public": bool, "listing": {...}}
        {"ok": True, "exists": False}    — never published
        {"ok": False, "error": ...}      — gateway error
    """
    try:
        status, body = gateway.listing_get(slug=slug)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status == 404:
        return {"ok": True, "exists": False}
    if status != 200:
        return {
            "ok": False,
            "error": body.get("error", f"Gateway returned {status}"),
        }

    # /by-slug endpoint hard-filters is_public=true (private rows return
    # 404), so any 200 response means the listing is currently public.
    # Private listings cannot be observed through this path — use
    # gateway.listing_publish(is_public=False) to flip a public listing
    # back to private if needed (no read-back support today).
    project = body.get("project", {}) if isinstance(body, dict) else {}
    return {
        "ok": True,
        "exists": True,
        "is_public": True,
        "listing": project,
    }
