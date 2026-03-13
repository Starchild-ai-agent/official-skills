#!/usr/bin/env python3
"""
Coinglass Bitcoin ETF Module

Provides Bitcoin ETF data including:
- ETF flow history (inflows/outflows)
- Net assets history
- Premium/discount rates
- Comprehensive ETF history
- ETF list
- Hong Kong Bitcoin ETF flows

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key

Usage Example:
    from tools.coinglass.bitcoin_etf import get_btc_etf_flows

    # Get Bitcoin ETF flow history
    data = get_btc_etf_flows()
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


def get_btc_etf_flows() -> Optional[Dict[str, Any]]:
    """
    Get Bitcoin ETF flow history including daily net inflows/outflows.

    Returns:
        Dictionary with ETF flows:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "date": "2024-01-15",
                    "net_flow_usd": 500000000,
                    "inflow_usd": 700000000,
                    "outflow_usd": 200000000,
                    "btc_price": 45000
                }
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/etf/bitcoin/flow-history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_btc_etf_net_assets() -> Optional[Dict[str, Any]]:
    """
    Get Bitcoin ETF net assets history.

    Returns:
        Dictionary with net assets:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "date": "2024-01-15",
                    "net_assets_usd": 25000000000,
                    "daily_change_usd": 500000000,
                    "btc_price": 45000,
                    "btc_holdings": 555555
                }
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/reference/bitcoin-etf-netassets-history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_btc_etf_premium_discount() -> Optional[Dict[str, Any]]:
    """
    Get Bitcoin ETF premium/discount rates.

    Returns:
        Dictionary with premium/discount data:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "ticker": "IBIT",
                    "nav": 45000,
                    "market_price": 45100,
                    "premium_discount_percent": 0.22,
                    "timestamp": 1705334400
                }
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/etf/bitcoin/premium-discount/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_btc_etf_history(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive Bitcoin ETF history for a specific ticker.

    Includes market price, NAV, premium/discount %, shares outstanding, and net assets.

    Args:
        ticker: ETF ticker symbol (e.g. IBIT, FBTC, GBTC)

    Returns:
        Dictionary with comprehensive ETF history for the specified ticker
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/etf/bitcoin/history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}
    params = {"ticker": ticker.upper()}

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_btc_etf_list() -> Optional[Dict[str, Any]]:
    """
    Get list of Bitcoin ETFs with key status information.

    Returns:
        Dictionary with ETF list including ticker, name, inception date, etc.
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/etf/bitcoin/list"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_hk_btc_etf_flows() -> Optional[Dict[str, Any]]:
    """
    Get Hong Kong Bitcoin ETF flow history.

    Returns:
        Dictionary with HK ETF flows similar to US ETF flows structure
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/hk-etf/bitcoin/flow-history"
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
        description="Coinglass Bitcoin ETF Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--function", "-f", required=True,
                       choices=["flows", "net-assets", "premium-discount", "history", "list", "hk-flows"],
                       help="Function to call")
    parser.add_argument("--ticker", "-t", help="ETF ticker (e.g. IBIT, FBTC, GBTC)")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = None

    if args.function == "flows":
        result = get_btc_etf_flows()
    elif args.function == "net-assets":
        result = get_btc_etf_net_assets()
    elif args.function == "premium-discount":
        result = get_btc_etf_premium_discount()
    elif args.function == "history":
        if not args.ticker:
            parser.error("--ticker required for history")
        result = get_btc_etf_history(args.ticker)
    elif args.function == "list":
        result = get_btc_etf_list()
    elif args.function == "hk-flows":
        result = get_hk_btc_etf_flows()

    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
