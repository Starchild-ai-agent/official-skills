#!/usr/bin/env python3
"""Download and extract a migration bundle from the relay.

Usage:
    python3 download.py <CODE> <DOWNLOAD_TOKEN>

Both CODE and DOWNLOAD_TOKEN are printed by the source agent after export.
The relay is reached over the public internet — no Fly network required.
"""

import json
import os
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

# Internal URL is tried first so the download is recorded under the machine's
# Fly-internal IPv6 (fdaa::/16).  This is required for the migration reward
# system: credit-api looks up completion by the machine's internal IPv6, and
# the relay only records the downloader's actual client IP.
# If running outside the Fly network the internal URL will fail; we fall back
# to the public URL automatically (reward not grantable in that case, but the
# bundle is still delivered).
RELAY_INTERNAL = "http://sc-agent-migration.fly.internal:8080"
RELAY_PUBLIC = "https://sc-agent-migration.fly.dev"
WORKSPACE = Path("/data/workspace")
EXTRACT_DIR = WORKSPACE / "migration"

# Max bundle size: 50MB
MAX_SIZE = 50 * 1024 * 1024


def _do_request(url: str, download_token: str, timeout: int) -> bytes:
    """Make a single GET request. Raises urllib.error.* on failure."""
    req = urllib.request.Request(
        url,
        headers={"X-Download-Token": download_token},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(MAX_SIZE + 1)


def download_bundle(code: str, download_token: str) -> bytes:
    """Download bundle from relay using the download token.

    Tries the Fly-internal URL first (so the relay records the machine's
    internal IPv6, which is required for the migration reward).  Falls back
    to the public URL if the internal endpoint is unreachable (e.g. when
    running outside the Fly network).
    """
    internal_url = f"{RELAY_INTERNAL}/paste/{code}"
    public_url = f"{RELAY_PUBLIC}/paste/{code}"

    # --- attempt internal (short timeout: if not on Fly it will fail fast) ---
    try:
        data = _do_request(internal_url, download_token, timeout=10)
        print("(downloaded via Fly internal network — migration reward eligible)")
        if len(data) > MAX_SIZE:
            print(f"ERROR: Bundle too large ({len(data)} bytes, max {MAX_SIZE}).", file=sys.stderr)
            sys.exit(1)
        return data
    except urllib.error.HTTPError as e:
        # HTTP errors from the relay are authoritative — don't fall back,
        # surface the error directly.
        body = e.read().decode(errors="replace")
        try:
            msg = json.loads(body).get("message", body)
        except Exception:
            msg = body
        if e.code == 401:
            print(f"ERROR: Invalid download token — {msg}", file=sys.stderr)
        elif e.code == 404:
            print(f"ERROR: Code not found — expired or already used.", file=sys.stderr)
        elif e.code == 410:
            print(f"ERROR: Code expired — ask the source agent for a new export.", file=sys.stderr)
        elif e.code == 429:
            print(f"ERROR: Rate limited — too many failed attempts.", file=sys.stderr)
        else:
            print(f"ERROR: HTTP {e.code}: {msg}", file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, OSError):
        # Internal network unreachable — fall back to public URL.
        print("(internal network unreachable, falling back to public URL — migration reward will not be granted)")

    # --- fallback: public URL ---
    try:
        data = _do_request(public_url, download_token, timeout=60)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            msg = json.loads(body).get("message", body)
        except Exception:
            msg = body
        if e.code == 401:
            print(f"ERROR: Invalid download token — {msg}", file=sys.stderr)
        elif e.code == 404:
            print(f"ERROR: Code not found — expired or already used.", file=sys.stderr)
        elif e.code == 410:
            print(f"ERROR: Code expired — ask the source agent for a new export.", file=sys.stderr)
        elif e.code == 429:
            print(f"ERROR: Rate limited — too many failed attempts.", file=sys.stderr)
        else:
            print(f"ERROR: HTTP {e.code}: {msg}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Cannot reach relay: {e.reason}", file=sys.stderr)
        sys.exit(1)

    if len(data) > MAX_SIZE:
        print(f"ERROR: Bundle too large ({len(data)} bytes, max {MAX_SIZE}).", file=sys.stderr)
        sys.exit(1)

    return data


def validate_and_extract(data: bytes) -> dict:
    """Validate tar.gz and extract to migration/."""
    if EXTRACT_DIR.exists():
        import shutil
        shutil.rmtree(EXTRACT_DIR)

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
        f.write(data)
        tmp_path = f.name

    try:
        with tarfile.open(tmp_path, "r:gz") as tar:
            # Security: check for path traversal
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    print(f"ERROR: Dangerous path in archive: {member.name}", file=sys.stderr)
                    sys.exit(1)

            EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
            tar.extractall(EXTRACT_DIR, filter="data")
    except tarfile.TarError as e:
        print(f"ERROR: Invalid tar.gz archive: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        os.unlink(tmp_path)

    # Validate manifest
    manifest_path = EXTRACT_DIR / "manifest.json"
    if not manifest_path.exists():
        print("ERROR: No manifest.json found in bundle root.", file=sys.stderr)
        sys.exit(1)

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid manifest.json: {e}", file=sys.stderr)
        sys.exit(1)

    if "version" not in manifest:
        print("ERROR: manifest.json missing 'version' field.", file=sys.stderr)
        sys.exit(1)

    return manifest


def summarize(manifest: dict):
    """Print a summary of the extracted bundle."""
    print(f"✅ Bundle downloaded and extracted to migration/")
    print(f"   Source:  {manifest.get('source', 'unknown')}")
    print(f"   Version: {manifest.get('version')}")
    if desc := manifest.get("description"):
        print(f"   Desc:    {desc}")
    print()

    components = []

    agent_mem = EXTRACT_DIR / "memory" / "agent.json"
    if agent_mem.exists():
        data = json.loads(agent_mem.read_text())
        n = len(data.get("entries", []))
        components.append(f"  📝 Agent memory: {n} entries")

    user_mem = EXTRACT_DIR / "memory" / "user.json"
    if user_mem.exists():
        data = json.loads(user_mem.read_text())
        n = len(data.get("entries", []))
        components.append(f"  👤 User memory: {n} entries")

    profile = EXTRACT_DIR / "identity" / "profile.json"
    if profile.exists():
        data = json.loads(profile.read_text())
        fields = [k for k in ["name", "vibe", "emoji", "creature"] if data.get(k)]
        components.append(f"  🎭 Identity: {', '.join(fields)}")

    soul = EXTRACT_DIR / "identity" / "soul.md"
    if soul.exists():
        lines = len(soul.read_text().strip().splitlines())
        components.append(f"  💫 Soul: {lines} lines")

    settings = EXTRACT_DIR / "user" / "settings.json"
    if settings.exists():
        data = json.loads(settings.read_text())
        fields = [k for k in ["name", "timezone", "language", "what_to_call"] if data.get(k)]
        components.append(f"  ⚙️  User settings: {', '.join(fields)}")

    tasks = EXTRACT_DIR / "tasks" / "tasks.json"
    if tasks.exists():
        data = json.loads(tasks.read_text())
        n = len(data.get("tasks", []))
        components.append(f"  ⏰ Tasks: {n} scheduled tasks")

    env_keys = EXTRACT_DIR / "env" / "keys.json"
    if env_keys.exists():
        data = json.loads(env_keys.read_text())
        n = len(data.get("keys", []))
        components.append(f"  🔑 Env keys: {n} variables needed")

    files_dir = EXTRACT_DIR / "files"
    if files_dir.exists():
        files = list(files_dir.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        if file_count:
            components.append(f"  📁 Files: {file_count} files")

    if components:
        print("Components found:")
        print("\n".join(components))
    else:
        print("⚠️  Bundle contains only manifest — no data components found.")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 download.py <CODE> <DOWNLOAD_TOKEN>", file=sys.stderr)
        print("  CODE:           8-character migration code", file=sys.stderr)
        print("  DOWNLOAD_TOKEN: token returned at upload time", file=sys.stderr)
        sys.exit(1)

    code = sys.argv[1].strip().upper()
    download_token = sys.argv[2].strip()

    if len(code) != 8:
        print("ERROR: Code must be exactly 8 characters.", file=sys.stderr)
        sys.exit(1)

    if not download_token:
        print("ERROR: Download token cannot be empty.", file=sys.stderr)
        sys.exit(1)

    print(f"Downloading bundle (code: {code}) ...")
    data = download_bundle(code, download_token)
    print(f"Downloaded {len(data):,} bytes")

    manifest = validate_and_extract(data)
    summarize(manifest)


if __name__ == "__main__":
    main()
