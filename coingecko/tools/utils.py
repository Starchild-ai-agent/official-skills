#!/usr/bin/env python3
"""
CoinGecko API Utilities

This module provides utility functions for CoinGecko API tools including:
- Natural language time parsing
- Automatic data splitting for large time ranges  
- Input validation and normalization
- Cryptocurrency search functionality (search by name/symbol with market cap ranking)
"""

import re
from datetime import datetime, timedelta
from typing import Union, List, Tuple, Optional, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import requests
from core.http_client import proxied_get


def normalize_timestamp_to_seconds(timestamp: Union[int, float]) -> int:
    """
    Automatically detect and convert timestamp format (seconds or milliseconds) to seconds.
    
    Args:
        timestamp: Unix timestamp in seconds or milliseconds
        
    Returns:
        int: Unix timestamp in seconds
        
    Example:
        >>> normalize_timestamp_to_seconds(1672531200)     # seconds
        1672531200
        >>> normalize_timestamp_to_seconds(1672531200000)  # milliseconds
        1672531200
    """
    timestamp = int(timestamp)
    
    # Timestamps after year 2001 and before year 2286 in milliseconds format
    # Milliseconds: 13 digits, starts around 1000000000000 (2001)
    # Seconds: 10 digits, starts around 1000000000 (2001)
    if timestamp > 1000000000000:  # Likely milliseconds (13+ digits)
        return timestamp // 1000
    else:  # Likely seconds (10 digits or less)
        return timestamp


def normalize_timestamp_to_milliseconds(timestamp: Union[int, float]) -> int:
    """
    Automatically detect and convert timestamp format (seconds or milliseconds) to milliseconds.
    
    Args:
        timestamp: Unix timestamp in seconds or milliseconds
        
    Returns:
        int: Unix timestamp in milliseconds
        
    Example:
        >>> normalize_timestamp_to_milliseconds(1672531200)     # seconds
        1672531200000
        >>> normalize_timestamp_to_milliseconds(1672531200000)  # milliseconds
        1672531200000
    """
    timestamp = int(timestamp)
    
    if timestamp > 1000000000000:  # Already milliseconds
        return timestamp
    else:  # Convert from seconds to milliseconds
        return timestamp * 1000


def parse_flexible_time(time_input: Union[str, int, float]) -> int:
    """
    Parse flexible time input to Unix timestamp with automatic seconds/milliseconds conversion.
    
    Args:
        time_input: Can be:
            - Unix timestamp (int/float) - automatically detects seconds vs milliseconds
            - ISO date string (YYYY-MM-DD)
            - Natural language (e.g., "2 weeks ago", "yesterday", "last month")
            - Datetime string (YYYY-MM-DD HH:MM:SS)
    
    Returns:
        int: Unix timestamp in seconds
    
    Example:
        >>> parse_flexible_time("2023-01-01")
        1672531200
        >>> parse_flexible_time("2 weeks ago")
        # Returns timestamp for 2 weeks ago
        >>> parse_flexible_time(1672531200)
        1672531200
        >>> parse_flexible_time(1672531200000)  # milliseconds auto-converted
        1672531200
    """
    if isinstance(time_input, (int, float)):
        # Auto-convert milliseconds to seconds if needed
        return normalize_timestamp_to_seconds(time_input)
    
    # Clean string input and try to parse as timestamp first
    time_str = str(time_input).strip().lower()
    # Remove common shell artifacts like quotes
    time_str = time_str.strip("'\"")
    
    # Try to parse as numeric timestamp first
    if time_str.isdigit():
        return normalize_timestamp_to_seconds(int(time_str))
    
    # Try ISO date formats
    iso_patterns = [
        r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
        r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$',  # YYYY-MM-DD HH:MM:SS
        r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
        r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
        r'^\d{2}-\d{2}-\d{4}$'   # DD-MM-YYYY (for historical data format)
    ]
    
    for pattern in iso_patterns:
        if re.match(pattern, time_str):
            return _parse_date_string(time_str)
    
    # Parse natural language
    return _parse_natural_language(time_str)


def _parse_date_string(date_str: str) -> int:
    """Parse various date string formats to Unix timestamp."""
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d',
        '%m/%d/%Y',
        '%d-%m-%Y'
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return int(dt.timestamp())
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date string: {date_str}")


def _parse_natural_language(text: str) -> int:
    """Parse natural language time expressions to Unix timestamp."""
    now = datetime.now()
    
    # Handle "today", "yesterday", etc.
    if text in ['today', 'now']:
        return int(now.timestamp())
    elif text == 'yesterday':
        return int((now - timedelta(days=1)).timestamp())
    elif text == 'tomorrow':
        return int((now + timedelta(days=1)).timestamp())
    
    # Handle relative time expressions
    relative_patterns = [
        (r'(\d+)\s*(second|sec)s?\s*ago', 'seconds'),
        (r'(\d+)\s*(minute|min)s?\s*ago', 'minutes'),
        (r'(\d+)\s*(hour|hr)s?\s*ago', 'hours'),
        (r'(\d+)\s*(day)s?\s*ago', 'days'),
        (r'(\d+)\s*(week)s?\s*ago', 'weeks'),
        (r'(\d+)\s*(month)s?\s*ago', 'months'),
        (r'(\d+)\s*(year)s?\s*ago', 'years'),
        (r'last\s*(week)', 'weeks'),
        (r'last\s*(month)', 'months'),
        (r'last\s*(year)', 'years')
    ]
    
    for pattern, unit in relative_patterns:
        match = re.search(pattern, text)
        if match:
            if match.group(1).isdigit():
                amount = int(match.group(1))
            else:
                amount = 1  # for "last week", etc.
            
            if unit == 'seconds':
                delta = timedelta(seconds=amount)
            elif unit == 'minutes':
                delta = timedelta(minutes=amount)
            elif unit == 'hours':
                delta = timedelta(hours=amount)
            elif unit == 'days':
                delta = timedelta(days=amount)
            elif unit == 'weeks':
                delta = timedelta(weeks=amount)
            elif unit == 'months':
                # Approximate months as 30 days
                delta = timedelta(days=amount * 30)
            elif unit == 'years':
                # Approximate years as 365 days
                delta = timedelta(days=amount * 365)
            else:
                continue
            
            return int((now - delta).timestamp())
    
    raise ValueError(f"Unable to parse natural language time: {text}")


def split_time_range(from_timestamp: int, to_timestamp: int, max_days: int = 180) -> List[Tuple[int, int]]:
    """
    Split a time range into chunks that don't exceed the maximum days limit.
    
    Args:
        from_timestamp: Start timestamp
        to_timestamp: End timestamp
        max_days: Maximum days per chunk (default 180 for CoinGecko)
    
    Returns:
        List of (start, end) timestamp tuples
    
    Example:
        >>> splits = split_time_range(1640995200, 1672531200, 180)  # 1 year range
        >>> len(splits)
        3  # Split into 3 chunks
    """
    if from_timestamp >= to_timestamp:
        raise ValueError("from_timestamp must be less than to_timestamp")
    
    total_seconds = to_timestamp - from_timestamp
    max_seconds = max_days * 24 * 60 * 60  # Convert days to seconds
    
    if total_seconds <= max_seconds:
        return [(from_timestamp, to_timestamp)]
    
    chunks = []
    current_start = from_timestamp
    
    while current_start < to_timestamp:
        current_end = min(current_start + max_seconds, to_timestamp)
        chunks.append((current_start, current_end))
        current_start = current_end
    
    return chunks


def validate_coin_input(coin_input: str) -> str:
    """
    Validate and normalize coin input (ID or symbol).
    
    Args:
        coin_input: Coin ID or symbol
    
    Returns:
        str: Normalized coin input
    
    Raises:
        ValueError: If input is invalid
    """
    if not coin_input or not isinstance(coin_input, str):
        raise ValueError("Coin input must be a non-empty string")
    
    return coin_input.strip().lower()


def format_dd_mm_yyyy_date(timestamp: int) -> str:
    """
    Convert Unix timestamp to dd-mm-yyyy format for CoinGecko historical API.
    
    Args:
        timestamp: Unix timestamp
    
    Returns:
        str: Date in dd-mm-yyyy format
    """
    dt = datetime.utcfromtimestamp(timestamp)
    return dt.strftime('%d-%m-%Y')


def get_days_difference(from_timestamp: int, to_timestamp: int) -> int:
    """
    Calculate the number of days between two timestamps.
    
    Args:
        from_timestamp: Start timestamp
        to_timestamp: End timestamp
    
    Returns:
        int: Number of days
    """
    return int((to_timestamp - from_timestamp) / (24 * 60 * 60))


def merge_ohlc_data(data_chunks: List[List]) -> List:
    """
    Merge multiple OHLC data chunks into a single list.
    
    Args:
        data_chunks: List of OHLC data chunks
    
    Returns:
        List: Merged OHLC data sorted by timestamp
    """
    merged = []
    for chunk in data_chunks:
        merged.extend(chunk)
    
    # Sort by timestamp (first element in each OHLC array)
    merged.sort(key=lambda x: x[0])
    
    # Remove duplicates (same timestamp)
    seen_timestamps = set()
    unique_data = []
    for item in merged:
        timestamp = item[0]
        if timestamp not in seen_timestamps:
            seen_timestamps.add(timestamp)
            unique_data.append(item)
    
    return unique_data


def merge_market_chart_data(data_chunks: List[dict]) -> dict:
    """
    Merge multiple market chart data chunks into a single dictionary.
    
    Args:
        data_chunks: List of market chart data dictionaries
    
    Returns:
        dict: Merged market chart data with sorted timestamps
    """
    merged = {
        'prices': [],
        'market_caps': [],
        'total_volumes': []
    }
    
    for chunk in data_chunks:
        if 'prices' in chunk:
            merged['prices'].extend(chunk['prices'])
        if 'market_caps' in chunk:
            merged['market_caps'].extend(chunk['market_caps'])
        if 'total_volumes' in chunk:
            merged['total_volumes'].extend(chunk['total_volumes'])
    
    # Sort all arrays by timestamp
    for key in merged:
        merged[key].sort(key=lambda x: x[0])
        
        # Remove duplicates
        seen_timestamps = set()
        unique_data = []
        for item in merged[key]:
            timestamp = item[0]
            if timestamp not in seen_timestamps:
                seen_timestamps.add(timestamp)
                unique_data.append(item)
        merged[key] = unique_data
    
    return merged


def search_coin_by_name(query: str, max_results: int = 100) -> Optional[Dict[str, str]]:
    """
    Search for a cryptocurrency by name or symbol with intelligent input detection.
    
    - All uppercase input (e.g., "BTC") is treated as symbol search
    - Input with ≤3 letters (e.g., "btc", "eth", "sol") is treated as symbol search
    - Other mixed/lowercase input (e.g., "bitcoin", "Bitcoin") is treated as name search
    - Symbol search: prioritizes exact symbol match, then market cap ranking
    - Name search: prioritizes exact name match, then market cap ranking
    
    Special cases handled:
    - ORDER/order/Order -> Orderly Network (orderly-network)
    - orderly-network -> Returns directly as valid CoinGecko ID
    
    Args:
        query (str): Search query - uppercase or ≤3 letters for symbol, otherwise name search
        
    Returns:
        Optional[Dict[str, str]]: Dictionary with symbol, name, and id of the best match, or None if not found
        
    Example:
        >>> search_coin_by_name("BTC")     # Symbol search (uppercase)
        {'symbol': 'BTC', 'name': 'Bitcoin', 'id': 'bitcoin'}
        >>> search_coin_by_name("btc")     # Symbol search (≤3 letters)
        {'symbol': 'BTC', 'name': 'Bitcoin', 'id': 'bitcoin'}
        >>> search_coin_by_name("bitcoin") # Name search (>3 letters, mixed case)
        {'symbol': 'BTC', 'name': 'Bitcoin', 'id': 'bitcoin'}
        >>> search_coin_by_name("order")   # Special case for Orderly Network
        {'symbol': 'ORDER', 'name': 'Orderly Network', 'id': 'orderly-network'}
        
    Raises:
        ValueError: If API key is missing or query is invalid
        requests.RequestException: If API request fails
    """
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string")
    
    # Special case mappings for ambiguous tokens and direct CoinGecko IDs
    # When users say "ORDER", they almost always mean Orderly Network
    # When users say "WOO", they mean WOO Network (id: woo-network, not woo)
    special_mappings = {
        'order': {'symbol': 'ORDER', 'name': 'Orderly Network', 'id': 'orderly-network'},
        'ORDER': {'symbol': 'ORDER', 'name': 'Orderly Network', 'id': 'orderly-network'},
        'Order': {'symbol': 'ORDER', 'name': 'Orderly Network', 'id': 'orderly-network'},
        'orderly-network': {'symbol': 'ORDER', 'name': 'Orderly Network', 'id': 'orderly-network'},  # Handle direct ID
        'woo': {'symbol': 'WOO', 'name': 'WOO', 'id': 'woo-network'},
        'WOO': {'symbol': 'WOO', 'name': 'WOO', 'id': 'woo-network'},
        'Woo': {'symbol': 'WOO', 'name': 'WOO', 'id': 'woo-network'},
        'woo-network': {'symbol': 'WOO', 'name': 'WOO', 'id': 'woo-network'},  # Handle direct ID
    }
    
    # Check for special cases first
    query_stripped = query.strip()
    if query_stripped in special_mappings:
        return special_mappings[query_stripped]
    
    # Get API key
    api_key = os.getenv("COINGECKO_API_KEY")
    if not api_key:
        raise ValueError(
            "COINGECKO_API_KEY environment variable is required. "
            "Get your API key from https://coingecko.com/en/api"
        )
    
    # Prepare API request
    url = "https://pro-api.coingecko.com/api/v3/search"
    headers = {
        "x-cg-pro-api-key": api_key,
        "accept": "application/json"
    }
    params = {
        "query": query.strip()
    }
    
    try:
        # Make single API request (no retry logic)
        response = proxied_get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract coins from search results
        coins = data.get("coins", [])
        
        if not coins:
            return None
        
        # Determine if input is symbol or name based on case and length
        query_stripped = query.strip()
        is_symbol_search = query_stripped.isupper() or len(query_stripped) <= 3
        
        if is_symbol_search:
            # Symbol search: check for exact symbol OR exact name match in order of relevance
            # This ensures "SOLANA" matches the real Solana (name match at index 0)
            # rather than a meme coin with symbol "SOLANA" at index 18
            for coin in coins:
                coin_symbol = coin.get("symbol", "")
                coin_name = coin.get("name", "")
                if coin_symbol.upper() == query_stripped.upper() or coin_name.upper() == query_stripped.upper():
                    return {
                        "symbol": coin.get("symbol", "").upper(),
                        "name": coin.get("name", ""),
                        "id": coin.get("id", "")
                    }

            # No exact symbol or name match, return highest market cap
            best_coin = coins[0]
            return {
                "symbol": best_coin.get("symbol", "").upper(),
                "name": best_coin.get("name", ""),
                "id": best_coin.get("id", "")
            }
        else:
            # Name search: prioritize exact name match, then market cap
            for coin in coins:
                coin_name = coin.get("name", "")
                if coin_name.lower() == query_stripped.lower():
                    return {
                        "symbol": coin.get("symbol", "").upper(),
                        "name": coin.get("name", ""),
                        "id": coin.get("id", "")
                    }
            
            # No exact name match, return highest market cap
            best_coin = coins[0]
            return {
                "symbol": best_coin.get("symbol", "").upper(),
                "name": best_coin.get("name", ""),
                "id": best_coin.get("id", "")
            }
                
    except requests.exceptions.Timeout:
        raise requests.RequestException("Request timeout - CoinGecko API may be slow")
    except requests.exceptions.ConnectionError:
        raise requests.RequestException("Connection error - check internet connection")
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(f"API request failed: {e}")
    
    return None


