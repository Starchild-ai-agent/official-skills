#!/usr/bin/env python3
"""
Coinglass Open Interest Module

Fetch aggregate open interest data across major cryptocurrency exchanges.
Open interest represents the total number of outstanding derivative contracts.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
    load_dotenv(os.path.join(project_root, '.env'))
except ImportError:
    pass

from core.http_client import proxied_get

# Coinglass Configuration
BASE_URL_V2 = "https://open-api.coinglass.com/public/v2"
BASE_URL_V4 = "https://open-api-v4.coinglass.com"
HEADER_KEY_V2 = "coinglassSecret"
HEADER_KEY_V4 = "CG-API-KEY"


# MCP Tool Schema
MCP_OPEN_INTEREST_SCHEMA = {
    "name": "cg_open_interest",
    "title": "Coinglass Open Interest",
    "description": "Get aggregate open interest across exchanges for a symbol.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Symbol (BTC, ETH, SOL, etc.)"
            },
            "interval": {
                "type": "string",
                "description": "Time interval for history: 0 (all time), h1, h4, h12, h24",
                "default": "0",
                "enum": ["0", "h1", "h4", "h12", "h24"]
            }
        },
        "required": ["symbol"],
        "additionalProperties": False
    }
}


def _get_api_key() -> Optional[str]:
    """Get Coinglass API key from environment."""
    return os.getenv("COINGLASS_API_KEY")


def get_open_interest(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get aggregate open interest for a symbol across all exchanges.

    Args:
        symbol: Symbol to query (BTC, ETH, etc.)

    Returns:
        Dictionary with open interest data:
        {
            "symbol": "BTC",
            "total_open_interest_usd": 50000000000,
            "total_open_interest_btc": 500000,
            "exchanges": [
                {
                    "exchange": "Binance",
                    "open_interest_usd": 15000000000,
                    "open_interest_btc": 150000,
                    "change_24h": 2.5
                },
                ...
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found in environment", file=sys.stderr)
        return None

    url = f"{BASE_URL_V2}/open_interest"
    headers = {
        "accept": "application/json",
        HEADER_KEY_V2: api_key
    }
    params = {"symbol": symbol.upper()}

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "0":
            print(f"API Error: {data.get('msg', 'Unknown error')}", file=sys.stderr)
            return None

        raw_data = data.get("data", [])
        if not raw_data:
            return None

        # Aggregate data
        exchanges = []
        total_oi_usd = 0
        total_oi_coin = 0

        for item in raw_data:
            oi_usd = item.get("openInterest", 0)
            oi_coin = item.get("openInterestAmount", 0)
            total_oi_usd += oi_usd
            total_oi_coin += oi_coin

            exchanges.append({
                "exchange": item.get("exchangeName", ""),
                "open_interest_usd": oi_usd,
                "open_interest_coin": oi_coin,
                "change_1h": item.get("h1OIChangePercent"),
                "change_4h": item.get("h4OIChangePercent"),
                "change_24h": item.get("h24OIChangePercent"),
            })

        # Sort by open interest
        exchanges.sort(key=lambda x: x["open_interest_usd"], reverse=True)

        return {
            "symbol": symbol.upper(),
            "total_open_interest_usd": total_oi_usd,
            "total_open_interest_coin": total_oi_coin,
            "num_exchanges": len(exchanges),
            "exchanges": exchanges
        }

    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}", file=sys.stderr)
        return None


def get_open_interest_history(
    symbol: str,
    interval: str = "h24"
) -> Optional[Dict[str, Any]]:
    """
    Get historical open interest data for a symbol.

    Args:
        symbol: Symbol to query (BTC, ETH, etc.)
        interval: Time interval (0=all time, h1, h4, h12, h24)

    Returns:
        Dictionary with historical OI data
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found in environment", file=sys.stderr)
        return None

    # Use V4 API endpoint
    url = f"{BASE_URL_V4}/api/futures/open-interest/aggregated-history"
    headers = {
        "accept": "application/json",
        HEADER_KEY_V4: api_key
    }

    # Convert interval format for V4 API
    # V2 used: 0, h1, h4, h12, h24
    # V4 uses: 1h, 4h, 12h, 1d (need to confirm format)
    interval_map = {
        "0": "all",
        "h1": "1h",
        "h4": "4h",
        "h12": "12h",
        "h24": "1d"
    }
    v4_interval = interval_map.get(interval, interval)

    params = {
        "symbol": symbol.upper(),
        "interval": v4_interval
    }

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "0":
            error_msg = f"OI History API Error [code={data.get('code')}]: {data.get('msg', 'Unknown error')}"
            print(error_msg, file=sys.stderr)
            return None

        raw_data = data.get("data", [])

        # V4 API returns data as array of OHLC candles
        if isinstance(raw_data, list):
            return {
                "symbol": symbol.upper(),
                "interval": interval,
                "data": raw_data,
                "count": len(raw_data)
            }
        else:
            # Fallback for dict format (if API returns differently)
            return {
                "symbol": symbol.upper(),
                "interval": interval,
                "data": raw_data,
                "data_points": raw_data.get("dataMap", {}),
                "price_list": raw_data.get("priceList", []),
                "date_list": raw_data.get("dateList", [])
            }

    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Fetch Coinglass open interest data")
    parser.add_argument("--symbol", "-s", required=True, help="Symbol (BTC, ETH, etc.)")
    parser.add_argument("--history", action="store_true", help="Get historical data")
    parser.add_argument(
            "--interval",
            "-i",
            default="h24",
            choices=["0",
                     "h1",
                     "h4",
                     "h12",
                     "h24"],
            help="History interval"
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--schema", action="store_true", help="Output MCP schema")

    args = parser.parse_args()

    if args.schema:
        print(json.dumps(MCP_OPEN_INTEREST_SCHEMA, indent=2))
        return 0

    try:
        if args.history:
            result = get_open_interest_history(args.symbol, args.interval)
        else:
            result = get_open_interest(args.symbol)

        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\n{result['symbol']} Open Interest")
                print("=" * 50)
                if args.history:
                    print(f"Interval: {result['interval']}")
                    count = result.get('count', len(result.get('date_list', [])))
                    print(f"Data points: {count}")
                else:
                    print(f"Total OI (USD): ${result['total_open_interest_usd']:,.0f}")
                    print(f"Total OI (Coin): {result['total_open_interest_coin']:,.2f}")
                    print("\nTop exchanges:")
                    for ex in result['exchanges'][:5]:
                        oi_usd = ex['open_interest_usd']
                        chg = ex.get('change_24h', 0)
                        print(f"  {ex['exchange']:15s} ${oi_usd:>15,.0f} ({chg:+.2f}% 24h)")
            return 0
        else:
            print(f"No data found for {args.symbol}", file=sys.stderr)
            return 1

    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    exit(main())
