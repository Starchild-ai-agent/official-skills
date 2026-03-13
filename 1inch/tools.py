"""
1inch DEX Aggregator Tools — BaseTool subclasses for agent use.

Read-only tools (3): oneinch_quote, oneinch_tokens, oneinch_check_allowance
Write tools (2): oneinch_approve, oneinch_swap

All tools require a `chain` parameter to specify the network.
"""

import logging
from typing import Dict

from core.tool import BaseTool, ToolContext, ToolResult
from .client import OneInchClient, NATIVE_TOKEN, SUPPORTED_CHAINS, resolve_chain

logger = logging.getLogger(__name__)

# Cache of clients per chain_id
_clients: Dict[int, OneInchClient] = {}


def _get_client(chain: str) -> OneInchClient:
    chain_id = resolve_chain(chain)
    if chain_id not in _clients:
        _clients[chain_id] = OneInchClient(chain_id=chain_id)
    return _clients[chain_id]


async def _get_address(chain: str) -> str:
    """Get the agent's EVM address."""
    return await _get_client(chain)._get_address()


# ── Read-Only Tools ──────────────────────────────────────────────────────────


class OneInchQuoteTool(BaseTool):
    """Get a swap quote from 1inch DEX aggregator."""

    @property
    def name(self) -> str:
        return "oneinch_quote"

    @property
    def description(self) -> str:
        return """Get a swap price quote from 1inch DEX aggregator.

Returns the estimated output amount and route info WITHOUT executing a swap.
Use this to check prices before swapping. Use oneinch_tokens to discover token addresses on the target chain.

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- src: Source token address (use 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE for native ETH)
- dst: Destination token address
- amount: Amount in wei (smallest unit, e.g. "1000000000000000000" = 1 ETH, "1000000" = 1 USDC)

Returns: dstAmount (estimated output in wei), gas estimate, route protocols"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {
                    "type": "string",
                    "description": "Network: arbitrum, ethereum, base, optimism, polygon, bsc, avalanche, gnosis",
                },
                "src": {
                    "type": "string",
                    "description": "Source token address",
                },
                "dst": {
                    "type": "string",
                    "description": "Destination token address",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount in wei (smallest unit)",
                },
            },
            "required": ["chain", "src", "dst", "amount"],
        }

    async def execute(
        self, ctx: ToolContext, chain: str = "", src: str = "", dst: str = "", amount: str = "", **kwargs
    ) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        if not src or not dst or not amount:
            return ToolResult(success=False, error="'src', 'dst', and 'amount' are required")
        try:
            client = _get_client(chain)
            data = await client.get_quote(src, dst, amount)
            return ToolResult(success=True, output=data)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OneInchTokensTool(BaseTool):
    """Search supported tokens on a network."""

    @property
    def name(self) -> str:
        return "oneinch_tokens"

    @property
    def description(self) -> str:
        return """List or search supported tokens on a network via 1inch.

Use this to find token addresses and decimals before quoting or swapping. Token addresses differ between networks.

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- search: (optional) Filter by token name or symbol (case-insensitive). Omit to list popular tokens.

Returns: array of {address, symbol, name, decimals} (max 20 results)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {
                    "type": "string",
                    "description": "Network: arbitrum, ethereum, base, optimism, polygon, bsc, avalanche, gnosis",
                },
                "search": {
                    "type": "string",
                    "description": "Filter by name or symbol (optional)",
                },
            },
            "required": ["chain"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", search: str = "", **kwargs) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        try:
            client = _get_client(chain)
            data = await client.get_tokens()

            # API returns {"tokens": {"0x...": {...}, ...}}
            token_map = data.get("tokens", data) if isinstance(data, dict) else data
            tokens = list(token_map.values()) if isinstance(token_map, dict) else token_map

            if search:
                query = search.lower()
                tokens = [
                    t for t in tokens
                    if query in t.get("symbol", "").lower()
                    or query in t.get("name", "").lower()
                ]

            # Return compact info, limited to 20
            result = [
                {
                    "address": t.get("address"),
                    "symbol": t.get("symbol"),
                    "name": t.get("name"),
                    "decimals": t.get("decimals"),
                }
                for t in tokens[:20]
            ]

            return ToolResult(success=True, output={"tokens": result, "count": len(result)})
        except ValueError as e:
            return ToolResult(success=False, error=str(e))
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

Native ETH does not need approval. ERC-20 tokens (USDC, WETH, etc.) must be approved before swapping.

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- token_address: ERC-20 token address to check

Returns: allowance amount, whether approval is needed"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {
                    "type": "string",
                    "description": "Network: arbitrum, ethereum, base, optimism, polygon, bsc, avalanche, gnosis",
                },
                "token_address": {
                    "type": "string",
                    "description": "ERC-20 token address to check",
                },
            },
            "required": ["chain", "token_address"],
        }

    async def execute(
        self, ctx: ToolContext, chain: str = "", token_address: str = "", **kwargs
    ) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        if not token_address:
            return ToolResult(success=False, error="'token_address' is required")

        # Native ETH never needs approval
        if token_address.lower() == NATIVE_TOKEN.lower():
            return ToolResult(
                success=True,
                output={"allowance": "unlimited", "needs_approval": False, "note": "Native ETH does not need approval"},
            )

        try:
            client = _get_client(chain)
            address = await _get_address(chain)
            data = await client.get_allowance(token_address, address)
            allowance = data.get("allowance", "0")
            needs_approval = allowance == "0"
            return ToolResult(
                success=True,
                output={
                    "allowance": allowance,
                    "needs_approval": needs_approval,
                    "token": token_address,
                    "wallet": address,
                },
            )
        except ValueError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Write Tools (require wallet) ────────────────────────────────────────────


class OneInchApproveTool(BaseTool):
    """Approve a token for 1inch router spending."""

    @property
    def name(self) -> str:
        return "oneinch_approve"

    @property
    def description(self) -> str:
        return """Approve an ERC-20 token for the 1inch router.

This sends an on-chain approval transaction so the 1inch router can spend your tokens.
Required before swapping ERC-20 tokens (not needed for native ETH).

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- token_address: ERC-20 token address to approve (use oneinch_tokens to find addresses)
- amount: (optional) Amount to approve in wei. Omit for unlimited approval.

Returns: transaction hash"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {
                    "type": "string",
                    "description": "Network: arbitrum, ethereum, base, optimism, polygon, bsc, avalanche, gnosis",
                },
                "token_address": {
                    "type": "string",
                    "description": "ERC-20 token address to approve",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount to approve in wei (omit for unlimited)",
                },
            },
            "required": ["chain", "token_address"],
        }

    async def execute(
        self, ctx: ToolContext, chain: str = "", token_address: str = "", amount: str = "", **kwargs
    ) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        if not token_address:
            return ToolResult(success=False, error="'token_address' is required")

        from tools.wallet import _wallet_request, _is_fly_machine

        if not _is_fly_machine():
            return ToolResult(
                success=False,
                error="Not running on a Fly Machine — wallet unavailable",
            )

        try:
            client = _get_client(chain)
            tx_data = await client.get_approve_transaction(
                token_address, amount=amount if amount else None
            )

            # Broadcast approval tx via wallet service
            resp = await _wallet_request("POST", "/agent/transfer", {
                "to": tx_data["to"],
                "amount": tx_data.get("value", "0"),
                "data": tx_data["data"],
                "chain_id": client.chain_id,
            })

            return ToolResult(
                success=True,
                output={
                    "status": "approval_sent",
                    "token": token_address,
                    "tx": resp,
                },
            )
        except ValueError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            error_msg = str(e)
            if "policy" in error_msg.lower():
                return ToolResult(
                    success=False,
                    error=f"Policy violation: {error_msg}. "
                          f"The wallet policy does not allow this operation. "
                          f"Use wallet_propose_policy to propose a policy that allows "
                          f"this transaction. Inform the user what policy change is needed."
                )
            return ToolResult(success=False, error=error_msg)


class OneInchSwapTool(BaseTool):
    """Execute a token swap via 1inch."""

    @property
    def name(self) -> str:
        return "oneinch_swap"

    @property
    def description(self) -> str:
        return """Execute a token swap via 1inch DEX aggregator.

1inch finds the best route across DEXes (Uniswap, SushiSwap, Curve, etc.) and executes the swap.

IMPORTANT: For ERC-20 source tokens, check allowance first with oneinch_check_allowance and approve with oneinch_approve if needed. Native ETH swaps do not need approval. Use oneinch_tokens to discover token addresses on the target chain.

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- src: Source token address (use 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE for native ETH)
- dst: Destination token address
- amount: Amount in wei (smallest unit)
- slippage: Slippage tolerance in percent (default: 1.0)

Returns: transaction hash, estimated output amount"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {
                    "type": "string",
                    "description": "Network: arbitrum, ethereum, base, optimism, polygon, bsc, avalanche, gnosis",
                },
                "src": {
                    "type": "string",
                    "description": "Source token address",
                },
                "dst": {
                    "type": "string",
                    "description": "Destination token address",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount in wei (smallest unit)",
                },
                "slippage": {
                    "type": "number",
                    "description": "Slippage tolerance in percent (default: 1.0)",
                },
            },
            "required": ["chain", "src", "dst", "amount"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        chain: str = "",
        src: str = "",
        dst: str = "",
        amount: str = "",
        slippage: float = 1.0,
        **kwargs,
    ) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        if not src or not dst or not amount:
            return ToolResult(success=False, error="'src', 'dst', and 'amount' are required")

        from tools.wallet import _wallet_request, _is_fly_machine

        if not _is_fly_machine():
            return ToolResult(
                success=False,
                error="Not running on a Fly Machine — wallet unavailable",
            )

        try:
            client = _get_client(chain)
            address = await _get_address(chain)

            # Get swap tx data from 1inch
            swap_data = await client.get_swap(src, dst, amount, address, slippage)

            tx = swap_data.get("tx", {})
            if not tx:
                return ToolResult(success=False, error="1inch API returned no transaction data")

            # Broadcast swap tx via wallet service
            resp = await _wallet_request("POST", "/agent/transfer", {
                "to": tx["to"],
                "amount": tx.get("value", "0"),
                "data": tx["data"],
                "chain_id": client.chain_id,
            })

            return ToolResult(
                success=True,
                output={
                    "status": "swap_sent",
                    "src": src,
                    "dst": dst,
                    "srcAmount": amount,
                    "dstAmount": swap_data.get("dstAmount"),
                    "tx": resp,
                },
            )
        except ValueError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            error_msg = str(e)
            if "policy" in error_msg.lower():
                return ToolResult(
                    success=False,
                    error=f"Policy violation: {error_msg}. "
                          f"The wallet policy does not allow this operation. "
                          f"Use wallet_propose_policy to propose a policy that allows "
                          f"this transaction. Inform the user what policy change is needed."
                )
            return ToolResult(success=False, error=error_msg)
