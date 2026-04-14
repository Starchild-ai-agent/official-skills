"""
1inch Fusion+ Cross-Chain Swap Tools — BaseTool subclasses for cross-chain swaps.

Read-only tools (2): oneinch_cross_chain_quote, oneinch_cross_chain_status
Write tools (1): oneinch_cross_chain_swap (long-running — recommend background task)

Architecture note:
  All HTTP calls use proxied_get/proxied_post (sc-proxy sync path).
  The previous aiohttp async path caused pending+empty tx_hash bugs and has been removed.
  Verified: ETH→ARB 2 USDC swap, ~76s settlement (2025).
"""

import json
import logging
import os
import re
import time

from core.http_client import proxied_get, proxied_post
from core.tool import BaseTool, ToolContext, ToolResult
from .client import SUPPORTED_CHAINS, resolve_chain

logger = logging.getLogger(__name__)

SC_CALLER_ID = "skill:1inch"
FUSION_BASE = "https://api.1inch.com/fusion-plus"

MAX_POLL_TIME = 300   # 5 minutes
POLL_INTERVAL = 15    # seconds

# Reverse lookup: chain_id → chain_name
CHAIN_ID_TO_NAME = {v: k for k, v in SUPPORTED_CHAINS.items()}


# ── Internal sync helpers ─────────────────────────────────────────────────────

def _fusion_get(path: str, params: dict = None) -> dict:
    """Fusion+ API GET via sc-proxy (sync)."""
    url = f"{FUSION_BASE}{path}"
    resp = proxied_get(url, params=params or {}, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        raise RuntimeError(f"Fusion+ GET {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _fusion_post(path: str, body: dict, params: dict = None) -> dict:
    """Fusion+ API POST via sc-proxy (sync)."""
    url = f"{FUSION_BASE}{path}"
    resp = proxied_post(url, json=body, params=params or {}, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        raise RuntimeError(f"Fusion+ POST {resp.status_code}: {resp.text[:300]}")
    text = resp.text.strip()
    return resp.json() if text else {}


def _generate_secrets(count: int) -> list:
    return [os.urandom(32) for _ in range(count)]


def _hash_secret(secret: bytes) -> str:
    try:
        from eth_utils import keccak
        return "0x" + keccak(secret).hex()
    except ImportError:
        import hashlib
        return "0x" + hashlib.sha3_256(secret).hexdigest()


def _normalize_v(signature: str) -> str:
    sig_hex = signature.replace("0x", "")
    if len(sig_hex) == 130:
        v = int(sig_hex[-2:], 16)
        if v < 27:
            signature = "0x" + sig_hex[:-2] + format(v + 27, "02x")
            logger.info(f"Normalized signature v: {v} -> {v + 27}")
    return signature


def _get_wallet_address() -> str:
    try:
        from tools.wallet import wallet_info
        info = wallet_info()
        for w in (info if isinstance(info, list) else info.get("wallets", [])):
            if w.get("chain_type") == "ethereum":
                return w["wallet_address"]
    except Exception:
        pass
    return ""


# ── Read-Only Tools ──────────────────────────────────────────────────────────


class CrossChainQuoteTool(BaseTool):
    """Get a cross-chain swap quote via 1inch Fusion+."""

    @property
    def name(self) -> str:
        return "oneinch_cross_chain_quote"

    @property
    def description(self) -> str:
        return """Get a cross-chain swap price quote via 1inch Fusion+.

Returns the estimated output amount for swapping tokens across different chains
(e.g., ETH on Ethereum to USDC on Arbitrum). No transaction is executed.

Fusion+ uses intent-based atomic swaps — resolvers handle gas on both chains,
so the user doesn't need gas on the destination chain.

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
                "src_chain": {"type": "string", "description": "Source network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis"},
                "dst_chain": {"type": "string", "description": "Destination network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis"},
                "src_token": {"type": "string", "description": "Source token address on the source chain"},
                "dst_token": {"type": "string", "description": "Destination token address on the destination chain"},
                "amount": {"type": "string", "description": "Amount in wei (smallest unit)"},
            },
            "required": ["src_chain", "dst_chain", "src_token", "dst_token", "amount"],
        }

    async def execute(
        self, ctx: ToolContext,
        src_chain: str = "", dst_chain: str = "",
        src_token: str = "", dst_token: str = "", amount: str = "",
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

        wallet = _get_wallet_address() or "0x0000000000000000000000000000000000000000"
        try:
            data = _fusion_get("/quoter/v1.1/quote/receive", {
                "srcChain": str(src_chain_id),
                "dstChain": str(dst_chain_id),
                "srcTokenAddress": src_token,
                "dstTokenAddress": dst_token,
                "amount": amount,
                "walletAddress": wallet,
                "enableEstimate": "true",
            })
            return ToolResult(success=True, output=data)
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
                "order_hash": {"type": "string", "description": "The order hash from oneinch_cross_chain_swap"},
            },
            "required": ["order_hash"],
        }

    async def execute(self, ctx: ToolContext, order_hash: str = "", **kwargs) -> ToolResult:
        if not order_hash:
            return ToolResult(success=False, error="'order_hash' is required")
        try:
            data = _fusion_get(f"/orders/v1.1/order/status/{order_hash}")
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

This is a LONG-RUNNING operation (up to 5 minutes). Recommended to run as a background task
via sessions_spawn so the user isn't blocked.

Fusion+ swaps are gasless — resolvers handle gas on both chains. The user signs an EIP-712
order and resolvers execute the swap atomically.

Flow: Get quote → Generate secrets → Build order → Sign EIP-712 → Submit → Poll for fills → Reveal secrets → Complete

All HTTP calls use sc-proxy sync path (verified ETH→ARB 2 USDC, ~76s, 2025).

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
                "src_chain": {"type": "string", "description": "Source network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis"},
                "dst_chain": {"type": "string", "description": "Destination network: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis"},
                "src_token": {"type": "string", "description": "Source token address on the source chain"},
                "dst_token": {"type": "string", "description": "Destination token address on the destination chain"},
                "amount": {"type": "string", "description": "Amount in wei (smallest unit)"},
                "preset": {"type": "string", "description": "Speed preset: fast, medium, or slow (default: medium)"},
            },
            "required": ["src_chain", "dst_chain", "src_token", "dst_token", "amount"],
        }

    async def execute(
        self, ctx: ToolContext,
        src_chain: str = "", dst_chain: str = "",
        src_token: str = "", dst_token: str = "",
        amount: str = "", preset: str = "medium",
        **kwargs,
    ) -> ToolResult:
        if not src_chain or not dst_chain:
            return ToolResult(success=False, error="'src_chain' and 'dst_chain' are required")
        if not src_token or not dst_token or not amount:
            return ToolResult(success=False, error="'src_token', 'dst_token', and 'amount' are required")

        eth_addr_re = re.compile(r"^0x[0-9a-fA-F]{40}$")
        if not eth_addr_re.match(src_token):
            return ToolResult(success=False, error=f"Invalid src_token '{src_token}'. Must be 0x + 40 hex chars.")
        if not eth_addr_re.match(dst_token):
            return ToolResult(success=False, error=f"Invalid dst_token '{dst_token}'. Must be 0x + 40 hex chars.")

        try:
            src_chain_id = resolve_chain(src_chain)
            dst_chain_id = resolve_chain(dst_chain)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))

        if src_chain_id == dst_chain_id:
            return ToolResult(success=False, error=f"Same chain ({src_chain}). Use oneinch_swap for same-chain swaps.")
        if preset not in ("fast", "medium", "slow"):
            return ToolResult(success=False, error=f"Invalid preset '{preset}'. Use: fast, medium, slow")

        wallet_address = _get_wallet_address()
        if not wallet_address:
            return ToolResult(success=False, error="No ethereum wallet configured")

        src_token = src_token.lower()
        dst_token = dst_token.lower()

        try:
            # 1. Quote
            quote = _fusion_get("/quoter/v1.1/quote/receive", {
                "srcChain": str(src_chain_id),
                "dstChain": str(dst_chain_id),
                "srcTokenAddress": src_token,
                "dstTokenAddress": dst_token,
                "amount": amount,
                "walletAddress": wallet_address,
                "enableEstimate": "true",
            })
            quote_id = quote.get("quoteId", "")
            if not quote_id:
                return ToolResult(success=False, error="Quote missing quoteId — ensure enableEstimate=true")
            dst_amount_est = quote.get("dstTokenAmount", "")
            preset_info = quote.get("presets", {}).get(preset, quote.get("presets", {}).get("medium", {}))
            secrets_count = preset_info.get("secretsCount", 1)

            # 2. Generate secrets
            secrets = _generate_secrets(secrets_count)
            secret_hashes = [_hash_secret(s) for s in secrets]

            # 3. Build order
            build_result = _fusion_post(
                "/quoter/v1.1/quote/build/evm",
                body={"secretsHashList": secret_hashes, "preset": preset},
                params={"quoteId": quote_id},
            )
            order_hash = build_result.get("orderHash", "")
            typed_data = build_result.get("typedData", {})
            extension = build_result.get("extension", "")
            build_tx = build_result.get("transaction")
            build_signature = build_result.get("signature")

            if not typed_data:
                return ToolResult(success=False, error="Build API returned no typedData", output={"build_keys": list(build_result.keys())})

            # 4. Sign
            if build_tx:
                # Native ETH: execute deposit tx, use pre-computed signature
                from tools.wallet import wallet_sign_transaction
                wallet_sign_transaction({
                    "to": build_tx.get("to", ""),
                    "value": str(build_tx.get("value", "0")),
                    "chain_id": src_chain_id,
                    "data": build_tx.get("data", ""),
                })
                if not build_signature:
                    return ToolResult(success=False, error="Build API returned transaction but no pre-computed signature")
                signature = build_signature
            else:
                # ERC-20: sign EIP-712 typed data
                from tools.wallet import wallet_sign_typed_data
                sig_result = wallet_sign_typed_data(
                    domain=typed_data.get("domain", {}),
                    types=typed_data.get("types", {}),
                    primary_type=typed_data.get("primaryType", ""),
                    message=typed_data.get("message", {}),
                )
                signature = sig_result.get("signature", "")
                if not signature:
                    return ToolResult(success=False, error=f"Wallet returned no signature: {sig_result}")

            signature = _normalize_v(signature)

            # 5. Submit
            submit_payload = {
                "order": typed_data.get("message", {}),
                "signature": signature,
                "quoteId": quote_id,
                "extension": extension,
                "srcChainId": src_chain_id,
            }
            if secrets_count > 1:
                submit_payload["secretHashes"] = secret_hashes

            submit_result = _fusion_post("/relayer/v1.1/submit", submit_payload)
            order_hash = submit_result.get("orderHash", order_hash)

            if not order_hash:
                return ToolResult(success=False, error="Order submission returned no order hash")

            # 6. Poll (max 5 min)
            revealed = set()
            start = time.time()

            while time.time() - start < MAX_POLL_TIME:
                # Reveal secrets if fills ready
                if len(revealed) < secrets_count:
                    try:
                        fills = _fusion_get(f"/orders/v1.1/order/ready-to-accept-secret-fills/{order_hash}")
                        for fill in fills.get("fills", []):
                            idx = fill.get("idx", 0)
                            if idx not in revealed and idx < len(secrets):
                                _fusion_post("/relayer/v1.1/submit/secret", {
                                    "orderHash": order_hash,
                                    "secret": "0x" + secrets[idx].hex(),
                                })
                                revealed.add(idx)
                                logger.info(f"Revealed secret {idx} for order {order_hash}")
                    except Exception as e:
                        logger.debug(f"Fill check (may be normal): {e}")

                # Check status
                try:
                    status = _fusion_get(f"/orders/v1.1/order/status/{order_hash}")
                    order_status = status.get("status", "").lower()
                    if order_status in ("executed", "expired", "refunded", "cancelled"):
                        return ToolResult(
                            success=(order_status == "executed"),
                            output={
                                "status": order_status,
                                "order_hash": order_hash,
                                "src_chain": src_chain, "dst_chain": dst_chain,
                                "src_token": src_token, "dst_token": dst_token,
                                "src_amount": amount,
                                "dst_amount": status.get("dstAmount", status.get("takingAmount", dst_amount_est)),
                                "secrets_revealed": len(revealed),
                                "elapsed_seconds": int(time.time() - start),
                            },
                            error=f"Order {order_status}" if order_status != "executed" else None,
                        )
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "rate limit" in err_str.lower():
                        logger.warning("Rate limited on status check, backing off")
                        time.sleep(30)
                    else:
                        logger.warning(f"Status check error (order already submitted): {e}")

                time.sleep(POLL_INTERVAL)

            # Timeout — order is submitted, just didn't confirm in time
            return ToolResult(
                success=False,
                output={
                    "status": "submitted_polling_timeout",
                    "order_hash": order_hash,
                    "src_chain": src_chain, "dst_chain": dst_chain,
                    "src_amount": amount, "dst_amount_estimate": dst_amount_est,
                    "message": f"Order submitted but did not confirm within {MAX_POLL_TIME}s. "
                               "Use oneinch_cross_chain_status(order_hash) to check later.",
                },
                error=f"Order timed out after {MAX_POLL_TIME}s. Use oneinch_cross_chain_status to check later.",
            )

        except Exception as e:
            err = str(e)
            logger.error(f"Cross-chain swap failed: {err}", exc_info=True)
            if "policy" in err.lower():
                return ToolResult(
                    success=False,
                    error=f"Policy violation: {err}. Use wallet_propose_policy to allow this operation.",
                )
            return ToolResult(success=False, error=err)
