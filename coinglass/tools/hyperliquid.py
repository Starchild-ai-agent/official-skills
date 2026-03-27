#!/usr/bin/env python3
"""
Coinglass Hyperliquid Module

Provides Hyperliquid-specific data including:
- Whale alerts (large position opens/closes)
- Whale positions (current holdings)
- Wallet positions by coin
- Wallet positions by address
- Position distribution analysis

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key

Usage Example:
    from tools.coinglass.hyperliquid import get_whale_alerts

    # Get recent whale alerts on Hyperliquid
    data = get_whale_alerts()
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

def get_whale_alerts(max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get recent whale alerts on Hyperliquid (positions > $1M).

    Returns approximately 200 most recent large position opens/closes.

    Returns:
        Dictionary with whale alerts:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "user": "0x...",
                    "symbol": "ETH",
                    "position_size": 12700,
                    "entry_price": 1611.62,
                    "liq_price": 527.2521,
                    "position_value_usd": 21003260,
                    "position_action": 2,  # 1=open, 2=close
                    "create_time": 1745219517000
                }
            ]
        }
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/hyperliquid/whale-alert"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None

def get_whale_positions(max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get current whale positions on Hyperliquid.

    Shows large active positions with entry price, PnL, leverage, and margin data.

    Returns:
        Dictionary with whale positions:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "user": "0x...",
                    "symbol": "ETH",
                    "position_size": -44727.1273,  # negative=short
                    "entry_price": 2249.7,
                    "mark_price": 1645.8,
                    "liq_price": 2358.2766,
                    "leverage": 25,
                    "margin_balance": 2943581.7019,
                    "position_value_usd": 73589542.5467,
                    "unrealized_pnl": 27033236.424,
                    "funding_fee": -3107520.7373,
                    "margin_mode": "cross",
                    "create_time": 1741680802000,
                    "update_time": 1745219966000
                }
            ]
        }
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/hyperliquid/whale-position"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None

def get_positions_by_coin(symbol: str, max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get real-time wallet positions for a specific coin on Hyperliquid.

    Args:
        symbol: Trading coin (BTC, ETH, SOL, etc.)

    Returns:
        Dictionary with positions for the specified coin:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "user": "0x...",
                    "symbol": "ETH",
                    "position_size": -44727.1273,
                    "entry_price": 2249.7,
                    "mark_price": 1645.8,
                    "liq_price": 2358.2766,
                    "leverage": 25,
                    "margin_balance": 2943581.7019,
                    "position_value_usd": 73589542.5467,
                    "unrealized_pnl": 27033236.424,
                    "funding_fee": -3107520.7373,
                    "margin_mode": "cross",
                    "create_time": 1741680802000,
                    "update_time": 1745219966000
                }
            ]
        }
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/hyperliquid/position"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {"symbol": symbol.upper()}

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None

def get_user_positions(user_address: str, max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get positions for a specific user address on Hyperliquid.

    Shows margin summaries, withdrawable balance, and open positions.

    Args:
        user_address: Wallet address to query (required)

    Returns:
        Dictionary with user position data including margin and open positions
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/hyperliquid/user-position"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {"user_address": user_address}

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None

def get_position_distribution(max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get wallet position distribution on Hyperliquid.

    Shows distribution of positions by size tiers, including:
    - Address counts per tier
    - Long/short position values
    - Sentiment indicators
    - Profit/loss distribution

    Returns:
        Dictionary with position distribution analysis grouped by size tiers
    """
    api_key = get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/hyperliquid/wallet/position-distribution"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Coinglass Hyperliquid Data Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
            "--function",
            "-f",
            required=True,
            choices=["whale-alerts",
                     "whale-positions",
                     "positions-by-coin",
                     "user-positions",
                     "position-distribution"],
            help="Function to call"
    )
    parser.add_argument("--user", "-u", help="User address (for user-positions)")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = None

    if args.function == "whale-alerts":
        result = get_whale_alerts()
    elif args.function == "whale-positions":
        result = get_whale_positions()
    elif args.function == "positions-by-coin":
        result = get_positions_by_coin()
    elif args.function == "user-positions":
        result = get_user_positions(args.user)
    elif args.function == "position-distribution":
        result = get_position_distribution()

    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
