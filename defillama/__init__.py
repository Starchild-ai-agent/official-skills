"""
DefiLlama Extension - DeFi Analytics Native Tools

Provides DeFi market data via DefiLlama public API:
- Protocol TVL rankings and detail
- Chain TVL rankings and history
- Fees/revenue overview
- DEX volume overview
- Yield pool discovery
- Stablecoin market data

No API key required (public API).
"""
import logging
from typing import List

try:
    from core.tool import ToolRegistry
except Exception:
    ToolRegistry = None

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """Extension entry point — register all DefiLlama tools."""
    registered = []
    try:
        from .defillama import (
            DefiLlamaTVLRankTool,
            DefiLlamaProtocolTool,
            DefiLlamaChainsTVLTool,
            DefiLlamaChainHistoryTool,
            DefiLlamaFeesTool,
            DefiLlamaDEXVolumeTool,
            DefiLlamaYieldsTool,
            DefiLlamaStablecoinsTool,
        )
        tools = [
            DefiLlamaTVLRankTool(),
            DefiLlamaProtocolTool(),
            DefiLlamaChainsTVLTool(),
            DefiLlamaChainHistoryTool(),
            DefiLlamaFeesTool(),
            DefiLlamaDEXVolumeTool(),
            DefiLlamaYieldsTool(),
            DefiLlamaStablecoinsTool(),
        ]
        for tool in tools:
            api.registry.register(tool)
            registered.append(tool.name)
            logger.info(f"Registered DefiLlama tool: {tool.name}")
    except Exception as e:
        logger.error(f"Failed to register DefiLlama tools: {e}")
    return registered


EXTENSION_INFO = {
    "name": "defillama",
    "version": "2.0.0",
    "description": "DefiLlama DeFi analytics — native Python tools for TVL, fees, DEX volume, yields, stablecoins (8 tools, no API key needed)",
    "tools": [
        "defillama_tvl_rank",
        "defillama_protocol",
        "defillama_chains",
        "defillama_chain_history",
        "defillama_fees",
        "defillama_dex_volume",
        "defillama_yields",
        "defillama_stablecoins",
    ],
    "env_vars": [],
}
