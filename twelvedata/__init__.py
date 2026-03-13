"""
Twelve Data Extension - Stocks and Forex Market Data

Provides stocks and forex market data including:
- Real-time quotes
- Historical time series (OHLCV)
- Reference data (stocks, forex pairs, exchanges)
- Search

Environment Variables Required:
- TWELVEDATA_API_KEY: Twelve Data Pro API key

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
    Extension entry point - register all Twelve Data tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    # Import and register Twelve Data tools (stocks & forex)
    # Only Pro subscription compatible tools (10 tools)
    try:
        from .tools.time_series import (
            TwelveDataTimeSeriesTools,
            TwelveDataPriceTool,
            TwelveDataEODTool,
        )
        from .tools.quote import (
            TwelveDataQuoteTool,
            TwelveDataQuoteBatchTool,
            TwelveDataPriceBatchTool,
        )
        from .tools.reference_data import (
            TwelveDataSearchTool,
            TwelveDataStocksTool,
            TwelveDataForexPairsTool,
            TwelveDataExchangesTool,
        )

        # Register time series tools (3)
        api.register_tool(TwelveDataTimeSeriesTools())
        api.register_tool(TwelveDataPriceTool())
        api.register_tool(TwelveDataEODTool())

        # Register quote tools (3)
        api.register_tool(TwelveDataQuoteTool())
        api.register_tool(TwelveDataQuoteBatchTool())
        api.register_tool(TwelveDataPriceBatchTool())

        # Register reference data tools (4)
        api.register_tool(TwelveDataSearchTool())
        api.register_tool(TwelveDataStocksTool())
        api.register_tool(TwelveDataForexPairsTool())
        api.register_tool(TwelveDataExchangesTool())

        # Note: Branding tool (logo) is omitted - currently has API key issues
        # Fundamental data tools removed - require Grow/Pro+/Ultra/Enterprise tiers

        registered.extend([
            # Time series (3)
            "twelvedata_time_series",
            "twelvedata_price",
            "twelvedata_eod",
            # Quotes (3)
            "twelvedata_quote",
            "twelvedata_quote_batch",
            "twelvedata_price_batch",
            # Reference data (4)
            "twelvedata_search",
            "twelvedata_stocks",
            "twelvedata_forex_pairs",
            "twelvedata_exchanges",
        ])
        logger.info("Registered Twelve Data tools (10 tools - Pro subscription compatible)")
    except Exception as e:
        logger.warning(f"Failed to load Twelve Data tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "twelvedata",
    "version": "1.0.0",
    "description": "Twelve Data stocks and forex market data tools",
    "tools": [
        # Time Series (3 tools)
        "twelvedata_time_series",
        "twelvedata_price",
        "twelvedata_eod",
        # Quotes (3 tools)
        "twelvedata_quote",
        "twelvedata_quote_batch",
        "twelvedata_price_batch",
        # Reference Data (4 tools)
        "twelvedata_search",
        "twelvedata_stocks",
        "twelvedata_forex_pairs",
        "twelvedata_exchanges",
    ],
    "env_vars": [
        "TWELVEDATA_API_KEY",
    ],
}
