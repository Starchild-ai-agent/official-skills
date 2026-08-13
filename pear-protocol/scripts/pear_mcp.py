"""Pear Protocol MCP CLI.

Usage:
  python3 pear_mcp.py status               # token info, no network
  python3 pear_mcp.py list                 # tools/list
  python3 pear_mcp.py call <tool> '<json>' # tools/call
Auth: PEAR_API_KEY (x-api-key header) from env or workspace/.env.
Mint one with: python3 scripts/gateway.py ensure-key
Key scope gates the tool surface: read = analytics/account tools only;
read_write = adds the plan_/execute_ trading tools.
"""
import json
import os
import sys

import requests

# ---------------------------------------------------------------------------
# Starchild proxied HTTP client (optional)
# ---------------------------------------------------------------------------
_HAVE_PROXY = False
try:
    sys.path.insert(0, '/app')
    from core.http_client import proxied_post
    _HAVE_PROXY = True
except Exception:
    pass

MCP_URL = "https://mcp.pearprotocol.io/mcp"
ENV_PATH = "/data/workspace/.env"


def die(msg: str):
    print(msg, file=sys.stderr)
    sys.exit(1)


def load_api_key() -> str | None:
    key = os.environ.get("PEAR_API_KEY")
    if key:
        return key
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                if line.startswith("PEAR_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return None


def load_tokens() -> dict:
    key = load_api_key()
    if key:
        return {"api_key": key}
    die("No PEAR_API_KEY found. Mint one first: "
        "python3 skills/pear-protocol/scripts/gateway.py ensure-key")


def parse_body(resp: requests.Response):
    ctype = resp.headers.get("content-type", "")
    if "text/event-stream" in ctype:
        payload = None
        for line in resp.text.splitlines():
            if line.startswith("data: "):
                payload = line[len("data: "):]
        return json.loads(payload) if payload else None
    if resp.text.strip():
        return resp.json()
    return None


def mcp_request(tok: dict, method: str, params=None, session_id=None, req_id=None):
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        body["params"] = params
    if req_id is not None:
        body["id"] = req_id
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    headers["x-api-key"] = tok["api_key"]
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    if _HAVE_PROXY:
        resp = proxied_post(MCP_URL, json=body, headers=headers, timeout=60)
    else:
        resp = requests.post(MCP_URL, json=body, headers=headers, timeout=60)
    if resp.status_code >= 400:
        die(f"MCP HTTP {resp.status_code} on {method}: {resp.text[:300]}")
    return parse_body(resp), resp.headers.get("mcp-session-id")


def handshake(tok: dict) -> str | None:
    _, session_id = mcp_request(tok, "initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "starchild-pear", "version": "1.0"},
    }, req_id=1)
    try:
        mcp_request(tok, "notifications/initialized", session_id=session_id)
    except SystemExit:
        pass  # some servers 4xx notifications; not fatal
    return session_id


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("status", "list", "call"):
        die(__doc__)
    cmd = sys.argv[1]
    tok = load_tokens()
    if cmd == "status":
        print(json.dumps({
            "connected": True,
            "auth": "api_key",
            "key_head": tok["api_key"][:10] + "…",
        }, indent=2))
        return
    session_id = handshake(tok)
    if cmd == "list":
        result, _ = mcp_request(tok, "tools/list", {}, session_id=session_id, req_id=2)
    else:
        if len(sys.argv) < 3:
            die("Usage: pear_mcp.py call <tool> '<json-args>'")
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        result, _ = mcp_request(tok, "tools/call",
                                {"name": sys.argv[2], "arguments": args},
                                session_id=session_id, req_id=2)
    if isinstance(result, dict) and "result" in result:
        print(json.dumps(result["result"], indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
