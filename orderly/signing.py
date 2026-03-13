"""
Orderly Network Signing — Ed25519 request signing + Privy EIP-712 registration.

Two responsibilities:
1. Auto-provision: Generate Ed25519 key pair in memory, register account with
   Orderly via Privy EIP-712 signing, and add the key — all on first use.
2. Ongoing signing: Sign every private API request with the in-memory Ed25519 key.

No API key env vars needed — keys are auto-provisioned via Privy on container boot.
"""

import asyncio
import base64
import logging
import os
import time
from typing import Optional, Tuple

import base58
from nacl.signing import SigningKey

from tools.wallet import _wallet_request, _is_fly_machine

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_API_URL = "https://api.orderly.org"
DEFAULT_BROKER_ID = "woofi_pro"
DEFAULT_CHAIN_ID = 42161  # Arbitrum

ORDERLY_DOMAIN = {
    "name": "Orderly",
    "version": "1",
    "chainId": DEFAULT_CHAIN_ID,
    "verifyingContract": "0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC",
}

REGISTRATION_TYPES = {
    "Registration": [
        {"name": "brokerId", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "timestamp", "type": "uint64"},
        {"name": "registrationNonce", "type": "uint256"},
    ]
}

ADD_KEY_TYPES = {
    "AddOrderlyKey": [
        {"name": "brokerId", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "orderlyKey", "type": "string"},
        {"name": "scope", "type": "string"},
        {"name": "timestamp", "type": "uint64"},
        {"name": "expiration", "type": "uint64"},
    ]
}

WITHDRAW_DOMAIN = {
    "name": "Orderly",
    "version": "1",
    "chainId": DEFAULT_CHAIN_ID,
    "verifyingContract": "0x6F7a338F2aA472838dEFD3283eB360d4Dff5D203",
}

WITHDRAW_TYPES = {
    "Withdraw": [
        {"name": "brokerId", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "receiver", "type": "address"},
        {"name": "token", "type": "string"},
        {"name": "amount", "type": "uint256"},
        {"name": "withdrawNonce", "type": "uint64"},
        {"name": "timestamp", "type": "uint64"},
    ]
}

# ── Module-level state (in-memory, lives as long as the process) ─────────────

_signing_key: Optional[SigningKey] = None
_public_key_b64: Optional[str] = None  # "ed25519:<base58>"
_account_id: Optional[str] = None
_wallet_address: Optional[str] = None
_registered: bool = False
_registration_lock = asyncio.Lock()


def _get_api_url() -> str:
    return os.environ.get("ORDERLY_API_URL", DEFAULT_API_URL)


def _get_broker_id() -> str:
    return os.environ.get("ORDERLY_BROKER_ID", DEFAULT_BROKER_ID)


def _get_chain_id() -> int:
    return int(os.environ.get("ORDERLY_CHAIN_ID", DEFAULT_CHAIN_ID))


def _get_domain() -> dict:
    """Get EIP-712 domain with configured chain ID."""
    chain_id = _get_chain_id()
    return {**ORDERLY_DOMAIN, "chainId": chain_id}


# ── Ed25519 Key Management ───────────────────────────────────────────────────

def _ensure_keypair() -> Tuple[SigningKey, str]:
    """Generate Ed25519 key pair if not already created."""
    global _signing_key, _public_key_b64

    if _signing_key is not None:
        return _signing_key, _public_key_b64

    _signing_key = SigningKey.generate()
    pub_bytes = _signing_key.verify_key.encode()
    _public_key_b64 = "ed25519:" + base58.b58encode(pub_bytes).decode()
    logger.info(f"Generated Orderly Ed25519 key: {_public_key_b64[:30]}...")
    return _signing_key, _public_key_b64


def _reconstruct_signature(result: dict) -> str:
    """Reconstruct flat hex signature from wallet service response."""
    sig = result.get("signature", "")

    if isinstance(sig, str):
        hex_clean = sig.replace("0x", "")
        if len(hex_clean) == 130:
            return sig if sig.startswith("0x") else f"0x{hex_clean}"

    if isinstance(sig, dict):
        r = sig.get("r", "").replace("0x", "").zfill(64)
        s = sig.get("s", "").replace("0x", "").zfill(64)
        v = sig.get("v", 0)
        if isinstance(v, str):
            v = int(v, 16) if v.startswith("0x") else int(v)
        if v < 27:
            v += 27  # Normalize 0/1 → 27/28
        return f"0x{r}{s}{v:02x}"

    raise ValueError(f"Cannot parse signature: {result}")


# ── Request Signing (Ed25519) ────────────────────────────────────────────────

def sign_request(timestamp: int, method: str, path: str, body: str = "") -> str:
    """
    Sign an API request with the in-memory Ed25519 key.

    Orderly signature format: base64(ed25519_sign(timestamp + method + path + body))
    """
    key, _ = _ensure_keypair()
    message = f"{timestamp}{method.upper()}{path}{body}"
    signed = key.sign(message.encode())
    # signed.signature is the 64-byte signature, Orderly expects standard base64
    return base64.b64encode(signed.signature).decode()


def build_auth_headers(
    method: str, path: str, body: str = ""
) -> dict:
    """
    Build full authentication headers for a private Orderly API request.

    Returns dict with: orderly-timestamp, orderly-account-id, orderly-key, orderly-signature
    """
    if not _registered or not _account_id:
        raise RuntimeError("Orderly account not registered — call ensure_registered() first")

    _, pub_key = _ensure_keypair()
    timestamp = int(time.time() * 1000)
    signature = sign_request(timestamp, method, path, body)

    headers = {
        "orderly-timestamp": str(timestamp),
        "orderly-account-id": _account_id,
        "orderly-key": pub_key,
        "orderly-signature": signature,
    }
    logger.debug(f"Orderly auth: {method} {path}, account={_account_id}, key={pub_key[:30]}...")
    return headers


# ── Privy-Based Registration Flow ────────────────────────────────────────────

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


async def _register_account(address: str) -> str:
    """
    Register account with Orderly Network via Privy EIP-712 signing.

    Steps:
    1. GET /v1/registration_nonce
    2. Sign EIP-712 Registration message via Privy
    3. POST /v1/register_account

    Returns: account_id
    """
    import aiohttp

    api_url = _get_api_url()
    broker_id = _get_broker_id()
    chain_id = _get_chain_id()

    # 1. Get registration nonce
    async with aiohttp.ClientSession() as session:
        url = f"{api_url}/v1/registration_nonce"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status >= 400:
                body = await resp.text()
                raise Exception(f"Failed to get registration nonce: HTTP {resp.status}: {body}")
            data = await resp.json()
            reg_nonce = data["data"]["registration_nonce"]

    # 2. Sign EIP-712 Registration via Privy
    timestamp = int(time.time() * 1000)
    message = {
        "brokerId": broker_id,
        "chainId": chain_id,
        "timestamp": timestamp,
        "registrationNonce": int(reg_nonce),
    }

    result = await _wallet_request("POST", "/agent/sign-typed-data", {
        "domain": _get_domain(),
        "types": REGISTRATION_TYPES,
        "primaryType": "Registration",
        "message": message,
    })

    signature = _reconstruct_signature(result)

    # 3. POST register_account
    async with aiohttp.ClientSession() as session:
        url = f"{api_url}/v1/register_account"
        payload = {
            "message": message,
            "signature": signature,
            "userAddress": address,
        }
        async with session.post(
            url, json=payload, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status >= 400:
                body = await resp.text()
                raise Exception(f"Failed to register account: HTTP {resp.status}: {body}")
            data = await resp.json()

    account_id = data.get("data", {}).get("account_id")
    if not account_id:
        raise Exception(f"No account_id in registration response: {data}")

    logger.info(f"Orderly account registered: {account_id}")
    return account_id


async def _add_orderly_key(address: str, public_key: str) -> None:
    """
    Add Ed25519 key to Orderly account via Privy EIP-712 signing.

    Steps:
    1. Sign EIP-712 AddOrderlyKey message via Privy
    2. POST /v1/orderly_key
    """
    import aiohttp

    api_url = _get_api_url()
    broker_id = _get_broker_id()
    chain_id = _get_chain_id()

    timestamp = int(time.time() * 1000)
    # Key expires in 30 days
    expiration = timestamp + (30 * 24 * 60 * 60 * 1000)

    message = {
        "brokerId": broker_id,
        "chainId": chain_id,
        "orderlyKey": public_key,
        "scope": "read,trading",
        "timestamp": timestamp,
        "expiration": expiration,
    }

    logger.info(f"Orderly _add_orderly_key: signing EIP-712 AddOrderlyKey via wallet service...")
    result = await _wallet_request("POST", "/agent/sign-typed-data", {
        "domain": _get_domain(),
        "types": ADD_KEY_TYPES,
        "primaryType": "AddOrderlyKey",
        "message": message,
    })
    logger.info(f"Orderly _add_orderly_key: wallet sign result keys={list(result.keys()) if isinstance(result, dict) else type(result)}")

    signature = _reconstruct_signature(result)
    logger.info(f"Orderly _add_orderly_key: reconstructed sig len={len(signature)}")

    async with aiohttp.ClientSession() as session:
        url = f"{api_url}/v1/orderly_key"
        payload = {
            "message": message,
            "signature": signature,
            "userAddress": address,
        }
        async with session.post(
            url, json=payload, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status >= 400:
                body = await resp.text()
                raise Exception(f"Failed to add orderly key: HTTP {resp.status}: {body}")
            data = await resp.json()

    if not data.get("success", True):
        raise Exception(f"Failed to add orderly key: {data.get('message', data)}")

    logger.info(f"Orderly key added: response={data}")
    return data


async def _check_account_exists(address: str) -> Optional[str]:
    """Check if account already exists and return account_id if so."""
    import aiohttp

    api_url = _get_api_url()
    broker_id = _get_broker_id()

    async with aiohttp.ClientSession() as session:
        url = f"{api_url}/v1/get_account?address={address}&broker_id={broker_id}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("success") and data.get("data", {}).get("account_id"):
                    return data["data"]["account_id"]
    return None


async def ensure_registered() -> str:
    """
    Ensure the agent is registered with Orderly and has an active Ed25519 key.

    Orchestrates the full flow:
    1. Generate Ed25519 key pair (in memory)
    2. Get wallet address from Privy
    3. Check if account exists, register if not
    4. Add Ed25519 key to account
    5. Return account_id

    Idempotent — safe to call multiple times. Uses asyncio.Lock to prevent
    concurrent registration attempts from parallel tool calls.
    """
    global _account_id, _registered

    if _registered and _account_id:
        return _account_id  # Fast path, no lock

    async with _registration_lock:
        if _registered and _account_id:
            return _account_id  # Double-check after acquiring lock

        # 1. Generate key pair
        _, public_key = _ensure_keypair()

        # 2. Get wallet address
        address = await _get_wallet_address()
        logger.info(f"Orderly registration: wallet address = {address}")

        # 3. Check if account exists first, register only if needed
        existing = await _check_account_exists(address)
        if existing:
            _account_id = existing
            logger.info(f"Orderly account already exists: {_account_id}")
        else:
            logger.info(f"Orderly account not found, registering...")
            _account_id = await _register_account(address)

        # 4. Add Ed25519 key (always — key is ephemeral per container boot)
        try:
            await _add_orderly_key(address, public_key)
        except Exception as e:
            logger.error(f"Orderly _add_orderly_key FAILED: {e}")
            raise

        _registered = True
        logger.info(f"Orderly ready: account={_account_id}, key={public_key[:30]}...")
        return _account_id


def get_account_id() -> Optional[str]:
    """Get the cached account ID (None if not yet registered)."""
    return _account_id


async def get_withdraw_nonce() -> int:
    """
    Get the next withdraw nonce from Orderly API.

    Requires Ed25519 registration to be complete.
    """
    import aiohttp

    if not _registered or not _account_id:
        raise RuntimeError("Orderly account not registered — call ensure_registered() first")

    api_url = _get_api_url()
    path = "/v1/withdraw_nonce"
    headers = build_auth_headers("GET", path)

    async with aiohttp.ClientSession() as session:
        url = f"{api_url}{path}"
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status >= 400:
                body = await resp.text()
                raise Exception(f"Failed to get withdraw nonce: HTTP {resp.status}: {body}")
            data = await resp.json()

    nonce = data.get("data", {}).get("withdraw_nonce")
    if nonce is None:
        raise Exception(f"No withdraw_nonce in response: {data}")

    return int(nonce)
