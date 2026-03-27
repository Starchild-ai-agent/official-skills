#!/usr/bin/env python3
"""
Birdeye Wallet Net Worth Module

Track wallet net worth (current snapshot and historical chart).
Provides portfolio value tracking across chains.

Note: Wallet APIs have limited rate (5 req/s, 75 req/min).

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- BIRDEYE_API_KEY: Your Birdeye API key

Usage Example:
    from tools.wallet.networth import get_wallet_networth, get_wallet_networth_chart

    # Get current net worth
    networth = get_wallet_networth(wallet="wallet_address", chain="solana")

    # Get net worth chart over time
    chart = get_wallet_networth_chart(wallet="wallet_address", chain="solana", interval="1d")

CLI Usage:
    python networth.py current --wallet <address> --chain solana
    python networth.py chart --wallet <address> --chain solana --interval 1d
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
    load_dotenv(os.path.join(project_root, '.env'))
except ImportError:
    pass

import requests
from core.http_client import proxied_get

# Birdeye Configuration
BASE_URL = "https://public-api.birdeye.so"
HEADER_KEY = "X-API-KEY"

# Supported chains
CHAINS = ["solana", "ethereum", "arbitrum", "avalanche", "bsc", "optimism", "polygon", "base", "zksync", "sui"]


def _get_api_key() -> Optional[str]:
    """Get Birdeye API key from environment."""
    return os.getenv("BIRDEYE_API_KEY")


def get_wallet_networth(
    wallet: str,
    chain: str = "solana", max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get current net worth and portfolio snapshot for a wallet.

    Returns total portfolio value, token breakdown, and asset allocation.

    Args:
        wallet: Wallet address
        chain: Blockchain (solana, ethereum, arbitrum, etc.)

    Returns:
        Dictionary with net worth data:
        {
            "success": true,
            "data": {
                "wallet": "wallet_address",
                "total_usd": 12345.67,
                "items": [
                    {
                        "address": "token_address",
                        "symbol": "TOKEN",
                        "name": "Token Name",
                        "balance": 1000.0,
                        "price_usd": 1.23,
                        "value_usd": 1230.0,
                        "percentage": 10.0
                    },
                    ...
                ]
            }
        }
        Returns None if request fails.

    Example:
        networth = get_wallet_networth("wallet_address", "solana")
        print(f"Total: ${networth['data']['total_usd']:,.2f}")
        for token in networth["data"]["items"][:5]:
            print(f"{token['symbol']}: ${token['value_usd']:,.2f} ({token['percentage']:.1f}%)")
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: BIRDEYE_API_KEY environment variable is required", file=sys.stderr)
        return None

    if chain not in CHAINS:
        print(f"Error: Unsupported chain '{chain}'. Supported: {', '.join(CHAINS)}", file=sys.stderr)
        return None

    url = f"{BASE_URL}/wallet/v2/net-worth"

    headers = {
        "accept": "application/json",
        HEADER_KEY: api_key,
        "x-chain": chain
    }

    params = {"wallet": wallet}

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            print(f"API Error: {data.get('message', 'Unknown error')}", file=sys.stderr)
            return None

        filtered_output = data.get("data", data)
        if isinstance(filtered_output, list):
            filtered_output = filtered_output[:max_results]
        return filtered_output

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}", file=sys.stderr)
        return None


def get_wallet_networth_chart(
    wallet: str,
    chain: str = "solana",
    interval: str = "1d",
    time_from: Optional[int] = None,
    time_to: Optional[int] = None, max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get net worth chart data over time.

    Provides historical net worth timeseries for portfolio tracking.

    Args:
        wallet: Wallet address
        chain: Blockchain (solana, ethereum, arbitrum, etc.)
        interval: Time interval (1h, 4h, 1d, 1w)
        time_from: Start timestamp (Unix seconds) (optional)
        time_to: End timestamp (Unix seconds) (optional)

    Returns:
        Dictionary with chart data:
        {
            "success": true,
            "data": {
                "wallet": "wallet_address",
                "items": [
                    {
                        "timestamp": 1234567890,
                        "value_usd": 12345.67
                    },
                    ...
                ]
            }
        }
        Returns None if request fails.

    Example:
        chart = get_wallet_networth_chart("wallet_address", "solana", interval="1d")
        for point in chart["data"]["items"]:
            print(f"{point['timestamp']}: ${point['value_usd']:,.2f}")
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: BIRDEYE_API_KEY environment variable is required", file=sys.stderr)
        return None

    if chain not in CHAINS:
        print(f"Error: Unsupported chain '{chain}'. Supported: {', '.join(CHAINS)}", file=sys.stderr)
        return None

    url = f"{BASE_URL}/wallet/v2/net-worth"

    headers = {
        "accept": "application/json",
        HEADER_KEY: api_key,
        "x-chain": chain
    }

    params = {
        "wallet": wallet,
        "time_type": interval
    }

    if time_from:
        params["time_from"] = time_from
    if time_to:
        params["time_to"] = time_to

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            print(f"API Error: {data.get('message', 'Unknown error')}", file=sys.stderr)
            return None

        filtered_output = data.get("data", data)
        if isinstance(filtered_output, list):
            filtered_output = filtered_output[:max_results]
        return filtered_output

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}", file=sys.stderr)
        return None


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Birdeye wallet net worth tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Current net worth command
    current_parser = subparsers.add_parser("current", help="Get current net worth")
    current_parser.add_argument("--wallet", "-w", required=True, help="Wallet address")
    current_parser.add_argument("--chain", "-c", default="solana", choices=CHAINS, help="Blockchain")
    current_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    # Chart command
    chart_parser = subparsers.add_parser("chart", help="Get net worth chart")
    chart_parser.add_argument("--wallet", "-w", required=True, help="Wallet address")
    chart_parser.add_argument("--chain", "-c", default="solana", choices=CHAINS, help="Blockchain")
    chart_parser.add_argument("--interval", "-i", default="1d", choices=["1h", "4h", "1d", "1w"], help="Time interval")
    chart_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.command == "current":
        result = get_wallet_networth(wallet=args.wallet, chain=args.chain)

        if result and result.get("success"):
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                data = result.get("data", {})
                print(f"\nNet Worth for {args.wallet[:8]}... on {args.chain.upper()}")
                print("=" * 80)
                print(f"Total: ${data.get('total_usd', 0):,.2f}")
                print("\nTop Holdings:")
                print(f"{'Symbol':<12} {'Balance':>15} {'Price':>12} {'Value USD':>15} {'%':>8}")
                print("-" * 80)
                for token in data.get("items", [])[:10]:
                    print(
                        f"{token.get('symbol', 'N/A'):<12} "
                        f"{token.get('balance', 0):>15,.4f} "
                        f"${token.get('price_usd', 0):>11.6f} "
                        f"${token.get('value_usd', 0):>14,.2f} "
                        f"{token.get('percentage', 0):>7.1f}%"
                    )
        else:
            print("Failed to fetch wallet net worth")
            sys.exit(1)

    elif args.command == "chart":
        result = get_wallet_networth_chart(
            wallet=args.wallet,
            chain=args.chain,
            interval=args.interval
        )

        if result and result.get("success"):
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                items = result.get("data", {}).get("items", [])
                print(f"\nNet Worth Chart for {args.wallet[:8]}... on {args.chain.upper()}")
                print(f"Interval: {args.interval}")
                print("=" * 60)
                print(f"{'Timestamp':<20} {'Value USD':>20}")
                print("-" * 60)
                for point in items[-20:]:  # Last 20 data points
                    from datetime import datetime
                    ts = datetime.fromtimestamp(point.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M')
                    print(f"{ts:<20} ${point.get('value_usd', 0):>19,.2f}")
        else:
            print("Failed to fetch wallet net worth chart")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
