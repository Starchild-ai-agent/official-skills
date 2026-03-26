#!/usr/bin/env python3
"""
CoinGecko Market Discovery Tools

Tools for discovering trending coins, top movers, and newly listed coins.
"""

import os
from dotenv import load_dotenv
import json
import argparse
from typing import Dict, Any, Optional, List

from core.http_client import proxied_get

try:
    from .utils import search_coin_by_name
except ImportError:
    from utils import search_coin_by_name

# Load environment variables
load_dotenv()


# MCP Tool Schemas
MCP_TRENDING_SCHEMA = {
    "name": "cg_trending",
    "title": "CoinGecko Trending Coins",
    "description": "Get trending coins in the last 24 hours based on user search data.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False
    }
}

MCP_TOP_GAINERS_LOSERS_SCHEMA = {
    "name": "cg_top_gainers_losers",
    "title": "CoinGecko Top Gainers/Losers",
    "description": "Get top 30 gainers and losers by price change percentage.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "vs_currency": {
                "type": "string",
                "description": "Target currency for price data",
                "default": "usd"
            },
            "duration": {
                "type": "string",
                "description": "Time duration: 1h, 24h, 7d, 14d, 30d, 60d, 1y",
                "default": "24h",
                "enum": ["1h", "24h", "7d", "14d", "30d", "60d", "1y"]
            }
        },
        "additionalProperties": False
    }
}

MCP_NEW_COINS_SCHEMA = {
    "name": "cg_new_coins",
    "title": "CoinGecko Recently Added Coins",
    "description": "Get recently added coins to CoinGecko.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False
    }
}


def get_api_key() -> str:
    """Get CoinGecko API key from environment."""
    api_key = os.getenv("COINGECKO_API_KEY")
    if not api_key:
        raise ValueError("COINGECKO_API_KEY environment variable is required")
    return api_key


def get_trending(max_results: int = 100) -> Dict[str, Any]:
    try:
        """
        Get trending coins in the last 24 hours.

        Based on user search data on CoinGecko.

        Returns:
            Dictionary with trending coins, nfts, and categories
        """
        api_key = get_api_key()

        url = "https://pro-api.coingecko.com/api/v3/search/trending"
        headers = {"x-cg-pro-api-key": api_key}

        response = proxied_get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Format coins
        trending_coins = []
        for item in data.get("coins", []):
            coin = item.get("item", {})
            trending_coins.append({
                "rank": coin.get("score", 0) + 1,
                "id": coin.get("id", ""),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name", ""),
                "market_cap_rank": coin.get("market_cap_rank"),
                "price_btc": coin.get("price_btc"),
                "price_change_24h": coin.get("data", {}).get("price_change_percentage_24h", {}).get("usd"),
                "market_cap": coin.get("data", {}).get("market_cap"),
                "total_volume": coin.get("data", {}).get("total_volume"),
                "sparkline": coin.get("data", {}).get("sparkline")
            })

        # Format NFTs
        trending_nfts = []
        for nft in data.get("nfts", []):
            trending_nfts.append({
                "id": nft.get("id", ""),
                "name": nft.get("name", ""),
                "symbol": nft.get("symbol", ""),
                "floor_price_24h_change": nft.get("floor_price_24h_percentage_change")
            })

        # Format categories
        trending_categories = []
        for cat in data.get("categories", []):
            trending_categories.append({
                "id": cat.get("id"),
                "name": cat.get("name", ""),
                "market_cap_change_24h": cat.get("market_cap_1h_change")
            })

        return {
            "coins": trending_coins,
            "nfts": trending_nfts,
            "categories": trending_categories
        }
    except Exception as e:
        return {"error": str(e), "skill": "coingecko", "function": "get_trending"}


def get_top_gainers_losers(
    vs_currency: str = "usd",
    duration: str = "24h"
,
    max_results: int = 100
) -> Dict[str, Any]:
    try:
        """
        Get top 30 gainers and losers by price change percentage.

        Args:
            vs_currency: Target currency (usd, eur, btc)
            duration: Time duration (1h, 24h, 7d, 14d, 30d, 60d, 1y)

        Returns:
            Dictionary with top_gainers and top_losers lists
        """
        api_key = get_api_key()

        url = "https://pro-api.coingecko.com/api/v3/coins/top_gainers_losers"
        headers = {"x-cg-pro-api-key": api_key}
        params = {
            "vs_currency": vs_currency,
            "duration": duration
        }

        response = proxied_get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Format gainers
        gainers = []
        for coin in data.get("top_gainers", []):
            gainers.append({
                "id": coin.get("id", ""),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name", ""),
                "image": coin.get("image", ""),
                "price": coin.get(vs_currency),
                "price_change_percentage": coin.get(f"{vs_currency}_24h_change")
            })

        # Format losers
        losers = []
        for coin in data.get("top_losers", []):
            losers.append({
                "id": coin.get("id", ""),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name", ""),
                "image": coin.get("image", ""),
                "price": coin.get(vs_currency),
                "price_change_percentage": coin.get(f"{vs_currency}_24h_change")
            })

        return {
            "vs_currency": vs_currency,
            "duration": duration,
            "top_gainers": gainers,
            "top_losers": losers
        }
    except Exception as e:
        return {"error": str(e), "skill": "coingecko", "function": "get_top_gainers_losers"}


def get_new_coins(max_results: int = 100) -> Dict[str, Any]:
    try:
        """
        Get recently added coins to CoinGecko.

        Returns:
            Dictionary with list of newly added coins
        """
        api_key = get_api_key()

        url = "https://pro-api.coingecko.com/api/v3/coins/list/new"
        headers = {"x-cg-pro-api-key": api_key}

        response = proxied_get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        coins = []
        for coin in data:
            coins.append({
                "id": coin.get("id", ""),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name", ""),
                "activated_at": coin.get("activated_at")
            })

        return {
            "new_coins": coins,
            "count": len(coins)
        }
    except Exception as e:
        return {"error": str(e), "skill": "coingecko", "function": "get_new_coins"}


def main():
    """CLI interface for market discovery tools."""
    parser = argparse.ArgumentParser(
        description="CoinGecko Market Discovery Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command")

    # Trending command
    subparsers.add_parser("trending", help="Get trending coins")

    # Gainers/losers command
    gl_parser = subparsers.add_parser("gainers-losers", help="Get top gainers and losers")
    gl_parser.add_argument("--currency", default="usd")
    gl_parser.add_argument("--duration", default="24h",
                          choices=["1h", "24h", "7d", "14d", "30d", "60d", "1y"])

    # New coins command
    subparsers.add_parser("new", help="Get newly added coins")

    parser.add_argument("--schema", action="store_true", help="Output MCP schema")

    args = parser.parse_args()

    if args.schema:
        schemas = {
            "trending": MCP_TRENDING_SCHEMA,
            "top_gainers_losers": MCP_TOP_GAINERS_LOSERS_SCHEMA,
            "new_coins": MCP_NEW_COINS_SCHEMA
        }
        print(json.dumps(schemas, indent=2))
        return 0

    try:
        if args.command == "trending":
            result = get_trending()
        elif args.command == "gainers-losers":
            result = get_top_gainers_losers(args.currency, args.duration)
        elif args.command == "new":
            result = get_new_coins()
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
