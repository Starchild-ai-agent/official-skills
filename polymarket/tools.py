"""
Polymarket Prediction Market Tools — CLI Wrapper Edition.

Uses the official Polymarket Rust CLI for all operations.
Users manage their own private keys via polymarket wallet commands.
"""

import logging
from typing import Optional

from core.tool import BaseTool, ToolContext, ToolResult
from .cli_wrapper import PolymarketCLI, PolymarketCLIError

logger = logging.getLogger(__name__)

# Module-level shared CLI instance
_cli: Optional[PolymarketCLI] = None


def _get_cli() -> PolymarketCLI:
    """Get or create Polymarket CLI instance."""
    global _cli
    if _cli is None:
        try:
            _cli = PolymarketCLI()
        except PolymarketCLIError as e:
            logger.error(f"Failed to initialize Polymarket CLI: {e}")
            raise
    return _cli


# ══════════════════════════════════════════════════════════════════════════
# Market Discovery Tools (6)
# ══════════════════════════════════════════════════════════════════════════


class PolymarketMarketsTool(BaseTool):
    """Browse and filter Polymarket prediction markets."""

    @property
    def name(self) -> str:
        return "polymarket_markets"

    @property
    def description(self) -> str:
        return """Browse and filter Polymarket prediction markets.

Parameters:
- status: "active" (default), "closed", or "all"
- sort: "volume", "liquidity", or "created_at" (newest first)
- limit: Number of results, 1-25 (default 10)
- offset: Pagination offset

Returns: List of markets with question, outcomes, prices, volume, liquidity"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter: active (default), closed, or all",
                    "enum": ["active", "closed", "all"],
                },
                "sort": {
                    "type": "string",
                    "description": "Sort by: volume, liquidity, or created_at",
                    "enum": ["volume", "liquidity", "created_at"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results (1-25, default 10)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset",
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        status: str = "active",
        sort: str = "volume",
        limit: int = 10,
        offset: int = 0,
        **kwargs,
    ) -> ToolResult:
        try:
            cli = _get_cli()
            limit = max(1, min(25, limit))

            # Map status to active/closed params
            active = None
            closed = None
            if status == "active":
                active = True
            elif status == "closed":
                closed = True

            markets = cli.markets_list(
                limit=limit,
                offset=offset,
                order=sort,
                active=active,
                closed=closed
            )

            return ToolResult(success=True, output={"markets": markets, "count": len(markets)})
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_markets: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketPriceTool(BaseTool):
    """Get live price/probability for a Polymarket market."""

    @property
    def name(self) -> str:
        return "polymarket_price"

    @property
    def description(self) -> str:
        return """Get live price/probability for a Polymarket prediction market.

Parameters:
- market_id: Market slug (e.g. "will-bitcoin-reach-100k") or condition ID

Returns: Market question, outcomes with probabilities, volume, liquidity"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "market_id": {
                    "type": "string",
                    "description": "Market slug or condition ID",
                },
            },
            "required": ["market_id"],
        }

    async def execute(self, ctx: ToolContext, market_id: str = "", **kwargs) -> ToolResult:
        if not market_id:
            return ToolResult(success=False, error="'market_id' is required")
        try:
            cli = _get_cli()
            market = cli.markets_get(market_id)

            if not market:
                return ToolResult(success=False, error=f"Market not found: {market_id}")

            return ToolResult(success=True, output=market)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_price: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketEventTool(BaseTool):
    """Get a Polymarket event with all child markets."""

    @property
    def name(self) -> str:
        return "polymarket_event"

    @property
    def description(self) -> str:
        return """Get a Polymarket event with all its child markets.

An event groups related markets (e.g. "2024 Election" contains multiple state/race markets).

Parameters:
- event_id: Event ID

Returns: Event title, description, and list of child markets"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Event ID",
                },
            },
            "required": ["event_id"],
        }

    async def execute(self, ctx: ToolContext, event_id: str = "", **kwargs) -> ToolResult:
        if not event_id:
            return ToolResult(success=False, error="'event_id' is required")
        try:
            cli = _get_cli()
            event = cli.events_get(event_id)

            if not event:
                return ToolResult(success=False, error=f"Event not found: {event_id}")

            return ToolResult(success=True, output=event)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_event: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketTagsTool(BaseTool):
    """List Polymarket market categories."""

    @property
    def name(self) -> str:
        return "polymarket_tags"

    @property
    def description(self) -> str:
        return """List all Polymarket market categories/tags.

Use these to filter markets.

Returns: List of categories with id, label, and slug"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            cli = _get_cli()
            tags = cli.tags_list()

            return ToolResult(success=True, output={"tags": tags, "count": len(tags)})
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_tags: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketBookTool(BaseTool):
    """Get orderbook depth for a Polymarket token."""

    @property
    def name(self) -> str:
        return "polymarket_book"

    @property
    def description(self) -> str:
        return """Get orderbook depth for a Polymarket CLOB token.

Shows bid/ask levels, spread, and liquidity.

Parameters:
- token_id: CLOB token ID (from polymarket_price output)

Returns: Bid/ask levels, best bid, best ask, spread"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "CLOB token ID",
                },
            },
            "required": ["token_id"],
        }

    async def execute(self, ctx: ToolContext, token_id: str = "", **kwargs) -> ToolResult:
        if not token_id:
            return ToolResult(success=False, error="'token_id' is required")
        try:
            cli = _get_cli()
            book = cli.clob_book(token_id)

            return ToolResult(success=True, output=book)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_book: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketLeaderboardTool(BaseTool):
    """Get top Polymarket traders leaderboard."""

    @property
    def name(self) -> str:
        return "polymarket_leaderboard"

    @property
    def description(self) -> str:
        return """Get top Polymarket traders ranked by profit.

Parameters:
- period: Time period — "week", "month", "year", or "all" (default)
- order_by: Sort field — "pnl", "volume", or "trades" (default: pnl)
- limit: Number of traders (default 10, max 25)

Returns: Ranked list of traders with profit, volume, number of trades"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Time period",
                    "enum": ["week", "month", "year", "all"],
                },
                "order_by": {
                    "type": "string",
                    "description": "Sort field",
                    "enum": ["pnl", "volume", "trades"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of traders (default 10, max 25)",
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        period: str = "month",
        order_by: str = "pnl",
        limit: int = 10,
        **kwargs,
    ) -> ToolResult:
        try:
            cli = _get_cli()
            limit = max(1, min(25, limit))
            leaderboard = cli.data_leaderboard(period=period, order_by=order_by, limit=limit)

            return ToolResult(success=True, output={"traders": leaderboard, "count": len(leaderboard)})
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_leaderboard: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


# ══════════════════════════════════════════════════════════════════════════
# Trading Tools (8) — Require Wallet Configuration
# ══════════════════════════════════════════════════════════════════════════


class PolymarketPlaceLimitOrderTool(BaseTool):
    """Place a limit order on Polymarket."""

    @property
    def name(self) -> str:
        return "polymarket_place_limit_order"

    @property
    def description(self) -> str:
        return """Place a limit order (GTC) on Polymarket.

Requires wallet configuration (polymarket wallet import <private_key>).

Parameters:
- token_id: CLOB token ID
- side: "buy" or "sell"
- price: Limit price (0.01-0.99, e.g., 0.65 for 65%)
- size: Order size in shares
- post_only: Maker-only mode (default false)

Returns: Order details with order_id"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {"type": "string", "description": "CLOB token ID"},
                "side": {"type": "string", "enum": ["buy", "sell"], "description": "Order side"},
                "price": {"type": "number", "description": "Limit price (0.01-0.99)"},
                "size": {"type": "number", "description": "Order size in shares"},
                "post_only": {"type": "boolean", "description": "Maker-only mode"},
            },
            "required": ["token_id", "side", "price", "size"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        token_id: str = "",
        side: str = "",
        price: float = 0,
        size: float = 0,
        post_only: bool = False,
        **kwargs,
    ) -> ToolResult:
        if not all([token_id, side, price, size]):
            return ToolResult(success=False, error="Missing required parameters")

        try:
            cli = _get_cli()
            order = cli.clob_create_order(
                token_id=token_id,
                side=side,
                price=price,
                size=size,
                post_only=post_only
            )

            return ToolResult(success=True, output=order)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_place_limit_order: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketPlaceMarketOrderTool(BaseTool):
    """Place a market order (FOK) on Polymarket."""

    @property
    def name(self) -> str:
        return "polymarket_place_market_order"

    @property
    def description(self) -> str:
        return """Place a market order (Fill-or-Kill) on Polymarket.

Market orders execute immediately at best available price or cancel.
Requires wallet configuration.

Parameters:
- token_id: CLOB token ID
- side: "buy" or "sell"
- amount: For BUY = dollars to spend, for SELL = shares to sell
- price: Worst acceptable price (slippage protection, optional)

Returns: Order details with order_id"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {"type": "string", "description": "CLOB token ID"},
                "side": {"type": "string", "enum": ["buy", "sell"], "description": "Order side"},
                "amount": {"type": "number", "description": "Amount ($ for buy, shares for sell)"},
                "price": {"type": "number", "description": "Worst acceptable price (slippage limit)"},
            },
            "required": ["token_id", "side", "amount"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        token_id: str = "",
        side: str = "",
        amount: float = 0,
        price: Optional[float] = None,
        **kwargs,
    ) -> ToolResult:
        if not all([token_id, side, amount]):
            return ToolResult(success=False, error="Missing required parameters")

        try:
            cli = _get_cli()
            order = cli.clob_market_order(
                token_id=token_id,
                side=side,
                amount=amount,
                price=price
            )

            return ToolResult(success=True, output=order)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_place_market_order: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketCancelOrderTool(BaseTool):
    """Cancel an order on Polymarket."""

    @property
    def name(self) -> str:
        return "polymarket_cancel_order"

    @property
    def description(self) -> str:
        return "Cancel a single order by ID (requires wallet configuration)"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID"},
            },
            "required": ["order_id"],
        }

    async def execute(self, ctx: ToolContext, order_id: str = "", **kwargs) -> ToolResult:
        if not order_id:
            return ToolResult(success=False, error="'order_id' is required")
        try:
            cli = _get_cli()
            result = cli.clob_cancel(order_id)
            return ToolResult(success=True, output=result)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_cancel_order: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketCancelAllOrdersTool(BaseTool):
    """Cancel all orders."""

    @property
    def name(self) -> str:
        return "polymarket_cancel_all_orders"

    @property
    def description(self) -> str:
        return """Cancel ALL open orders (requires wallet configuration).

Use with caution! Optionally filter by market."""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "market": {"type": "string", "description": "Filter by market condition ID (optional)"},
            },
        }

    async def execute(self, ctx: ToolContext, market: str = "", **kwargs) -> ToolResult:
        try:
            cli = _get_cli()
            result = cli.clob_cancel_all(market if market else None)
            return ToolResult(success=True, output=result)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_cancel_all_orders: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketGetOrdersTool(BaseTool):
    """Get open orders."""

    @property
    def name(self) -> str:
        return "polymarket_get_orders"

    @property
    def description(self) -> str:
        return "Get your open orders (requires wallet configuration)"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "market": {"type": "string", "description": "Filter by market condition ID (optional)"},
            },
        }

    async def execute(self, ctx: ToolContext, market: str = "", **kwargs) -> ToolResult:
        try:
            cli = _get_cli()
            orders = cli.clob_orders(market if market else None)
            return ToolResult(success=True, output={"orders": orders, "count": len(orders)})
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_get_orders: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketGetBalancesTool(BaseTool):
    """Get account balances."""

    @property
    def name(self) -> str:
        return "polymarket_get_balances"

    @property
    def description(self) -> str:
        return """Get your USDC collateral balance (requires wallet configuration).

Returns: Balance information"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            cli = _get_cli()
            balance = cli.clob_balance(asset_type="collateral")
            return ToolResult(success=True, output=balance)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_get_balances: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketGetPositionsTool(BaseTool):
    """Get user positions."""

    @property
    def name(self) -> str:
        return "polymarket_get_positions"

    @property
    def description(self) -> str:
        return """Get current open positions (requires wallet address).

Shows all markets where you hold position tokens.

Parameters:
- address: Wallet address to query positions for

Returns: List of positions with market info, size, current value, PnL"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Wallet address"},
            },
            "required": ["address"],
        }

    async def execute(self, ctx: ToolContext, address: str = "", **kwargs) -> ToolResult:
        if not address:
            return ToolResult(success=False, error="'address' is required")

        try:
            cli = _get_cli()
            positions = cli.data_positions(address)

            return ToolResult(success=True, output={"positions": positions, "count": len(positions)})
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_get_positions: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketGetTradesTool(BaseTool):
    """Get trade history."""

    @property
    def name(self) -> str:
        return "polymarket_get_trades"

    @property
    def description(self) -> str:
        return """Get your trade history (requires wallet configuration).

Parameters:
- limit: Number of trades (default 50, max 100)

Returns: List of historical trades"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of trades (default 50)"},
            },
        }

    async def execute(self, ctx: ToolContext, limit: int = 50, **kwargs) -> ToolResult:
        try:
            cli = _get_cli()
            limit = max(1, min(100, limit))
            trades = cli.clob_trades(limit)

            return ToolResult(success=True, output={"trades": trades, "count": len(trades)})
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_get_trades: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


# ══════════════════════════════════════════════════════════════════════════
# Contract Approval Tools (2) — NEW
# ══════════════════════════════════════════════════════════════════════════


class PolymarketCheckApprovalsTool(BaseTool):
    """Check contract approval status."""

    @property
    def name(self) -> str:
        return "polymarket_check_approvals"

    @property
    def description(self) -> str:
        return """Check ERC-20 and ERC-1155 contract approval status.

Before trading, Polymarket contracts need approvals for USDC (collateral) and CTF tokens.

Parameters:
- address: Wallet address to check (optional, defaults to configured wallet)

Returns: Approval status for each contract"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Wallet address (optional)"},
            },
        }

    async def execute(self, ctx: ToolContext, address: str = "", **kwargs) -> ToolResult:
        try:
            cli = _get_cli()
            approvals = cli.approve_check(address if address else None)

            return ToolResult(success=True, output=approvals)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_check_approvals: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketSetApprovalsTool(BaseTool):
    """Set all contract approvals (on-chain transaction)."""

    @property
    def name(self) -> str:
        return "polymarket_set_approvals"

    @property
    def description(self) -> str:
        return """Approve all Polymarket contracts for trading.

IMPORTANT: This sends 6 on-chain transactions and requires MATIC for gas.
Only needs to be done once per wallet.

Returns: Transaction hashes and status messages"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            cli = _get_cli()
            result = cli.approve_set()

            return ToolResult(success=True, output={"message": result})
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_set_approvals: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


# ══════════════════════════════════════════════════════════════════════════
# CTF Token Operation Tools (3) — NEW
# ══════════════════════════════════════════════════════════════════════════


class PolymarketCTFSplitTool(BaseTool):
    """Split collateral into conditional tokens."""

    @property
    def name(self) -> str:
        return "polymarket_ctf_split"

    @property
    def description(self) -> str:
        return """Split USDC collateral into conditional tokens (YES/NO shares).

This is an on-chain operation that converts USDC into outcome tokens.
Requires MATIC for gas fees.

Parameters:
- condition_id: Market condition ID (0x... format)
- amount: Amount in USDC to split (e.g., 10 = $10)

Returns: Transaction output with tx hash"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "condition_id": {"type": "string", "description": "Market condition ID (0x...)"},
                "amount": {"type": "number", "description": "Amount in USDC to split"},
            },
            "required": ["condition_id", "amount"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        condition_id: str = "",
        amount: float = 0,
        **kwargs,
    ) -> ToolResult:
        if not condition_id or amount <= 0:
            return ToolResult(success=False, error="Missing required parameters or invalid amount")

        try:
            cli = _get_cli()
            result = cli.ctf_split(condition_id, amount)

            return ToolResult(success=True, output={"message": result})
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_ctf_split: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketCTFMergeTool(BaseTool):
    """Merge conditional tokens back to collateral."""

    @property
    def name(self) -> str:
        return "polymarket_ctf_merge"

    @property
    def description(self) -> str:
        return """Merge conditional tokens (YES/NO shares) back into USDC collateral.

Requires holding BOTH outcome tokens in equal amounts.
On-chain operation requiring MATIC for gas.

Parameters:
- condition_id: Market condition ID (0x... format)
- amount: Amount to merge (in token units)

Returns: Transaction output with tx hash"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "condition_id": {"type": "string", "description": "Market condition ID (0x...)"},
                "amount": {"type": "number", "description": "Amount to merge"},
            },
            "required": ["condition_id", "amount"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        condition_id: str = "",
        amount: float = 0,
        **kwargs,
    ) -> ToolResult:
        if not condition_id or amount <= 0:
            return ToolResult(success=False, error="Missing required parameters or invalid amount")

        try:
            cli = _get_cli()
            result = cli.ctf_merge(condition_id, amount)

            return ToolResult(success=True, output={"message": result})
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_ctf_merge: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketCTFRedeemTool(BaseTool):
    """Redeem winning tokens after market resolution."""

    @property
    def name(self) -> str:
        return "polymarket_ctf_redeem"

    @property
    def description(self) -> str:
        return """Redeem winning conditional tokens for USDC after market resolution.

Only works for resolved markets. Winning tokens pay $1 per share.
On-chain operation requiring MATIC for gas.

Parameters:
- condition_id: Market condition ID (0x... format)

Returns: Transaction output with tx hash"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "condition_id": {"type": "string", "description": "Market condition ID (0x...)"},
            },
            "required": ["condition_id"],
        }

    async def execute(self, ctx: ToolContext, condition_id: str = "", **kwargs) -> ToolResult:
        if not condition_id:
            return ToolResult(success=False, error="'condition_id' is required")

        try:
            cli = _get_cli()
            result = cli.ctf_redeem(condition_id)

            return ToolResult(success=True, output={"message": result})
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_ctf_redeem: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


# ══════════════════════════════════════════════════════════════════════════
# Bridge Deposit Tools (2) — NEW
# ══════════════════════════════════════════════════════════════════════════


class PolymarketBridgeDepositTool(BaseTool):
    """Get deposit addresses for bridging to Polymarket."""

    @property
    def name(self) -> str:
        return "polymarket_bridge_deposit"

    @property
    def description(self) -> str:
        return """Get deposit addresses for bridging assets from other chains to Polygon.

Supports deposits from EVM chains, Solana, and Bitcoin.

Parameters:
- address: Your Polygon wallet address (destination)

Returns: Deposit addresses for each supported chain"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Destination Polygon address"},
            },
            "required": ["address"],
        }

    async def execute(self, ctx: ToolContext, address: str = "", **kwargs) -> ToolResult:
        if not address:
            return ToolResult(success=False, error="'address' is required")

        try:
            cli = _get_cli()
            deposit_addresses = cli.bridge_deposit(address)

            return ToolResult(success=True, output=deposit_addresses)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_bridge_deposit: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class PolymarketBridgeStatusTool(BaseTool):
    """Check bridge deposit status."""

    @property
    def name(self) -> str:
        return "polymarket_bridge_status"

    @property
    def description(self) -> str:
        return """Check status of bridge deposits (pending or completed).

Parameters:
- deposit_address: The deposit address to check

Returns: Status information with pending/completed deposits"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "deposit_address": {"type": "string", "description": "Deposit address to check"},
            },
            "required": ["deposit_address"],
        }

    async def execute(self, ctx: ToolContext, deposit_address: str = "", **kwargs) -> ToolResult:
        if not deposit_address:
            return ToolResult(success=False, error="'deposit_address' is required")

        try:
            cli = _get_cli()
            status = cli.bridge_status(deposit_address)

            return ToolResult(success=True, output=status)
        except PolymarketCLIError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in polymarket_bridge_status: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))
