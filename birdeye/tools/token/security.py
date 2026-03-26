#!/usr/bin/env python3
"""
Birdeye Token Security Module

Get token security score and analysis. Identifies rug pull risks, contract issues,
and liquidity concerns.

Usage Example:
    from tools.token.security import get_token_security

    # Check token security on Solana
    security = get_token_security(address="token_address", chain="solana")
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

BASE_URL = "https://public-api.birdeye.so"
HEADER_KEY = "X-API-KEY"
CHAINS = ["solana", "ethereum", "arbitrum", "avalanche", "bsc", "optimism", "polygon", "base", "zksync", "sui"]


def _get_api_key() -> Optional[str]:
    return os.getenv("BIRDEYE_API_KEY")


def get_token_security(address: str, chain: str = "solana", max_results: int = 100) -> Optional[Dict[str, Any]]:
    """Get token security score and analysis."""
    api_key = _get_api_key()
    if not api_key:
        print("Error: BIRDEYE_API_KEY environment variable is required", file=sys.stderr)
        return None

    if chain not in CHAINS:
        print(f"Error: Unsupported chain '{chain}'", file=sys.stderr)
        return None

    url = f"{BASE_URL}/defi/token_security"
    headers = {"accept": "application/json", HEADER_KEY: api_key, "x-chain": chain}
    params = {"address": address}

    try:
        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            print(f"API Error: {data.get('message', 'Unknown error')}", file=sys.stderr)
            return None
        return data.get("data", data)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Birdeye token security check")
    parser.add_argument("--address", "-a", required=True, help="Token address")
    parser.add_argument("--chain", "-c", default="solana", choices=CHAINS)
    parser.add_argument("--json", "-j", action="store_true")
    args = parser.parse_args()

    result = get_token_security(args.address, args.chain)
    if result and result.get("success"):
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            data = result.get("data", {})
            print(f"\nSecurity Analysis for {args.address[:8]}... on {args.chain.upper()}")
            print("=" * 60)
            print(f"Score: {data.get('security_score', 'N/A')}/100")
            print(f"Risk Level: {data.get('risk_level', 'N/A')}")
            if data.get("issues"):
                print("\nIssues Found:")
                for issue in data["issues"]:
                    print(f"  - {issue}")
    else:
        print("Failed to fetch token security")
        sys.exit(1)


if __name__ == "__main__":
    main()
