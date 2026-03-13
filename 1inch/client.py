"""
1inch Swap API Client — async HTTP client for 1inch DEX aggregator.

Supports multiple EVM networks: Ethereum, Arbitrum, Base, Optimism, Polygon, BSC, Avalanche, Gnosis.

Uses the 1inch Swap API v6.1 for:
- Quote: price estimate without tx data
- Swap: full transaction data for execution
- Approve: ERC-20 token approval for 1inch router
- Tokens: supported token list on the selected network

Environment Variables:
- ONEINCH_API_KEY: 1inch Developer Portal API key (required)
- WALLET_SERVICE_URL: Privy wallet service URL (for address lookup)
"""

import logging
import os
from typing import Any, Dict, Optional

import aiohttp

from core.http_client import get_aiohttp_proxy_kwargs

logger = logging.getLogger(__name__)

SUPPORTED_CHAINS = {
    "ethereum": 1,
    "arbitrum": 42161,
    "base": 8453,
    "optimism": 10,
    "polygon": 137,
    "bsc": 56,
    "avalanche": 43114,
    "gnosis": 100,
}

NATIVE_TOKEN = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
ROUTER_ADDRESS = "0x111111125421cA6dc452d289314280a0f8842A65"  # 1inch v6 router (EIP-55 checksummed)


def resolve_chain(chain: str) -> int:
    """Map a chain name to its chain ID. Raises ValueError for unknown chains."""
    chain_lower = chain.lower().strip()
    if chain_lower not in SUPPORTED_CHAINS:
        supported = ", ".join(sorted(SUPPORTED_CHAINS.keys()))
        raise ValueError(f"Unknown chain '{chain}'. Supported: {supported}")
    return SUPPORTED_CHAINS[chain_lower]


class OneInchClient:
    """
    Async 1inch client for EVM networks.

    All methods call the 1inch Swap API v6.1 with Bearer token auth.
    """

    def __init__(self, chain_id: int, api_key: Optional[str] = None):
        self.chain_id = chain_id
        self._api_base = f"https://api.1inch.com/swap/v6.1/{chain_id}"
        self.api_key = api_key or os.environ.get("ONEINCH_API_KEY", "")
        if not self.api_key:
            logger.warning("ONEINCH_API_KEY not set — 1inch API calls will fail")

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET request to 1inch API with Bearer auth."""
        url = f"{self._api_base}{path}"
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
                timeout=aiohttp.ClientTimeout(total=15),
                **proxy_kw,
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Exception(f"1inch API {resp.status}: {body}")
                return await resp.json()

    # ── Address helper ───────────────────────────────────────────────────

    _cached_address: Optional[str] = None

    async def _get_address(self) -> str:
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

    # ── Quote & Swap ─────────────────────────────────────────────────────

    async def get_quote(self, src: str, dst: str, amount: str) -> dict:
        """
        Get a swap quote (price estimate, no tx data).

        Args:
            src: Source token address
            dst: Destination token address
            amount: Amount in wei (smallest unit)

        Returns: dict with dstAmount, gas, protocols (route info)
        """
        params = {"src": src, "dst": dst, "amount": amount}
        return await self._get("/quote", params)

    async def get_swap(
        self,
        src: str,
        dst: str,
        amount: str,
        from_addr: str,
        slippage: float = 1.0,
    ) -> dict:
        """
        Get swap transaction data for execution.

        Args:
            src: Source token address
            dst: Destination token address
            amount: Amount in wei
            from_addr: Wallet address executing the swap
            slippage: Slippage tolerance in percent (default 1.0%)

        Returns: dict with tx {to, data, value, gas} and dstAmount
        """
        params = {
            "src": src,
            "dst": dst,
            "amount": amount,
            "from": from_addr,
            "slippage": str(slippage),
        }
        return await self._get("/swap", params)

    # ── Token Approval ───────────────────────────────────────────────────

    async def get_approve_spender(self) -> dict:
        """Get the 1inch router address (spender for approvals)."""
        return await self._get("/approve/spender")

    async def get_approve_transaction(
        self, token_address: str, amount: Optional[str] = None
    ) -> dict:
        """
        Get approval tx data for a token.

        Args:
            token_address: ERC-20 token to approve
            amount: Amount to approve in wei (omit for unlimited)

        Returns: dict with {to, data, value} for the approval tx
        """
        params = {"tokenAddress": token_address}
        if amount is not None:
            params["amount"] = amount
        return await self._get("/approve/transaction", params)

    async def get_allowance(self, token_address: str, wallet_address: str) -> dict:
        """
        Check current allowance for the 1inch router.

        Args:
            token_address: ERC-20 token address
            wallet_address: Wallet to check

        Returns: dict with allowance amount
        """
        params = {
            "tokenAddress": token_address,
            "walletAddress": wallet_address,
        }
        return await self._get("/approve/allowance", params)

    # ── Token List ───────────────────────────────────────────────────────

    async def get_tokens(self) -> dict:
        """
        Get all supported tokens on the configured network.

        Returns: dict mapping address → {symbol, name, decimals, address, ...}
        """
        return await self._get("/tokens")
