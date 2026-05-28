"""
MCP Connection Manager

Manages lifecycle of MCP server connections. Connections persist globally
(not per-session) so they can be reused across tool calls.
"""

import logging
from typing import Any, Dict, List, Optional

from .client import (
    MCPClient,
    MCPError,
    SSETransport,
    StdioTransport,
    StreamableHTTPTransport,
)

logger = logging.getLogger(__name__)

# Global connection store: server_name -> MCPClient
_connections: Dict[str, MCPClient] = {}
# Metadata about each connection (transport type, command/url, etc.)
_connection_meta: Dict[str, Dict[str, Any]] = {}


async def connect_stdio(
    name: str,
    command: str,
    args: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
) -> dict:
    """
    Connect to an MCP server via stdio transport.

    Args:
        name: Unique name for this connection
        command: Command to execute (e.g., "npx", "python")
        args: Command arguments
        env: Additional environment variables for the subprocess

    Returns:
        Server info dict with capabilities
    """
    # Disconnect existing connection with same name
    if name in _connections:
        await disconnect(name)

    transport = StdioTransport(command=command, args=args or [], env=env)
    client = MCPClient(transport)

    try:
        info = await client.connect()
    except Exception as e:
        await client.close()
        raise MCPError(-1, f"Failed to connect to stdio server '{name}': {e}")

    _connections[name] = client
    _connection_meta[name] = {
        "transport": "stdio",
        "command": command,
        "args": args or [],
    }

    logger.info(f"MCP connected (stdio): {name} — {info.get('serverInfo', {}).get('name', 'unknown')}")
    return info


async def connect_sse(
    name: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
) -> dict:
    """
    Connect to an MCP server via SSE transport.

    Args:
        name: Unique name for this connection
        url: SSE endpoint URL
        headers: Optional HTTP headers (e.g., auth tokens)

    Returns:
        Server info dict with capabilities
    """
    if name in _connections:
        await disconnect(name)

    transport = SSETransport(url=url, headers=headers)
    client = MCPClient(transport)

    try:
        info = await client.connect()
    except Exception as e:
        await client.close()
        raise MCPError(-1, f"Failed to connect to SSE server '{name}': {e}")

    _connections[name] = client
    _connection_meta[name] = {
        "transport": "sse",
        "url": url,
    }

    logger.info(f"MCP connected (SSE): {name} — {info.get('serverInfo', {}).get('name', 'unknown')}")
    return info


async def connect_streamable_http(
    name: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
) -> dict:
    """
    Connect to an MCP server via streamable HTTP transport.

    Args:
        name: Unique name for this connection
        url: HTTP endpoint URL
        headers: Optional HTTP headers

    Returns:
        Server info dict with capabilities
    """
    if name in _connections:
        await disconnect(name)

    transport = StreamableHTTPTransport(url=url, headers=headers)
    client = MCPClient(transport)

    try:
        info = await client.connect()
    except Exception as e:
        await client.close()
        raise MCPError(-1, f"Failed to connect to streamable-http server '{name}': {e}")

    _connections[name] = client
    _connection_meta[name] = {
        "transport": "streamable-http",
        "url": url,
    }

    logger.info(f"MCP connected (streamable-http): {name} — {info.get('serverInfo', {}).get('name', 'unknown')}")
    return info


async def disconnect(name: str) -> bool:
    """
    Disconnect from an MCP server.

    Returns:
        True if disconnected, False if not found
    """
    client = _connections.pop(name, None)
    _connection_meta.pop(name, None)
    if client:
        await client.close()
        logger.info(f"MCP disconnected: {name}")
        return True
    return False


async def disconnect_all() -> int:
    """Disconnect all servers. Returns count of disconnected servers."""
    count = 0
    for name in list(_connections.keys()):
        await disconnect(name)
        count += 1
    return count


def get_client(name: str) -> Optional[MCPClient]:
    """Get client by server name."""
    client = _connections.get(name)
    if client and not client.is_connected:
        # Connection dropped — clean up
        _connections.pop(name, None)
        _connection_meta.pop(name, None)
        return None
    return client


def list_servers() -> List[Dict[str, Any]]:
    """List all connected servers with metadata."""
    servers = []
    for name, client in list(_connections.items()):
        connected = client.is_connected
        meta = _connection_meta.get(name, {})
        servers.append({
            "name": name,
            "connected": connected,
            "transport": meta.get("transport", "unknown"),
            "server_info": client.server_info,
            "capabilities": client.capabilities,
            **{k: v for k, v in meta.items() if k not in ("transport",)},
        })
    return servers
