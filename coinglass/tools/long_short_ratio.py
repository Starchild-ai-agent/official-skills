#!/usr/bin/env python3
"""
Coinglass Long/Short Ratio Module

Fetch long/short account ratios across major cryptocurrency exchanges including
Binance, OKX, Bybit, KuCoin, Gate, and more.

The long/short ratio indicates the proportion of traders with long positions
versus short positions. A ratio > 50% long suggests bullish sentiment, while
< 50% suggests bearish sentiment.

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key

Usage Example:
    from tools.coinglass.long_short_ratio import get_long_short_ratio, get_exchange_ratio

    # Get long/short ratio for BTC (1h timeframe)
    ratio = get_long_short_ratio(symbol="BTC", time_type="h1")

    # Get ratio for specific exchange
    binance = get_exchange_ratio(symbol="BTC", exchange="Binance", time_type="h1")

CLI Usage:
    python long_short_ratio.py --symbol BTC
    python long_short_ratio.py --symbol ETH --exchange Binance
    python long_short_ratio.py --symbol BTC --time-type h4
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional, List

try:
    from dotenv import load_dotenv
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
    load_dotenv(os.path.join(project_root, '.env'))
except ImportError:
    pass

import requests
from core.http_client import proxied_get

# Coinglass Configuration
BASE_URL = "https://open-api.coinglass.com/public/v2"
HEADER_KEY = "coinglassSecret"

# Supported exchanges
EXCHANGES = [
    "Binance", "OKX", "Bybit", "KuCoin", "Gate", "Bitget", "dYdX"
]

# Supported time types
TIME_TYPES = ["m5", "m15", "m30", "h1", "h4", "h12", "h24"]

# Common symbols
SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "MATIC"]


def _get_api_key() -> Optional[str]:
    """Get Coinglass API key from environment."""
    return os.getenv("COINGLASS_API_KEY")


def get_long_short_ratio(
    symbol: str,
    time_type: str = "h1"
) -> Optional[Dict[str, Any]]:
    """
    Fetch long/short account ratio for a symbol across all exchanges.

    Args:
        symbol: Symbol to query (BTC, ETH, etc.)
        time_type: Time interval (m5, m15, m30, h1, h4, h12, h24)

    Returns:
        Dictionary with long/short ratio data:
        {
            "symbol": "BTC",
            "longRate": 49.75,  # Percentage of longs
            "shortRate": 50.25,  # Percentage of shorts
            "longVolUsd": 3273317562.23,  # Long volume in USD
            "shortVolUsd": 3306465205.80,  # Short volume in USD
            "totalVolUsd": 6579782768.04,
            "exchanges": [
                {
                    "exchangeName": "Binance",
                    "longRate": 50.06,
                    "shortRate": 49.94,
                    "turnoverNumber": 543983,
                    ...
                },
                ...
            ]
        }
        Returns None if request fails.

    Example:
        ratio = get_long_short_ratio("BTC", "h1")
        print(f"BTC Long: {ratio['longRate']:.2f}% | Short: {ratio['shortRate']:.2f}%")
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found in environment", file=sys.stderr)
        return None

    url = f"{BASE_URL}/long_short"
    headers = {
        "accept": "application/json",
        HEADER_KEY: api_key
    }
    params = {
        "symbol": symbol.upper(),
        "time_type": time_type
    }

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "0":
            print(f"API Error: {data.get('msg', 'Unknown error')}", file=sys.stderr)
            return None

        # Parse and restructure the response
        result_data = data.get("data", [])
        if not result_data:
            return None

        # The API returns a list, we want the first (and usually only) item
        symbol_data = result_data[0] if isinstance(result_data, list) else result_data

        return {
            "symbol": symbol_data.get("symbol", symbol.upper()),
            "longRate": symbol_data.get("longRate", 0),
            "shortRate": symbol_data.get("shortRate", 0),
            "longVolUsd": symbol_data.get("longVolUsd", 0),
            "shortVolUsd": symbol_data.get("shortVolUsd", 0),
            "totalVolUsd": symbol_data.get("totalVolUsd", 0),
            "time_type": time_type,
            "exchanges": symbol_data.get("list", [])
        }

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}", file=sys.stderr)
        return None


def get_exchange_ratio(
    symbol: str,
    exchange: str,
    time_type: str = "h1"
) -> Optional[Dict[str, Any]]:
    """
    Get long/short ratio for a specific exchange.

    Args:
        symbol: Symbol to query (BTC, ETH, etc.)
        exchange: Exchange name (Binance, OKX, Bybit, etc.)
        time_type: Time interval (m5, m15, m30, h1, h4, h12, h24)

    Returns:
        Dictionary with exchange-specific ratio:
        {
            "symbol": "BTC",
            "exchange": "Binance",
            "longRate": 50.06,
            "shortRate": 49.94,
            "longVolUsd": 792481834.58,
            "shortVolUsd": 790530803.79,
            "totalVolUsd": 1583012638.21,
            "turnoverNumber": 543983,
            "buyTurnoverNumber": 267594,
            "sellTurnoverNumber": 276389
        }
        Returns None if not found.

    Example:
        ratio = get_exchange_ratio("BTC", "Binance")
        if ratio:
            print(f"Binance BTC - Long: {ratio['longRate']:.2f}%")
    """
    data = get_long_short_ratio(symbol, time_type)
    if not data:
        return None

    for ex_data in data.get("exchanges", []):
        if ex_data.get("exchangeName", "").lower() == exchange.lower():
            return {
                "symbol": data["symbol"],
                "exchange": ex_data.get("exchangeName"),
                "longRate": ex_data.get("longRate", 0),
                "shortRate": ex_data.get("shortRate", 0),
                "longVolUsd": ex_data.get("longVolUsd", 0),
                "shortVolUsd": ex_data.get("shortVolUsd", 0),
                "totalVolUsd": ex_data.get("totalVolUsd", 0),
                "turnoverNumber": ex_data.get("turnoverNumber", 0),
                "buyTurnoverNumber": ex_data.get("buyTurnoverNumber", 0),
                "sellTurnoverNumber": ex_data.get("sellTurnoverNumber", 0),
                "time_type": time_type
            }

    return None


def get_sentiment(symbol: str, time_type: str = "h1") -> Optional[Dict[str, Any]]:
    """
    Analyze market sentiment based on long/short ratio.

    Args:
        symbol: Symbol to analyze (BTC, ETH, etc.)
        time_type: Time interval (m5, m15, m30, h1, h4, h12, h24)

    Returns:
        Dictionary with sentiment analysis:
        {
            "symbol": "BTC",
            "sentiment": "neutral" | "bullish" | "bearish" | "extremely_bullish" | "extremely_bearish",
            "longRate": 49.75,
            "shortRate": 50.25,
            "bias": -0.5,  # Positive = bullish, negative = bearish
            "confidence": "low" | "medium" | "high",
            "description": "Market is slightly bearish with 50.25% shorts"
        }
    """
    data = get_long_short_ratio(symbol, time_type)
    if not data:
        return None

    long_rate = data.get("longRate", 50)
    short_rate = data.get("shortRate", 50)
    bias = long_rate - short_rate  # Positive = more longs, negative = more shorts

    # Determine sentiment
    if bias >= 10:
        sentiment = "extremely_bullish"
        confidence = "high"
    elif bias >= 5:
        sentiment = "bullish"
        confidence = "medium"
    elif bias >= 2:
        sentiment = "slightly_bullish"
        confidence = "low"
    elif bias <= -10:
        sentiment = "extremely_bearish"
        confidence = "high"
    elif bias <= -5:
        sentiment = "bearish"
        confidence = "medium"
    elif bias <= -2:
        sentiment = "slightly_bearish"
        confidence = "low"
    else:
        sentiment = "neutral"
        confidence = "low"

    # Generate description
    dominant = "longs" if bias > 0 else "shorts"
    dom_rate = long_rate if bias > 0 else short_rate
    description = f"Market is {sentiment.replace('_', ' ')} with {dom_rate:.1f}% {dominant}"

    return {
        "symbol": data["symbol"],
        "sentiment": sentiment,
        "longRate": long_rate,
        "shortRate": short_rate,
        "bias": round(bias, 2),
        "confidence": confidence,
        "description": description,
        "time_type": time_type,
        "totalVolUsd": data.get("totalVolUsd", 0)
    }


def compare_exchanges(symbol: str, time_type: str = "h1") -> Optional[List[Dict[str, Any]]]:
    """
    Compare long/short ratios across exchanges for a symbol.

    Args:
        symbol: Symbol to compare (BTC, ETH, etc.)
        time_type: Time interval

    Returns:
        List of exchange ratios sorted by long percentage:
        [
            {"exchange": "CoinEx", "longRate": 55.2, "shortRate": 44.8, "bias": 10.4},
            {"exchange": "Binance", "longRate": 50.1, "shortRate": 49.9, "bias": 0.2},
            ...
        ]
    """
    data = get_long_short_ratio(symbol, time_type)
    if not data or not data.get("exchanges"):
        return None

    results = []
    for ex in data["exchanges"]:
        long_rate = ex.get("longRate", 50)
        short_rate = ex.get("shortRate", 50)
        results.append({
            "exchange": ex.get("exchangeName"),
            "longRate": long_rate,
            "shortRate": short_rate,
            "bias": round(long_rate - short_rate, 2),
            "totalVolUsd": ex.get("totalVolUsd", 0)
        })

    return sorted(results, key=lambda x: x["longRate"], reverse=True)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Fetch Coinglass long/short ratios")
    parser.add_argument("--symbol", "-s", required=True, help="Symbol to query (BTC, ETH, etc.)")
    parser.add_argument("--exchange", "-e", help="Specific exchange (Binance, OKX, etc.)")
    parser.add_argument("--time-type", "-t", default="h1",
                       choices=TIME_TYPES, help="Time interval (default: h1)")
    parser.add_argument("--sentiment", action="store_true", help="Show sentiment analysis")
    parser.add_argument("--compare", action="store_true", help="Compare across exchanges")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.sentiment:
        result = get_sentiment(args.symbol, args.time_type)
        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\n{result['symbol']} Sentiment Analysis ({args.time_type})")
                print("=" * 50)
                print(f"Sentiment: {result['sentiment'].upper()}")
                print(f"Long: {result['longRate']:.2f}% | Short: {result['shortRate']:.2f}%")
                print(f"Bias: {result['bias']:+.2f}%")
                print(f"Confidence: {result['confidence']}")
                print(f"Description: {result['description']}")
        else:
            print(f"No data found for {args.symbol}")
        return

    if args.compare:
        result = compare_exchanges(args.symbol, args.time_type)
        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\n{args.symbol} Exchange Comparison ({args.time_type})")
                print("=" * 60)
                print(f"{'Exchange':<15} {'Long':>8} {'Short':>8} {'Bias':>8}")
                print("-" * 60)
                for ex in result:
                    print(f"{ex['exchange']:<15} {ex['longRate']:>7.2f}% {ex['shortRate']:>7.2f}% {ex['bias']:>+7.2f}%")
        else:
            print(f"No data found for {args.symbol}")
        return

    if args.exchange:
        result = get_exchange_ratio(args.symbol, args.exchange, args.time_type)
        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\n{result['symbol']} on {result['exchange']} ({args.time_type})")
                print("=" * 50)
                print(f"Long: {result['longRate']:.2f}%")
                print(f"Short: {result['shortRate']:.2f}%")
                print(f"Total Volume: ${result['totalVolUsd']:,.2f}")
                print(f"Turnover: {result['turnoverNumber']:,}")
        else:
            print(f"No data found for {args.symbol} on {args.exchange}")
        return

    # Default: get overall ratio
    result = get_long_short_ratio(args.symbol, args.time_type)
    if result:
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n{result['symbol']} Long/Short Ratio ({args.time_type})")
            print("=" * 50)
            print(f"Long: {result['longRate']:.2f}%")
            print(f"Short: {result['shortRate']:.2f}%")
            print(f"Long Volume: ${result['longVolUsd']:,.2f}")
            print(f"Short Volume: ${result['shortVolUsd']:,.2f}")
            print(f"Total Volume: ${result['totalVolUsd']:,.2f}")
            print(f"\nExchanges: {len(result.get('exchanges', []))}")
    else:
        print(f"No data found for {args.symbol}")


if __name__ == "__main__":
    main()
