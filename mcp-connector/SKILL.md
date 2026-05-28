---
name: mcp-connector
version: 1.0.1
description: Connect to any MCP (Model Context Protocol) server (Including Robinhood and Base) and use its tools, resources, and prompts
tools:
  - mcp_browse
  - mcp_connect
  - mcp_disconnect
  - mcp_list_servers
  - mcp_list_tools
  - mcp_call_tool
  - mcp_list_resources
  - mcp_read_resource
  - mcp_list_prompts
  - mcp_get_prompt

metadata:
  starchild:
    emoji: "🔌"
    skillKey: mcp-connector

user-invocable: false
---

# MCP Connector

Connect to any MCP (Model Context Protocol) server and interact with its tools, resources, and prompts.

## Supported Transports

- **stdio** — Launch a local MCP server as a subprocess (e.g. `npx @modelcontextprotocol/server-filesystem /path`)
- **sse** — Connect to a remote MCP server via HTTP Server-Sent Events
- **streamable-http** — Connect via the newer streamable HTTP transport (POST with SSE response)

## Usage Flow

1. **Browse** available servers with `mcp_browse` (or filter by category)
2. **Connect** by name from the registry: `mcp_connect(name="coingecko")`
3. **Discover** available tools/resources with `mcp_list_tools` or `mcp_list_resources`
4. **Use** them via `mcp_call_tool` or `mcp_read_resource`
5. **Disconnect** when done with `mcp_disconnect`

## Pre-configured Registry

A curated list of MCP servers is maintained in `config/mcp_servers.yaml`. Connect to any of them by name — no URL or transport details needed:

```
mcp_connect(name="coingecko")     # Crypto market data
mcp_connect(name="exa")           # Neural web search
mcp_connect(name="dexpaprika")    # DEX data across chains
```

Use `mcp_browse()` to see all available servers, or filter by category:
```
mcp_browse(category="blockchain")
mcp_browse(category="developer")
```

Some servers require environment variables (API keys). The tool will tell you which ones are missing.

## Ad-hoc Connections

You can still connect to any MCP server not in the registry by providing transport details:

### stdio (local subprocess)
```
mcp_connect(
    name="fs",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
)
```

### SSE (HTTP Server-Sent Events)
```
mcp_connect(
    name="remote-tools",
    transport="sse",
    url="https://mcp.example.com/sse"
)
```

### Streamable HTTP
```
mcp_connect(
    name="api-server",
    transport="streamable-http",
    url="https://mcp.example.com/mcp"
)
```

## Using Connected Servers

### Call a tool
```
mcp_call_tool(
    server="coingecko",
    tool="get_price",
    arguments={"coin": "bitcoin"}
)
```

### Read a resource
```
mcp_read_resource(
    server="remote-tools",
    uri="file:///data/config.json"
)
```

## Notes

- Connections persist for the duration of the session
- Multiple servers can be connected simultaneously
- Server names must be unique — reconnecting with the same name replaces the old connection
- Environment variables can be passed to stdio servers via the `env` parameter
- Registry entries are in `config/mcp_servers.yaml` — add new servers there (no code changes needed)
