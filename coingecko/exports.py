"""
CoinGecko skill exports — tool names match SKILL.md frontmatter.

Usage in task scripts:
    from core.skill_tools import coingecko
    data = coingecko.coin_price(coin_ids="bitcoin", timestamps=["now"])
"""
import os, sys

_tools_dir = os.path.join(os.path.dirname(__file__), "tools")
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)

# --- Prices ---
from coin_prices import get_coin_prices_at_timestamps as coin_price
from coin_ohlc_range_by_id import get_coin_ohlc_range_by_id as coin_ohlc
from coin_historical_chart_range_by_id import get_coin_historical_chart_range_by_id as coin_chart

# --- Market Discovery ---
from market_discovery import get_trending as cg_trending
from market_discovery import get_top_gainers_losers as cg_top_gainers_losers
from market_discovery import get_new_coins as cg_new_coins

# --- Global ---
from global_data import get_global as cg_global
from global_data import get_global_defi as cg_global_defi

# --- Coins ---
from coins import get_coins_list as cg_coins_list
from coins import get_coins_markets as cg_coins_markets
from coins import get_coin_data as cg_coin_data
from coins import get_coin_tickers as cg_coin_tickers

# --- Exchanges ---
from exchanges import get_exchanges as cg_exchanges
from exchanges import get_exchange as cg_exchange
from exchanges import get_exchange_tickers as cg_exchange_tickers
from exchanges import get_exchange_volume_chart as cg_exchange_volume_chart

# --- Derivatives ---
from derivatives import get_derivatives as cg_derivatives
from derivatives import get_derivatives_exchanges as cg_derivatives_exchanges
from derivatives import get_categories as cg_categories

# --- Infrastructure ---
from infrastructure import get_asset_platforms as cg_asset_platforms
from infrastructure import get_exchange_rates as cg_exchange_rates
from infrastructure import get_vs_currencies as cg_vs_currencies
from infrastructure import get_categories_list as cg_categories_list

# --- Search & Contracts ---
from search import search as cg_search
from contracts import get_token_price as cg_token_price
from contracts import get_coin_by_contract as cg_coin_by_contract

# --- NFTs ---
from nfts import get_nfts_list as cg_nfts_list
from nfts import get_nft as cg_nft
from nfts import get_nft_by_contract as cg_nft_by_contract
