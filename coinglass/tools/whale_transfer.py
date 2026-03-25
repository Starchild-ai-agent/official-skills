#!/usr/bin/env python3
"""
Coinglass Whale Transfer Module

Provides on-chain whale transfer data including:
- Large transfers (minimum $10M) across major blockchains
- Bitcoin, Ethereum, Tron, Ripple, Dogecoin, Litecoin, Polygon, Algorand, Bitcoin Cash, Solana
- Past 6 months of data

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key

Usage Example:
    from tools.coinglass.whale_transfer import get_whale_transfers

    # Get recent whale transfers (>$10M)
    data = get_whale_transfers()
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


def get_whale_transfers() -> Optional[Dict[str, Any]]:
    """
    Get large on-chain transfers (minimum $10M) across major blockchains.

    Covers Bitcoin, Ethereum, Tron, Ripple, Dogecoin, Litecoin, Polygon,
    Algorand, Bitcoin Cash, and Solana within the past 6 months.

    Returns:
        Dictionary with whale transfers:
        {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "transaction_hash": "0x...",
                    "asset_symbol": "USDT",
                    "amount_usd": 15000000.0,
                    "asset_quantity": 15000000.0,
                    "exchange_name": "Coinbase",
                    "transfer_type": 1,  # 1=inflow, 2=outflow, 3=internal
                    "from_address": "0x...",
                    "to_address": "0x...",
                    "transaction_time": timestamp
                }
            ]
        }
    """
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/chain/v2/whale-transfer"
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
        description="Coinglass Whale Transfer Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    _ = parser.parse_args()  # noqa: F841 — parsed for --help

    result = get_whale_transfers()

    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
