"""Pre-publish validation — mirrors gateway-side checks so we fail fast locally."""
from __future__ import annotations
import os
import re
from typing import Any

from .manifest import VALID_TYPES, SLUG_RE, SEMVER_RE

# Hard-block these path patterns
BLOCKED_PATHS = [
    re.compile(r"(^|/)\.env$"),
    re.compile(r"(^|/)\.env\.(local|production|development)$"),
    re.compile(r"(^|/)secrets/"),
    re.compile(r"\.(key|pem|pfx|p12|der)$"),
    re.compile(r"(^|/)id_rsa(\.pub)?$"),
    re.compile(r"(^|/)id_ed25519(\.pub)?$"),
    re.compile(r"(^|/)\.ssh/"),
    re.compile(r"(^|/)\.aws/credentials"),
    re.compile(r"(^|/)__pycache__/"),
    re.compile(r"\.pyc$"),
    re.compile(r"(^|/)\.git/"),
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)\.venv/"),
]

# Patterns of secrets we scan inside file content
SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OpenAI/Anthropic-style API key (sk-...)"),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{40,}"), "Anthropic API key"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{40,}"), "GitHub fine-grained PAT"),
    (re.compile(r"ghp_[A-Za-z0-9]{36,}"), "GitHub classic PAT"),
    (re.compile(r"gho_[A-Za-z0-9]{36,}"), "GitHub OAuth token"),
    (re.compile(r"glpat-[A-Za-z0-9_\-]{20,}"), "GitLab PAT"),
    (re.compile(r"xox[baprs]-[0-9]+-[0-9]+-[A-Za-z0-9]+"), "Slack token"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "Google API key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key ID"),
    (re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY-----"), "Private key"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{20,}\.eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]+"), "JWT token"),
]

# Skip secret scanning for these binary/noise file types
SKIP_SCAN_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".webm", ".ogg",
    ".zip", ".tar", ".gz", ".tgz", ".bz2",
    ".pdf",
}

REQUIRED_README_SECTIONS = [
    "## What",
    "## Required env",
    "## How to start",
    "## Outputs",          # accepts "## Outputs / Behavior" too
    "## Troubleshooting",
]

MAX_FILE_BYTES = 1_048_576       # 1 MB
MAX_BUNDLE_BYTES = 10_485_760    # 10 MB


def collect_files(project_dir: str) -> list[tuple[str, bytes]]:
    """Walk project_dir, return (relative_path, content_bytes) for each non-blocked file."""
    files: list[tuple[str, bytes]] = []
    for root, dirs, names in os.walk(project_dir):
        # Skip blocked subdirs early
        dirs[:] = [d for d in dirs if not _is_blocked_path(os.path.relpath(os.path.join(root, d), project_dir) + "/")]
        for name in names:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, project_dir).replace("\\", "/")
            if _is_blocked_path(rel):
                continue
            try:
                with open(full, "rb") as f:
                    files.append((rel, f.read()))
            except OSError:
                continue
    return files


def _is_blocked_path(rel: str) -> bool:
    for pat in BLOCKED_PATHS:
        if pat.search(rel):
            return True
    return False


def validate(project_dir: str, manifest: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings).

    Caller should refuse to publish if errors is non-empty.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Manifest top-level
    name = manifest.get("name")
    version = manifest.get("version")
    ptype = manifest.get("type")
    description = manifest.get("description")
    license_ = manifest.get("license")
    entry = manifest.get("entry")

    if not name or not SLUG_RE.match(str(name)):
        errors.append(f"manifest.name invalid (must be lowercase alphanumeric + hyphen, 3-50 chars): {name!r}")
    folder_name = os.path.basename(os.path.abspath(project_dir))
    if name and name != folder_name:
        warnings.append(f"manifest.name '{name}' differs from folder name '{folder_name}' — gateway requires they match")

    if not version or not SEMVER_RE.match(str(version)):
        errors.append(f"manifest.version must be semver (x.y.z), got: {version!r}")

    if ptype not in VALID_TYPES:
        errors.append(f"manifest.type must be one of {VALID_TYPES}, got: {ptype!r}")

    if not description or len(str(description)) < 5:
        errors.append("manifest.description must be at least 5 chars")

    if not license_:
        errors.append("manifest.license required (use SPDX identifier like MIT, Apache-2.0)")

    if not entry:
        errors.append("manifest.entry required (relative path to main file)")

    # Type-specific
    if ptype == "task" and not manifest.get("schedule"):
        errors.append("manifest.schedule required for type=task (cron expression in UTC)")
    if ptype == "service" and not manifest.get("port"):
        errors.append("manifest.port required for type=service (HTTP listening port)")

    # Files on disk
    files = collect_files(project_dir)
    file_paths = {p for p, _ in files}

    # Required files
    for req in ("project.yaml", "PROJECT.md", ".env.example"):
        if req not in file_paths:
            errors.append(f"Missing required file: {req}")

    # Entry must exist
    if entry and entry not in file_paths:
        errors.append(f"manifest.entry '{entry}' not found in project directory")

    # PROJECT.md sections check
    readme_path = os.path.join(project_dir, "PROJECT.md")
    if os.path.isfile(readme_path):
        with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
            readme = f.read()
        missing_sections = []
        for section in REQUIRED_README_SECTIONS:
            # Accept "## Outputs / Behavior" or "## Outputs"
            if section == "## Outputs":
                if not re.search(r"^## Outputs", readme, re.M):
                    missing_sections.append("## Outputs (or '## Outputs / Behavior')")
            else:
                if section not in readme:
                    missing_sections.append(section)
        if missing_sections:
            errors.append(f"PROJECT.md missing required sections: {', '.join(missing_sections)}")

    # env_required must be in .env.example
    env_example_path = os.path.join(project_dir, ".env.example")
    declared_envs: set[str] = set()
    if os.path.isfile(env_example_path):
        with open(env_example_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    declared_envs.add(line.split("=", 1)[0].strip())

    env_required = manifest.get("env_required") or []
    if isinstance(env_required, list):
        for env in env_required:
            if env not in declared_envs:
                errors.append(f"env_required '{env}' not declared in .env.example")

    # Sizes + secret scan
    total_bytes = 0
    for rel, content in files:
        if len(content) > MAX_FILE_BYTES:
            errors.append(f"File too large: {rel} ({len(content)} > {MAX_FILE_BYTES} bytes)")
        total_bytes += len(content)

        ext = os.path.splitext(rel)[1].lower()
        if ext in SKIP_SCAN_EXTS:
            continue
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            continue

        is_env_example = rel == ".env.example" or rel.endswith("/.env.example")
        for pat, label in SECRET_PATTERNS:
            matches = pat.findall(text)
            if not matches:
                continue
            if is_env_example:
                # Allow only obvious placeholders in .env.example
                real = [m for m in matches if not re.search(r"(your|example|placeholder|xxx|todo|change[_-]?me|<.*>)", m, re.I)]
                if not real:
                    continue
            errors.append(f"Possible secret in {rel}: {label}")
            break

    if total_bytes > MAX_BUNDLE_BYTES:
        errors.append(f"Bundle too large: {total_bytes} > {MAX_BUNDLE_BYTES} bytes")

    return errors, warnings
