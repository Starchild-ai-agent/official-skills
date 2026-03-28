#!/usr/bin/env python3
"""
CoinGecko Coins Tools

Tools for fetching coin lists, market data, detailed coin info, and tickers.
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


def get_coins_list(include_platform: bool = False) -> Dict[str, Any]:
    """
    Get all supported coins with id, symbol, name.

    Args:
        include_platform: Include platform contract addresses

    Returns:
        Dictionary with list of all coins
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/coins/list"
    headers = {"x-cg-pro-api-key": api_key}
    params = {"include_platform": str(include_platform).lower()}

    response = proxied_get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    coins = []
    for coin in data:
        coin_data = {
            "id": coin.get("id", ""),
            "symbol": coin.get("symbol", "").upper(),
            "name": coin.get("name", "")
        }
        if include_platform and "platforms" in coin:
            coin_data["platforms"] = coin.get("platforms", {})
        coins.append(coin_data)

    return {
        "coins": coins,
        "count": len(coins)
    }


def get_coins_markets(
    vs_currency: str = "usd",
    order: str = "market_cap_desc",
    per_page: int = 100,
    page: int = 1,
    sparkline: bool = False,
    price_change_percentage: str = "24h",
    category: Optional[str] = None,
    ids: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get market data for coins with sorting and pagination.

    Args:
        vs_currency: Target currency (usd, eur, btc)
        order: Sort order (market_cap_desc, volume_desc, price_change_24h_desc)
        per_page: Results per page (max 250)
        page: Page number
        sparkline: Include 7-day sparkline data
        price_change_percentage: Comma-separated time periods (1h, 24h, 7d, 14d, 30d, 200d, 1y)
        category: Filter by category id
        ids: Comma-separated coin ids to filter

    Returns:
        Dictionary with market data for coins
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/coins/markets"
    headers = {"x-cg-pro-api-key": api_key}
    params = {
        "vs_currency": vs_currency,
        "order": order,
        "per_page": min(per_page, 250),
        "page": page,
        "sparkline": str(sparkline).lower(),
        "price_change_percentage": price_change_percentage
    }
    if category:
        params["category"] = category
    if ids:
        params["ids"] = ids

    response = proxied_get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    coins = []
    for coin in data:
        coin_data = {
            "id": coin.get("id", ""),
            "symbol": coin.get("symbol", "").upper(),
            "name": coin.get("name", ""),
            "image": coin.get("image"),
            "current_price": coin.get("current_price"),
            "market_cap": coin.get("market_cap"),
            "market_cap_rank": coin.get("market_cap_rank"),
            "fully_diluted_valuation": coin.get("fully_diluted_valuation"),
            "total_volume": coin.get("total_volume"),
            "high_24h": coin.get("high_24h"),
            "low_24h": coin.get("low_24h"),
            "price_change_24h": coin.get("price_change_24h"),
            "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
            "market_cap_change_24h": coin.get("market_cap_change_24h"),
            "market_cap_change_percentage_24h": coin.get("market_cap_change_percentage_24h"),
            "circulating_supply": coin.get("circulating_supply"),
            "total_supply": coin.get("total_supply"),
            "max_supply": coin.get("max_supply"),
            "ath": coin.get("ath"),
            "ath_change_percentage": coin.get("ath_change_percentage"),
            "ath_date": coin.get("ath_date"),
            "atl": coin.get("atl"),
            "atl_change_percentage": coin.get("atl_change_percentage"),
            "atl_date": coin.get("atl_date"),
            "last_updated": coin.get("last_updated")
        }
        # Add price change percentages if available
        for key in coin:
            if key.startswith("price_change_percentage_"):
                coin_data[key] = coin.get(key)
        if sparkline and "sparkline_in_7d" in coin:
            coin_data["sparkline_in_7d"] = coin.get("sparkline_in_7d")
        coins.append(coin_data)

    return {
        "coins": coins,
        "count": len(coins),
        "vs_currency": vs_currency,
        "order": order,
        "page": page,
        "per_page": per_page
    }


def get_coin_data(
    coin_id: str,
    localization: bool = False,
    tickers: bool = False,
    market_data: bool = True,
    community_data: bool = False,
    developer_data: bool = False,
    sparkline: bool = False
) -> Dict[str, Any]:
    """
    Get full coin metadata including description, links, ATH, ATL, market data.

    Args:
        coin_id: CoinGecko coin id
        localization: Include localized languages
        tickers: Include tickers data
        market_data: Include market data
        community_data: Include community data
        developer_data: Include developer data
        sparkline: Include sparkline 7 days data

    Returns:
        Dictionary with comprehensive coin data
    """
    api_key = get_api_key()

    url = f"https://pro-api.coingecko.com/api/v3/coins/{coin_id}"
    headers = {"x-cg-pro-api-key": api_key}
    params = {
        "localization": str(localization).lower(),
        "tickers": str(tickers).lower(),
        "market_data": str(market_data).lower(),
        "community_data": str(community_data).lower(),
        "developer_data": str(developer_data).lower(),
        "sparkline": str(sparkline).lower()
    }

    response = proxied_get(url, headers=headers, params=params, timeout=30)
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
            "official_forum_url": data.get("links", {}).get("official_forum_url", []),
            "chat_url": data.get("links", {}).get("chat_url", []),
            "announcement_url": data.get("links", {}).get("announcement_url", []),
            "twitter_screen_name": data.get("links", {}).get("twitter_screen_name"),
            "facebook_username": data.get("links", {}).get("facebook_username"),
            "telegram_channel_identifier": data.get("links", {}).get("telegram_channel_identifier"),
            "subreddit_url": data.get("links", {}).get("subreddit_url"),
            "repos_url": data.get("links", {}).get("repos_url", {})
        },
        "image": data.get("image", {}),
        "country_origin": data.get("country_origin"),
        "genesis_date": data.get("genesis_date"),
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

    if market_data and "market_data" in data:
        md = data["market_data"]
        result["market_data"] = {
            "current_price": md.get("current_price", {}),
            "total_value_locked": md.get("total_value_locked"),
            "mcap_to_tvl_ratio": md.get("mcap_to_tvl_ratio"),
            "fdv_to_tvl_ratio": md.get("fdv_to_tvl_ratio"),
            "roi": md.get("roi"),
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

    if tickers and "tickers" in data:
        result["tickers"] = data["tickers"]

    if community_data and "community_data" in data:
        result["community_data"] = data["community_data"]

    if developer_data and "developer_data" in data:
        result["developer_data"] = data["developer_data"]

    return result


def get_coin_tickers(
    coin_id: str,
    exchange_ids: Optional[str] = None,
    include_exchange_logo: bool = False,
    page: int = 1,
    order: str = "volume_desc",
    depth: bool = False
) -> Dict[str, Any]:
    """
    Get all trading pairs/tickers for a coin across exchanges.

    Args:
        coin_id: CoinGecko coin id
        exchange_ids: Comma-separated exchange ids to filter
        include_exchange_logo: Include exchange logo
        page: Page number
        order: Sort order (trust_score_desc, trust_score_asc, volume_desc, volume_asc)
        depth: Include order book depth (cost_to_move_up_usd, cost_to_move_down_usd)

    Returns:
        Dictionary with tickers for the coin
    """
    api_key = get_api_key()

    url = f"https://pro-api.coingecko.com/api/v3/coins/{coin_id}/tickers"
    headers = {"x-cg-pro-api-key": api_key}
    params = {
        "include_exchange_logo": str(include_exchange_logo).lower(),
        "page": page,
        "order": order,
        "depth": str(depth).lower()
    }
    if exchange_ids:
        params["exchange_ids"] = exchange_ids

    response = proxied_get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    tickers = []
    for ticker in data.get("tickers", []):
        ticker_data = {
            "base": ticker.get("base", ""),
            "target": ticker.get("target", ""),
            "market": {
                "name": ticker.get("market", {}).get("name", ""),
                "identifier": ticker.get("market", {}).get("identifier", ""),
                "has_trading_incentive": ticker.get("market", {}).get("has_trading_incentive")
            },
            "last": ticker.get("last"),
            "volume": ticker.get("volume"),
            "converted_last": ticker.get("converted_last", {}),
            "converted_volume": ticker.get("converted_volume", {}),
            "trust_score": ticker.get("trust_score"),
            "bid_ask_spread_percentage": ticker.get("bid_ask_spread_percentage"),
            "timestamp": ticker.get("timestamp"),
            "last_traded_at": ticker.get("last_traded_at"),
            "last_fetch_at": ticker.get("last_fetch_at"),
            "is_anomaly": ticker.get("is_anomaly"),
            "is_stale": ticker.get("is_stale"),
            "trade_url": ticker.get("trade_url"),
            "token_info_url": ticker.get("token_info_url"),
            "coin_id": ticker.get("coin_id"),
            "target_coin_id": ticker.get("target_coin_id")
        }
        if include_exchange_logo:
            ticker_data["market"]["logo"] = ticker.get("market", {}).get("logo")
        if depth:
            ticker_data["cost_to_move_up_usd"] = ticker.get("cost_to_move_up_usd")
            ticker_data["cost_to_move_down_usd"] = ticker.get("cost_to_move_down_usd")
        tickers.append(ticker_data)

    return {
        "name": data.get("name", ""),
        "tickers": tickers,
        "count": len(tickers),
        "page": page
    }


def main():
    """CLI interface for coins tools."""
    parser = argparse.ArgumentParser(
        description="CoinGecko Coins Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command")

    # List command
    list_parser = subparsers.add_parser("list", help="Get all supported coins")
    list_parser.add_argument("--platforms", action="store_true", help="Include platform addresses")

    # Markets command
    markets_parser = subparsers.add_parser("markets", help="Get market data for coins")
    markets_parser.add_argument("--currency", default="usd")
    markets_parser.add_argument("--order", default="market_cap_desc")
    markets_parser.add_argument("--per-page", type=int, default=100)
    markets_parser.add_argument("--page", type=int, default=1)
    markets_parser.add_argument("--category", help="Filter by category")
    markets_parser.add_argument("--ids", help="Filter by coin ids (comma-separated)")

    # Data command
    data_parser = subparsers.add_parser("data", help="Get detailed coin data")
    data_parser.add_argument("coin_id", help="CoinGecko coin ID")
    data_parser.add_argument("--tickers", action="store_true", help="Include tickers")
    data_parser.add_argument("--community", action="store_true", help="Include community data")
    data_parser.add_argument("--developer", action="store_true", help="Include developer data")

    # Tickers command
    tickers_parser = subparsers.add_parser("tickers", help="Get coin tickers")
    tickers_parser.add_argument("coin_id", help="CoinGecko coin ID")
    tickers_parser.add_argument("--exchanges", help="Filter by exchange ids")
    tickers_parser.add_argument("--page", type=int, default=1)
    tickers_parser.add_argument("--order", default="volume_desc")

    args = parser.parse_args()

    try:
        if args.command == "list":
            result = get_coins_list(args.platforms)
        elif args.command == "markets":
            result = get_coins_markets(
                vs_currency=args.currency,
                order=args.order,
                per_page=args.per_page,
                page=args.page,
                category=args.category,
                ids=args.ids
            )
        elif args.command == "data":
            result = get_coin_data(
                coin_id=args.coin_id,
                tickers=args.tickers,
                community_data=args.community,
                developer_data=args.developer
            )
        elif args.command == "tickers":
            result = get_coin_tickers(
                coin_id=args.coin_id,
                exchange_ids=args.exchanges,
                page=args.page,
                order=args.order
            )
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
