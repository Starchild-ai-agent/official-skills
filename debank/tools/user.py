#!/usr/bin/env python3
"""
DeBank User API Tools

Get user portfolio, balances, transactions, and DeFi positions.
"""

from typing import Dict, Any, Optional

try:
    from .utils import debank_api_request, validate_address, validate_chain_id
except ImportError:
    from utils import debank_api_request, validate_address, validate_chain_id


def get_user_total_balance(user_addr: str) -> Dict[str, Any]:
    """
    Get user total balance on all supported chains.

    Args:
        user_addr: User wallet address

    Returns:
        Dict with total balance in USD

    Example:
        >>> balance = get_user_total_balance("0x...")
        >>> print(f"Total: ${balance['total_usd_value']}")
    """
    user_addr = validate_address(user_addr)

    params = {"id": user_addr}
    return debank_api_request("/v1/user/total_balance", params=params)


def get_user_token_list(
    user_addr: str,
    chain_id: str,
    is_all: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Get user token balances on a chain.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier
        is_all: If true, return all tokens including zero balances

    Returns:
        Dict with token list and balances

    Example:
        >>> tokens = get_user_token_list("0x...", "eth")
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "id": user_addr,
        "chain_id": chain_id
    }

    if is_all is not None:
        params["is_all"] = is_all

    return debank_api_request("/v1/user/token_list", params=params)


def get_user_all_token_list(
    user_addr: str,
    is_all: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Get user token balances on all supported chains.

    Args:
        user_addr: User wallet address
        is_all: If true, return all tokens including zero balances

    Returns:
        Dict with token list across all chains

    Example:
        >>> tokens = get_user_all_token_list("0x...")
    """
    user_addr = validate_address(user_addr)

    params = {"id": user_addr}

    if is_all is not None:
        params["is_all"] = is_all

    return debank_api_request("/v1/user/all_token_list", params=params)


def get_user_history_list(
    user_addr: str,
    chain_id: str,
    start_time: Optional[int] = None,
    page_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get user transaction history.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier
        start_time: Start timestamp for filtering (Unix timestamp)
        page_count: Number of records per page (max 20)

    Returns:
        Dict with transaction history

    Example:
        >>> history = get_user_history_list("0x...", "eth", page_count=10)
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "id": user_addr,
        "chain_id": chain_id
    }

    if start_time is not None:
        params["start_time"] = start_time

    if page_count is not None:
        params["page_count"] = min(page_count, 20)

    return debank_api_request("/v1/user/history_list", params=params)


def get_user_all_history_list(
    user_addr: str,
    start_time: Optional[int] = None,
    page_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get user transaction history on all supported chains.

    Args:
        user_addr: User wallet address
        start_time: Start timestamp for filtering
        page_count: Number of records per page (max 20)

    Returns:
        Dict with transaction history across all chains

    Example:
        >>> history = get_user_all_history_list("0x...", page_count=20)
    """
    user_addr = validate_address(user_addr)

    params = {"id": user_addr}

    if start_time is not None:
        params["start_time"] = start_time

    if page_count is not None:
        params["page_count"] = min(page_count, 20)

    return debank_api_request("/v1/user/all_history_list", params=params)


def get_user_simple_protocol_list(
    user_addr: str,
    chain_id: str
) -> Dict[str, Any]:
    """
    Get user balance on a chain in the protocol.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier

    Returns:
        Dict with simple protocol balances

    Example:
        >>> protocols = get_user_simple_protocol_list("0x...", "eth")
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "id": user_addr,
        "chain_id": chain_id
    }
    return debank_api_request("/v1/user/simple_protocol_list", params=params)


def get_user_all_simple_protocol_list(user_addr: str) -> Dict[str, Any]:
    """
    Get user balance on all supported chains in the protocol.

    Args:
        user_addr: User wallet address

    Returns:
        Dict with simple protocol balances across all chains

    Example:
        >>> protocols = get_user_all_simple_protocol_list("0x...")
    """
    user_addr = validate_address(user_addr)

    params = {"id": user_addr}
    return debank_api_request("/v1/user/all_simple_protocol_list", params=params)


def get_user_complex_protocol_list(
    user_addr: str,
    chain_id: str
) -> Dict[str, Any]:
    """
    Get user detail portfolios on a chain in the protocol.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier

    Returns:
        Dict with detailed protocol positions

    Example:
        >>> positions = get_user_complex_protocol_list("0x...", "eth")
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "id": user_addr,
        "chain_id": chain_id
    }
    return debank_api_request("/v1/user/complex_protocol_list", params=params)


def get_user_all_complex_protocol_list(user_addr: str) -> Dict[str, Any]:
    """
    Get user detail portfolios on all supported chains in the protocol.

    Args:
        user_addr: User wallet address

    Returns:
        Dict with detailed protocol positions across all chains

    Example:
        >>> positions = get_user_all_complex_protocol_list("0x...")
    """
    user_addr = validate_address(user_addr)

    params = {"id": user_addr}
    return debank_api_request("/v1/user/all_complex_protocol_list", params=params)


def get_user_complex_app_list(user_addr: str) -> Dict[str, Any]:
    """
    Get user detail portfolios on all supported app-chain protocol.

    Args:
        user_addr: User wallet address

    Returns:
        Dict with app-chain protocol positions

    Example:
        >>> apps = get_user_complex_app_list("0x...")
    """
    user_addr = validate_address(user_addr)

    params = {"id": user_addr}
    return debank_api_request("/v1/user/complex_app_list", params=params)


def get_user_nft_list(
    user_addr: str,
    chain_id: str,
    is_all: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Get user nft list on a chain.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier
        is_all: If true, return all NFTs

    Returns:
        Dict with NFT list

    Example:
        >>> nfts = get_user_nft_list("0x...", "eth")
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "id": user_addr,
        "chain_id": chain_id
    }

    if is_all is not None:
        params["is_all"] = is_all

    return debank_api_request("/v1/user/nft_list", params=params)


def get_user_all_nft_list(
    user_addr: str,
    is_all: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Get user nft list on all supported chains.

    Args:
        user_addr: User wallet address
        is_all: If true, return all NFTs

    Returns:
        Dict with NFT list across all chains

    Example:
        >>> nfts = get_user_all_nft_list("0x...")
    """
    user_addr = validate_address(user_addr)

    params = {"id": user_addr}

    if is_all is not None:
        params["is_all"] = is_all

    return debank_api_request("/v1/user/all_nft_list", params=params)


def get_user_chain_balance(
    user_addr: str,
    chain_id: str
) -> Dict[str, Any]:
    """
    Get the balance on a chain.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier

    Returns:
        Dict with chain balance

    Example:
        >>> balance = get_user_chain_balance("0x...", "eth")
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "id": user_addr,
        "chain_id": chain_id
    }
    return debank_api_request("/v1/user/chain_balance", params=params)


def get_user_token(
    user_addr: str,
    chain_id: str,
    token_id: str
) -> Dict[str, Any]:
    """
    Get the balance of a specific token.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier
        token_id: Token contract address

    Returns:
        Dict with token balance

    Example:
        >>> token = get_user_token("0x...", "eth", "0x...")
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "id": user_addr,
        "chain_id": chain_id,
        "token_id": token_id
    }
    return debank_api_request("/v1/user/token", params=params)


def get_user_protocol(
    user_addr: str,
    protocol_id: str
) -> Dict[str, Any]:
    """
    Get user realtime portfolio in a protocol.

    Args:
        user_addr: User wallet address
        protocol_id: Protocol identifier

    Returns:
        Dict with protocol portfolio

    Example:
        >>> protocol = get_user_protocol("0x...", "uniswap")
    """
    user_addr = validate_address(user_addr)

    params = {
        "id": user_addr,
        "protocol_id": protocol_id
    }
    return debank_api_request("/v1/user/protocol", params=params)


def get_user_used_chain_list(user_addr: str) -> Dict[str, Any]:
    """
    Get the list of chains used by the user.

    Args:
        user_addr: User wallet address

    Returns:
        Dict with list of chains the user has activity on

    Example:
        >>> chains = get_user_used_chain_list("0x...")
    """
    user_addr = validate_address(user_addr)

    params = {"id": user_addr}
    return debank_api_request("/v1/user/used_chain_list", params=params)


def get_user_token_authorized_list(
    user_addr: str,
    chain_id: str
) -> Dict[str, Any]:
    """
    Get user current token authorization list.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier

    Returns:
        Dict with authorized tokens/contracts

    Example:
        >>> auth = get_user_token_authorized_list("0x...", "eth")
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "id": user_addr,
        "chain_id": chain_id
    }
    return debank_api_request("/v1/user/token_authorized_list", params=params)


def get_user_nft_authorized_list(
    user_addr: str,
    chain_id: str
) -> Dict[str, Any]:
    """
    Get user current nft authorization list.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier

    Returns:
        Dict with authorized NFT contracts

    Example:
        >>> auth = get_user_nft_authorized_list("0x...", "eth")
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "id": user_addr,
        "chain_id": chain_id
    }
    return debank_api_request("/v1/user/nft_authorized_list", params=params)


def get_user_chain_net_curve(
    user_addr: str,
    chain_id: str
) -> Dict[str, Any]:
    """
    Get user 24-hour net curve on a single chain.

    Args:
        user_addr: User wallet address
        chain_id: Chain identifier

    Returns:
        Dict with 24h net worth curve data

    Example:
        >>> curve = get_user_chain_net_curve("0x...", "eth")
    """
    user_addr = validate_address(user_addr)
    chain_id = validate_chain_id(chain_id)

    params = {
        "id": user_addr,
        "chain_id": chain_id
    }
    return debank_api_request("/v1/user/chain_net_curve", params=params)


def get_user_total_net_curve(user_addr: str) -> Dict[str, Any]:
    """
    Get user 24-hour net curve on all chains.

    Args:
        user_addr: User wallet address

    Returns:
        Dict with 24h total net worth curve across all chains

    Example:
        >>> curve = get_user_total_net_curve("0x...")
    """
    user_addr = validate_address(user_addr)

    params = {"id": user_addr}
    return debank_api_request("/v1/user/total_net_curve", params=params)
