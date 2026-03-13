#!/usr/bin/env python3
"""
CoinGecko Search Tools

Tools for searching coins, exchanges, categories, and NFTs.
"""

import os
from dotenv import load_dotenv
import json
import argparse
from typing import Dict, Any

from core.http_client import proxied_get

# Load environment variables
load_dotenv()


def get_api_key() -> str:
    """Get CoinGecko API key from environment."""
    api_key = os.getenv("COINGECKO_API_KEY")
    if not api_key:
        raise ValueError("COINGECKO_API_KEY environment variable is required")
    return api_key


def search(query: str) -> Dict[str, Any]:
    """
    Search for coins, exchanges, categories, and NFTs.

    Args:
        query: Search query string

    Returns:
        Dictionary with search results across all categories
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/search"
    headers = {"x-cg-pro-api-key": api_key}
    params = {"query": query}

    response = proxied_get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Format coins
    coins = []
    for coin in data.get("coins", []):
        coins.append({
            "id": coin.get("id", ""),
            "name": coin.get("name", ""),
            "api_symbol": coin.get("api_symbol", ""),
            "symbol": coin.get("symbol", "").upper(),
            "market_cap_rank": coin.get("market_cap_rank"),
            "thumb": coin.get("thumb"),
            "large": coin.get("large")
        })

    # Format exchanges
    exchanges = []
    for exchange in data.get("exchanges", []):
        exchanges.append({
            "id": exchange.get("id", ""),
            "name": exchange.get("name", ""),
            "market_type": exchange.get("market_type"),
            "thumb": exchange.get("thumb"),
            "large": exchange.get("large")
        })

    # Format categories
    categories = []
    for category in data.get("categories", []):
        categories.append({
            "id": category.get("id"),
            "name": category.get("name", "")
        })

    # Format NFTs
    nfts = []
    for nft in data.get("nfts", []):
        nfts.append({
            "id": nft.get("id", ""),
            "name": nft.get("name", ""),
            "symbol": nft.get("symbol", ""),
            "thumb": nft.get("thumb")
        })

    # Format ICOs (if present)
    icos = data.get("icos", [])

    return {
        "query": query,
        "coins": coins,
        "coins_count": len(coins),
        "exchanges": exchanges,
        "exchanges_count": len(exchanges),
        "categories": categories,
        "categories_count": len(categories),
        "nfts": nfts,
        "nfts_count": len(nfts),
        "icos": icos,
        "icos_count": len(icos)
    }


def main():
    """CLI interface for search tools."""
    parser = argparse.ArgumentParser(
        description="CoinGecko Search Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("query", help="Search query")

    args = parser.parse_args()

    try:
        result = search(args.query)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    exit(main())
