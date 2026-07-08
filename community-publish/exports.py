"""community-publish skill exports.

This skill handles TWO distinct concepts — keep them separate:

  PUBLISH (发布) — make something accessible:
    - publish_preview()      → public URL for a running service
    - unpublish_preview()    → remove the public URL
    - list_published_previews() → list your public URLs
    - open_source()          → push code to community GitHub
    - remove_open_source()   → delete code from GitHub
    - list_open_source()     → browse open-sourced code
    - get_open_source()      → fetch one project's metadata
    - fork()                 → install someone's project locally
    - validate_open_source() → pre-flight check
    - link_to_listing()      → manual cross-link repair (rare)

  LIST (上架) — make something discoverable/purchasable on the marketplace:
    Free listing (no review, no pricing):
      - list_in_dashboard()      → show on /projects gallery
      - unlist_from_dashboard()  → hide from gallery (soft, preserves stats)
      - delete_listing()         → permanently delete listing row
      - get_listing_status()     → check if listed
    Paid listing (x402 charging; review is an optional advisory self-check):
      - create_paid_service()    → create a service record
      - submit_for_review()      → run the 5-check self-report (advisory)
      - get_review_status()      → poll review progress
      - publish_service()        → go live (any pre-listed state; review never gates)
      - unpublish_service()      → take down
      - list_my_services()       → list your services
      - get_service()            → fetch one service
      - update_service()         → update service fields
      - delete_service()         → delete a service

Publishing and listing are independent. A project can be published (URL
works) without being listed (not on the gallery), and vice versa. Paid
listing requires a published URL first (the api_endpoint must be reachable).

Cross-link binding lives in project.yaml under `publisher:`. Either side can
register the binding first; the gateway holds a pending entry until the
counterpart arrives. No manual link step needed in the typical flow.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/community-publish")
    from exports import open_source, publish_preview, list_in_dashboard
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

    This is a PUBLISH action (发布代码) — it pushes code to GitHub so others
    can fork it. It does NOT list anything on the marketplace. To make a
    project discoverable, call list_in_dashboard() (free) or
    create_paid_service() (paid) separately after publishing.

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


def _detect_x402_billing(port: int) -> bool:
    """Best-effort probe: does the local service on `port` charge via x402?

    Checks /.well-known/x402 (discovery index) and whether the root route
    answers 402. 2s timeout each; any failure returns False — detection
    must never break or slow down publishing.

    Known limitation: a service that bills only on sub-routes AND has no
    discovery document is not detected. Acceptable — the x402 quickstart
    ships /.well-known/x402 on every gateway.
    """
    import json
    import urllib.request
    import urllib.error
    base = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(base + "/.well-known/x402", timeout=2) as r:
            if r.status == 200:
                # Static sites with SPA fallback answer 200 HTML for ANY
                # path — only count a real x402 discovery document: JSON
                # with x402 marker fields.
                body = r.read(65536)
                try:
                    doc = json.loads(body)
                except Exception:
                    doc = None
                if isinstance(doc, dict) and (
                    "x402Version" in doc or "accepts" in doc or "resources" in doc
                ):
                    return True
    except urllib.error.HTTPError:
        pass
    except Exception:
        pass
    try:
        urllib.request.urlopen(base + "/", timeout=2)
    except urllib.error.HTTPError as e:
        if e.code == 402:
            return True
    except Exception:
        pass
    return False


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

    x402_detected = _detect_x402_billing(port)
    return {
        "ok": True,
        "slug": final_slug,
        "url": public_url,
        "port": port,
        "verified_status": verify_status,
        "x402_detected": x402_detected,
        **({"next_step": (
            "x402 billing detected on this service — a public URL is NOT a "
            "paid listing. The marketplace will show nothing (or 'free') "
            "until you complete: create_paid_service(...) -> "
            "publish_service(service_id). Optionally run submit_for_review() "
            "for an advisory 5-check self-report."
        )} if x402_detected else {}),
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
    """Show this preview on the public Service Marketplace.

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
    """Hide this preview from the Service Marketplace (soft unlist).

    The preview URL keeps working and the listing row is preserved
    (view_count / favorite_count retained). Only is_public is set to
    False so the project card disappears from Explore but still shows
    in "My Projects". To permanently delete the listing row, use
    delete_listing().

    Args:
        slug: Public slug to unlist.

    Returns:
        {"ok": True} on success
        {"ok": False, "error": ...} on failure (404 if not listed)
    """
    user_id = _user_id()

    # Fetch current listing data so we can preserve name/description/etc.
    try:
        get_status, get_body = gateway.listing_get(slug=slug)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if get_status == 404:
        return {
            "ok": False,
            "error": f"Slug '{slug}' is not listed on the dashboard.",
        }
    if get_status != 200:
        return {
            "ok": False,
            "error": get_body.get("error", f"Gateway returned {get_status}"),
        }

    listing = get_body.get("listing") or get_body
    name = listing.get("name", slug)
    description = listing.get("description", "")
    cover_url = listing.get("cover_url") or None
    tags = listing.get("tags") or None

    try:
        status, body = gateway.listing_publish(
            slug=slug,
            owner_user_id=user_id,
            name=name,
            description=description,
            cover_url=cover_url,
            tags=tags,
            is_public=False,
        )
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

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


def delete_listing(slug: str) -> dict[str, Any]:
    """Permanently delete a free project listing (owner only).

    This removes the listing row entirely from the database, including
    view_count and favorite_count. The preview URL keeps working — only
    the marketplace listing is removed.

    To temporarily hide instead of permanently delete, use
    unlist_from_dashboard() (sets is_public=False, preserves stats).

    Args:
        slug: Public slug to delete.

    Returns:
        {"ok": True} on success
        {"ok": False, "error": ...} on failure (404 if not found)
    """
    user_id = _user_id()
    try:
        status, body = gateway.listing_delete(slug=slug, owner_user_id=user_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status == 404:
        return {
            "ok": False,
            "error": f"Slug '{slug}' listing not found or not owned by you.",
        }
    if status != 200:
        return {
            "ok": False,
            "error": body.get("error", f"Gateway returned {status}"),
        }
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════
# PAID SERVICE LISTING — create paid services on the Service Marketplace.
# These require x402 charging. Review is ADVISORY: an optional 5-check
# self-report for the owner — it never gates publishing.
# Completely different from the free listing flow above.
#
# Lifecycle: published → listed (publish any time; optional advisory self-check: pending → approved/rejected)
# ════════════════════════════════════════════════════════════════════════

def create_paid_service(
    name: str,
    description: str,
    category: str,
    service_type: str,
    api_endpoint: str,
    provider_wallet: str,
    pricing_model: str,
    price: float,
    project_slug: str | None = None,
    cover_url: str | None = None,
    tags: list[str] | None = None,
    free_trial_count: int | None = None,
    api_documentation: str | None = None,
    example_request: str | None = None,
    example_response: str | None = None,
    service_description: str | None = None,
    pricing_options: list[dict] | None = None,
    api_endpoints: list[dict] | None = None,
) -> dict[str, Any]:
    """Create a paid service listing on the Service Marketplace.

    This is a LIST action (上架) — it creates a service record that, after
    review and publishing, will be discoverable and purchasable. It does
    NOT publish a URL or push code — use publish_preview() and open_source()
    first.

    Required by service_type (validated here; the reviewer rejects if missing):
        - paid_project: service_description
        - paid_api: api_documentation, example_request, example_response

    Prerequisites:
        - The project must have a public URL (publish_preview() first).
        - The api_endpoint must implement x402 charging (return 402 when
          unpaid, 200 + data after payment). Use the x402 skill to set
          this up.

    Args:
        name: Service display name (≤500 chars).
        description: Service description (Markdown).
        category: Service category (e.g. "数据服务", "工具服务").
        service_type: "paid_project" or "paid_api".
        api_endpoint: The x402 charge endpoint URL. For paid_project this
            is the project's public URL; for paid_api it's the external
            API URL.
        provider_wallet: Base chain wallet address to receive payments.
        pricing_model: "pay_per_use", "lifetime", "monthly", "weekly",
            "quarterly", "yearly", or "prepaid". With pricing_options this is
            the default plan.
        price: Price in USDC (>0).
        project_slug: Required for paid_project (the full published slug WITH
            user prefix, e.g. "33-my-app"). OPTIONAL for paid_api — only set
            this when the user explicitly wants to link a free Starchild
            project page with this paid API (the "free webpage + paid API"
            pattern, Flow D in SKILL.md). Do NOT pass project_slug for
            standalone paid APIs with no associated project page. The backend
            validates the slug against project_listings and silently clears
            non-existent slugs. Must be the full slug with user prefix.
        cover_url: Optional cover image URL.
        tags: Optional list of ≤5 tags (≤20 chars each).
        free_trial_count: Optional, only for pay_per_use (N free calls).
        api_documentation: Required for paid_api (Markdown, with params +
            response format + example).
        example_request: Required for paid_api (curl/HTTP example).
        example_response: Required for paid_api (JSON example response).
        service_description: Required for paid_project (what subscribers get).
        pricing_options: Optional multi-plan list (see SKILL.md "multiple
            pricing plans"): [{"pricing_model", "price", "is_default", "label"}].

    Returns:
        {"ok": True, "service": {...}, "service_id": "..."} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    if service_type not in ("paid_project", "paid_api"):
        return {"ok": False, "error": f"service_type must be 'paid_project' or 'paid_api', got: {service_type!r}"}
    _MODES = ("pay_per_use", "lifetime", "monthly", "weekly", "quarterly", "yearly", "prepaid")
    if pricing_model not in _MODES:
        return {"ok": False, "error": f"pricing_model must be one of {_MODES}, got: {pricing_model!r}"}
    if price <= 0:
        return {"ok": False, "error": f"price must be positive, got: {price}"}
    # paid_api + project_slug is the "free webpage + paid API" pattern (Flow D
    # in SKILL.md): the project page serves as the API's introduction page.
    # Upgrade to paid_project BEFORE required-field validation so the upgraded
    # type's requirements (service_description) are enforced, the frontend
    # shows "View Project" correctly, and the marketplace merges the cards.
    project_slug_warning: str | None = None
    if project_slug and service_type == "paid_api":
        service_type = "paid_project"
        project_slug_warning = (
            f"project_slug='{project_slug}' was passed — service_type has been "
            "auto-upgraded from 'paid_api' to 'paid_project' (the 'free webpage "
            "+ paid API' pattern, Flow D). The project page will serve as the "
            "API's introduction page in the marketplace."
        )
    _missing = []
    if service_type == "paid_project" and not service_description:
        _missing.append("service_description (what subscribers get)")
    if service_type == "paid_api":
        if not api_documentation:
            _missing.append("api_documentation (markdown with a parameter "
                            "table, a non-empty Response/响应格式 section, "
                            "and an example)")
        if not example_request:
            _missing.append("example_request")
        if not example_response:
            _missing.append("example_response")
    if _missing:
        return {"ok": False, "error":
                f"{service_type} requires: {', '.join(_missing)} — the "
                "gateway and the self-check both treat them as required, so "
                "they are enforced at call time."}

    payload: dict[str, Any] = {
        "name": name,
        "description": description,
        "category": category,
        "service_type": service_type,
        "api_endpoint": api_endpoint,
        "provider_wallet": provider_wallet,
        "pricing_model": pricing_model,
        "price": price,
    }
    # project_slug: REQUIRED for paid_project — the project page that
    # subscribers access. (paid_api + project_slug was already upgraded to
    # paid_project above, before validation.)
    if project_slug:
        payload["project_slug"] = project_slug
    if cover_url:
        payload["cover_url"] = cover_url
    if tags:
        payload["tags"] = [str(t)[:20] for t in tags[:5]]
    if free_trial_count is not None:
        payload["free_trial_count"] = free_trial_count
    if api_documentation:
        payload["api_documentation"] = api_documentation
    if example_request:
        payload["example_request"] = example_request
    if example_response:
        payload["example_response"] = example_response
    if service_description:
        payload["service_description"] = service_description
    if api_endpoints:
        payload["api_endpoints"] = api_endpoints
    if pricing_options:
        # multi-plan (docs: 多支付方式): [{"pricing_model": "weekly", "price": 3,
        # "is_default": True, "label": "Weekly"}, ...] — gateway stores them in
        # service_pricing_options; buyers pick a plan on the detail page.
        payload["pricing_options"] = pricing_options

    try:
        status, body = gateway.service_create(uid, payload)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 201:
        return {
            "ok": False,
            "error": body.get("error", f"Gateway returned HTTP {status}"),
            "http_status": status,
        }

    service = body.get("service", {})
    result: dict[str, Any] = {
        "ok": True,
        "service": service,
        "service_id": service.get("id"),
        "review_status": service.get("review_status", "published"),
        "next_step": (
            "Service created in published state (URL accessible but not listed). "
            "Call publish_service(service_id) to list it on the marketplace — "
            "review is advisory and never blocks publishing. Recommended: also run "
            "submit_for_review(service_id) and show the 5-check report to the user "
            "so they can confirm buyers can actually pay."
        ),
    }
    # Surface client-side warning (paid_api + project_slug passed)
    if project_slug_warning:
        result["project_slug_warning"] = project_slug_warning
    # Surface server-side warning (backend cleared a non-existent project_slug)
    backend_warning = body.get("warning")
    if backend_warning:
        result["project_slug_warning"] = backend_warning
    return result


def submit_for_review(service_id: str) -> dict[str, Any]:
    """Run the automated 5-check self-report for a paid service (ADVISORY).

    Checks: api_reachable, pricing_consistency, x402_payment, response_match,
    doc_completeness. The result is a report for the OWNER — it never gates
    publish_service(), and a check run against a listed service never
    delists it. Pre-listed services show 'pending' while the check runs.

    Args:
        service_id: The UUID returned by create_paid_service().

    Returns:
        {"ok": True, "service": {...}, "review_task_id": "..."} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_submit_review(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    service = body.get("service", {})
    return {
        "ok": True,
        "service": service,
        "review_task_id": body.get("review_task_id"),
        "review_status": service.get("review_status", "pending"),
        "next_step": "Review is running asynchronously. Poll get_review_status() until it's no longer 'pending'.",
    }


def get_review_status(service_id: str) -> dict[str, Any]:
    """Poll the review status of a paid service.

    Returns the current review_status (published/pending/approved/rejected),
    review_feedback (if rejected), and the latest review task with
    per-check details.

    Args:
        service_id: The UUID returned by create_paid_service().

    Returns:
        {"ok": True, "review_status": "...", "review_feedback": ...,
         "latest_task": {...}} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_review_status(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    review_status = body.get("review_status", "")
    latest_task = body.get("latest_task") or {}
    task_status = latest_task.get("status", "")
    result: dict[str, Any] = {
        "ok": True,
        "review_status": review_status,
        "review_feedback": body.get("review_feedback"),
        "reviewed_at": body.get("reviewed_at"),
        "latest_task": body.get("latest_task"),
    }
    # The self-check result lives in latest_task. A listed service keeps
    # review_status='listed' while a check runs, so latest_task.status is
    # the authoritative progress signal — check it FIRST.
    if task_status == "pending":
        result["next_step"] = "Self-check still running. Poll again in a few seconds."
        return result
    if review_status == "listed" and task_status in ("approved", "rejected"):
        result["next_step"] = (
            f"Service is live; latest self-check finished: {task_status}. "
            "Show latest_task.checks + feedback to the user (ADVISORY — a "
            "rejected report never delists the service)."
        )
        return result
    if review_status == "approved":
        result["next_step"] = (
            "Self-check passed all 5 checks. Call publish_service(service_id) "
            "to go live (if not already listed)."
        )
    elif review_status == "rejected":
        result["next_step"] = (
            "Self-check found issues (ADVISORY — this does not block publishing "
            "or delist the service). Show review_feedback and latest_task.checks "
            "to the user; they decide whether to fix (update_service() + "
            "submit_for_review() again) or publish as-is."
        )
    elif review_status == "listed":
        result["next_step"] = (
            "Service is live. See latest_task for the most recent self-check "
            "report (checks + feedback)."
        )
    else:
        result["next_step"] = f"Review status: {review_status} — see latest_task for the most recent self-check report."
    return result


def publish_service(service_id: str) -> dict[str, Any]:
    """Publish a paid service — make it live on the marketplace.

    Works from any pre-listed active state (published/approved/rejected/
    pending/unlisted) — review is advisory and never blocks publishing.
    Free projects use list_in_dashboard() instead, not this function.

    Args:
        service_id: The UUID returned by create_paid_service().

    Returns:
        {"ok": True, "service": {...}} on success
        {"ok": False, "error": ...} on failure (e.g. already listed, unavailable, or deleted)
    """
    uid = _user_id()
    try:
        status, body = gateway.service_publish(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    service = body.get("service", {})
    return {
        "ok": True,
        "service": service,
        "review_status": service.get("review_status", "listed"),
        "message": "Service is now live on the marketplace!",
    }


def unpublish_service(service_id: str) -> dict[str, Any]:
    """Take down a published paid service.

    Moves the service from listed/unavailable → unlisted. Already-purchased
    users keep access. To make it live again, re-submit for review and
    publish.

    Args:
        service_id: The UUID returned by create_paid_service().

    Returns:
        {"ok": True, "service": {...}} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_unpublish(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    service = body.get("service", {})
    return {
        "ok": True,
        "service": service,
        "message": "Service taken down. Already-purchased users still have access.",
    }


def list_my_services(cursor: str | None = None, limit: int = 20) -> dict[str, Any]:
    """List the current user's paid services (paginated).

    Args:
        cursor: Pagination cursor (from previous response's next_cursor).
        limit: Max items per page (default 20, max 50).

    Returns:
        {"ok": True, "services": [...], "next_cursor": ..., "has_more": bool}
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_list_mine(uid, cursor=cursor, limit=limit)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, **body}


def get_service(service_id: str) -> dict[str, Any]:
    """Fetch a single paid service by ID (owner only).

    Args:
        service_id: The UUID returned by create_paid_service().

    Returns:
        {"ok": True, "service": {...}} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_get(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, "service": body.get("service", {})}


def update_service(service_id: str, **fields) -> dict[str, Any]:
    """Update a paid service's fields (owner only).

    Common use: fix issues after a rejected review, then re-submit.

    Args:
        service_id: The UUID returned by create_paid_service().
        **fields: Any of the create_paid_service() parameters to update
            (name, description, category, api_endpoint, provider_wallet,
            pricing_model, price, api_documentation, etc.).

    Returns:
        {"ok": True, "service": {...}} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    # Filter out None values so we don't accidentally null out fields
    payload = {k: v for k, v in fields.items() if v is not None}
    if not payload:
        return {"ok": False, "error": "No fields to update — pass at least one keyword argument."}

    try:
        status, body = gateway.service_update(uid, service_id, payload)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, "service": body.get("service", {})}


def delete_service(service_id: str) -> dict[str, Any]:
    """Permanently delete a paid service (owner only).

    This removes the service record entirely. To temporarily take down
    instead, use unpublish_service().

    Args:
        service_id: The UUID returned by create_paid_service().

    Returns:
        {"ok": True} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_delete(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════
# SERVICE MARKETPLACE — browse, review, favorite, earnings
# ════════════════════════════════════════════════════════════════════════
# These are consumer-facing functions for browsing the marketplace,
# writing reviews, managing favorites, and checking earnings.
# They use the same internal-key auth as the provider functions above.


def explore_services(
    search: str | None = None,
    category: str | None = None,
    service_type: str | None = None,
    tags: list[str] | None = None,
    sort: str = "latest",
    cursor: str | None = None,
    limit: int = 20,
    purchased_only: bool = False,
) -> dict[str, Any]:
    """Browse the Service Marketplace with filtering, search, and pagination.

    Args:
        search: Full-text search query.
        category: Filter by category (e.g. "数据服务").
        service_type: Filter by type ("paid_project" or "paid_api").
        tags: Filter by tags (list of strings).
        sort: Sort order — "latest", "popular", "price_low", "price_high", "rating".
        cursor: Pagination cursor from previous response.
        limit: Page size (default 20, max 50).
        purchased_only: If True, return only services the current user has
            purchased or called.

    Returns:
        {"ok": True, "services": [...], "next_cursor": ..., "has_more": bool,
         "total_count": int} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_explore(
            owner_user_id=uid,
            cursor=cursor,
            limit=limit,
            search=search,
            category=category,
            service_type=service_type,
            tags=tags,
            sort=sort,
            filter_purchased=purchased_only,
        )
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {
        "ok": True,
        "services": body.get("services", []),
        "next_cursor": body.get("next_cursor"),
        "has_more": body.get("has_more", False),
        "total_count": body.get("total_count", 0),
    }


def explore_marketplace(
    search: str | None = None,
    paid_only: bool = False,
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """UNIFIED marketplace browse — project cards + standalone services.

    ⭐ Use THIS to find paid services/APIs for a buyer. It wraps
    /api/projects/explore-all (the same feed the web All/Paid tabs use) and
    is the ONLY search path that also surfaces services merged into public
    project cards. `explore_services()` covers standalone service items
    only — a listed service whose project_slug points to a public project
    is folded into the project card and will NOT appear there.

    Args:
        search: Keyword (matches project/service name, description, tags).
        paid_only: If True, keep only paid items. Applied client-side to the
            fetched page (the endpoint has no server-side paid filter), so a
            page may return fewer than `limit` items — follow `next_cursor`
            for more.
        cursor: Pagination cursor from previous response.
        limit: Page size (default 20).

    Returns:
        {"ok": True, "items": [...], "next_cursor": ..., "has_more": bool}
        Each item has `type`: "service" (standalone — use its `id` with
        get_service_detail) or "project" (card — when `is_paid` is true it
        carries `service_id`, `price`, `pricing_model`; pass `service_id`
        to get_service_detail/get_service_pricing to enter the buy flow).
    """
    try:
        status, body = gateway.marketplace_explore_all(
            search=search, cursor=cursor, limit=limit)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    items = body.get("items") or body.get("projects") or []
    if paid_only:
        items = [i for i in items if i.get("is_paid")]

    return {
        "ok": True,
        "items": items,
        "next_cursor": body.get("next_cursor"),
        "has_more": body.get("has_more", False),
        "total_count": body.get("total_count", 0),
    }


def get_service_categories() -> dict[str, Any]:
    """List all service categories with counts.

    Returns:
        {"ok": True, "categories": [...]} on success
        {"ok": False, "error": ...} on failure
    """
    try:
        status, body = gateway.service_categories()
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, "categories": body.get("categories", [])}


def get_service_detail(service_id: str) -> dict[str, Any]:
    """Get public details for a published service (market view).

    Includes full documentation, pricing options, and provider info.
    Increments view count. Use get_service() for provider management
    (owner only, includes published/rejected services).

    Args:
        service_id: The service UUID.

    Returns:
        {"ok": True, "service": {...}} on success
        {"ok": False, "error": ...} on failure
    """
    try:
        status, body = gateway.service_detail(service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, "service": body.get("service", {})}


def get_service_pricing(service_id: str) -> dict[str, Any]:
    """Get verified pricing for a published service.

    Performs real-time x402 402-response verification (cached 5 min) to
    ensure the displayed price matches the actual x402-declared price.

    Args:
        service_id: The service UUID.

    Returns:
        {"ok": True, "pricing": {...}, "pricing_options": [...]} on success
        {"ok": False, "error": ...} on failure
    """
    try:
        status, body = gateway.service_pricing(service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, **body}


def get_service_reviews(
    service_id: str,
    sort: str = "latest",
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Get reviews for a service (public).

    Args:
        service_id: The service UUID.
        sort: "latest" or "helpful".
        cursor: Pagination cursor.
        limit: Page size.

    Returns:
        {"ok": True, "reviews": [...], "next_cursor": ..., "has_more": bool,
         "total_count": int} on success
        {"ok": False, "error": ...} on failure
    """
    try:
        status, body = gateway.service_reviews(service_id, cursor=cursor, limit=limit, sort=sort)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {
        "ok": True,
        "reviews": body.get("reviews", []),
        "next_cursor": body.get("next_cursor"),
        "has_more": body.get("has_more", False),
        "total_count": body.get("total_count", 0),
    }


def write_service_review(
    service_id: str,
    rating: int,
    comment: str | None = None,
    is_anonymous: bool = False,
) -> dict[str, Any]:
    """Submit or update a review for a service (upsert — one review per user).

    The user must have purchased or used the service before reviewing.
    Only published services can be reviewed.

    Args:
        service_id: The service UUID.
        rating: Integer 1-5.
        comment: Optional review text.
        is_anonymous: If True, hide the reviewer's identity.

    Returns:
        {"ok": True, "review": {...}} on success
        {"ok": False, "error": ...} on failure
    """
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return {"ok": False, "error": f"rating must be an integer 1-5, got: {rating}"}

    uid = _user_id()
    try:
        status, body = gateway.service_review_create(uid, service_id, rating, comment, is_anonymous)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status not in (200, 201):
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, "review": body.get("review", {})}


def get_user_services(user_id: str, limit: int = 20) -> dict[str, Any]:
    """Get published paid services owned by a specific user (public).

    Used to display a user's published services on their profile.

    Args:
        user_id: The user ID to query.
        limit: Max results.

    Returns:
        {"ok": True, "services": [...], "total_count": int} on success
        {"ok": False, "error": ...} on failure
    """
    try:
        status, body = gateway.service_user_published(user_id, limit=limit)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, "services": body.get("services", []), "total_count": body.get("total_count", 0)}


def favorite_service(service_id: str) -> dict[str, Any]:
    """Add a service to the current user's favorites.

    Args:
        service_id: The service UUID.

    Returns:
        {"ok": True, "inserted": bool} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_favorite_add(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, "inserted": body.get("inserted", False)}


def unfavorite_service(service_id: str) -> dict[str, Any]:
    """Remove a service from the current user's favorites.

    Args:
        service_id: The service UUID.

    Returns:
        {"ok": True, "deleted": bool} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_favorite_remove(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, "deleted": body.get("deleted", False)}


def get_favorite_services(
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List the current user's favorite services (paginated).

    Returns:
        {"ok": True, "services": [...], "next_cursor": ..., "has_more": bool,
         "total_count": int} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_favorites_list(uid, cursor=cursor, limit=limit)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {
        "ok": True,
        "services": body.get("services", []),
        "next_cursor": body.get("next_cursor"),
        "has_more": body.get("has_more", False),
        "total_count": body.get("total_count", 0),
    }


def get_service_purchase_status(service_id: str) -> dict[str, Any]:
    """Check if the current user has purchased or used a service.

    Used to determine review eligibility and UI state (e.g. "Buy" vs "Call").

    Args:
        service_id: The service UUID.

    Returns:
        {"ok": True, "has_purchased": bool, "has_used": bool, ...} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_purchase_status(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, **body}


def get_service_earnings(service_id: str) -> dict[str, Any]:
    """Get earnings statistics for a single service (owner only).

    Includes total revenue, call count, daily earnings trend, etc.

    Args:
        service_id: The service UUID.

    Returns:
        {"ok": True, "total_earnings": ..., "call_count": ..., ...} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_earnings(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, **body}


def get_earnings_summary() -> dict[str, Any]:
    """Get earnings summary across all services owned by the current user.

    Returns:
        {"ok": True, "total_earnings": ..., "service_count": ..., ...} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_earnings_summary(uid)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, **body}


def get_service_onchain_records(
    service_id: str,
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Get on-chain transaction records for a service (owner only).

    Used for payment reconciliation — shows USDC settlements on Base chain.

    Args:
        service_id: The service UUID.
        cursor: Pagination cursor.
        limit: Page size.

    Returns:
        {"ok": True, "records": [...], "next_cursor": ..., "has_more": bool}
        on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_onchain_records(uid, service_id, cursor=cursor, limit=limit)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {
        "ok": True,
        "records": body.get("records", []),
        "next_cursor": body.get("next_cursor"),
        "has_more": body.get("has_more", False),
    }


def restore_service(service_id: str) -> dict[str, Any]:
    """Restore an unavailable service back to published state.

    Used when a service was automatically taken down (e.g. health check
    failure) and the provider has fixed the issue.

    Args:
        service_id: The service UUID.

    Returns:
        {"ok": True, "service": {...}} on success
        {"ok": False, "error": ...} on failure
    """
    uid = _user_id()
    try:
        status, body = gateway.service_restore(uid, service_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to reach gateway: {e}"}

    if status != 200:
        return {"ok": False, "error": body.get("error", f"Gateway returned HTTP {status}"), "http_status": status}

    return {"ok": True, "service": body.get("service", {})}
