#!/usr/bin/env python3
"""Pear Protocol V3 Gateway CLI — headless agent-wallet auth (SIWE-style).

Usage:
  python3 gateway.py login
  python3 gateway.py status
  python3 gateway.py ensure-key
  python3 gateway.py markets [--connector hyperliquid] [--limit N]
  python3 gateway.py get <path>
  python3 gateway.py post <path> <json-string>
"""
import argparse
import base64
import json
import os
import stat
import sys
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Wallet signing module
# ---------------------------------------------------------------------------
sys.path.insert(0, '/app')
try:
    from core.skill_tools import wallet
except Exception as exc:
    wallet = None
    print(f"Warning: could not import wallet module: {exc}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Starchild proxied HTTP client (optional)
# ---------------------------------------------------------------------------
_HAVE_PROXY = False
try:
    from core.http_client import proxied_get, proxied_post
    _HAVE_PROXY = True
except Exception:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://pro-gateway.pearprotocol.io"
TOKEN_DIR = "/data/workspace/.pear"
TOKEN_FILE = os.path.join(TOKEN_DIR, "gateway_tokens.json")
ENV_FILE = "/data/workspace/.env"
USER_AGENT = "PearGateway/1.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def trunc(s, n=10):
    """Truncate a secret string for display."""
    s = str(s)
    return s[:n] + "…"

def jwt_payload(token):
    """Decode the payload of a JWT without signature verification."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1] + "=="
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}

def load_env_key():
    """Load PEAR_API_KEY from os.environ, falling back to .env file."""
    key = os.environ.get("PEAR_API_KEY")
    if key:
        return key
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("PEAR_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return None

def proxy_handler():
    """Build a urllib proxy handler from environment, if set."""
    host = os.environ.get("PROXY_HOST")
    port = os.environ.get("PROXY_PORT")
    if host and port:
        proxy_url = f"http://[{host}]:{port}"
        return urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    return urllib.request.ProxyHandler()

def build_opener():
    """Build a urllib opener with proxy and default headers."""
    ph = proxy_handler()
    opener = urllib.request.build_opener(ph)
    opener.addheaders = [("User-Agent", USER_AGENT)]
    return opener

def http_get(path, headers=None):
    if _HAVE_PROXY:
        resp = proxied_get(f"{BASE_URL}{path}", headers=headers, timeout=15)
        body = resp.text
        data = json.loads(body) if body else {}
        return resp.status_code, data
    opener = build_opener()
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=headers or {})
    try:
        with opener.open(req, timeout=15) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body

def http_post(path, body_dict, headers=None):
    if _HAVE_PROXY:
        resp = proxied_post(
            f"{BASE_URL}{path}",
            json=body_dict,
            headers=headers,
            timeout=15,
        )
        body = resp.text
        data = json.loads(body) if body else {}
        return resp.status_code, data
    opener = build_opener()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(body_dict).encode(),
        headers=h,
        method="POST",
    )
    try:
        with opener.open(req, timeout=15) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body

# ---------------------------------------------------------------------------
# Wallet helpers
# ---------------------------------------------------------------------------
def get_evm_address():
    """Return the agent's EVM wallet address."""
    if wallet is None:
        raise RuntimeError("wallet module unavailable")
    info = wallet.wallet_info()
    wallets = info.get("wallets", [])
    for w in wallets:
        if w.get("chain_type") == "ethereum":
            addr = w.get("wallet_address", "")
            if addr.startswith("0x"):
                return addr
    # Fallback: first 0x address
    for w in wallets:
        addr = w.get("wallet_address", "")
        if addr.startswith("0x"):
            return addr
    raise RuntimeError(f"No EVM wallet found in wallet_info(): {info}")

def sign_message(message):
    """Sign a SIWE message with the agent wallet (EIP-191 personal_sign)."""
    if wallet is None:
        raise RuntimeError("wallet module unavailable")
    result = wallet.wallet_sign(message)
    # Handle both result["signature"] and result["data"]["signature"]
    if "signature" in result:
        return result["signature"]
    if "data" in result and "signature" in result["data"]:
        return result["data"]["signature"]
    raise RuntimeError(f"wallet_sign returned unexpected shape: {result}")

# ---------------------------------------------------------------------------
# Token cache
# ---------------------------------------------------------------------------
def load_cached_tokens():
    try:
        with open(TOKEN_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def save_cached_tokens(tokens):
    os.makedirs(TOKEN_DIR, exist_ok=True)
    os.chmod(TOKEN_DIR, 0o700)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(TOKEN_FILE, 0o600)

def token_seconds_left(access_token):
    payload = jwt_payload(access_token)
    exp = payload.get("exp", 0)
    return exp - int(time.time())

# ---------------------------------------------------------------------------
# Auth flow
# ---------------------------------------------------------------------------
def siwe_login():
    """Perform a fresh SIWE login and return (access_token, refresh_token, user)."""
    addr = get_evm_address()
    status, nonce_resp = http_post("/auth/nonce", {"address": addr})
    if status != 200:
        raise RuntimeError(f"/auth/nonce failed (HTTP {status}): {nonce_resp}")
    message = nonce_resp["message"]
    signature = sign_message(message)
    status, login_resp = http_post(
        "/auth/login",
        {"method": "wallet", "address": addr, "signature": signature},
    )
    if status != 200:
        raise RuntimeError(f"/auth/login failed (HTTP {status}): {login_resp}")
    access = login_resp["accessToken"]
    refresh = login_resp.get("refreshToken")
    user = login_resp.get("user", {})
    return access, refresh, user

def refresh_session(refresh_token):
    """Refresh the access token using the refresh token."""
    status, resp = http_post("/auth/session/refresh/token", {"refreshToken": refresh_token})
    if status != 200:
        return None, None
    return resp.get("accessToken"), resp.get("refreshToken")

def ensure_bearer():
    """Get a valid Bearer token: reuse cached if >60s left, else refresh, else fresh login."""
    cached = load_cached_tokens()
    access = cached.get("accessToken")
    if access and token_seconds_left(access) > 60:
        return access

    refresh = cached.get("refreshToken")
    if refresh:
        new_access, new_refresh = refresh_session(refresh)
        if new_access:
            cached["accessToken"] = new_access
            if new_refresh:
                cached["refreshToken"] = new_refresh
            save_cached_tokens(cached)
            return new_access

    # Fresh login
    access, refresh, user = siwe_login()
    save_cached_tokens({"accessToken": access, "refreshToken": refresh, "user": user})
    return access

# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------
def cmd_login(args):
    """Force fresh SIWE login; cache tokens; print identity."""
    access, refresh, user = siwe_login()
    save_cached_tokens({"accessToken": access, "refreshToken": refresh, "user": user})
    # Fetch identity
    status, resp = http_get("/auth/session/me", {"Authorization": f"Bearer {access}"})
    if status != 200:
        print(f"Warning: /auth/session/me returned HTTP {status}: {resp}", file=sys.stderr)
        resp = user
    print(f"✅ Logged in")
    print(f"   id:        {resp.get('id', user.get('id', 'unknown'))}")
    print(f"   role:      {resp.get('role', user.get('role', 'unknown'))}")
    print(f"   provider:  {resp.get('providerId', user.get('providerId', 'unknown'))}")
    print(f"   method:    {resp.get('loginMethod', user.get('loginMethod', 'unknown'))}")
    print(f"   token:     {trunc(access)} (exp in {token_seconds_left(access)}s)")
    return 0

def cmd_status(args):
    """Show api-key identity (if set) and cached bearer token validity."""
    api_key = load_env_key()
    any_ok = False

    # API key identity
    if api_key:
        status, resp = http_get("/auth/api-key/me", {"x-api-key": api_key})
        if status == 200 and isinstance(resp, dict):
            any_ok = True
            print(f"🔑 API key identity:")
            print(f"   id:        {resp.get('id', 'unknown')}")
            print(f"   role:      {resp.get('role', 'unknown')}")
            print(f"   scope:     {resp.get('scope', 'unknown')}")
            print(f"   key:       {trunc(api_key)}")
        else:
            print(f"⚠️  API key auth failed (HTTP {status}): {resp}")
    else:
        print("🔑 API key: not set in env or .env")

    # Cached bearer token
    cached = load_cached_tokens()
    access = cached.get("accessToken")
    if access:
        left = token_seconds_left(access)
        state = f"valid ({left}s remaining)" if left > 0 else "expired"
        print(f"🎫  Cached bearer token: {trunc(access)} — {state}")
        if left > 0:
            any_ok = True
    else:
        print("🎫  Cached bearer token: none")

    return 0 if any_ok else 1

def cmd_ensure_key(args):
    """If PEAR_API_KEY missing from .env: mint one and append it."""
    if load_env_key():
        print(f"✅ PEAR_API_KEY already set: {trunc(load_env_key())}")
        return 0

    # Need a bearer token to mint
    access = ensure_bearer()
    status, resp = http_post("/api-keys", {"label": "starchild-agent"},
                             {"Authorization": f"Bearer {access}"})
    if status not in (200, 201):
        print(f"❌ Failed to mint API key (HTTP {status}): {resp}", file=sys.stderr)
        return 1

    # Extract raw key — try common field names
    key = None
    for field in ("key", "apiKey", "rawKey", "secret", "apiKeySecret"):
        if field in resp:
            key = resp[field]
            break
    if key is None:
        print(f"❌ Could not find key field in response: {resp}", file=sys.stderr)
        return 1

    # Append to .env
    with open(ENV_FILE, "a") as f:
        f.write(f"\nPEAR_API_KEY={key}\n")
    print(f"✅ Minted API key and appended to .env: {trunc(key)}")
    return 0

def cmd_markets(args):
    """GET /markets with x-api-key; print compact table."""
    api_key = load_env_key()
    if not api_key:
        print("❌ PEAR_API_KEY not set. Run `ensure-key` first.", file=sys.stderr)
        return 1

    params = []
    if args.connector:
        params.append(f"connector={args.connector}")
    path = "/markets" + ("?" + "&".join(params) if params else "")
    status, resp = http_get(path, {"x-api-key": api_key})
    if status != 200:
        print(f"❌ /markets failed (HTTP {status}): {resp}", file=sys.stderr)
        return 1

    markets = resp.get("markets", resp.get("data", []))
    if not isinstance(markets, list):
        markets = [markets]

    print(f"📊 Markets: {len(markets)} total")
    limit = args.limit or 15
    top = sorted(markets, key=lambda m: float(m.get("volume24h", 0) or 0), reverse=True)[:limit]

    # Header
    hdr = f"{'Symbol':<14} {'Price':>14} {'Funding':>12} {'24h%':>10} {'OI':>16} {'Vol24h':>16}"
    print(hdr)
    print("-" * len(hdr))
    for m in top:
        sym = m.get("displaySymbol") or f"{m.get('base','?')}/{m.get('quote','?')}"
        price = m.get("price", "")
        funding = m.get("fundingRate", "")
        try:
            change = float(m.get("change24h", 0) or 0) * 100
            change_s = f"{change:+.2f}%"
        except (ValueError, TypeError):
            change_s = "n/a"
        oi = m.get("openInterest", "")
        vol = m.get("volume24h", "")
        print(f"{sym:<14} {price:>14} {funding:>12} {change_s:>10} {str(oi):>16} {str(vol):>16}")
    return 0

def cmd_get(args):
    """Arbitrary GET; try x-api-key first, on 401/403 retry with Bearer."""
    path = args.path
    api_key = load_env_key()

    # Try api-key first
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    status, resp = http_get(path, headers)

    if status in (401, 403):
        # Retry with Bearer
        try:
            access = ensure_bearer()
            status, resp = http_get(path, {"Authorization": f"Bearer {access}"})
        except RuntimeError as exc:
            print(f"❌ Bearer auth failed: {exc}", file=sys.stderr)
            return 1

    if status != 200:
        print(f"❌ GET {path} failed (HTTP {status}): {resp}", file=sys.stderr)
        return 1

    print(json.dumps(resp, indent=2))
    return 0

def cmd_post(args):
    """Arbitrary POST with valid Bearer (auto login/refresh first)."""
    path = args.path
    try:
        body = json.loads(args.body)
    except json.JSONDecodeError as exc:
        print(f"❌ Invalid JSON body: {exc}", file=sys.stderr)
        return 1

    try:
        access = ensure_bearer()
    except RuntimeError as exc:
        print(f"❌ Bearer auth failed: {exc}", file=sys.stderr)
        return 1

    headers = {"Authorization": f"Bearer {access}"}
    status, resp = http_post(path, body, headers)
    if status not in (200, 201):
        print(f"❌ POST {path} failed (HTTP {status}): {resp}", file=sys.stderr)
        return 1

    print(json.dumps(resp, indent=2))
    return 0

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="gateway.py",
        description="Pear Protocol V3 Gateway CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # login
    sub.add_parser("login", help="Force fresh SIWE login and cache tokens")

    # status
    sub.add_parser("status", help="Show auth status (api-key + cached bearer)")

    # ensure-key
    sub.add_parser("ensure-key", help="Mint API key if missing from .env")

    # markets
    p = sub.add_parser("markets", help="List markets")
    p.add_argument("--connector", default="hyperliquid", help="Connector (default: hyperliquid)")
    p.add_argument("--limit", type=int, default=15, help="Top N by volume (default: 15)")

    # get
    p = sub.add_parser("get", help="Arbitrary GET request")
    p.add_argument("path", help="API path, e.g. /trade-accounts")

    # post
    p = sub.add_parser("post", help="Arbitrary POST request (needs valid Bearer)")
    p.add_argument("path", help="API path")
    p.add_argument("body", help="JSON body string")

    args = parser.parse_args()

    dispatch = {
        "login": cmd_login,
        "status": cmd_status,
        "ensure-key": cmd_ensure_key,
        "markets": cmd_markets,
        "get": cmd_get,
        "post": cmd_post,
    }
    try:
        return dispatch[args.command](args)
    except Exception as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
