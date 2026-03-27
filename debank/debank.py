"""
DeBank Tool Wrappers

Wraps tools from /tools/debank/ for use in Agent framework.
Provides blockchain data, user portfolios, DeFi positions, and transaction simulation.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

# Import tools from local tools directory
try:
    from .tools.chain import (
        get_chain_list,
        get_chain,
        get_gas_market,
    )
    from .tools.token import (
        get_token,
        get_token_history_price,
        get_token_list_by_ids,
        get_token_top_holders,
    )
    from .tools.user import (
        get_user_total_balance,
        get_user_token_list,
        get_user_all_token_list,
        get_user_history_list,
        get_user_all_history_list,
        get_user_simple_protocol_list,
        get_user_all_simple_protocol_list,
        get_user_complex_protocol_list,
        get_user_all_complex_protocol_list,
        get_user_complex_app_list,
        get_user_nft_list,
        get_user_all_nft_list,
        get_user_chain_balance,
        get_user_token,
        get_user_protocol,
        get_user_used_chain_list,
        get_user_token_authorized_list,
        get_user_nft_authorized_list,
        get_user_chain_net_curve,
        get_user_total_net_curve,
    )
    from .tools.wallet import (
        pre_exec_tx,
        explain_tx,
    )
    from .tools.protocol import (
        get_protocol,
        get_protocol_list,
        get_protocol_all_list,
        get_app_protocol_list,
        get_pool,
    )
    DEBANK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"DeBank tools not available: {e}")
    DEBANK_AVAILABLE = False


# ==================== Chain Tools ====================

class DebankChainListTool(BaseTool):
    """Get list of all supported chains."""

    @property
    def name(self) -> str:
        return "db_chain_list"

    @property
    def description(self) -> str:
        return "Get the list of all chains supported by DeBank."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_chain_list)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankChainTool(BaseTool):
    """Get details of a specific chain."""

    @property
    def name(self) -> str:
        return "db_chain"

    @property
    def description(self) -> str:
        return "Get details of a specific blockchain by chain ID."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain_id": {
                    "type": "string",
                    "description": "Chain identifier (eth, bsc, polygon, etc.)"
                }
            },
            "required": ["chain_id"]
        }

    async def execute(self, ctx: ToolContext, chain_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_chain, chain_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankGasMarketTool(BaseTool):
    """Get gas prices for a chain."""

    @property
    def name(self) -> str:
        return "db_gas_market"

    @property
    def description(self) -> str:
        return "Get current gas prices for a specific chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain_id": {
                    "type": "string",
                    "description": "Chain identifier"
                }
            },
            "required": ["chain_id"]
        }

    async def execute(self, ctx: ToolContext, chain_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_gas_market, chain_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Token Tools ====================

class DebankTokenTool(BaseTool):
    """Get token details."""

    @property
    def name(self) -> str:
        return "db_token"

    @property
    def description(self) -> str:
        return "Get token details including symbol, name, decimals, and price."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "token_id": {"type": "string", "description": "Token contract address"}
            },
            "required": ["chain_id", "token_id"]
        }

    async def execute(self, ctx: ToolContext, chain_id: str, token_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_token, chain_id, token_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankTokenHistoryPriceTool(BaseTool):
    """Get token price history."""

    @property
    def name(self) -> str:
        return "db_token_history_price"

    @property
    def description(self) -> str:
        return "Get historical price data for a token."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "token_id": {"type": "string", "description": "Token contract address"},
                "start_time": {"type": "integer", "description": "Start timestamp (Unix)"},
                "end_time": {"type": "integer", "description": "End timestamp (Unix, optional)"}
            },
            "required": ["chain_id", "token_id", "start_time"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        chain_id: str,
        token_id: str,
        start_time: int,
        end_time: Optional[int] = None
    ) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(
                get_token_history_price, chain_id, token_id, start_time, end_time
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankTokenListByIdsTool(BaseTool):
    """Batch fetch multiple tokens."""

    @property
    def name(self) -> str:
        return "db_token_list_by_ids"

    @property
    def description(self) -> str:
        return "Batch fetch multiple tokens on a chain by their addresses. Use max_results to limit output."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "token_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of token contract addresses"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of tokens to return",
                    "default": 50
                }
            },
            "required": ["chain_id", "token_ids"]
        }

    async def execute(self, ctx: ToolContext, chain_id: str, token_ids: List[str], max_results: int = 50, **kwargs) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_token_list_by_ids, chain_id, token_ids)
            if isinstance(result, list):
                result = result[:max_results]
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankTokenTopHoldersTool(BaseTool):
    """Get top holders of a token."""

    @property
    def name(self) -> str:
        return "db_token_top_holders"

    @property
    def description(self) -> str:
        return "Get top holders of a token on a chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "token_id": {"type": "string", "description": "Token contract address"},
                "start": {"type": "integer", "description": "Start index for pagination", "default": 0}
            },
            "required": ["chain_id", "token_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        chain_id: str,
        token_id: str,
        start: int = 0
    ) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_token_top_holders, chain_id, token_id, start)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== User Balance Tools ====================

class DebankUserTotalBalanceTool(BaseTool):
    """Get user total balance across all chains."""

    @property
    def name(self) -> str:
        return "db_user_total_balance"

    @property
    def description(self) -> str:
        return "Get user's total portfolio balance across all supported chains."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address (0x...)"}
            },
            "required": ["user_addr"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_total_balance, user_addr)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserTokenListTool(BaseTool):
    """Get user token list on a chain."""

    @property
    def name(self) -> str:
        return "db_user_token_list"

    @property
    def description(self) -> str:
        return "Get user's token balances on a specific chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "is_all": {"type": "boolean", "description": "Include zero balances", "default": False}
            },
            "required": ["user_addr", "chain_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        user_addr: str,
        chain_id: str,
        is_all: Optional[bool] = None
    ) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_token_list, user_addr, chain_id, is_all)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserAllTokenListTool(BaseTool):
    """Get user token list on all chains."""

    @property
    def name(self) -> str:
        return "db_user_all_token_list"

    @property
    def description(self) -> str:
        return "Get user's token balances across all supported chains."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "is_all": {"type": "boolean", "description": "Include zero balances"}
            },
            "required": ["user_addr"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str, is_all: Optional[bool] = None) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_all_token_list, user_addr, is_all)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== User History Tools ====================

class DebankUserHistoryListTool(BaseTool):
    """Get user transaction history on a chain."""

    @property
    def name(self) -> str:
        return "db_user_history_list"

    @property
    def description(self) -> str:
        return "Get user's transaction history on a specific chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "start_time": {"type": "integer", "description": "Start timestamp (Unix)"},
                "page_count": {"type": "integer", "description": "Number of records (max 20)"}
            },
            "required": ["user_addr", "chain_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        user_addr: str,
        chain_id: str,
        start_time: Optional[int] = None,
        page_count: Optional[int] = None
    ) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(
                get_user_history_list, user_addr, chain_id, start_time, page_count
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserAllHistoryListTool(BaseTool):
    """Get user transaction history on all chains."""

    @property
    def name(self) -> str:
        return "db_user_all_history_list"

    @property
    def description(self) -> str:
        return "Get user's transaction history across all supported chains."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "start_time": {"type": "integer", "description": "Start timestamp"},
                "page_count": {"type": "integer", "description": "Number of records (max 20)"}
            },
            "required": ["user_addr"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        user_addr: str,
        start_time: Optional[int] = None,
        page_count: Optional[int] = None
    ) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(
                get_user_all_history_list, user_addr, start_time, page_count
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== User Protocol Tools ====================

class DebankUserSimpleProtocolListTool(BaseTool):
    """Get user simple protocol list on a chain."""

    @property
    def name(self) -> str:
        return "db_user_simple_protocol_list"

    @property
    def description(self) -> str:
        return "Get user's simple protocol balances on a specific chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"}
            },
            "required": ["user_addr", "chain_id"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str, chain_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_simple_protocol_list, user_addr, chain_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserAllSimpleProtocolListTool(BaseTool):
    """Get user simple protocol list on all chains."""

    @property
    def name(self) -> str:
        return "db_user_all_simple_protocol_list"

    @property
    def description(self) -> str:
        return "Get user's simple protocol balances across all chains."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"}
            },
            "required": ["user_addr"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_all_simple_protocol_list, user_addr)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserComplexProtocolListTool(BaseTool):
    """Get user detailed protocol positions on a chain."""

    @property
    def name(self) -> str:
        return "db_user_complex_protocol_list"

    @property
    def description(self) -> str:
        return "Get user's detailed protocol positions on a specific chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"}
            },
            "required": ["user_addr", "chain_id"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str, chain_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_complex_protocol_list, user_addr, chain_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserAllComplexProtocolListTool(BaseTool):
    """Get user detailed protocol positions on all chains."""

    @property
    def name(self) -> str:
        return "db_user_all_complex_protocol_list"

    @property
    def description(self) -> str:
        return "Get user's detailed protocol positions across all chains."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"}
            },
            "required": ["user_addr"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_all_complex_protocol_list, user_addr)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserComplexAppListTool(BaseTool):
    """Get user app-chain protocol positions."""

    @property
    def name(self) -> str:
        return "db_user_complex_app_list"

    @property
    def description(self) -> str:
        return "Get user's detailed positions on app-chain protocols."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"}
            },
            "required": ["user_addr"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_complex_app_list, user_addr)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== User NFT Tools ====================

class DebankUserNftListTool(BaseTool):
    """Get user NFT list on a chain."""

    @property
    def name(self) -> str:
        return "db_user_nft_list"

    @property
    def description(self) -> str:
        return "Get user's NFT collections on a specific chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "is_all": {"type": "boolean", "description": "Include all NFTs"}
            },
            "required": ["user_addr", "chain_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        user_addr: str,
        chain_id: str,
        is_all: Optional[bool] = None
    ) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_nft_list, user_addr, chain_id, is_all)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserAllNftListTool(BaseTool):
    """Get user NFT list on all chains."""

    @property
    def name(self) -> str:
        return "db_user_all_nft_list"

    @property
    def description(self) -> str:
        return "Get user's NFT collections across all chains."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "is_all": {"type": "boolean", "description": "Include all NFTs"}
            },
            "required": ["user_addr"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str, is_all: Optional[bool] = None) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_all_nft_list, user_addr, is_all)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== User Misc Tools ====================

class DebankUserChainBalanceTool(BaseTool):
    """Get user balance on a specific chain."""

    @property
    def name(self) -> str:
        return "db_user_chain_balance"

    @property
    def description(self) -> str:
        return "Get user's total balance on a specific chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"}
            },
            "required": ["user_addr", "chain_id"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str, chain_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_chain_balance, user_addr, chain_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserTokenTool(BaseTool):
    """Get user balance of a specific token."""

    @property
    def name(self) -> str:
        return "db_user_token"

    @property
    def description(self) -> str:
        return "Get user's balance of a specific token."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "token_id": {"type": "string", "description": "Token contract address"}
            },
            "required": ["user_addr", "chain_id", "token_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        user_addr: str,
        chain_id: str,
        token_id: str
    ) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_token, user_addr, chain_id, token_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserProtocolTool(BaseTool):
    """Get user realtime portfolio in a protocol."""

    @property
    def name(self) -> str:
        return "db_user_protocol"

    @property
    def description(self) -> str:
        return "Get user's realtime portfolio in a specific protocol."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "protocol_id": {"type": "string", "description": "Protocol identifier"}
            },
            "required": ["user_addr", "protocol_id"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str, protocol_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_protocol, user_addr, protocol_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserUsedChainListTool(BaseTool):
    """Get list of chains used by user."""

    @property
    def name(self) -> str:
        return "db_user_used_chain_list"

    @property
    def description(self) -> str:
        return "Get list of chains the user has activity on."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"}
            },
            "required": ["user_addr"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_used_chain_list, user_addr)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserTokenAuthorizedListTool(BaseTool):
    """Get user token authorization list."""

    @property
    def name(self) -> str:
        return "db_user_token_authorized_list"

    @property
    def description(self) -> str:
        return "Get user's current token approvals/authorizations on a chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"}
            },
            "required": ["user_addr", "chain_id"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str, chain_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_token_authorized_list, user_addr, chain_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserNftAuthorizedListTool(BaseTool):
    """Get user NFT authorization list."""

    @property
    def name(self) -> str:
        return "db_user_nft_authorized_list"

    @property
    def description(self) -> str:
        return "Get user's current NFT approvals/authorizations on a chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"}
            },
            "required": ["user_addr", "chain_id"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str, chain_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_nft_authorized_list, user_addr, chain_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserChainNetCurveTool(BaseTool):
    """Get user 24h net curve on a chain."""

    @property
    def name(self) -> str:
        return "db_user_chain_net_curve"

    @property
    def description(self) -> str:
        return "Get user's 24-hour net worth curve on a specific chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"}
            },
            "required": ["user_addr", "chain_id"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str, chain_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_chain_net_curve, user_addr, chain_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankUserTotalNetCurveTool(BaseTool):
    """Get user 24h net curve on all chains."""

    @property
    def name(self) -> str:
        return "db_user_total_net_curve"

    @property
    def description(self) -> str:
        return "Get user's 24-hour total net worth curve across all chains."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"}
            },
            "required": ["user_addr"]
        }

    async def execute(self, ctx: ToolContext, user_addr: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_user_total_net_curve, user_addr)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Wallet Tools ====================

class DebankPreExecTxTool(BaseTool):
    """Enhanced pre-execute transaction."""

    @property
    def name(self) -> str:
        return "db_pre_exec_tx"

    @property
    def description(self) -> str:
        return "Simulate a transaction before sending it to the blockchain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "tx": {
                    "type": "object",
                    "description": "Transaction object with from, to, value, data fields"
                }
            },
            "required": ["user_addr", "chain_id", "tx"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        user_addr: str,
        chain_id: str,
        tx: Dict[str, Any]
    ) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(pre_exec_tx, user_addr, chain_id, tx)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankExplainTxTool(BaseTool):
    """Explain transaction."""

    @property
    def name(self) -> str:
        return "db_explain_tx"

    @property
    def description(self) -> str:
        return "Get human-readable explanation of what a transaction does."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_addr": {"type": "string", "description": "User wallet address"},
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "tx": {
                    "type": "object",
                    "description": "Transaction object with from, to, value, data fields"
                }
            },
            "required": ["user_addr", "chain_id", "tx"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        user_addr: str,
        chain_id: str,
        tx: Dict[str, Any]
    ) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(explain_tx, user_addr, chain_id, tx)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Protocol Tools ====================

class DebankProtocolTool(BaseTool):
    """Get protocol details."""

    @property
    def name(self) -> str:
        return "db_protocol"

    @property
    def description(self) -> str:
        return "Get details of a DeFi protocol."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "protocol_id": {"type": "string", "description": "Protocol identifier (e.g., uniswap, aave)"}
            },
            "required": ["protocol_id"]
        }

    async def execute(self, ctx: ToolContext, protocol_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_protocol, protocol_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankProtocolListTool(BaseTool):
    """Get protocols on a chain."""

    @property
    def name(self) -> str:
        return "db_protocol_list"

    @property
    def description(self) -> str:
        return "Get list of protocols on a specific chain."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain_id": {"type": "string", "description": "Chain identifier"}
            },
            "required": ["chain_id"]
        }

    async def execute(self, ctx: ToolContext, chain_id: str) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_protocol_list, chain_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankProtocolAllListTool(BaseTool):
    """Get all protocols across all chains."""

    @property
    def name(self) -> str:
        return "db_protocol_all_list"

    @property
    def description(self) -> str:
        return "Get list of all protocols across all supported chains."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_protocol_all_list)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankAppProtocolListTool(BaseTool):
    """Get all app-protocols."""

    @property
    def name(self) -> str:
        return "db_app_protocol_list"

    @property
    def description(self) -> str:
        return "Get list of all app-chain protocols."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_app_protocol_list)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DebankPoolTool(BaseTool):
    """Get pool details."""

    @property
    def name(self) -> str:
        return "db_pool"

    @property
    def description(self) -> str:
        return "Get details of a DeFi pool."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "protocol_id": {"type": "string", "description": "Protocol identifier"},
                "chain_id": {"type": "string", "description": "Chain identifier"},
                "pool_id": {"type": "string", "description": "Pool identifier (contract address)"}
            },
            "required": ["protocol_id", "chain_id", "pool_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        protocol_id: str,
        chain_id: str,
        pool_id: str
    ) -> ToolResult:
        if not DEBANK_AVAILABLE:
            return ToolResult(success=False, output=None, error="DeBank tools not available")

        try:
            result = await asyncio.to_thread(get_pool, protocol_id, chain_id, pool_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
