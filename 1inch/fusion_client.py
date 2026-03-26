"""
1inch Fusion+ Cross-Chain Swap Client — async HTTP client for intent-based atomic cross-chain swaps.

Uses the Fusion+ API (api.1inch.com/fusion-plus) for:
- Quote: Get pricing for cross-chain token swaps
- Order Submit: Submit signed cross-chain swap orders
- Order Status: Check order execution status
- Fill Management: Reveal secrets as resolvers fill orders

Supported networks: Same as classic swap (Ethereum, Arbitrum, Base, Optimism, Polygon, BSC, Avalanche, Gnosis).

Environment Variables:
- ONEINCH_API_KEY: 1inch Developer Portal API key (required)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp
from eth_utils import keccak

from core.http_client import get_aiohttp_proxy_kwargs

logger = logging.getLogger(__name__)

FUSION_API_BASE = "https://api.1inch.com/fusion-plus"


# ── Secret Management ─────────────────────────────────────────────────────────


def generate_secrets(count: int) -> List[bytes]:
    """Generate random 32-byte secrets for Fusion+ order fills."""
    count = min(count, 100)  # Cap to prevent excessive generation
    return [os.urandom(32) for _ in range(count)]


def hash_secret(secret: bytes) -> str:
    """Compute keccak256 hash of a secret. Returns 0x-prefixed hex string."""
    return "0x" + keccak(secret).hex()


# ── Fusion+ API Client ───────────────────────────────────────────────────────


class FusionPlusClient:
    """
    Async client for 1inch Fusion+ cross-chain swap API.

    Handles quoting, order submission, status polling, and secret reveal.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ONEINCH_API_KEY", "")
        if not self.api_key:
            logger.warning("ONEINCH_API_KEY not set — Fusion+ API calls will fail")

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET request to Fusion+ API with Bearer auth."""
        url = f"{FUSION_API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        proxy_kw = get_aiohttp_proxy_kwargs(url)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
                **proxy_kw,
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Exception(f"Fusion+ API {resp.status}: {body}")
                return await resp.json()

    async def _post(
        self,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """POST request to Fusion+ API with Bearer auth."""
        url = f"{FUSION_API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        proxy_kw = get_aiohttp_proxy_kwargs(url)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
                **proxy_kw,
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Exception(f"Fusion+ API {resp.status}: {body}")
                # Some endpoints return empty body on success
                text = await resp.text()
                if not text:
                    return {}
                return await resp.json(content_type=None)

    # ── Address helper ───────────────────────────────────────────────────

    _cached_address: Optional[str] = None

    async def get_address(self) -> str:
        """Get the agent's EVM address from wallet service (cached)."""
        if self._cached_address:
            return self._cached_address

        from tools.wallet import _wallet_request, _is_fly_machine

        if not _is_fly_machine():
            raise RuntimeError("Not running on Fly — wallet unavailable")

        data = await _wallet_request("GET", "/agent/wallet")
        wallets = data if isinstance(data, list) else data.get("wallets", [])
        for w in wallets:
            if w.get("chain_type") == "ethereum":
                self._cached_address = w["wallet_address"]
                return self._cached_address

        raise RuntimeError("No ethereum wallet found")

    # ── Build Order ────────────────────────────────────────────────────────

    async def build_order(
        self,
        quote_id: str,
        secret_hashes: list,
        preset: str = "medium",
        receiver: str = "",
    ) -> dict:
        """
        Build order via API — returns extension, orderHash, typedData.

        The build endpoint constructs the complete order server-side,
        including extension encoding, salt, and makerTraits. The quote
        is referenced by quoteId (returned from get_quote with enableEstimate=true).

        Args:
            quote_id: The quoteId from get_quote() response
            secret_hashes: List of 0x-prefixed keccak256 secret hashes
            preset: Speed preset — "fast", "medium", "slow" (default: "medium")
            receiver: Custom receiver address (optional, defaults to maker)

        Returns: { "extension": "0x...", "orderHash": "0x...", "typedData": { ... } }
        """
        body: Dict[str, Any] = {
            "secretsHashList": secret_hashes,
            "preset": preset,
        }
        if receiver:
            body["receiver"] = receiver
        return await self._post(
            "/quoter/v1.1/quote/build/evm",
            json_body=body,
            params={"quoteId": quote_id},
        )

    # ── Quote ─────────────────────────────────────────────────────────────

    async def get_quote(
        self,
        src_chain: int,
        dst_chain: int,
        src_token: str,
        dst_token: str,
        amount: str,
        wallet_address: str,
    ) -> dict:
        """
        Get a cross-chain swap quote.

        Args:
            src_chain: Source chain ID
            dst_chain: Destination chain ID
            src_token: Source token address
            dst_token: Destination token address
            amount: Amount in wei (smallest unit)
            wallet_address: Wallet address for the quote

        Returns: Quote with estimated output, presets, fees
        """
        params = {
            "srcChain": str(src_chain),
            "dstChain": str(dst_chain),
            "srcTokenAddress": src_token,
            "dstTokenAddress": dst_token,
            "amount": amount,
            "walletAddress": wallet_address,
            "enableEstimate": "true",
        }
        return await self._get("/quoter/v1.1/quote/receive", params)

    # ── Order Management ─────────────────────────────────────────────────

    async def place_order(self, order_data: dict) -> str:
        """
        Submit a signed cross-chain swap order.

        Args:
            order_data: Complete order payload (EvmSignedOrderInput)

        Returns: Order hash
        """
        result = await self._post("/relayer/v1.1/submit", order_data)
        return result.get("orderHash", result.get("order_hash", ""))

    async def get_order_status(self, order_hash: str) -> dict:
        """
        Get the current status of a cross-chain order.

        Args:
            order_hash: The order hash returned from place_order

        Returns: Status dict with status, fills, timestamps
        """
        return await self._get(f"/orders/v1.1/order/status/{order_hash}")

    async def get_ready_to_accept_fills(self, order_hash: str) -> dict:
        """
        Check which fills are ready to accept (secrets can be revealed).

        Args:
            order_hash: The order hash

        Returns: Dict with fills ready for secret reveal
        """
        return await self._get(f"/orders/v1.1/order/ready-to-accept-secret-fills/{order_hash}")

    async def submit_secret(self, order_hash: str, secret: str) -> None:
        """
        Reveal a secret for a fill.

        Args:
            order_hash: The order hash
            secret: The secret to reveal (0x-prefixed hex)
        """
        await self._post("/relayer/v1.1/submit/secret", {
            "orderHash": order_hash,
            "secret": secret,
        })
