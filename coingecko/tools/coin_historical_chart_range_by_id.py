#!/usr/bin/env python3
"""
CoinGecko Coin Historical Chart Data within Time Range Tool

This tool provides access to the CoinGecko Pro API /coins/{id}/market-chart/range endpoint,
which returns historical chart data for a specific coin by its id or symbol within a time range.

API Reference: https://docs.coingecko.com/reference/coins-id-market-chart-range

Usage Example:
    from tools.coin_historical_chart_range_by_id import get_coin_historical_chart_range
    
    # Using symbol
    data = get_coin_historical_chart_range('BTC', vs_currency='usd', from_timestamp=1672531200, to_timestamp=1672617600)
    
    # Using ID
    data = get_coin_historical_chart_range('bitcoin', vs_currency='usd', from_timestamp=1672531200, to_timestamp=1672617600)
    print(data)

Returns:
    dict with keys: 'prices', 'market_caps', 'total_volumes'
"""

import os
from dotenv import load_dotenv
import time
import argparse
import json

from core.http_client import proxied_get
try:
    from .utils import parse_flexible_time, split_time_range, merge_market_chart_data, get_days_difference, search_coin_by_name
except ImportError:
    from utils import parse_flexible_time, split_time_range, merge_market_chart_data, get_days_difference, search_coin_by_name


# MCP Tool Schema
MCP_TOOL_SCHEMA = {
    "name": "get_coin_historical_chart_range_by_id",
    "title": "CoinGecko Historical Chart Range",
    "description": "Retrieve historical chart data (prices, market caps, total volumes) for a specific cryptocurrency within a custom time range. Automatically determines optimal data granularity based on the time range. Will return a lot of data, use with caution.",
    "inputSchema": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "coin_id": {
                "type": "string",
                "minLength": 1,
                "description": "The coin id (e.g., 'bitcoin') or symbol (e.g., 'BTC')"
            },
            "vs_currency": {
                "type": "string",
                "default": "usd",
                "description": "The target currency (e.g., 'usd')"
            },
            "from_timestamp": {
                "type": ["string", "integer", "number"],
                "description": "Start time - supports Unix timestamp (1640995200), ISO date ('2023-01-01' or '2023-01-01 10:30:00'), or natural language ('2 weeks ago', 'last month', 'yesterday')"
            },
            "to_timestamp": {
                "type": ["string", "integer", "number"],
                "description": "End time - same formats as from_timestamp"
            }
        },
        "required": ["coin_id", "from_timestamp", "to_timestamp"],
        "additionalProperties": False
    },
    "outputSchema": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "prices": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": [
                        {"type": "number", "description": "Unix timestamp in milliseconds"},
                        {"type": "number", "description": "Price in the specified vs_currency"}
                    ],
                    "minItems": 2,
                    "maxItems": 2
                },
                "description": "Array of [timestamp_ms, price] pairs showing coin price at each time point"
            },
            "market_caps": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": [
                        {"type": "number", "description": "Unix timestamp in milliseconds"},
                        {"type": "number", "description": "Market capitalization at this timestamp"}
                    ],
                    "minItems": 2,
                    "maxItems": 2
                },
                "description": "Array of [timestamp_ms, market_cap] pairs showing market capitalization"
            },
            "total_volumes": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": [
                        {"type": "number", "description": "Unix timestamp in milliseconds"},
                        {"type": "number", "description": "Total trading volume"}
                    ],
                    "minItems": 2,
                    "maxItems": 2
                },
                "description": "Array of [timestamp_ms, volume] pairs showing trading volume"
            }
        },
        "required": ["prices", "market_caps", "total_volumes"],
        "additionalProperties": False
    },
    "annotations": {
        "path": "tools/coingecko/coin_historical_chart_range_by_id.py",
        "function": "get_coin_historical_chart_range_by_id",
        "examples": [
            {
                "name": "basic_auto_interval",
                "arguments": {
                    "coin_id": "BTC",
                    "from_timestamp": "30 days ago",
                    "to_timestamp": "today"
                }
            },
            {
                "name": "large_range_splitting",
                "arguments": {
                    "coin_id": "BTC",
                    "from_timestamp": "2023-01-01",
                    "to_timestamp": "2023-12-31"
                }
            }
        ]
    }
}



# Load environment variables from project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
load_dotenv(os.path.join(project_root, '.env'))

def get_coin_historical_chart_range_by_id(coin_id, vs_currency='usd', from_timestamp=None, to_timestamp=None):
    """
    Fetch historical chart data for a specific coin by its id or symbol within a time range from CoinGecko.
    Automatically handles data splitting for large time ranges based on interval limits and flexible time input parsing.
    
    Args:
        coin_id (str): The coin id (e.g., 'bitcoin') or symbol (e.g., 'BTC')
        vs_currency (str): The target currency (e.g., 'usd')
        from_timestamp (Union[str, int, float]): Start time - supports:
            - Unix timestamp (1640995200)
            - ISO date ('2023-01-01' or '2023-01-01 10:30:00')
            - Natural language ('2 weeks ago', 'last month', 'yesterday')
        to_timestamp (Union[str, int, float]): End time - same formats as from_timestamp
    
    Returns:
        dict: Historical chart data with keys: 'prices', 'market_caps', 'total_volumes'
              Automatically merges data from multiple API calls if needed for large ranges
    
    Raises:
        ConnectionError: If API request fails after retries
        ValueError: If parameters are invalid or time range exceeds interval limits
        
    Data Limitations (based on official CoinGecko API):
        - Auto granularity: 1 day = 5-min, 1-90 days = hourly, >90 days = daily
        - Cache frequency: 1 day = 30s, 2-90 days = 30min, >90 days = 12h
        
    Examples:
        >>> # Get last 30 days of data
        >>> data = get_coin_historical_chart_range_by_id('BTC', 'usd', '30 days ago', 'today')
        
        >>> # Get data for specific date range
        >>> data = get_coin_historical_chart_range_by_id('ETH', 'usd', '2023-01-01', '2023-03-31')
        
        >>> # Large range with automatic splitting
        >>> data = get_coin_historical_chart_range_by_id('BTC', 'usd', '2023-01-01', '2023-12-31')
    """
    if not coin_id:
        raise ValueError("coin_id parameter is required")
    
    if not from_timestamp or not to_timestamp:
        raise ValueError("Both from_timestamp and to_timestamp are required")
    
    # Convert symbol to ID if needed
    coin_result = search_coin_by_name(coin_id)
    if not coin_result:
        raise ValueError(f"Could not find coin with symbol or name: {coin_id}")
    actual_coin_id = coin_result['id']
    
    # Parse flexible time inputs
    from_ts = parse_flexible_time(from_timestamp)
    to_ts = parse_flexible_time(to_timestamp)
    
    if from_ts >= to_ts:
        raise ValueError("from_timestamp must be earlier than to_timestamp")
    
    # Determine splitting strategy based on time range
    days_diff = get_days_difference(from_ts, to_ts)
    
    # For better granularity, split at 90 days to maintain hourly data when possible
    if days_diff <= 90:
        return _fetch_single_range(actual_coin_id, vs_currency, from_ts, to_ts)
    else:
        return _fetch_with_splitting(actual_coin_id, vs_currency, from_ts, to_ts, max_days=90)


def _fetch_single_range(coin_id, vs_currency, from_timestamp, to_timestamp):
    """Fetch historical chart data for a single time range."""
    url = f"https://pro-api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
    params = {
        'vs_currency': vs_currency,
        'from': from_timestamp,
        'to': to_timestamp
    }
    
    headers = {"x-cg-pro-api-key": os.getenv("COINGECKO_API_KEY")}
    
    if not headers["x-cg-pro-api-key"]:
        raise ValueError("COINGECKO_API_KEY environment variable is required")
    
    for attempt in range(3):
        try:
            resp = proxied_get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 2:  # Last attempt
                raise ConnectionError(f"API request failed after retries: {e}")
            time.sleep(1)


def _fetch_with_splitting(coin_id, vs_currency, from_ts, to_ts, max_days):
    """Fetch historical chart data with automatic splitting for large ranges."""
    time_chunks = split_time_range(from_ts, to_ts, max_days=max_days)
    data_chunks = []
    
    for chunk_start, chunk_end in time_chunks:
        chunk_data = _fetch_single_range(coin_id, vs_currency, chunk_start, chunk_end)
        data_chunks.append(chunk_data)
        # Small delay between requests to be respectful to the API
        time.sleep(0.5)
    
    # Merge all chunks
    return merge_market_chart_data(data_chunks)

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Fetch historical chart data within a time range for a specific coin from CoinGecko API.",
        epilog="""INPUT:
  --coin_id: Coin ID/symbol (bitcoin, BTC, ethereum, ETH)
  --from_timestamp: Start time ("30 days ago", "2023-01-01", timestamp)
  --to_timestamp: End time ("today", "2023-12-31", timestamp)
  --vs_currency: Target currency (default: usd)

OUTPUT:
  JSON array of price and volume data:
  [{"timestamp": 1640995200, "price": 46300.45, "market_cap": 874500000000, 
    "total_volume": 34500000000}]

EXAMPLE:
  python coin_historical_chart_range_by_id.py --coin_id BTC --from_timestamp "30 days ago" --to_timestamp "today"
  python coin_historical_chart_range_by_id.py --coin_id ethereum --from_timestamp "2023-01-01" --to_timestamp "2023-06-30"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # MCP Schema query options
    parser.add_argument('--schema', action='store_true',
                       help='Output complete MCP tool schema (JSON)')
    parser.add_argument('--name', action='store_true',
                       help='Output tool name from schema')
    parser.add_argument('--title', action='store_true',
                       help='Output tool title from schema')
    parser.add_argument('--description', action='store_true',
                       help='Output tool description from schema')
    parser.add_argument('--inputSchema', action='store_true',
                       help='Output input schema')
    parser.add_argument('--outputSchema', action='store_true',
                       help='Output output schema')
    parser.add_argument('--annotations', action='store_true',
                       help='Output annotations from schema')
    
    # Tool functionality options
    parser.add_argument('--coin_id', type=str, help='Coin id (e.g., bitcoin) or symbol (e.g., BTC)')
    parser.add_argument('--vs_currency', type=str, default='usd', help='Target currency (default: usd)')
    parser.add_argument('--from_timestamp', type=str, 
                       help='Start time - supports: Unix timestamp, ISO date (2023-01-01), natural language ("2 weeks ago", "last month")')
    parser.add_argument('--to_timestamp', type=str,
                       help='End time - same formats as from_timestamp')

    args = parser.parse_args()

    # Handle MCP schema queries first
    if args.schema:
        print(json.dumps(MCP_TOOL_SCHEMA, indent=2, sort_keys=True))
        return
    elif args.name:
        print(MCP_TOOL_SCHEMA["name"])
        return
    elif args.title:
        print(MCP_TOOL_SCHEMA["title"])
        return
    elif args.description:
        print(MCP_TOOL_SCHEMA["description"])
        return
    elif args.inputSchema:
        print(json.dumps(MCP_TOOL_SCHEMA["inputSchema"], indent=2, sort_keys=True))
        return
    elif args.outputSchema:
        print(json.dumps(MCP_TOOL_SCHEMA["outputSchema"], indent=2, sort_keys=True))
        return
    elif args.annotations:
        print(json.dumps(MCP_TOOL_SCHEMA["annotations"], indent=2, sort_keys=True))
        return

    # Check required arguments only if not showing example
    if not args.coin_id:
        parser.error("--coin_id is required")
    if not args.from_timestamp:
        parser.error("--from_timestamp is required")
    if not args.to_timestamp:
        parser.error("--to_timestamp is required")

    try:
        # Call the main function to fetch historical chart data using the provided arguments
        data = get_coin_historical_chart_range_by_id(
            coin_id=args.coin_id,
            vs_currency=args.vs_currency,
            from_timestamp=args.from_timestamp,
            to_timestamp=args.to_timestamp
        )
        
        # Print the result as pretty-formatted JSON
        print(json.dumps(data, ensure_ascii=False, indent=2))
            
    except Exception as e:
        # Print error message if the API call fails
        print(f"Failed to fetch historical chart data: {e}")


if __name__ == "__main__":
    main()