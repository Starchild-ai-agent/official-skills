"""
1inch DEX Aggregator Tools — BaseTool subclasses for agent use.

Read-only tools (3): oneinch_quote, oneinch_tokens, oneinch_check_allowance
Write tools (2):     oneinch_approve, oneinch_swap

All tools use wallet_transfer (Starchild native) for on-chain tx broadcast.
No Fly Machine dependency. Works in any Starchild container.
"""

import logging
import os
from typing import Dict

from core.tool import BaseTool, ToolContext, ToolResult
from .client import OneInchClient, NATIVE_TOKEN, resolve_chain

logger = logging.getLogger(__name__)

# Agent wallet address — set once at startup
AGENT_ADDRESS = os.environ.get("AGENT_EVM_ADDRESS", "")

# Cache of clients per chain_id
_clients: Dict[int, OneInchClient] = {}


def _get_client(chain: str) -> OneInchClient:
    chain_id = resolve_chain(chain)
    if chain_id not in _clients:
        _clients[chain_id] = OneInchClient(chain_id=chain_id)
    return _clients[chain_id]


def _get_address() -> str:
    """Get agent EVM address from env."""
    addr = AGENT_ADDRESS or os.environ.get("AGENT_EVM_ADDRESS", "")
    if not addr:
        raise RuntimeError(
            "AGENT_EVM_ADDRESS not configured. "
            "Starchild sets this automatically for internal wallets."
        )
    return addr


# ── Read-Only Tools ──────────────────────────────────────────────────────────


class OneInchQuoteTool(BaseTool):
    """Get a swap quote from 1inch DEX aggregator."""

    @property
    def name(self) -> str:
        return "oneinch_quote"

    @property
    def description(self) -> str:
        return """Get a swap price quote from 1inch DEX aggregator.

Returns the estimated output amount and route WITHOUT executing a swap.
Use this to check prices before swapping. Use oneinch_tokens to find token addresses.

Parameters:
- chain: Network (ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis)
- src: Source token address (0xEeee...EEeE for native ETH)
- dst: Destination token address
- amount: Amount in wei (e.g. "2000000" = 2 USDC with 6 decimals)

Returns: dstAmount (estimated output in wei), gas estimate, route protocols"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "description": "Network name"},
                "src":   {"type": "string", "description": "Source token address"},
                "dst":   {"type": "string", "description": "Destination token address"},
                "amount": {"type": "string", "description": "Amount in wei"},
            },
            "required": ["chain", "src", "dst", "amount"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", src: str = "", dst: str = "", amount: str = "", **kwargs) -> ToolResult:
        if not all([chain, src, dst, amount]):
            return ToolResult(success=False, error="chain, src, dst, amount are all required")
        try:
            data = _get_client(chain).get_quote(src, dst, amount)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OneInchTokensTool(BaseTool):
    """Search or list supported tokens on a network via 1inch."""

    @property
    def name(self) -> str:
        return "oneinch_tokens"

    @property
    def description(self) -> str:
        return """List or search supported tokens on a network via 1inch.

Use to find token addresses before quoting or swapping. Addresses differ per network.

Parameters:
- chain: Network (ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis)
- search: (optional) Filter by token name or symbol (case-insensitive)

Returns: [{address, symbol, name, decimals}] (max 20 results)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain":  {"type": "string", "description": "Network name"},
                "search": {"type": "string", "description": "Filter by name or symbol (optional)"},
            },
            "required": ["chain"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", search: str = "", **kwargs) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        try:
            data = _get_client(chain).get_tokens()
            token_map = data.get("tokens", data) if isinstance(data, dict) else data
            tokens = list(token_map.values()) if isinstance(token_map, dict) else token_map
            if search:
                q = search.lower()
                tokens = [t for t in tokens if q in t.get("symbol", "").lower() or q in t.get("name", "").lower()]
            result = [{"address": t.get("address"), "symbol": t.get("symbol"), "name": t.get("name"), "decimals": t.get("decimals")} for t in tokens[:20]]
            return ToolResult(success=True, output={"tokens": result, "count": len(result)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OneInchCheckAllowanceTool(BaseTool):
    """Check if a token needs approval for 1inch swaps."""

    @property
    def name(self) -> str:
        return "oneinch_check_allowance"

    @property
    def description(self) -> str:
        return """Check if a token has sufficient allowance for the 1inch router.

Native ETH never needs approval. ERC-20 tokens (USDC, WETH, etc.) must be approved before swapping.

Parameters:
- chain: Network (ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis)
- token_address: ERC-20 token address to check

Returns: allowance amount, needs_approval (bool)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain":         {"type": "string", "description": "Network name"},
                "token_address": {"type": "string", "description": "ERC-20 token address"},
            },
            "required": ["chain", "token_address"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", token_address: str = "", **kwargs) -> ToolResult:
        if not chain or not token_address:
            return ToolResult(success=False, error="chain and token_address are required")
        if token_address.lower() == NATIVE_TOKEN.lower():
            return ToolResult(success=True, output={"allowance": "unlimited", "needs_approval": False, "note": "Native ETH does not need approval"})
        try:
            address = _get_address()
            data = _get_client(chain).get_allowance(token_address, address)
            allowance = data.get("allowance", "0")
            return ToolResult(success=True, output={"allowance": allowance, "needs_approval": allowance == "0", "token": token_address, "wallet": address})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Write Tools ──────────────────────────────────────────────────────────────


class OneInchApproveTool(BaseTool):
    """Approve a token for 1inch router spending via wallet_transfer."""

    @property
    def name(self) -> str:
        return "oneinch_approve"

    @property
    def description(self) -> str:
        return """Approve an ERC-20 token for the 1inch router.

Sends an on-chain approval transaction so 1inch router can spend your tokens.
Required before swapping ERC-20 tokens (not needed for native ETH).

Parameters:
- chain: Network (ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis)
- token_address: ERC-20 token address to approve
- amount: (optional) Amount to approve in wei. Omit for unlimited approval.

Returns: transaction hash"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain":         {"type": "string", "description": "Network name"},
                "token_address": {"type": "string", "description": "ERC-20 token address to approve"},
                "amount":        {"type": "string", "description": "Amount in wei (omit for unlimited)"},
            },
            "required": ["chain", "token_address"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", token_address: str = "", amount: str = "", **kwargs) -> ToolResult:
        if not chain or not token_address:
            return ToolResult(success=False, error="chain and token_address are required")
        try:
            from tools.wallet import wallet_transfer_sync

            client = _get_client(chain)
            tx_data = client.get_approve_transaction(token_address, amount=amount if amount else None)

            # Broadcast via Starchild wallet_transfer (no Fly Machine required)
            result = wallet_transfer_sync(
                to=tx_data["to"],
                amount=tx_data.get("value", "0"),
                data=tx_data.get("data", ""),
                chain_id=client.chain_id,
            )
            return ToolResult(success=True, output={"status": "approval_sent", "token": token_address, "tx": result})
        except Exception as e:
            err = str(e)
            if "policy" in err.lower():
                return ToolResult(success=False, error=f"Policy violation: {err}. Use wallet_propose_policy to allow this operation.")
            return ToolResult(success=False, error=err)


class OneInchSwapTool(BaseTool):
    """Execute a token swap via 1inch DEX aggregator."""

    @property
    def name(self) -> str:
        return "oneinch_swap"

    @property
    def description(self) -> str:
        return """Execute a token swap via 1inch DEX aggregator.

1inch finds the best route across DEXes (Uniswap, Curve, etc.) and executes the swap.

IMPORTANT: For ERC-20 tokens, check allowance first with oneinch_check_allowance
and approve with oneinch_approve if needed. Native ETH needs no approval.

Parameters:
- chain: Network (ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis)
- src: Source token address (0xEeee...EEeE for native ETH)
- dst: Destination token address
- amount: Amount in wei
- slippage: Slippage tolerance in percent (default: 1.0)

Returns: transaction hash, estimated output amount"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain":    {"type": "string", "description": "Network name"},
                "src":      {"type": "string", "description": "Source token address"},
                "dst":      {"type": "string", "description": "Destination token address"},
                "amount":   {"type": "string", "description": "Amount in wei"},
                "slippage": {"type": "number", "description": "Slippage % (default 1.0)"},
            },
            "required": ["chain", "src", "dst", "amount"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", src: str = "", dst: str = "", amount: str = "", slippage: float = 1.0, **kwargs) -> ToolResult:
        if not all([chain, src, dst, amount]):
            return ToolResult(success=False, error="chain, src, dst, amount are all required")
        try:
            from tools.wallet import wallet_transfer_sync

            client = _get_client(chain)
            address = _get_address()

            swap_data = client.get_swap(src, dst, amount, address, slippage)
            tx = swap_data.get("tx", {})
            if not tx:
                return ToolResult(success=False, error="1inch API returned no transaction data")

            # Broadcast via Starchild wallet_transfer (no Fly Machine required)
            result = wallet_transfer_sync(
                to=tx["to"],
                amount=tx.get("value", "0"),
                data=tx.get("data", ""),
                chain_id=client.chain_id,
            )
            return ToolResult(success=True, output={
                "status": "swap_sent",
                "src": src,
                "dst": dst,
                "srcAmount": amount,
                "dstAmount": swap_data.get("dstAmount"),
                "tx": result,
            })
        except Exception as e:
            err = str(e)
            if "policy" in err.lower():
                return ToolResult(success=False, error=f"Policy violation: {err}. Use wallet_propose_policy to allow this operation.")
            return ToolResult(success=False, error=err)
