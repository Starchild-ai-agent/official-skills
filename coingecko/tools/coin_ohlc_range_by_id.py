#!/usr/bin/env python3
"""
CoinGecko Coin OHLC Chart within Time Range Tool - MCP Compliant

API Reference: https://docs.coingecko.com/reference/coins-id-ohlc-range
Returns: Array of [timestamp_ms, open, high, low, close] in USD
"""

import os
from dotenv import load_dotenv
import time
import argparse
import json
import sys
from typing import Union
try:
    from .utils import parse_flexible_time, split_time_range, merge_ohlc_data, get_days_difference, search_coin_by_name
except ImportError:
    from utils import parse_flexible_time, split_time_range, merge_ohlc_data, get_days_difference, search_coin_by_name

from core.http_client import proxied_get

# Load environment variables from project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
load_dotenv(os.path.join(project_root, '.env'))

# MCP Tool Schema
MCP_TOOL_SCHEMA = {
    "name": "get_coin_ohlc_range_by_id",
    "title": "CoinGecko OHLC Range",
    "description": "Retrieve OHLC candlestick data within a custom time range for technical analysis. Supports unlimited time ranges (365+ days) with automatic data splitting for large ranges. Will return a lot of data, use with caution.",
    "inputSchema": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "coin_id": {
                "type": "string",
                "minLength": 1,
                "description": "The coin ID (e.g., 'bitcoin', 'ethereum') or symbol (e.g., 'BTC', 'ETH')"
            },
            "from_timestamp": {
                "type": ["string", "integer", "number"],
                "description": "Start time - supports Unix timestamp, ISO date ('2023-01-01'), or natural language ('2 weeks ago', 'last month')"
            },
            "to_timestamp": {
                "type": ["string", "integer", "number"],
                "description": "End time - same formats as from_timestamp"
            },
            "interval": {
                "type": ["string", "null"],
                "enum": ["daily", "hourly", None],
                "description": "Data interval - 'daily' (max 180 days per request), 'hourly' (max 31 days per request), or null for auto-selection based on time range"
            }
        },
        "required": ["coin_id", "from_timestamp", "to_timestamp"],
        "additionalProperties": False
    },
    "outputSchema": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "array",
        "items": {
            "type": "array",
            "items": [
                {"type": "number", "description": "Unix timestamp in milliseconds"},
                {"type": "number", "description": "Opening price in USD"},
                {"type": "number", "description": "Highest price in USD"},
                {"type": "number", "description": "Lowest price in USD"},
                {"type": "number", "description": "Closing price in USD"}
            ],
            "minItems": 5,
            "maxItems": 5
        },
        "description": "Array of OHLC candlestick data where each item is [timestamp_ms, open, high, low, close] in USD"
    },
    "annotations": {
        "path": "tools/coingecko/coin_ohlc_range_by_id.py",
        "function": "get_coin_ohlc_range_by_id",
        "examples": [
            {
                "name": "basic_daily",
                "arguments": {
                    "coin_id": "bitcoin",
                    "from_timestamp": "2024-01-01",
                    "to_timestamp": "2024-01-07",
                    "interval": "daily"
                }
            },
            {
                "name": "natural_language",
                "arguments": {
                    "coin_id": "ETH",
                    "from_timestamp": "30 days ago",
                    "to_timestamp": "today",
                    "interval": "hourly"
                }
            }
        ]
    }
}

def get_coin_ohlc_range_by_id(coin_id, from_timestamp=None, to_timestamp=None, interval=None, max_results: int = 100):
    """
    Fetch OHLC chart data for a specific coin within a time range from CoinGecko Pro API.
    Handles automatic data splitting for large time ranges. Currency fixed to USD.
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
    
    # Currency is fixed to USD
    vs_currency = 'usd'
    
    # Parse flexible time inputs
    from_ts = parse_flexible_time(from_timestamp)
    to_ts = parse_flexible_time(to_timestamp)
    
    if from_ts >= to_ts:
        raise ValueError("from_timestamp must be earlier than to_timestamp")
    
    # Validate interval parameter
    if interval is not None:
        valid_intervals = ['daily', 'hourly']
        if interval not in valid_intervals:
            raise ValueError(f"interval must be one of {valid_intervals} or None, got: {interval}")
    
    # Determine optimal interval and splitting strategy
    days_diff = get_days_difference(from_ts, to_ts)
    
    # Auto-select interval if not specified
    if interval is None:
        if days_diff <= 31:
            interval = 'hourly'
        else:
            interval = 'daily'
    
    # Validate time range against interval limits
    if interval == 'hourly' and days_diff > 31:
        if days_diff <= 180:
            # Switch to daily for better compatibility
            interval = 'daily'
        else:
            # Split into hourly chunks (31 days each) then merge
            return _fetch_ohlc_with_splitting(actual_coin_id, vs_currency, from_ts, to_ts, 'hourly', 31)
    elif interval == 'daily' and days_diff > 180:
        # Split into daily chunks (180 days each) then merge
        return _fetch_ohlc_with_splitting(actual_coin_id, vs_currency, from_ts, to_ts, 'daily', 180)
    
    # Single request
    return _fetch_single_ohlc_range(actual_coin_id, vs_currency, from_ts, to_ts, interval)


def _fetch_ohlc_with_splitting(coin_id, vs_currency, from_ts, to_ts, interval, max_days, max_results: int = None):
    """Fetch OHLC data with automatic splitting for large ranges."""
    time_chunks = split_time_range(from_ts, to_ts, max_days=max_days)
    data_chunks = []
    
    for chunk_start, chunk_end in time_chunks:
        chunk_data = _fetch_single_ohlc_range(coin_id, vs_currency, chunk_start, chunk_end, interval)
        data_chunks.append(chunk_data)
        # Small delay between requests to be respectful to the API
        time.sleep(0.5)
    
    # Merge all chunks
    return merge_ohlc_data(data_chunks)


def _fetch_single_ohlc_range(coin_id, vs_currency, from_timestamp, to_timestamp, interval, max_results: int = None):
    """Fetch OHLC data for a single time range."""
    url = f"https://pro-api.coingecko.com/api/v3/coins/{coin_id}/ohlc/range"
    params = {
        'vs_currency': vs_currency,
        'from': from_timestamp,
        'to': to_timestamp
    }
    if interval:
        params['interval'] = interval
    
    headers = {"x-cg-pro-api-key": os.getenv("COINGECKO_API_KEY")}
    
    if not headers["x-cg-pro-api-key"]:
        raise ValueError("COINGECKO_API_KEY environment variable is required")
    
    # Retry logic
    for attempt in range(3):
        try:
            resp = proxied_get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 2:  # Last attempt
                raise ConnectionError(f"API request failed after retries: {e}")
            time.sleep(1)


# Backward compatibility
def get_coin_ohlc_range(coin_id, vs_currency='usd', from_timestamp=None, to_timestamp=None, interval=None):
    """Backward compatibility wrapper for get_coin_ohlc_range_by_id. vs_currency is ignored (always USD)."""
    return get_coin_ohlc_range_by_id(coin_id, from_timestamp, to_timestamp, interval)


def main(max_results: int = None):
    """Command-line interface for the coin OHLC range tool."""
    
    # Handle MCP schema queries first (single argument only)
    if len(sys.argv) == 2:
        arg = sys.argv[1]
        
        if arg == "--schema":
            print(json.dumps(MCP_TOOL_SCHEMA, indent=2, sort_keys=True, ensure_ascii=False))
            return 0
        elif arg.startswith("--") and len(arg) > 2:
            field_name = arg[2:]  # Remove "--" prefix
            if field_name in MCP_TOOL_SCHEMA:
                field_value = MCP_TOOL_SCHEMA[field_name]
                print(json.dumps(field_value, indent=2, sort_keys=True, ensure_ascii=False))
                return 0

    parser = argparse.ArgumentParser(
        description="Fetch OHLC chart data within a time range for a specific coin from CoinGecko API.",
        epilog="""INPUT:
  --coin_id: Coin ID/symbol (bitcoin, BTC, ethereum, ETH)
  --from_timestamp: Start time ("30 days ago", "2023-01-01", timestamp)
  --to_timestamp: End time ("today", "2023-12-31", timestamp)  
  --interval: Data interval (daily, hourly, or auto-select)

OUTPUT:
  JSON array of OHLC data points:
  [{"timestamp": 1640995200, "open": 46300.45, "high": 47100.23, 
    "low": 45800.12, "close": 46950.78}]

EXAMPLE:
  python coin_ohlc_range_by_id.py --coin_id BTC --from_timestamp "30 days ago" --to_timestamp "today"
  python coin_ohlc_range_by_id.py --coin_id ethereum --from_timestamp "2023-01-01" --to_timestamp "2023-12-31" --interval daily
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # MCP schema arguments
    parser.add_argument('--schema', action='store_true', help='Output complete MCP Tool Schema (JSON)')
    parser.add_argument('--name', action='store_true', help='Output tool name')
    parser.add_argument('--title', action='store_true', help='Output tool title')
    parser.add_argument('--description', action='store_true', help='Output tool description')
    parser.add_argument('--inputSchema', action='store_true', help='Output input schema')
    parser.add_argument('--outputSchema', action='store_true', help='Output output schema')
    parser.add_argument('--annotations', action='store_true', help='Output annotations')
    
    # Original functionality arguments
    parser.add_argument('--coin_id', help='Coin id (e.g., bitcoin) or symbol (e.g., BTC)')
    parser.add_argument('--from_timestamp', type=str,
                       help='Start time - supports: Unix timestamp, ISO date (2023-01-01), natural language ("2 weeks ago", "last month")')
    parser.add_argument('--to_timestamp', type=str,
                       help='End time - same formats as from_timestamp')
    parser.add_argument('--interval', type=str, choices=['daily', 'hourly'], 
                       help='Data interval - "daily" (max 180 days) or "hourly" (max 31 days). Auto-selected if not specified')

    args = parser.parse_args()
    
    # Handle MCP schema queries
    if args.schema:
        print(json.dumps(MCP_TOOL_SCHEMA, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    elif args.name:
        print(json.dumps(MCP_TOOL_SCHEMA["name"], ensure_ascii=False))
        return 0
    elif args.title:
        print(json.dumps(MCP_TOOL_SCHEMA["title"], ensure_ascii=False))
        return 0
    elif args.description:
        print(json.dumps(MCP_TOOL_SCHEMA["description"], ensure_ascii=False))
        return 0
    elif args.inputSchema:
        print(json.dumps(MCP_TOOL_SCHEMA["inputSchema"], indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    elif args.outputSchema:
        print(json.dumps(MCP_TOOL_SCHEMA["outputSchema"], indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    elif args.annotations:
        print(json.dumps(MCP_TOOL_SCHEMA["annotations"], indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    
    # Validate required arguments for normal operation
    if not args.coin_id:
        parser.error("--coin_id is required")
    if not args.from_timestamp:
        parser.error("--from_timestamp is required")
    if not args.to_timestamp:
        parser.error("--to_timestamp is required")

    try:
        data = get_coin_ohlc_range_by_id(
            coin_id=args.coin_id,
            from_timestamp=args.from_timestamp,
            to_timestamp=args.to_timestamp,
            interval=args.interval
        )
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Failed to fetch OHLC range data: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main()) 