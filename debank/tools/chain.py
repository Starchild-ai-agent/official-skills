#!/usr/bin/env python3
"""
DeBank Chain API Tools

Get information about supported blockchains.
"""

from typing import Dict, Any

try:
    from .utils import debank_api_request, validate_chain_id
except ImportError:
    from utils import debank_api_request, validate_chain_id

def get_chain_list() -> Dict[str, Any]:
    """
    Get the list of current support chains.

    Returns:
        Dict with list of supported chains and their metadata

    Example:
        >>> chains = get_chain_list()
        >>> print(chains)
    """
    return debank_api_request("/v1/chain/list")

def get_chain(chain_id: str) -> Dict[str, Any]:
    """
    Get details of a specific chain.

    Args:
        chain_id: Chain identifier (e.g., "eth", "bsc", "polygon")

    Returns:
        Dict with chain details including name, native token, etc.

    Example:
        >>> chain = get_chain("eth")
        >>> print(chain)
    """
    chain_id = validate_chain_id(chain_id)

    params = {"id": chain_id}
    return debank_api_request("/v1/chain", params=params)

def get_gas_market(chain_id: str) -> Dict[str, Any]:
    """
    Get gas prices for a specific chain.

    Args:
        chain_id: Chain identifier (e.g., "eth", "bsc", "polygon")

    Returns:
        Dict with gas market data including slow, normal, fast, and rapid prices

    Example:
        >>> gas = get_gas_market("eth")
        >>> print(f"Fast gas: {gas['fast']}")
    """
    chain_id = validate_chain_id(chain_id)

    params = {"chain_id": chain_id}
    return debank_api_request("/v1/wallet/gas_market", params=params)
