"""
1inch Fusion+ Cross-Chain Swap Tools — BaseTool subclasses for cross-chain swaps.

Read-only tools (2): oneinch_cross_chain_quote, oneinch_cross_chain_status
Write tools (1): oneinch_cross_chain_swap (long-running — recommend background task)
"""

import asyncio
import json
import logging
import time

from core.tool import BaseTool, ToolContext, ToolResult
from .client import SUPPORTED_CHAINS, resolve_chain
from .fusion_client import (
    FusionPlusClient,
    generate_secrets,
    hash_secret,
)

logger = logging.getLogger(__name__)

# Singleton client (no chain-specific base URL needed for Fusion+)
_fusion_client: FusionPlusClient = None


def _get_fusion_client() -> FusionPlusClient:
    global _fusion_client
    if _fusion_client is None:
        _fusion_client = FusionPlusClient()
    return _fusion_client


# Reverse lookup: chain_id → chain_name
CHAIN_ID_TO_NAME = {v: k for k, v in SUPPORTED_CHAINS.items()}

MAX_POLL_TIME = 600  # 10 minutes
POLL_INTERVAL = 15   # seconds (2 calls/15s = 8 req/min, under 15/min rate limit)


# ── Read-Only Tools ──────────────────────────────────────────────────────────


class CrossChainQuoteTool(BaseTool):
    """Get a cross-chain swap quote via 1inch Fusion+."""

    @property
    def name(self) -> str:
        return "oneinch_cross_chain_quote"

    @property
    def description(self) -> str:
        return """Get a cross-chain swap price quote via 1inch Fusion+.

Returns the estimated output amount for swapping tokens across different chains (e.g., ETH on Ethereum to USDC on Arbitrum). No transaction is executed.

Fusion+ uses intent-based atomic swaps — resolvers handle gas on both chains, so the user doesn't need gas on the destination chain.

Parameters:
- src_chain: Source network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- dst_chain: Destination network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- src_token: Source token address on the source chain
- dst_token: Destination token address on the destination chain
- amount: Amount in wei (smallest unit)

Returns: estimated output amount, presets (slow/medium/fast), fees"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "src_chain": {
                    "type": "string",
                    "description": "Source network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis",
                },
                "dst_chain": {
                    "type": "string",
                    "description": "Destination network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis",
                },
                "src_token": {
                    "type": "string",
                    "description": "Source token address on the source chain",
                },
                "dst_token": {
                    "type": "string",
                    "description": "Destination token address on the destination chain",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount in wei (smallest unit)",
                },
            },
            "required": ["src_chain", "dst_chain", "src_token", "dst_token", "amount"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        src_chain: str = "",
        dst_chain: str = "",
        src_token: str = "",
        dst_token: str = "",
        amount: str = "",
        **kwargs,
    ) -> ToolResult:
        if not src_chain or not dst_chain:
            return ToolResult(success=False, error="'src_chain' and 'dst_chain' are required")
        if not src_token or not dst_token or not amount:
            return ToolResult(success=False, error="'src_token', 'dst_token', and 'amount' are required")

        try:
            src_chain_id = resolve_chain(src_chain)
            dst_chain_id = resolve_chain(dst_chain)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))

        if src_chain_id == dst_chain_id:
            return ToolResult(
                success=False,
                error=f"Source and destination chains are the same ({src_chain}). Use oneinch_quote for same-chain swaps.",
            )

        try:
            client = _get_fusion_client()
            wallet_address = await client.get_address()
            data = await client.get_quote(
                src_chain=src_chain_id,
                dst_chain=dst_chain_id,
                src_token=src_token,
                dst_token=dst_token,
                amount=amount,
                wallet_address=wallet_address,
            )
            return ToolResult(success=True, output=data)
        except RuntimeError:
            # Wallet unavailable — try with zero address for read-only quote
            try:
                client = _get_fusion_client()
                data = await client.get_quote(
                    src_chain=src_chain_id,
                    dst_chain=dst_chain_id,
                    src_token=src_token,
                    dst_token=dst_token,
                    amount=amount,
                    wallet_address="0x0000000000000000000000000000000000000000",
                )
                return ToolResult(success=True, output=data)
            except Exception as e2:
                return ToolResult(success=False, error=str(e2))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CrossChainStatusTool(BaseTool):
    """Check the status of a cross-chain swap order."""

    @property
    def name(self) -> str:
        return "oneinch_cross_chain_status"

    @property
    def description(self) -> str:
        return """Check the status of a cross-chain swap order on 1inch Fusion+.

Parameters:
- order_hash: The order hash returned from oneinch_cross_chain_swap

Returns: order status (pending/executed/expired/refunded), fill details, timestamps"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order_hash": {
                    "type": "string",
                    "description": "The order hash from oneinch_cross_chain_swap",
                },
            },
            "required": ["order_hash"],
        }

    async def execute(
        self, ctx: ToolContext, order_hash: str = "", **kwargs
    ) -> ToolResult:
        if not order_hash:
            return ToolResult(success=False, error="'order_hash' is required")

        try:
            client = _get_fusion_client()
            data = await client.get_order_status(order_hash)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Write Tools ──────────────────────────────────────────────────────────────


class CrossChainSwapTool(BaseTool):
    """Execute a cross-chain swap via 1inch Fusion+."""

    @property
    def name(self) -> str:
        return "oneinch_cross_chain_swap"

    @property
    def description(self) -> str:
        return """Execute a cross-chain token swap via 1inch Fusion+ (intent-based atomic swap).

This is a LONG-RUNNING operation (up to 10 minutes). It is recommended to run this as a background task via sessions_spawn so the user isn't blocked.

Fusion+ swaps are gasless — resolvers handle gas on both chains. The user signs an EIP-712 order and resolvers execute the swap.

Flow: Get quote → Generate secrets → Sign order (EIP-712) → Submit → Poll for fills → Reveal secrets → Complete

Parameters:
- src_chain: Source network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- dst_chain: Destination network name (required) — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
- src_token: Source token address on the source chain
- dst_token: Destination token address on the destination chain
- amount: Amount in wei (smallest unit)
- preset: Speed preset — "fast", "medium", or "slow" (default: "medium")

Returns: order hash, final status, amounts"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "src_chain": {
                    "type": "string",
                    "description": "Source network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis",
                },
                "dst_chain": {
                    "type": "string",
                    "description": "Destination network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis",
                },
                "src_token": {
                    "type": "string",
                    "description": "Source token address on the source chain",
                },
                "dst_token": {
                    "type": "string",
                    "description": "Destination token address on the destination chain",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount in wei (smallest unit)",
                },
                "preset": {
                    "type": "string",
                    "description": "Speed preset: fast, medium, or slow (default: medium)",
                },
            },
            "required": ["src_chain", "dst_chain", "src_token", "dst_token", "amount"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        src_chain: str = "",
        dst_chain: str = "",
        src_token: str = "",
        dst_token: str = "",
        amount: str = "",
        preset: str = "medium",
        **kwargs,
    ) -> ToolResult:
        if not src_chain or not dst_chain:
            return ToolResult(success=False, error="'src_chain' and 'dst_chain' are required")
        if not src_token or not dst_token or not amount:
            return ToolResult(success=False, error="'src_token', 'dst_token', and 'amount' are required")

        # Validate token addresses are proper Ethereum addresses (0x + 40 hex chars)
        import re
        eth_addr_re = re.compile(r"^0x[0-9a-fA-F]{40}$")
        if not eth_addr_re.match(src_token):
            return ToolResult(
                success=False,
                error=f"Invalid src_token address '{src_token}'. Must be a 42-character hex address (0x + 40 hex chars).",
            )
        if not eth_addr_re.match(dst_token):
            return ToolResult(
                success=False,
                error=f"Invalid dst_token address '{dst_token}'. Must be a 42-character hex address (0x + 40 hex chars).",
            )

        try:
            src_chain_id = resolve_chain(src_chain)
            dst_chain_id = resolve_chain(dst_chain)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))

        if src_chain_id == dst_chain_id:
            return ToolResult(
                success=False,
                error=f"Source and destination chains are the same ({src_chain}). Use oneinch_swap for same-chain swaps.",
            )

        if preset not in ("fast", "medium", "slow"):
            return ToolResult(success=False, error=f"Invalid preset '{preset}'. Use: fast, medium, slow")

        try:
            from tools.wallet import wallet_sign_transaction, wallet_sign_typed_data
            client = _get_fusion_client()
            wallet_address = (await client.get_address()).lower()
            src_token = src_token.lower()
            dst_token = dst_token.lower()

            # 1. Get quote
            quote = await client.get_quote(
                src_chain=src_chain_id,
                dst_chain=dst_chain_id,
                src_token=src_token,
                dst_token=dst_token,
                amount=amount,
                wallet_address=wallet_address,
            )

            # 2. Determine secrets count from preset
            presets = quote.get("presets", {})
            preset_data = presets.get(preset, presets.get("medium", {}))
            secrets_count = preset_data.get("secretsCount", 1)

            # 3. Generate secrets
            secrets = generate_secrets(secrets_count)
            secret_hashes = [hash_secret(s) for s in secrets]

            # 4. Build order via API (server builds extension, salt, makerTraits, typed data)
            quote_id = quote.get("quoteId", "")
            if not quote_id:
                return ToolResult(
                    success=False,
                    error="Quote response missing quoteId — ensure enableEstimate=true",
                )
            build_result = await client.build_order(
                quote_id=quote_id,
                secret_hashes=secret_hashes,
                preset=preset,
            )

            logger.info(f"Build API response keys: {list(build_result.keys())}")
            logger.info(f"Build API response: {json.dumps(build_result, indent=2, default=str)[:2000]}")

            # Extract fields from build response
            extension = build_result.get("extension", "")
            order_hash = build_result.get("orderHash", "")
            typed_data = build_result.get("typedData", {})
            build_tx = build_result.get("transaction")
            build_signature = build_result.get("signature")

            if not typed_data:
                return ToolResult(
                    success=False,
                    error="Build API returned no typedData — cannot sign order",
                    output={"build_result_keys": list(build_result.keys()), "build_result": build_result},
                )

            logger.info(f"Build API returned orderHash={order_hash}, extension length={len(extension)}")

            # 5. Get signature — native ETH vs ERC-20 flow
            if build_tx:
                # ── Native ETH flow: execute deposit tx, use pre-computed signature ──
                tx_to = build_tx.get("to", "")
                tx_data = build_tx.get("data", "")
                tx_value = str(build_tx.get("value", "0"))

                if not tx_to:
                    return ToolResult(success=False, error="Build API returned transaction with no 'to' address")

                logger.info(f"Native ETH swap: executing deposit tx to {tx_to} (value={tx_value})")
                tx_result = wallet_sign_transaction({
                    "to": tx_to,
                    "value": tx_value,
                    "chain_id": src_chain_id,
                    "data": tx_data,
                })
                tx_hash = tx_result.get("tx_hash", tx_result.get("hash", ""))
                logger.info(f"Deposit tx sent: {tx_hash}")

                if not build_signature:
                    return ToolResult(success=False, error="Build API returned transaction but no signature for native ETH order")
                signature = build_signature
                logger.info("Using pre-computed signature from build API (native ETH swap)")
            else:
                # ── ERC-20 flow: sign typedData with platform wallet ──
                sig_result = wallet_sign_typed_data(
                    domain=typed_data.get("domain", {}),
                    types=typed_data.get("types", {}),
                    primary_type=typed_data.get("primaryType", ""),
                    message=typed_data.get("message", {}),
                )
                signature = sig_result.get("signature", "")

                if not signature:
                    return ToolResult(
                        success=False,
                        error=f"Wallet returned no signature. Response: {json.dumps(sig_result)}",
                    )

            # 6. Normalize signature v-value (some wallets return v=0/1, relayer expects v=27/28)
            sig_hex = signature.replace("0x", "")
            if len(sig_hex) == 130:  # 65 bytes = 130 hex chars
                v = int(sig_hex[-2:], 16)
                if v < 27:
                    signature = "0x" + sig_hex[:-2] + format(v + 27, "02x")
                    logger.info(f"Normalized signature v: {v} -> {v + 27}")
            else:
                logger.warning(f"Unexpected signature length: {len(sig_hex)} hex chars (expected 130)")

            # 7. Submit order
            order_message = typed_data.get("message", {})
            submit_payload = {
                "order": order_message,
                "signature": signature,
                "quoteId": quote_id,
                "extension": extension,
                "srcChainId": src_chain_id,
            }
            if secrets_count > 1:
                submit_payload["secretHashes"] = secret_hashes

            logger.info(f"Submit payload keys: {list(submit_payload.keys())}")

            try:
                submitted_hash = await client.place_order(submit_payload)
                order_hash = submitted_hash or order_hash
            except Exception as submit_err:
                error_msg = str(submit_err)
                logger.error(f"Order submit failed: {error_msg}")
                return ToolResult(
                    success=False,
                    error=f"Order submit failed: {error_msg}",
                    output={
                        "order_hash": order_hash,
                        "quoteId": quote_id,
                        "secretsCount": secrets_count,
                    },
                )

            if not order_hash:
                return ToolResult(
                    success=False,
                    error="Order submission returned no order hash",
                )

            # 8. Poll for fills and reveal secrets
            revealed = set()
            start = time.time()
            backoff = POLL_INTERVAL

            while time.time() - start < MAX_POLL_TIME:
                # Check for fills ready to accept (skip once all secrets revealed)
                if len(revealed) < secrets_count:
                    try:
                        fills = await client.get_ready_to_accept_fills(order_hash)
                        fill_list = fills.get("fills", [])

                        for fill in fill_list:
                            idx = fill.get("idx", 0)
                            if idx not in revealed and idx < len(secrets):
                                secret_hex = "0x" + secrets[idx].hex()
                                await client.submit_secret(order_hash, secret_hex)
                                revealed.add(idx)
                                logger.info(f"Revealed secret {idx} for order {order_hash}")
                    except Exception as e:
                        logger.debug(f"Fill check error (may be normal): {e}")

                # Check order status (protected — order is already submitted)
                try:
                    status = await client.get_order_status(order_hash)
                    order_status = status.get("status", "").lower()
                    backoff = POLL_INTERVAL  # reset backoff on success

                    if order_status in ("executed", "expired", "refunded", "cancelled", "refunding"):
                        return ToolResult(
                            success=order_status == "executed",
                            output={
                                "order_hash": order_hash,
                                "status": order_status,
                                "src_chain": src_chain,
                                "dst_chain": dst_chain,
                                "src_token": src_token,
                                "dst_token": dst_token,
                                "src_amount": amount,
                                "dst_amount": status.get("dstAmount", status.get("takingAmount", "")),
                                "fills": status.get("fills", []),
                                "secrets_revealed": len(revealed),
                            },
                            error=f"Order {order_status}" if order_status != "executed" else None,
                        )
                except Exception as status_err:
                    err_str = str(status_err)
                    if "429" in err_str or "rate limit" in err_str.lower():
                        backoff = min(backoff * 2, 60)
                        logger.warning(f"Rate limited on status check, backing off to {backoff}s")
                    else:
                        logger.warning(f"Status check error (order already submitted): {status_err}")

                await asyncio.sleep(backoff)

            # Timeout
            return ToolResult(
                success=False,
                output={
                    "order_hash": order_hash,
                    "status": "timeout",
                    "secrets_revealed": len(revealed),
                    "message": f"Order did not complete within {MAX_POLL_TIME}s. Check status with oneinch_cross_chain_status.",
                },
                error=f"Order timed out after {MAX_POLL_TIME}s. Use oneinch_cross_chain_status to check later.",
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Cross-chain swap failed: {error_msg}", exc_info=True)
            if "policy" in error_msg.lower():
                return ToolResult(
                    success=False,
                    error=f"Policy violation: {error_msg}. "
                          f"The wallet policy is blocking this operation. "
                          f"Inform the user and propose the permissive default policy "
                          f"(DENY exportPrivateKey + ALLOW *) using wallet_propose_policy, "
                          f"or read the wallet-policy skill for specific templates."
                )
            return ToolResult(success=False, error=error_msg)
