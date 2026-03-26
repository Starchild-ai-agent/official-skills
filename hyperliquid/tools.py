"""
Hyperliquid Trading Tools — BaseTool subclasses for agent use.

Info tools (9): hl_account, hl_balances, hl_total_balance, hl_open_orders, hl_market,
                hl_orderbook, hl_fills, hl_candles, hl_funding
Exchange tools (10): hl_order, hl_spot_order, hl_cancel, hl_cancel_all,
                     hl_modify, hl_leverage, hl_transfer_usd, hl_withdraw, hl_deposit,
                     hl_set_abstraction
"""

import time
import logging

from core.tool import BaseTool, ToolContext, ToolResult
from .client import HyperliquidClient

logger = logging.getLogger(__name__)

# Module-level shared client instance
_client: HyperliquidClient = None


def _get_client() -> HyperliquidClient:
    global _client
    if _client is None:
        _client = HyperliquidClient()
    return _client


async def _get_address() -> str:
    """Get the agent's EVM address."""
    return await _get_client()._get_address()


# ── Info Tools ───────────────────────────────────────────────────────────────


class HLAccountTool(BaseTool):
    """Get perp account state — positions, margin, PnL."""

    @property
    def name(self) -> str:
        return "hl_account"

    @property
    def description(self) -> str:
        return """Get Hyperliquid perpetual account state: open positions, margin balances, unrealized PnL, and account value.

**⚠️ WARNING: This tool shows PERP account only! With unified account mode (default), your funds may be in SPOT.**
**🎯 Use `hl_total_balance` instead to check if you have funds to place orders!**

**Understanding account modes:**
- **Unified Account (default)**: Funds are shared across spot/perp. This tool may show $0 even if you have USDC in spot!
- **Disabled mode**: Spot and perp are separate. This tool accurately shows perp margin.

**When to use this tool:**
- To check open positions and their PnL
- To see margin usage on perp side
- To monitor position sizes and liquidation risk
- NOT to check if you have funds to place orders (use `hl_total_balance` for that!)

**🚨 CRITICAL for RWA/Stock Perps (xyz:NVDA, xyz:TSLA, etc.):**
- ✅ Check MAIN account (`hl_account()`) for positions, NOT for available funds
- ❌ DO NOT check xyz dex (`hl_account(dex="xyz")`) before placing orders - it shows $0 until you have positions!
- ✅ xyz dex showing $0 is NORMAL and EXPECTED before your first builder perp order
- ✅ DEX abstraction auto-transfers funds from main → xyz dex when you place orders
- ✅ Only check xyz dex AFTER placing orders to verify positions opened

Parameters:
- dex: (optional) Builder dex name (e.g. "xyz"). Omit for main crypto perps account.

Returns: marginSummary (accountValue, totalMarginUsed, totalNtlPos), assetPositions array"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "dex": {
                    "type": "string",
                    "description": "Builder dex name (e.g. 'xyz') for RWA/stock perps. Omit for default crypto perps.",
                },
            },
        }

    async def execute(self, ctx: ToolContext, dex: str = "", **kwargs) -> ToolResult:
        try:
            client = _get_client()
            address = await _get_address()
            data = await client.get_account_state(address, dex=dex if dex else None)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLBalancesTool(BaseTool):
    """Get spot token balances (USDC, tokens)."""

    @property
    def name(self) -> str:
        return "hl_balances"

    @property
    def description(self) -> str:
        return """Get Hyperliquid spot balances: USDC and all token holdings.

**⚠️ WARNING: This tool shows SPOT account only!**
**🎯 Use `hl_total_balance` to check total available funds for trading!**

**Understanding account modes:**
- **Unified Account (default)**: SPOT USDC is shared collateral for all trading (spot/perp/builder-dexes)
- **Disabled mode**: Spot and perp are separate, you may need to transfer between them

**When to use this tool:**
- To check spot token holdings (e.g. PURR, HYPE, etc.)
- To see USDC available for spot trading
- NOT as the sole indicator of available margin (use `hl_total_balance` for that!)

Returns: balances array with coin, hold, total for each token"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            address = await _get_address()
            data = await client.get_spot_state(address)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLTotalBalanceTool(BaseTool):
    """Get total available balance (accounts for unified account mode)."""

    @property
    def name(self) -> str:
        return "hl_total_balance"

    @property
    def description(self) -> str:
        return """Get total available balance across all Hyperliquid accounts.

**🎯 Use this to check if you have enough funds to place orders!**

This tool intelligently checks the RIGHT account based on your abstraction mode:
- **Unified Account Mode (default)**: Returns SPOT balance (shared collateral for all trading)
- **Disabled Mode**: Returns PERP balance separately

**Why use this instead of hl_account or hl_balances?**
- hl_account shows perp only ($0 if funds are in spot with unified account)
- hl_balances shows spot only
- hl_total_balance shows ACTUAL available margin regardless of mode

Returns:
- totalAvailable: Total USDC available for trading
- abstractionMode: Current mode (unifiedAccount, disabled, etc.)
- breakdown: Where the funds actually are (spot/perp)"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            address = await _get_address()

            # Check abstraction mode
            try:
                abstraction_result = await client.get_user_abstraction_state(address)
                if isinstance(abstraction_result, str):
                    abstraction_mode = abstraction_result
                elif isinstance(abstraction_result, dict):
                    abstraction_mode = abstraction_result.get("type", abstraction_result.get("state", "default"))
                else:
                    abstraction_mode = "default"
            except Exception:
                abstraction_mode = "default"

            # Get spot and perp balances
            spot_state = await client.get_spot_state(address)
            perp_state = await client.get_account_state(address)

            # Calculate spot USDC
            spot_usdc = 0.0
            for bal in spot_state.get("balances", []):
                if bal.get("coin") == "USDC":
                    spot_usdc = float(bal.get("total", 0))
                    break

            # Calculate perp margin
            perp_margin = perp_state.get("marginSummary", {})
            perp_value = float(perp_margin.get("accountValue", 0))
            perp_used = float(perp_margin.get("totalMarginUsed", 0))
            perp_available = perp_value - perp_used

            # Determine total available based on mode
            if abstraction_mode == "unifiedAccount":
                # Unified mode: all USDC is shared collateral
                total_available = spot_usdc + perp_available
                note = "Unified account: funds are shared across spot/perp/builder-dexes"
            else:
                # Separate mode: perp and spot are independent
                total_available = perp_available
                note = "Disabled mode: perp and spot are separate"

            return ToolResult(
                success=True,
                output={
                    "totalAvailable": round(total_available, 2),
                    "abstractionMode": abstraction_mode,
                    "note": note,
                    "breakdown": {
                        "spot": {
                            "usdc": round(spot_usdc, 2),
                        },
                        "perp": {
                            "accountValue": round(perp_value, 2),
                            "marginUsed": round(perp_used, 2),
                            "available": round(perp_available, 2),
                        },
                    },
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLOpenOrdersTool(BaseTool):
    """Get all open orders (perp + spot)."""

    @property
    def name(self) -> str:
        return "hl_open_orders"

    @property
    def description(self) -> str:
        return """Get all open orders on Hyperliquid (both perp and spot).

Use this to see pending limit orders, check order status, or find order IDs for cancellation.

Returns: array of orders with coin, side, sz, limitPx, oid, timestamp"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            address = await _get_address()
            data = await client.get_open_orders(address)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLMarketTool(BaseTool):
    """Get market info — mid prices, metadata."""

    @property
    def name(self) -> str:
        return "hl_market"

    @property
    def description(self) -> str:
        return """Get Hyperliquid market info: current mid prices and asset metadata.

If coin is specified, returns targeted info for that asset. Otherwise returns all mid prices.

**Crypto perps**: Use plain names — "BTC", "ETH", "SOL", etc.
**RWA / stocks / commodities**: Use "xyz:TICKER" format — "xyz:NVDA", "xyz:TSLA", "xyz:AAPL", "xyz:GOLD", "xyz:SILVER", etc.
Use dex="xyz" to list all available RWA/stock perps.

Parameters:
- coin: (optional) Specific asset like "BTC", "ETH", "xyz:NVDA". Omit for all crypto perps.
- dex: (optional) Builder dex name like "xyz" to list all assets on that dex (stocks/RWAs).

Returns: mid prices, and if coin specified: maxLeverage, szDecimals"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC', 'xyz:NVDA'). Omit for all.",
                },
                "dex": {
                    "type": "string",
                    "description": "Builder dex name (e.g. 'xyz') to list all RWA/stock perps on that dex.",
                },
            },
        }

    async def execute(self, ctx: ToolContext, coin: str = "", dex: str = "", **kwargs) -> ToolResult:
        try:
            client = _get_client()

            # List all assets on a builder dex (e.g. dex="xyz" for RWA/stocks)
            if dex and not coin:
                await client._ensure_meta()
                await client._ensure_builder_dex(dex)
                mids = await client.get_all_mids(dex=dex)
                return ToolResult(success=True, output=mids)

            if coin and ":" in coin:
                # Builder perp (e.g. "xyz:NVDA")
                dex_name = coin.split(":", 1)[0]
                await client._ensure_meta()
                await client._ensure_builder_dex(dex_name)
                mids = await client.get_all_mids(dex=dex_name)
                # allMids keys are prefixed: "xyz:NVDA"
                mid = mids.get(coin)
                if mid is None:
                    return ToolResult(
                        success=False,
                        error=f"No mid price for {coin}. Available: {list(mids.keys())[:10]}",
                    )
                meta = client._builder_meta.get(dex_name, {})
                universe = meta.get("universe", [])
                asset_info = {}
                for asset in universe:
                    # meta returns names like "xyz:NVDA" (prefixed)
                    if asset["name"] == coin or asset["name"] == coin.split(":", 1)[1]:
                        asset_info = asset
                        break
                return ToolResult(
                    success=True,
                    output={
                        "coin": coin,
                        "dex": dex_name,
                        "midPrice": mid,
                        "maxLeverage": asset_info.get("maxLeverage"),
                        "szDecimals": asset_info.get("szDecimals"),
                    },
                )

            mids = await client.get_all_mids()

            if coin:
                mid = mids.get(coin)
                # Case-insensitive fallback (e.g. "ai16z" -> "AI16Z")
                if mid is None:
                    coin_upper = coin.upper()
                    for key, val in mids.items():
                        if key.upper() == coin_upper:
                            coin = key  # Use the canonical name
                            mid = val
                            break
                if mid is None:
                    return ToolResult(
                        success=False,
                        error=f"No data for {coin}. If this is a stock/RWA, use 'xyz:{coin}' format (e.g. 'xyz:NVDA'). Use hl_market(dex=\"xyz\") to list all available RWA/stock perps.",
                    )
                await client._ensure_meta()
                meta = client._meta or {}
                universe = meta.get("universe", [])
                asset_info = {}
                for asset in universe:
                    if asset["name"] == coin:
                        asset_info = asset
                        break
                return ToolResult(
                    success=True,
                    output={
                        "coin": coin,
                        "midPrice": mid,
                        "maxLeverage": asset_info.get("maxLeverage"),
                        "szDecimals": asset_info.get("szDecimals"),
                    },
                )

            return ToolResult(success=True, output=mids)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class HLOrderbookTool(BaseTool):
    """Get L2 orderbook snapshot."""

    @property
    def name(self) -> str:
        return "hl_orderbook"

    @property
    def description(self) -> str:
        return """Get the L2 orderbook for a Hyperliquid asset.

Shows current bid/ask levels with sizes. Useful for checking liquidity and spread.
Supports builder perps via "dex:COIN" format (e.g. "xyz:NVDA").

Parameters:
- coin: Asset name (required, e.g. "BTC", "ETH", "xyz:NVDA")

Returns: levels array with [[price, size], ...] for bids and asks"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC', 'xyz:NVDA')",
                },
            },
            "required": ["coin"],
        }

    async def execute(self, ctx: ToolContext, coin: str = "", **kwargs) -> ToolResult:
        if not coin:
            return ToolResult(success=False, error="'coin' is required")
        try:
            client = _get_client()
            data = await client.get_l2_book(coin)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLFillsTool(BaseTool):
    """Get recent trade fills."""

    @property
    def name(self) -> str:
        return "hl_fills"

    @property
    def description(self) -> str:
        return """Get recent trade fills (executed orders) for this wallet.

Use this to verify if orders were filled, check execution prices, or review trade history.

Parameters:
- limit: Number of fills to return (default: 20)

Returns: array of fills with coin, side, px, sz, fee, time"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of fills (default: 20)",
                },
            },
        }

    async def execute(self, ctx: ToolContext, limit: int = 20, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            address = await _get_address()
            fills = await client.get_user_fills(address)
            return ToolResult(success=True, output=fills[:limit])
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLCandlesTool(BaseTool):
    """Get OHLCV candlestick data."""

    @property
    def name(self) -> str:
        return "hl_candles"

    @property
    def description(self) -> str:
        return """Get OHLCV candlestick data for a Hyperliquid asset.

Use this for price analysis, charting, and identifying trends.

Parameters:
- coin: Asset name (required, e.g. "BTC")
- interval: Candle interval (default: "1h"). Options: 1m, 5m, 15m, 1h, 4h, 1d
- lookback: Hours of history to fetch (default: 24)
- max_results: Maximum candles to return (default: 500)

Returns: array of candles with t (time), o, h, l, c (prices), v (volume)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC')",
                },
                "interval": {
                    "type": "string",
                    "description": "Candle interval: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)",
                },
                "lookback": {
                    "type": "integer",
                    "description": "Hours of history (default: 24)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of candles to return (default: 500)",
                },
            },
            "required": ["coin"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin: str = "",
        interval: str = "1h",
        lookback: int = 24,
        max_results: int = 500,
        **kwargs,
    ) -> ToolResult:
        if not coin:
            return ToolResult(success=False, error="'coin' is required")
        try:
            client = _get_client()
            end = int(time.time() * 1000)
            start = end - (lookback * 3600 * 1000)
            data = await client.get_candles(coin, interval, start, end)
            if isinstance(data, list) and len(data) > max_results:
                data = data[-max_results:]  # Keep most recent
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLFundingTool(BaseTool):
    """Get funding rate info."""

    @property
    def name(self) -> str:
        return "hl_funding"

    @property
    def description(self) -> str:
        return """Get funding rate information for Hyperliquid perps.

Shows predicted next funding and recent historical funding rates. Positive = longs pay shorts.

Parameters:
- coin: (optional) Specific asset. Omit for all predicted fundings.
- lookback: Hours of funding history (default: 24, only used if coin specified)

Returns: predicted funding rates, and if coin specified: historical rates"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC'). Omit for all.",
                },
                "lookback": {
                    "type": "integer",
                    "description": "Hours of history (default: 24)",
                },
            },
        }

    async def execute(
        self, ctx: ToolContext, coin: str = "", lookback: int = 24, **kwargs
    ) -> ToolResult:
        try:
            client = _get_client()
            predicted = await client.get_predicted_fundings()

            if coin:
                # predictedFundings returns [[coin, [[venue, data], ...]], ...]
                coin_predicted = None
                for entry in predicted:
                    if isinstance(entry, list) and len(entry) >= 2 and entry[0] == coin:
                        # entry[1] is [[venue, {fundingRate, ...}], ...]
                        coin_predicted = {
                            venue: data
                            for venue, data in entry[1]
                        }
                        break

                # Fetch historical
                start = int((time.time() - lookback * 3600) * 1000)
                history = await client.get_funding_history(coin, start)

                return ToolResult(
                    success=True,
                    output={
                        "coin": coin,
                        "predicted": coin_predicted or "No predicted funding found",
                        "history": history,
                    },
                )

            # Summarize all predicted fundings into a readable dict
            summary = {}
            for entry in predicted:
                if isinstance(entry, list) and len(entry) >= 2:
                    name = entry[0]
                    venues = entry[1]
                    # Pick HlPerp rate if available, otherwise first venue
                    for venue, data in venues:
                        if venue == "HlPerp":
                            summary[name] = data.get("fundingRate", "N/A")
                            break
                    else:
                        if venues:
                            summary[name] = venues[0][1].get("fundingRate", "N/A")

            return ToolResult(success=True, output={"predicted": summary})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Exchange Tools ───────────────────────────────────────────────────────────


class HLOrderTool(BaseTool):
    """Place a perp limit or market order."""

    @property
    def name(self) -> str:
        return "hl_order"

    @property
    def description(self) -> str:
        return """Place a perpetual futures order on Hyperliquid.

**Crypto**: Use plain names — "BTC", "ETH", "SOL"
**Stocks/RWA**: Use "xyz:TICKER" — "xyz:NVDA", "xyz:TSLA", "xyz:AAPL", "xyz:GOLD"

Parameters:
- coin: Asset name (required, e.g. "BTC", "ETH", "xyz:NVDA")
- side: "buy" or "sell" (required)
- size: Order size in base asset (required, e.g. 0.01 for 0.01 BTC)
- price: Limit price (optional — omit for market order)
- order_type: "limit" (GTC, default), "ioc" (fill-or-kill), "alo" (post-only)
- reduce_only: If true, only reduces existing position (default: false)

Market orders (no price): Uses IoC at mid price +/- 3% slippage.

Returns: order status with oid, filled size, price"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC', 'xyz:NVDA')",
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Order side",
                },
                "size": {
                    "type": "number",
                    "description": "Order size in base asset",
                },
                "price": {
                    "type": "number",
                    "description": "Limit price (omit for market order)",
                },
                "order_type": {
                    "type": "string",
                    "enum": ["limit", "ioc", "alo"],
                    "description": "Order type (default: limit)",
                },
                "reduce_only": {
                    "type": "boolean",
                    "description": "Reduce-only (default: false)",
                },
            },
            "required": ["coin", "side", "size"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin: str = "",
        side: str = "",
        size: float = 0,
        price: float = None,
        order_type: str = "limit",
        reduce_only: bool = False,
        **kwargs,
    ) -> ToolResult:
        if not coin or not side or not size:
            return ToolResult(
                success=False, error="'coin', 'side', and 'size' are required"
            )
        try:
            client = _get_client()
            is_buy = side.lower() == "buy"
            data = await client.place_order(
                coin=coin,
                is_buy=is_buy,
                size=size,
                price=price,
                order_type=order_type,
                reduce_only=reduce_only,
            )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLSpotOrderTool(BaseTool):
    """Place a spot limit or market order."""

    @property
    def name(self) -> str:
        return "hl_spot_order"

    @property
    def description(self) -> str:
        return """Place a spot order on Hyperliquid.

Parameters:
- coin: Token name (required, e.g. "PURR", "HYPE")
- side: "buy" or "sell" (required)
- size: Order size in base token (required)
- price: Limit price (optional — omit for market order)
- order_type: "limit" (GTC, default), "ioc" (fill-or-kill), "alo" (post-only)

Market orders (no price): Uses IoC at mid price +/- 3% slippage.

Returns: order status with oid, filled size, price"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Token name (e.g. 'PURR', 'HYPE')",
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Order side",
                },
                "size": {
                    "type": "number",
                    "description": "Order size in base token",
                },
                "price": {
                    "type": "number",
                    "description": "Limit price (omit for market order)",
                },
                "order_type": {
                    "type": "string",
                    "enum": ["limit", "ioc", "alo"],
                    "description": "Order type (default: limit)",
                },
            },
            "required": ["coin", "side", "size"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin: str = "",
        side: str = "",
        size: float = 0,
        price: float = None,
        order_type: str = "limit",
        **kwargs,
    ) -> ToolResult:
        if not coin or not side or not size:
            return ToolResult(
                success=False, error="'coin', 'side', and 'size' are required"
            )
        try:
            client = _get_client()
            is_buy = side.lower() == "buy"
            data = await client.place_order(
                coin=coin,
                is_buy=is_buy,
                size=size,
                price=price,
                order_type=order_type,
                is_spot=True,
            )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLTPSLOrderTool(BaseTool):
    """Place a stop loss or take profit order."""

    @property
    def name(self) -> str:
        return "hl_tpsl_order"

    @property
    def description(self) -> str:
        return """Place a stop loss or take profit order on Hyperliquid.

**Stop Loss**: Automatically sell when price drops to a trigger level to limit losses.
**Take Profit**: Automatically sell when price rises to a trigger level to lock in gains.

**Crypto**: Use plain names — "BTC", "ETH", "SOL"
**Stocks/RWA**: Use "xyz:TICKER" — "xyz:NVDA", "xyz:TSLA", "xyz:GOLD"

Parameters:
- coin: Asset name (required, e.g. "BTC", "ETH", "xyz:NVDA")
- side: "buy" or "sell" (required) - direction to close the position
- size: Order size in base asset (required, e.g. 0.01 for 0.01 BTC)
- trigger_px: Price that triggers the order (required)
- tpsl: "tp" for take profit, "sl" for stop loss (required)
- is_market: If true, execute as market order when triggered. If false, use limit_px. (default: true)
- limit_px: Limit price for the order when it triggers (optional, only used if is_market=false)
- reduce_only: If true, only reduces existing position (default: true)

**How it works:**
1. Order sits dormant until market price reaches trigger_px
2. When triggered, executes immediately as market order (or limit if is_market=false)
3. Use reduce_only=true to ensure it only closes positions (recommended for TP/SL)

**Examples:**
- Stop loss: If you're long BTC at $95k and want to exit if it drops to $90k:
  `hl_tpsl_order(coin="BTC", side="sell", size=0.1, trigger_px=90000, tpsl="sl")`

- Take profit: If you're long ETH and want to take profit at $3500:
  `hl_tpsl_order(coin="ETH", side="sell", size=1.0, trigger_px=3500, tpsl="tp")`

Returns: order status with oid, trigger details"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC', 'xyz:NVDA')",
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Order side (usually opposite of your position)",
                },
                "size": {
                    "type": "number",
                    "description": "Order size in base asset",
                },
                "trigger_px": {
                    "type": "number",
                    "description": "Price that triggers the order",
                },
                "tpsl": {
                    "type": "string",
                    "enum": ["tp", "sl"],
                    "description": "Order type: 'tp' for take profit, 'sl' for stop loss",
                },
                "is_market": {
                    "type": "boolean",
                    "description": "Execute as market order when triggered (default: true)",
                },
                "limit_px": {
                    "type": "number",
                    "description": "Limit price when triggered (only if is_market=false)",
                },
                "reduce_only": {
                    "type": "boolean",
                    "description": "Only reduce position, don't open new (default: true)",
                },
            },
            "required": ["coin", "side", "size", "trigger_px", "tpsl"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin: str = "",
        side: str = "",
        size: float = 0,
        trigger_px: float = 0,
        tpsl: str = "",
        is_market: bool = True,
        limit_px: float = None,
        reduce_only: bool = True,
        **kwargs,
    ) -> ToolResult:
        if not coin or not side or not size or not trigger_px or not tpsl:
            return ToolResult(
                success=False,
                error="'coin', 'side', 'size', 'trigger_px', and 'tpsl' are required",
            )
        if tpsl not in ("tp", "sl"):
            return ToolResult(
                success=False,
                error="'tpsl' must be either 'tp' (take profit) or 'sl' (stop loss)",
            )
        try:
            client = _get_client()
            is_buy = side.lower() == "buy"

            # For trigger orders: always pass a limit price
            # - For market triggers: use the trigger price as limit (matches SDK)
            # - For limit triggers: use the specified limit price
            price = trigger_px if is_market else (limit_px or trigger_px)

            data = await client.place_order(
                coin=coin,
                is_buy=is_buy,
                size=size,
                price=price,
                reduce_only=reduce_only,
                trigger_px=trigger_px,
                tpsl=tpsl,
            )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLCancelTool(BaseTool):
    """Cancel an order (perp or spot)."""

    @property
    def name(self) -> str:
        return "hl_cancel"

    @property
    def description(self) -> str:
        return """Cancel an open order on Hyperliquid by order ID.

Parameters:
- coin: Asset name (required, e.g. "BTC", "xyz:NVDA")
- order_id: Order ID to cancel (required — get from hl_open_orders)

Returns: cancel confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC', 'xyz:NVDA')",
                },
                "order_id": {
                    "type": "integer",
                    "description": "Order ID (oid) to cancel",
                },
            },
            "required": ["coin", "order_id"],
        }

    async def execute(
        self, ctx: ToolContext, coin: str = "", order_id: int = 0, **kwargs
    ) -> ToolResult:
        if not coin or not order_id:
            return ToolResult(
                success=False, error="'coin' and 'order_id' are required"
            )
        try:
            client = _get_client()
            data = await client.cancel_order(coin, order_id)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLCancelAllTool(BaseTool):
    """Cancel all open orders."""

    @property
    def name(self) -> str:
        return "hl_cancel_all"

    @property
    def description(self) -> str:
        return """Cancel all open orders on Hyperliquid.

Parameters:
- coin: (optional) Asset name to cancel orders for. Omit to cancel ALL orders.

Returns: array of cancel results"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Asset name (optional — omit for all)",
                },
            },
        }

    async def execute(self, ctx: ToolContext, coin: str = "", **kwargs) -> ToolResult:
        try:
            client = _get_client()
            results = await client.cancel_all(coin or None)
            return ToolResult(
                success=True,
                output={
                    "cancelled": len(results),
                    "results": results,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLModifyTool(BaseTool):
    """Modify an existing order."""

    @property
    def name(self) -> str:
        return "hl_modify"

    @property
    def description(self) -> str:
        return """Modify an existing order on Hyperliquid (change price or size).

Parameters:
- order_id: Order ID to modify (required)
- coin: Asset name (required, e.g. "BTC", "xyz:NVDA")
- side: "buy" or "sell" (required)
- size: New size (required)
- price: New price (required)

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
                "coin": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC', 'xyz:NVDA')",
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Order side",
                },
                "size": {
                    "type": "number",
                    "description": "New order size",
                },
                "price": {
                    "type": "number",
                    "description": "New limit price",
                },
            },
            "required": ["order_id", "coin", "side", "size", "price"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        order_id: int = 0,
        coin: str = "",
        side: str = "",
        size: float = 0,
        price: float = 0,
        **kwargs,
    ) -> ToolResult:
        if not order_id or not coin or not side or not size or not price:
            return ToolResult(
                success=False,
                error="All parameters required: order_id, coin, side, size, price",
            )
        try:
            client = _get_client()
            is_buy = side.lower() == "buy"
            data = await client.modify_order(
                oid=order_id,
                coin=coin,
                is_buy=is_buy,
                size=size,
                price=price,
            )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLLeverageTool(BaseTool):
    """Set leverage for a perp."""

    @property
    def name(self) -> str:
        return "hl_leverage"

    @property
    def description(self) -> str:
        return """Set leverage for a Hyperliquid perpetual asset.

Parameters:
- coin: Asset name (required, e.g. "BTC", "xyz:NVDA")
- leverage: Leverage multiplier (required, e.g. 5 for 5x)
- cross: If true, use cross margin. If false, use isolated margin. (default: true)

Returns: leverage update confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Asset name (e.g. 'BTC', 'xyz:NVDA')",
                },
                "leverage": {
                    "type": "integer",
                    "description": "Leverage multiplier (e.g. 5)",
                },
                "cross": {
                    "type": "boolean",
                    "description": "Cross margin (default: true)",
                },
            },
            "required": ["coin", "leverage"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin: str = "",
        leverage: int = 0,
        cross: bool = True,
        **kwargs,
    ) -> ToolResult:
        if not coin or not leverage:
            return ToolResult(
                success=False, error="'coin' and 'leverage' are required"
            )
        try:
            client = _get_client()
            # Builder perps (HIP-3) require isolated margin
            if ":" in coin:
                cross = False
            data = await client.update_leverage(coin, leverage, is_cross=cross)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLTransferUsdTool(BaseTool):
    """Transfer USDC between spot and perp."""

    @property
    def name(self) -> str:
        return "hl_transfer_usd"

    @property
    def description(self) -> str:
        return """Transfer USDC between Hyperliquid spot and perp accounts.

**⚠️ IMPORTANT: This will FAIL if unified account mode is active!**

Unified account mode (default) shares funds automatically - manual transfers are disabled.
If you get "Action disabled when unified account is active", this is expected behavior.

**When to use:**
- Only when unified account is DISABLED
- To manually move USDC between spot ↔ perp
- Not needed when unified account is active (funds are already shared!)

**To check your mode:** Use `hl_total_balance` - it shows the current abstraction mode

Parameters:
- amount: USDC amount to transfer (required, e.g. 100.0)
- to_perp: If true, transfer from spot to perp. If false, from perp to spot. (default: true)

Returns: transfer confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "USDC amount to transfer",
                },
                "to_perp": {
                    "type": "boolean",
                    "description": "True = spot→perp, False = perp→spot (default: true)",
                },
            },
            "required": ["amount"],
        }

    async def execute(
        self, ctx: ToolContext, amount: float = 0, to_perp: bool = True, **kwargs
    ) -> ToolResult:
        if not amount or amount <= 0:
            return ToolResult(success=False, error="'amount' must be positive")
        try:
            client = _get_client()
            data = await client.transfer_usd(amount, to_perp=to_perp)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLWithdrawTool(BaseTool):
    """Withdraw USDC from Hyperliquid to Arbitrum wallet."""

    @property
    def name(self) -> str:
        return "hl_withdraw"

    @property
    def description(self) -> str:
        return """Withdraw USDC from Hyperliquid to an Arbitrum wallet (L1 bridge withdrawal).

Fee: 1 USDC (deducted by Hyperliquid). Processing time: ~5 minutes.

Parameters:
- amount: USDC amount to withdraw (required, e.g. 100.0)
- destination: Target wallet address (optional — defaults to this agent's own wallet)

Returns: withdrawal confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "USDC amount to withdraw",
                },
                "destination": {
                    "type": "string",
                    "description": "Target Arbitrum wallet address (default: own wallet)",
                },
            },
            "required": ["amount"],
        }

    async def execute(
        self, ctx: ToolContext, amount: float = 0, destination: str = "", **kwargs
    ) -> ToolResult:
        if not amount or amount <= 0:
            return ToolResult(success=False, error="'amount' must be positive")
        try:
            client = _get_client()
            data = await client.withdraw_from_bridge(
                amount, destination=destination or None
            )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLDepositTool(BaseTool):
    """Deposit USDC from Arbitrum wallet into Hyperliquid."""

    @property
    def name(self) -> str:
        return "hl_deposit"

    @property
    def description(self) -> str:
        return """Deposit USDC from this agent's Arbitrum wallet into Hyperliquid.

Sends an on-chain ERC-20 transfer of USDC to the Hyperliquid bridge contract.
Minimum deposit: 5 USDC. Requires USDC balance on Arbitrum.

Parameters:
- amount: USDC amount to deposit (required, minimum 5.0)

Returns: approve_tx_hash, transfer_tx_hash, amount_deposited"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "USDC amount to deposit (minimum 5)",
                },
            },
            "required": ["amount"],
        }

    async def execute(
        self, ctx: ToolContext, amount: float = 0, **kwargs
    ) -> ToolResult:
        if not amount or amount <= 0:
            return ToolResult(success=False, error="'amount' must be positive")
        if amount < 5:
            return ToolResult(
                success=False,
                error="Minimum Hyperliquid deposit is 5 USDC",
            )
        try:
            client = _get_client()
            data = await client.deposit_usdc(amount)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HLSetAbstractionTool(BaseTool):
    """Enable or disable unified account (DEX abstraction)."""

    @property
    def name(self) -> str:
        return "hl_set_abstraction"

    @property
    def description(self) -> str:
        return """Set Hyperliquid account abstraction mode.

**Abstraction modes:**
- "unifiedAccount": Unified margin across spot and perp (auto-transfers, can't manually transfer)
- "disabled": Separate spot/perp accounts (can manually transfer between them)
- "portfolioMargin": Advanced portfolio margin (if eligible)

**When to use:**
- Disable unified account to manually transfer funds and trade builder perps (xyz:NVDA, etc.)
- Enable unified account for automatic fund management across spot and perp

Parameters:
- mode: Abstraction mode (required: "unifiedAccount", "disabled", or "portfolioMargin")

Returns: abstraction update confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["unifiedAccount", "disabled", "portfolioMargin"],
                    "description": "Abstraction mode to set",
                },
            },
            "required": ["mode"],
        }

    async def execute(
        self, ctx: ToolContext, mode: str = "", **kwargs
    ) -> ToolResult:
        if mode not in ("unifiedAccount", "disabled", "portfolioMargin"):
            return ToolResult(
                success=False,
                error="'mode' must be 'unifiedAccount', 'disabled', or 'portfolioMargin'",
            )
        try:
            client = _get_client()
            address = await _get_address()
            # Call the private method directly for setting abstraction
            data = await client._user_set_abstraction(address, mode)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
