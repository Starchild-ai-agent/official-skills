#!/usr/bin/env python3
"""
CoinGecko Global Data Tools

Tools for fetching global crypto market statistics and DeFi data.
"""

import json
import argparse
from typing import Dict, Any

from core.http_client import proxied_get
from .utils import get_api_key

# Load environment variables

# MCP Tool Schemas
MCP_GLOBAL_SCHEMA = {
    "name": "cg_global",
    "title": "CoinGecko Global Market Stats",
    "description": "Get global cryptocurrency market statistics including total market cap, volume, BTC dominance.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False
    }
}

MCP_GLOBAL_DEFI_SCHEMA = {
    "name": "cg_global_defi",
    "title": "CoinGecko Global DeFi Stats",
    "description": "Get global DeFi market statistics including TVL and DeFi dominance.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False
    }
}

def get_global(max_results: int = 100) -> Dict[str, Any]:
    """
    Get global cryptocurrency market statistics.

    Returns:
        Dictionary with market cap, volume, BTC dominance, etc.
    """
    try:
        api_key = get_api_key()

        url = "https://pro-api.coingecko.com/api/v3/global"
        headers = {"x-cg-pro-api-key": api_key}

        response = proxied_get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json().get("data", {})

        return {
            "active_cryptocurrencies": data.get("active_cryptocurrencies"),
            "upcoming_icos": data.get("upcoming_icos"),
            "ongoing_icos": data.get("ongoing_icos"),
            "ended_icos": data.get("ended_icos"),
            "markets": data.get("markets"),
            "total_market_cap": data.get("total_market_cap", {}),
            "total_volume": data.get("total_volume", {}),
            "market_cap_percentage": data.get("market_cap_percentage", {}),
            "market_cap_change_percentage_24h_usd": data.get("market_cap_change_percentage_24h_usd"),
            "updated_at": data.get("updated_at")
        }
    except Exception as e:
        return {"error": str(e)}

def get_global_defi(max_results: int = 100) -> Dict[str, Any]:
    """
    Get global DeFi market statistics.

    Returns:
        Dictionary with DeFi market cap, TVL, dominance
    """
    try:
        api_key = get_api_key()

        url = "https://pro-api.coingecko.com/api/v3/global/decentralized_finance_defi"
        headers = {"x-cg-pro-api-key": api_key}

        response = proxied_get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json().get("data", {})

        return {
            "defi_market_cap": data.get("defi_market_cap"),
            "eth_market_cap": data.get("eth_market_cap"),
            "defi_to_eth_ratio": data.get("defi_to_eth_ratio"),
            "trading_volume_24h": data.get("trading_volume_24h"),
            "defi_dominance": data.get("defi_dominance"),
            "top_coin_name": data.get("top_coin_name"),
            "top_coin_defi_dominance": data.get("top_coin_defi_dominance")
        }
    except Exception as e:
        return {"error": str(e)}

def main():
    """CLI interface for global data tools."""
    parser = argparse.ArgumentParser(
        description="CoinGecko Global Data Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command")

    # Global command
    subparsers.add_parser("global", help="Get global market stats")

    # DeFi command
    subparsers.add_parser("defi", help="Get DeFi market stats")

    parser.add_argument("--schema", action="store_true", help="Output MCP schema")

    args = parser.parse_args()

    if args.schema:
        schemas = {
            "global": MCP_GLOBAL_SCHEMA,
            "global_defi": MCP_GLOBAL_DEFI_SCHEMA
        }
        print(json.dumps(schemas, indent=2))
        return 0

    try:
        if args.command == "global":
            result = get_global()
        elif args.command == "defi":
            result = get_global_defi()
        else:
            parser.print_help()
            return 0

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return 1

if __name__ == "__main__":
    exit(main())
