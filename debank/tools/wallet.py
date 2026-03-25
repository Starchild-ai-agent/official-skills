#!/usr/bin/env python3
"""
DeBank Wallet API Tools

Transaction simulation and explanation.
"""

from typing import Dict, Any

try:
    from .utils import debank_api_request, validate_address, validate_chain_id
except ImportError:
    from utils import debank_api_request, validate_address, validate_chain_id


def pre_exec_tx(
    user_addr: str,
    chain_id: str,
    tx: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enhanced pre-execute transaction.

    Simulates a transaction before sending it to the blockchain.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier
        tx: Transaction object with fields:
            - from: Sender address
            - to: Recipient address
            - value: Amount in wei (hex or decimal)
            - data: Transaction data (hex)
            - gas: Gas limit (optional)
            - gasPrice: Gas price (optional)

    Returns:
        Dict with simulation results including balance changes, gas estimates

    Example:
        >>> tx = {
        ...     "from": "0x...",
        ...     "to": "0x...",
        ...     "value": "0x0",
        ...     "data": "0x..."
        ... }
        >>> result = pre_exec_tx("0x...", "eth", tx)
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "user_addr": user_addr,
        "chain_id": chain_id,
        "tx": tx
    }
    return debank_api_request("/v1/wallet/pre_exec_tx", params=params, method="POST")


def explain_tx(
    user_addr: str,
    chain_id: str,
    tx: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Explain transaction.

    Provides human-readable explanation of what a transaction does.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier
        tx: Transaction object with fields:
            - from: Sender address
            - to: Recipient address
            - value: Amount in wei
            - data: Transaction data (hex)

    Returns:
        Dict with transaction explanation

    Example:
        >>> tx = {
        ...     "from": "0x...",
        ...     "to": "0x...",
        ...     "value": "0x0",
        ...     "data": "0x..."
        ... }
        >>> explanation = explain_tx("0x...", "eth", tx)
        >>> print(explanation['description'])
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "user_addr": user_addr,
        "chain_id": chain_id,
        "tx": tx
    }
    return debank_api_request("/v1/wallet/explain_tx", params=params, method="POST")
