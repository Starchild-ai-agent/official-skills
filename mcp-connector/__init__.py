"""
MCP Connector Skill — Connect to any MCP server

Provides tools to connect to MCP (Model Context Protocol) servers via
stdio, SSE, or streamable-http transports, and interact with their
tools, resources, and prompts.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """
    Extension entry point — register all MCP connector tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .tools import (
            MCPBrowseTool,
            MCPConnectTool,
            MCPDisconnectTool,
            MCPListServersTool,
            MCPListToolsTool,
            MCPCallToolTool,
            MCPListResourcesTool,
            MCPReadResourceTool,
            MCPListPromptsTool,
            MCPGetPromptTool,
        )

        api.register_tool(MCPBrowseTool())
        api.register_tool(MCPConnectTool())
        api.register_tool(MCPDisconnectTool())
        api.register_tool(MCPListServersTool())
        api.register_tool(MCPListToolsTool())
        api.register_tool(MCPCallToolTool())
        api.register_tool(MCPListResourcesTool())
        api.register_tool(MCPReadResourceTool())
        api.register_tool(MCPListPromptsTool())
        api.register_tool(MCPGetPromptTool())

        registered = [
            "mcp_browse",
            "mcp_connect",
            "mcp_disconnect",
            "mcp_list_servers",
            "mcp_list_tools",
            "mcp_call_tool",
            "mcp_list_resources",
            "mcp_read_resource",
            "mcp_list_prompts",
            "mcp_get_prompt",
        ]

        logger.info(f"Registered MCP connector tools ({len(registered)} tools)")
    except Exception as e:
        logger.warning(f"Failed to load MCP connector tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "mcp-connector",
    "version": "1.0.0",
    "description": "Connect to any MCP server and use its tools, resources, and prompts",
    "tools": [
        "mcp_browse",
        "mcp_connect",
        "mcp_disconnect",
        "mcp_list_servers",
        "mcp_list_tools",
        "mcp_call_tool",
        "mcp_list_resources",
        "mcp_read_resource",
        "mcp_list_prompts",
        "mcp_get_prompt",
    ],
    "env_vars": [],
}
