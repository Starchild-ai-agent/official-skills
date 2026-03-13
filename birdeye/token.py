"""
Birdeye Token Intelligence Tool Wrappers

BaseTool wrappers for token security and overview analysis.
"""
import asyncio
import logging
from typing import Optional

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

try:
    from .tools.token import (
        get_token_security,
        get_token_overview
    )
    BIRDEYE_TOKEN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Birdeye token tools not available: {e}")
    BIRDEYE_TOKEN_AVAILABLE = False


class BirdeyeTokenSecurityTool(BaseTool):
    """Get token security score and analysis."""

    @property
    def name(self) -> str:
        return "birdeye_token_security"

    @property
    def description(self) -> str:
        return """Get token security score and risk analysis.

Identifies rug pull risks, contract issues, and liquidity concerns.

Parameters:
- address: Token contract address (required)
- chain: Blockchain (default: solana)

Returns: Security score, risk level, and list of detected issues"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Token address"},
                "chain": {"type": "string", "description": "Blockchain", "default": "solana"}
            },
            "required": ["address"]
        }

    async def execute(self, ctx: ToolContext, address: str, chain: str = "solana", **kwargs) -> ToolResult:
        if not BIRDEYE_TOKEN_AVAILABLE:
            return ToolResult(success=False, output=None, error="Birdeye token tools not available")
        try:
            result = await asyncio.to_thread(get_token_security, address=address, chain=chain)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch token security.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class BirdeyeTokenOverviewTool(BaseTool):
    """Get comprehensive token data."""

    @property
    def name(self) -> str:
        return "birdeye_token_overview"

    @property
    def description(self) -> str:
        return """Get comprehensive token overview.

Includes price, volume, market cap, liquidity, and price changes.

Parameters:
- address: Token contract address (required)
- chain: Blockchain (default: solana)

Returns: Symbol, price, volume, market cap, liquidity, and price change data"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Token address"},
                "chain": {"type": "string", "description": "Blockchain", "default": "solana"}
            },
            "required": ["address"]
        }

    async def execute(self, ctx: ToolContext, address: str, chain: str = "solana", **kwargs) -> ToolResult:
        if not BIRDEYE_TOKEN_AVAILABLE:
            return ToolResult(success=False, output=None, error="Birdeye token tools not available")
        try:
            result = await asyncio.to_thread(get_token_overview, address=address, chain=chain)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch token overview.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
