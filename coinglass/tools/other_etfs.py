#!/usr/bin/env python3
"""
Coinglass Other ETFs Module

Provides ETF data for Ethereum, Solana, and XRP including:
- ETF flow history (inflows/outflows)
- ETF lists

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key

Usage Example:
    from tools.coinglass.other_etfs import get_eth_etf_flows

    # Get Ethereum ETF flow history
    data = get_eth_etf_flows()
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


# ==================== Ethereum ETF Endpoints ====================

def get_eth_etf_flows() -> Optional[Dict[str, Any]]:
    """Get Ethereum ETF flow history including daily net inflows/outflows."""
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/etf/ethereum/flow-history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def get_eth_etf_list() -> Optional[Dict[str, Any]]:
    """Get list of Ethereum ETFs with key status information."""
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/etf/ethereum/list"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


# ==================== Solana ETF Endpoints ====================

def get_sol_etf_flows() -> Optional[Dict[str, Any]]:
    """Get Solana ETF flow history including daily net inflows/outflows."""
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/etf/solana/flow-history"
    headers = {"accept": "application/json", HEADER_KEY: api_key}

    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


# ==================== XRP ETF Endpoints ====================

def get_xrp_etf_flows() -> Optional[Dict[str, Any]]:
    """Get XRP ETF flow history including daily net inflows/outflows."""
    api_key = _get_api_key()
    if not api_key:
        print("Error: COINGLASS_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/api/etf/xrp/flow-history"
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
        description="Coinglass Other ETF Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
            "--function",
            "-f",
            required=True,
            choices=["eth-flows",
                     "eth-list",
                     "sol-flows",
                     "xrp-flows"],
            help="Function to call"
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = None

    if args.function == "eth-flows":
        result = get_eth_etf_flows()
    elif args.function == "eth-list":
        result = get_eth_etf_list()
    elif args.function == "sol-flows":
        result = get_sol_etf_flows()
    elif args.function == "xrp-flows":
        result = get_xrp_etf_flows()

    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
