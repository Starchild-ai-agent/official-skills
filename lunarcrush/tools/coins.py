#!/usr/bin/env python3
"""
LunarCrush Coins API Tools

Tools for fetching coin metrics, time series, and metadata from LunarCrush.
Provides Galaxy Score, AltRank, and social sentiment data.
"""

import json
import argparse
from typing import Dict, Any

try:
    from .utils import make_request, normalize_symbol, parse_time_series_bucket
except ImportError:
    from utils import make_request, normalize_symbol, parse_time_series_bucket


# MCP Tool Schemas
MCP_COINS_LIST_SCHEMA = {
    "name": "lunar_coins_list",
    "title": "LunarCrush Trending Coins",
    "description": "Get trending coins with Galaxy Score, AltRank, and social metrics.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "sort": {
                "type": "string",
                "description": "Sort field (galaxy_score, alt_rank, market_cap, volume)",
                "default": "galaxy_score",
                "enum": ["galaxy_score", "alt_rank", "market_cap", "volume", "social_volume"]
            },
            "limit": {
                "type": "integer",
                "description": "Number of results (max 100)",
                "default": 50,
                "minimum": 1,
                "maximum": 100
            },
            "desc": {
                "type": "boolean",
                "description": "Sort descending",
                "default": True
            }
        },
        "additionalProperties": False
    }
}

MCP_COIN_SCHEMA = {
    "name": "lunar_coin",
    "title": "LunarCrush Single Coin",
    "description": "Get detailed metrics for a single coin including Galaxy Score, AltRank, sentiment.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "coin": {
                "type": "string",
                "description": "Coin symbol (e.g., BTC, ETH, SOL)"
            }
        },
        "required": ["coin"],
        "additionalProperties": False
    }
}

MCP_COIN_TIME_SERIES_SCHEMA = {
    "name": "lunar_coin_time_series",
    "title": "LunarCrush Coin Time Series",
    "description": "Get historical social + market data for a coin.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "coin": {
                "type": "string",
                "description": "Coin symbol (e.g., BTC, ETH)"
            },
            "bucket": {
                "type": "string",
                "description": "Time bucket: hour, day, week",
                "default": "day",
                "enum": ["hour", "day", "week"]
            },
            "interval": {
                "type": "string",
                "description": "Time interval: 1w, 1m, 3m, 6m, 1y, all",
                "default": "1m",
                "enum": ["1w", "1m", "3m", "6m", "1y", "all"]
            }
        },
        "required": ["coin"],
        "additionalProperties": False
    }
}

MCP_COIN_META_SCHEMA = {
    "name": "lunar_coin_meta",
    "title": "LunarCrush Coin Metadata",
    "description": "Get coin metadata including links, description, social accounts.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "coin": {
                "type": "string",
                "description": "Coin symbol (e.g., BTC, ETH)"
            }
        },
        "required": ["coin"],
        "additionalProperties": False
    }
}


def get_coins_list(
    sort: str = "galaxy_score",
    limit: int = 50,
    desc: bool = True
) -> Dict[str, Any]:
    """
    Get trending coins with Galaxy Score and social metrics.

    Args:
        sort: Sort field (galaxy_score, alt_rank, market_cap, volume, social_volume)
        limit: Number of results (max 100)
        desc: Sort descending

    Returns:
        Dictionary with list of coins and their metrics
    """
    params = {
        "sort": sort,
        "limit": min(limit, 100),
        "desc": str(desc).lower()
    }

    data = make_request("/public/coins/list/v2", params)

    # Extract and format coin data
    coins = data.get("data", [])
    formatted = []

    for coin in coins:
        formatted.append({
            "symbol": coin.get("symbol", ""),
            "name": coin.get("name", ""),
            "price": coin.get("price"),
            "price_change_24h": coin.get("percent_change_24h"),
            "market_cap": coin.get("market_cap"),
            "galaxy_score": coin.get("galaxy_score"),
            "alt_rank": coin.get("alt_rank"),
            "social_volume": coin.get("social_volume"),
            "social_dominance": coin.get("social_dominance"),
            "sentiment": coin.get("sentiment"),
            "categories": coin.get("categories", [])
        })

    return {
        "coins": formatted,
        "count": len(formatted),
        "sort_by": sort,
        "sort_desc": desc
    }


def get_coin(coin: str) -> Dict[str, Any]:
    """
    Get detailed metrics for a single coin.

    Args:
        coin: Coin symbol (e.g., BTC, ETH, SOL)

    Returns:
        Dictionary with coin metrics including Galaxy Score, AltRank, sentiment
    """
    symbol = normalize_symbol(coin)
    data = make_request(f"/public/coins/{symbol}/v1")

    coin_data = data.get("data", {})

    return {
        "symbol": coin_data.get("symbol", symbol),
        "name": coin_data.get("name", ""),
        "price": coin_data.get("price"),
        "price_change_24h": coin_data.get("percent_change_24h"),
        "price_change_7d": coin_data.get("percent_change_7d"),
        "market_cap": coin_data.get("market_cap"),
        "volume_24h": coin_data.get("volume_24h"),
        "galaxy_score": coin_data.get("galaxy_score"),
        "alt_rank": coin_data.get("alt_rank"),
        "social_volume": coin_data.get("social_volume"),
        "social_volume_change_24h": coin_data.get("social_volume_24h_percent_change"),
        "social_dominance": coin_data.get("social_dominance"),
        "sentiment": coin_data.get("sentiment"),
        "social_contributors": coin_data.get("social_contributors"),
        "news_articles": coin_data.get("news"),
        "tweets": coin_data.get("tweets"),
        "categories": coin_data.get("categories", []),
        "timeSeries": coin_data.get("timeSeries")
    }


def get_coin_time_series(
    coin: str,
    bucket: str = "day",
    interval: str = "1m"
) -> Dict[str, Any]:
    """
    Get historical social and market data for a coin.

    Args:
        coin: Coin symbol (e.g., BTC, ETH)
        bucket: Time bucket (hour, day, week)
        interval: Time interval (1w, 1m, 3m, 6m, 1y, all)

    Returns:
        Dictionary with time series data
    """
    symbol = normalize_symbol(coin)
    bucket = parse_time_series_bucket(bucket)

    params = {
        "bucket": bucket,
        "interval": interval
    }

    data = make_request(f"/public/coins/{symbol}/time-series/v2", params)

    time_series = data.get("data", [])

    # Format time series data
    formatted = []
    for point in time_series:
        formatted.append({
            "time": point.get("time"),
            "open": point.get("open"),
            "high": point.get("high"),
            "low": point.get("low"),
            "close": point.get("close"),
            "volume": point.get("volume"),
            "market_cap": point.get("market_cap"),
            "galaxy_score": point.get("galaxy_score"),
            "alt_rank": point.get("alt_rank"),
            "sentiment": point.get("sentiment"),
            "social_volume": point.get("social_volume"),
            "social_dominance": point.get("social_dominance"),
            "tweets": point.get("tweets"),
            "news": point.get("news")
        })

    return {
        "symbol": symbol,
        "bucket": bucket,
        "interval": interval,
        "data_points": len(formatted),
        "time_series": formatted
    }


def get_coin_meta(coin: str) -> Dict[str, Any]:
    """
    Get coin metadata including links, description, social accounts.

    Args:
        coin: Coin symbol (e.g., BTC, ETH)

    Returns:
        Dictionary with coin metadata
    """
    symbol = normalize_symbol(coin)
    data = make_request(f"/public/coins/{symbol}/meta/v1")

    meta = data.get("data", {})

    return {
        "symbol": meta.get("symbol", symbol),
        "name": meta.get("name", ""),
        "description": meta.get("description", ""),
        "website": meta.get("website"),
        "whitepaper": meta.get("whitepaper"),
        "twitter": meta.get("twitter"),
        "telegram": meta.get("telegram"),
        "discord": meta.get("discord"),
        "reddit": meta.get("reddit"),
        "github": meta.get("github"),
        "medium": meta.get("medium"),
        "youtube": meta.get("youtube"),
        "blockchain": meta.get("blockchain"),
        "contract_address": meta.get("contract_address"),
        "categories": meta.get("categories", []),
        "logo": meta.get("logo")
    }


def main():
    """CLI interface for LunarCrush coins tools."""
    parser = argparse.ArgumentParser(
        description="LunarCrush Coins API Tools",
        epilog="""
Commands:
  list     Get trending coins with Galaxy Score
  coin     Get single coin metrics
  series   Get coin time series data
  meta     Get coin metadata

Examples:
  python coins.py list --limit 10
  python coins.py coin --symbol BTC
  python coins.py series --symbol ETH --bucket day --interval 1m
  python coins.py meta --symbol SOL
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="Get trending coins")
    list_parser.add_argument("--sort", default="galaxy_score",
                            choices=["galaxy_score", "alt_rank", "market_cap", "volume", "social_volume"])
    list_parser.add_argument("--limit", type=int, default=50)
    list_parser.add_argument("--asc", action="store_true", help="Sort ascending")

    # Coin command
    coin_parser = subparsers.add_parser("coin", help="Get single coin metrics")
    coin_parser.add_argument("--symbol", required=True, help="Coin symbol (BTC, ETH)")

    # Time series command
    series_parser = subparsers.add_parser("series", help="Get coin time series")
    series_parser.add_argument("--symbol", required=True, help="Coin symbol")
    series_parser.add_argument("--bucket", default="day", choices=["hour", "day", "week"])
    series_parser.add_argument("--interval", default="1m", choices=["1w", "1m", "3m", "6m", "1y", "all"])

    # Meta command
    meta_parser = subparsers.add_parser("meta", help="Get coin metadata")
    meta_parser.add_argument("--symbol", required=True, help="Coin symbol")

    # Schema output
    parser.add_argument("--schema", action="store_true", help="Output MCP schema")

    args = parser.parse_args()

    if args.schema:
        schemas = {
            "coins_list": MCP_COINS_LIST_SCHEMA,
            "coin": MCP_COIN_SCHEMA,
            "time_series": MCP_COIN_TIME_SERIES_SCHEMA,
            "meta": MCP_COIN_META_SCHEMA
        }
        print(json.dumps(schemas, indent=2))
        return 0

    try:
        if args.command == "list":
            result = get_coins_list(sort=args.sort, limit=args.limit, desc=not args.asc)
        elif args.command == "coin":
            result = get_coin(args.symbol)
        elif args.command == "series":
            result = get_coin_time_series(args.symbol, args.bucket, args.interval)
        elif args.command == "meta":
            result = get_coin_meta(args.symbol)
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
