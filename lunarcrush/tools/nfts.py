#!/usr/bin/env python3
"""
LunarCrush NFTs API Tools

Tools for fetching NFT collections with social metrics.
"""

import json
import argparse
from typing import Dict, Any

try:
    from .utils import make_request
except ImportError:
    from utils import make_request


# MCP Tool Schemas
MCP_NFTS_SCHEMA = {
    "name": "lunar_nfts",
    "title": "LunarCrush NFT Collections",
    "description": "Get NFT collections with social metrics and Galaxy Score.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "sort": {
                "type": "string",
                "description": "Sort field",
                "default": "galaxy_score",
                "enum": ["galaxy_score", "social_volume", "floor_price", "market_cap"]
            },
            "limit": {
                "type": "integer",
                "description": "Number of results (max 100)",
                "default": 50,
                "minimum": 1,
                "maximum": 100
            }
        },
        "additionalProperties": False
    }
}

MCP_NFT_SCHEMA = {
    "name": "lunar_nft",
    "title": "LunarCrush Single NFT",
    "description": "Get detailed metrics for a single NFT collection.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "nft": {
                "type": "string",
                "description": "NFT collection slug or ID (e.g., 'bored-ape-yacht-club', 'cryptopunks')"
            }
        },
        "required": ["nft"],
        "additionalProperties": False
    }
}


def get_nfts(
    sort: str = "galaxy_score",
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get NFT collections with social metrics and Galaxy Score.

    Args:
        sort: Sort field (galaxy_score, social_volume, floor_price, market_cap)
        limit: Number of results (max 100)

    Returns:
        Dictionary with list of NFT collections
    """
    params = {
        "sort": sort,
        "limit": min(limit, 100)
    }

    data = make_request("/public/nfts/list/v2", params)

    nfts = data.get("data", [])
    formatted = []

    for nft in nfts:
        formatted.append({
            "id": nft.get("id"),
            "name": nft.get("name", ""),
            "symbol": nft.get("symbol", ""),
            "slug": nft.get("slug", ""),
            "floor_price": nft.get("floor_price"),
            "floor_price_usd": nft.get("floor_price_usd"),
            "floor_price_change_24h": nft.get("floor_price_24h_percent_change"),
            "market_cap": nft.get("market_cap"),
            "volume_24h": nft.get("volume_24h"),
            "holders": nft.get("holders"),
            "total_supply": nft.get("total_supply"),
            "galaxy_score": nft.get("galaxy_score"),
            "alt_rank": nft.get("alt_rank"),
            "social_volume": nft.get("social_volume"),
            "social_dominance": nft.get("social_dominance"),
            "sentiment": nft.get("sentiment"),
            "blockchain": nft.get("blockchain", ""),
            "categories": nft.get("categories", []),
            "image": nft.get("image", "")
        })

    return {
        "nfts": formatted,
        "count": len(formatted),
        "sort_by": sort
    }


def get_nft(nft: str) -> Dict[str, Any]:
    """
    Get detailed metrics for a single NFT collection.

    Args:
        nft: NFT collection slug or ID (e.g., 'bored-ape-yacht-club')

    Returns:
        Dictionary with NFT collection details
    """
    nft_slug = nft.lower().strip().replace(" ", "-")
    data = make_request(f"/public/nfts/{nft_slug}/v1")

    nft_data = data.get("data", {})

    return {
        "id": nft_data.get("id"),
        "name": nft_data.get("name", ""),
        "symbol": nft_data.get("symbol", ""),
        "slug": nft_data.get("slug", nft_slug),
        "description": nft_data.get("description", ""),
        "floor_price": nft_data.get("floor_price"),
        "floor_price_usd": nft_data.get("floor_price_usd"),
        "floor_price_change_24h": nft_data.get("floor_price_24h_percent_change"),
        "floor_price_change_7d": nft_data.get("floor_price_7d_percent_change"),
        "market_cap": nft_data.get("market_cap"),
        "volume_24h": nft_data.get("volume_24h"),
        "volume_7d": nft_data.get("volume_7d"),
        "sales_24h": nft_data.get("sales_24h"),
        "holders": nft_data.get("holders"),
        "total_supply": nft_data.get("total_supply"),
        "galaxy_score": nft_data.get("galaxy_score"),
        "alt_rank": nft_data.get("alt_rank"),
        "social_volume": nft_data.get("social_volume"),
        "social_volume_change_24h": nft_data.get("social_volume_24h_percent_change"),
        "social_dominance": nft_data.get("social_dominance"),
        "sentiment": nft_data.get("sentiment"),
        "tweets": nft_data.get("tweets"),
        "news_articles": nft_data.get("news"),
        "blockchain": nft_data.get("blockchain", ""),
        "contract_address": nft_data.get("contract_address", ""),
        "website": nft_data.get("website", ""),
        "twitter": nft_data.get("twitter", ""),
        "discord": nft_data.get("discord", ""),
        "opensea": nft_data.get("opensea", ""),
        "categories": nft_data.get("categories", []),
        "image": nft_data.get("image", ""),
        "banner": nft_data.get("banner", "")
    }


def main():
    """CLI interface for LunarCrush NFTs tools."""
    parser = argparse.ArgumentParser(
        description="LunarCrush NFTs API Tools",
        epilog="""
Commands:
  list  Get NFT collections with social metrics
  nft   Get single NFT collection details

Examples:
  python nfts.py list --limit 10
  python nfts.py nft --slug bored-ape-yacht-club
  python nfts.py nft --slug cryptopunks
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="Get NFT collections")
    list_parser.add_argument("--sort", default="galaxy_score",
                            choices=["galaxy_score", "social_volume", "floor_price", "market_cap"])
    list_parser.add_argument("--limit", type=int, default=50)

    # NFT command
    nft_parser = subparsers.add_parser("nft", help="Get single NFT collection")
    nft_parser.add_argument("--slug", required=True, help="NFT collection slug")

    # Schema output
    parser.add_argument("--schema", action="store_true", help="Output MCP schema")

    args = parser.parse_args()

    if args.schema:
        schemas = {
            "nfts": MCP_NFTS_SCHEMA,
            "nft": MCP_NFT_SCHEMA
        }
        print(json.dumps(schemas, indent=2))
        return 0

    try:
        if args.command == "list":
            result = get_nfts(sort=args.sort, limit=args.limit)
        elif args.command == "nft":
            result = get_nft(args.slug)
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
