#!/usr/bin/env python3
"""
CoinGecko Infrastructure Tools

Tools for fetching reference data: asset platforms, exchange rates, supported currencies, and categories list.
"""

import os
from dotenv import load_dotenv
import json
import argparse
from typing import Dict, Any, Optional, List

from core.http_client import proxied_get

# Load environment variables
load_dotenv()


def get_api_key() -> str:
    """Get CoinGecko API key from environment."""
    api_key = os.getenv("COINGECKO_API_KEY")
    if not api_key:
        raise ValueError("COINGECKO_API_KEY environment variable is required")
    return api_key


def get_asset_platforms(filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Get all blockchain networks/asset platforms.

    Args:
        filter: Filter platforms (e.g., "nft" for NFT-supporting platforms)

    Returns:
        Dictionary with list of asset platforms
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/asset_platforms"
    headers = {"x-cg-pro-api-key": api_key}
    params = {}
    if filter:
        params["filter"] = filter

    response = proxied_get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    platforms = []
    for platform in data:
        platforms.append({
            "id": platform.get("id", ""),
            "chain_identifier": platform.get("chain_identifier"),
            "name": platform.get("name", ""),
            "shortname": platform.get("shortname"),
            "native_coin_id": platform.get("native_coin_id"),
            "image": platform.get("image", {})
        })

    return {
        "platforms": platforms,
        "count": len(platforms),
        "filter": filter
    }


def get_exchange_rates() -> Dict[str, Any]:
    """
    Get BTC exchange rates to all fiat currencies.

    Returns:
        Dictionary with BTC exchange rates
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/exchange_rates"
    headers = {"x-cg-pro-api-key": api_key}

    response = proxied_get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    rates = data.get("rates", {})
    formatted_rates = {}
    for currency, info in rates.items():
        formatted_rates[currency] = {
            "name": info.get("name", ""),
            "unit": info.get("unit", ""),
            "value": info.get("value"),
            "type": info.get("type", "")
        }

    return {
        "base": "btc",
        "rates": formatted_rates,
        "count": len(formatted_rates)
    }


def get_vs_currencies() -> Dict[str, Any]:
    """
    Get list of supported quote currencies (vs_currencies).

    Returns:
        Dictionary with list of supported currencies
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/simple/supported_vs_currencies"
    headers = {"x-cg-pro-api-key": api_key}

    response = proxied_get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    return {
        "currencies": data,
        "count": len(data)
    }


def get_categories_list() -> Dict[str, Any]:
    """
    Get lightweight list of category names and IDs (no market data).

    Returns:
        Dictionary with list of categories
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/coins/categories/list"
    headers = {"x-cg-pro-api-key": api_key}

    response = proxied_get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    categories = []
    for category in data:
        categories.append({
            "category_id": category.get("category_id", ""),
            "name": category.get("name", "")
        })

    return {
        "categories": categories,
        "count": len(categories)
    }


def main():
    """CLI interface for infrastructure tools."""
    parser = argparse.ArgumentParser(
        description="CoinGecko Infrastructure Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command")

    # Asset platforms command
    platforms_parser = subparsers.add_parser("platforms", help="Get all asset platforms")
    platforms_parser.add_argument("--filter", help="Filter platforms (e.g., nft)")

    # Exchange rates command
    subparsers.add_parser("exchange-rates", help="Get BTC exchange rates")

    # Supported currencies command
    subparsers.add_parser("currencies", help="Get supported vs_currencies")

    # Categories list command
    subparsers.add_parser("categories", help="Get category names and IDs")

    args = parser.parse_args()

    try:
        if args.command == "platforms":
            result = get_asset_platforms(getattr(args, 'filter', None))
        elif args.command == "exchange-rates":
            result = get_exchange_rates()
        elif args.command == "currencies":
            result = get_vs_currencies()
        elif args.command == "categories":
            result = get_categories_list()
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
