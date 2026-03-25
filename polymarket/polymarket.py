"""
Polymarket Tool Wrappers

API-based tools for Polymarket prediction markets.
Provides market discovery, research, and trading capabilities.
"""
import asyncio
import logging
import json
from typing import Any, Dict, Optional

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

# Import functions from tools directory
try:
    from .tools.auth import build_clob_auth_message, derive_api_credentials
    from .tools.market_data import (
        full_lookup,
        search_markets,
        analyze_orderbook,
        rr_analysis,
    )
    from .tools.trading import (
        get_balance,
        get_open_orders,
        get_trades,
        get_positions,
        cancel_order,
        cancel_all_orders,
        build_order_payload,
        post_signed_order,
    )
    from .tools.utils import BASE
    POLYMARKET_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Polymarket tools not available: {e}")
    POLYMARKET_AVAILABLE = False


# ==================== Authentication Tools ====================


class PolymarketAuthTool(BaseTool):
    """
    Create Polymarket API credentials via EIP-712 signing.
    One-time setup to get API key/secret/passphrase.
    """

    @property
    def name(self) -> str:
        return "polymarket_auth"

    @property
    def description(self) -> str:
        return """Create Polymarket API credentials (one-time setup).

Returns EIP-712 message to sign with wallet_sign_typed_data.
After signing, call again with signature to get credentials.

Examples:
- Get message to sign: polymarket_auth(wallet_address="0x...")
- Submit signature: polymarket_auth(wallet_address="0x...", signature="0x...", timestamp=...)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "wallet_address": {
                    "type": "string",
                    "description": "Your Polygon wallet address",
                },
                "signature": {
                    "type": "string",
                    "description": "Signed EIP-712 message (if already signed)",
                },
                "timestamp": {
                    "type": "integer",
                    "description": "Server timestamp from previous call",
                },
            },
            "required": ["wallet_address"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        wallet_address: str,
        signature: Optional[str] = None,
        timestamp: Optional[int] = None,
    ) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            if not signature:
                # Step 1: Build message to sign
                import time

                ts = int(time.time())
                message = await asyncio.to_thread(
                    build_clob_auth_message, wallet_address, ts
                )
                return ToolResult(
                    success=True,
                    output={
                        "step": "sign",
                        "timestamp": ts,
                        "eip712_message": message,
                        "instructions": "Sign this message with wallet_sign_typed_data, then call this tool again with signature and timestamp",
                    },
                )
            else:
                # Step 2: Derive credentials
                creds = await asyncio.to_thread(
                    derive_api_credentials, signature, wallet_address, timestamp or 0
                )
                return ToolResult(
                    success=True,
                    output={
                        "step": "complete",
                        "credentials": creds,
                        "instructions": "Save these to .env: POLY_API_KEY, POLY_SECRET, POLY_PASSPHRASE, POLY_WALLET",
                    },
                )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Market Discovery Tools ====================


class PolymarketLookupTool(BaseTool):
    """
    Look up Polymarket event or market from URL or slug.
    Returns enriched data with live prices.
    """

    @property
    def name(self) -> str:
        return "polymarket_lookup"

    @property
    def description(self) -> str:
        return """Look up Polymarket market from URL or slug.

Returns full market details including live prices, outcomes, volume, resolution criteria.

Examples:
- By URL: polymarket_lookup(url_or_slug="https://polymarket.com/event/will-trump-win")
- By slug: polymarket_lookup(url_or_slug="will-trump-win")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url_or_slug": {
                    "type": "string",
                    "description": "Polymarket URL or event/market slug",
                }
            },
            "required": ["url_or_slug"],
        }

    async def execute(
        self, ctx: ToolContext, url_or_slug: str
    ) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            result = await asyncio.to_thread(full_lookup, url_or_slug)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketSearchTool(BaseTool):
    """
    Search for Polymarket markets.
    """

    @property
    def name(self) -> str:
        return "polymarket_search"

    @property
    def description(self) -> str:
        return """Search for Polymarket markets by keyword.

Returns active markets matching query.

Examples:
- Search: polymarket_search(query="trump election")
- Limited results: polymarket_search(query="bitcoin", limit=5)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(
        self, ctx: ToolContext, query: str, limit: int = 5
    ) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            result = await asyncio.to_thread(search_markets, query, limit)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketOrderbookTool(BaseTool):
    """
    Analyze orderbook depth and spread for a token.
    """

    @property
    def name(self) -> str:
        return "polymarket_orderbook"

    @property
    def description(self) -> str:
        return """Analyze orderbook for a Polymarket outcome token.

Returns bid/ask levels, spread, liquidity depth, top levels.

Examples:
- Analyze orderbook: polymarket_orderbook(token_id="123456")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "CLOB token ID from market lookup",
                }
            },
            "required": ["token_id"],
        }

    async def execute(self, ctx: ToolContext, token_id: str) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            result = await asyncio.to_thread(analyze_orderbook, token_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketRRAnalysisTool(BaseTool):
    """
    Risk/reward analysis for a potential trade.
    """

    @property
    def name(self) -> str:
        return "polymarket_rr_analysis"

    @property
    def description(self) -> str:
        return """Calculate risk/reward for a Polymarket trade.

Returns entry price, tokens, profit/loss scenarios, R/R ratio.

Examples:
- Analyze YES bet: polymarket_rr_analysis(token_id="123456", side="YES", size_usd=100)
- Analyze NO bet: polymarket_rr_analysis(token_id="789012", side="NO", size_usd=50)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "CLOB token ID",
                },
                "side": {
                    "type": "string",
                    "description": "YES or NO",
                },
                "size_usd": {
                    "type": "number",
                    "description": "Amount in USD to bet",
                },
            },
            "required": ["token_id", "side", "size_usd"],
        }

    async def execute(
        self, ctx: ToolContext, token_id: str, side: str, size_usd: float
    ) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            result = await asyncio.to_thread(rr_analysis, token_id, side, size_usd)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Trading Tools ====================


class PolymarketGetBalanceTool(BaseTool):
    """
    Get USDC balance and allowance.
    """

    @property
    def name(self) -> str:
        return "polymarket_get_balance"

    @property
    def description(self) -> str:
        return """Get USDC balance and allowance on Polymarket.

Requires API credentials configured in .env.

Examples:
- Check balance: polymarket_get_balance()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            result = await asyncio.to_thread(get_balance)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketGetOrdersTool(BaseTool):
    """
    Get all open orders.
    """

    @property
    def name(self) -> str:
        return "polymarket_get_orders"

    @property
    def description(self) -> str:
        return """Get all open orders on Polymarket.

Requires API credentials.

Examples:
- List orders: polymarket_get_orders()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            result = await asyncio.to_thread(get_open_orders)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketGetPositionsTool(BaseTool):
    """
    Get current positions.
    """

    @property
    def name(self) -> str:
        return "polymarket_get_positions"

    @property
    def description(self) -> str:
        return """Get current positions on Polymarket.

Requires API credentials.

Examples:
- View positions: polymarket_get_positions()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            result = await asyncio.to_thread(get_positions)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketGetTradesTool(BaseTool):
    """
    Get recent trade history.
    """

    @property
    def name(self) -> str:
        return "polymarket_get_trades"

    @property
    def description(self) -> str:
        return """Get recent trade history on Polymarket.

Requires API credentials.

Examples:
- Get trades: polymarket_get_trades()
- Limited: polymarket_get_trades(limit=10)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 20)",
                    "default": 20,
                }
            },
        }

    async def execute(self, ctx: ToolContext, limit: int = 20) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            result = await asyncio.to_thread(get_trades, limit)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketQuickPrepareTool(BaseTool):
    """
    🚀 FAST: One-shot bet preparation combining balance/orderbook/R-R/order-prep.
    Use this instead of separate calls for faster execution.
    """

    @property
    def name(self) -> str:
        return "polymarket_quick_prepare"

    @property
    def description(self) -> str:
        return """🚀 FAST: Prepare bet in ONE call (balance + orderbook + R/R + order prep).

This is optimized for speed - combines multiple operations into one tool call.

Examples:
- Quick prep: polymarket_quick_prepare(token_id="123456", side="YES", size_usd=10)
- With override: polymarket_quick_prepare(token_id="789012", side="NO", size_usd=50, price_override=0.45)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "CLOB token ID from market lookup",
                },
                "side": {
                    "type": "string",
                    "description": "YES or NO",
                },
                "size_usd": {
                    "type": "number",
                    "description": "Amount in USD to bet",
                },
                "price_override": {
                    "type": "number",
                    "description": "Override best price from orderbook (optional)",
                },
                "neg_risk": {
                    "type": "boolean",
                    "description": "Use neg-risk exchange (default false)",
                    "default": False,
                },
                "tick_size": {
                    "type": "string",
                    "description": "Price tick size (default 0.01)",
                    "default": "0.01",
                },
            },
            "required": ["token_id", "side", "size_usd"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        token_id: str,
        side: str,
        size_usd: float,
        price_override: Optional[float] = None,
        neg_risk: bool = False,
        tick_size: str = "0.01",
    ) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            # Run balance + orderbook in parallel for speed
            balance_task = asyncio.to_thread(get_balance)
            orderbook_task = asyncio.to_thread(analyze_orderbook, token_id)

            balance, orderbook = await asyncio.gather(balance_task, orderbook_task)

            # Determine entry price from orderbook
            if price_override:
                entry_price = price_override
            elif side.upper() == "YES":
                entry_price = orderbook["best_ask"]
            else:
                entry_price = 1 - orderbook["best_bid"]

            # Calculate tokens and R/R
            tokens = size_usd / entry_price
            profit_if_win = tokens - size_usd
            rr_ratio = profit_if_win / size_usd if size_usd > 0 else 0

            # Build order payload
            order_side = "BUY" if side.upper() == "YES" else "SELL"
            domain, types, message, meta = await asyncio.to_thread(
                build_order_payload, token_id, order_side, entry_price, tokens, neg_risk, tick_size, None
            )

            return ToolResult(
                success=True,
                output={
                    "balance": {
                        "usdc": float(balance.get("balance", 0)) / 1e6,
                        "allowance": float(balance.get("allowance", 0)) / 1e6,
                    },
                    "orderbook": {
                        "best_bid": orderbook["best_bid"],
                        "best_ask": orderbook["best_ask"],
                        "spread": orderbook["spread"],
                        "spread_pct": orderbook["spread_pct"],
                    },
                    "trade": {
                        "side": side.upper(),
                        "entry_price": round(entry_price, 4),
                        "implied_probability": f"{entry_price*100:.1f}%",
                        "size_usd": round(size_usd, 2),
                        "tokens": round(tokens, 2),
                        "profit_if_win": round(profit_if_win, 2),
                        "loss_if_lose": round(size_usd, 2),
                        "risk_reward_ratio": f"1:{round(rr_ratio, 2)}",
                    },
                    "eip712": {
                        "domain": domain,
                        "types": types,
                        "primaryType": "Order",
                        "message": message,
                    },
                    "meta": meta,
                    "instructions": "Review trade details, then sign eip712 with wallet_sign_typed_data. Use polymarket_post_order with signature and meta to execute.",
                },
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketPrepareOrderTool(BaseTool):
    """
    Prepare order payload for EIP-712 signing.
    """

    @property
    def name(self) -> str:
        return "polymarket_prepare_order"

    @property
    def description(self) -> str:
        return """Prepare Polymarket order for signing.

Returns EIP-712 message to sign with wallet_sign_typed_data.

Examples:
- Buy order: polymarket_prepare_order(token_id="123456", side="BUY", price=0.65, size=100)
- Sell order: polymarket_prepare_order(token_id="789012", side="SELL", price=0.35, size=50)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "CLOB token ID",
                },
                "side": {
                    "type": "string",
                    "description": "BUY or SELL",
                },
                "price": {
                    "type": "number",
                    "description": "Order price (0.01-0.99)",
                },
                "size": {
                    "type": "number",
                    "description": "Order size in tokens",
                },
                "neg_risk": {
                    "type": "boolean",
                    "description": "Use neg-risk exchange (default false)",
                    "default": False,
                },
                "tick_size": {
                    "type": "string",
                    "description": "Price tick size (default 0.01)",
                    "default": "0.01",
                },
                "fee_bps": {
                    "type": "integer",
                    "description": "Fee rate in basis points (auto-queries from market if not provided)",
                },
            },
            "required": ["token_id", "side", "price", "size"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        token_id: str,
        side: str,
        price: float,
        size: float,
        neg_risk: bool = False,
        tick_size: str = "0.01",
        fee_bps: int = None,
    ) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            domain, types, message, meta = await asyncio.to_thread(
                build_order_payload, token_id, side, price, size, neg_risk, tick_size, fee_bps
            )
            return ToolResult(
                success=True,
                output={
                    "eip712": {
                        "domain": domain,
                        "types": types,
                        "primaryType": "Order",
                        "message": message,
                    },
                    "meta": meta,
                    "instructions": "Sign this with wallet_sign_typed_data, then use polymarket_post_order with signature and meta",
                },
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketPostOrderTool(BaseTool):
    """
    Post a signed order to CLOB.
    """

    @property
    def name(self) -> str:
        return "polymarket_post_order"

    @property
    def description(self) -> str:
        return """Post signed order to Polymarket CLOB.

Requires signature from wallet_sign_typed_data and meta from prepare_order.

Examples:
- Post order: polymarket_post_order(token_id="123456", signature="0x...", meta={...})"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "CLOB token ID",
                },
                "signature": {
                    "type": "string",
                    "description": "EIP-712 signature from wallet",
                },
                "meta": {
                    "type": "object",
                    "description": "Metadata from prepare_order",
                },
            },
            "required": ["token_id", "signature", "meta"],
        }

    async def execute(
        self, ctx: ToolContext, token_id: str, signature: str, meta: Dict[str, Any]
    ) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            status_code, response = await asyncio.to_thread(
                post_signed_order, token_id, signature, meta
            )
            return ToolResult(
                success=(200 <= status_code < 300),
                output={"status_code": status_code, "response": response},
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketCancelOrderTool(BaseTool):
    """
    Cancel a specific order.
    """

    @property
    def name(self) -> str:
        return "polymarket_cancel_order"

    @property
    def description(self) -> str:
        return """Cancel a specific Polymarket order.

Examples:
- Cancel: polymarket_cancel_order(order_id="abc123...")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Order ID to cancel",
                }
            },
            "required": ["order_id"],
        }

    async def execute(self, ctx: ToolContext, order_id: str) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            status_code, response = await asyncio.to_thread(cancel_order, order_id)
            return ToolResult(
                success=(200 <= status_code < 300),
                output={"status_code": status_code, "response": response},
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PolymarketCancelAllTool(BaseTool):
    """
    Cancel all open orders.
    """

    @property
    def name(self) -> str:
        return "polymarket_cancel_all"

    @property
    def description(self) -> str:
        return """Cancel ALL open Polymarket orders.

WARNING: Use with caution!

Examples:
- Cancel all: polymarket_cancel_all()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not POLYMARKET_AVAILABLE:
            return ToolResult(
                success=False, output=None, error="Polymarket tools not available"
            )

        try:
            status_code, response = await asyncio.to_thread(cancel_all_orders)
            return ToolResult(
                success=(200 <= status_code < 300),
                output={"status_code": status_code, "response": response},
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
