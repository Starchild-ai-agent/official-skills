#!/usr/bin/env python3
"""
CoinGecko Contract/Token Tools

Tools for fetching token data by contract address.
"""

import os
from dotenv import load_dotenv
import json
import argparse
from typing import Dict, Any, Optional

from core.http_client import proxied_get

# Load environment variables
load_dotenv()


def get_api_key() -> str:
    """Get CoinGecko API key from environment."""
    api_key = os.getenv("COINGECKO_API_KEY")
    if not api_key:
        raise ValueError("COINGECKO_API_KEY environment variable is required")
    return api_key


def get_token_price(
    platform: str,
    contract_addresses: str,
    vs_currencies: str = "usd",
    include_market_cap: bool = False,
    include_24hr_vol: bool = False,
    include_24hr_change: bool = False,
    include_last_updated_at: bool = False
,
    max_results: int = 100
) -> Dict[str, Any]:
    try:
        """
        Get token prices by contract address.

        Args:
            platform: Asset platform id (ethereum, solana, polygon-pos, etc.)
            contract_addresses: Comma-separated contract addresses
            vs_currencies: Comma-separated target currencies (usd, eur, btc)
            include_market_cap: Include market cap
            include_24hr_vol: Include 24h volume
            include_24hr_change: Include 24h price change
            include_last_updated_at: Include last updated timestamp

        Returns:
            Dictionary with token prices
        """
        api_key = get_api_key()

        url = f"https://pro-api.coingecko.com/api/v3/simple/token_price/{platform}"
        headers = {"x-cg-pro-api-key": api_key}
        params = {
            "contract_addresses": contract_addresses,
            "vs_currencies": vs_currencies,
            "include_market_cap": str(include_market_cap).lower(),
            "include_24hr_vol": str(include_24hr_vol).lower(),
            "include_24hr_change": str(include_24hr_change).lower(),
            "include_last_updated_at": str(include_last_updated_at).lower()
        }

        response = proxied_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Format response
        tokens = {}
        for address, price_data in data.items():
            tokens[address.lower()] = price_data

        return {
            "platform": platform,
            "vs_currencies": vs_currencies.split(","),
            "tokens": tokens,
            "count": len(tokens)
        }
    except Exception as e:
        return {"error": str(e), "skill": "coingecko", "function": "get_token_price"}


def get_coin_by_contract(
    platform: str,
    contract_address: str
,
    max_results: int = 100
) -> Dict[str, Any]:
    try:
        """
        Get coin data by contract address.

        Args:
            platform: Asset platform id (ethereum, solana, polygon-pos, etc.)
            contract_address: Token contract address

        Returns:
            Dictionary with coin data
        """
        api_key = get_api_key()

        url = f"https://pro-api.coingecko.com/api/v3/coins/{platform}/contract/{contract_address}"
        headers = {"x-cg-pro-api-key": api_key}

        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        result = {
            "id": data.get("id", ""),
            "symbol": data.get("symbol", "").upper(),
            "name": data.get("name", ""),
            "asset_platform_id": data.get("asset_platform_id"),
            "platforms": data.get("platforms", {}),
            "block_time_in_minutes": data.get("block_time_in_minutes"),
            "hashing_algorithm": data.get("hashing_algorithm"),
            "categories": data.get("categories", []),
            "description": data.get("description", {}).get("en", ""),
            "links": {
                "homepage": data.get("links", {}).get("homepage", []),
                "blockchain_site": data.get("links", {}).get("blockchain_site", []),
                "twitter_screen_name": data.get("links", {}).get("twitter_screen_name"),
                "telegram_channel_identifier": data.get("links", {}).get("telegram_channel_identifier"),
                "subreddit_url": data.get("links", {}).get("subreddit_url")
            },
            "image": data.get("image", {}),
            "country_origin": data.get("country_origin"),
            "genesis_date": data.get("genesis_date"),
            "contract_address": data.get("contract_address"),
            "sentiment_votes_up_percentage": data.get("sentiment_votes_up_percentage"),
            "sentiment_votes_down_percentage": data.get("sentiment_votes_down_percentage"),
            "market_cap_rank": data.get("market_cap_rank"),
            "coingecko_rank": data.get("coingecko_rank"),
            "coingecko_score": data.get("coingecko_score"),
            "developer_score": data.get("developer_score"),
            "community_score": data.get("community_score"),
            "liquidity_score": data.get("liquidity_score"),
            "public_interest_score": data.get("public_interest_score"),
            "last_updated": data.get("last_updated")
        }

        # Include market data if available
        if "market_data" in data:
            md = data["market_data"]
            result["market_data"] = {
                "current_price": md.get("current_price", {}),
                "ath": md.get("ath", {}),
                "ath_change_percentage": md.get("ath_change_percentage", {}),
                "ath_date": md.get("ath_date", {}),
                "atl": md.get("atl", {}),
                "atl_change_percentage": md.get("atl_change_percentage", {}),
                "atl_date": md.get("atl_date", {}),
                "market_cap": md.get("market_cap", {}),
                "market_cap_rank": md.get("market_cap_rank"),
                "fully_diluted_valuation": md.get("fully_diluted_valuation", {}),
                "total_volume": md.get("total_volume", {}),
                "high_24h": md.get("high_24h", {}),
                "low_24h": md.get("low_24h", {}),
                "price_change_24h": md.get("price_change_24h"),
                "price_change_percentage_24h": md.get("price_change_percentage_24h"),
                "price_change_percentage_7d": md.get("price_change_percentage_7d"),
                "price_change_percentage_14d": md.get("price_change_percentage_14d"),
                "price_change_percentage_30d": md.get("price_change_percentage_30d"),
                "price_change_percentage_60d": md.get("price_change_percentage_60d"),
                "price_change_percentage_200d": md.get("price_change_percentage_200d"),
                "price_change_percentage_1y": md.get("price_change_percentage_1y"),
                "market_cap_change_24h": md.get("market_cap_change_24h"),
                "market_cap_change_percentage_24h": md.get("market_cap_change_percentage_24h"),
                "total_supply": md.get("total_supply"),
                "max_supply": md.get("max_supply"),
                "circulating_supply": md.get("circulating_supply")
            }

        return {"data": result}
    except Exception as e:
        return {"error": str(e), "skill": "coingecko", "function": "get_coin_by_contract"}


def main():
    """CLI interface for contract tools."""
    parser = argparse.ArgumentParser(
        description="CoinGecko Contract/Token Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command")

    # Token price command
    price_parser = subparsers.add_parser("price", help="Get token price by contract")
    price_parser.add_argument("platform", help="Asset platform (ethereum, solana, etc.)")
    price_parser.add_argument("addresses", help="Contract addresses (comma-separated)")
    price_parser.add_argument("--currencies", default="usd", help="Target currencies")
    price_parser.add_argument("--market-cap", action="store_true", help="Include market cap")
    price_parser.add_argument("--volume", action="store_true", help="Include 24h volume")
    price_parser.add_argument("--change", action="store_true", help="Include 24h change")

    # Coin data command
    data_parser = subparsers.add_parser("data", help="Get coin data by contract")
    data_parser.add_argument("platform", help="Asset platform (ethereum, solana, etc.)")
    data_parser.add_argument("address", help="Contract address")

    args = parser.parse_args()

    try:
        if args.command == "price":
            result = get_token_price(
                platform=args.platform,
                contract_addresses=args.addresses,
                vs_currencies=args.currencies,
                include_market_cap=args.market_cap,
                include_24hr_vol=args.volume,
                include_24hr_change=args.change
            )
        elif args.command == "data":
            result = get_coin_by_contract(args.platform, args.address)
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
