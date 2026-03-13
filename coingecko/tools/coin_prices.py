#!/usr/bin/env python3
"""
CoinGecko Coin Prices at Multiple Timestamps Tool

This tool provides functionality to fetch coin prices at multiple specific timestamps
using the CoinGecko Pro API. It supports flexible time input formats including "now"
for current prices and various date formats for historical prices.

MCP Tool Schema compliant with CLI interface supporting:
- --help: Output complete Schema (JSON, pretty-printed)
- --<field>: Output specific Schema field

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGECKO_API_KEY: Your CoinGecko Pro API key (required for API access)

API Limitations:
- Rate limits apply based on your CoinGecko Pro subscription
- Historical data available from February 9, 2018 onwards
- Current price endpoint updates every 20 seconds for Pro API tiers
"""

import os
from dotenv import load_dotenv
import time
import argparse
import json
from typing import List, Dict, Any, Union
from datetime import datetime

try:
    from .utils import parse_flexible_time, format_dd_mm_yyyy_date, search_coin_by_name
except ImportError:
    from utils import parse_flexible_time, format_dd_mm_yyyy_date, search_coin_by_name

from core.http_client import proxied_get

# Load environment variables from agent_framework root directory
# Path: extensions/trading/tools/coingecko/ -> go up 4 levels to agent_framework/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
load_dotenv(os.path.join(project_root, '.env'))

# MCP Tool Schema
MCP_TOOL_SCHEMA = {
    "name": "get_coin_prices_at_timestamps",
    "title": "CoinGecko Coin Prices at Multiple Timestamps",
    "description": "Fetch cryptocurrency prices at multiple specific timestamps using CoinGecko Pro API. Supports flexible time input formats including 'now' for current prices and various date formats for historical prices.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "coin_ids": {
                "type": ["string", "array"],
                "items": {
                    "type": "string"
                },
                "description": "Single coin ID/symbol or list of coin IDs/symbols. Supports comma-separated strings, individual strings, or arrays. Accepts both full names ('bitcoin') and symbols ('BTC'). Case-insensitive.",
                "examples": ["bitcoin", "BTC", "BTC,ETH,SOL", ["bitcoin", "ethereum", "solana"]]
            },
            "timestamps": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of timestamp strings in various formats. Supports 'now' for current price, Unix timestamps, ISO dates, and natural language expressions.",
                "default": ["now"],
                "examples": [["now"], ["now", "2023-01-01", "yesterday"], ["now", "1640995200", "last month"]]
            },
            "vs_currency": {
                "type": "string",
                "description": "The target currency for price quotes",
                "default": "usd",
                "examples": ["usd", "eur", "btc"]
            },
            "rate_limit_delay": {
                "type": "number",
                "description": "Delay between API calls in seconds to respect rate limits",
                "default": 1.0,
                "minimum": 0.1,
                "maximum": 10.0
            }
        },
        "required": ["coin_ids"],
        "additionalProperties": False
    },
    "outputSchema": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "string",
                    "description": "Original timestamp input"
                },
                "parsed_timestamp": {
                    "type": ["integer", "null"],
                    "description": "Unix timestamp (for historical data) or null for errors"
                },
                "date": {
                    "type": "string",
                    "description": "Human readable date"
                },
                "price": {
                    "type": ["number", "null"],
                    "description": "Price in specified currency or null for errors"
                },
                "coin_id": {
                    "type": "string",
                    "description": "CoinGecko coin ID used for API call"
                },
                "coin_symbol": {
                    "type": "string",
                    "description": "Coin symbol (e.g., 'BTC')"
                },
                "coin_name": {
                    "type": "string",
                    "description": "Coin name (e.g., 'Bitcoin')"
                },
                "status": {
                    "type": "string",
                    "enum": ["success", "error"],
                    "description": "Status of the price fetch operation"
                },
                "error": {
                    "type": ["string", "null"],
                    "description": "Error message if status is 'error', otherwise null"
                }
            },
            "required": ["timestamp", "parsed_timestamp", "date", "price", "coin_id", "coin_symbol", "coin_name", "status", "error"]
        }
    },
    "annotations": {
        "path": "tools/coingecko/coin_prices.py",
        "function":  "get_coin_prices_at_timestamps",
        "examples": [
            {
                "name": "Single coin current price",
                "input": {
                    "coin_ids": "bitcoin"
                },
                "output": [
                    {
                        "timestamp": "now",
                        "parsed_timestamp": 1672531200,
                        "date": "2023-01-01 00:00:00 UTC",
                        "price": 16547.32,
                        "coin_id": "bitcoin",
                        "coin_symbol": "BTC",
                        "coin_name": "Bitcoin",
                        "status": "success",
                        "error": None
                    }
                ]
            },
            {
                "name": "Multiple coins with timestamps",
                "input": {
                    "coin_ids": "BTC,ETH,SOL",
                    "timestamps": ["now", "yesterday"]
                },
                "output": [
                    {
                        "timestamp": "now",
                        "parsed_timestamp": 1672531200,
                        "date": "2023-01-01 00:00:00 UTC",
                        "price": 16547.32,
                        "coin_id": "bitcoin",
                        "coin_symbol": "BTC",
                        "coin_name": "Bitcoin",
                        "status": "success",
                        "error": None
                    },
                    {
                        "timestamp": "yesterday",
                        "parsed_timestamp": 1672444800,
                        "date": "2022-12-31 00:00:00 UTC",
                        "price": 16625.11,
                        "coin_id": "bitcoin",
                        "coin_symbol": "BTC",
                        "coin_name": "Bitcoin",
                        "status": "success",
                        "error": None
                    }
                ]
            }
        ],
        "env_vars": {
            "COINGECKO_API_KEY": {
                "description": "CoinGecko Pro API key for authentication",
                "required": True,
                "url": "https://coingecko.com/en/api"
            }
        },
        "data_availability": {
            "current": "Real-time updates every 20 seconds",
            "historical": "Available from February 9, 2018 onwards"
        }
    }
}


def get_coin_prices_at_timestamps(coin_ids: Union[str, List[str]], 
                                timestamps: List[str] = None, 
                                vs_currency: str = 'usd',
                                rate_limit_delay: float = 1.0) -> List[Dict[str, Any]]:
    """
    Get multiple coin prices at multiple specific timestamps.
    
    This function fetches prices for one or more coins at multiple timestamps using CoinGecko API.
    It automatically handles different time input formats and uses appropriate 
    API endpoints for current vs historical prices with rate limiting protection.
    
    Args:
        coin_ids (Union[str, List[str]]): Single coin ID/symbol or list of coin IDs/symbols
            - String: "bitcoin" or "BTC" for single coin
            - String with comma-separation: "BTC,ETH,SOL" for multiple coins
            - List: ["bitcoin", "ethereum", "solana"] for multiple coins
        timestamps (List[str], optional): List of timestamp strings in various formats (default: ["now"]):
            - "now": Current price
            - Unix timestamp (1640995200)
            - ISO date ('2023-01-01' or '2023-01-01 10:30:00')
            - Natural language ('2 weeks ago', 'last month', 'yesterday')
        vs_currency (str): The target currency (default: 'usd')
        rate_limit_delay (float): Delay between API calls in seconds (default: 1.0)
    
    Returns:
        List[Dict[str, Any]]: List of price data dictionaries with:
            - timestamp: Original timestamp input
            - parsed_timestamp: Unix timestamp (for historical data)
            - date: Human readable date
            - price: Price in specified currency
            - coin_id: CoinGecko coin ID used for API call
            - coin_symbol: Coin symbol (e.g., 'BTC')
            - coin_name: Coin name (e.g., 'Bitcoin')
            - status: 'success' or 'error'
            - error: Error message (if status is 'error')
    
    Raises:
        ValueError: If coin_ids is invalid
        ConnectionError: If API requests fail after retries
        
    Example Usage:
        # Single coin with multiple timestamps
        timestamps = ["now", "2023-01-01", "30 days ago"]
        prices = get_coin_prices_at_timestamps("BTC", timestamps)
        
        # Multiple coins with single timestamp
        prices = get_coin_prices_at_timestamps(["BTC", "ETH", "SOL"], ["now"])
        
        # Multiple coins with multiple timestamps (comma-separated string)
        prices = get_coin_prices_at_timestamps("BTC,ETH,SOL", ["now", "yesterday"])
        
        for price_data in prices:
            print(f"{price_data['coin_symbol']} on {price_data['date']}: ${price_data['price']}")
    """
    if not coin_ids:
        raise ValueError("coin_ids parameter is required")
    
    # Default to current price if no timestamps provided
    if timestamps is None:
        timestamps = ["now"]
    elif not isinstance(timestamps, list):
        raise ValueError("timestamps must be a list")
    
    # Parse coin_ids input - handle string, comma-separated string, or list
    if isinstance(coin_ids, str):
        # Check if it's comma-separated
        if ',' in coin_ids:
            coin_list = [coin.strip() for coin in coin_ids.split(',') if coin.strip()]
        else:
            coin_list = [coin_ids.strip()]
    elif isinstance(coin_ids, list):
        coin_list = [str(coin).strip() for coin in coin_ids if str(coin).strip()]
    else:
        raise ValueError("coin_ids must be a string or list of strings")
    
    if not coin_list:
        raise ValueError("No valid coin IDs provided")
    
    # Resolve all coin IDs
    resolved_coins = []
    for coin_input in coin_list:
        coin_result = search_coin_by_name(coin_input)
        if not coin_result:
            raise ValueError(f"Could not find coin with symbol or name: {coin_input}")
        resolved_coins.append(coin_result)
    
    results = []
    total_api_calls = len(resolved_coins) * len(timestamps)
    call_count = 0
    
    # Get prices for each coin at each timestamp
    for coin_data in resolved_coins:
        actual_coin_id = coin_data['id']
        coin_symbol = coin_data['symbol']
        coin_name = coin_data['name']
        
        for timestamp in timestamps:
            try:
                result = _get_single_price(actual_coin_id, timestamp, vs_currency)
                result['coin_id'] = actual_coin_id
                result['coin_symbol'] = coin_symbol
                result['coin_name'] = coin_name
                results.append(result)
                
                call_count += 1
                # Add rate limiting delay between API calls (except after the last call)
                if call_count < total_api_calls:
                    time.sleep(rate_limit_delay)
                    
            except Exception as e:
                error_result = {
                    'timestamp': timestamp,
                    'parsed_timestamp': None,
                    'date': str(timestamp),
                    'price': None,
                    'coin_id': actual_coin_id,
                    'coin_symbol': coin_symbol,
                    'coin_name': coin_name,
                    'status': 'error',
                    'error': str(e)
                }
                results.append(error_result)
                continue
    
    return results


def _get_single_price(coin_id: str, timestamp: str, vs_currency: str) -> Dict[str, Any]:
    """Get price for a single timestamp."""
    timestamp_str = str(timestamp).strip().lower()
    
    # Handle "now" case - get current price
    if timestamp_str == "now":
        return _get_current_price(coin_id, vs_currency, timestamp)
    
    # Parse timestamp and get historical price
    try:
        parsed_ts = parse_flexible_time(timestamp)
        return _get_historical_price(coin_id, parsed_ts, vs_currency, timestamp)
    except Exception as e:
        raise ValueError(f"Invalid timestamp format '{timestamp}': {e}")


def _get_current_price(coin_id: str, vs_currency: str, original_timestamp: str) -> Dict[str, Any]:
    """Get current price using simple/price endpoint."""
    url = "https://pro-api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': coin_id,
        'vs_currencies': vs_currency,
        'include_last_updated_at': 'true'
    }
    
    headers = {"x-cg-pro-api-key": os.getenv("COINGECKO_API_KEY")}
    
    if not headers["x-cg-pro-api-key"]:
        raise ValueError("COINGECKO_API_KEY environment variable is required")
    
    # Retry logic
    for attempt in range(3):
        try:
            resp = proxied_get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if coin_id not in data:
                raise ValueError(f"Coin '{coin_id}' not found")
            
            coin_data = data[coin_id]
            price = coin_data.get(vs_currency)
            last_updated = coin_data.get('last_updated_at')
            
            if price is None:
                raise ValueError(f"Price not available for currency '{vs_currency}'")
            
            return {
                'timestamp': original_timestamp,
                'parsed_timestamp': last_updated,
                'date': datetime.utcfromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S UTC') if last_updated else 'now',
                'price': price,
                'status': 'success',
                'error': None
            }
            
        except Exception as e:
            if attempt == 2:  # Last attempt
                raise ConnectionError(f"Failed to fetch current price: {e}")
            time.sleep(1)


def _get_historical_price(coin_id: str, timestamp: int, vs_currency: str, original_timestamp: str) -> Dict[str, Any]:
    """Get historical price using history endpoint."""
    # Format date for CoinGecko API (dd-mm-yyyy)
    date_str = format_dd_mm_yyyy_date(timestamp)
    
    url = f"https://pro-api.coingecko.com/api/v3/coins/{coin_id}/history"
    params = {
        'date': date_str,
        'localization': 'false'
    }
    
    headers = {"x-cg-pro-api-key": os.getenv("COINGECKO_API_KEY")}
    
    if not headers["x-cg-pro-api-key"]:
        raise ValueError("COINGECKO_API_KEY environment variable is required")
    
    # Retry logic
    for attempt in range(3):
        try:
            resp = proxied_get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            # Extract price from market_data
            if 'market_data' not in data or 'current_price' not in data['market_data']:
                raise ValueError(f"Price data not available for date {date_str}")
            
            price_data = data['market_data']['current_price']
            price = price_data.get(vs_currency)
            
            if price is None:
                raise ValueError(f"Price not available for currency '{vs_currency}' on date {date_str}")
            
            return {
                'timestamp': original_timestamp,
                'parsed_timestamp': timestamp,
                'date': datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'price': price,
                'status': 'success',
                'error': None
            }
            
        except Exception as e:
            if attempt == 2:  # Last attempt
                raise ConnectionError(f"Failed to fetch historical price for {date_str}: {e}")
            time.sleep(1)


def main():
    """Command-line interface for the coin prices at timestamps tool with MCP Schema support."""
    
    import sys
    
    # Handle MCP Schema CLI arguments (only if they don't contain coin_ids or timestamps)
    if len(sys.argv) > 1 and not any("coin_ids" in arg or "timestamps" in arg for arg in sys.argv[1:]):
        arg = sys.argv[1]
        
        # Handle --help (complete schema) - only if no other arguments
        if arg == "--schema" and len(sys.argv) == 2:
            print(json.dumps(MCP_TOOL_SCHEMA, indent=2, sort_keys=True, ensure_ascii=False))
            return 0
        
        # Handle specific field requests (e.g., --name, --description, --inputSchema)
        if arg.startswith("--") and len(arg) > 2 and len(sys.argv) == 2:
            field_name = arg[2:]  # Remove "--" prefix
            if field_name in MCP_TOOL_SCHEMA:
                field_value = MCP_TOOL_SCHEMA[field_name]
                print(json.dumps(field_value, indent=2, sort_keys=True, ensure_ascii=False))
                return 0

    # Original CLI functionality
    parser = argparse.ArgumentParser(
        description="Get coin prices at multiple specific timestamps from CoinGecko API.",
        epilog="""INPUT:
  --coin_ids: Coin symbols/names (BTC, bitcoin, "BTC,ETH,SOL")
  --timestamps: Time points ("now,yesterday,2023-01-01,last month")

OUTPUT:
  JSON array with price data for each coin-timestamp combination:
  [{"timestamp": "now", "price": 16547.32, "coin_symbol": "BTC", 
    "coin_name": "Bitcoin", "date": "2023-01-01 00:00:00 UTC", "status": "success"}]

EXAMPLE:
  python coin_prices.py --coin_ids BTC --timestamps "now,yesterday"
  python coin_prices.py --coin_ids "BTC,ETH" --timestamps "now"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--coin_ids', required=True, 
                       help='Coin id(s), symbol(s), or comma-separated list (e.g., "bitcoin", "BTC", "BTC,ETH,SOL")')
    parser.add_argument('--timestamps', 
                       help='Comma-separated list of timestamps (e.g., "now,2023-01-01,yesterday"). Default: "now"')

    args = parser.parse_args()

    try:
        # Parse comma-separated timestamps or use default
        if args.timestamps:
            timestamps = [ts.strip() for ts in args.timestamps.split(',') if ts.strip()]
            if not timestamps:
                raise ValueError("No valid timestamps provided")
        else:
            timestamps = None  # Will default to ["now"] in function

        # Call main function with fixed parameters
        results = get_coin_prices_at_timestamps(
            coin_ids=args.coin_ids,
            timestamps=timestamps,
            vs_currency='usd',
            rate_limit_delay=1.0
        )
        
        # Output in JSON format only
        print(json.dumps(results, ensure_ascii=False, indent=2))
            
    except Exception as e:
        error_result = {
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "status": "failed"
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main())