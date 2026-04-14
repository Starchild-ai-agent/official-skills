"""
1inch Limit Order (Orderbook) Tools — EIP-712 signed limit orders via 1inch Orderbook API.

Read-only tools (2): oneinch_get_orders, oneinch_get_order
Write tools (2):     oneinch_create_limit_order, oneinch_cancel_limit_order

Flow:
  1. Build order struct locally (EIP-712)
  2. Sign with platform wallet (wallet_sign_typed_data)
  3. POST to 1inch Orderbook API
  4. Order lives off-chain; resolvers fill it on-chain when price is met
"""

import hashlib
import logging
import os
import time

from core.http_client import proxied_get, proxied_post
from core.tool import BaseTool, ToolContext, ToolResult
from .client import SUPPORTED_CHAINS, resolve_chain

logger = logging.getLogger(__name__)

SC_CALLER_ID = "skill:1inch"
ORDERBOOK_BASE = "https://api.1inch.dev/orderbook/v4.0"

# Limit Order Protocol v4 contract addresses per chain
LOP_CONTRACTS = {
    1:     "0x111111125421cA6dc452d289314280a0f8842A65",  # Ethereum
    42161: "0x111111125421cA6dc452d289314280a0f8842A65",  # Arbitrum
    8453:  "0x111111125421cA6dc452d289314280a0f8842A65",  # Base
    10:    "0x111111125421cA6dc452d289314280a0f8842A65",  # Optimism
    137:   "0x111111125421cA6dc452d289314280a0f8842A65",  # Polygon
    56:    "0x111111125421cA6dc452d289314280a0f8842A65",  # BSC
    43114: "0x111111125421cA6dc452d289314280a0f8842A65",  # Avalanche
    100:   "0x111111125421cA6dc452d289314280a0f8842A65",  # Gnosis
}

# EIP-712 type definitions for Limit Order v4
ORDER_TYPES = {
    "Order": [
        {"name": "salt",          "type": "uint256"},
        {"name": "maker",         "type": "address"},
        {"name": "receiver",      "type": "address"},
        {"name": "makerAsset",    "type": "address"},
        {"name": "takerAsset",    "type": "address"},
        {"name": "makingAmount",  "type": "uint256"},
        {"name": "takingAmount",  "type": "uint256"},
        {"name": "makerTraits",   "type": "uint256"},
    ]
}


def _ob_get(chain_id: int, path: str, params: dict = None) -> dict:
    url = f"{ORDERBOOK_BASE}/{chain_id}{path}"
    resp = proxied_get(url, params=params or {}, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        raise Exception(f"1inch Orderbook API {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _ob_post(chain_id: int, path: str, body: dict) -> dict:
    url = f"{ORDERBOOK_BASE}/{chain_id}{path}"
    resp = proxied_post(url, json=body, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        raise Exception(f"1inch Orderbook API {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _build_maker_traits(expiry_seconds: int = 0, allow_partial_fill: bool = True) -> int:
    """
    Build makerTraits bitmask for Limit Order v4.
    Bit layout (from 1inch LOP v4 spec):
      bit 255: NO_PARTIAL_FILLS
      bits 80..119: expiration (40-bit unix timestamp)
    """
    traits = 0
    if not allow_partial_fill:
        traits |= (1 << 255)
    if expiry_seconds > 0:
        expiry_ts = int(time.time()) + expiry_seconds
        # Expiration occupies bits 80-119 (40 bits)
        traits |= ((expiry_ts & 0xFFFFFFFFFF) << 80)
    return traits


def _random_salt() -> int:
    """Generate a secure random 256-bit salt."""
    return int.from_bytes(os.urandom(32), "big")


# ── Read-Only Tools ──────────────────────────────────────────────────────────

class GetOrdersTool(BaseTool):
    """Get open limit orders for a wallet address."""

    @property
    def name(self) -> str:
        return "oneinch_get_orders"

    @property
    def description(self) -> str:
        return """Get open limit orders on 1inch for a wallet address.

Returns all active limit orders placed by the specified wallet (or the agent wallet if omitted).

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- wallet_address: Address to query (optional, defaults to agent wallet)
- page: Page number for pagination (default: 1)
- limit: Number of orders per page (default: 10, max: 100)

Returns: list of open orders with hash, status, maker/taker assets, amounts, expiry"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "description": "Network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis"},
                "wallet_address": {"type": "string", "description": "Wallet address to query (optional, defaults to agent wallet)"},
                "page": {"type": "integer", "description": "Page number (default: 1)"},
                "limit": {"type": "integer", "description": "Results per page (default: 10, max: 100)"},
            },
            "required": ["chain"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", wallet_address: str = "",
                      page: int = 1, limit: int = 10, **kwargs) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        try:
            chain_id = resolve_chain(chain)
            if not wallet_address:
                from tools.wallet import wallet_info
                info = wallet_info()
                for w in (info if isinstance(info, list) else info.get("wallets", [])):
                    if w.get("chain_type") == "ethereum":
                        wallet_address = w["wallet_address"]
                        break
            if not wallet_address:
                return ToolResult(success=False, error="wallet_address required")

            data = _ob_get(chain_id, f"/address/{wallet_address}", {
                "page": page,
                "limit": min(limit, 100),
                "sortBy": "createDateTime",
            })
            return ToolResult(success=True, output={"chain": chain, "wallet": wallet_address, "orders": data})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetOrderTool(BaseTool):
    """Get a specific limit order by hash."""

    @property
    def name(self) -> str:
        return "oneinch_get_order"

    @property
    def description(self) -> str:
        return """Get details of a specific limit order by its hash on 1inch Orderbook.

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- order_hash: The order hash (returned from oneinch_create_limit_order)

Returns: order status, fill amounts, expiry, maker/taker info"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "description": "Network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis"},
                "order_hash": {"type": "string", "description": "The order hash"},
            },
            "required": ["chain", "order_hash"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", order_hash: str = "", **kwargs) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        if not order_hash:
            return ToolResult(success=False, error="'order_hash' is required")
        try:
            chain_id = resolve_chain(chain)
            data = _ob_get(chain_id, f"/{order_hash}")
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Write Tools ──────────────────────────────────────────────────────────────

class CreateLimitOrderTool(BaseTool):
    """Create and submit a limit order on 1inch."""

    @property
    def name(self) -> str:
        return "oneinch_create_limit_order"

    @property
    def description(self) -> str:
        return """Create and submit a limit order on 1inch Orderbook.

A limit order lets you swap tokens at a specific price target. It is signed off-chain and submitted to the 1inch Orderbook. Resolvers fill it when the market price matches.

Both maker and taker tokens need approval for the 1inch Limit Order Protocol contract.
Use oneinch_check_allowance and oneinch_approve before creating an order.

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- maker_asset: Token address you are selling (maker asset)
- taker_asset: Token address you want to receive (taker asset)
- making_amount: Amount of maker_asset to sell, in wei
- taking_amount: Amount of taker_asset you want to receive, in wei
- expiry_seconds: Order validity duration in seconds (default: 86400 = 24 hours, 0 = no expiry)
- allow_partial_fill: Allow partial fills (default: true)

Example: Sell 100 USDC for at least 0.001 WETH
  maker_asset=USDC, taker_asset=WETH, making_amount=100000000, taking_amount=1000000000000000

Returns: order_hash, order details"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "description": "Network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis"},
                "maker_asset": {"type": "string", "description": "Token address you are selling"},
                "taker_asset": {"type": "string", "description": "Token address you want to receive"},
                "making_amount": {"type": "string", "description": "Amount of maker_asset in wei"},
                "taking_amount": {"type": "string", "description": "Amount of taker_asset in wei"},
                "expiry_seconds": {"type": "integer", "description": "Order validity in seconds (default: 86400 = 24h, 0 = no expiry)"},
                "allow_partial_fill": {"type": "boolean", "description": "Allow partial fills (default: true)"},
            },
            "required": ["chain", "maker_asset", "taker_asset", "making_amount", "taking_amount"],
        }

    async def execute(
        self, ctx: ToolContext,
        chain: str = "", maker_asset: str = "", taker_asset: str = "",
        making_amount: str = "", taking_amount: str = "",
        expiry_seconds: int = 86400, allow_partial_fill: bool = True,
        **kwargs,
    ) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        if not maker_asset or not taker_asset or not making_amount or not taking_amount:
            return ToolResult(success=False, error="maker_asset, taker_asset, making_amount, taking_amount all required")

        try:
            from tools.wallet import wallet_info, wallet_sign_typed_data
            chain_id = resolve_chain(chain)
            contract = LOP_CONTRACTS.get(chain_id)
            if not contract:
                return ToolResult(success=False, error=f"Limit orders not supported on chain {chain}")

            # Get wallet address
            wallet_address = ""
            info = wallet_info()
            for w in (info if isinstance(info, list) else info.get("wallets", [])):
                if w.get("chain_type") == "ethereum":
                    wallet_address = w["wallet_address"]
                    break
            if not wallet_address:
                return ToolResult(success=False, error="No ethereum wallet configured")

            # Build order struct
            salt = _random_salt()
            maker_traits = _build_maker_traits(expiry_seconds, allow_partial_fill)

            order = {
                "salt": str(salt),
                "maker": wallet_address,
                "receiver": "0x0000000000000000000000000000000000000000",
                "makerAsset": maker_asset,
                "takerAsset": taker_asset,
                "makingAmount": str(making_amount),
                "takingAmount": str(taking_amount),
                "makerTraits": str(maker_traits),
            }

            # EIP-712 typed data
            typed_data = {
                "domain": {
                    "name": "1inch Aggregation Router",
                    "version": "6",
                    "chainId": chain_id,
                    "verifyingContract": contract,
                },
                "types": ORDER_TYPES,
                "primaryType": "Order",
                "message": {
                    "salt": salt,
                    "maker": wallet_address,
                    "receiver": "0x0000000000000000000000000000000000000000",
                    "makerAsset": maker_asset,
                    "takerAsset": taker_asset,
                    "makingAmount": int(making_amount),
                    "takingAmount": int(taking_amount),
                    "makerTraits": maker_traits,
                },
            }

            # Sign order
            sig_result = wallet_sign_typed_data(
                domain=typed_data["domain"],
                types=typed_data["types"],
                primary_type=typed_data["primaryType"],
                message=typed_data["message"],
            )
            signature = sig_result.get("signature", "")
            if not signature:
                return ToolResult(success=False, error=f"Wallet sign failed: {sig_result}")

            # Submit to Orderbook API
            payload = {"orderHash": "", "signature": signature, "data": order}
            result = _ob_post(chain_id, "", payload)

            return ToolResult(
                success=True,
                output={
                    "status": "order_submitted",
                    "chain": chain,
                    "order_hash": result.get("orderHash", result.get("hash", "")),
                    "maker_asset": maker_asset,
                    "taker_asset": taker_asset,
                    "making_amount": making_amount,
                    "taking_amount": taking_amount,
                    "expiry_seconds": expiry_seconds,
                    "allow_partial_fill": allow_partial_fill,
                    "raw": result,
                },
            )
        except Exception as e:
            err = str(e)
            if "policy" in err.lower():
                return ToolResult(
                    success=False,
                    error=f"Policy violation: {err}. Use wallet_propose_policy to allow signing.",
                )
            return ToolResult(success=False, error=err)


class CancelLimitOrderTool(BaseTool):
    """Cancel a limit order on-chain via 1inch."""

    @property
    def name(self) -> str:
        return "oneinch_cancel_limit_order"

    @property
    def description(self) -> str:
        return """Cancel a limit order on-chain via 1inch Limit Order Protocol.

Sends an on-chain cancellation transaction. Requires gas.

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- order_hash: The order hash to cancel (returned from oneinch_create_limit_order)

Returns: transaction hash"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "description": "Network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis"},
                "order_hash": {"type": "string", "description": "The order hash to cancel"},
            },
            "required": ["chain", "order_hash"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", order_hash: str = "", **kwargs) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        if not order_hash:
            return ToolResult(success=False, error="'order_hash' is required")

        try:
            from tools.wallet import wallet_sign_transaction
            chain_id = resolve_chain(chain)
            contract = LOP_CONTRACTS.get(chain_id)
            if not contract:
                return ToolResult(success=False, error=f"Limit orders not supported on chain {chain}")

            # Get order details to build cancel calldata
            order_data = _ob_get(chain_id, f"/{order_hash}")
            order_struct = order_data.get("data", {})
            if not order_struct:
                return ToolResult(success=False, error=f"Order {order_hash} not found")

            # cancelOrder(Order calldata order) — selector: 0x5ead15b7 (LOP v4)
            # For simplicity, use the orderHash-based cancel if available
            # cancelOrder selector in v4: depends on implementation
            # Use the REST cancel endpoint if available, fallback to on-chain
            try:
                result = _ob_post(chain_id, f"/{order_hash}", {})
                return ToolResult(success=True, output={"status": "cancel_requested", "order_hash": order_hash, "raw": result})
            except Exception:
                pass

            # On-chain fallback: encode cancelOrder(makerTraits, orderHash)
            from web3 import Web3
            maker_traits = int(order_struct.get("makerTraits", "0"))
            order_hash_bytes = bytes.fromhex(order_hash.replace("0x", ""))

            # cancelOrder(uint256 makerTraits, bytes32 orderHash) selector = 0x2b155166
            selector = bytes.fromhex("2b155166")
            calldata = (
                selector
                + maker_traits.to_bytes(32, "big")
                + order_hash_bytes
            )

            result = wallet_sign_transaction({
                "to": contract,
                "data": "0x" + calldata.hex(),
                "value": "0",
                "chain_id": chain_id,
            })
            return ToolResult(
                success=True,
                output={"status": "cancel_sent", "order_hash": order_hash, "tx": result},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
