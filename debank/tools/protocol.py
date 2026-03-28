#!/usr/bin/env python3
"""
DeBank Protocol API Tools

Get DeFi protocol and pool information.
"""

from typing import Dict, Any

try:
    from .utils import debank_api_request, validate_chain_id
except ImportError:
    from utils import debank_api_request, validate_chain_id


def get_protocol(protocol_id: str) -> Dict[str, Any]:
    """
    Get details of a protocol.

    Args:
        protocol_id: Protocol identifier (e.g., "uniswap", "aave", "compound")

    Returns:
        Dict with protocol details including name, logo, chains, TVL

    Example:
        >>> protocol = get_protocol("uniswap")
        >>> print(f"{protocol['name']}: ${protocol['tvl']}")
    """
    params = {"id": protocol_id}
    return debank_api_request("/v1/protocol", params=params)


def get_protocol_list(chain_id: str) -> Dict[str, Any]:
    """
    Get protocols of a chain.

    Args:
        chain_id: Chain identifier

    Returns:
        Dict with list of protocols on the chain

    Example:
        >>> protocols = get_protocol_list("eth")
    """
    chain_id = validate_chain_id(chain_id)

    params = {"chain_id": chain_id}
    return debank_api_request("/v1/protocol/list", params=params)


def get_protocol_all_list() -> Dict[str, Any]:
    """
    Get all protocols of supported chains.

    Returns:
        Dict with all protocols across all chains

    Example:
        >>> protocols = get_protocol_all_list()
    """
    return debank_api_request("/v1/protocol/all_list")


def get_app_protocol_list() -> Dict[str, Any]:
    """
    Get all app-protocols.

    Returns:
        Dict with app-chain protocols

    Example:
        >>> app_protocols = get_app_protocol_list()
    """
    return debank_api_request("/v1/app_protocol/list")


def get_pool(
    protocol_id: str,
    chain_id: str,
    pool_id: str
) -> Dict[str, Any]:
    """
    Get details of a pool.

    Args:
        protocol_id: Protocol identifier
        chain_id: Chain identifier
        pool_id: Pool identifier (usually contract address)

    Returns:
        Dict with pool details including tokens, TVL, APY

    Example:
        >>> pool = get_pool("uniswap", "eth", "0x...")
        >>> print(f"APY: {pool['apy']}%")
    """
    chain_id = validate_chain_id(chain_id)

    params = {
        "protocol_id": protocol_id,
        "chain_id": chain_id,
        "id": pool_id
    }
    return debank_api_request("/v1/pool", params=params)
