#!/usr/bin/env python3
"""
DeBank API Utilities

This module provides utility functions for DeBank API tools including:
- API request helpers with authentication
- Input validation and normalization
- Error handling and retry logic
"""

import os
import time
from typing import Dict, Any, Optional
import requests
from core.http_client import proxied_get, proxied_post

# Load environment variables

# DeBank API base URL
DEBANK_API_BASE = "https://pro-openapi.debank.com"

def get_debank_headers() -> Dict[str, str]:
    """
    Get headers for DeBank API requests.

    Returns:
        Dict[str, str]: Headers including API key

    Raises:
        ValueError: If DEBANK_API_KEY is not set
    """
    api_key = os.getenv("DEBANK_API_KEY")
    if not api_key:
        raise ValueError(
            "DEBANK_API_KEY environment variable is required. "
            "Get your API key from https://docs.cloud.debank.com/"
        )

    return {
        "AccessKey": api_key,
        "accept": "application/json"
    }

def debank_api_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    method: str = "GET",
    max_retries: int = 3,
    retry_delay: float = 1.0,
    max_results: int = 100
) -> Dict[str, Any]:
    """
    Make a request to DeBank API with retry logic.

    Args:
        endpoint: API endpoint path (e.g., "/v1/user/total_balance")
        params: Query parameters
        method: HTTP method (default: GET)
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Dict[str, Any]: API response data

    Raises:
        requests.RequestException: If API request fails after retries
    """
    url = f"{DEBANK_API_BASE}{endpoint}"
    headers = get_debank_headers()

    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = proxied_get(url, headers=headers, params=params, timeout=30)
            elif method == "POST":
                response = proxied_post(url, headers=headers, json=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            data = response.json()
            # Truncate large list responses
            if isinstance(data, list) and len(data) > max_results:
                data = data[:max_results]
            return data

        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                raise requests.RequestException("Request timeout - DeBank API may be slow")
            time.sleep(retry_delay)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                if attempt == max_retries - 1:
                    raise requests.RequestException("Rate limit exceeded - please wait before retrying")
                time.sleep(retry_delay * 2)  # Longer delay for rate limits
            elif e.response.status_code >= 500:  # Server error
                if attempt == max_retries - 1:
                    raise requests.RequestException(f"Server error: {e}")
                time.sleep(retry_delay)
            else:
                raise requests.RequestException(f"HTTP error: {e}")

        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                raise requests.RequestException("Connection error - check internet connection")
            time.sleep(retry_delay)

        except Exception as e:
            if attempt == max_retries - 1:
                raise requests.RequestException(f"API request failed: {e}")
            time.sleep(retry_delay)

    raise requests.RequestException("Max retries exceeded")

def validate_address(address: str) -> str:
    """
    Validate and normalize Ethereum address.

    Args:
        address: Ethereum address

    Returns:
        str: Normalized address (lowercase)

    Raises:
        ValueError: If address is invalid
    """
    if not address or not isinstance(address, str):
        raise ValueError("Address must be a non-empty string")

    address = address.strip().lower()

    if not address.startswith("0x"):
        raise ValueError("Address must start with '0x'")

    if len(address) != 42:
        raise ValueError("Address must be 42 characters long (0x + 40 hex chars)")

    # Check if valid hex
    try:
        int(address[2:], 16)
    except ValueError:
        raise ValueError("Address must contain only hexadecimal characters")

    return address

def validate_chain_id(chain_id: str) -> str:
    """
    Validate and normalize chain ID.

    Args:
        chain_id: Chain identifier

    Returns:
        str: Normalized chain ID (lowercase)

    Raises:
        ValueError: If chain_id is invalid
    """
    if not chain_id or not isinstance(chain_id, str):
        raise ValueError("Chain ID must be a non-empty string")

    return chain_id.strip().lower()

def format_token_amount(amount: float, decimals: int) -> str:
    """
    Format token amount with decimals.

    Args:
        amount: Raw token amount
        decimals: Number of decimal places

    Returns:
        str: Formatted amount
    """
    if decimals == 0:
        return str(int(amount))

    formatted = amount / (10 ** decimals)
    return f"{formatted:.{min(decimals, 8)}f}"

def safe_get(data: Dict[str, Any], *keys, default=None) -> Any:
    """
    Safely get nested dictionary values.

    Args:
        data: Dictionary to query
        *keys: Sequence of keys to traverse
        default: Default value if key path doesn't exist

    Returns:
        Value at key path or default

    Example:
        >>> safe_get({"a": {"b": {"c": 1}}}, "a", "b", "c")
        1
        >>> safe_get({"a": {"b": {}}}, "a", "b", "c", default=0)
        0
    """
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current
