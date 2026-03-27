#!/usr/bin/env python3
"""
CoinGecko NFT Tools

Tools for fetching NFT collection data including lists, details, and contract lookups.
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


def get_nfts_list(
    order: str = "market_cap_usd_desc",
    per_page: int = 100,
    page: int = 1
) -> Dict[str, Any]:
    """
    Get all NFT collections with IDs and contract addresses.

    Args:
        order: Sort order (market_cap_usd_desc, h24_volume_usd_desc, etc.)
        per_page: Results per page (max 250)
        page: Page number

    Returns:
        Dictionary with list of NFT collections
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/nfts/list"
    headers = {"x-cg-pro-api-key": api_key}
    params = {
        "order": order,
        "per_page": min(per_page, 250),
        "page": page
    }

    response = proxied_get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    nfts = []
    for nft in data:
        nfts.append({
            "id": nft.get("id", ""),
            "contract_address": nft.get("contract_address", ""),
            "name": nft.get("name", ""),
            "asset_platform_id": nft.get("asset_platform_id"),
            "symbol": nft.get("symbol", "")
        })

    return {
        "nfts": nfts,
        "count": len(nfts),
        "page": page,
        "per_page": per_page,
        "order": order
    }


def get_nft(nft_id: str) -> Dict[str, Any]:
    """
    Get NFT collection data including floor price, volume, and market cap.

    Args:
        nft_id: CoinGecko NFT collection id

    Returns:
        Dictionary with NFT collection data
    """
    api_key = get_api_key()

    url = f"https://pro-api.coingecko.com/api/v3/nfts/{nft_id}"
    headers = {"x-cg-pro-api-key": api_key}

    response = proxied_get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    return {
        "id": data.get("id", ""),
        "contract_address": data.get("contract_address", ""),
        "asset_platform_id": data.get("asset_platform_id"),
        "name": data.get("name", ""),
        "symbol": data.get("symbol", ""),
        "image": data.get("image", {}),
        "description": data.get("description"),
        "native_currency": data.get("native_currency"),
        "native_currency_symbol": data.get("native_currency_symbol"),
        "floor_price": data.get("floor_price", {}),
        "market_cap": data.get("market_cap", {}),
        "volume_24h": data.get("volume_24h", {}),
        "floor_price_in_usd_24h_percentage_change": data.get("floor_price_in_usd_24h_percentage_change"),
        "floor_price_24h_percentage_change": data.get("floor_price_24h_percentage_change", {}),
        "market_cap_24h_percentage_change": data.get("market_cap_24h_percentage_change", {}),
        "volume_24h_percentage_change": data.get("volume_24h_percentage_change", {}),
        "number_of_unique_addresses": data.get("number_of_unique_addresses"),
        "number_of_unique_addresses_24h_percentage_change": data.get("number_of_unique_addresses_24h_percentage_change"),
        "volume_in_usd_24h_percentage_change": data.get("volume_in_usd_24h_percentage_change"),
        "total_supply": data.get("total_supply"),
        "one_day_sales": data.get("one_day_sales"),
        "one_day_sales_24h_percentage_change": data.get("one_day_sales_24h_percentage_change"),
        "one_day_average_sale_price": data.get("one_day_average_sale_price"),
        "one_day_average_sale_price_24h_percentage_change": data.get("one_day_average_sale_price_24h_percentage_change"),
        "links": data.get("links", {}),
        "floor_price_7d_percentage_change": data.get("floor_price_7d_percentage_change", {}),
        "floor_price_14d_percentage_change": data.get("floor_price_14d_percentage_change", {}),
        "floor_price_30d_percentage_change": data.get("floor_price_30d_percentage_change", {}),
        "floor_price_60d_percentage_change": data.get("floor_price_60d_percentage_change", {}),
        "floor_price_1y_percentage_change": data.get("floor_price_1y_percentage_change", {}),
        "explorers": data.get("explorers", [])
    }


def get_nft_by_contract(
    asset_platform: str,
    contract_address: str
) -> Dict[str, Any]:
    """
    Get NFT collection data by contract address.

    Args:
        asset_platform: Asset platform id (e.g., ethereum, solana)
        contract_address: NFT contract address

    Returns:
        Dictionary with NFT collection data
    """
    api_key = get_api_key()

    url = f"https://pro-api.coingecko.com/api/v3/nfts/{asset_platform}/contract/{contract_address}"
    headers = {"x-cg-pro-api-key": api_key}

    response = proxied_get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    return {
        "id": data.get("id", ""),
        "contract_address": data.get("contract_address", ""),
        "asset_platform_id": data.get("asset_platform_id"),
        "name": data.get("name", ""),
        "symbol": data.get("symbol", ""),
        "image": data.get("image", {}),
        "description": data.get("description"),
        "native_currency": data.get("native_currency"),
        "native_currency_symbol": data.get("native_currency_symbol"),
        "floor_price": data.get("floor_price", {}),
        "market_cap": data.get("market_cap", {}),
        "volume_24h": data.get("volume_24h", {}),
        "floor_price_in_usd_24h_percentage_change": data.get("floor_price_in_usd_24h_percentage_change"),
        "floor_price_24h_percentage_change": data.get("floor_price_24h_percentage_change", {}),
        "market_cap_24h_percentage_change": data.get("market_cap_24h_percentage_change", {}),
        "volume_24h_percentage_change": data.get("volume_24h_percentage_change", {}),
        "number_of_unique_addresses": data.get("number_of_unique_addresses"),
        "number_of_unique_addresses_24h_percentage_change": data.get("number_of_unique_addresses_24h_percentage_change"),
        "volume_in_usd_24h_percentage_change": data.get("volume_in_usd_24h_percentage_change"),
        "total_supply": data.get("total_supply"),
        "one_day_sales": data.get("one_day_sales"),
        "one_day_sales_24h_percentage_change": data.get("one_day_sales_24h_percentage_change"),
        "one_day_average_sale_price": data.get("one_day_average_sale_price"),
        "one_day_average_sale_price_24h_percentage_change": data.get("one_day_average_sale_price_24h_percentage_change"),
        "links": data.get("links", {}),
        "floor_price_7d_percentage_change": data.get("floor_price_7d_percentage_change", {}),
        "floor_price_14d_percentage_change": data.get("floor_price_14d_percentage_change", {}),
        "floor_price_30d_percentage_change": data.get("floor_price_30d_percentage_change", {}),
        "floor_price_60d_percentage_change": data.get("floor_price_60d_percentage_change", {}),
        "floor_price_1y_percentage_change": data.get("floor_price_1y_percentage_change", {}),
        "explorers": data.get("explorers", [])
    }


def main():
    """CLI interface for NFT tools."""
    parser = argparse.ArgumentParser(
        description="CoinGecko NFT Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command")

    # List command
    list_parser = subparsers.add_parser("list", help="Get all NFT collections")
    list_parser.add_argument("--order", default="market_cap_usd_desc")
    list_parser.add_argument("--per-page", type=int, default=100)
    list_parser.add_argument("--page", type=int, default=1)

    # Get command
    get_parser = subparsers.add_parser("get", help="Get NFT collection details")
    get_parser.add_argument("nft_id", help="NFT collection ID")

    # Contract command
    contract_parser = subparsers.add_parser("contract", help="Get NFT by contract")
    contract_parser.add_argument("platform", help="Asset platform (ethereum, solana)")
    contract_parser.add_argument("address", help="Contract address")

    args = parser.parse_args()

    try:
        if args.command == "list":
            result = get_nfts_list(args.order, args.per_page, args.page)
        elif args.command == "get":
            result = get_nft(args.nft_id)
        elif args.command == "contract":
            result = get_nft_by_contract(args.platform, args.address)
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
