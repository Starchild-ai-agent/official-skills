#!/usr/bin/env python3
"""
Coinglass Advanced Long/Short Ratio Module

Provides advanced long/short ratio data including:
- Global account ratio history
- Top traders account ratio
- Top traders position ratio
- Taker buy/sell volume exchange list
- Net position data (v1 and v2)

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key

Usage Example:
    from tools.coinglass.long_short_advanced import get_global_account_ratio

    # Get global account ratio for BTC on Binance
    data = get_global_account_ratio(symbol="BTC", exchange="Binance", interval="1h")
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

# Coinglass API V4 Configuration
BASE_URL = "https://open-api-v4.coinglass.com"
HEADER_KEY = "CG-API-KEY"


def _get_api_key() -> Optional[str]:
    """Get Coinglass API key from environment."""
    return os.getenv("COINGLASS_API_KEY")


def _normalize_exchange_name(exchange: str) -> str:
    """
    Normalize exchange name to proper case format required by API.

    API expects proper case like "Binance", "OKX", "Bybit", not "BINANCE".

    Args:
        exchange: Exchange name in any case

    Returns:
        Exchange name in proper case format
    """
    # Handle common exchanges with specific casing
    exchange_map = {
        "binance": "Binance",
        "okx": "OKX",
        "bybit": "Bybit",
        "deribit": "Deribit",
        "bitmex": "BitMEX",
        "bitget": "Bitget",
        "gate": "Gate",
        "kraken": "Kraken",
        "huobi": "Huobi",
        "coinex": "CoinEx",
        "mexc": "MEXC",
        "bitfinex": "Bitfinex",
    }

    exchange_lower = exchange.lower()
    return exchange_map.get(exchange_lower, exchange.capitalize())


def get_global_account_ratio(
    symbol: str,
    exchange: str,
    interval: str = "1h",
    limit: int = 100
) -> Optional[Dict[str, Any]]:
    """
    Get global long/short account ratio history for a trading pair on an exchange.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)
        exchange: Exchange name (Binance, OKX, Bybit, etc.)
        interval: Time interval (1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w)
        limit: Number of results (default 100)

    Returns:
        Dictionary with account ratio history:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "time": timestamp,
                    "long_ratio": number,
                    "short_ratio": number
                }
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/global-long-short-account-ratio/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    # API requires trading pair format (e.g., "BTCUSDT") not just symbol
    trading_pair = f"{symbol.upper()}USDT" if not symbol.upper().endswith("USDT") else symbol.upper()
    params = {
        "symbol": trading_pair,
        "exchange": _normalize_exchange_name(exchange),
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


def get_top_account_ratio(
    symbol: str,
    exchange: str,
    interval: str = "1h",
    limit: int = 100
) -> Optional[Dict[str, Any]]:
    """
    Get long/short account ratio history for top traders.

    Args:
        symbol: Trading coin
        exchange: Exchange name
        interval: Time interval
        limit: Number of results

    Returns:
        Dictionary with top trader account ratio data
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/top-long-short-account-ratio/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    # API requires trading pair format (e.g., "BTCUSDT") not just symbol
    trading_pair = f"{symbol.upper()}USDT" if not symbol.upper().endswith("USDT") else symbol.upper()
    params = {
        "symbol": trading_pair,
        "exchange": _normalize_exchange_name(exchange),
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


def get_top_position_ratio(
    symbol: str,
    exchange: str,
    interval: str = "1h",
    limit: int = 100
) -> Optional[Dict[str, Any]]:
    """
    Get long/short position ratio history for top traders.

    Args:
        symbol: Trading coin
        exchange: Exchange name
        interval: Time interval
        limit: Number of results

    Returns:
        Dictionary with top trader position ratio data
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/top-long-short-position-ratio/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    # API requires trading pair format (e.g., "BTCUSDT") not just symbol
    trading_pair = f"{symbol.upper()}USDT" if not symbol.upper().endswith("USDT") else symbol.upper()
    params = {
        "symbol": trading_pair,
        "exchange": _normalize_exchange_name(exchange),
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


def get_taker_buysell_exchanges(symbol: str, range: str = "1h") -> Optional[Dict[str, Any]]:
    """
    Get list of exchanges with taker buy/sell volume data for a specific symbol.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)
        range: Time range (1h, 4h, 12h, 24h) - default: 1h

    Returns:
        Dictionary with exchange list and volume ratios for the specified coin
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/taker-buy-sell-volume/exchange-list"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {"symbol": symbol.upper(), "range": range}

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_net_position(
    symbol: str,
    exchange: str,
    interval: str = "1h",
    limit: int = 100
) -> Optional[Dict[str, Any]]:
    """
    Get historical net position data (net long/short changes).

    Args:
        symbol: Trading coin
        exchange: Exchange name
        interval: Time interval
        limit: Number of results

    Returns:
        Dictionary with net position history including net_long_change and net_short_change
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/net-position/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    # API requires trading pair format (e.g., "BTCUSDT") not just symbol
    trading_pair = f"{symbol.upper()}USDT" if not symbol.upper().endswith("USDT") else symbol.upper()
    params = {
        "symbol": trading_pair,
        "exchange": _normalize_exchange_name(exchange),
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


def get_net_position_v2(
    symbol: str,
    exchange: str,
    interval: str = "1h",
    limit: int = 100
) -> Optional[Dict[str, Any]]:
    """
    Get enhanced historical net position data (v2 endpoint).

    Args:
        symbol: Trading coin
        exchange: Exchange name
        interval: Time interval
        limit: Number of results

    Returns:
        Dictionary with enhanced net position history
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/v2/net-position/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {
        "symbol": symbol.upper(),
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
        description="Coinglass Advanced Long/Short Ratio Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--function", "-f", required=True,
                       choices=["global-account", "top-account", "top-position", "taker-exchanges", "net-position", "net-position-v2"],
                       help="Function to call")
    parser.add_argument("--symbol", "-s", help="Symbol (BTC, ETH, etc.)")
    parser.add_argument("--exchange", "-e", help="Exchange name (Binance, OKX, etc.)")
    parser.add_argument("--interval", "-i", default="1h", help="Time interval (default: 1h)")
    parser.add_argument("--limit", "-l", type=int, default=100, help="Number of results (default: 100)")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = None

    if args.function == "global-account":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for global-account")
        result = get_global_account_ratio(args.symbol, args.exchange, args.interval, args.limit)
    elif args.function == "top-account":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for top-account")
        result = get_top_account_ratio(args.symbol, args.exchange, args.interval, args.limit)
    elif args.function == "top-position":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for top-position")
        result = get_top_position_ratio(args.symbol, args.exchange, args.interval, args.limit)
    elif args.function == "taker-exchanges":
        result = get_taker_buysell_exchanges()
    elif args.function == "net-position":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for net-position")
        result = get_net_position(args.symbol, args.exchange, args.interval, args.limit)
    elif args.function == "net-position-v2":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for net-position-v2")
        result = get_net_position_v2(args.symbol, args.exchange, args.interval, args.limit)

    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
