#!/usr/bin/env python3
"""
Coinglass Futures Market Module

Fetch futures market data including supported coins, exchanges, trading pairs,
market data, and OHLC price history from Coinglass API.

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key

Usage Example:
    from tools.coinglass.futures_market import get_supported_coins, get_pair_data

    # Get all supported coins
    coins = get_supported_coins()

    # Get market data for specific pair
    data = get_pair_data(symbol="BTC", exchange="Binance")

CLI Usage:
    python futures_market.py --supported-coins
    python futures_market.py --supported-exchanges
    python futures_market.py --pair-data --symbol BTC --exchange Binance
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

from core.http_client import proxied_get

# Coinglass API V4 Configuration
BASE_URL = "https://open-api-v4.coinglass.com"
HEADER_KEY = "CG-API-KEY"


def _get_api_key() -> Optional[str]:
    """Get Coinglass API key from environment."""
    return os.getenv("COINGLASS_API_KEY")


def get_supported_coins() -> Optional[Dict[str, Any]]:
    """
    Get list of supported coins for futures trading.

    Returns:
        Dictionary with supported coins data:
        {
            "code": "0",
            "msg": "success",
            "data": ["BTC", "ETH", "SOL", ...]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/supported-coins"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_supported_exchanges() -> Optional[Dict[str, Any]]:
    """
    Get list of supported exchanges for futures trading.

    Returns:
        Dictionary with supported exchanges data:
        {
            "code": "0",
            "msg": "success",
            "data": ["Binance", "OKX", "Bybit", ...]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/supported-exchange-pairs"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_supported_pairs(symbol: Optional[str] = None, exchange: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get list of supported trading pairs.

    Args:
        symbol: Optional coin symbol filter (BTC, ETH, etc.)
        exchange: Optional exchange filter (Binance, OKX, etc.)

    Returns:
        Dictionary with supported pairs data
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/supported-exchange-pairs"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {}

    if symbol:
        params["symbol"] = symbol.upper()
    if exchange:
        params["exchange"] = exchange

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_coins_data() -> Optional[Dict[str, Any]]:
    """
    Get market data for all coins.

    Returns:
        Dictionary with market data for all supported coins including
        price, volume, open interest, funding rate, etc.
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/coins-markets"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_pair_data(symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
    """
    Get market data for a specific trading pair.

    Args:
        symbol: Coin symbol (BTC, ETH, SOL, etc.)
        exchange: Exchange name (Binance, OKX, Bybit, etc.)

    Returns:
        Dictionary with pair market data including price, volume,
        open interest, funding rate, long/short ratio, etc.
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/pairs-markets"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {"symbol": symbol.upper(), "exchange": exchange}

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_ohlc_history(
    symbol: str,
    exchange: str,
    interval: str = "h1",
    limit: int = 100
) -> Optional[Dict[str, Any]]:
    """
    Get OHLC price history for a trading pair.

    Args:
        symbol: Coin symbol (BTC, ETH, SOL, etc.)
        exchange: Exchange name (Binance, OKX, Bybit, etc.)
        interval: Time interval (m1, m5, m15, m30, h1, h4, h12, d1)
        limit: Number of candles to return (default: 100)

    Returns:
        Dictionary with OHLC data:
        {
            "code": "0",
            "data": [
                {
                    "t": 1234567890000,  # timestamp
                    "o": 50000.0,  # open
                    "h": 51000.0,  # high
                    "l": 49500.0,  # low
                    "c": 50500.0   # close
                },
                ...
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    # Use V4 API endpoint for futures price history
    url = f"{BASE_URL}/api/futures/price/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    # Build trading pair symbol (e.g., BTCUSDT)
    # Most futures pairs are vs USDT
    trading_pair = f"{symbol.upper()}USDT" if not symbol.upper().endswith("USDT") else symbol.upper()

    params = {
        "symbol": trading_pair,
        "exchange": exchange,
        "interval": interval,
        "limit": limit
    }

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Coinglass Futures Market Data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get supported coins
  python futures_market.py --supported-coins

  # Get supported exchanges
  python futures_market.py --supported-exchanges

  # Get supported pairs
  python futures_market.py --supported-pairs
  python futures_market.py --supported-pairs --symbol BTC

  # Get all coins market data
  python futures_market.py --coins-data

  # Get specific pair data
  python futures_market.py --pair-data --symbol BTC --exchange Binance

  # Get OHLC history
  python futures_market.py --ohlc --symbol BTC --exchange Binance --interval h1 --limit 50
        """
    )

    parser.add_argument("--supported-coins", action="store_true", help="Get supported coins")
    parser.add_argument("--supported-exchanges", action="store_true", help="Get supported exchanges")
    parser.add_argument("--supported-pairs", action="store_true", help="Get supported pairs")
    parser.add_argument("--coins-data", action="store_true", help="Get all coins market data")
    parser.add_argument("--pair-data", action="store_true", help="Get specific pair data")
    parser.add_argument("--ohlc", action="store_true", help="Get OHLC history")

    parser.add_argument("--symbol", type=str, help="Coin symbol (BTC, ETH, SOL)")
    parser.add_argument("--exchange", type=str, help="Exchange name (Binance, OKX, Bybit)")
    parser.add_argument("--interval", type=str, default="h1", help="Time interval (m1, m5, m15, m30, h1, h4, h12, d1)")
    parser.add_argument("--limit", type=int, default=100, help="Number of candles")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = None

    if args.supported_coins:
        result = get_supported_coins()
    elif args.supported_exchanges:
        result = get_supported_exchanges()
    elif args.supported_pairs:
        result = get_supported_pairs(args.symbol, args.exchange)
    elif args.coins_data:
        result = get_coins_data()
    elif args.pair_data:
        if not args.symbol or not args.exchange:
            parser.error("--pair-data requires --symbol and --exchange")
        result = get_pair_data(args.symbol, args.exchange)
    elif args.ohlc:
        if not args.symbol or not args.exchange:
            parser.error("--ohlc requires --symbol and --exchange")
        result = get_ohlc_history(args.symbol, args.exchange, args.interval, args.limit)
    else:
        parser.print_help()
        return

    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
