"""
Coinglass Extension - Crypto Derivatives Data Tools

Provides crypto derivatives market data including:
- Funding rates (V2 API)
- Open interest (V2 API)
- Long/Short ratios (V2 API)
- Liquidations (V2/V4 API)
- Futures market data (V4 API)
  - Supported coins and exchanges
  - Comprehensive market data for all coins
  - Pair-specific market metrics
  - OHLC price history

Environment Variables Required:
- COINGLASS_API_KEY: Coinglass API key

Usage:
    This extension is auto-loaded by the ExtensionLoader.
    Tools are available to agents configured with these tools in agents.yaml.
"""
import os
import sys
import logging
from typing import List

try:
    from core.tool import ToolRegistry
except Exception:
    ToolRegistry = None  # Standalone script usage

logger = logging.getLogger(__name__)

# Add local tools directory to path for imports
TOOLS_DIR = os.path.join(os.path.dirname(__file__), 'tools')
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)


def register(api) -> List[str]:
    """
    Extension entry point - register all Coinglass tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .coinglass import (
            FundingRateTool,
            LongShortRatioTool,
            GlobalAccountRatioTool,
            TopAccountRatioTool,
            TopPositionRatioTool,
            TakerBuySellExchangesTool,
            NetPositionTool,
            OpenInterestTool,
            LiquidationsTool,
            LiquidationAnalysisTool,
            CoinLiquidationHistoryTool,
            PairLiquidationHistoryTool,
            LiquidationCoinListTool,
            LiquidationOrdersTool,
            HyperliquidWhaleAlertsTool,
            HyperliquidWhalePositionsTool,
            HyperliquidPositionsByCoinTool,
            HyperliquidPositionDistributionTool,
            SupportedCoinsTool,
            SupportedExchangesTool,
            CoinsMarketDataTool,
            PairMarketDataTool,
            OHLCHistoryTool,
            TakerVolumeHistoryTool,
            AggregatedTakerVolumeTool,
            CumulativeVolumeDeltaTool,
            CoinNetflowTool,
            WhaleTransferTool,
            BTCETFFlowsTool,
            BTCETFPremiumDiscountTool,
            BTCETFHistoryTool,
            BTCETFListTool,
            HKBTCETFFlowsTool,
            ETHETFFlowsTool,
            ETHETFListTool,
            SOLETFFlowsTool,
            XRPETFFlowsTool,
        )
        # Register existing V2 tools
        api.register_tool(FundingRateTool())
        api.register_tool(LongShortRatioTool())

        # Register advanced long/short ratio tools
        api.register_tool(GlobalAccountRatioTool())
        api.register_tool(TopAccountRatioTool())
        api.register_tool(TopPositionRatioTool())
        api.register_tool(TakerBuySellExchangesTool())
        api.register_tool(NetPositionTool())

        api.register_tool(OpenInterestTool())
        api.register_tool(LiquidationsTool())
        api.register_tool(LiquidationAnalysisTool())

        # Register advanced liquidation tools
        api.register_tool(CoinLiquidationHistoryTool())
        api.register_tool(PairLiquidationHistoryTool())
        api.register_tool(LiquidationCoinListTool())
        api.register_tool(LiquidationOrdersTool())

        # Register Hyperliquid tools
        api.register_tool(HyperliquidWhaleAlertsTool())
        api.register_tool(HyperliquidWhalePositionsTool())
        api.register_tool(HyperliquidPositionsByCoinTool())
        api.register_tool(HyperliquidPositionDistributionTool())

        # Register new V4 futures market tools
        api.register_tool(SupportedCoinsTool())
        api.register_tool(SupportedExchangesTool())
        api.register_tool(CoinsMarketDataTool())
        api.register_tool(PairMarketDataTool())
        api.register_tool(OHLCHistoryTool())

        # Register Volume & Flow tools
        api.register_tool(TakerVolumeHistoryTool())
        api.register_tool(AggregatedTakerVolumeTool())
        api.register_tool(CumulativeVolumeDeltaTool())
        api.register_tool(CoinNetflowTool())

        # Register Whale Transfer tool
        api.register_tool(WhaleTransferTool())

        # Register Bitcoin ETF tools
        api.register_tool(BTCETFFlowsTool())
        api.register_tool(BTCETFPremiumDiscountTool())
        api.register_tool(BTCETFHistoryTool())
        api.register_tool(BTCETFListTool())
        api.register_tool(HKBTCETFFlowsTool())

        # Register Ethereum & Other ETF tools
        api.register_tool(ETHETFFlowsTool())
        api.register_tool(ETHETFListTool())
        api.register_tool(SOLETFFlowsTool())
        api.register_tool(XRPETFFlowsTool())

        registered.extend([
            "funding_rate",
            "long_short_ratio",
            "cg_global_account_ratio",
            "cg_top_account_ratio",
            "cg_top_position_ratio",
            "cg_taker_exchanges",
            "cg_net_position",
            "cg_open_interest",
            "cg_liquidations",
            "cg_liquidation_analysis",
            "cg_coin_liquidation_history",
            "cg_pair_liquidation_history",
            "cg_liquidation_coin_list",
            "cg_liquidation_orders",
            "cg_hyperliquid_whale_alerts",
            "cg_hyperliquid_whale_positions",
            "cg_hyperliquid_positions_by_coin",
            "cg_hyperliquid_position_distribution",
            "cg_supported_coins",
            "cg_supported_exchanges",
            "cg_coins_market_data",
            "cg_pair_market_data",
            "cg_ohlc_history",
            "cg_taker_volume_history",
            "cg_aggregated_taker_volume",
            "cg_cumulative_volume_delta",
            "cg_coin_netflow",
            "cg_whale_transfers",
            "cg_btc_etf_flows",
            "cg_btc_etf_premium_discount",
            "cg_btc_etf_history",
            "cg_btc_etf_list",
            "cg_hk_btc_etf_flows",
            "cg_eth_etf_flows",
            "cg_eth_etf_list",
            "cg_sol_etf_flows",
            "cg_xrp_etf_flows",
        ])
        logger.info("Registered Coinglass tools (37 tools)")
    except Exception as e:
        logger.warning(f"Failed to load Coinglass tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "coinglass",
    "version": "3.0.0",
    "description": "Coinglass crypto derivatives data tools - V4 API with advanced long/short ratios, liquidations, Hyperliquid whale tracking, volume & flow analysis, on-chain whale transfers, comprehensive ETF data (Bitcoin, Ethereum, Solana, XRP, Hong Kong), and futures market data (37 tools)",
    "tools": [
        "funding_rate",
        "long_short_ratio",
        "cg_global_account_ratio",
        "cg_top_account_ratio",
        "cg_top_position_ratio",
        "cg_taker_exchanges",
        "cg_net_position",
        "cg_open_interest",
        "cg_liquidations",
        "cg_liquidation_analysis",
        "cg_coin_liquidation_history",
        "cg_pair_liquidation_history",
        "cg_liquidation_coin_list",
        "cg_liquidation_orders",
        "cg_hyperliquid_whale_alerts",
        "cg_hyperliquid_whale_positions",
        "cg_hyperliquid_positions_by_coin",
        "cg_hyperliquid_position_distribution",
        "cg_supported_coins",
        "cg_supported_exchanges",
        "cg_coins_market_data",
        "cg_pair_market_data",
        "cg_ohlc_history",
        "cg_taker_volume_history",
        "cg_aggregated_taker_volume",
        "cg_cumulative_volume_delta",
        "cg_coin_netflow",
        "cg_whale_transfers",
        "cg_btc_etf_flows",
        "cg_btc_etf_premium_discount",
        "cg_btc_etf_history",
        "cg_btc_etf_list",
        "cg_hk_btc_etf_flows",
        "cg_eth_etf_flows",
        "cg_eth_etf_list",
        "cg_sol_etf_flows",
        "cg_xrp_etf_flows",
    ],
    "env_vars": [
        "COINGLASS_API_KEY",
    ],
}
