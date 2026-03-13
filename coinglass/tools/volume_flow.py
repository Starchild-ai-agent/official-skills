#!/usr/bin/env python3
"""
Coinglass Volume & Flow Module

Provides volume and flow data including:
- Taker buy/sell volume history (pair-specific)
- Aggregated taker buy/sell volume (coin-level)
- Cumulative Volume Delta (CVD)
- Coin netflow data
- Volume OHLC history

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key

Usage Example:
    from tools.coinglass.volume_flow import get_taker_volume_history

    # Get taker volume history for BTC on Binance
    data = get_taker_volume_history(symbol="BTC", exchange="Binance", interval="1h", limit=100)
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


def get_taker_volume_history(
    symbol: str,
    exchange: str,
    interval: str = "1h",
    limit: int = 1000,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Get historical taker buy/sell volume data for a specific trading pair.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)
        exchange: Exchange name (Binance, OKX, Bybit, etc.)
        interval: Time interval (1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 8h, 12h, 1d, 1w)
        limit: Number of results (default 1000, max 4500)
        start_time: Start timestamp in seconds
        end_time: End timestamp in seconds

    Returns:
        Dictionary with taker volume history:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "time": timestamp,
                    "buy_vol_usd": amount,
                    "sell_vol_usd": amount,
                    "buy_sell_ratio": ratio
                }
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/v2/taker-buy-sell-volume/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    # API requires trading pair format (e.g., "BTCUSDT") not just symbol
    trading_pair = f"{symbol.upper()}USDT" if not symbol.upper().endswith("USDT") else symbol.upper()
    params = {
        "symbol": trading_pair,
        "exchange": exchange,
        "interval": interval,
        "limit": limit
    }

    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_aggregated_taker_volume(
    symbol: str,
    exchange_list: str,
    interval: str = "1h",
    limit: int = 1000,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Get aggregated taker buy/sell volume across specified exchanges for a coin.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)
        exchange_list: Comma-separated exchange list (e.g. 'Binance,OKX,Bybit')
        interval: Time interval (1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 8h, 12h, 1d, 1w)
        limit: Number of results (default 1000, max 4500)
        start_time: Start timestamp in seconds
        end_time: End timestamp in seconds

    Returns:
        Dictionary with aggregated taker volume:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "time": timestamp,
                    "buy_vol_usd": total_buy,
                    "sell_vol_usd": total_sell,
                    "buy_sell_ratio": ratio
                }
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/aggregated-taker-buy-sell-volume/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {
        "symbol": symbol.upper(),
        "exchange_list": exchange_list,
        "interval": interval,
        "limit": limit
    }

    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_cumulative_volume_delta(
    symbol: str,
    exchange: str,
    interval: str = "1h",
    limit: int = 1000,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Get Cumulative Volume Delta (CVD) history for a trading pair.

    CVD tracks the difference between taker buy and sell volume over time,
    providing insight into market pressure and trend strength.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)
        exchange: Exchange name (Binance, OKX, Bybit, etc.)
        interval: Time interval (1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 8h, 12h, 1d, 1w)
        limit: Number of results (default 1000, max 4500)
        start_time: Start timestamp in seconds
        end_time: End timestamp in seconds

    Returns:
        Dictionary with CVD history:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "time": timestamp,
                    "cvd": cumulative_delta,
                    "buy_vol": buy_volume,
                    "sell_vol": sell_volume
                }
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/cvd/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    # API requires trading pair format (e.g., "BTCUSDT") not just symbol
    trading_pair = f"{symbol.upper()}USDT" if not symbol.upper().endswith("USDT") else symbol.upper()
    params = {
        "symbol": trading_pair,
        "exchange": exchange,
        "interval": interval,
        "limit": limit
    }

    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_coin_netflow() -> Optional[Dict[str, Any]]:
    """
    Get coin netflow data for all futures coins.

    Netflow indicates whether capital is flowing into or out of a coin
    across exchanges, useful for identifying accumulation/distribution.

    Returns:
        Dictionary with netflow data for all coins:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "symbol": "BTC",
                    "netflow_usd": amount,
                    "netflow_24h": amount,
                    "netflow_7d": amount
                }
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/netflow-list"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_volume_ohlc_history(
    symbol: str,
    exchange: str,
    interval: str = "1h",
    limit: int = 100
) -> Optional[Dict[str, Any]]:
    """
    Get trading volume OHLC (Open, High, Low, Close) history.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)
        exchange: Exchange name (Binance, OKX, Bybit, etc.)
        interval: Time interval (1h, 4h, 12h, 1d)
        limit: Number of results (default 100)

    Returns:
        Dictionary with volume OHLC history:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "time": timestamp,
                    "open_vol": volume,
                    "high_vol": volume,
                    "low_vol": volume,
                    "close_vol": volume,
                    "volume_usd": amount
                }
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/vol-weight-ohlc-history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    # API requires trading pair format (e.g., "BTCUSDT") not just symbol
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
        description="Coinglass Volume & Flow Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--function", "-f", required=True,
                       choices=["taker-volume", "aggregated-taker", "cvd", "netflow", "volume-ohlc"],
                       help="Function to call")
    parser.add_argument("--symbol", "-s", help="Symbol (BTC, ETH, etc.)")
    parser.add_argument("--exchange", "-e", help="Exchange name (Binance, OKX, etc.)")
    parser.add_argument("--interval", "-i", default="1h", help="Time interval (default: 1h)")
    parser.add_argument("--limit", "-l", type=int, default=1000, help="Number of results")
    parser.add_argument("--start-time", type=int, help="Start timestamp in seconds")
    parser.add_argument("--end-time", type=int, help="End timestamp in seconds")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = None

    if args.function == "taker-volume":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for taker-volume")
        result = get_taker_volume_history(
            args.symbol, args.exchange, args.interval, args.limit, args.start_time, args.end_time
        )
    elif args.function == "aggregated-taker":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for aggregated-taker")
        result = get_aggregated_taker_volume(
            args.symbol, args.exchange, args.interval, args.limit, args.start_time, args.end_time
        )
    elif args.function == "cvd":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for cvd")
        result = get_cumulative_volume_delta(
            args.symbol, args.exchange, args.interval, args.limit, args.start_time, args.end_time
        )
    elif args.function == "netflow":
        result = get_coin_netflow()
    elif args.function == "volume-ohlc":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for volume-ohlc")
        result = get_volume_ohlc_history(
            args.symbol, args.exchange, args.interval, args.limit
        )

    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
