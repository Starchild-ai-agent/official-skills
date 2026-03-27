#!/usr/bin/env python3
"""
DeBank Token API Tools

Get token information, prices, and holder data.
"""

from typing import Dict, Any, Optional, List

try:
    from .utils import debank_api_request, validate_chain_id
except ImportError:
    from utils import debank_api_request, validate_chain_id


def get_token(chain_id: str, token_id: str) -> Dict[str, Any]:
    """
    Get token details.

    Args:
        chain_id: Chain identifier (e.g., "eth", "bsc")
        token_id: Token contract address

    Returns:
        Dict with token details including symbol, name, decimals, price

    Example:
        >>> token = get_token("eth", "0x6b175474e89094c44da98b954eedeac495271d0f")
        >>> print(f"{token['symbol']}: ${token['price']}")
    """
    chain_id = validate_chain_id(chain_id)

    params = {
        "chain_id": chain_id,
        "id": token_id
    }
    return debank_api_request("/v1/token", params=params)


def get_token_history_price(
    chain_id: str,
    token_id: str,
    start_time: int,
    end_time: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get token history price.

    Args:
        chain_id: Chain identifier
        token_id: Token contract address
        start_time: Start timestamp (Unix timestamp in seconds)
        end_time: End timestamp (Unix timestamp in seconds). If not provided, uses current time

    Returns:
        Dict with historical price data

    Example:
        >>> prices = get_token_history_price("eth", "0x...", 1640995200, 1672531200)
    """
    chain_id = validate_chain_id(chain_id)

    params = {
        "chain_id": chain_id,
        "id": token_id,
        "start_time": start_time
    }

    if end_time is not None:
        params["end_time"] = end_time

    return debank_api_request("/v1/token/history_price", params=params)


def get_token_list_by_ids(chain_id: str, token_ids: List[str],
                         max_results: int = 50) -> Dict[str, Any]:
    """
    Batch fetch multiple tokens on a chain.

    Args:
        chain_id: Chain identifier
        token_ids: List of token contract addresses
        max_results: Maximum number of tokens to return (default 50)

    Returns:
        Dict with token data for each requested token

    Example:
        >>> tokens = get_token_list_by_ids("eth", ["0x...", "0x..."])
    """
    chain_id = validate_chain_id(chain_id)
    token_ids = token_ids[:max_results]

    params = {
        "chain_id": chain_id,
        "ids": ",".join(token_ids)
    }
    return debank_api_request("/v1/token/list_by_ids", params=params)


def get_token_top_holders(
    chain_id: str,
    token_id: str,
    start: Optional[int] = 0
) -> Dict[str, Any]:
    """
    Get top holders of token on a chain.

    Args:
        chain_id: Chain identifier
        token_id: Token contract address
        start: Start index for pagination (default: 0)

    Returns:
        Dict with top holders data

    Example:
        >>> holders = get_token_top_holders("eth", "0x...")
        >>> print(f"Top holder: {holders[0]['address']}")
    """
    chain_id = validate_chain_id(chain_id)

    params = {
        "chain_id": chain_id,
        "id": token_id,
        "start": start
    }
    return debank_api_request("/v1/token/top_holders", params=params)
