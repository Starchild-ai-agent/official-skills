"""
Coinglass skill exports — tool names match SKILL.md frontmatter.

Usage in task scripts:
    from core.skill_tools import coinglass
    fr = coinglass.funding_rate(symbol="BTC")
"""
# --- Funding Rate ---
from funding_rate import get_symbol_funding_rate as funding_rate

# --- Long/Short ---
from long_short_ratio import get_long_short_ratio as long_short_ratio
from long_short_advanced import get_global_account_ratio as cg_global_account_ratio
from long_short_advanced import get_top_account_ratio as cg_top_account_ratio
from long_short_advanced import get_top_position_ratio as cg_top_position_ratio
from long_short_advanced import get_taker_buysell_exchanges as cg_taker_exchanges
from long_short_advanced import get_net_position as cg_net_position

# --- Open Interest ---
from open_interest import get_open_interest as cg_open_interest

# --- Liquidations ---
from liquidations import get_liquidations as cg_liquidations
from liquidations import get_liquidation_aggregated as cg_liquidation_analysis
from liquidations_advanced import get_coin_liquidation_history as cg_coin_liquidation_history
from liquidations_advanced import get_pair_liquidation_history as cg_pair_liquidation_history
from liquidations_advanced import get_liquidation_coin_list as cg_liquidation_coin_list
from liquidations_advanced import get_liquidation_orders as cg_liquidation_orders

# --- Futures Market ---
from futures_market import get_supported_coins as cg_supported_coins
from futures_market import get_supported_exchanges as cg_supported_exchanges
from futures_market import get_coins_data as cg_coins_market_data
from futures_market import get_pair_data as cg_pair_market_data
from futures_market import get_ohlc_history as cg_ohlc_history

# --- Hyperliquid ---
from hyperliquid import get_whale_alerts as cg_hyperliquid_whale_alerts
from hyperliquid import get_whale_positions as cg_hyperliquid_whale_positions
from hyperliquid import get_positions_by_coin as cg_hyperliquid_positions_by_coin
from hyperliquid import get_position_distribution as cg_hyperliquid_position_distribution

# --- Volume & Flow ---
from volume_flow import get_taker_volume_history as cg_taker_volume_history
from volume_flow import get_aggregated_taker_volume as cg_aggregated_taker_volume
from volume_flow import get_cumulative_volume_delta as cg_cumulative_volume_delta
from volume_flow import get_coin_netflow as cg_coin_netflow

# --- Whale Transfers ---
from whale_transfer import get_whale_transfers as cg_whale_transfers

# --- BTC ETF ---
from bitcoin_etf import get_btc_etf_flows as cg_btc_etf_flows
from bitcoin_etf import get_btc_etf_premium_discount as cg_btc_etf_premium_discount
from bitcoin_etf import get_btc_etf_history as cg_btc_etf_history
from bitcoin_etf import get_btc_etf_list as cg_btc_etf_list
from bitcoin_etf import get_hk_btc_etf_flows as cg_hk_btc_etf_flows

# --- Other ETFs ---
from other_etfs import get_eth_etf_flows as cg_eth_etf_flows
from other_etfs import get_eth_etf_list as cg_eth_etf_list
from other_etfs import get_sol_etf_flows as cg_sol_etf_flows
from other_etfs import get_xrp_etf_flows as cg_xrp_etf_flows
