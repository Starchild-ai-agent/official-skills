"""
MCP Server Registry

Loads pre-configured MCP server definitions from config/mcp_servers.yaml.
Allows mcp_connect to resolve servers by name and mcp_browse to list them.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Cached registry data
_registry: Optional[Dict[str, Dict[str, Any]]] = None
_registry_path: Optional[str] = None


def _find_registry_file() -> Optional[str]:
    """Locate config/mcp_servers.yaml relative to project root."""
    # Walk up from this file to find the project root with config/
    current = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = current / "config" / "mcp_servers.yaml"
        if candidate.exists():
            return str(candidate)
        current = current.parent

    # Fallback: check common locations
    for path in [
        "./config/mcp_servers.yaml",
        os.environ.get("MCP_REGISTRY_PATH", ""),
    ]:
        if path and os.path.exists(path):
            return path

    return None


def _resolve_env_vars(value: str) -> str:
    """Resolve ${VAR} placeholders in a string from environment."""
    import re
    def replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, "")
    return re.sub(r'\$\{(\w+)\}', replacer, value)


def load_registry(force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Load the MCP server registry from YAML.

    Returns:
        Dict mapping server key -> server config
    """
    global _registry, _registry_path

    if _registry is not None and not force_reload:
        return _registry

    path = _find_registry_file()
    if not path:
        logger.warning("MCP registry file not found (config/mcp_servers.yaml)")
        _registry = {}
        return _registry

    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        _registry = data.get("servers", {})
        _registry_path = path
        logger.info(f"Loaded MCP registry: {len(_registry)} servers from {path}")
    except Exception as e:
        logger.error(f"Failed to load MCP registry from {path}: {e}")
        _registry = {}

    return _registry


def get_server(name: str) -> Optional[Dict[str, Any]]:
    """
    Look up a server by registry key.

    Returns:
        Server config dict if found, None otherwise.
    """
    registry = load_registry()
    return registry.get(name)


def resolve_server_config(name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a registry entry into connection parameters ready for manager.connect_*.

    Resolves env var placeholders in headers and checks for missing required env vars.

    Returns:
        Dict with keys: transport, url, command, args, env, headers, missing_env
        or None if not in registry.
    """
    entry = get_server(name)
    if not entry:
        return None

    transport = entry.get("transport", "streamable-http")
    result: Dict[str, Any] = {"transport": transport}

    # Check required env vars
    env_required = entry.get("env_required", [])
    missing = [var for var in env_required if not os.environ.get(var)]
    if missing:
        result["missing_env"] = missing

    if transport == "stdio":
        result["command"] = entry.get("command")
        result["args"] = entry.get("args", [])
        # Build env dict from env_required
        env_dict = {}
        for var in env_required:
            val = os.environ.get(var)
            if val:
                env_dict[var] = val
        if env_dict:
            result["env"] = env_dict
    else:
        result["url"] = entry.get("url")
        # Resolve headers from env
        headers_from_env = entry.get("headers_from_env", {})
        if headers_from_env:
            resolved_headers = {}
            for header_name, template in headers_from_env.items():
                resolved_headers[header_name] = _resolve_env_vars(template)
            result["headers"] = resolved_headers

    return result


def list_servers_by_category() -> Dict[str, List[Dict[str, Any]]]:
    """
    List all registry entries grouped by category.

    Returns:
        Dict mapping category -> list of server summaries
    """
    registry = load_registry()
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for key, entry in registry.items():
        category = entry.get("category", "other")
        summary = {
            "key": key,
            "name": entry.get("name", key),
            "description": entry.get("description", ""),
            "transport": entry.get("transport", "unknown"),
            "auth": entry.get("auth", "none"),
        }
        if entry.get("env_required"):
            summary["env_required"] = entry["env_required"]
        if entry.get("notes"):
            summary["notes"] = entry["notes"]

        grouped.setdefault(category, []).append(summary)

    return grouped


def reload_registry() -> int:
    """Force reload the registry. Returns number of servers loaded."""
    load_registry(force_reload=True)
    return len(_registry or {})
