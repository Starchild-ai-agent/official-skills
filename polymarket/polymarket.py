"""
Polymarket Tool Wrappers v4.0

Privy-only. 13 tools: auth(1) + discovery(4) + trading(8).
No CLI dependency. Pure API via tools/ helpers.
"""
import asyncio
import logging
import json
import time
from typing import Any, Dict, Optional

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

try:
    from .tools.auth import build_clob_auth_message, derive_api_credentials
    from .tools.market_data import search, full_lookup, analyze_orderbook, rr_analysis
    from .tools.trading import (
        get_balance, get_open_orders, get_trades, get_positions,
        build_order_payload, post_signed_order, get_market_info,
        cancel_order, cancel_all_orders,
    )
    AVAILABLE = True
except ImportError as e:
    logger.warning(f"Polymarket tools not available: {e}")
    AVAILABLE = False


def _unavailable():
    return ToolResult(success=False, error="Polymarket tools not available")


# ==================== Authentication ====================

class PolymarketAuthTool(BaseTool):
    @property
    def name(self): return "polymarket_auth"
    @property
    def description(self):
        return """Create/refresh Polymarket API credentials (one-time setup).

Step 1: polymarket_auth(wallet_address="0x...") → returns EIP-712 message to sign
Step 2: Sign with wallet_sign_typed_data
Step 3: polymarket_auth(wallet_address="0x...", signature="0x...", timestamp=T) → derives credentials, saves to .env"""

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "wallet_address": {"type": "string", "description": "Polygon wallet address"},
                "signature": {"type": "string", "description": "Signed EIP-712 message (step 2)"},
                "timestamp": {"type": "integer", "description": "Timestamp from step 1"},
            },
            "required": ["wallet_address"],
        }

    async def execute(self, ctx, wallet_address, signature=None, timestamp=None):
        if not AVAILABLE: return _unavailable()
        try:
            if not signature:
                ts = int(time.time())
                msg = await asyncio.to_thread(build_clob_auth_message, wallet_address, ts)
                return ToolResult(success=True, output={
                    "step": "sign", "timestamp": ts, "eip712_message": msg,
                    "instructions": "Sign with wallet_sign_typed_data, then call again with signature and timestamp",
                })
            else:
                creds = await asyncio.to_thread(derive_api_credentials, signature, wallet_address, timestamp or 0)
                # Auto-save to .env
                import os
                env_path = "/data/workspace/.env"
                updates = {
                    "POLY_API_KEY": creds.get("apiKey", ""),
                    "POLY_SECRET": creds.get("secret", ""),
                    "POLY_PASSPHRASE": creds.get("passphrase", ""),
                    "POLY_WALLET": wallet_address,
                }
                try:
                    existing = {}
                    if os.path.exists(env_path):
                        with open(env_path) as f:
                            for line in f:
                                line = line.strip()
                                if line and "=" in line and not line.startswith("#"):
                                    k, v = line.split("=", 1)
                                    existing[k.strip()] = v.strip()
                    existing.update(updates)
                    with open(env_path, "w") as f:
                        for k, v in existing.items():
                            f.write(f"{k}={v}\n")
                    # Also set in current process
                    for k, v in updates.items():
                        os.environ[k] = v
                except Exception as e:
                    logger.warning(f"Failed to save credentials to .env: {e}")

                return ToolResult(success=True, output={
                    "step": "complete",
                    "api_key": creds.get("apiKey", "")[:8] + "...",
                    "saved_to": env_path,
                })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== Discovery ====================

class PolymarketSearchTool(BaseTool):
    @property
    def name(self): return "polymarket_search"
    @property
    def description(self):
        return "Search Polymarket markets. Uses search-v2 (primary) with /markets fallback. Returns events with nested markets, prices, token_ids."
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        }

    async def execute(self, ctx, query, limit=10):
        if not AVAILABLE: return _unavailable()
        try:
            result = await asyncio.to_thread(search, query, limit)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketLookupTool(BaseTool):
    @property
    def name(self): return "polymarket_lookup"
    @property
    def description(self):
        return "Deep event/market lookup by URL or slug. Returns enriched data with live prices per outcome."
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "url_or_slug": {"type": "string", "description": "Polymarket URL or event slug"},
            },
            "required": ["url_or_slug"],
        }

    async def execute(self, ctx, url_or_slug):
        if not AVAILABLE: return _unavailable()
        try:
            result = await asyncio.to_thread(full_lookup, url_or_slug)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketOrderbookTool(BaseTool):
    @property
    def name(self): return "polymarket_orderbook"
    @property
    def description(self):
        return "Analyze orderbook for a token. Returns best bid/ask, spread, depth at 2¢/5¢ bands, top 5 levels."
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "token_id": {"type": "string", "description": "CLOB token ID"},
            },
            "required": ["token_id"],
        }

    async def execute(self, ctx, token_id):
        if not AVAILABLE: return _unavailable()
        try:
            result = await asyncio.to_thread(analyze_orderbook, token_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketRRAnalysisTool(BaseTool):
    @property
    def name(self): return "polymarket_rr_analysis"
    @property
    def description(self):
        return "Risk/reward analysis for a potential trade. Returns entry price, tokens, profit/loss, R/R ratio."
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "token_id": {"type": "string", "description": "CLOB token ID"},
                "side": {"type": "string", "description": "YES or NO"},
                "size_usd": {"type": "number", "description": "Trade size in USD"},
            },
            "required": ["token_id", "side", "size_usd"],
        }

    async def execute(self, ctx, token_id, side, size_usd):
        if not AVAILABLE: return _unavailable()
        try:
            result = await asyncio.to_thread(rr_analysis, token_id, side, size_usd)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== Trading ====================

class PolymarketGetBalanceTool(BaseTool):
    @property
    def name(self): return "polymarket_get_balances"
    @property
    def description(self):
        return "Get USDC.e balance and contract allowances on Polymarket."
    @property
    def parameters(self):
        return {"type": "object", "properties": {}}

    async def execute(self, ctx):
        if not AVAILABLE: return _unavailable()
        try:
            result = await asyncio.to_thread(get_balance)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketGetOrdersTool(BaseTool):
    @property
    def name(self): return "polymarket_get_orders"
    @property
    def description(self):
        return "Get all open GTC orders on Polymarket."
    @property
    def parameters(self):
        return {"type": "object", "properties": {}}

    async def execute(self, ctx):
        if not AVAILABLE: return _unavailable()
        try:
            result = await asyncio.to_thread(get_open_orders)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketGetPositionsTool(BaseTool):
    @property
    def name(self): return "polymarket_get_positions"
    @property
    def description(self):
        return "Get current positions on Polymarket."
    @property
    def parameters(self):
        return {"type": "object", "properties": {}}

    async def execute(self, ctx):
        if not AVAILABLE: return _unavailable()
        try:
            result = await asyncio.to_thread(get_positions)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketGetTradesTool(BaseTool):
    @property
    def name(self): return "polymarket_get_trades"
    @property
    def description(self):
        return "Get recent trade history on Polymarket."
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max trades to return (default 20)"},
            },
        }

    async def execute(self, ctx, limit=20):
        if not AVAILABLE: return _unavailable()
        try:
            result = await asyncio.to_thread(get_trades, limit)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketPrepareOrderTool(BaseTool):
    @property
    def name(self): return "polymarket_prepare_order"
    @property
    def description(self):
        return """Build EIP-712 order payload for signing. Auto-fetches market metadata (tick_size, fee_bps, neg_risk).

Returns domain/types/message for wallet_sign_typed_data, plus order_meta for polymarket_post_order."""

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "token_id": {"type": "string", "description": "CLOB token ID"},
                "side": {"type": "string", "description": "BUY or SELL"},
                "price": {"type": "number", "description": "Order price (0.01-0.99)"},
                "size": {"type": "number", "description": "Order size in tokens"},
            },
            "required": ["token_id", "side", "price", "size"],
        }

    async def execute(self, ctx, token_id, side, price, size):
        if not AVAILABLE: return _unavailable()
        try:
            domain, types, message, meta = await asyncio.to_thread(
                build_order_payload, token_id, side, price, size
            )
            return ToolResult(success=True, output={
                "domain": domain,
                "types": types,
                "primaryType": "Order",
                "message": message,
                "order_meta": meta,
                "instructions": "Sign with wallet_sign_typed_data(domain, types, 'Order', message), then call polymarket_post_order",
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketPostOrderTool(BaseTool):
    @property
    def name(self): return "polymarket_post_order"
    @property
    def description(self):
        return "Post a signed order to Polymarket CLOB. Requires signature from wallet_sign_typed_data and order_meta from polymarket_prepare_order."
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "token_id": {"type": "string", "description": "CLOB token ID"},
                "signature": {"type": "string", "description": "EIP-712 signature"},
                "order_meta": {"type": "object", "description": "Meta dict from polymarket_prepare_order"},
            },
            "required": ["token_id", "signature", "order_meta"],
        }

    async def execute(self, ctx, token_id, signature, order_meta):
        if not AVAILABLE: return _unavailable()
        try:
            status_code, response = await asyncio.to_thread(
                post_signed_order, token_id, signature, order_meta
            )
            return ToolResult(
                success=(200 <= status_code < 300),
                output={"status_code": status_code, "response": response},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketCancelOrderTool(BaseTool):
    @property
    def name(self): return "polymarket_cancel_order"
    @property
    def description(self):
        return "Cancel a specific Polymarket order by order ID."
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID to cancel"},
            },
            "required": ["order_id"],
        }

    async def execute(self, ctx, order_id):
        if not AVAILABLE: return _unavailable()
        try:
            status_code, response = await asyncio.to_thread(cancel_order, order_id)
            return ToolResult(
                success=(200 <= status_code < 300),
                output={"status_code": status_code, "response": response},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketCancelAllTool(BaseTool):
    @property
    def name(self): return "polymarket_cancel_all"
    @property
    def description(self):
        return "Cancel ALL open Polymarket orders. Use with caution."
    @property
    def parameters(self):
        return {"type": "object", "properties": {}}

    async def execute(self, ctx):
        if not AVAILABLE: return _unavailable()
        try:
            status_code, response = await asyncio.to_thread(cancel_all_orders)
            return ToolResult(
                success=(200 <= status_code < 300),
                output={"status_code": status_code, "response": response},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
