"""
Orderly One JWT Authentication — EIP-191 personal_sign via Privy wallet.

Auth flow (different from Orderly Ed25519):
1. POST /api/auth/nonce { address } → get message with nonce
2. Sign message via Privy wallet service (EIP-191 personal_sign)
3. POST /api/auth/verify { address, signature } → get JWT token
4. Cache JWT, re-auth on 401 or after 1 hour TTL

Environment Variables:
- WALLET_SERVICE_URL: Privy wallet service URL (required for signing)
- ORDERLY_ONE_API_URL: Orderly One API base URL (default: https://api.dex.orderly.network)
"""

import asyncio
import logging
import os
import time
from typing import Optional

import aiohttp

from tools.wallet import _wallet_request, _is_fly_machine

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.dex.orderly.network"
JWT_TTL_SECONDS = 3600  # 1 hour

# ── Module-level state (in-memory, lives as long as the process) ─────────────

_jwt_token: Optional[str] = None
_jwt_expiry: float = 0
_wallet_address: Optional[str] = None
_auth_lock = asyncio.Lock()


def _get_api_url() -> str:
    return os.environ.get("ORDERLY_ONE_API_URL", DEFAULT_API_URL)


async def _get_wallet_address() -> str:
    """Get the agent's EVM address from Privy wallet service (cached)."""
    global _wallet_address

    if _wallet_address:
        return _wallet_address

    if not _is_fly_machine():
        raise RuntimeError("Not running on Fly — wallet unavailable")

    data = await _wallet_request("GET", "/agent/wallet")
    wallets = data if isinstance(data, list) else data.get("wallets", [])
    for w in wallets:
        if w.get("chain_type") == "ethereum":
            _wallet_address = w["wallet_address"]
            return _wallet_address

    raise RuntimeError("No ethereum wallet found")


async def _fetch_jwt(address: str) -> str:
    """
    Authenticate with Orderly One API via EIP-191 personal_sign.

    Steps:
    1. POST /api/auth/nonce { address } → nonce message
    2. Sign message via Privy wallet service
    3. POST /api/auth/verify { address, signature } → JWT token
    """
    api_url = _get_api_url()

    # 1. Get nonce
    async with aiohttp.ClientSession() as session:
        url = f"{api_url}/api/auth/nonce"
        async with session.post(
            url,
            json={"address": address},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status >= 400:
                body = await resp.text()
                raise Exception(f"Failed to get auth nonce: HTTP {resp.status}: {body}")
            data = await resp.json()

    message = data.get("message") or data.get("data", {}).get("message")
    if not message:
        raise Exception(f"No message in nonce response: {data}")

    logger.info("Orderly One auth: signing nonce message via wallet service...")

    # 2. Sign via Privy (EIP-191 personal_sign)
    result = await _wallet_request("POST", "/agent/sign", {"message": message})
    signature = result.get("signature", "")
    if not signature:
        raise Exception(f"No signature in wallet response: {result}")

    # 3. Verify and get JWT
    async with aiohttp.ClientSession() as session:
        url = f"{api_url}/api/auth/verify"
        async with session.post(
            url,
            json={"address": address, "signature": signature},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status >= 400:
                body = await resp.text()
                raise Exception(f"Failed to verify auth: HTTP {resp.status}: {body}")
            data = await resp.json()

    token = data.get("token") or data.get("data", {}).get("token")
    if not token:
        raise Exception(f"No token in verify response: {data}")

    logger.info("Orderly One auth: JWT obtained successfully")
    return token


async def ensure_jwt() -> str:
    """
    Ensure we have a valid JWT token, refreshing if expired.

    Idempotent — safe to call multiple times. Uses asyncio.Lock to prevent
    concurrent auth attempts.
    """
    global _jwt_token, _jwt_expiry

    if _jwt_token and time.time() < _jwt_expiry:
        return _jwt_token  # Fast path, no lock

    async with _auth_lock:
        if _jwt_token and time.time() < _jwt_expiry:
            return _jwt_token  # Double-check after acquiring lock

        address = await _get_wallet_address()
        _jwt_token = await _fetch_jwt(address)
        _jwt_expiry = time.time() + JWT_TTL_SECONDS
        return _jwt_token


def invalidate_jwt() -> None:
    """Invalidate the cached JWT (e.g. on 401 response)."""
    global _jwt_token, _jwt_expiry
    _jwt_token = None
    _jwt_expiry = 0


def get_jwt() -> Optional[str]:
    """Get the cached JWT token (None if not yet authenticated)."""
    return _jwt_token
