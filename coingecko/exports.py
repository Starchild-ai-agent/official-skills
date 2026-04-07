"""
CoinGecko skill exports — tool names and signatures match SKILL.md / agent tools.

Usage in task scripts:
    from core.skill_tools import coingecko
    prices = coingecko.coin_price(coin_ids="bitcoin,ethereum,solana")
    ohlc = coingecko.coin_ohlc(coin_id="bitcoin", days=30)
    trending = coingecko.cg_trending()
"""
from coin_prices import get_coin_prices_at_timestamps
from coin_ohlc_range_by_id import get_coin_ohlc_range_by_id
from coin_historical_chart_range_by_id import get_coin_historical_chart_range_by_id
from coins import (get_coins_list, get_coins_markets, get_coin_data, get_coin_tickers)
from market_discovery import get_trending, get_top_gainers_losers, get_new_coins
from global_data import get_global, get_global_defi
from search import search as _search
from derivatives import get_derivatives, get_derivatives_exchanges, get_categories
from exchanges import (get_exchanges, get_exchange, get_exchange_tickers,
                       get_exchange_volume_chart)
from infrastructure import (get_asset_platforms, get_exchange_rates,
                             get_vs_currencies, get_categories_list)
from nfts import get_nfts_list, get_nft, get_nft_by_contract
from contracts import get_token_price, get_coin_by_contract


# ── Price tools ──

def coin_price(coin_ids, timestamps=None, vs_currency="usd"):
    """Get coin prices. coin_ids: comma-separated IDs or symbols (bitcoin,BTC,ETH)."""
    return get_coin_prices_at_timestamps(
        coin_ids=coin_ids,
        timestamps=timestamps or ["now"],
        vs_currency=vs_currency
    )

def coin_ohlc(coin_id, days=30, vs_currency="usd"):
    """Get OHLC candlestick data."""
    return get_coin_ohlc_range_by_id(coin_id, days, vs_currency)

def coin_chart(coin_id, days=30, vs_currency="usd"):
    """Get price chart data (timestamp + price points)."""
    return get_coin_historical_chart_range_by_id(coin_id, days, vs_currency)


# ── Discovery tools ──

def cg_trending():
    """Get trending coins, NFTs, categories."""
    return get_trending()

def cg_top_gainers_losers(vs_currency="usd", duration="24h"):
    """Get top gainers and losers."""
    return get_top_gainers_losers(vs_currency, duration)

def cg_new_coins():
    """Get recently added coins."""
    return get_new_coins()

def cg_search(query):
    """Search for coins, exchanges, categories by name."""
    return _search(query)


# ── Global data ──

def cg_global():
    """Get global crypto market stats."""
    return get_global()

def cg_global_defi():
    """Get global DeFi market stats."""
    return get_global_defi()


# ── Coins ──

def cg_coins_list(include_platform=False):
    """Get list of all coins (id, symbol, name)."""
    return get_coins_list(include_platform)

def cg_coins_markets(vs_currency="usd", order="market_cap_desc", per_page=100,
                     page=1, sparkline=False, price_change_percentage="24h",
                     category=None, ids=None):
    """Get coin market data (price, mcap, volume, change%)."""
    return get_coins_markets(vs_currency, order, per_page, page, sparkline,
                             price_change_percentage, category, ids)

def cg_coin_data(coin_id, localization=False, tickers=False, market_data=True,
                 community_data=False, developer_data=False, sparkline=False):
    """Get detailed data for a specific coin."""
    return get_coin_data(coin_id, localization, tickers, market_data,
                         community_data, developer_data, sparkline)

def cg_coin_tickers(coin_id, exchange_ids=None, include_exchange_logo=False,
                    page=1, order="volume_desc", depth=False):
    """Get coin trading tickers across exchanges."""
    return get_coin_tickers(coin_id, exchange_ids, include_exchange_logo,
                            page, order, depth)


# ── Categories ──

def cg_categories(order="market_cap_desc"):
    """Get coin categories with market data."""
    return get_categories(order)

def cg_categories_list():
    """Get list of all categories (id + name only)."""
    return get_categories_list()


# ── Derivatives ──

def cg_derivatives(include_tickers="unexpired"):
    """Get derivatives tickers (futures/perpetuals)."""
    return get_derivatives(include_tickers)

def cg_derivatives_exchanges(order="open_interest_btc_desc", per_page=50):
    """Get derivatives exchanges ranked by open interest."""
    return get_derivatives_exchanges(order, per_page)


# ── Exchanges ──

def cg_exchanges(per_page=100, page=1):
    """Get list of exchanges with volume data."""
    return get_exchanges(per_page, page)

def cg_exchange(exchange_id):
    """Get specific exchange data."""
    return get_exchange(exchange_id)

def cg_exchange_tickers(exchange_id, coin_ids=None, include_exchange_logo=False,
                        page=1, order="volume_desc", depth=False):
    """Get tickers for a specific exchange."""
    return get_exchange_tickers(exchange_id, coin_ids, include_exchange_logo,
                                page, order, depth)

def cg_exchange_volume_chart(exchange_id, days=30):
    """Get exchange volume chart data."""
    return get_exchange_volume_chart(exchange_id, days)


# ── NFTs ──

def cg_nfts_list(order="market_cap_usd_desc", per_page=100, page=1):
    """Get NFT collections list."""
    return get_nfts_list(order, per_page, page)

def cg_nft(nft_id):
    """Get specific NFT collection data."""
    return get_nft(nft_id)

def cg_nft_by_contract(asset_platform, contract_address):
    """Get NFT data by contract address."""
    return get_nft_by_contract(asset_platform, contract_address)


# ── Infrastructure ──

def cg_asset_platforms(filter=None):
    """Get list of asset platforms (blockchains)."""
    return get_asset_platforms(filter)

def cg_exchange_rates():
    """Get BTC exchange rates to other currencies."""
    return get_exchange_rates()

def cg_vs_currencies():
    """Get list of supported vs currencies."""
    return get_vs_currencies()


# ── Contract/Token tools ──

def cg_token_price(platform, contract_addresses, vs_currencies="usd",
                   include_market_cap=False, include_24hr_vol=False,
                   include_24hr_change=False, include_last_updated_at=False):
    """Get token price by contract address."""
    return get_token_price(platform, contract_addresses, vs_currencies,
                           include_market_cap, include_24hr_vol,
                           include_24hr_change, include_last_updated_at)

def cg_coin_by_contract(platform, contract_address):
    """Get coin data by contract address."""
    return get_coin_by_contract(platform, contract_address)
