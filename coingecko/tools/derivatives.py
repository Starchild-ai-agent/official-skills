#!/usr/bin/env python3
"""
CoinGecko Derivatives Tools

Tools for fetching derivatives market data including tickers and exchanges.
"""

import os
from dotenv import load_dotenv
import json
import argparse
from typing import Dict, Any, Optional

from core.http_client import proxied_get

# Load environment variables
load_dotenv()


# MCP Tool Schemas
MCP_DERIVATIVES_SCHEMA = {
    "name": "cg_derivatives",
    "title": "CoinGecko Derivatives Tickers",
    "description": "Get all derivatives tickers (perpetuals, futures).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "include_tickers": {
                "type": "string",
                "description": "Filter: all, unexpired (default)",
                "default": "unexpired",
                "enum": ["all", "unexpired"]
            }
        },
        "additionalProperties": False
    }
}

MCP_DERIVATIVES_EXCHANGES_SCHEMA = {
    "name": "cg_derivatives_exchanges",
    "title": "CoinGecko Derivatives Exchanges",
    "description": "Get list of derivatives exchanges with ranking.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "order": {
                "type": "string",
                "description": "Sort by: name_asc, name_desc, open_interest_btc_asc, open_interest_btc_desc, trade_volume_24h_btc_asc, trade_volume_24h_btc_desc",
                "default": "open_interest_btc_desc"
            },
            "per_page": {
                "type": "integer",
                "description": "Results per page (max 100)",
                "default": 50,
                "minimum": 1,
                "maximum": 100
            }
        },
        "additionalProperties": False
    }
}

MCP_CATEGORIES_SCHEMA = {
    "name": "cg_categories",
    "title": "CoinGecko Coin Categories",
    "description": "Get coin categories with market data (DeFi, L1, L2, Memes, etc.).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "order": {
                "type": "string",
                "description": "Sort by: market_cap_desc, market_cap_asc, name_desc, name_asc, market_cap_change_24h_desc, market_cap_change_24h_asc",
                "default": "market_cap_desc"
            }
        },
        "additionalProperties": False
    }
}


def get_api_key() -> str:
    """Get CoinGecko API key from environment."""
    api_key = os.getenv("COINGECKO_API_KEY")
    if not api_key:
        raise ValueError("COINGECKO_API_KEY environment variable is required")
    return api_key


def get_derivatives(include_tickers: str = "unexpired") -> Dict[str, Any]:
    """
    Get all derivatives tickers.

    Args:
        include_tickers: Filter - all or unexpired

    Returns:
        Dictionary with derivatives tickers
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/derivatives"
    headers = {"x-cg-pro-api-key": api_key}
    params = {"include_tickers": include_tickers}

    response = proxied_get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    tickers = []
    for item in data:
        tickers.append({
            "market": item.get("market", ""),
            "symbol": item.get("symbol", ""),
            "index_id": item.get("index_id"),
            "price": item.get("price"),
            "price_percentage_change_24h": item.get("price_percentage_change_24h"),
            "contract_type": item.get("contract_type"),
            "index": item.get("index"),
            "basis": item.get("basis"),
            "spread": item.get("spread"),
            "funding_rate": item.get("funding_rate"),
            "open_interest": item.get("open_interest"),
            "volume_24h": item.get("volume_24h"),
            "last_traded_at": item.get("last_traded_at"),
            "expired_at": item.get("expired_at")
        })

    return {
        "tickers": tickers,
        "count": len(tickers),
        "filter": include_tickers
    }


def get_derivatives_exchanges(
    order: str = "open_interest_btc_desc",
    per_page: int = 50
) -> Dict[str, Any]:
    """
    Get list of derivatives exchanges with ranking.

    Args:
        order: Sort order
        per_page: Results per page (max 100)

    Returns:
        Dictionary with derivatives exchanges
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/derivatives/exchanges"
    headers = {"x-cg-pro-api-key": api_key}
    params = {
        "order": order,
        "per_page": min(per_page, 100)
    }

    response = proxied_get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    exchanges = []
    for item in data:
        exchanges.append({
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "open_interest_btc": item.get("open_interest_btc"),
            "trade_volume_24h_btc": item.get("trade_volume_24h_btc"),
            "number_of_perpetual_pairs": item.get("number_of_perpetual_pairs"),
            "number_of_futures_pairs": item.get("number_of_futures_pairs"),
            "image": item.get("image"),
            "year_established": item.get("year_established"),
            "country": item.get("country"),
            "url": item.get("url")
        })

    return {
        "exchanges": exchanges,
        "count": len(exchanges),
        "order": order
    }


def get_categories(order: str = "market_cap_desc") -> Dict[str, Any]:
    """
    Get coin categories with market data.

    Args:
        order: Sort order (market_cap_desc, market_cap_change_24h_desc, etc.)

    Returns:
        Dictionary with coin categories
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/coins/categories"
    headers = {"x-cg-pro-api-key": api_key}
    params = {"order": order}

    response = proxied_get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    categories = []
    for item in data:
        categories.append({
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "market_cap": item.get("market_cap"),
            "market_cap_change_24h": item.get("market_cap_change_24h"),
            "content": item.get("content"),
            "top_3_coins": item.get("top_3_coins", []),
            "volume_24h": item.get("volume_24h"),
            "updated_at": item.get("updated_at")
        })

    return {
        "categories": categories,
        "count": len(categories),
        "order": order
    }


def main():
    """CLI interface for derivatives tools."""
    parser = argparse.ArgumentParser(
        description="CoinGecko Derivatives Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command")

    # Derivatives tickers command
    deriv_parser = subparsers.add_parser("derivatives", help="Get derivatives tickers")
    deriv_parser.add_argument("--filter", default="unexpired", choices=["all", "unexpired"])

    # Exchanges command
    exch_parser = subparsers.add_parser("exchanges", help="Get derivatives exchanges")
    exch_parser.add_argument("--order", default="open_interest_btc_desc")
    exch_parser.add_argument("--limit", type=int, default=50)

    # Categories command
    cat_parser = subparsers.add_parser("categories", help="Get coin categories")
    cat_parser.add_argument("--order", default="market_cap_desc")

    parser.add_argument("--schema", action="store_true", help="Output MCP schema")

    args = parser.parse_args()

    if args.schema:
        schemas = {
            "derivatives": MCP_DERIVATIVES_SCHEMA,
            "derivatives_exchanges": MCP_DERIVATIVES_EXCHANGES_SCHEMA,
            "categories": MCP_CATEGORIES_SCHEMA
        }
        print(json.dumps(schemas, indent=2))
        return 0

    try:
        if args.command == "derivatives":
            result = get_derivatives(args.filter)
        elif args.command == "exchanges":
            result = get_derivatives_exchanges(args.order, args.limit)
        elif args.command == "categories":
            result = get_categories(args.order)
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
