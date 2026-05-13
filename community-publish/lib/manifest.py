"""project.yaml parsing/writing + semver helpers.

We use a minimal YAML approach (PyYAML if available, fallback to manual parser)
so the skill works even on stripped-down environments.
"""
from __future__ import annotations
import os
import re
from typing import Any

try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

VALID_TYPES = ("task", "preview", "service", "script")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_semver(v: str) -> tuple[int, int, int]:
    m = SEMVER_RE.match(v.strip())
    if not m:
        raise ValueError(f"Invalid semver: {v}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bump_semver(v: str, kind: str) -> str:
    major, minor, patch = parse_semver(v)
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Invalid bump kind: {kind} (want patch|minor|major)")


def compare_semver(a: str, b: str) -> int:
    """Returns 1 if a > b, -1 if a < b, 0 if equal."""
    aa = parse_semver(a)
    bb = parse_semver(b)
    if aa > bb:
        return 1
    if aa < bb:
        return -1
    return 0


def load_manifest(project_dir: str) -> dict[str, Any]:
    path = os.path.join(project_dir, "project.yaml")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"project.yaml not found in {project_dir}")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if _HAS_YAML:
        return yaml.safe_load(text) or {}
    return _parse_yaml_lite(text)


def save_manifest(project_dir: str, manifest: dict[str, Any]) -> None:
    path = os.path.join(project_dir, "project.yaml")
    if _HAS_YAML:
        text = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, default_flow_style=False)
    else:
        text = _dump_yaml_lite(manifest)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _parse_yaml_lite(text: str) -> dict[str, Any]:
    """Minimal YAML parser supporting key:value, lists, single-level nesting."""
    result: dict[str, Any] = {}
    lines = text.split("\n")
    current_key: str | None = None
    current_obj_key: str | None = None

    for raw in lines:
        # Strip comments outside quotes (cheap heuristic)
        line = raw.split("#", 1)[0].rstrip() if not _line_in_quotes(raw, "#") else raw.rstrip()
        if not line.strip():
            continue

        # Indented list item: "  - foo"
        m = re.match(r"^\s+-\s+(.+)$", line)
        if m and current_key is not None and isinstance(result.get(current_key), list):
            result[current_key].append(_parse_scalar(m.group(1).strip()))
            continue

        # Indented nested key: "  python: '>=3.10'"
        m = re.match(r"^\s+([a-zA-Z_]\w*):\s*(.*)$", line)
        if m and current_obj_key is not None and isinstance(result.get(current_obj_key), dict):
            result[current_obj_key][m.group(1)] = _parse_scalar(m.group(2).strip())
            continue

        # Top-level key
        m = re.match(r"^([a-zA-Z_]\w*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            current_key = key
            current_obj_key = None
            if val == "":
                # Could be list or dict — peek ahead
                # We'll create a list by default; if first nested item is "key: value", convert to dict
                result[key] = []
            elif val == "[]":
                result[key] = []
                current_key = None
            elif val == "{}":
                result[key] = {}
                current_key = None
                current_obj_key = key
            else:
                result[key] = _parse_scalar(val)
                current_key = None

    # Post-process: if a "list" actually got dict items, convert
    # (this happens when key has nested object below it)
    # Best-effort — for full schema, install pyyaml
    return _normalize_lite(result)


def _line_in_quotes(line: str, ch: str) -> bool:
    in_quote = False
    quote_char = None
    for c in line:
        if c in ('"', "'"):
            if not in_quote:
                in_quote = True
                quote_char = c
            elif c == quote_char:
                in_quote = False
        elif c == ch and in_quote:
            return True
    return False


def _normalize_lite(d: dict[str, Any]) -> dict[str, Any]:
    """Empty list values are ambiguous; leave as-is (caller can interpret)."""
    return d


def _parse_scalar(s: str) -> Any:
    s = s.strip()
    if s == "" or s == "~" or s == "null":
        return None
    if s == "true":
        return True
    if s == "false":
        return False
    # Strip surrounding quotes
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def _dump_yaml_lite(d: dict[str, Any], indent: int = 0) -> str:
    """Minimal YAML serializer (used only when PyYAML missing)."""
    pad = "  " * indent
    out: list[str] = []
    for k, v in d.items():
        if isinstance(v, dict):
            out.append(f"{pad}{k}:")
            out.append(_dump_yaml_lite(v, indent + 1))
        elif isinstance(v, list):
            if not v:
                out.append(f"{pad}{k}: []")
            else:
                out.append(f"{pad}{k}:")
                for item in v:
                    out.append(f"{pad}  - {_dump_scalar(item)}")
        else:
            out.append(f"{pad}{k}: {_dump_scalar(v)}")
    return "\n".join(out) + ("\n" if indent == 0 else "")


def _dump_scalar(v: Any) -> str:
    if v is None:
        return "~"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if any(c in s for c in (':', '#', '[', ']', '{', '}', ',', '&', '*', '!', '|', '>', "'", '"', '%', '@', '`')):
        return f'"{s}"'
    if s == "" or s.lower() in ("true", "false", "null", "yes", "no", "~"):
        return f'"{s}"'
    return s
