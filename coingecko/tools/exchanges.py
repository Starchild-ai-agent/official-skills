#!/usr/bin/env python3
"""
CoinGecko Exchanges Tools

Tools for fetching spot exchange data, tickers, and volume history.
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


def get_exchanges(
    per_page: int = 100,
    page: int = 1
) -> Dict[str, Any]:
    """
    Get all spot exchanges with volumes and trust scores.

    Args:
        per_page: Results per page (max 250)
        page: Page number

    Returns:
        Dictionary with list of exchanges
    """
    api_key = get_api_key()

    url = "https://pro-api.coingecko.com/api/v3/exchanges"
    headers = {"x-cg-pro-api-key": api_key}
    params = {
        "per_page": min(per_page, 250),
        "page": page
    }

    response = proxied_get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    exchanges = []
    for exchange in data:
        exchanges.append({
            "id": exchange.get("id", ""),
            "name": exchange.get("name", ""),
            "year_established": exchange.get("year_established"),
            "country": exchange.get("country"),
            "description": exchange.get("description"),
            "url": exchange.get("url"),
            "image": exchange.get("image"),
            "has_trading_incentive": exchange.get("has_trading_incentive"),
            "trust_score": exchange.get("trust_score"),
            "trust_score_rank": exchange.get("trust_score_rank"),
            "trade_volume_24h_btc": exchange.get("trade_volume_24h_btc"),
            "trade_volume_24h_btc_normalized": exchange.get("trade_volume_24h_btc_normalized")
        })

    return {
        "exchanges": exchanges,
        "count": len(exchanges),
        "page": page,
        "per_page": per_page
    }


def get_exchange(exchange_id: str) -> Dict[str, Any]:
    """
    Get detailed exchange data including tickers and BTC volume.

    Args:
        exchange_id: CoinGecko exchange id (e.g., binance, coinbase-exchange)

    Returns:
        Dictionary with detailed exchange data
    """
    api_key = get_api_key()

    url = f"https://pro-api.coingecko.com/api/v3/exchanges/{exchange_id}"
    headers = {"x-cg-pro-api-key": api_key}

    response = proxied_get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    result = {
        "id": data.get("id", ""),
        "name": data.get("name", ""),
        "year_established": data.get("year_established"),
        "country": data.get("country"),
        "description": data.get("description"),
        "url": data.get("url"),
        "image": data.get("image"),
        "facebook_url": data.get("facebook_url"),
        "reddit_url": data.get("reddit_url"),
        "telegram_url": data.get("telegram_url"),
        "slack_url": data.get("slack_url"),
        "other_url_1": data.get("other_url_1"),
        "other_url_2": data.get("other_url_2"),
        "twitter_handle": data.get("twitter_handle"),
        "has_trading_incentive": data.get("has_trading_incentive"),
        "centralized": data.get("centralized"),
        "public_notice": data.get("public_notice"),
        "alert_notice": data.get("alert_notice"),
        "trust_score": data.get("trust_score"),
        "trust_score_rank": data.get("trust_score_rank"),
        "trade_volume_24h_btc": data.get("trade_volume_24h_btc"),
        "trade_volume_24h_btc_normalized": data.get("trade_volume_24h_btc_normalized"),
        "tickers_count": len(data.get("tickers", []))
    }

    # Include sample tickers (first 10)
    tickers = data.get("tickers", [])[:10]
    result["sample_tickers"] = [
        {
            "base": t.get("base", ""),
            "target": t.get("target", ""),
            "last": t.get("last"),
            "volume": t.get("volume"),
            "trust_score": t.get("trust_score"),
            "bid_ask_spread_percentage": t.get("bid_ask_spread_percentage")
        }
        for t in tickers
    ]

    return result


def get_exchange_tickers(
    exchange_id: str,
    coin_ids: Optional[str] = None,
    include_exchange_logo: bool = False,
    page: int = 1,
    order: str = "volume_desc",
    depth: bool = False
) -> Dict[str, Any]:
    """
    Get all trading pairs on an exchange.

    Args:
        exchange_id: CoinGecko exchange id
        coin_ids: Comma-separated coin ids to filter
        include_exchange_logo: Include exchange logo
        page: Page number
        order: Sort order (trust_score_desc, trust_score_asc, volume_desc, volume_asc)
        depth: Include order book depth

    Returns:
        Dictionary with exchange tickers
    """
    api_key = get_api_key()

    url = f"https://pro-api.coingecko.com/api/v3/exchanges/{exchange_id}/tickers"
    headers = {"x-cg-pro-api-key": api_key}
    params = {
        "include_exchange_logo": str(include_exchange_logo).lower(),
        "page": page,
        "order": order,
        "depth": str(depth).lower()
    }
    if coin_ids:
        params["coin_ids"] = coin_ids

    response = proxied_get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    tickers = []
    for ticker in data.get("tickers", []):
        ticker_data = {
            "base": ticker.get("base", ""),
            "target": ticker.get("target", ""),
            "coin_id": ticker.get("coin_id"),
            "target_coin_id": ticker.get("target_coin_id"),
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
            "trade_url": ticker.get("trade_url")
        }
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


def get_exchange_volume_chart(
    exchange_id: str,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get historical volume chart for an exchange.

    Args:
        exchange_id: CoinGecko exchange id
        days: Number of days (1, 7, 14, 30, 90, 180, 365)

    Returns:
        Dictionary with volume history data
    """
    api_key = get_api_key()

    url = f"https://pro-api.coingecko.com/api/v3/exchanges/{exchange_id}/volume_chart"
    headers = {"x-cg-pro-api-key": api_key}
    params = {"days": days}

    response = proxied_get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Data is array of [timestamp, volume_btc]
    volume_data = []
    for item in data:
        if isinstance(item, list) and len(item) >= 2:
            volume_data.append({
                "timestamp": item[0],
                "volume_btc": item[1]
            })

    return {
        "exchange_id": exchange_id,
        "days": days,
        "volume_history": volume_data,
        "count": len(volume_data)
    }


def main():
    """CLI interface for exchanges tools."""
    parser = argparse.ArgumentParser(
        description="CoinGecko Exchanges Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command")

    # List command
    list_parser = subparsers.add_parser("list", help="Get all exchanges")
    list_parser.add_argument("--per-page", type=int, default=100)
    list_parser.add_argument("--page", type=int, default=1)

    # Exchange command
    exch_parser = subparsers.add_parser("get", help="Get exchange details")
    exch_parser.add_argument("exchange_id", help="Exchange ID")

    # Tickers command
    tickers_parser = subparsers.add_parser("tickers", help="Get exchange tickers")
    tickers_parser.add_argument("exchange_id", help="Exchange ID")
    tickers_parser.add_argument("--coins", help="Filter by coin ids")
    tickers_parser.add_argument("--page", type=int, default=1)
    tickers_parser.add_argument("--order", default="volume_desc")

    # Volume chart command
    chart_parser = subparsers.add_parser("volume-chart", help="Get exchange volume history")
    chart_parser.add_argument("exchange_id", help="Exchange ID")
    chart_parser.add_argument("--days", type=int, default=30)

    args = parser.parse_args()

    try:
        if args.command == "list":
            result = get_exchanges(args.per_page, args.page)
        elif args.command == "get":
            result = get_exchange(args.exchange_id)
        elif args.command == "tickers":
            result = get_exchange_tickers(
                exchange_id=args.exchange_id,
                coin_ids=args.coins,
                page=args.page,
                order=args.order
            )
        elif args.command == "volume-chart":
            result = get_exchange_volume_chart(args.exchange_id, args.days)
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
