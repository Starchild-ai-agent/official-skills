"""
Lighter.xyz Tool Classes

All BaseTool subclasses for the Lighter DEX skill.
- Market Data tools use the REST client (no auth needed for public endpoints)
- Account tools use the REST client with optional auth
- Trading tools use the lighter-sdk SignerClient for signed transactions
- All tools support symbol resolution (BTC, ETH/USDC) as alternative to market_id
- Trading tools accept human-unit prices/amounts and auto-scale to integer ticks
"""
import json
import logging
import time
from typing import Optional

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


# Helper to resolve symbol or market_id
async def _resolve_market(symbol: Optional[str] = None, market_id: Optional[int] = None):
    """Resolve symbol or market_id to (market_index, market_type, symbol_str).
    Returns None if neither provided."""
    if symbol is not None:
        from .client import get_rest_client, resolve_symbol
        return await resolve_symbol(symbol, get_rest_client())
    if market_id is not None:
        from .client import get_rest_client, resolve_symbol
        return await resolve_symbol(str(market_id), get_rest_client())
    return None


def _get_idx(account_index: Optional[int] = None) -> Optional[int]:
    """Get account index from param or config."""
    if account_index is not None:
        return account_index
    from .client import get_account_index
    return get_account_index()


def _require_signer():
    """Get signer client or raise."""
    from .client import get_signer_client
    signer = get_signer_client()
    if signer is None:
        raise RuntimeError(
            "Trading unavailable: install lighter-sdk and set "
            "LIGHTER_PRIVATE_KEY + LIGHTER_ACCOUNT_INDEX "
            "(via env vars or ~/.lighter/lighter-agent-kit/credentials)"
        )
    return signer


# Order type name -> integer mapping
ORDER_TYPE_MAP = {
    "limit": 0,
    "market": 1,
    "stop_loss": 2,
    "stop_loss_limit": 3,
    "take_profit": 4,
    "take_profit_limit": 5,
    "twap": 6,
}

# Time-in-force name -> integer mapping
TIF_MAP = {
    "ioc": 0,
    "gtt": 1,
    "post_only": 2,
}

# Asset name -> SDK constant name
ASSETS = {
    "usdc": "ASSET_ID_USDC",
    "eth": "ASSET_ID_ETH",
    "lit": "ASSET_ID_LIT",
    "link": "ASSET_ID_LINK",
    "uni": "ASSET_ID_UNI",
    "aave": "ASSET_ID_AAVE",
    "sky": "ASSET_ID_SKY",
    "ldo": "ASSET_ID_LDO",
}


# ═══════════════════════════════════════════════════════════════════
# MARKET DATA TOOLS (public, no auth)
# ═══════════════════════════════════════════════════════════════════


class LighterGetNetworkTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_network"

    @property
    def description(self) -> str:
        return """Show which Lighter deployment (network) is selected and the available options.

Lighter runs as SEPARATE deployments with separate accounts, API keys, contracts and
markets: "ethereum" (app.lighter.xyz) and "robinhood" (robinhoodchain.lighter.xyz).
If nothing is selected, ask the user which one they use, then have them set
LIGHTER_NETWORK=ethereum or LIGHTER_NETWORK=robinhood (env var or credentials file).

Example: lighter_get_network()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            from .client import get_network_info
            return ToolResult(success=True, output=json.dumps(get_network_info(), indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetMarketsTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_markets"

    @property
    def description(self) -> str:
        return """List available markets on Lighter with metadata (symbol, fees, decimals, status).

Examples:
- All markets: lighter_get_markets()
- Perps only: lighter_get_markets(filter="perp")
- Spot only: lighter_get_markets(filter="spot")
- Single market: lighter_get_markets(market_id=0)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "market_id": {
                    "type": "integer",
                    "description": "Market ID (255 or omit for all markets)",
                    "default": 255,
                },
                "filter": {
                    "type": "string",
                    "enum": ["all", "spot", "perp"],
                    "description": "Filter by market type",
                    "default": "all",
                },
            },
            "required": [],
        }

    async def execute(self, ctx: ToolContext, market_id: int = 255, filter: str = "all", **kwargs) -> ToolResult:
        try:
            from .client import get_rest_client
            client = get_rest_client()
            data = await client.get_order_book_details(market_id=market_id, filter_type=filter)
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetOrderbookTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_orderbook"

    @property
    def description(self) -> str:
        return """Get current orderbook orders (bids and asks) for a market.

Use symbol (e.g. "BTC", "ETH/USDC") or market_id. Symbol is preferred.

Examples:
- lighter_get_orderbook(symbol="BTC", limit=20)
- lighter_get_orderbook(symbol="ETH/USDC", limit=10)
- lighter_get_orderbook(market_id=0, limit=20)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Market symbol: perp ticker (BTC, ETH) or spot pair (ETH/USDC)",
                },
                "market_id": {
                    "type": "integer",
                    "description": "Market ID (alternative to symbol)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of price levels per side (1-250)",
                    "default": 50,
                },
            },
            "required": [],
        }

    async def execute(self, ctx: ToolContext, symbol: Optional[str] = None,
                      market_id: Optional[int] = None, limit: int = 50, **kwargs) -> ToolResult:
        try:
            resolved = await _resolve_market(symbol=symbol, market_id=market_id)
            if resolved is None:
                return ToolResult(success=False, error="Provide symbol or market_id")
            mid, _, _ = resolved
            from .client import get_rest_client
            data = await get_rest_client().get_order_book_orders(market_id=mid, limit=limit)
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetRecentTradesTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_recent_trades"

    @property
    def description(self) -> str:
        return """Get the most recent trades for a specific market.

Examples:
- lighter_get_recent_trades(symbol="BTC", limit=20)
- lighter_get_recent_trades(market_id=0, limit=100)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Market symbol (e.g. BTC, ETH/USDC)",
                },
                "market_id": {
                    "type": "integer",
                    "description": "Market ID (alternative to symbol)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of trades to return (1-100)",
                    "default": 50,
                },
            },
            "required": [],
        }

    async def execute(self, ctx: ToolContext, symbol: Optional[str] = None,
                      market_id: Optional[int] = None, limit: int = 50, **kwargs) -> ToolResult:
        try:
            resolved = await _resolve_market(symbol=symbol, market_id=market_id)
            if resolved is None:
                return ToolResult(success=False, error="Provide symbol or market_id")
            mid, _, _ = resolved
            from .client import get_rest_client
            data = await get_rest_client().get_recent_trades(market_id=mid, limit=limit)
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetCandlesTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_candles"

    @property
    def description(self) -> str:
        return """Get OHLCV candlestick data for charting and technical analysis.

Resolutions: 1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w. Max 500 candles.

Examples:
- lighter_get_candles(symbol="ETH", resolution="1h", count_back=100)
- lighter_get_candles(market_id=1, resolution="1d", count_back=30)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Market symbol (e.g. BTC, ETH/USDC)",
                },
                "market_id": {
                    "type": "integer",
                    "description": "Market ID (alternative to symbol)",
                },
                "resolution": {
                    "type": "string",
                    "enum": ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"],
                    "description": "Candle resolution/timeframe",
                },
                "count_back": {
                    "type": "integer",
                    "description": "Number of candles to return (max 500)",
                    "default": 100,
                },
                "start_timestamp": {
                    "type": "integer",
                    "description": "Start time in milliseconds (optional)",
                },
                "end_timestamp": {
                    "type": "integer",
                    "description": "End time in milliseconds (optional, defaults to now)",
                },
            },
            "required": ["resolution"],
        }

    async def execute(
        self, ctx: ToolContext, resolution: str,
        symbol: Optional[str] = None, market_id: Optional[int] = None,
        count_back: int = 100, start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None, **kwargs,
    ) -> ToolResult:
        try:
            resolved = await _resolve_market(symbol=symbol, market_id=market_id)
            if resolved is None:
                return ToolResult(success=False, error="Provide symbol or market_id")
            mid, _, _ = resolved
            from .client import get_rest_client
            data = await get_rest_client().get_candles(
                market_id=mid, resolution=resolution, count_back=count_back,
                start_timestamp=start_timestamp, end_timestamp=end_timestamp,
            )
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetExchangeStatsTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_exchange_stats"

    @property
    def description(self) -> str:
        return """Get exchange-wide statistics: 24h volume, trade count, and per-market
index/mark prices, open interest, funding rates, daily volume, price changes.

Example: lighter_get_exchange_stats()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            from .client import get_rest_client
            data = await get_rest_client().get_exchange_stats()
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetFundingRatesTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_funding_rates"

    @property
    def description(self) -> str:
        return """Get current funding rates for all perpetual markets, compared across
Binance, Bybit, Hyperliquid, and Lighter. Useful for funding arbitrage analysis.

Example: lighter_get_funding_rates()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            from .client import get_rest_client
            data = await get_rest_client().get_funding_rates()
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetAssetDetailsTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_asset_details"

    @property
    def description(self) -> str:
        return """Get asset details: symbol, decimals, min transfer/withdrawal amounts,
margin mode, index price, supply caps, liquidation parameters.

Asset IDs: ETH=1, LIT=2, USDC=3, LINK=5, UNI=6, AAVE=7, SKY=8, LDO=9, AZTEC=10

Examples:
- lighter_get_asset_details()           # all assets
- lighter_get_asset_details(asset_id=1) # ETH only"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "integer",
                    "description": "Asset ID (0 or omit for all assets)",
                    "default": 0,
                },
            },
            "required": [],
        }

    async def execute(self, ctx: ToolContext, asset_id: int = 0, **kwargs) -> ToolResult:
        try:
            from .client import get_rest_client
            data = await get_rest_client().get_asset_details(asset_id=asset_id)
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════════
# ACCOUNT TOOLS
# ═══════════════════════════════════════════════════════════════════


class LighterGetAccountTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_account"

    @property
    def description(self) -> str:
        return """Get account details including balances, positions, and metadata.

Examples:
- lighter_get_account()                          # uses configured account
- lighter_get_account(account_index=123)
- lighter_get_account(l1_address="0xabc...")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "account_index": {
                    "type": "integer",
                    "description": "Account index on Lighter (defaults to LIGHTER_ACCOUNT_INDEX)",
                },
                "l1_address": {
                    "type": "string",
                    "description": "Ethereum L1 address (alternative to account_index)",
                },
            },
            "required": [],
        }

    async def execute(
        self, ctx: ToolContext, account_index: Optional[int] = None,
        l1_address: Optional[str] = None, **kwargs,
    ) -> ToolResult:
        try:
            from .client import get_rest_client
            client = get_rest_client()

            if account_index is not None:
                data = await client.get_account(by="index", value=str(account_index))
            elif l1_address is not None:
                data = await client.get_account(by="l1_address", value=l1_address)
            else:
                idx = _get_idx()
                if idx is None:
                    return ToolResult(success=False, error="Provide account_index, l1_address, or set LIGHTER_ACCOUNT_INDEX")
                data = await client.get_account(by="index", value=str(idx))

            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetActiveOrdersTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_active_orders"

    @property
    def description(self) -> str:
        return """Get all active/open orders for an account, optionally filtered by market.

Examples:
- lighter_get_active_orders()
- lighter_get_active_orders(symbol="BTC")
- lighter_get_active_orders(market_id=0)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "account_index": {
                    "type": "integer",
                    "description": "Account index (defaults to LIGHTER_ACCOUNT_INDEX)",
                },
                "symbol": {
                    "type": "string",
                    "description": "Filter by symbol (e.g. BTC, ETH/USDC)",
                },
                "market_id": {
                    "type": "integer",
                    "description": "Filter by market ID (alternative to symbol)",
                },
            },
            "required": [],
        }

    async def execute(
        self, ctx: ToolContext, account_index: Optional[int] = None,
        symbol: Optional[str] = None, market_id: Optional[int] = None, **kwargs,
    ) -> ToolResult:
        try:
            from .client import get_rest_client
            client = get_rest_client()
            idx = _get_idx(account_index)
            if idx is None:
                return ToolResult(success=False, error="Set LIGHTER_ACCOUNT_INDEX or provide account_index")

            mid = market_id
            if mid is None and symbol is not None:
                resolved = await _resolve_market(symbol=symbol)
                if resolved:
                    mid = resolved[0]

            data = await client.get_account_active_orders(account_index=idx, market_id=mid)
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetOrderHistoryTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_order_history"

    @property
    def description(self) -> str:
        return """Get inactive orders (filled, canceled, expired) for an account.

Examples:
- lighter_get_order_history(limit=20)
- lighter_get_order_history(symbol="ETH", limit=50)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "account_index": {
                    "type": "integer",
                    "description": "Account index (defaults to LIGHTER_ACCOUNT_INDEX)",
                },
                "symbol": {
                    "type": "string",
                    "description": "Filter by symbol (e.g. BTC, ETH/USDC)",
                },
                "market_id": {
                    "type": "integer",
                    "description": "Filter by market ID",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of orders to return (1-100)",
                    "default": 50,
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
            },
            "required": [],
        }

    async def execute(
        self, ctx: ToolContext, account_index: Optional[int] = None,
        symbol: Optional[str] = None, market_id: Optional[int] = None,
        limit: int = 50, cursor: Optional[str] = None, **kwargs,
    ) -> ToolResult:
        try:
            from .client import get_rest_client
            client = get_rest_client()
            idx = _get_idx(account_index)
            if idx is None:
                return ToolResult(success=False, error="Set LIGHTER_ACCOUNT_INDEX or provide account_index")

            mid = market_id
            if mid is None and symbol is not None:
                resolved = await _resolve_market(symbol=symbol)
                if resolved:
                    mid = resolved[0]

            data = await client.get_account_inactive_orders(
                account_index=idx, limit=limit, market_id=mid, cursor=cursor,
            )
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetTradeHistoryTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_trade_history"

    @property
    def description(self) -> str:
        return """Get trade history for an account with optional filters.

Examples:
- lighter_get_trade_history(limit=20)
- lighter_get_trade_history(symbol="BTC", role="maker")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "account_index": {
                    "type": "integer",
                    "description": "Account index (defaults to LIGHTER_ACCOUNT_INDEX)",
                },
                "symbol": {
                    "type": "string",
                    "description": "Filter by symbol",
                },
                "market_id": {
                    "type": "integer",
                    "description": "Filter by market ID",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of trades to return (1-100)",
                    "default": 50,
                },
                "role": {
                    "type": "string",
                    "enum": ["all", "maker", "taker"],
                    "default": "all",
                },
                "trade_type": {
                    "type": "string",
                    "enum": ["all", "trade", "liquidation", "deleverage", "market-settlement"],
                    "default": "all",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor",
                },
            },
            "required": [],
        }

    async def execute(
        self, ctx: ToolContext, account_index: Optional[int] = None,
        symbol: Optional[str] = None, market_id: Optional[int] = None,
        limit: int = 50, role: str = "all", trade_type: str = "all",
        cursor: Optional[str] = None, **kwargs,
    ) -> ToolResult:
        try:
            from .client import get_rest_client
            client = get_rest_client()
            idx = _get_idx(account_index)
            if idx is None:
                return ToolResult(success=False, error="Set LIGHTER_ACCOUNT_INDEX or provide account_index")

            mid = market_id
            if mid is None and symbol is not None:
                resolved = await _resolve_market(symbol=symbol)
                if resolved:
                    mid = resolved[0]

            data = await client.get_trades(
                account_index=idx, market_id=mid, limit=limit,
                role=role, trade_type=trade_type, cursor=cursor,
            )
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterGetPnlTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_get_pnl"

    @property
    def description(self) -> str:
        return """Get profit/loss chart data for an account over time.

Resolutions: 1m, 5m, 15m, 1h, 4h, 1d

Examples:
- lighter_get_pnl(resolution="1d", count_back=30)
- lighter_get_pnl(resolution="1h", count_back=168)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "account_index": {
                    "type": "integer",
                    "description": "Account index (defaults to LIGHTER_ACCOUNT_INDEX)",
                },
                "resolution": {
                    "type": "string",
                    "enum": ["1m", "5m", "15m", "1h", "4h", "1d"],
                    "default": "1d",
                },
                "count_back": {
                    "type": "integer",
                    "default": 30,
                },
                "ignore_transfers": {
                    "type": "boolean",
                    "default": False,
                },
            },
            "required": [],
        }

    async def execute(
        self, ctx: ToolContext, account_index: Optional[int] = None,
        resolution: str = "1d", count_back: int = 30,
        ignore_transfers: bool = False, **kwargs,
    ) -> ToolResult:
        try:
            from .client import get_rest_client
            client = get_rest_client()
            idx = _get_idx(account_index)
            if idx is None:
                return ToolResult(success=False, error="Set LIGHTER_ACCOUNT_INDEX or provide account_index")
            data = await client.get_pnl(
                account_index=idx, resolution=resolution,
                count_back=count_back, ignore_transfers=ignore_transfers,
            )
            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════════
# TRADING TOOLS (requires lighter-sdk + private key)
# ═══════════════════════════════════════════════════════════════════


class LighterCreateOrderTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_create_order"

    @property
    def description(self) -> str:
        return """Place a new order on Lighter DEX.

Accepts human-unit prices and amounts (e.g. amount=0.1 ETH, price=3200.50).
Auto-scales to the market's integer tick/lot precision.

Side: "buy"/"long" or "sell"/"short" — both accepted for perp and spot.

Order types: limit, market, stop_loss, stop_loss_limit, take_profit, take_profit_limit
Time-in-force: ioc (immediate-or-cancel), gtt (good-till-time, default), post_only

Examples:
- Market buy 0.1 BTC:
  lighter_create_order(symbol="BTC", side="long", amount=0.1, order_type="market")
- Limit sell 1 ETH at $3200:
  lighter_create_order(symbol="ETH", side="short", amount=1.0, price=3200, order_type="limit")
- Stop-loss:
  lighter_create_order(symbol="ETH", side="short", amount=1.0, price=2800,
                       order_type="stop_loss", trigger_price=2800, reduce_only=true)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Market symbol: perp ticker (BTC) or spot pair (ETH/USDC)",
                },
                "market_index": {
                    "type": "integer",
                    "description": "Market ID (alternative to symbol)",
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell", "long", "short"],
                    "description": "Order side",
                },
                "amount": {
                    "type": "number",
                    "description": "Order size in human units (e.g. 0.1 for 0.1 ETH)",
                },
                "price": {
                    "type": "number",
                    "description": "Limit price in human units (e.g. 3200.50). Required for limit orders.",
                },
                "order_type": {
                    "type": "string",
                    "enum": ["limit", "market", "stop_loss", "stop_loss_limit", "take_profit", "take_profit_limit", "twap"],
                    "default": "limit",
                },
                "time_in_force": {
                    "type": "string",
                    "enum": ["ioc", "gtt", "post_only"],
                    "description": "Default: ioc for market, gtt for limit",
                },
                "reduce_only": {
                    "type": "boolean",
                    "default": False,
                },
                "trigger_price": {
                    "type": "number",
                    "description": "Trigger price for stop/take-profit orders (human units)",
                    "default": 0,
                },
                "slippage": {
                    "type": "number",
                    "description": "Max slippage for market orders (default: 0.01 = 1%)",
                    "default": 0.01,
                },
            },
            "required": ["side", "amount"],
        }

    async def execute(
        self, ctx: ToolContext, side: str, amount: float,
        symbol: Optional[str] = None, market_index: Optional[int] = None,
        price: Optional[float] = None, order_type: str = "limit",
        time_in_force: Optional[str] = None, reduce_only: bool = False,
        trigger_price: float = 0, slippage: float = 0.01, **kwargs,
    ) -> ToolResult:
        try:
            from .client import (
                get_rest_client, get_market_decimals, scale_to_raw,
                format_scaled, resolve_symbol, normalize_side, side_to_is_ask,
            )

            signer = _require_signer()
            client = get_rest_client()

            # Resolve market
            if symbol is not None:
                market_id, market_type, sym = await resolve_symbol(symbol, client)
            elif market_index is not None:
                market_id, market_type, sym = await resolve_symbol(str(market_index), client)
            else:
                return ToolResult(success=False, error="Provide symbol or market_index")

            if amount <= 0:
                return ToolResult(success=False, error="amount must be positive")

            # Get market decimals and scale
            size_dec, price_dec = await get_market_decimals(client, market_id)
            base_amount = scale_to_raw(amount, size_dec)
            if base_amount <= 0:
                return ToolResult(success=False, error="amount too small for this market's precision")

            normalized = normalize_side(side, market_type)
            is_ask = side_to_is_ask(normalized)
            ot = ORDER_TYPE_MAP.get(order_type, 0)
            coi = int(time.time() * 1000) % (2**31)

            if ot == 1:  # market order
                tx, response, err = await signer.create_market_order_limited_slippage(
                    market_index=market_id,
                    client_order_index=coi,
                    base_amount=base_amount,
                    max_slippage=slippage,
                    is_ask=is_ask,
                    reduce_only=reduce_only,
                )
                if err:
                    return ToolResult(success=False, error=f"Order rejected: {err}")

                result = {
                    "status": "submitted",
                    "symbol": sym,
                    "side": normalized,
                    "order_type": "market",
                    "client_order_index": coi,
                    "effective_amount": format_scaled(base_amount, size_dec),
                }
                if response and getattr(response, "tx_hash", None):
                    result["tx_hash"] = response.tx_hash
                return ToolResult(success=True, output=json.dumps(result, indent=2))

            else:  # limit, stop_loss, etc.
                if price is None or price <= 0:
                    return ToolResult(success=False, error="price is required for non-market orders")

                scaled_price = scale_to_raw(price, price_dec)

                if time_in_force is None:
                    tif = TIF_MAP["gtt"]
                else:
                    tif = TIF_MAP.get(time_in_force, 1)

                order_expiry = 0 if tif == 0 else -1
                scaled_trigger = scale_to_raw(trigger_price, price_dec) if trigger_price > 0 else 0

                tx, response, err = await signer.create_order(
                    market_index=market_id,
                    client_order_index=coi,
                    base_amount=base_amount,
                    price=scaled_price,
                    is_ask=is_ask,
                    order_type=ot,
                    time_in_force=tif,
                    reduce_only=reduce_only,
                    trigger_price=scaled_trigger,
                    order_expiry=order_expiry,
                )
                if err:
                    return ToolResult(success=False, error=f"Order rejected: {err}")

                result = {
                    "status": "submitted",
                    "symbol": sym,
                    "side": normalized,
                    "order_type": order_type,
                    "client_order_index": coi,
                    "effective_amount": format_scaled(base_amount, size_dec),
                    "effective_price": format_scaled(scaled_price, price_dec),
                }
                if response and getattr(response, "tx_hash", None):
                    result["tx_hash"] = response.tx_hash
                return ToolResult(success=True, output=json.dumps(result, indent=2))

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterCancelOrderTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_cancel_order"

    @property
    def description(self) -> str:
        return """Cancel a specific order by market and order index.

Examples:
- lighter_cancel_order(symbol="BTC", order_index=12345)
- lighter_cancel_order(market_index=0, order_index=12345)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Market symbol",
                },
                "market_index": {
                    "type": "integer",
                    "description": "Market ID (alternative to symbol)",
                },
                "order_index": {
                    "type": "integer",
                    "description": "Client order index to cancel",
                },
            },
            "required": ["order_index"],
        }

    async def execute(self, ctx: ToolContext, order_index: int,
                      symbol: Optional[str] = None, market_index: Optional[int] = None, **kwargs) -> ToolResult:
        try:
            signer = _require_signer()
            resolved = await _resolve_market(symbol=symbol, market_id=market_index)
            if resolved is None:
                return ToolResult(success=False, error="Provide symbol or market_index")
            mid, _, sym = resolved

            tx, response, err = await signer.cancel_order(
                market_index=mid, order_index=order_index,
            )
            if err:
                return ToolResult(success=False, error=f"Cancel rejected: {err}")

            result = {"status": "cancel_submitted", "symbol": sym, "market_index": mid, "order_index": order_index}
            if response and getattr(response, "tx_hash", None):
                result["tx_hash"] = response.tx_hash
            return ToolResult(success=True, output=json.dumps(result, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterCancelAllOrdersTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_cancel_all_orders"

    @property
    def description(self) -> str:
        return """Cancel all active orders across all markets.

Example: lighter_cancel_all_orders()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            signer = _require_signer()
            tx, response, err = await signer.cancel_all_orders(
                time_in_force=signer.CANCEL_ALL_TIF_IMMEDIATE,
                timestamp_ms=0,
            )
            if err:
                return ToolResult(success=False, error=f"Cancel-all rejected: {err}")

            result = {"status": "cancel_all_submitted"}
            if response and getattr(response, "tx_hash", None):
                result["tx_hash"] = response.tx_hash
            return ToolResult(success=True, output=json.dumps(result, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterModifyOrderTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_modify_order"

    @property
    def description(self) -> str:
        return """Modify an existing order's size and/or price. Accepts human-unit values.

Examples:
- lighter_modify_order(symbol="BTC", order_index=12345, amount=0.2, price=61000)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Market symbol",
                },
                "market_index": {
                    "type": "integer",
                    "description": "Market ID (alternative to symbol)",
                },
                "order_index": {
                    "type": "integer",
                    "description": "Client order index to modify",
                },
                "amount": {
                    "type": "number",
                    "description": "New order size in human units",
                },
                "price": {
                    "type": "number",
                    "description": "New price in human units",
                },
            },
            "required": ["order_index", "amount", "price"],
        }

    async def execute(
        self, ctx: ToolContext, order_index: int, amount: float, price: float,
        symbol: Optional[str] = None, market_index: Optional[int] = None, **kwargs,
    ) -> ToolResult:
        try:
            from .client import get_rest_client, get_market_decimals, scale_to_raw, format_scaled

            signer = _require_signer()
            resolved = await _resolve_market(symbol=symbol, market_id=market_index)
            if resolved is None:
                return ToolResult(success=False, error="Provide symbol or market_index")
            mid, _, sym = resolved

            if amount <= 0 or price <= 0:
                return ToolResult(success=False, error="amount and price must be positive")

            client = get_rest_client()
            size_dec, price_dec = await get_market_decimals(client, mid)
            base_amount = scale_to_raw(amount, size_dec)
            scaled_price = scale_to_raw(price, price_dec)

            tx, response, err = await signer.modify_order(
                market_index=mid, order_index=order_index,
                base_amount=base_amount, price=scaled_price,
            )
            if err:
                return ToolResult(success=False, error=f"Modify rejected: {err}")

            result = {
                "status": "modify_submitted",
                "symbol": sym,
                "order_index": order_index,
                "effective_amount": format_scaled(base_amount, size_dec),
                "effective_price": format_scaled(scaled_price, price_dec),
            }
            if response and getattr(response, "tx_hash", None):
                result["tx_hash"] = response.tx_hash
            return ToolResult(success=True, output=json.dumps(result, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════════
# NEW TRADING TOOLS — ported from lighter-agent-kit
# ═══════════════════════════════════════════════════════════════════


class LighterCloseAllPositionsTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_close_all_positions"

    @property
    def description(self) -> str:
        return """[HIGH-RISK] Flatten all open positions with reduce-only market orders.

ALWAYS run with preview=true first to see what would be closed, then get
explicit user confirmation before running with preview=false.

Do NOT infer intent from vague prompts like "clean up" or "reset".

Examples:
- Preview: lighter_close_all_positions(preview=true)
- Execute: lighter_close_all_positions(preview=false)
- With cancel: lighter_close_all_positions(preview=false, with_cancel_all=true)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "preview": {
                    "type": "boolean",
                    "description": "If true, only show what would be closed without executing",
                    "default": True,
                },
                "slippage": {
                    "type": "number",
                    "description": "Max slippage per closing order (default: 0.01 = 1%)",
                    "default": 0.01,
                },
                "with_cancel_all": {
                    "type": "boolean",
                    "description": "Cancel all resting orders before closing. Kills TP/SL brackets too.",
                    "default": False,
                },
            },
            "required": [],
        }

    async def execute(
        self, ctx: ToolContext, preview: bool = True,
        slippage: float = 0.01, with_cancel_all: bool = False, **kwargs,
    ) -> ToolResult:
        try:
            from .client import get_rest_client, get_market_decimals, scale_to_raw, format_scaled

            signer = _require_signer()
            client = get_rest_client()

            # Get all markets for decimal info
            books_data = await client.get_order_books(market_id=255, filter_type="all")
            decimals_by_market = {}
            symbol_by_market = {}
            for ob in books_data.get("order_books", []):
                mid = ob.get("market_id")
                decimals_by_market[mid] = (ob.get("supported_size_decimals", 0), ob.get("supported_price_decimals", 0))
                symbol_by_market[mid] = ob.get("symbol", str(mid))

            # Get account positions
            acct_data = await client.get_account(by="index", value=str(signer.account_index))
            accounts = acct_data.get("accounts", [])
            positions = accounts[0].get("positions", []) if accounts else []

            non_zero = []
            for p in positions:
                try:
                    size = float(p.get("position", 0))
                except (TypeError, ValueError):
                    size = 0.0
                if size > 0:
                    non_zero.append(p)

            would_close = []
            for p in non_zero:
                mid = p.get("market_id")
                size_dec = decimals_by_market.get(mid, (0, 0))[0]
                size = float(p.get("position", 0))
                is_long = int(p.get("sign", 1)) == 1
                would_close.append({
                    "symbol": p.get("symbol") or symbol_by_market.get(mid, str(mid)),
                    "market_id": mid,
                    "current_side": "long" if is_long else "short",
                    "closing_side": "short" if is_long else "long",
                    "amount": f"{size:.{size_dec}f}" if size_dec else str(size),
                })

            if preview:
                result = {"status": "ok", "preview": True, "would_close": would_close}
                if with_cancel_all:
                    result["note"] = "--with_cancel_all would cancel all resting orders before closing"
                return ToolResult(success=True, output=json.dumps(result, indent=2))

            # Execute close-all
            if with_cancel_all:
                tx, response, err = await signer.cancel_all_orders(
                    time_in_force=signer.CANCEL_ALL_TIF_IMMEDIATE, timestamp_ms=0,
                )
                if err:
                    return ToolResult(success=False, error=f"Cancel-all failed: {err}")

            closed = []
            failed = []
            for p in non_zero:
                mid = p.get("market_id")
                decs = decimals_by_market.get(mid)
                if decs is None:
                    failed.append({"symbol": symbol_by_market.get(mid), "error": "market decimals not found"})
                    continue

                size_dec, _ = decs
                size = float(p.get("position", 0))
                base_amount = scale_to_raw(size, size_dec)
                if base_amount <= 0:
                    failed.append({"symbol": symbol_by_market.get(mid), "error": "size rounds to zero"})
                    continue

                is_long = int(p.get("sign", 1)) == 1
                is_ask = is_long
                coi = int(time.time() * 1000) % (2**31)

                try:
                    tx, response, err = await signer.create_market_order_limited_slippage(
                        market_index=mid,
                        client_order_index=coi,
                        base_amount=base_amount,
                        max_slippage=slippage,
                        is_ask=is_ask,
                        reduce_only=True,
                    )
                    if err:
                        failed.append({"symbol": symbol_by_market.get(mid), "error": str(err)})
                    else:
                        entry = {
                            "symbol": symbol_by_market.get(mid),
                            "closing_side": "short" if is_long else "long",
                            "amount": format_scaled(base_amount, size_dec),
                            "client_order_index": coi,
                        }
                        if response and getattr(response, "tx_hash", None):
                            entry["tx_hash"] = response.tx_hash
                        closed.append(entry)
                except Exception as exc:
                    failed.append({"symbol": symbol_by_market.get(mid), "error": str(exc)})

            status = "ok" if not failed else ("partial" if closed else "error")
            result = {
                "status": status,
                "closed": closed,
                "failed": failed,
                "cancelled_orders_first": with_cancel_all,
            }
            return ToolResult(success=status != "error", output=json.dumps(result, indent=2))

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterSetLeverageTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_set_leverage"

    @property
    def description(self) -> str:
        return """Set leverage for a market. Default margin mode is cross.

Examples:
- lighter_set_leverage(symbol="BTC", leverage=10)
- lighter_set_leverage(symbol="ETH", leverage=5, margin_mode="isolated")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Market symbol (e.g. BTC, ETH)",
                },
                "market_index": {
                    "type": "integer",
                    "description": "Market ID (alternative to symbol)",
                },
                "leverage": {
                    "type": "integer",
                    "description": "Leverage multiplier (e.g. 10)",
                },
                "margin_mode": {
                    "type": "string",
                    "enum": ["cross", "isolated"],
                    "default": "cross",
                },
            },
            "required": ["leverage"],
        }

    async def execute(
        self, ctx: ToolContext, leverage: int,
        symbol: Optional[str] = None, market_index: Optional[int] = None,
        margin_mode: str = "cross", **kwargs,
    ) -> ToolResult:
        try:
            signer = _require_signer()
            resolved = await _resolve_market(symbol=symbol, market_id=market_index)
            if resolved is None:
                return ToolResult(success=False, error="Provide symbol or market_index")
            mid, _, sym = resolved

            if leverage < 1:
                return ToolResult(success=False, error="leverage must be >= 1")

            mode = signer.CROSS_MARGIN_MODE if margin_mode == "cross" else signer.ISOLATED_MARGIN_MODE

            tx, response, err = await signer.update_leverage(
                market_index=mid, margin_mode=mode, leverage=leverage,
            )
            if err:
                return ToolResult(success=False, error=f"Set leverage failed: {err}")

            result = {"status": "submitted", "symbol": sym, "leverage": leverage, "margin_mode": margin_mode}
            if response and getattr(response, "tx_hash", None):
                result["tx_hash"] = response.tx_hash
            return ToolResult(success=True, output=json.dumps(result, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterAdjustMarginTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_adjust_margin"

    @property
    def description(self) -> str:
        return """Add or remove isolated margin collateral (USDC) for a position.
Only valid on isolated-margin positions.

Examples:
- lighter_adjust_margin(symbol="ETH", amount=100, direction="add")
- lighter_adjust_margin(symbol="BTC", amount=50, direction="remove")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Market symbol",
                },
                "market_index": {
                    "type": "integer",
                    "description": "Market ID (alternative to symbol)",
                },
                "amount": {
                    "type": "number",
                    "description": "USDC amount to add or remove",
                },
                "direction": {
                    "type": "string",
                    "enum": ["add", "remove"],
                },
            },
            "required": ["amount", "direction"],
        }

    async def execute(
        self, ctx: ToolContext, amount: float, direction: str,
        symbol: Optional[str] = None, market_index: Optional[int] = None, **kwargs,
    ) -> ToolResult:
        try:
            signer = _require_signer()
            resolved = await _resolve_market(symbol=symbol, market_id=market_index)
            if resolved is None:
                return ToolResult(success=False, error="Provide symbol or market_index")
            mid, _, sym = resolved

            if amount <= 0:
                return ToolResult(success=False, error="amount must be positive")

            dir_val = (
                signer.ISOLATED_MARGIN_ADD_COLLATERAL
                if direction == "add"
                else signer.ISOLATED_MARGIN_REMOVE_COLLATERAL
            )

            tx, response, err = await signer.update_margin(
                market_index=mid, usdc_amount=amount, direction=dir_val,
            )
            if err:
                return ToolResult(success=False, error=f"Adjust margin failed: {err}")

            result = {"status": "submitted", "symbol": sym, "amount": amount, "direction": direction}
            if response and getattr(response, "tx_hash", None):
                result["tx_hash"] = response.tx_hash
            return ToolResult(success=True, output=json.dumps(result, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterWithdrawTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_withdraw"

    @property
    def description(self) -> str:
        return """Withdraw assets from Lighter. Creates a withdrawal request.
Funds may go through a pending/claim flow before appearing in wallet.

Assets: usdc, eth, lit, link, uni, aave, sky, ldo
Routes: perp (default), spot

Examples:
- lighter_withdraw(asset="usdc", amount=100)
- lighter_withdraw(asset="eth", amount=0.5, route="spot")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "asset": {
                    "type": "string",
                    "enum": list(ASSETS.keys()),
                    "description": "Asset to withdraw",
                },
                "amount": {
                    "type": "number",
                    "description": "Amount to withdraw",
                },
                "route": {
                    "type": "string",
                    "enum": ["perp", "spot"],
                    "description": "Withdraw from perp or spot balance",
                    "default": "perp",
                },
            },
            "required": ["asset", "amount"],
        }

    async def execute(
        self, ctx: ToolContext, asset: str, amount: float,
        route: str = "perp", **kwargs,
    ) -> ToolResult:
        try:
            signer = _require_signer()

            if amount <= 0:
                return ToolResult(success=False, error="amount must be positive")

            asset_id = getattr(signer, ASSETS[asset])
            route_type = signer.ROUTE_PERP if route == "perp" else signer.ROUTE_SPOT

            tx, response, err = await signer.withdraw(
                asset_id=asset_id, route_type=route_type, amount=amount,
            )
            if err:
                return ToolResult(success=False, error=f"Withdraw failed: {err}")

            result = {"status": "submitted", "asset": asset, "amount": amount, "route": route}
            if response and getattr(response, "tx_hash", None):
                result["tx_hash"] = response.tx_hash
            return ToolResult(success=True, output=json.dumps(result, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterTransferFundsTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_transfer_funds"

    @property
    def description(self) -> str:
        return """Transfer assets between your own perp and spot collateral buckets.
No L1 signature required, no cross-account routing.

Examples:
- lighter_transfer_funds(asset="usdc", amount=250, from_route="perp", to_route="spot")
- lighter_transfer_funds(asset="eth", amount=1.0, from_route="spot", to_route="perp")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "asset": {
                    "type": "string",
                    "enum": list(ASSETS.keys()),
                },
                "amount": {
                    "type": "number",
                    "description": "Amount to transfer",
                },
                "from_route": {
                    "type": "string",
                    "enum": ["perp", "spot"],
                },
                "to_route": {
                    "type": "string",
                    "enum": ["perp", "spot"],
                },
            },
            "required": ["asset", "amount", "from_route", "to_route"],
        }

    async def execute(
        self, ctx: ToolContext, asset: str, amount: float,
        from_route: str = "perp", to_route: str = "spot", **kwargs,
    ) -> ToolResult:
        try:
            signer = _require_signer()

            if amount <= 0:
                return ToolResult(success=False, error="amount must be positive")
            if from_route == to_route:
                return ToolResult(success=False, error="from_route and to_route must differ")

            asset_id = getattr(signer, ASSETS[asset])
            route_from = signer.ROUTE_PERP if from_route == "perp" else signer.ROUTE_SPOT
            route_to = signer.ROUTE_PERP if to_route == "perp" else signer.ROUTE_SPOT

            tx, response, err = await signer.transfer_same_master_account(
                to_account_index=signer.account_index,
                asset_id=asset_id,
                route_from=route_from,
                route_to=route_to,
                amount=amount,
                fee=0,
                memo="0" * 64,
            )
            if err:
                return ToolResult(success=False, error=f"Transfer failed: {err}")

            result = {
                "status": "submitted", "asset": asset, "amount": amount,
                "from_route": from_route, "to_route": to_route,
            }
            if response and getattr(response, "tx_hash", None):
                result["tx_hash"] = response.tx_hash
            return ToolResult(success=True, output=json.dumps(result, indent=2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════════
# PAPER TRADING TOOLS (no credentials required, local simulation)
# ═══════════════════════════════════════════════════════════════════

# Paper trading state is persisted to a local JSON file.
# These tools depend on lighter-sdk's PaperClient.

import os
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import replace


def _paper_data_dir() -> Path:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "lighter-agent-kit"
    return Path.home() / ".lighter" / "lighter-agent-kit"


def _paper_state_path() -> Path:
    override = os.environ.get("LIGHTER_PAPER_STATE_PATH")
    if override:
        return Path(override)
    # One paper book per network so switching venues never mixes positions.
    # Ethereum keeps the legacy filename for backward compatibility.
    from .client import get_network
    try:
        network = get_network()
    except Exception:
        network = None
    if network and network != "ethereum":
        return _paper_data_dir() / f"paper-state-{network}.json"
    return _paper_data_dir() / "paper-state.json"


_STATE_VERSION = 1


def _load_paper_sdk():
    """Import paper trading classes from lighter-sdk via agent-kit vendor dir."""
    from .client import ensure_lighter_sdk
    if not ensure_lighter_sdk():
        raise ImportError("lighter-sdk not available")
    from lighter.paper_client import (
        AccountTier, InMemoryOrderBook, MarketConfig, PaperAccount,
        PaperClient, PaperOrderRequest, PaperOrderSide, PaperOrderType,
        PaperPosition, PaperTrade,
    )
    from lighter.paper_client.accounting import new_paper_account
    return {
        "AccountTier": AccountTier, "InMemoryOrderBook": InMemoryOrderBook,
        "MarketConfig": MarketConfig, "PaperAccount": PaperAccount,
        "PaperClient": PaperClient, "PaperOrderRequest": PaperOrderRequest,
        "PaperOrderSide": PaperOrderSide, "PaperOrderType": PaperOrderType,
        "PaperPosition": PaperPosition, "PaperTrade": PaperTrade,
        "new_paper_account": new_paper_account,
    }


def _tier_map(AccountTier):
    return {tier.name.lower(): tier for tier in AccountTier}


def _fee_bps(tier_enum):
    return {
        "taker_fee_bps": round(tier_enum.taker_fee * 10_000, 2),
        "maker_fee_bps": round(tier_enum.maker_fee * 10_000, 2),
    }


def _ser_position(pos):
    return {
        "market_id": pos.market_id, "size": pos.size,
        "entry_quote": pos.entry_quote, "avg_entry_price": pos.avg_entry_price,
        "mark_price": pos.mark_price, "unrealized_pnl": pos.unrealized_pnl,
        "realized_pnl": pos.realized_pnl, "liquidation_price": pos.liquidation_price,
    }


def _deser_position(d, PaperPosition):
    return PaperPosition(
        market_id=d["market_id"], size=d.get("size", 0),
        entry_quote=d.get("entry_quote", 0), avg_entry_price=d.get("avg_entry_price", 0),
        mark_price=d.get("mark_price", 0), unrealized_pnl=d.get("unrealized_pnl", 0),
        realized_pnl=d.get("realized_pnl", 0), liquidation_price=d.get("liquidation_price", 0),
    )


def _ser_trade(t):
    return {
        "market_id": t.market_id, "side": int(t.side), "size": t.size,
        "price": t.price, "fee": t.fee, "realized_pnl": t.realized_pnl,
        "is_liquidation": t.is_liquidation, "timestamp": t.timestamp.isoformat(),
    }


def _deser_trade(d, PaperOrderSide, PaperTrade):
    return PaperTrade(
        market_id=d["market_id"], side=PaperOrderSide(d["side"]),
        size=d["size"], price=d["price"], fee=d["fee"],
        realized_pnl=d["realized_pnl"], is_liquidation=d["is_liquidation"],
        timestamp=datetime.fromisoformat(d["timestamp"]),
    )


def _ser_account(acct):
    return {
        "initial_collateral": acct.initial_collateral,
        "collateral": acct.collateral,
        "positions": {str(k): _ser_position(v) for k, v in acct.positions.items()},
        "trades": [_ser_trade(t) for t in acct.trades],
    }


def _deser_account(d, sdk):
    return sdk["PaperAccount"](
        initial_collateral=d["initial_collateral"],
        collateral=d["collateral"],
        positions={int(k): _deser_position(v, sdk["PaperPosition"]) for k, v in d.get("positions", {}).items()},
        trades=[_deser_trade(t, sdk["PaperOrderSide"], sdk["PaperTrade"]) for t in d.get("trades", [])],
    )


def _ser_config(cfg):
    return {
        "market_id": cfg.market_id, "symbol": cfg.symbol,
        "size_decimals": cfg.size_decimals, "price_decimals": cfg.price_decimals,
        "default_initial_margin_fraction": cfg.default_initial_margin_fraction,
        "min_initial_margin_fraction": cfg.min_initial_margin_fraction,
        "maintenance_margin_fraction": cfg.maintenance_margin_fraction,
        "closeout_margin_fraction": cfg.closeout_margin_fraction,
        "taker_fee": cfg.taker_fee, "maker_fee": cfg.maker_fee,
        "min_base_amount": cfg.min_base_amount, "min_quote_amount": cfg.min_quote_amount,
        "last_trade_price": cfg.last_trade_price,
    }


def _deser_config(d, MarketConfig):
    return MarketConfig(**d)


def _save_paper_state(tier_name, account, market_configs):
    state = {
        "version": _STATE_VERSION, "tier": tier_name,
        "account": _ser_account(account),
        "market_configs": {str(k): _ser_config(v) for k, v in market_configs.items()},
    }
    path = _paper_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f"{path.name}.", suffix=".tmp", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def _load_paper_state():
    path = _paper_state_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict) or data.get("version") != _STATE_VERSION:
        return None
    return data


def _unpack_paper_state(state, sdk):
    tiers = _tier_map(sdk["AccountTier"])
    tier_name = state["tier"]
    tier_enum = tiers[tier_name]
    account = _deser_account(state["account"], sdk)
    configs = {int(k): _deser_config(v, sdk["MarketConfig"]) for k, v in state.get("market_configs", {}).items()}
    return tier_name, tier_enum, account, configs


def _hydrate_paper_client(api_client, tier_enum, account, configs, sdk):
    paper = sdk["PaperClient"](api_client, account.initial_collateral, account_tier=tier_enum)
    paper.account = account
    paper.market_configs = dict(configs)
    for mid, pos in account.positions.items():
        if pos.size == 0:
            continue
        paper.order_books.setdefault(mid, sdk["InMemoryOrderBook"]())
        cfg = paper.market_configs.get(mid)
        if cfg is not None and pos.mark_price > 0:
            paper.market_configs[mid] = replace(cfg, last_trade_price=pos.mark_price)
    return paper


def _symbol_for_market(market_id, market_configs):
    cfg = market_configs.get(market_id)
    return cfg.symbol if cfg else str(market_id)


class LighterPaperInitTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_paper_init"

    @property
    def description(self) -> str:
        return """Create a new paper trading account for risk-free simulation.

No credentials needed. Simulates against real Lighter order book snapshots.
Perp markets only. State persists locally.

Tiers: standard (0/0 bps), premium (2.8/0.4 bps, default), premium_1 through premium_7.

Examples:
- lighter_paper_init()
- lighter_paper_init(collateral=50000, tier="premium_3")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "collateral": {
                    "type": "number",
                    "description": "Starting USDC collateral (default: 10000)",
                    "default": 10000,
                },
                "tier": {
                    "type": "string",
                    "description": "Fee tier (default: premium)",
                    "default": "premium",
                },
            },
            "required": [],
        }

    async def execute(self, ctx: ToolContext, collateral: float = 10000, tier: str = "premium", **kwargs) -> ToolResult:
        try:
            sdk = _load_paper_sdk()
            tiers = _tier_map(sdk["AccountTier"])

            if tier not in tiers:
                return ToolResult(success=False, error=f"Unknown tier '{tier}'. Valid: {', '.join(tiers.keys())}")

            state = _load_paper_state()
            if state is not None:
                return ToolResult(success=False, error="Paper account already exists. Use lighter_paper_reset to reinitialize.")

            tier_enum = tiers[tier]
            account = sdk["new_paper_account"](collateral)
            _save_paper_state(tier, account, {})

            return ToolResult(success=True, output=json.dumps({
                "status": "ok", "collateral": collateral, "tier": tier,
                **_fee_bps(tier_enum), "state_path": str(_paper_state_path()),
            }, indent=2))
        except ImportError:
            return ToolResult(success=False, error="lighter-sdk not installed. Run: pip install lighter-sdk")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterPaperResetTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_paper_reset"

    @property
    def description(self) -> str:
        return """Reset the paper trading account. Wipes all positions and trades.
No-args form reuses previous collateral and tier.

Examples:
- lighter_paper_reset()
- lighter_paper_reset(collateral=25000, tier="premium_1")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "collateral": {"type": "number", "description": "New starting collateral"},
                "tier": {"type": "string", "description": "New fee tier"},
            },
            "required": [],
        }

    async def execute(self, ctx: ToolContext, collateral: Optional[float] = None, tier: Optional[str] = None, **kwargs) -> ToolResult:
        try:
            sdk = _load_paper_sdk()
            tiers = _tier_map(sdk["AccountTier"])
            state = _load_paper_state()

            if state is None:
                coll = collateral if collateral is not None else 10000
                t = tier if tier is not None else "premium"
            else:
                coll = collateral if collateral is not None else state["account"]["initial_collateral"]
                t = tier if tier is not None else state["tier"]

            if t not in tiers:
                return ToolResult(success=False, error=f"Unknown tier '{t}'. Valid: {', '.join(tiers.keys())}")

            tier_enum = tiers[t]
            account = sdk["new_paper_account"](coll)
            _save_paper_state(t, account, {})

            return ToolResult(success=True, output=json.dumps({
                "status": "ok", "collateral": coll, "tier": t,
                **_fee_bps(tier_enum), "state_path": str(_paper_state_path()),
            }, indent=2))
        except ImportError:
            return ToolResult(success=False, error="lighter-sdk not installed. Run: pip install lighter-sdk")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterPaperStatusTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_paper_status"

    @property
    def description(self) -> str:
        return """Get paper trading account summary: collateral, PnL, position/trade counts.
Auto-refreshes mark prices for open positions.

Example: lighter_paper_status()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            sdk = _load_paper_sdk()
            import lighter
            state = _load_paper_state()
            if state is None:
                return ToolResult(success=False, error="No paper account. Run lighter_paper_init first.")

            tier_name, tier_enum, account, configs = _unpack_paper_state(state, sdk)
            from .client import get_base_url
            host = get_base_url()

            async with lighter.ApiClient(configuration=lighter.Configuration(host=host)) as api_client:
                paper = _hydrate_paper_client(api_client, tier_enum, account, configs, sdk)
                # Refresh mark prices
                for mid, pos in list(paper.account.positions.items()):
                    if pos.size != 0:
                        try:
                            await paper.track_market_snapshot(mid)
                        except Exception:
                            pass
                account = paper.get_account()
                _save_paper_state(tier_name, paper.account, paper.market_configs)

            total_unrealized = sum(pos.unrealized_pnl for pos in account.positions.values())
            return ToolResult(success=True, output=json.dumps({
                "status": "ok",
                "collateral": account.collateral,
                "initial_collateral": account.initial_collateral,
                "tier": tier_name, **_fee_bps(tier_enum),
                "unrealized_pnl": total_unrealized,
                "total_pnl": account.collateral - account.initial_collateral + total_unrealized,
                "positions_count": len(account.positions),
                "trades_count": len(account.trades),
            }, indent=2))
        except ImportError:
            return ToolResult(success=False, error="lighter-sdk not installed. Run: pip install lighter-sdk")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterPaperPositionsTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_paper_positions"

    @property
    def description(self) -> str:
        return """List open paper trading positions with mark prices and PnL.

Examples:
- lighter_paper_positions()
- lighter_paper_positions(symbol="ETH")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Filter to one symbol (e.g. ETH)"},
            },
            "required": [],
        }

    async def execute(self, ctx: ToolContext, symbol: Optional[str] = None, **kwargs) -> ToolResult:
        try:
            sdk = _load_paper_sdk()
            import lighter
            state = _load_paper_state()
            if state is None:
                return ToolResult(success=False, error="No paper account. Run lighter_paper_init first.")

            tier_name, tier_enum, account, configs = _unpack_paper_state(state, sdk)
            from .client import get_base_url
            host = get_base_url()

            async with lighter.ApiClient(configuration=lighter.Configuration(host=host)) as api_client:
                paper = _hydrate_paper_client(api_client, tier_enum, account, configs, sdk)
                for mid, pos in list(paper.account.positions.items()):
                    if pos.size != 0:
                        try:
                            await paper.track_market_snapshot(mid)
                        except Exception:
                            pass
                account = paper.get_account()
                mcfg = paper.market_configs
                _save_paper_state(tier_name, paper.account, mcfg)

            positions = []
            for mid, pos in account.positions.items():
                positions.append({
                    "symbol": _symbol_for_market(mid, mcfg),
                    "market_id": mid,
                    "side": "long" if pos.size > 0 else "short",
                    "size": abs(pos.size),
                    "avg_entry_price": pos.avg_entry_price,
                    "mark_price": pos.mark_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "realized_pnl": pos.realized_pnl,
                    "liquidation_price": pos.liquidation_price,
                })
            if symbol:
                sym = symbol.upper()
                positions = [p for p in positions if p["symbol"].upper() == sym]

            return ToolResult(success=True, output=json.dumps({"positions": positions}, indent=2))
        except ImportError:
            return ToolResult(success=False, error="lighter-sdk not installed. Run: pip install lighter-sdk")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterPaperOrderTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_paper_order"

    @property
    def description(self) -> str:
        return """Place a paper trade against real Lighter order book snapshots.
No credentials, no broadcast, no risk. Perp markets only.

Side: buy/long or sell/short.

Examples:
- lighter_paper_order(symbol="BTC", side="long", amount=0.1)
- lighter_paper_order(symbol="ETH", side="short", amount=1.0)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Perp symbol (e.g. BTC, ETH, SOL)",
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell", "long", "short"],
                },
                "amount": {
                    "type": "number",
                    "description": "Base amount in human units (e.g. 0.1)",
                },
            },
            "required": ["symbol", "side", "amount"],
        }

    async def execute(self, ctx: ToolContext, symbol: str, side: str, amount: float, **kwargs) -> ToolResult:
        try:
            sdk = _load_paper_sdk()
            import lighter
            state = _load_paper_state()
            if state is None:
                return ToolResult(success=False, error="No paper account. Run lighter_paper_init first.")
            if amount <= 0:
                return ToolResult(success=False, error="amount must be positive")

            tier_name, tier_enum, account, configs = _unpack_paper_state(state, sdk)
            from .client import get_base_url, resolve_symbol, get_rest_client, normalize_side
            host = get_base_url()

            async with lighter.ApiClient(configuration=lighter.Configuration(host=host)) as api_client:
                # Resolve symbol
                from .client import resolve_symbol as _resolve
                market_id, market_type, sym = await _resolve(symbol, get_rest_client())
                if market_type != "perp":
                    return ToolResult(success=False, error="Paper trading supports perp markets only. Use a perp symbol like BTC, not ETH/USDC.")

                paper = _hydrate_paper_client(api_client, tier_enum, account, configs, sdk)
                await paper.track_market_snapshot(market_id)

                normalized = normalize_side(side, "perp")
                paper_side = sdk["PaperOrderSide"].BUY if normalized in ("long", "buy") else sdk["PaperOrderSide"].SELL
                request = sdk["PaperOrderRequest"](
                    market_id=market_id, side=paper_side,
                    base_amount=amount, order_type=sdk["PaperOrderType"].MARKET,
                )

                trades_before = len(paper.get_trades())
                result = await paper.create_paper_order(request)
                new_trades = paper.get_trades()[trades_before:]
                liquidated = any(t.is_liquidation and t.market_id == market_id for t in new_trades)

                _save_paper_state(tier_name, paper.account, paper.market_configs)

            return ToolResult(success=True, output=json.dumps({
                "status": "ok", "symbol": sym, "market_id": market_id,
                "side": normalized, "order_type": "market",
                "filled_size": result.filled_size, "avg_price": result.avg_price,
                "total_fee": result.total_fee, "quote_amount": result.quote_amount,
                "unfilled": result.unfilled, "liquidated": liquidated,
                "fills_count": len(result.fills),
            }, indent=2))
        except ImportError:
            return ToolResult(success=False, error="lighter-sdk not installed. Run: pip install lighter-sdk")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterPaperTradesTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_paper_trades"

    @property
    def description(self) -> str:
        return """List paper trade history, most recent first.

Examples:
- lighter_paper_trades()
- lighter_paper_trades(symbol="BTC", limit=10)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Filter by symbol"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": [],
        }

    async def execute(self, ctx: ToolContext, symbol: Optional[str] = None, limit: int = 50, **kwargs) -> ToolResult:
        try:
            sdk = _load_paper_sdk()
            state = _load_paper_state()
            if state is None:
                return ToolResult(success=False, error="No paper account. Run lighter_paper_init first.")

            _, _, account, configs = _unpack_paper_state(state, sdk)
            trades = list(account.trades)

            if symbol:
                sym = symbol.upper()
                trades = [t for t in trades if _symbol_for_market(t.market_id, configs).upper() == sym]

            trades = list(reversed(trades))[:limit]
            return ToolResult(success=True, output=json.dumps({"trades": [
                {
                    "symbol": _symbol_for_market(t.market_id, configs),
                    "market_id": t.market_id,
                    "side": "buy" if t.side == sdk["PaperOrderSide"].BUY else "sell",
                    "size": t.size, "price": t.price, "fee": t.fee,
                    "realized_pnl": t.realized_pnl,
                    "is_liquidation": t.is_liquidation,
                    "timestamp": t.timestamp.isoformat(),
                }
                for t in trades
            ]}, indent=2))
        except ImportError:
            return ToolResult(success=False, error="lighter-sdk not installed. Run: pip install lighter-sdk")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LighterPaperHealthTool(BaseTool):

    @property
    def name(self) -> str:
        return "lighter_paper_health"

    @property
    def description(self) -> str:
        return """Check paper account health: total account value, margin requirements, leverage.

Example: lighter_paper_health()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            sdk = _load_paper_sdk()
            import lighter
            state = _load_paper_state()
            if state is None:
                return ToolResult(success=False, error="No paper account. Run lighter_paper_init first.")

            tier_name, tier_enum, account, configs = _unpack_paper_state(state, sdk)
            from .client import get_base_url
            host = get_base_url()

            async with lighter.ApiClient(configuration=lighter.Configuration(host=host)) as api_client:
                paper = _hydrate_paper_client(api_client, tier_enum, account, configs, sdk)
                for mid, pos in list(paper.account.positions.items()):
                    if pos.size != 0:
                        try:
                            await paper.track_market_snapshot(mid)
                        except Exception:
                            pass
                health = paper.get_health()
                _save_paper_state(tier_name, paper.account, paper.market_configs)

            return ToolResult(success=True, output=json.dumps({
                "status": health.status.name.lower(),
                "total_account_value": health.total_account_value,
                "initial_margin_requirement": health.initial_margin_requirement,
                "maintenance_margin_requirement": health.maintenance_margin_requirement,
                "margin_usage": round(health.margin_usage, 2),
                "leverage": round(health.leverage, 4),
                "collateral": paper.account.collateral,
                "tier": tier_name, **_fee_bps(tier_enum),
            }, indent=2))
        except ImportError:
            return ToolResult(success=False, error="lighter-sdk not installed. Run: pip install lighter-sdk")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
