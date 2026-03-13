"""
Hyperliquid L1 Action Signing — phantom agent EIP-712 pattern.

Hyperliquid trading actions (orders, cancels, leverage, modify) require an EIP-712
"Agent" signature over a keccak256 hash of the msgpack-serialized action.

Since we don't have direct private key access (Privy server wallet), we delegate
EIP-712 signing to the wallet service's /agent/sign-typed-data endpoint.

Two signing schemes:
1. L1 Action (orders, cancels, leverage) — msgpack → keccak → Agent struct
2. User-Signed (USDC transfers, withdrawals) — direct EIP-712 over action fields

The connectionId field (bytes32) encoding must match what the Privy wallet service
expects. We try multiple encodings and verify each with local ecrecover.
"""

import logging
from typing import Optional

import msgpack
from eth_utils import keccak

from tools.wallet import _wallet_request

logger = logging.getLogger(__name__)

# Hyperliquid chain constants
MAINNET_SOURCE = "a"

# EIP-712 domains
L1_DOMAIN = {
    "name": "Exchange",
    "version": "1",
    "chainId": 1337,
    "verifyingContract": "0x0000000000000000000000000000000000000000",
}

USER_SIGNED_DOMAIN = {
    "name": "HyperliquidSignTransaction",
    "version": "1",
    "chainId": 42161,  # Arbitrum mainnet
    "verifyingContract": "0x0000000000000000000000000000000000000000",
}

# EIP-712 types for Agent struct
AGENT_TYPES = {
    "Agent": [
        {"name": "source", "type": "string"},
        {"name": "connectionId", "type": "bytes32"},
    ]
}


# ── Wallet address cache ─────────────────────────────────────────────────

_cached_wallet_address: Optional[str] = None


async def _get_wallet_address() -> Optional[str]:
    """Get the Privy wallet address for signature verification (cached)."""
    global _cached_wallet_address
    if _cached_wallet_address:
        return _cached_wallet_address

    try:
        from tools.wallet import _is_fly_machine
        if not _is_fly_machine():
            return None

        data = await _wallet_request("GET", "/agent/wallet")
        wallets = data if isinstance(data, list) else data.get("wallets", [])
        for w in wallets:
            if w.get("chain_type") == "ethereum":
                _cached_wallet_address = w["wallet_address"].lower()
                return _cached_wallet_address
    except Exception as e:
        logger.debug(f"Could not fetch wallet address for verification: {e}")

    return None


# ── EIP-712 hash computation (manual, no encode_typed_data dependency) ────

def _eip712_domain_separator(domain: dict) -> bytes:
    """Compute EIP-712 domain separator hash."""
    type_hash = keccak(
        b"EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    )
    encoded = type_hash
    encoded += keccak(domain["name"].encode())
    encoded += keccak(domain["version"].encode())
    encoded += domain["chainId"].to_bytes(32, "big")
    addr = domain["verifyingContract"].replace("0x", "")
    encoded += bytes.fromhex(addr).rjust(32, b"\x00")
    return keccak(encoded)


def _eip712_encode_field(field_type: str, value) -> bytes:
    """ABI-encode a single EIP-712 field value to 32 bytes."""
    if field_type == "string":
        return keccak(value.encode() if isinstance(value, str) else value)
    elif field_type == "bytes32":
        if isinstance(value, bytes):
            return value.ljust(32, b"\x00")
        elif isinstance(value, str):
            return bytes.fromhex(value.replace("0x", "")).ljust(32, b"\x00")
        elif isinstance(value, list):
            return bytes(value).ljust(32, b"\x00")
    elif field_type in ("uint256", "uint64"):
        return int(value).to_bytes(32, "big")
    elif field_type == "bool":
        return int(bool(value)).to_bytes(32, "big")
    elif field_type == "address":
        return bytes.fromhex(value.replace("0x", "")).rjust(32, b"\x00")
    raise ValueError(f"Unsupported EIP-712 type: {field_type}")


def _eip712_hash_struct(primary_type: str, types: dict, message: dict) -> bytes:
    """Compute hashStruct for an EIP-712 message."""
    fields = types[primary_type]
    type_string = (
        primary_type
        + "("
        + ",".join(f"{f['type']} {f['name']}" for f in fields)
        + ")"
    )
    encoded = keccak(type_string.encode())
    for field in fields:
        encoded += _eip712_encode_field(field["type"], message[field["name"]])
    return keccak(encoded)


def _eip712_digest(domain: dict, types: dict, primary_type: str, message: dict) -> bytes:
    """Compute the full EIP-712 digest: keccak256(0x1901 || domainSep || structHash)."""
    domain_sep = _eip712_domain_separator(domain)
    struct_hash = _eip712_hash_struct(primary_type, types, message)
    return keccak(b"\x19\x01" + domain_sep + struct_hash)


# ── Local ecrecover verification ──────────────────────────────────────────

def _verify_signature_locally(
    domain: dict,
    types: dict,
    primary_type: str,
    message: dict,
    signature_hex: str,
    expected_address: Optional[str],
) -> bool:
    """
    Verify an EIP-712 signature locally using ecrecover.

    Computes the EIP-712 hash manually (no encode_typed_data dependency)
    and recovers the signer address from the signature.

    Returns True if the recovered address matches expected_address.
    """
    if not expected_address:
        return True  # Can't verify without address, assume OK

    try:
        from eth_keys import keys

        digest = _eip712_digest(domain, types, primary_type, message)

        sig_bytes = bytes.fromhex(signature_hex.replace("0x", ""))
        r = int.from_bytes(sig_bytes[:32], "big")
        s = int.from_bytes(sig_bytes[32:64], "big")
        v = sig_bytes[64]
        if v >= 27:
            v -= 27

        sig = keys.Signature(vrs=(v, r, s))
        public_key = sig.recover_public_key_from_msg_hash(digest)
        recovered = public_key.to_checksum_address()
        recovered_lower = recovered.lower()
        expected_lower = expected_address.lower()

        if recovered_lower == expected_lower:
            logger.info(f"EIP-712 ecrecover OK: {recovered}")
            return True
        else:
            logger.warning(
                f"EIP-712 ecrecover MISMATCH: recovered={recovered}, expected={expected_address}"
            )
            return False

    except Exception as e:
        logger.warning(f"Local ecrecover verification failed: {e}")
        return False


def _signature_to_hex(sig: dict) -> str:
    """Convert {r, s, v} dict to flat hex signature string."""
    r = sig["r"].replace("0x", "").zfill(64)
    s = sig["s"].replace("0x", "").zfill(64)
    v = sig["v"]
    return "0x" + r + s + format(v, "02x")


# ── Core hashing ──────────────────────────────────────────────────────────

def action_hash(action: dict, vault_address: Optional[str], nonce: int) -> bytes:
    """
    Compute keccak256 hash of a Hyperliquid L1 action.

    Steps:
    1. msgpack serialize the action dict
    2. Append nonce as 8-byte big-endian
    3. Append vault flag: 0x01 if vault_address else 0x00
    4. If vault, append 20 bytes of vault address
    5. keccak256 the whole blob
    """
    data = msgpack.packb(action)
    data += nonce.to_bytes(8, "big")

    if vault_address:
        data += b"\x01"
        # Remove 0x prefix if present, decode hex to bytes
        addr_bytes = bytes.fromhex(vault_address.replace("0x", ""))
        data += addr_bytes
    else:
        data += b"\x00"

    return keccak(data)


# ── L1 Action Signing (orders, cancels, leverage) ────────────────────────

async def sign_l1_action(
    action: dict,
    nonce: int,
    vault_address: Optional[str] = None,
) -> dict:
    """
    Sign an L1 action (order, cancel, leverage, modify) via wallet service.

    Tries multiple connectionId encodings and verifies each with local ecrecover.
    Uses the first encoding that produces a signature matching the wallet address.

    Returns: {"r": "0x...", "s": "0x...", "v": 27|28}
    """
    hash_bytes = action_hash(action, vault_address, nonce)
    source = MAINNET_SOURCE
    expected_address = await _get_wallet_address()

    # Multiple connectionId encodings to try
    encodings = [
        ("hex_with_0x", "0x" + hash_bytes.hex()),          # current: hex string with prefix
        ("byte_array",  list(hash_bytes)),                  # byte array as list of ints
        ("hex_no_prefix", hash_bytes.hex()),                # hex string without 0x prefix
    ]

    last_error = None
    for encoding_name, connection_id_value in encodings:
        try:
            payload = {
                "domain": L1_DOMAIN,
                "types": AGENT_TYPES,
                "primaryType": "Agent",
                "message": {
                    "source": source,
                    "connectionId": connection_id_value,
                },
            }

            logger.info(
                f"sign_l1_action: trying encoding={encoding_name}, "
                f"connectionId type={type(connection_id_value).__name__}"
            )

            result = await _wallet_request("POST", "/agent/sign-typed-data", payload)
            sig = _parse_signature(result)

            # Verify locally with ecrecover
            # For verification, connectionId must be the raw bytes32
            verify_message = {
                "source": source,
                "connectionId": hash_bytes,
            }

            sig_hex = _signature_to_hex(sig)
            match = _verify_signature_locally(
                domain=L1_DOMAIN,
                types=AGENT_TYPES,
                primary_type="Agent",
                message=verify_message,
                signature_hex=sig_hex,
                expected_address=expected_address,
            )

            if match:
                logger.info(f"sign_l1_action: encoding={encoding_name} VERIFIED")
                return sig
            else:
                logger.warning(
                    f"sign_l1_action: encoding={encoding_name} signature mismatch, trying next"
                )

        except Exception as e:
            logger.warning(f"sign_l1_action: encoding={encoding_name} failed: {e}")
            last_error = e

    raise RuntimeError(
        f"sign_l1_action: No encoding produced a verified signature. "
        f"Expected address: {expected_address}. Last error: {last_error}"
    )


# ── User-Signed Action (transfers, withdrawals, abstraction) ──────────────────────────

async def sign_user_set_abstraction(
    user: str,
    abstraction: str,
    nonce: int,
) -> dict:
    """Sign a user set abstraction action.

    Uses HyperliquidSignTransaction domain for user-signed actions.
    Matches SDK's sign_user_set_abstraction_action exactly.

    Args:
        user: User address (lowercase)
        abstraction: Abstraction mode ("unifiedAccount", "portfolioMargin", "disabled")
        nonce: Timestamp in milliseconds

    Returns: {"r": "0x...", "s": "0x...", "v": 27|28}
    """
    types = {
        "HyperliquidTransaction:UserSetAbstraction": [
            {"name": "hyperliquidChain", "type": "string"},
            {"name": "user", "type": "address"},  # ADDRESS, not string!
            {"name": "abstraction", "type": "string"},
            {"name": "nonce", "type": "uint64"},
        ]
    }

    action = {
        "hyperliquidChain": "Mainnet",
        "user": user.lower(),
        "abstraction": abstraction,
        "nonce": nonce,
    }

    return await sign_user_action(
        action=action,
        types=types,
        primary_type="HyperliquidTransaction:UserSetAbstraction",
    )


async def sign_user_action(
    action: dict,
    types: dict,
    primary_type: str,
) -> dict:
    """
    Sign a user-level action (USDC transfer, withdrawal) via wallet service.
    Uses the HyperliquidSignTransaction domain (no msgpack/keccak).

    Verifies the signature locally with ecrecover before returning.

    Returns: {"r": "0x...", "s": "0x...", "v": 27|28}
    """
    expected_address = await _get_wallet_address()

    payload = {
        "domain": USER_SIGNED_DOMAIN,
        "types": types,
        "primaryType": primary_type,
        "message": action,
    }

    result = await _wallet_request("POST", "/agent/sign-typed-data", payload)
    sig = _parse_signature(result)

    # Verify locally
    sig_hex = _signature_to_hex(sig)
    match = _verify_signature_locally(
        domain=USER_SIGNED_DOMAIN,
        types=types,
        primary_type=primary_type,
        message=action,
        signature_hex=sig_hex,
        expected_address=expected_address,
    )

    if not match:
        logger.error(
            f"sign_user_action: signature mismatch! "
            f"Expected address: {expected_address}, action type: {primary_type}"
        )

    return sig


# ── Signature parsing ─────────────────────────────────────────────────────

def _parse_signature(result: dict) -> dict:
    """
    Parse signature from wallet service into {r, s, v} format.

    The wallet service may return either:
    - A flat hex signature string in result["signature"]
    - Already-split {r, s, v} components
    """
    sig = result.get("signature", result)

    if isinstance(sig, str):
        # Flat hex signature — split into r, s, v
        sig_hex = sig.replace("0x", "")
        if len(sig_hex) == 130:
            r = "0x" + sig_hex[:64]
            s = "0x" + sig_hex[64:128]
            v = int(sig_hex[128:130], 16)
            # Normalize v to 27/28
            if v < 27:
                v += 27
            return {"r": r, "s": s, "v": v}
        raise ValueError(f"Unexpected signature length: {len(sig_hex)}")

    if isinstance(sig, dict):
        # Already has components
        r = sig.get("r", "")
        s = sig.get("s", "")
        v = sig.get("v", 0)
        if isinstance(v, str):
            v = int(v, 16) if v.startswith("0x") else int(v)
        if v < 27:
            v += 27
        return {"r": r, "s": s, "v": v}

    raise ValueError(f"Cannot parse signature from wallet response: {result}")
