"""
Coinglass skill exports — script-mode skill.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/coinglass")
    from exports import funding_rate, cg_open_interest
    print(funding_rate(symbol="BTC"))
    EOF
"""
import os, sys

# Add skill root to sys.path so `tools` works as a package
# (tools/*.py uses relative imports like `from ._api import cg_request`).
_SKILL_ROOT = os.path.dirname(os.path.abspath(__file__))
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

# --- Funding Rate ---
from tools.funding_rate import get_symbol_funding_rate as funding_rate

# --- Long/Short ---
from tools.long_short_ratio import get_long_short_ratio as long_short_ratio
from tools.long_short_advanced import get_global_account_ratio as cg_global_account_ratio
from tools.long_short_advanced import get_top_account_ratio as cg_top_account_ratio
from tools.long_short_advanced import get_top_position_ratio as cg_top_position_ratio
from tools.long_short_advanced import get_taker_buysell_exchanges as cg_taker_exchanges
from tools.long_short_advanced import get_net_position as cg_net_position

# --- Open Interest ---
from tools.open_interest import get_open_interest as cg_open_interest

# --- Liquidations ---
from tools.liquidations import get_liquidations as cg_liquidations
from tools.liquidations import get_liquidation_aggregated as cg_liquidation_analysis
from tools.liquidations_advanced import get_coin_liquidation_history as cg_coin_liquidation_history
from tools.liquidations_advanced import get_pair_liquidation_history as cg_pair_liquidation_history
from tools.liquidations_advanced import get_liquidation_coin_list as cg_liquidation_coin_list
from tools.liquidations_advanced import get_liquidation_orders as cg_liquidation_orders

# --- Futures Market ---
from tools.futures_market import get_supported_coins as cg_supported_coins
from tools.futures_market import get_supported_exchanges as cg_supported_exchanges
from tools.futures_market import get_coins_data as cg_coins_market_data
from tools.futures_market import get_pair_data as cg_pair_market_data
from tools.futures_market import get_ohlc_history as cg_ohlc_history

# --- Hyperliquid ---
from tools.hyperliquid import get_whale_alerts as cg_hyperliquid_whale_alerts
from tools.hyperliquid import get_whale_positions as cg_hyperliquid_whale_positions
from tools.hyperliquid import get_positions_by_coin as cg_hyperliquid_positions_by_coin
from tools.hyperliquid import get_position_distribution as cg_hyperliquid_position_distribution

# --- Volume & Flow ---
from tools.volume_flow import get_taker_volume_history as cg_taker_volume_history
from tools.volume_flow import get_aggregated_taker_volume as cg_aggregated_taker_volume
from tools.volume_flow import get_cumulative_volume_delta as cg_cumulative_volume_delta
from tools.volume_flow import get_coin_netflow as cg_coin_netflow

# --- Whale Transfers ---
from tools.whale_transfer import get_whale_transfers as cg_whale_transfers

# --- BTC ETF ---
from tools.bitcoin_etf import get_btc_etf_flows as cg_btc_etf_flows
from tools.bitcoin_etf import get_btc_etf_premium_discount as cg_btc_etf_premium_discount
from tools.bitcoin_etf import get_btc_etf_history as cg_btc_etf_history
from tools.bitcoin_etf import get_btc_etf_list as cg_btc_etf_list
from tools.bitcoin_etf import get_hk_btc_etf_flows as cg_hk_btc_etf_flows

# --- Other ETFs ---
from tools.other_etfs import get_eth_etf_flows as cg_eth_etf_flows
from tools.other_etfs import get_eth_etf_list as cg_eth_etf_list
from tools.other_etfs import get_sol_etf_flows as cg_sol_etf_flows
from tools.other_etfs import get_xrp_etf_flows as cg_xrp_etf_flows
