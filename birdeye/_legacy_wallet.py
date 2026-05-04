"""
Birdeye Wallet Analytics Tool Wrappers

BaseTool wrappers for wallet net worth analysis.

Note: Wallet APIs have limited rate (5 req/s, 75 req/min).
"""
import asyncio
import logging

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

try:
    from .tools.wallet import (
        get_wallet_networth,
    )
    BIRDEYE_WALLET_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Birdeye wallet tools not available: {e}")
    BIRDEYE_WALLET_AVAILABLE = False


class BirdeyeWalletNetworthTool(BaseTool):
    """Get current wallet net worth and portfolio breakdown."""

    @property
    def name(self) -> str:
        return "birdeye_wallet_networth"

    @property
    def description(self) -> str:
        return """Get current net worth and portfolio snapshot for a wallet.

Returns total value, token breakdown, and asset allocation.

Parameters:
- wallet: Wallet address (required)
- chain: Blockchain (default: solana)

Returns: Total USD value and detailed token holdings with balances and values"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "wallet": {"type": "string", "description": "Wallet address"},
                "chain": {"type": "string", "description": "Blockchain", "default": "solana"}
            },
            "required": ["wallet"]
        }

    async def execute(self, ctx: ToolContext, wallet: str, chain: str = "solana", **kwargs) -> ToolResult:
        if not BIRDEYE_WALLET_AVAILABLE:
            return ToolResult(success=False, output=None, error="Birdeye wallet tools not available")

        try:
            result = await asyncio.to_thread(get_wallet_networth, wallet=wallet, chain=chain)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch wallet net worth. Check BIRDEYE_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
