"""
Orderly Network Trading Tools — BaseTool subclasses for agent use.

Public tools (8):  orderly_system_info, orderly_futures, orderly_funding,
                   orderly_volume, orderly_orderbook, orderly_kline,
                   orderly_market, orderly_chain_info
Private tools (6): orderly_account, orderly_holdings, orderly_positions,
                   orderly_orders, orderly_trades, orderly_liquidations
Trading tools (5): orderly_order, orderly_modify, orderly_cancel,
                   orderly_cancel_all, orderly_leverage
Fund tools (2):    orderly_deposit, orderly_withdraw
"""

import logging

from core.tool import BaseTool, ToolContext, ToolResult
from .client import OrderlyClient, _get_client

logger = logging.getLogger(__name__)


# ── Public / Market Data Tools (8) — No Auth ────────────────────────────────


class OrderlySystemInfoTool(BaseTool):
    """Get Orderly system maintenance status."""

    @property
    def name(self) -> str:
        return "orderly_system_info"

    @property
    def description(self) -> str:
        return """Get Orderly Network system status and maintenance information.

Use this to check if the exchange is operational before placing trades.

Returns: system status, maintenance windows"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            data = await client.get_system_info()
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyFuturesTool(BaseTool):
    """Get futures instrument info."""

    @property
    def name(self) -> str:
        return "orderly_futures"

    @property
    def description(self) -> str:
        return """Get Orderly futures instrument information.

If symbol is specified, returns details for that instrument. Otherwise returns all futures.

Parameters:
- symbol: (optional) Specific symbol like "PERP_BTC_USDC". Or just "BTC" — auto-expanded.

Returns: instrument details (tick sizes, lot sizes, max leverage, base/quote info)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol (e.g. 'BTC' or 'PERP_BTC_USDC'). Omit for all.",
                },
            },
        }

    async def execute(self, ctx: ToolContext, symbol: str = "", **kwargs) -> ToolResult:
        try:
            client = _get_client()
            if symbol:
                resolved = client._resolve_symbol(symbol)
                data = await client.get_futures(resolved)
            else:
                data = await client.get_futures()
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyFundingTool(BaseTool):
    """Get funding rate info."""

    @property
    def name(self) -> str:
        return "orderly_funding"

    @property
    def description(self) -> str:
        return """Get funding rate information for Orderly perps.

Shows current funding rate and recent history. Positive = longs pay shorts.

Parameters:
- symbol: Asset name or full symbol (required, e.g. "BTC" or "PERP_BTC_USDC")
- history: If true, also fetch funding rate history (default: false)

Returns: current funding rate, and optionally historical rates"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC') or full symbol",
                },
                "history": {
                    "type": "boolean",
                    "description": "Include funding history (default: false)",
                },
            },
            "required": ["symbol"],
        }

    async def execute(
        self, ctx: ToolContext, symbol: str = "", history: bool = False, **kwargs
    ) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="'symbol' is required")
        try:
            client = _get_client()
            resolved = client._resolve_symbol(symbol)
            current = await client.get_funding_rate(resolved)
            result = {"current": current}
            if history:
                hist = await client.get_funding_rate_history(resolved)
                result["history"] = hist
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyVolumeTool(BaseTool):
    """Get volume statistics."""

    @property
    def name(self) -> str:
        return "orderly_volume"

    @property
    def description(self) -> str:
        return """Get Orderly Network volume statistics.

Returns: 24h volume, open interest, and other aggregate stats"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            data = await client.get_volume_stats()
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOrderbookTool(BaseTool):
    """Get orderbook snapshot."""

    @property
    def name(self) -> str:
        return "orderly_orderbook"

    @property
    def description(self) -> str:
        return """Get the orderbook for an Orderly asset.

Shows current bid/ask levels with sizes. Useful for checking liquidity and spread.

Parameters:
- symbol: Asset name or full symbol (required, e.g. "BTC" or "PERP_BTC_USDC")
- max_level: Number of price levels (default: 20)

Returns: asks and bids arrays with [price, quantity] entries"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC') or full symbol",
                },
                "max_level": {
                    "type": "integer",
                    "description": "Number of price levels (default: 20)",
                },
            },
            "required": ["symbol"],
        }

    async def execute(
        self, ctx: ToolContext, symbol: str = "", max_level: int = 20, **kwargs
    ) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="'symbol' is required")
        try:
            client = _get_client()
            resolved = client._resolve_symbol(symbol)
            data = await client.get_orderbook(resolved, max_level)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyKlineTool(BaseTool):
    """Get OHLCV candlestick data."""

    @property
    def name(self) -> str:
        return "orderly_kline"

    @property
    def description(self) -> str:
        return """Get OHLCV candlestick data for an Orderly asset.

Use this for price analysis, charting, and identifying trends.

Parameters:
- symbol: Asset name or full symbol (required, e.g. "BTC" or "PERP_BTC_USDC")
- interval: Candle interval (default: "1h"). Options: 1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w
- limit: Number of candles (default: 100, max: 1000)

Returns: array of candles with open, high, low, close, volume, timestamp"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC') or full symbol",
                },
                "interval": {
                    "type": "string",
                    "description": "Candle interval: 1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w (default: 1h)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of candles (default: 100)",
                },
            },
            "required": ["symbol"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str = "",
        interval: str = "1h",
        limit: int = 100,
        **kwargs,
    ) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="'symbol' is required")
        try:
            client = _get_client()
            resolved = client._resolve_symbol(symbol)
            data = await client.get_kline(resolved, interval, limit)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyMarketTool(BaseTool):
    """Get market overview — futures + recent trades."""

    @property
    def name(self) -> str:
        return "orderly_market"

    @property
    def description(self) -> str:
        return """Get market overview for Orderly futures.

If symbol is specified, returns instrument details and recent market trades.
Otherwise returns all futures instruments.

Parameters:
- symbol: (optional) Asset name (e.g. "BTC") or full symbol. Omit for all instruments.

Returns: futures info and optionally recent market trades"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC'). Omit for all.",
                },
            },
        }

    async def execute(self, ctx: ToolContext, symbol: str = "", **kwargs) -> ToolResult:
        try:
            client = _get_client()
            if symbol:
                resolved = client._resolve_symbol(symbol)
                futures = await client.get_futures(resolved)
                trades = await client.get_market_trades(resolved, limit=20)
                return ToolResult(
                    success=True,
                    output={"instrument": futures, "recent_trades": trades},
                )
            else:
                data = await client.get_futures()
                return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyChainInfoTool(BaseTool):
    """Get chain and broker configuration."""

    @property
    def name(self) -> str:
        return "orderly_chain_info"

    @property
    def description(self) -> str:
        return """Get Orderly chain and broker configuration.

Returns: supported chains, broker info, deposit/withdrawal config"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            data = await client.get_chain_info()
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Private / Account Tools (6) — Ed25519 Auth ──────────────────────────────


class OrderlyAccountTool(BaseTool):
    """Get account info (fees, tier, etc.)."""

    @property
    def name(self) -> str:
        return "orderly_account"

    @property
    def description(self) -> str:
        return """Get Orderly account information: fee tier, maker/taker rates, account status.

Use this to check your fee rates and account tier.

Returns: account_id, fee tier, maker/taker fee rates, account status"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            data = await client.get_account_info()
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyHoldingsTool(BaseTool):
    """Get asset balances (holdings)."""

    @property
    def name(self) -> str:
        return "orderly_holdings"

    @property
    def description(self) -> str:
        return """Get Orderly asset balances (holdings).

Shows available and frozen balances for all assets in the account.

Returns: array of holdings with token, holding (available), frozen, pending_short"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            data = await client.get_holdings()
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyPositionsTool(BaseTool):
    """Get open positions."""

    @property
    def name(self) -> str:
        return "orderly_positions"

    @property
    def description(self) -> str:
        return """Get all open positions on Orderly.

Use this to check current perp portfolio, position sizes, entry prices, and unrealized PnL.

Returns: array of positions with symbol, position_qty, cost_position, unsettled_pnl, mark_price"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            data = await client.get_positions()
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOrdersTool(BaseTool):
    """List orders."""

    @property
    def name(self) -> str:
        return "orderly_orders"

    @property
    def description(self) -> str:
        return """Get orders on Orderly (open and/or historical).

Parameters:
- symbol: (optional) Filter by symbol (e.g. "BTC" or "PERP_BTC_USDC")
- status: (optional) Filter by status: "INCOMPLETE" (open), "COMPLETED", "CANCELLED"
- limit: Number of orders to return (default: 50)

Returns: array of orders with order_id, symbol, side, type, price, quantity, status"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol filter (e.g. 'BTC'). Omit for all.",
                },
                "status": {
                    "type": "string",
                    "enum": ["INCOMPLETE", "COMPLETED", "CANCELLED"],
                    "description": "Order status filter",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of orders (default: 50)",
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str = "",
        status: str = "",
        limit: int = 50,
        **kwargs,
    ) -> ToolResult:
        try:
            client = _get_client()
            resolved = client._resolve_symbol(symbol) if symbol else None
            data = await client.get_orders(
                symbol=resolved, status=status or None, limit=limit
            )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyTradesTool(BaseTool):
    """Get trade/fill history."""

    @property
    def name(self) -> str:
        return "orderly_trades"

    @property
    def description(self) -> str:
        return """Get trade (fill) history on Orderly.

Use this to verify if orders were filled, check execution prices, or review trade history.

Parameters:
- symbol: (optional) Filter by symbol (e.g. "BTC" or "PERP_BTC_USDC")
- limit: Number of trades to return (default: 50)

Returns: array of trades with symbol, side, executed_price, executed_quantity, fee, timestamp"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol filter (e.g. 'BTC'). Omit for all.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of trades (default: 50)",
                },
            },
        }

    async def execute(
        self, ctx: ToolContext, symbol: str = "", limit: int = 50, **kwargs
    ) -> ToolResult:
        try:
            client = _get_client()
            resolved = client._resolve_symbol(symbol) if symbol else None
            data = await client.get_trades(symbol=resolved, limit=limit)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyLiquidationsTool(BaseTool):
    """Get liquidation history."""

    @property
    def name(self) -> str:
        return "orderly_liquidations"

    @property
    def description(self) -> str:
        return """Get liquidation history for the account.

Use this to review past liquidation events.

Parameters:
- limit: Number of liquidations to return (default: 50)

Returns: array of liquidation records"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of liquidations (default: 50)",
                },
            },
        }

    async def execute(self, ctx: ToolContext, limit: int = 50, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            data = await client.get_liquidations(limit=limit)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Trading Tools (5) — Ed25519 Auth ────────────────────────────────────────


class OrderlyOrderTool(BaseTool):
    """Create an order (limit/market/IOC/FOK/post-only)."""

    @property
    def name(self) -> str:
        return "orderly_order"

    @property
    def description(self) -> str:
        return """Place an order on Orderly Network (perpetual futures or spot).

Parameters:
- symbol: Asset name or full symbol (required, e.g. "BTC" or "PERP_BTC_USDC")
- side: "buy" or "sell" (required)
- order_type: "LIMIT", "MARKET", "IOC", "FOK", "POST_ONLY" (default: "LIMIT")
- quantity: Order size in base asset (required, e.g. 0.01 for 0.01 BTC)
- price: Limit price (required for LIMIT, IOC, FOK, POST_ONLY. Omit for MARKET)
- reduce_only: If true, only reduces existing position (default: false)

Order types:
- LIMIT: Rests on book until filled or cancelled (GTC)
- MARKET: Fills at best available price immediately
- IOC: Immediate-or-Cancel (fill what's available, cancel rest)
- FOK: Fill-or-Kill (fill entirely or cancel entirely)
- POST_ONLY: Rejected if it would immediately fill (maker only)

Returns: order_id, status, filled quantity"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC') or full symbol (e.g. 'PERP_BTC_USDC')",
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Order side",
                },
                "order_type": {
                    "type": "string",
                    "enum": ["LIMIT", "MARKET", "IOC", "FOK", "POST_ONLY"],
                    "description": "Order type (default: LIMIT)",
                },
                "quantity": {
                    "type": "number",
                    "description": "Order size in base asset",
                },
                "price": {
                    "type": "number",
                    "description": "Limit price (omit for MARKET orders)",
                },
                "reduce_only": {
                    "type": "boolean",
                    "description": "Reduce-only (default: false)",
                },
            },
            "required": ["symbol", "side", "quantity"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str = "",
        side: str = "",
        order_type: str = "LIMIT",
        quantity: float = 0,
        price: float = None,
        reduce_only: bool = False,
        **kwargs,
    ) -> ToolResult:
        if not symbol or not side or not quantity:
            return ToolResult(
                success=False, error="'symbol', 'side', and 'quantity' are required"
            )
        try:
            client = _get_client()
            resolved = client._resolve_symbol(symbol)
            data = await client.create_order(
                symbol=resolved,
                side=side.upper(),
                order_type=order_type.upper(),
                order_quantity=quantity,
                order_price=price,
                reduce_only=reduce_only,
            )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyModifyTool(BaseTool):
    """Modify an existing order."""

    @property
    def name(self) -> str:
        return "orderly_modify"

    @property
    def description(self) -> str:
        return """Modify an existing order on Orderly (change price or quantity).

Parameters:
- order_id: Order ID to modify (required — get from orderly_orders)
- symbol: Asset name or full symbol (required)
- side: "buy" or "sell" (required)
- order_type: "LIMIT", "IOC", "FOK", "POST_ONLY" (default: "LIMIT")
- quantity: New order quantity (optional)
- price: New limit price (optional)

Returns: modified order confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "Order ID to modify",
                },
                "symbol": {
                    "type": "string",
                    "description": "Asset name or full symbol",
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Order side",
                },
                "order_type": {
                    "type": "string",
                    "enum": ["LIMIT", "IOC", "FOK", "POST_ONLY"],
                    "description": "Order type (default: LIMIT)",
                },
                "quantity": {
                    "type": "number",
                    "description": "New order quantity",
                },
                "price": {
                    "type": "number",
                    "description": "New limit price",
                },
            },
            "required": ["order_id", "symbol", "side"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        order_id: int = 0,
        symbol: str = "",
        side: str = "",
        order_type: str = "LIMIT",
        quantity: float = None,
        price: float = None,
        **kwargs,
    ) -> ToolResult:
        if not order_id or not symbol or not side:
            return ToolResult(
                success=False,
                error="'order_id', 'symbol', and 'side' are required",
            )
        try:
            client = _get_client()
            resolved = client._resolve_symbol(symbol)
            data = await client.modify_order(
                order_id=order_id,
                symbol=resolved,
                side=side.upper(),
                order_type=order_type.upper(),
                order_quantity=quantity,
                order_price=price,
            )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyCancelTool(BaseTool):
    """Cancel an order."""

    @property
    def name(self) -> str:
        return "orderly_cancel"

    @property
    def description(self) -> str:
        return """Cancel an open order on Orderly by order ID.

Parameters:
- symbol: Asset name or full symbol (required, e.g. "BTC" or "PERP_BTC_USDC")
- order_id: Order ID to cancel (required — get from orderly_orders)

Returns: cancel confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC') or full symbol",
                },
                "order_id": {
                    "type": "integer",
                    "description": "Order ID to cancel",
                },
            },
            "required": ["symbol", "order_id"],
        }

    async def execute(
        self, ctx: ToolContext, symbol: str = "", order_id: int = 0, **kwargs
    ) -> ToolResult:
        if not symbol or not order_id:
            return ToolResult(
                success=False, error="'symbol' and 'order_id' are required"
            )
        try:
            client = _get_client()
            resolved = client._resolve_symbol(symbol)
            data = await client.cancel_order(resolved, order_id)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyCancelAllTool(BaseTool):
    """Cancel all open orders."""

    @property
    def name(self) -> str:
        return "orderly_cancel_all"

    @property
    def description(self) -> str:
        return """Cancel all open orders on Orderly.

Parameters:
- symbol: (optional) Asset name to cancel orders for. Omit to cancel ALL orders.

Returns: cancel confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Asset name (optional — omit for all)",
                },
            },
        }

    async def execute(self, ctx: ToolContext, symbol: str = "", **kwargs) -> ToolResult:
        try:
            client = _get_client()
            resolved = client._resolve_symbol(symbol) if symbol else None
            data = await client.cancel_all_orders(resolved)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyLeverageTool(BaseTool):
    """Update leverage for a symbol."""

    @property
    def name(self) -> str:
        return "orderly_leverage"

    @property
    def description(self) -> str:
        return """Set leverage for an Orderly perpetual asset.

Parameters:
- symbol: Asset name or full symbol (required, e.g. "BTC" or "PERP_BTC_USDC")
- leverage: Leverage multiplier (required, e.g. 5 for 5x)

Returns: leverage update confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC') or full symbol",
                },
                "leverage": {
                    "type": "integer",
                    "description": "Leverage multiplier (e.g. 5)",
                },
            },
            "required": ["symbol", "leverage"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str = "",
        leverage: int = 0,
        **kwargs,
    ) -> ToolResult:
        if not symbol or not leverage:
            return ToolResult(
                success=False, error="'symbol' and 'leverage' are required"
            )
        try:
            client = _get_client()
            resolved = client._resolve_symbol(symbol)
            data = await client.update_leverage(resolved, leverage)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Fund Management Tools (2) — Deposit & Withdraw ──────────────────────────


class OrderlyDepositTool(BaseTool):
    """Deposit USDC into Orderly trading account."""

    @property
    def name(self) -> str:
        return "orderly_deposit"

    @property
    def description(self) -> str:
        return """Deposit USDC into Orderly Network trading account from the agent's on-chain wallet.

This performs two on-chain transactions:
1. ERC-20 approve — allows the Orderly vault to spend USDC
2. Vault deposit — transfers USDC into the Orderly trading account

The deposit fee (cross-chain relay cost) is paid in ETH automatically.
Funds typically settle in 1-5 minutes after the deposit transaction confirms.

Parameters:
- amount: USDC amount to deposit (e.g. 34.08)

Returns: approve_tx_hash, deposit_tx_hash, amount_deposited, fee_paid"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "USDC amount to deposit (e.g. 34.08)",
                },
            },
            "required": ["amount"],
        }

    async def execute(self, ctx: ToolContext, amount: float = 0, **kwargs) -> ToolResult:
        if not amount or amount <= 0:
            return ToolResult(success=False, error="'amount' must be a positive number")
        try:
            from .deposit import deposit_usdc
            data = await deposit_usdc(amount)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyWithdrawTool(BaseTool):
    """Withdraw USDC from Orderly trading account."""

    @property
    def name(self) -> str:
        return "orderly_withdraw"

    @property
    def description(self) -> str:
        return """Withdraw USDC from Orderly Network trading account to the agent's on-chain wallet.

This creates an EIP-712 signed withdrawal request. The funds are sent back to the
agent's wallet address on the configured chain (default: Arbitrum).

Note: Withdrawals may take a few minutes to process. Check orderly_holdings to confirm.

Parameters:
- amount: USDC amount to withdraw (e.g. 10.0)

Returns: withdrawal confirmation with status"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "USDC amount to withdraw (e.g. 10.0)",
                },
            },
            "required": ["amount"],
        }

    async def execute(self, ctx: ToolContext, amount: float = 0, **kwargs) -> ToolResult:
        if not amount or amount <= 0:
            return ToolResult(success=False, error="'amount' must be a positive number")
        try:
            from .deposit import withdraw_usdc
            data = await withdraw_usdc(amount)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
