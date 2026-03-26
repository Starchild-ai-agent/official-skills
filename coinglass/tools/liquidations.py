#!/usr/bin/env python3
"""
Coinglass Liquidations Module

Fetch liquidation data across major cryptocurrency exchanges.
Liquidations occur when a trader's position is forcibly closed due to
insufficient margin to maintain the position.

CHANGELOG:
- 2026-03-26: Replaced /exchange-list endpoint (broken long/short=0) with
  /coin-list endpoint which returns correct long/short breakdowns.
  See: docs/coinglass-liquidation-endpoint-migration.md
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../../..'))
    load_dotenv(os.path.join(project_root, '.env'))
except ImportError:
    pass

from core.http_client import proxied_get

# Coinglass API V4 Configuration
BASE_URL_V4 = "https://open-api-v4.coinglass.com"
HEADER_KEY_V4 = "CG-API-KEY"

# Exchanges to aggregate when no specific exchange requested
DEFAULT_EXCHANGES = [
    "Binance", "OKX", "Bybit", "Bitget", "Gate", "CoinEx",
    "Huobi", "Deribit", "BingX", "Hyperliquid"
]

# Time window field suffixes in coin-list response
TIME_SUFFIXES = {
    "h1": "_1h", "h4": "_4h", "h12": "_12h", "h24": "_24h"
}

# MCP Tool Schemas
MCP_LIQUIDATIONS_SCHEMA = {
    "name": "cg_liquidations",
    "title": "Coinglass Liquidations",
    "description": (
        "Get recent liquidation data across exchanges. "
        "Uses coin-list endpoint for accurate long/short breakdowns."
    ),
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
            },
            "exchange": {
                "type": "string",
                "description": (
                    "Specific exchange (Binance, OKX, Bybit, etc.). "
                    "Omit to aggregate across all major exchanges."
                )
            }
        },
        "required": ["symbol"],
        "additionalProperties": False
    }
}

MCP_LIQUIDATION_ANALYSIS_SCHEMA = {
    "name": "cg_liquidation_analysis",
    "title": "Coinglass Liquidation Analysis",
    "description": "Get liquidation data with market sentiment analysis.",
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


def _get_api_key() -> Optional[str]:
    """Get Coinglass API key from environment."""
    return os.getenv("COINGLASS_API_KEY")


def _fetch_coin_list(exchange: str) -> Optional[list]:
    """
    Fetch coin-list data from a single exchange.

    Uses /api/futures/liquidation/coin-list which returns correct
    long/short breakdowns per symbol across all timeframes.
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    url = f"{BASE_URL_V4}/api/futures/liquidation/coin-list"
    headers = {"accept": "application/json", HEADER_KEY_V4: api_key}
    params = {"exchange": exchange}

    try:
        response = proxied_get(
            url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != "0":
            return None
        return data.get("data", [])
    except Exception as e:
        print(f"Request failed for {exchange}: {e}", file=sys.stderr)
        return None


def get_liquidations(
    symbol: str,
    time_type: str = "h24",
    exchange: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get recent liquidation data for a symbol.

    Uses the /coin-list endpoint which provides correct long/short
    breakdowns. If no exchange is specified, aggregates across all
    major exchanges.

    Args:
        symbol: Symbol to query (BTC, ETH, etc.)
        time_type: Time window (h1, h4, h12, h24)
        exchange: Specific exchange, or None for aggregated data

    Returns:
        Dictionary with liquidation data including long/short breakdown
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    suffix = TIME_SUFFIXES.get(time_type, "_24h")
    sym = symbol.upper()

    exchanges_to_query = [exchange] if exchange else DEFAULT_EXCHANGES

    total_long = 0.0
    total_short = 0.0
    total_liq = 0.0
    exchange_details = []

    for exch in exchanges_to_query:
        coins = _fetch_coin_list(exch)
        if not coins:
            continue

        # Find the target symbol in this exchange's data
        for coin in coins:
            if coin.get("symbol", "").upper() == sym:
                long_val = coin.get(
                    f"long_liquidation_usd{suffix}", 0) or 0
                short_val = coin.get(
                    f"short_liquidation_usd{suffix}", 0) or 0
                liq_val = coin.get(
                    f"liquidation_usd{suffix}", 0) or 0

                total_long += long_val
                total_short += short_val
                total_liq += liq_val

                exchange_details.append({
                    "exchange": exch,
                    "long_liquidations_usd": round(long_val, 2),
                    "short_liquidations_usd": round(short_val, 2),
                    "total_liquidations_usd": round(liq_val, 2),
                })
                break

    # Prefer summed long+short; fall back to total if both are zero
    computed_total = total_long + total_short
    if computed_total > 0:
        final_total = computed_total
    else:
        final_total = total_liq

    exchange_details.sort(
        key=lambda x: x["total_liquidations_usd"], reverse=True)

    return {
        "symbol": sym,
        "time_window": time_type,
        "total_liquidations_usd": round(final_total, 2),
        "long_liquidations_usd": round(total_long, 2),
        "short_liquidations_usd": round(total_short, 2),
        "long_percent": round(
            (total_long / final_total * 100) if final_total > 0 else 0, 1),
        "short_percent": round(
            (total_short / final_total * 100) if final_total > 0 else 0, 1),
        "num_exchanges": len(exchange_details),
        "exchanges": exchange_details,
    }


def get_liquidation_aggregated(
    symbol: str,
    time_type: str = "h24"
) -> Optional[Dict[str, Any]]:
    """
    Get aggregated liquidation data with sentiment analysis.

    Args:
        symbol: Symbol to query (BTC, ETH, etc.)
        time_type: Time window (h1, h4, h12, h24)

    Returns:
        Dictionary with liquidation data plus analysis section
    """
    current = get_liquidations(symbol, time_type)
    if not current:
        return None

    long_pct = current["long_percent"]
    short_pct = current["short_percent"]
    total_liq = current["total_liquidations_usd"]

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
        "imbalance": round(abs(long_pct - short_pct), 1),
    }

    return current


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch Coinglass liquidation data")
    parser.add_argument(
        "--symbol", "-s", required=True, help="Symbol (BTC, ETH, etc.)")
    parser.add_argument(
        "--time", "-t", default="h24",
        choices=["h1", "h4", "h12", "h24"], help="Time window")
    parser.add_argument(
        "--exchange", "-e", default=None,
        help="Specific exchange (omit for aggregated)")
    parser.add_argument(
        "--analyze", "-a", action="store_true",
        help="Include sentiment analysis")
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--schema", action="store_true", help="Output MCP schema")

    args = parser.parse_args()

    if args.schema:
        schemas = {
            "liquidations": MCP_LIQUIDATIONS_SCHEMA,
            "liquidation_analysis": MCP_LIQUIDATION_ANALYSIS_SCHEMA,
        }
        print(json.dumps(schemas, indent=2))
        return 0

    try:
        if args.analyze:
            result = get_liquidation_aggregated(args.symbol, args.time)
        else:
            result = get_liquidations(
                args.symbol, args.time, args.exchange)

        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(
                    f"\n{result['symbol']} Liquidations "
                    f"({result['time_window']})")
                print("=" * 50)
                total = result['total_liquidations_usd']
                long_usd = result['long_liquidations_usd']
                short_usd = result['short_liquidations_usd']
                long_pct = result['long_percent']
                short_pct = result['short_percent']
                print(f"Total Liquidations: ${total:,.0f}")
                print(
                    f"  Long Liquidations:  "
                    f"${long_usd:,.0f} ({long_pct:.1f}%)")
                print(
                    f"  Short Liquidations: "
                    f"${short_usd:,.0f} ({short_pct:.1f}%)")

                if args.analyze and result.get("analysis"):
                    print(
                        f"\nAnalysis: "
                        f"{result['analysis']['sentiment']}")

                print("\nTop exchanges:")
                for ex in result['exchanges'][:5]:
                    name = ex['exchange']
                    val = ex['total_liquidations_usd']
                    print(f"  {name:15s} ${val:>12,.0f}")
            return 0
        else:
            print(f"No data found for {args.symbol}", file=sys.stderr)
            return 1

    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    exit(main())
