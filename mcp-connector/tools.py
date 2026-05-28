"""
MCP Connector Tools

BaseTool implementations that expose MCP connectivity to the Star Child agent.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from core.tool import BaseTool, ToolContext, ToolResult

from . import manager
from .client import MCPError
from .registry import get_server, resolve_server_config, list_servers_by_category

logger = logging.getLogger(__name__)


class MCPConnectTool(BaseTool):
    """Connect to an MCP server."""

    @property
    def name(self) -> str:
        return "mcp_connect"

    @property
    def description(self) -> str:
        return (
            "Connect to an MCP (Model Context Protocol) server. "
            "Pass just a name to connect from the pre-configured registry (use mcp_browse to see available servers), "
            "or provide transport/url/command for ad-hoc connections. "
            "Supports stdio, sse, and streamable-http transports."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": (
                        "Server name. If it matches a registry entry (see mcp_browse), "
                        "connection details are auto-filled. Otherwise, provide transport + url/command."
                    ),
                },
                "transport": {
                    "type": "string",
                    "enum": ["stdio", "sse", "streamable-http"],
                    "description": "Transport type (optional if using a registry server)",
                },
                "command": {
                    "type": "string",
                    "description": "(stdio only) Command to run (e.g., 'npx', 'python', 'node')",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "(stdio only) Command arguments",
                },
                "env": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "(stdio only) Additional environment variables for the subprocess",
                },
                "url": {
                    "type": "string",
                    "description": "(sse/streamable-http only) Server endpoint URL",
                },
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "(sse/streamable-http only) HTTP headers (e.g., auth tokens)",
                },
            },
            "required": ["name"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        name: str,
        transport: Optional[str] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ToolResult:
        try:
            # --- Registry resolution ---
            # If transport is not provided, try to resolve from registry
            from_registry = False
            if not transport:
                resolved = resolve_server_config(name)
                if not resolved:
                    return ToolResult(
                        success=False,
                        error=f"'{name}' is not in the MCP registry and no transport was specified",
                        error_category="missing_parameter",
                        suggested_fix="Use mcp_browse to see available servers, or provide transport + url/command for ad-hoc connections",
                    )

                # Check for missing env vars
                missing = resolved.get("missing_env", [])
                if missing:
                    entry = get_server(name)
                    return ToolResult(
                        success=False,
                        error=f"Missing required environment variables for '{name}': {', '.join(missing)}",
                        error_category="missing_env",
                        suggested_fix=f"Set these env vars before connecting: {', '.join(missing)}",
                        output={"server": entry.get("name", name), "notes": entry.get("notes", "")},
                    )

                transport = resolved["transport"]
                command = command or resolved.get("command")
                args = args or resolved.get("args")
                env = env or resolved.get("env")
                url = url or resolved.get("url")
                headers = headers or resolved.get("headers")
                from_registry = True

            if transport == "stdio":
                if not command:
                    return ToolResult(
                        success=False,
                        error="'command' is required for stdio transport",
                        error_category="missing_parameter",
                        suggested_fix="Provide 'command' (e.g., 'npx', 'python') and optionally 'args'",
                    )
                info = await manager.connect_stdio(name, command, args, env)
            elif transport == "sse":
                if not url:
                    return ToolResult(
                        success=False,
                        error="'url' is required for sse transport",
                        error_category="missing_parameter",
                        suggested_fix="Provide the SSE endpoint URL",
                    )
                info = await manager.connect_sse(name, url, headers)
            elif transport == "streamable-http":
                if not url:
                    return ToolResult(
                        success=False,
                        error="'url' is required for streamable-http transport",
                        error_category="missing_parameter",
                        suggested_fix="Provide the HTTP endpoint URL",
                    )
                info = await manager.connect_streamable_http(name, url, headers)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown transport: {transport}",
                    error_category="invalid_type",
                    suggested_fix="Use 'stdio', 'sse', or 'streamable-http'",
                )

            # Also fetch available tools for immediate discovery
            client = manager.get_client(name)
            tools_list = []
            if client and client.capabilities and client.capabilities.get("tools"):
                try:
                    tools_list = await client.list_tools()
                except Exception:
                    pass

            output = {
                "status": "connected",
                "server": name,
                "from_registry": from_registry,
                "server_info": info.get("serverInfo", {}),
                "capabilities": info.get("capabilities", {}),
            }
            if tools_list:
                output["available_tools"] = [
                    {"name": t["name"], "description": t.get("description", "")}
                    for t in tools_list
                ]
                output["tool_count"] = len(tools_list)

            return ToolResult(success=True, output=output)

        except MCPError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Connection failed: {e}")


class MCPDisconnectTool(BaseTool):
    """Disconnect from an MCP server."""

    @property
    def name(self) -> str:
        return "mcp_disconnect"

    @property
    def description(self) -> str:
        return "Disconnect from a connected MCP server. Pass 'all' as server name to disconnect all."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Server name to disconnect, or 'all' to disconnect all servers",
                },
            },
            "required": ["server"],
        }

    async def execute(self, ctx: ToolContext, server: str) -> ToolResult:
        try:
            if server == "all":
                count = await manager.disconnect_all()
                return ToolResult(success=True, output=f"Disconnected {count} server(s)")

            disconnected = await manager.disconnect(server)
            if disconnected:
                return ToolResult(success=True, output=f"Disconnected from '{server}'")
            else:
                return ToolResult(
                    success=False,
                    error=f"No server named '{server}' is connected",
                    suggested_fix="Use mcp_list_servers to see connected servers",
                )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MCPListServersTool(BaseTool):
    """List connected MCP servers."""

    @property
    def name(self) -> str:
        return "mcp_list_servers"

    @property
    def description(self) -> str:
        return "List all connected MCP servers with their transport type, capabilities, and connection status."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, ctx: ToolContext) -> ToolResult:
        servers = manager.list_servers()
        if not servers:
            return ToolResult(success=True, output="No MCP servers connected. Use mcp_connect to connect to one.")
        return ToolResult(success=True, output={"servers": servers, "count": len(servers)})


class MCPListToolsTool(BaseTool):
    """List tools available on a connected MCP server."""

    @property
    def name(self) -> str:
        return "mcp_list_tools"

    @property
    def description(self) -> str:
        return "List all tools available on a connected MCP server, including their names, descriptions, and parameter schemas."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Name of the connected MCP server",
                },
            },
            "required": ["server"],
        }

    async def execute(self, ctx: ToolContext, server: str) -> ToolResult:
        client = manager.get_client(server)
        if not client:
            return ToolResult(
                success=False,
                error=f"No server named '{server}' is connected",
                suggested_fix="Use mcp_connect to connect first, or mcp_list_servers to see connected servers",
            )
        try:
            tools = await client.list_tools()
            return ToolResult(success=True, output={"server": server, "tools": tools, "count": len(tools)})
        except MCPError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list tools: {e}")


class MCPCallToolTool(BaseTool):
    """Call a tool on a connected MCP server."""

    @property
    def name(self) -> str:
        return "mcp_call_tool"

    @property
    def description(self) -> str:
        return (
            "Call a tool on a connected MCP server. Use mcp_list_tools first to discover "
            "available tools and their parameter schemas."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Name of the connected MCP server",
                },
                "tool": {
                    "type": "string",
                    "description": "Name of the tool to call",
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments to pass to the tool (must match the tool's input schema)",
                    "additionalProperties": True,
                },
            },
            "required": ["server", "tool"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        server: str,
        tool: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        client = manager.get_client(server)
        if not client:
            return ToolResult(
                success=False,
                error=f"No server named '{server}' is connected",
                suggested_fix="Use mcp_connect to connect first",
            )
        try:
            result = await client.call_tool(tool, arguments)

            # MCP tool results have a 'content' array with type/text entries
            content = result.get("content", [])
            is_error = result.get("isError", False)

            # Flatten content for readability
            output_parts = []
            for item in content:
                if item.get("type") == "text":
                    output_parts.append(item.get("text", ""))
                elif item.get("type") == "image":
                    output_parts.append(f"[Image: {item.get('mimeType', 'image/*')}]")
                elif item.get("type") == "resource":
                    res = item.get("resource", {})
                    output_parts.append(f"[Resource: {res.get('uri', 'unknown')}]\n{res.get('text', '')}")
                else:
                    output_parts.append(json.dumps(item))

            output_text = "\n".join(output_parts) if output_parts else json.dumps(result)

            if is_error:
                return ToolResult(success=False, error=output_text, is_error=True)
            return ToolResult(success=True, output=output_text)

        except MCPError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Tool call failed: {e}")


class MCPListResourcesTool(BaseTool):
    """List resources on a connected MCP server."""

    @property
    def name(self) -> str:
        return "mcp_list_resources"

    @property
    def description(self) -> str:
        return "List resources available on a connected MCP server."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Name of the connected MCP server",
                },
            },
            "required": ["server"],
        }

    async def execute(self, ctx: ToolContext, server: str) -> ToolResult:
        client = manager.get_client(server)
        if not client:
            return ToolResult(
                success=False,
                error=f"No server named '{server}' is connected",
                suggested_fix="Use mcp_connect to connect first",
            )
        try:
            resources = await client.list_resources()
            return ToolResult(success=True, output={"server": server, "resources": resources, "count": len(resources)})
        except MCPError as e:
            if "Method not found" in str(e):
                return ToolResult(success=True, output={"server": server, "resources": [], "note": "Server does not support resources"})
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list resources: {e}")


class MCPReadResourceTool(BaseTool):
    """Read a resource from a connected MCP server."""

    @property
    def name(self) -> str:
        return "mcp_read_resource"

    @property
    def description(self) -> str:
        return "Read a specific resource from a connected MCP server by URI."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Name of the connected MCP server",
                },
                "uri": {
                    "type": "string",
                    "description": "Resource URI (e.g., 'file:///path/to/file')",
                },
            },
            "required": ["server", "uri"],
        }

    async def execute(self, ctx: ToolContext, server: str, uri: str) -> ToolResult:
        client = manager.get_client(server)
        if not client:
            return ToolResult(
                success=False,
                error=f"No server named '{server}' is connected",
                suggested_fix="Use mcp_connect to connect first",
            )
        try:
            result = await client.read_resource(uri)

            # Flatten contents
            contents = result.get("contents", [])
            output_parts = []
            for item in contents:
                uri_str = item.get("uri", "")
                if "text" in item:
                    output_parts.append(f"--- {uri_str} ---\n{item['text']}")
                elif "blob" in item:
                    output_parts.append(f"--- {uri_str} ---\n[Binary blob, {item.get('mimeType', 'application/octet-stream')}]")
                else:
                    output_parts.append(json.dumps(item))

            return ToolResult(success=True, output="\n".join(output_parts) if output_parts else json.dumps(result))

        except MCPError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to read resource: {e}")


class MCPListPromptsTool(BaseTool):
    """List prompts from a connected MCP server."""

    @property
    def name(self) -> str:
        return "mcp_list_prompts"

    @property
    def description(self) -> str:
        return "List prompts available on a connected MCP server."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Name of the connected MCP server",
                },
            },
            "required": ["server"],
        }

    async def execute(self, ctx: ToolContext, server: str) -> ToolResult:
        client = manager.get_client(server)
        if not client:
            return ToolResult(
                success=False,
                error=f"No server named '{server}' is connected",
                suggested_fix="Use mcp_connect to connect first",
            )
        try:
            prompts = await client.list_prompts()
            return ToolResult(success=True, output={"server": server, "prompts": prompts, "count": len(prompts)})
        except MCPError as e:
            if "Method not found" in str(e):
                return ToolResult(success=True, output={"server": server, "prompts": [], "note": "Server does not support prompts"})
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list prompts: {e}")


class MCPGetPromptTool(BaseTool):
    """Get a prompt from a connected MCP server."""

    @property
    def name(self) -> str:
        return "mcp_get_prompt"

    @property
    def description(self) -> str:
        return "Get a specific prompt from a connected MCP server, optionally with arguments."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Name of the connected MCP server",
                },
                "prompt": {
                    "type": "string",
                    "description": "Name of the prompt to get",
                },
                "arguments": {
                    "type": "object",
                    "description": "Optional arguments for the prompt",
                    "additionalProperties": True,
                },
            },
            "required": ["server", "prompt"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        server: str,
        prompt: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        client = manager.get_client(server)
        if not client:
            return ToolResult(
                success=False,
                error=f"No server named '{server}' is connected",
                suggested_fix="Use mcp_connect to connect first",
            )
        try:
            result = await client.get_prompt(prompt, arguments)

            # Format prompt messages
            messages = result.get("messages", [])
            output_parts = []
            if result.get("description"):
                output_parts.append(f"Description: {result['description']}")
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", {})
                if isinstance(content, dict) and content.get("type") == "text":
                    output_parts.append(f"[{role}]: {content['text']}")
                else:
                    output_parts.append(f"[{role}]: {json.dumps(content)}")

            return ToolResult(success=True, output="\n".join(output_parts) if output_parts else json.dumps(result))

        except MCPError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to get prompt: {e}")


class MCPBrowseTool(BaseTool):
    """Browse available MCP servers from the pre-configured registry."""

    @property
    def name(self) -> str:
        return "mcp_browse"

    @property
    def description(self) -> str:
        return (
            "Browse pre-configured MCP servers available to connect to. "
            "Shows servers grouped by category with descriptions and auth requirements. "
            "Use mcp_connect(name=...) to connect to any listed server."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category (e.g., 'blockchain', 'developer', 'search', 'productivity', 'payments', 'database', 'utility'). Omit to show all.",
                },
            },
        }

    async def execute(self, ctx: ToolContext, category: Optional[str] = None) -> ToolResult:
        grouped = list_servers_by_category()

        if not grouped:
            return ToolResult(
                success=True,
                output="No MCP servers in registry. Add entries to config/mcp_servers.yaml.",
            )

        if category:
            category = category.lower()
            filtered = {category: grouped[category]} if category in grouped else {}
            if not filtered:
                available = ", ".join(sorted(grouped.keys()))
                return ToolResult(
                    success=False,
                    error=f"No servers in category '{category}'",
                    suggested_fix=f"Available categories: {available}",
                )
            grouped = filtered

        # Build output
        total = sum(len(servers) for servers in grouped.values())
        output = {
            "total_servers": total,
            "categories": {},
        }
        for cat, servers in sorted(grouped.items()):
            output["categories"][cat] = servers

        return ToolResult(success=True, output=output)
