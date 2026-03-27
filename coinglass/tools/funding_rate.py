#!/usr/bin/env python3
"""
Coinglass Funding Rate Module

Fetch funding rates across major cryptocurrency exchanges including
Binance, OKX, Bybit, KuCoin, MEXC, Bitfinex, Kraken, and more.

Funding rates are fees set by cryptocurrency exchanges to maintain balance
between contract price and underlying asset price in perpetual futures contracts.
Positive rates mean longs pay shorts; negative rates mean shorts pay longs.

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key

Usage Example:
    from tools.coinglass.funding_rate import get_funding_rates, get_symbol_funding_rate

    # Get all funding rates for BTC
    rates = get_funding_rates(symbol="BTC")

    # Get funding rate for specific exchange
    binance_rate = get_symbol_funding_rate(symbol="BTC", exchange="Binance")

CLI Usage:
    python funding_rate.py --symbol BTC
    python funding_rate.py --symbol ETH --exchange Binance
    python funding_rate.py --all
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional, List

import requests
from core.http_client import proxied_get
from .utils import get_api_key

# Coinglass Configuration
BASE_URL = "https://open-api.coinglass.com/public/v2"
HEADER_KEY = "coinglassSecret"

# Supported exchanges
EXCHANGES = [
    "Binance", "OKX", "Bybit", "KuCoin", "MEXC", "CoinEx",
    "Bitfinex", "Kraken", "dYdX", "Gate", "Bitmex"
]

# Common symbols
SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "MATIC"]

def get_funding_rates(symbol: Optional[str] = None, max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Fetch funding rates across all exchanges.

    Args:
        symbol: Optional symbol filter (BTC, ETH, etc.). If None, returns all.

    Returns:
        Dictionary with funding rate data:
        {
            "symbol": "BTC",
            "uMarginList": [
                {
                    "exchangeName": "Binance",
                    "rate": 0.0058,  # Funding rate as decimal (0.58%)
                    "nextFundingTime": 1765497600000,  # Unix ms
                    "fundingIntervalHours": 8
                },
                ...
            ]
        }
        Returns None if request fails.

    Example:
        rates = get_funding_rates("BTC")
        for exchange in rates["data"]:
            if exchange["symbol"] == "BTC":
                for rate_info in exchange["uMarginList"]:
                    print(f"{rate_info['exchangeName']}: {rate_info['rate'] * 100:.4f}%")
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found in environment", file=sys.stderr)
        return None

    url = f"{BASE_URL}/funding"
    headers = {
        "accept": "application/json",
        HEADER_KEY: api_key
    }

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "0":
            print(f"API Error: {data.get('msg', 'Unknown error')}", file=sys.stderr)
            return None

        if symbol:
            # Filter for specific symbol
            filtered = [d for d in data.get("data", []) if d.get("symbol", "").upper() == symbol.upper()]
            return {"code": "0", "msg": "success", "data": filtered}

        return dict(**data)  # structured API response

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}", file=sys.stderr)
        return None

def get_symbol_funding_rate(
    symbol: str,
    exchange: Optional[str] = None, max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get funding rate for a specific symbol and optionally a specific exchange.

    Args:
        symbol: Symbol to query (BTC, ETH, etc.)
        exchange: Optional exchange name (Binance, OKX, Bybit, etc.)

    Returns:
        Dictionary with funding rate info:
        {
            "symbol": "BTC",
            "exchange": "Binance",  # or "all" if no exchange specified
            "rate": 0.0058,  # as decimal
            "rate_percent": 0.58,  # as percentage
            "next_funding_time": 1765497600000,
            "funding_interval_hours": 8,
            "predicted_rate": 0.0059  # if available
        }
        Returns None if not found.

    Example:
        rate = get_symbol_funding_rate("BTC", "Binance")
        if rate:
            print(f"BTC funding rate on Binance: {rate['rate_percent']:.4f}%")
    """
    data = get_funding_rates(symbol)
    if not data or not data.get("data"):
        return None

    symbol_data = data["data"][0] if data["data"] else None
    if not symbol_data:
        return None

    if exchange:
        # Find specific exchange
        for rate_info in symbol_data.get("uMarginList", []):
            if rate_info.get("exchangeName", "").lower() == exchange.lower():
                rate = rate_info.get("rate", 0)
                interval_h = rate_info.get("fundingIntervalHours", 8)
                # FIX: Normalize rate to 8h-equivalent for cross-exchange comparison
                rate_8h_eq = rate * (8 / interval_h) if interval_h else rate
                return {
                    "symbol": symbol.upper(),
                    "exchange": rate_info.get("exchangeName"),
                    "rate": rate,
                    "rate_percent": rate * 100,
                    "rate_8h_equivalent": rate_8h_eq,
                    "rate_8h_equivalent_percent": rate_8h_eq * 100,
                    "annualized_percent": rate_8h_eq * 3 * 365 * 100,
                    "next_funding_time": rate_info.get("nextFundingTime"),
                    "funding_interval_hours": interval_h,
                    "predicted_rate": rate_info.get("predictedRate"),
                    "predicted_rate_percent": (
                        rate_info.get("predictedRate", 0) * 100
                        if rate_info.get("predictedRate") else None
                    ),
                }
        return None
    else:
        # Return average across all exchanges
        # FIX: Normalize all rates to 8h-equivalent before averaging
        margin_list = symbol_data.get("uMarginList", [])
        normalized_rates = []
        for r in margin_list:
            rate = r.get("rate")
            if rate is None:
                continue
            interval_h = r.get("fundingIntervalHours", 8)
            rate_8h = rate * (8 / interval_h) if interval_h else rate
            normalized_rates.append(rate_8h)

        if not normalized_rates:
            return None
        avg_rate_8h = sum(normalized_rates) / len(normalized_rates)
        return {
            "symbol": symbol.upper(),
            "exchange": "average",
            "rate_8h_equivalent": avg_rate_8h,
            "rate_8h_equivalent_percent": avg_rate_8h * 100,
            "annualized_percent": avg_rate_8h * 3 * 365 * 100,
            "num_exchanges": len(normalized_rates),
            "note": "Rates normalized to 8h-equivalent for comparison",
            "exchanges_data": margin_list,
        }

def get_funding_rate_by_exchange(exchange: str, max_results: int = 100) -> Optional[List[Dict[str, Any]]]:
    """
    Get funding rates for all symbols on a specific exchange.

    Args:
        exchange: Exchange name (Binance, OKX, Bybit, etc.)

    Returns:
        List of funding rate dicts for each symbol on the exchange:
        [
            {"symbol": "BTC", "rate": 0.0058, "rate_percent": 0.58},
            {"symbol": "ETH", "rate": 0.0042, "rate_percent": 0.42},
            ...
        ]
        Returns None if request fails.
    """
    data = get_funding_rates()
    if not data or not data.get("data"):
        return None

    results = []
    for symbol_data in data["data"]:
        for rate_info in symbol_data.get("uMarginList", []):
            if rate_info.get("exchangeName", "").lower() == exchange.lower():
                rate = rate_info.get("rate", 0)
                results.append({
                    "symbol": symbol_data.get("symbol"),
                    "rate": rate,
                    "rate_percent": rate * 100,
                    "next_funding_time": rate_info.get("nextFundingTime"),
                    "funding_interval_hours": rate_info.get("fundingIntervalHours"),
                    "predicted_rate": rate_info.get("predictedRate")
                })

    return sorted(results, key=lambda x: abs(x.get("rate", 0)), reverse=True) if results else None

def analyze_funding_opportunity(symbol: str, threshold: float = 0.01, max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Analyze funding rate arbitrage opportunities across exchanges.

    Args:
        symbol: Symbol to analyze (BTC, ETH, etc.)
        threshold: Minimum rate difference to flag (default 0.01 = 1%)

    Returns:
        Dictionary with arbitrage analysis:
        {
            "symbol": "BTC",
            "highest": {"exchange": "CoinEx", "rate": 0.02, "rate_percent": 2.0},
            "lowest": {"exchange": "Kraken", "rate": -0.001, "rate_percent": -0.1},
            "spread": 0.021,  # difference
            "spread_percent": 2.1,
            "opportunity": True/False,
            "all_rates": [...]
        }
    """
    data = get_funding_rates(symbol)
    if not data or not data.get("data") or not data["data"]:
        return None

    symbol_data = data["data"][0]
    rates_list = symbol_data.get("uMarginList", [])

    if not rates_list:
        return None

    # Extract rates with exchange names
    rates = [
        {
            "exchange": r.get("exchangeName"),
            "rate": r.get("rate", 0),
            "rate_percent": r.get("rate", 0) * 100
        }
        for r in rates_list
        if r.get("rate") is not None
    ]

    if not rates:
        return None

    sorted_rates = sorted(rates, key=lambda x: x["rate"])
    lowest = sorted_rates[0]
    highest = sorted_rates[-1]
    spread = highest["rate"] - lowest["rate"]

    return {
        "symbol": symbol.upper(),
        "highest": highest,
        "lowest": lowest,
        "spread": spread,
        "spread_percent": spread * 100,
        "opportunity": spread >= threshold,
        "all_rates": sorted_rates
    }

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Fetch Coinglass funding rates")
    parser.add_argument("--symbol", "-s", help="Symbol to query (BTC, ETH, etc.)")
    parser.add_argument("--exchange", "-e", help="Specific exchange (Binance, OKX, etc.)")
    parser.add_argument("--all", "-a", action="store_true", help="Get all funding rates")
    parser.add_argument("--analyze", action="store_true", help="Analyze arbitrage opportunities")
    parser.add_argument("--by-exchange", help="Get all rates for an exchange")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.analyze and args.symbol:
        result = analyze_funding_opportunity(args.symbol)
        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\n{result['symbol']} Funding Rate Analysis")
                print("=" * 50)
                print(f"Highest: {result['highest']['exchange']}: {result['highest']['rate_percent']:.4f}%")
                print(f"Lowest:  {result['lowest']['exchange']}: {result['lowest']['rate_percent']:.4f}%")
                print(f"Spread:  {result['spread_percent']:.4f}%")
                print(f"Opportunity: {'YES' if result['opportunity'] else 'NO'}")
        else:
            print(f"No data found for {args.symbol}")
        return

    if args.by_exchange:
        result = get_funding_rate_by_exchange(args.by_exchange)
        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\n{args.by_exchange} Funding Rates")
                print("=" * 50)
                for r in result[:20]:  # Top 20
                    print(f"{r['symbol']:10s} {r['rate_percent']:>8.4f}%")
        else:
            print(f"No data found for exchange {args.by_exchange}")
        return

    if args.symbol:
        result = get_symbol_funding_rate(args.symbol, args.exchange)
        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\n{result['symbol']} Funding Rate")
                print("=" * 50)
                if args.exchange:
                    print(f"Exchange: {result['exchange']}")
                    print(f"Rate: {result['rate_percent']:.4f}%")
                    if result.get('predicted_rate_percent'):
                        print(f"Predicted: {result['predicted_rate_percent']:.4f}%")
                else:
                    print(f"Average Rate: {result['rate_percent']:.4f}%")
                    print(f"Exchanges: {result['num_exchanges']}")
        else:
            print(f"No funding rate found for {args.symbol}" + (f" on {args.exchange}" if args.exchange else ""))
        return

    if args.all:
        result = get_funding_rates()
        if result and result.get("data"):
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("\nAll Funding Rates")
                print("=" * 50)
                for symbol_data in result["data"][:20]:  # First 20 symbols
                    symbol = symbol_data.get("symbol", "???")
                    rates = symbol_data.get("uMarginList", [])
                    if rates:
                        avg = sum(r.get("rate", 0) for r in rates) / len(rates)
                        print(f"{symbol:10s} avg: {avg * 100:>8.4f}%")
        else:
            print("Failed to fetch funding rates")
        return

    # Default: show help
    parser.print_help()

if __name__ == "__main__":
    main()
