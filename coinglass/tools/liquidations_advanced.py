#!/usr/bin/env python3
"""
Coinglass Advanced Liquidations Module

Provides detailed liquidation data including:
- Coin liquidation history (aggregated across exchanges)
- Pair liquidation history (exchange-specific)
- Exchange liquidation coin lists
- Individual liquidation orders
- Liquidation heatmaps

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key

Usage Example:
    from tools.coinglass.liquidations_advanced import get_coin_liquidation_history

    # Get BTC liquidation history aggregated across all exchanges
    data = get_coin_liquidation_history(symbol="BTC", interval="1h", limit=100)
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional

from core.http_client import proxied_get
from .utils import get_api_key

# Coinglass API V4 Configuration
BASE_URL = "https://open-api-v4.coinglass.com"
HEADER_KEY = "CG-API-KEY"

def get_coin_liquidation_history(
    symbol: str,
    exchange_list: str,
    interval: str = "1h",
    limit: int = 1000,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None, max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get aggregated liquidation history for a coin across specified exchanges.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)
        exchange_list: Comma-separated exchange list (e.g. 'Binance,OKX,Bybit')
        interval: Time interval (1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 8h, 12h, 1d, 1w)
        limit: Number of results (default 1000, max 4500)
        start_time: Start timestamp in milliseconds
        end_time: End timestamp in milliseconds

    Returns:
        Dictionary with aggregated liquidation history:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "time": timestamp,
                    "liquidation_usd": total,
                    "long_liquidation_usd": longs,
                    "short_liquidation_usd": shorts
                }
            ]
        }
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/liquidation/aggregated-history"
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

def get_pair_liquidation_history(
    symbol: str,
    exchange: str,
    interval: str = "1h",
    limit: int = 1000,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None, max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get liquidation history for a specific trading pair on an exchange.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)
        exchange: Exchange name (Binance, OKX, Bybit, etc.)
        interval: Time interval (1h, 4h, 12h, 24h)
        limit: Number of results (default 1000, max 4500)
        start_time: Start timestamp in seconds
        end_time: End timestamp in seconds

    Returns:
        Dictionary with pair liquidation history:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "exchange": "Binance",
                    "liquidation_usd": total,
                    "long_liquidation_usd": longs,
                    "short_liquidation_usd": shorts
                }
            ]
        }
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/liquidation/history"
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

def get_liquidation_coin_list(exchange: str, max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get liquidation data for all coins on a specific exchange.

    Shows liquidation amounts across multiple timeframes (1h, 4h, 12h, 24h) for all coins.

    Args:
        exchange: Exchange name (Binance, OKX, Bybit, etc.)

    Returns:
        Dictionary with coin liquidation data:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "symbol": "BTC",
                    "liquidation_usd_24h": amount,
                    "long_liquidation_usd_24h": longs,
                    "short_liquidation_usd_24h": shorts,
                    "liquidation_usd_12h": amount,
                    ... (same for 4h, 1h)
                }
            ]
        }
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/liquidation/coin-list"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {"exchange": exchange}

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None

def get_liquidation_orders(
    symbol: str,
    exchange: str,
    min_liquidation_amount: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None, max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get individual liquidation orders (past 7 days only).

    Retrieves actual liquidation events with details like price, side, and USD value.
    Max 200 records per request.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)
        exchange: Exchange name (Binance, OKX, Bybit, etc.)
        min_liquidation_amount: Minimum threshold for liquidation events (USD)
        start_time: Start timestamp in milliseconds
        end_time: End timestamp in milliseconds

    Returns:
        Dictionary with liquidation orders:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "exchange_name": "BINANCE",
                    "symbol": "BTCUSDT",
                    "base_asset": "BTC",
                    "price": 87535.9,
                    "usd_value": 205534.29,
                    "side": 2,  # 1=Buy, 2=Sell
                    "time": 1745216319263
                }
            ]
        }
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/liquidation/order"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {
        "symbol": symbol.upper(),
        "exchange": exchange,
        "min_liquidation_amount": min_liquidation_amount
    }

    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None

def get_liquidation_heatmap(
    symbol: str,
    exchange: str,
    range: str = "0.1", max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get liquidation heatmap data for a trading pair (Model 1).

    Shows liquidation levels calculated from market data and leverage amounts.
    Useful for identifying price levels with high liquidation risk.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)
        exchange: Exchange name (Binance, OKX, Bybit, etc.)
        range: Price range for heatmap (default: "0.1" for ±10%)
               Options: "0.05" (±5%), "0.1" (±10%), "0.15" (±15%), "0.2" (±20%)

    Returns:
        Dictionary with heatmap data for visualization
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/futures/liquidation/heatmap/model1"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {
        "symbol": symbol.upper(),
        "exchange": exchange,
        "range": range
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
        description="Coinglass Advanced Liquidations Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
            "--function",
            "-f",
            required=True,
            choices=["coin-history",
                     "pair-history",
                     "coin-list",
                     "orders",
                     "heatmap"],
            help="Function to call"
    )
    parser.add_argument("--symbol", "-s", help="Symbol (BTC, ETH, etc.)")
    parser.add_argument("--exchange", "-e", help="Exchange name (Binance, OKX, etc.)")
    parser.add_argument("--interval", "-i", default="1h", help="Time interval")
    parser.add_argument("--limit", "-l", type=int, default=1000, help="Number of results")
    parser.add_argument("--min-amount", type=str, help="Minimum liquidation amount (for orders)")
    parser.add_argument("--start-time", type=int, help="Start timestamp")
    parser.add_argument("--end-time", type=int, help="End timestamp")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = None

    if args.function == "coin-history":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for coin-history")
        result = get_coin_liquidation_history(
            args.symbol, args.exchange, args.interval, args.limit, args.start_time, args.end_time
        )
    elif args.function == "pair-history":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for pair-history")
        result = get_pair_liquidation_history(
            args.symbol, args.exchange, args.interval, args.limit, args.start_time, args.end_time
        )
    elif args.function == "coin-list":
        if not args.exchange:
            parser.error("--exchange required for coin-list")
        result = get_liquidation_coin_list(args.exchange)
    elif args.function == "orders":
        if not args.symbol or not args.exchange or not args.min_amount:
            parser.error("--symbol, --exchange, and --min-amount required for orders")
        result = get_liquidation_orders(
            args.symbol, args.exchange, args.min_amount, args.start_time, args.end_time
        )
    elif args.function == "heatmap":
        if not args.symbol or not args.exchange:
            parser.error("--symbol and --exchange required for heatmap")
        result = get_liquidation_heatmap(args.symbol, args.exchange)

    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
