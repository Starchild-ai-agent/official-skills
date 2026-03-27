"""
Polymarket Authentication — EIP-712 ClobAuth + credential derivation.
Privy-only: no private key needed, uses wallet_sign_typed_data.
"""
from .utils import CHAIN_ID, BASE, clob_get, clob_post


def build_clob_auth_message(address, timestamp, nonce=0):
    """
    Build EIP-712 message for ClobAuth.
    Returns dict ready for wallet_sign_typed_data.
    """
    return {
        "domain": {
            "name": "ClobAuthDomain",
            "version": "1",
            "chainId": CHAIN_ID,
        },
        "types": {
            "ClobAuth": [
                {"name": "address", "type": "address"},
                {"name": "timestamp", "type": "string"},
                {"name": "nonce", "type": "uint256"},
                {"name": "message", "type": "string"},
            ]
        },
        "primaryType": "ClobAuth",
        "message": {
            "address": address,
            "timestamp": str(timestamp),
            "nonce": nonce,
            "message": "This message attests that I control the given wallet",
        },
    }


def derive_api_credentials(signature, address, timestamp, nonce=0):
    """
    Derive or create API credentials from signed ClobAuth message.
    Returns: {apiKey, secret, passphrase}
    """
    headers = {
        "POLY_ADDRESS": address,
        "POLY_SIGNATURE": signature,
        "POLY_TIMESTAMP": str(timestamp),
        "POLY_NONCE": str(nonce),
        "Content-Type": "application/json",
    }

    # Try derive first (existing key)
    resp = clob_get(f"{BASE}/auth/derive-api-key", headers=headers)
    if resp.status_code == 200:
        return resp.json()

    # If not found, create new
    resp = clob_post(f"{BASE}/auth/api-key", headers=headers)
    resp.raise_for_status()
    return resp.json()
