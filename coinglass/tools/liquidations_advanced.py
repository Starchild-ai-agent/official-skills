#!/usr/bin/env python3
"""
Coinglass Liquidations Advanced Module

Provides detailed liquidation data: coin/pair history,
coin list aggregation, liquidation orders, and heatmap data.
"""

import sys
import json
import argparse
from typing import Dict, Any, List, Optional

from ._api import cg_request


def get_coin_liquidation_history(
    symbol: str = "BTC",
    interval: str = "h4"
) -> Optional[List[Dict[str, Any]]]:
    """
    Get aggregated liquidation history for a coin.

    Args:
        symbol: Coin symbol (BTC, ETH, SOL, etc.)
        interval: Time interval (h1, h4, h12, h24).
    """
    return cg_request(
        "api/futures/liquidation/aggregated-history",
        params={"symbol": symbol, "interval": interval}
    )


def get_pair_liquidation_history(
    symbol: str = "BTC",
    exchange: str = "Binance",
    interval: str = "h4"
) -> Optional[List[Dict[str, Any]]]:
    """
    Get liquidation history for a specific trading pair.

    Args:
        symbol: Coin symbol.
        exchange: Exchange name.
        interval: Time interval (h1, h4, h12, h24).
    """
    return cg_request(
        "api/futures/liquidation/history",
        params={
            "symbol": symbol,
            "exchange": exchange,
            "interval": interval,
        }
    )


def get_liquidation_coin_list(
    symbol: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Get liquidation summary aggregated by coin.

    Args:
        symbol: Optional coin filter.
    """
    params = {}
    if symbol:
        params["symbol"] = symbol
    return cg_request(
        "api/futures/liquidation/coin-list",
        params=params or None
    )


def get_liquidation_orders(
    symbol: str = "BTC",
    exchange: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Get recent large liquidation orders.

    Args:
        symbol: Coin symbol.
        exchange: Optional exchange filter.
    """
    params = {"symbol": symbol}
    if exchange:
        params["exchange"] = exchange
    return cg_request("api/futures/liquidation/order", params=params)


def get_liquidation_heatmap(
    symbol: str = "BTC",
    exchange: Optional[str] = None,
    range: str = "24h"
) -> Optional[Dict[str, Any]]:
    """
    Get liquidation heatmap data (price levels with liquidation density).

    Args:
        symbol: Coin symbol.
        exchange: Exchange name. If omitted, use aggregated heatmap across exchanges.
        range: Time range (12h, 24h, 3d, 7d, 30d, 90d, 180d, 1y).
    """
    if exchange:
        # Pair heatmap requires valid exchange+instrument mapping
        return cg_request(
            "api/futures/liquidation/heatmap/model1",
            params={"symbol": symbol, "exchange": exchange, "range": range}
        )

    # Aggregated heatmap is more stable for symbol-level liquidation zones
    return cg_request(
        "api/futures/liquidation/aggregated-heatmap/model1",
        params={"symbol": symbol, "range": range}
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Coinglass Liquidation Advanced Tools"
    )
    parser.add_argument("action", choices=[
        "coin-history", "pair-history", "coin-list",
        "orders", "heatmap"
    ])
    parser.add_argument("--symbol", "-s", default="BTC")
    parser.add_argument("--exchange", "-e", default=None)
    parser.add_argument("--range", "-r", default="24h")
    parser.add_argument("--interval", "-i", default="h4")
    args = parser.parse_args()

    actions = {
        "coin-history": lambda: get_coin_liquidation_history(
            args.symbol, args.interval
        ),
        "pair-history": lambda: get_pair_liquidation_history(
            args.symbol, args.exchange, args.interval
        ),
        "coin-list": lambda: get_liquidation_coin_list(args.symbol),
        "orders": lambda: get_liquidation_orders(
            args.symbol, args.exchange
        ),
        "heatmap": lambda: get_liquidation_heatmap(
            symbol=args.symbol,
            exchange=args.exchange,
            range=args.range,
        ),
    }

    try:
        result = actions[args.action]()
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
