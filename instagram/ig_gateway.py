"""Composio gateway client.

Follows the shipped ``composio`` skill contract:

* base URL is ``http://composio-gateway.flycast``;
* calls MUST NOT go through sc-proxy;
* search -> schema -> execute, with ``arguments`` as the execute key;
* Instagram posting uses the working legacy slugs
  ``INSTAGRAM_CREATE_MEDIA_CONTAINER`` + ``INSTAGRAM_CREATE_POST``.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

from ig_errors import ProviderError, ToolNotFound
from ig_http import request_json


DEFAULT_GATEWAY = "http://composio-gateway.flycast"

# Canonical name -> provider property candidates.
ARG_ALIASES: Dict[str, List[str]] = {
    "ig_user_id": ["ig_user_id", "ig_id", "instagram_user_id", "user_id"],
    "ig_media_id": ["ig_media_id", "media_id", "ig_media", "media"],
    "ig_comment_id": ["ig_comment_id", "comment_id"],
    "recipient_id": ["recipient_id", "recipient", "igsid", "user_id"],
    "conversation_id": ["conversation_id", "thread_id"],
    "text": ["text", "message", "message_text"],
    "caption": ["caption"],
    "image_url": ["image_url", "image", "media_url"],
    "video_url": ["video_url", "video", "media_url"],
    "creation_id": ["creation_id", "container_id"],
    "limit": ["limit", "count", "amount"],
    "after": ["after", "cursor"],
    "fields": ["fields"],
    "platform": ["platform"],
    "mode": ["mode", "media_type"],
}


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("connections", "data", "items", "results"):
            if isinstance(value.get(key), list):
                return value[key]
        return [value]
    return [value]


def _unwrap(value: Any) -> Any:
    """Peel the gateway's repeated ``{"data": ...}`` envelopes."""
    for _ in range(4):
        if isinstance(value, dict) and "data" in value and set(value.keys()) <= {"data", "error"}:
            if value.get("error"):
                raise ProviderError(str(value["error"]), code="gateway_error")
            value = value["data"]
            continue
        break
    return value


class GatewayClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (
            base_url
            or os.environ.get("COMPOSIO_GATEWAY_URL")
            or DEFAULT_GATEWAY
        ).rstrip("/")
        self._schema_cache: Dict[str, Dict[str, Any]] = {}

    # -- transport ---------------------------------------------------------

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return request_json(
            f"{self.base_url}{path}",
            params=params,
            timeout=30,
            no_proxy=True,
        )

    def _post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        return request_json(
            f"{self.base_url}{path}",
            method="POST",
            body=payload or {},
            timeout=90,
            no_proxy=True,
        )

    # -- discovery ---------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        try:
            data = self._get("/health")
            return {"ok": True, "data": data}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def search(self, query: str) -> Dict[str, Any]:
        return self._post("/internal/search", {"query": query})

    def tool_schema(self, tool: str, *, refresh: bool = False) -> Dict[str, Any]:
        if not refresh and tool in self._schema_cache:
            return self._schema_cache[tool]
        try:
            response = self._post("/internal/tool_schema", {"tool": tool})
        except Exception:
            # A schema miss is non-fatal: execute may still accept the args.
            self._schema_cache[tool] = {}
            return {}
        data = _unwrap(response)
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            data = data["data"]
        schema = data if isinstance(data, dict) else {}
        self._schema_cache[tool] = schema
        return schema

    def schema_properties(self, tool: str) -> Dict[str, Any]:
        schema = self.tool_schema(tool)
        params = schema.get("input_parameters") or schema.get("parameters") or schema
        props = params.get("properties") if isinstance(params, dict) else None
        return props if isinstance(props, dict) else {}

    # -- execution ---------------------------------------------------------

    def execute(self, tool: str, arguments: Dict[str, Any]) -> Any:
        response = self._post(
            "/internal/execute",
            {"tool": tool, "arguments": arguments},
        )
        if isinstance(response, dict) and response.get("error"):
            raise ProviderError(
                str(response["error"]),
                code="gateway_execute_error",
                details={"tool": tool, "tool_schema": response.get("tool_schema")},
            )
        return _unwrap(response)

    def call(
        self,
        tool: str,
        arguments: Dict[str, Any],
        *,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Map canonical args onto the provider's current schema, then execute."""
        props = self.schema_properties(tool)
        mapped: Dict[str, Any] = {}

        for canonical, value in arguments.items():
            if value is None:
                continue
            if not props or canonical in props:
                mapped[canonical] = value
                continue
            for candidate in ARG_ALIASES.get(canonical, []):
                if candidate in props:
                    mapped[candidate] = value
                    break
            else:
                # No schema or no matching alias: send the canonical name so
                # the gateway's own error can teach us the right one.
                mapped[canonical] = value

        if extra:
            mapped.update(extra)

        try:
            return self.execute(tool, mapped)
        except ProviderError as exc:
            message = str(exc.message).lower()
            if "not found" in message or "does not exist" in message:
                raise ToolNotFound(
                    f"Composio tool {tool!r} is not executable on this gateway.",
                    hint="Use the working legacy slug documented in composio/SKILL.md.",
                    details={"tool": tool, "original": exc.message},
                )
            raise

    # -- connections -------------------------------------------------------

    def connections(self, toolkit: str = "instagram") -> List[Dict[str, Any]]:
        try:
            response = self._get(
                "/internal/connections",
                {"toolkit": toolkit},
            )
        except Exception:
            return []
        data = _unwrap(response)
        candidates: Iterable[Any]
        if isinstance(data, dict):
            candidates = data.get("connections") or data.get("data") or []
        else:
            candidates = data or []
        return [c for c in _as_list(candidates) if isinstance(c, dict)]

    def active_connection(self, toolkit: str = "instagram") -> Optional[Dict[str, Any]]:
        active_states = {"ACTIVE", "CONNECTED", "active", "connected"}
        for connection in self.connections(toolkit):
            tk = str(connection.get("toolkit") or connection.get("toolkit_slug") or "").lower()
            if tk and tk != toolkit.lower():
                continue
            status = str(connection.get("status") or connection.get("state") or "").upper()
            if status in active_states or connection.get("is_active") is True:
                return connection
            if connection.get("oauth_completed_active") is True:
                return connection
        return None

    def connect(self, toolkit: str = "instagram") -> Dict[str, Any]:
        response = self._post("/api/connect", {"toolkit": toolkit})
        data = _unwrap(response)
        if not isinstance(data, dict):
            return {"raw": data}
        return data

    def disconnect(self, connection_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/connections/{connection_id}"
        return request_json(url, method="DELETE", timeout=30, no_proxy=True)

    def connected_account_label(self, connection: Dict[str, Any]) -> str:
        meta = connection.get("meta") if isinstance(connection.get("meta"), dict) else {}
        for key in ("username", "account_name", "name", "label"):
            value = connection.get(key) or meta.get(key)
            if value:
                return str(value)
        connection_id = str(connection.get("id") or connection.get("connection_id") or "default")
        return f"composio-{connection_id[:8]}"
