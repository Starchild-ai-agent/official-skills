"""
MCP Protocol Client

Lightweight implementation of the Model Context Protocol (MCP) client.
Supports stdio and HTTP (SSE / streamable-http) transports.

Protocol reference: https://spec.modelcontextprotocol.io/
"""

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# MCP protocol version
PROTOCOL_VERSION = "2024-11-05"

CLIENT_INFO = {
    "name": "starchild-mcp-connector",
    "version": "1.0.0",
}


class MCPError(Exception):
    """MCP protocol error."""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP error {code}: {message}")


class MCPTransport(ABC):
    """Abstract MCP transport layer."""

    @abstractmethod
    async def start(self) -> None:
        """Start the transport connection."""

    @abstractmethod
    async def send_request(self, method: str, params: Optional[dict] = None) -> dict:
        """Send a JSON-RPC request and return the result."""

    @abstractmethod
    async def send_notification(self, method: str, params: Optional[dict] = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""

    @abstractmethod
    async def close(self) -> None:
        """Close the transport."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the transport is currently connected."""


class StdioTransport(MCPTransport):
    """
    Stdio transport — launches an MCP server as a subprocess and
    communicates via stdin/stdout using newline-delimited JSON-RPC.
    """

    def __init__(self, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        self.command = command
        self.args = args or []
        self.env = env
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._connected = False

    async def start(self) -> None:
        # Build environment
        process_env = os.environ.copy()
        if self.env:
            process_env.update(self.env)

        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=process_env,
        )
        self._connected = True
        self._reader_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        """Read JSON-RPC messages from stdout."""
        assert self._process and self._process.stdout
        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug(f"MCP stdio: non-JSON line: {line[:200]}")
                    continue

                # Handle response to a request
                if "id" in msg and msg["id"] in self._pending:
                    fut = self._pending.pop(msg["id"])
                    if not fut.done():
                        fut.set_result(msg)
                # Notifications from server (no id or id not in pending)
                elif "method" in msg and "id" not in msg:
                    logger.debug(f"MCP notification: {msg.get('method')}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"MCP stdio reader error: {e}")
        finally:
            self._connected = False

    async def send_request(self, method: str, params: Optional[dict] = None) -> dict:
        if not self._process or not self._process.stdin:
            raise MCPError(-1, "Transport not connected")

        self._request_id += 1
        req_id = self._request_id
        msg: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            msg["params"] = params

        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut

        data = json.dumps(msg) + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()

        try:
            response = await asyncio.wait_for(fut, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise MCPError(-1, f"Request timed out: {method}")

        if "error" in response:
            err = response["error"]
            raise MCPError(err.get("code", -1), err.get("message", "Unknown error"), err.get("data"))

        return response.get("result", {})

    async def send_notification(self, method: str, params: Optional[dict] = None) -> None:
        if not self._process or not self._process.stdin:
            raise MCPError(-1, "Transport not connected")

        msg: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            msg["params"] = params

        data = json.dumps(msg) + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()

    async def close(self) -> None:
        self._connected = False
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        if self._process:
            try:
                self._process.stdin.close() if self._process.stdin else None
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except (asyncio.TimeoutError, ProcessLookupError):
                self._process.kill()
            except Exception:
                pass
        # Resolve any pending futures
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(MCPError(-1, "Transport closed"))
        self._pending.clear()

    @property
    def is_connected(self) -> bool:
        return self._connected


class SSETransport(MCPTransport):
    """
    SSE transport — connects to an MCP server via HTTP Server-Sent Events.

    Flow:
    1. GET <url> to open SSE stream
    2. Server sends 'endpoint' event with POST URL
    3. Client POSTs JSON-RPC messages to that endpoint
    4. Responses arrive as SSE 'message' events
    """

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {}
        self._endpoint_url: Optional[str] = None
        self._request_id = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._sse_task: Optional[asyncio.Task] = None
        self._session = None
        self._connected = False

    async def start(self) -> None:
        import httpx

        self._session = httpx.AsyncClient(headers=self.headers, timeout=60.0)

        # Open SSE stream to discover endpoint
        self._sse_task = asyncio.create_task(self._sse_loop())

        # Wait for endpoint discovery (with timeout)
        for _ in range(100):  # 10 seconds max
            if self._endpoint_url:
                break
            await asyncio.sleep(0.1)

        if not self._endpoint_url:
            await self.close()
            raise MCPError(-1, "Failed to discover MCP endpoint from SSE stream")

        self._connected = True

    async def _sse_loop(self) -> None:
        """Read SSE events from the server."""
        import httpx

        try:
            async with self._session.stream("GET", self.url) as response:
                response.raise_for_status()
                event_type = ""
                data_buffer = ""

                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        data_buffer += line[5:].strip()
                    elif line == "":
                        # End of event
                        if event_type == "endpoint" and data_buffer:
                            # Resolve relative URL
                            endpoint = data_buffer.strip()
                            if endpoint.startswith("/"):
                                from urllib.parse import urlparse
                                parsed = urlparse(self.url)
                                self._endpoint_url = f"{parsed.scheme}://{parsed.netloc}{endpoint}"
                            else:
                                self._endpoint_url = endpoint
                            logger.info(f"MCP SSE endpoint discovered: {self._endpoint_url}")
                        elif event_type == "message" and data_buffer:
                            try:
                                msg = json.loads(data_buffer)
                                if "id" in msg and msg["id"] in self._pending:
                                    fut = self._pending.pop(msg["id"])
                                    if not fut.done():
                                        fut.set_result(msg)
                            except json.JSONDecodeError:
                                pass
                        event_type = ""
                        data_buffer = ""
        except asyncio.CancelledError:
            pass
        except httpx.HTTPStatusError as e:
            logger.error(f"MCP SSE HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"MCP SSE error: {e}")
        finally:
            self._connected = False

    async def send_request(self, method: str, params: Optional[dict] = None) -> dict:
        if not self._endpoint_url or not self._session:
            raise MCPError(-1, "Transport not connected")

        self._request_id += 1
        req_id = self._request_id
        msg: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            msg["params"] = params

        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut

        # POST the request to the endpoint
        response = await self._session.post(self._endpoint_url, json=msg)
        response.raise_for_status()

        # Some servers respond directly in the POST response
        if response.headers.get("content-type", "").startswith("application/json"):
            body = response.json()
            if "id" in body:
                self._pending.pop(req_id, None)
                if not fut.done():
                    fut.set_result(body)

        try:
            result = await asyncio.wait_for(fut, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise MCPError(-1, f"Request timed out: {method}")

        if "error" in result:
            err = result["error"]
            raise MCPError(err.get("code", -1), err.get("message", "Unknown error"), err.get("data"))

        return result.get("result", {})

    async def send_notification(self, method: str, params: Optional[dict] = None) -> None:
        if not self._endpoint_url or not self._session:
            raise MCPError(-1, "Transport not connected")

        msg: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            msg["params"] = params

        await self._session.post(self._endpoint_url, json=msg)

    async def close(self) -> None:
        self._connected = False
        if self._sse_task:
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass
        if self._session:
            await self._session.aclose()
            self._session = None
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(MCPError(-1, "Transport closed"))
        self._pending.clear()

    @property
    def is_connected(self) -> bool:
        return self._connected


class StreamableHTTPTransport(MCPTransport):
    """
    Streamable HTTP transport — the newer MCP transport (2025+).

    Each request is a POST that returns either:
    - A JSON response directly, or
    - An SSE stream with the response
    """

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {}
        self._request_id = 0
        self._session = None
        self._connected = False
        self._session_id: Optional[str] = None

    async def start(self) -> None:
        import httpx

        self._session = httpx.AsyncClient(headers=self.headers, timeout=60.0)
        self._connected = True

    async def send_request(self, method: str, params: Optional[dict] = None) -> dict:
        if not self._session:
            raise MCPError(-1, "Transport not connected")

        self._request_id += 1
        req_id = self._request_id
        msg: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            msg["params"] = params

        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        response = await self._session.post(self.url, json=msg, headers=headers)
        response.raise_for_status()

        # Capture session ID from response
        if "mcp-session-id" in response.headers:
            self._session_id = response.headers["mcp-session-id"]

        content_type = response.headers.get("content-type", "")

        # Direct JSON response
        if "application/json" in content_type:
            result = response.json()
            if "error" in result:
                err = result["error"]
                raise MCPError(err.get("code", -1), err.get("message", "Unknown error"), err.get("data"))
            return result.get("result", {})

        # SSE stream response — parse for the result
        if "text/event-stream" in content_type:
            return await self._parse_sse_response(response.text, req_id)

        raise MCPError(-1, f"Unexpected content-type: {content_type}")

    async def _parse_sse_response(self, body: str, req_id: int) -> dict:
        """Parse SSE response body for JSON-RPC result."""
        for line in body.split("\n"):
            if line.startswith("data:"):
                data = line[5:].strip()
                if not data:
                    continue
                try:
                    msg = json.loads(data)
                    if msg.get("id") == req_id:
                        if "error" in msg:
                            err = msg["error"]
                            raise MCPError(err.get("code", -1), err.get("message", "Unknown"), err.get("data"))
                        return msg.get("result", {})
                except json.JSONDecodeError:
                    continue
        raise MCPError(-1, "No result found in SSE response")

    async def send_notification(self, method: str, params: Optional[dict] = None) -> None:
        if not self._session:
            raise MCPError(-1, "Transport not connected")

        msg: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            msg["params"] = params

        headers = {"Content-Type": "application/json"}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        await self._session.post(self.url, json=msg, headers=headers)

    async def close(self) -> None:
        self._connected = False
        if self._session:
            await self._session.aclose()
            self._session = None

    @property
    def is_connected(self) -> bool:
        return self._connected


class MCPClient:
    """
    MCP protocol client.

    Manages the protocol lifecycle (initialize → use → close) over any transport.
    """

    def __init__(self, transport: MCPTransport):
        self.transport = transport
        self.server_info: Optional[dict] = None
        self.capabilities: Optional[dict] = None
        self._initialized = False

    async def connect(self) -> dict:
        """Start transport and perform MCP handshake. Returns server info."""
        await self.transport.start()

        # Send initialize request
        result = await self.transport.send_request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": CLIENT_INFO,
        })

        self.server_info = result.get("serverInfo", {})
        self.capabilities = result.get("capabilities", {})

        # Send initialized notification
        await self.transport.send_notification("notifications/initialized")

        self._initialized = True
        return {
            "serverInfo": self.server_info,
            "capabilities": self.capabilities,
            "protocolVersion": result.get("protocolVersion", PROTOCOL_VERSION),
        }

    async def list_tools(self) -> List[dict]:
        """List available tools from the server."""
        if not self._initialized:
            raise MCPError(-1, "Client not initialized")
        result = await self.transport.send_request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: Optional[dict] = None) -> Any:
        """Call a tool on the server."""
        if not self._initialized:
            raise MCPError(-1, "Client not initialized")
        params: Dict[str, Any] = {"name": name}
        if arguments:
            params["arguments"] = arguments
        result = await self.transport.send_request("tools/call", params)
        return result

    async def list_resources(self) -> List[dict]:
        """List available resources."""
        if not self._initialized:
            raise MCPError(-1, "Client not initialized")
        result = await self.transport.send_request("resources/list")
        return result.get("resources", [])

    async def read_resource(self, uri: str) -> Any:
        """Read a resource by URI."""
        if not self._initialized:
            raise MCPError(-1, "Client not initialized")
        result = await self.transport.send_request("resources/read", {"uri": uri})
        return result

    async def list_prompts(self) -> List[dict]:
        """List available prompts."""
        if not self._initialized:
            raise MCPError(-1, "Client not initialized")
        result = await self.transport.send_request("prompts/list")
        return result.get("prompts", [])

    async def get_prompt(self, name: str, arguments: Optional[dict] = None) -> Any:
        """Get a prompt by name."""
        if not self._initialized:
            raise MCPError(-1, "Client not initialized")
        params: Dict[str, Any] = {"name": name}
        if arguments:
            params["arguments"] = arguments
        result = await self.transport.send_request("prompts/get", params)
        return result

    async def close(self) -> None:
        """Close the client and transport."""
        self._initialized = False
        await self.transport.close()

    @property
    def is_connected(self) -> bool:
        return self._initialized and self.transport.is_connected
