#!/usr/bin/env python3
"""
Coinglass Bitcoin ETF Module

Provides Bitcoin ETF data including flows, net assets,
premium/discount, history, and Hong Kong ETF data.
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional, List

from ._api import cg_request, CoinglassError


def get_btc_etf_flows() -> Optional[List[Dict[str, Any]]]:
    """Get Bitcoin ETF flow history (inflows/outflows by fund)."""
    return cg_request("api/etf/bitcoin/flow-history")


def get_btc_etf_net_assets() -> Optional[List[Dict[str, Any]]]:
    """Get Bitcoin ETF net assets history."""
    return cg_request("api/reference/bitcoin-etf-netassets-history")


def get_btc_etf_premium_discount() -> Optional[List[Dict[str, Any]]]:
    """Get Bitcoin ETF premium/discount rate history."""
    return cg_request("api/etf/bitcoin/premium-discount/history")


def get_btc_etf_history(
    etf_ticker: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Get comprehensive Bitcoin ETF history.

    Args:
        etf_ticker: Required by the API (e.g. "GBTC", "IBIT").
    """
    if not etf_ticker:
        raise CoinglassError(
            "Coinglass API error [400]: api/etf/bitcoin/history now "
            "requires a 'ticker' parameter (e.g. GBTC, IBIT). "
            "Pass etf_ticker explicitly.",
            code="API_400",
            suggestion="Use cg_btc_etf_flows() for aggregate daily "
                       "flows, or pass a specific ticker."
        )
    params = {"ticker": etf_ticker}
    return cg_request("api/etf/bitcoin/history", params=params)


def get_btc_etf_list() -> Optional[List[Dict[str, Any]]]:
    """Get list of all Bitcoin ETFs with details."""
    return cg_request("api/etf/bitcoin/list")


def get_hk_btc_etf_flows() -> Optional[List[Dict[str, Any]]]:
    """Get Hong Kong Bitcoin ETF flow history."""
    return cg_request("api/hk-etf/bitcoin/flow-history")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Coinglass BTC ETF Tools")
    parser.add_argument("action", choices=[
        "flows", "assets", "premium", "history", "list", "hk-flows"
    ])
    parser.add_argument("--ticker", help="ETF ticker filter")
    parser.add_argument("--json", "-j", action="store_true")
    args = parser.parse_args()

    actions = {
        "flows": get_btc_etf_flows,
        "assets": get_btc_etf_net_assets,
        "premium": get_btc_etf_premium_discount,
        "history": lambda: get_btc_etf_history(args.ticker),
        "list": get_btc_etf_list,
        "hk-flows": get_hk_btc_etf_flows,
    }

    try:
        result = actions[args.action]()
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
