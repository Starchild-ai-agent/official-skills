"""
Coinglass Tools Module

Provides access to Coinglass cryptocurrency derivatives data including
funding rates and long/short account ratios across major exchanges.

Usage:
    from tools.coinglass import get_funding_rates, get_long_short_ratio

    # Get BTC funding rates
    rates = get_funding_rates("BTC")

    # Get BTC long/short ratio
    ratio = get_long_short_ratio("BTC", "h1")

Environment Variables Required:
- COINGLASS_API_KEY: Your Coinglass API key
"""

from .funding_rate import (
    get_funding_rates,
    get_symbol_funding_rate,
    get_funding_rate_by_exchange,
    analyze_funding_opportunity
)

from .long_short_ratio import (
    get_long_short_ratio,
    get_exchange_ratio,
    get_sentiment,
    compare_exchanges
)

__all__ = [
    # Funding Rate functions
    "get_funding_rates",
    "get_symbol_funding_rate",
    "get_funding_rate_by_exchange",
    "analyze_funding_opportunity",
    # Long/Short Ratio functions
    "get_long_short_ratio",
    "get_exchange_ratio",
    "get_sentiment",
    "compare_exchanges"
]
