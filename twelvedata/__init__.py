"""
Twelve Data Extension - Stocks and Forex Market Data

Provides stocks and forex market data including:
- Real-time quotes (with pre/post-market support)
- Historical time series (OHLCV)
- Reference data (stocks, forex pairs, exchanges)
- Search

Environment Variables Required:
- TWELVEDATA_API_KEY: Twelve Data Pro API key
"""
import os
import sys
import logging
from typing import List

logger = logging.getLogger(__name__)

# Add local tools directory to path for imports
TOOLS_DIR = os.path.join(os.path.dirname(__file__), 'tools')
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)


def register(api) -> List[str]:
    """Extension entry point - register all Twelve Data tools."""
    registered = []

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

        tools = [
            TwelveDataTimeSeriesTools(),
            TwelveDataPriceTool(),
            TwelveDataEODTool(),
            TwelveDataQuoteTool(),
            TwelveDataQuoteBatchTool(),
            TwelveDataPriceBatchTool(),
            TwelveDataSearchTool(),
            TwelveDataStocksTool(),
            TwelveDataForexPairsTool(),
            TwelveDataExchangesTool(),
        ]

        for tool in tools:
            api.register_tool(tool)
            registered.append(tool.name)

        logger.info(f"Registered {len(registered)} Twelve Data tools (Pro tier)")
    except Exception as e:
        logger.warning(f"Failed to load Twelve Data tools: {e}")

    return registered


EXTENSION_INFO = {
    "name": "twelvedata",
    "version": "1.1.0",
    "description": "Twelve Data stocks and forex market data tools (with pre/post-market support)",
}
