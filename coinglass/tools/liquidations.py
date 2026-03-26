#!/usr/bin/env python3
"""
Coinglass Liquidations Module

Fetch liquidation data across major cryptocurrency exchanges.
Liquidations occur when a trader's position is forcibly closed due to
insufficient margin to maintain the position.
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
BASE_URL = "https://open-api.coinglass.com/public/v2"
BASE_URL_V4 = "https://open-api-v4.coinglass.com/api/futures/liquidation"
HEADER_KEY = "coinglassSecret"
HEADER_KEY_V4 = "CG-API-KEY"


# MCP Tool Schemas
MCP_LIQUIDATIONS_SCHEMA = {
    "name": "cg_liquidations",
    "title": "Coinglass Liquidations",
    "description": "Get recent liquidation data across exchanges.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Symbol (BTC, ETH, SOL, etc.)"
            },
            "time_type": {
                "type": "string",
                "description": "Time window: h1, h4, h12, h24",
                "default": "h24",
                "enum": ["h1", "h4", "h12", "h24"]
            }
        },
        "required": ["symbol"],
        "additionalProperties": False
    }
}

MCP_LIQUIDATION_HISTORY_SCHEMA = {
    "name": "cg_liquidation_history",
    "title": "Coinglass Liquidation History",
    "description": "Get historical liquidation aggregates.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Symbol (BTC, ETH, etc.)"
            },
            "interval": {
                "type": "string",
                "description": "Data interval: h1, h4, h12, h24",
                "default": "h24",
                "enum": ["h1", "h4", "h12", "h24"]
            }
        },
        "required": ["symbol"],
        "additionalProperties": False
    }
}


def _get_api_key() -> Optional[str]:
    """Get Coinglass API key from environment."""
    return os.getenv("COINGLASS_API_KEY")


def get_liquidations(
    symbol: str,
    time_type: str = "h24", max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get recent liquidation data for a symbol.

    Args:
        symbol: Symbol to query (BTC, ETH, etc.)
        time_type: Time window (h1, h4, h12, h24)

    Returns:
        Dictionary with liquidation data:
        {
            "symbol": "BTC",
            "time_window": "h24",
            "total_liquidations_usd": 50000000,
            "long_liquidations_usd": 30000000,
            "short_liquidations_usd": 20000000,
            "long_percent": 60.0,
            "short_percent": 40.0,
            "exchanges": [...]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found in environment", file=sys.stderr)
        return None

    # Map h1/h4/h12/h24 to v4 format: 1h/4h/12h/24h
    range_map = {"h1": "1h", "h4": "4h", "h12": "12h", "h24": "24h"}
    v4_range = range_map.get(time_type, "24h")

    url = f"{BASE_URL_V4}/exchange-list"
    headers = {
        "accept": "application/json",
        HEADER_KEY_V4: api_key
    }
    params = {
        "symbol": symbol.upper(),
        "range": v4_range
    }

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

        # Parse v4 exchange-list response
        agg_long = 0
        agg_short = 0
        sum_long = 0
        sum_short = 0
        exchanges = []

        for item in raw_data:
            exchange_name = item.get("exchange", "")
            long_liq = item.get("long_liquidation_usd", 0) or 0
            short_liq = item.get("short_liquidation_usd", 0) or 0
            total_liq = item.get("liquidation_usd", 0) or 0

            # "All" row contains the API's aggregate
            if exchange_name == "All":
                agg_long = long_liq
                agg_short = short_liq
                continue

            sum_long += long_liq
            sum_short += short_liq
            exchanges.append({
                "exchange": exchange_name,
                "long_liquidations_usd": long_liq,
                "short_liquidations_usd": short_liq,
                "total_liquidations_usd": total_liq,
            })

        # FIX: If "All" row returns zeros but exchanges have data,
        # fall back to self-computed sum (Coinglass aggregation bug)
        if (agg_long + agg_short) == 0 and (sum_long + sum_short) > 0:
            total_long = sum_long
            total_short = sum_short
        else:
            total_long = agg_long
            total_short = agg_short

        total = total_long + total_short
        exchanges.sort(key=lambda x: x["total_liquidations_usd"], reverse=True)

        return {
            "symbol": symbol.upper(),
            "time_window": time_type,
            "total_liquidations_usd": total,
            "long_liquidations_usd": total_long,
            "short_liquidations_usd": total_short,
            "long_percent": (total_long / total * 100) if total > 0 else 0,
            "short_percent": (total_short / total * 100) if total > 0 else 0,
            "num_exchanges": len(exchanges),
            "exchanges": exchanges
        }

    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}", file=sys.stderr)
        return None


def get_liquidation_aggregated(
    symbol: str,
    time_type: str = "h24", max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get aggregated liquidation data including historical context.

    Args:
        symbol: Symbol to query (BTC, ETH, etc.)
        time_type: Time window (h1, h4, h12, h24)

    Returns:
        Dictionary with aggregated liquidation data and context
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found in environment", file=sys.stderr)
        return None

    # Get current liquidations
    current = get_liquidations(symbol, time_type)
    if not current:
        return None

    # Add analysis
    long_pct = current["long_percent"]
    short_pct = current["short_percent"]

    # FIX: Guard against zero-data producing misleading "Balanced" label
    total_liq = current.get("total_liquidations_usd", 0)
    if total_liq == 0:
        sentiment = "No liquidation data available"
        dominant = "none"
    elif long_pct > 70:
        sentiment = "Heavily bearish pressure (longs being liquidated)"
        dominant = "longs"
    elif long_pct > 55:
        sentiment = "Moderately bearish pressure"
        dominant = "longs"
    elif short_pct > 70:
        sentiment = "Heavily bullish pressure (shorts being liquidated)"
        dominant = "shorts"
    elif short_pct > 55:
        sentiment = "Moderately bullish pressure"
        dominant = "shorts"
    else:
        sentiment = "Balanced liquidations"
        dominant = "longs" if long_pct > short_pct else "shorts"

    current["analysis"] = {
        "sentiment": sentiment,
        "dominant_side": dominant,
        "imbalance": abs(long_pct - short_pct)
    }

    return current


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Fetch Coinglass liquidation data")
    parser.add_argument("--symbol", "-s", required=True,
                        help="Symbol (BTC, ETH, etc.)")
    parser.add_argument("--time", "-t", default="h24",
                        choices=["h1", "h4", "h12", "h24"],
                        help="Time window")
    parser.add_argument("--analyze", "-a", action="store_true",
                        help="Include sentiment analysis")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--schema", action="store_true", help="Output MCP schema")

    args = parser.parse_args()

    if args.schema:
        schemas = {
            "liquidations": MCP_LIQUIDATIONS_SCHEMA,
            "liquidation_history": MCP_LIQUIDATION_HISTORY_SCHEMA
        }
        print(json.dumps(schemas, indent=2))
        return 0

    try:
        if args.analyze:
            result = get_liquidation_aggregated(args.symbol, args.time)
        else:
            result = get_liquidations(args.symbol, args.time)

        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\n{result['symbol']} Liquidations ({result['time_window']})")
                print("=" * 50)
                print(f"Total Liquidations: ${result['total_liquidations_usd']:,.0f}")
                long_usd = result['long_liquidations_usd']
                short_usd = result['short_liquidations_usd']
                long_pct = result['long_percent']
                short_pct = result['short_percent']
                print(f"  Long Liquidations:  ${long_usd:,.0f} ({long_pct:.1f}%)")
                print(f"  Short Liquidations: ${short_usd:,.0f} ({short_pct:.1f}%)")

                if args.analyze and result.get("analysis"):
                    print(f"\nAnalysis: {result['analysis']['sentiment']}")

                print("\nTop exchanges:")
                for ex in result['exchanges'][:5]:
                    print(f"  {ex['exchange']:15s} ${ex['total_liquidations_usd']:>12,.0f}")
            return 0
        else:
            print(f"No data found for {args.symbol}", file=sys.stderr)
            return 1

    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    exit(main())
