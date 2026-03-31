"""
DefiLlama Tool Wrappers

Native Python tools for DefiLlama DeFi analytics.
Replaces web_fetch-based SKILL.md approach with direct API calls + output trimming.
"""
import asyncio
import logging
from typing import Any, Dict, Optional

try:
    from core.tool import BaseTool, ToolContext, ToolResult
except ImportError:
    raise ImportError("Platform core not available")

from .tools import (
    get_protocols_tvl,
    get_protocol_detail,
    get_chains_tvl,
    get_chain_tvl_history,
    get_fees_overview,
    get_dex_volume_overview,
    get_yield_pools,
    get_stablecoins,
)

logger = logging.getLogger(__name__)

DEFILLAMA_AVAILABLE = True


class DefiLlamaTVLRankTool(BaseTool):
    """Get DeFi protocol TVL rankings."""

    @property
    def name(self) -> str:
        return "defillama_tvl_rank"

    @property
    def description(self) -> str:
        return """Get top DeFi protocols ranked by Total Value Locked (TVL).

Returns name, TVL, chain, category, and 1d/7d change for each protocol.
Use this for "top protocols", "TVL ranking", "biggest DeFi protocols".

Examples:
- Top 10 DeFi protocols: defillama_tvl_rank(top_n=10)
- Top 50: defillama_tvl_rank(top_n=50)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "default": 20, "description": "Number of top protocols (default 20)"},
            },
        }

    async def execute(self, ctx: ToolContext, top_n: int = 20) -> ToolResult:
        result = await asyncio.to_thread(get_protocols_tvl, top_n=top_n)
        if result is None:
            return ToolResult(success=False, output=None, error="Failed to fetch TVL data")
        return ToolResult(success=True, output=result)


class DefiLlamaProtocolTool(BaseTool):
    """Get detailed data for a specific DeFi protocol."""

    @property
    def name(self) -> str:
        return "defillama_protocol"

    @property
    def description(self) -> str:
        return """Get detailed data for a specific protocol: TVL, chain breakdown, 30-day history.

Use the protocol's DefiLlama slug (lowercase, hyphens). Common slugs:
  aave, lido, makerdao, uniswap, rocket-pool, compound-finance, curve-dex

Examples:
- Aave details: defillama_protocol(slug="aave")
- Lido details: defillama_protocol(slug="lido")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Protocol slug (e.g. 'aave', 'lido', 'uniswap')"},
            },
            "required": ["slug"],
        }

    async def execute(self, ctx: ToolContext, slug: str = "") -> ToolResult:
        if not slug:
            return ToolResult(success=False, output=None, error="slug is required")
        result = await asyncio.to_thread(get_protocol_detail, slug=slug)
        if result is None:
            return ToolResult(success=False, output=None, error=f"Protocol '{slug}' not found or API error")
        return ToolResult(success=True, output=result)


class DefiLlamaChainsTVLTool(BaseTool):
    """Get chain-level TVL rankings."""

    @property
    def name(self) -> str:
        return "defillama_chains"

    @property
    def description(self) -> str:
        return """Get TVL for all blockchain networks, ranked by TVL.

Returns chain name, TVL, and token symbol for top 30 chains.
Use for "chain TVL ranking", "ETH vs SOL TVL", "which chain has most TVL".

Examples:
- All chains: defillama_chains()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        result = await asyncio.to_thread(get_chains_tvl)
        if result is None:
            return ToolResult(success=False, output=None, error="Failed to fetch chain TVL")
        return ToolResult(success=True, output=result)


class DefiLlamaChainHistoryTool(BaseTool):
    """Get historical TVL for a specific chain."""

    @property
    def name(self) -> str:
        return "defillama_chain_history"

    @property
    def description(self) -> str:
        return """Get historical TVL trend for a specific chain (default last 30 days).

Use for "ETH TVL trend", "Solana TVL over time", "chain TVL change".

Examples:
- Ethereum 30d: defillama_chain_history(chain="Ethereum")
- Solana 90d: defillama_chain_history(chain="Solana", days=90)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "description": "Chain name (e.g. 'Ethereum', 'Solana', 'BSC')"},
                "days": {"type": "integer", "default": 30, "description": "Days of history (default 30)"},
            },
            "required": ["chain"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", days: int = 30) -> ToolResult:
        if not chain:
            return ToolResult(success=False, output=None, error="chain is required")
        result = await asyncio.to_thread(get_chain_tvl_history, chain=chain, days=days)
        if result is None:
            return ToolResult(success=False, output=None, error=f"No history for chain '{chain}'")
        return ToolResult(success=True, output=result)


class DefiLlamaFeesTool(BaseTool):
    """Get protocol fees & revenue rankings."""

    @property
    def name(self) -> str:
        return "defillama_fees"

    @property
    def description(self) -> str:
        return """Get DeFi protocol fees/revenue overview — 24h, 7d, 30d totals + protocol breakdown.

Use for "top fees protocols", "revenue ranking", "which protocols earn most".

Examples:
- Top 10 by fees: defillama_fees(top_n=10)
- Ethereum only: defillama_fees(chain="Ethereum")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "default": 20, "description": "Number of top protocols"},
                "chain": {"type": "string", "description": "Filter by chain (optional)"},
            },
        }

    async def execute(self, ctx: ToolContext, top_n: int = 20, chain: str = None) -> ToolResult:
        result = await asyncio.to_thread(get_fees_overview, top_n=top_n, chain=chain)
        if result is None:
            return ToolResult(success=False, output=None, error="Failed to fetch fees data")
        return ToolResult(success=True, output=result)


class DefiLlamaDEXVolumeTool(BaseTool):
    """Get DEX trading volume overview."""

    @property
    def name(self) -> str:
        return "defillama_dex_volume"

    @property
    def description(self) -> str:
        return """Get DEX trading volume overview — 24h total + protocol breakdown.

Use for "DEX volume ranking", "top DEXes", "Uniswap vs Raydium volume".

Examples:
- Top 10 DEXes: defillama_dex_volume(top_n=10)
- Solana DEXes: defillama_dex_volume(chain="Solana")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "default": 20, "description": "Number of top DEXes"},
                "chain": {"type": "string", "description": "Filter by chain (optional)"},
            },
        }

    async def execute(self, ctx: ToolContext, top_n: int = 20, chain: str = None) -> ToolResult:
        result = await asyncio.to_thread(get_dex_volume_overview, top_n=top_n, chain=chain)
        if result is None:
            return ToolResult(success=False, output=None, error="Failed to fetch DEX volume data")
        return ToolResult(success=True, output=result)


class DefiLlamaYieldsTool(BaseTool):
    """Get DeFi yield pools with filtering."""

    @property
    def name(self) -> str:
        return "defillama_yields"

    @property
    def description(self) -> str:
        return """Get DeFi yield/APY pools with filters for minimum APY, TVL, stablecoin-only, and chain.

Use for "best yields", "stablecoin farming", "low risk high APY pools".

Examples:
- Stablecoin pools >5% APY >50M TVL: defillama_yields(min_apy=5, min_tvl=50000000, stablecoin_only=True)
- Best yields on Ethereum: defillama_yields(chain="Ethereum", top_n=20)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "min_apy": {"type": "number", "default": 0, "description": "Minimum APY % (e.g. 5 for 5%)"},
                "min_tvl": {"type": "number", "default": 0, "description": "Minimum TVL in USD (e.g. 50000000)"},
                "stablecoin_only": {"type": "boolean", "default": False, "description": "Only stablecoin pools"},
                "chain": {"type": "string", "description": "Filter by chain (optional)"},
                "top_n": {"type": "integer", "default": 30, "description": "Max results"},
            },
        }

    async def execute(self, ctx: ToolContext, min_apy: float = 0, min_tvl: float = 0,
                      stablecoin_only: bool = False, chain: str = None, top_n: int = 30) -> ToolResult:
        result = await asyncio.to_thread(
            get_yield_pools, min_apy=min_apy, min_tvl=min_tvl,
            stablecoin_only=stablecoin_only, chain=chain, top_n=top_n,
        )
        if result is None:
            return ToolResult(success=False, output=None, error="Failed to fetch yield pools")
        return ToolResult(success=True, output=result)


class DefiLlamaStablecoinsTool(BaseTool):
    """Get stablecoin market data."""

    @property
    def name(self) -> str:
        return "defillama_stablecoins"

    @property
    def description(self) -> str:
        return """Get stablecoin market overview — total market cap + individual stablecoin data.

Returns name, symbol, market cap, chains, and price for top stablecoins.
Use for "stablecoin market cap", "USDT vs USDC", "stablecoin dominance".

Examples:
- Top 20 stablecoins: defillama_stablecoins()"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "default": 20, "description": "Number of top stablecoins"},
            },
        }

    async def execute(self, ctx: ToolContext, top_n: int = 20) -> ToolResult:
        result = await asyncio.to_thread(get_stablecoins, top_n=top_n)
        if result is None:
            return ToolResult(success=False, output=None, error="Failed to fetch stablecoin data")
        return ToolResult(success=True, output=result)
