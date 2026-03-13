"""
Orderly One API Client — async HTTP client for DEX management via Orderly One.

Public endpoints: unauthenticated GET requests (networks, leaderboard, stats).
Private endpoints: JWT-authenticated requests for DEX CRUD, theming, graduation.

Base URL: https://api.dex.orderly.network
"""

import json
import logging
import os
from typing import Any, Dict, Optional

import aiohttp

from . import auth

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.dex.orderly.network"


class OrderlyOneClient:
    """
    Async Orderly One client for DEX management.

    - Public methods: GET requests (no auth)
    - Private methods: JWT-authenticated requests
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or os.environ.get(
            "ORDERLY_ONE_API_URL", DEFAULT_API_URL
        )

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _public_get(self, path: str, params: Optional[dict] = None) -> Any:
        """Unauthenticated GET request."""
        url = f"{self.api_url}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Exception(f"Orderly One API {resp.status}: {body}")
                data = await resp.json()
                return data.get("data", data)

    async def _private_request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
        retry_on_401: bool = True,
    ) -> Any:
        """JWT-authenticated request."""
        token = await auth.ensure_jwt()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"{self.api_url}{path}"
        async with aiohttp.ClientSession() as session:
            kwargs = {
                "headers": headers,
                "timeout": aiohttp.ClientTimeout(total=30),
            }
            if method.upper() == "GET":
                kwargs["params"] = params
            elif body is not None:
                kwargs["data"] = json.dumps(body)

            async with session.request(method.upper(), url, **kwargs) as resp:
                if resp.status == 401 and retry_on_401:
                    auth.invalidate_jwt()
                    return await self._private_request(
                        method, path, params, body, retry_on_401=False
                    )
                if resp.status >= 400:
                    resp_body = await resp.text()
                    logger.error(
                        f"Orderly One API error: {method.upper()} {path} → "
                        f"{resp.status}: {resp_body}"
                    )
                    raise Exception(f"Orderly One API {resp.status}: {resp_body}")
                data = await resp.json()
                return data.get("data", data)

    # ── Public Methods (no auth) ─────────────────────────────────────────

    async def get_networks(self) -> Any:
        """Get available blockchain networks for DEX deployment."""
        return await self._public_get("/api/dex/networks")

    async def get_leaderboard(
        self,
        broker_id: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Any:
        """Get DEX leaderboard rankings."""
        params = {"page": page, "size": size}
        if broker_id:
            params["broker_id"] = broker_id
        return await self._public_get("/api/leaderboard", params=params)

    async def get_broker_stats(self, broker_id: str) -> Any:
        """Get detailed stats for a specific broker/DEX."""
        return await self._public_get(f"/api/leaderboard/broker/{broker_id}")

    async def get_platform_stats(self) -> Any:
        """Get platform-wide statistics."""
        return await self._public_get("/api/stats")

    # ── DEX Management (JWT auth) ────────────────────────────────────────

    async def get_my_dex(self) -> Any:
        """Get current user's DEX configuration."""
        return await self._private_request("GET", "/api/dex")

    async def get_dex(self, dex_id: str) -> Any:
        """Get a specific DEX by ID."""
        return await self._private_request("GET", f"/api/dex/{dex_id}")

    async def create_dex(
        self,
        broker_name: str,
        chain_ids: list,
        **kwargs,
    ) -> Any:
        """Create a new DEX."""
        body = {
            "broker_name": broker_name,
            "chain_ids": chain_ids,
            **kwargs,
        }
        return await self._private_request("POST", "/api/dex", body=body)

    async def update_dex(self, dex_id: str, **kwargs) -> Any:
        """Update DEX configuration."""
        return await self._private_request("PUT", f"/api/dex/{dex_id}", body=kwargs)

    async def delete_dex(self, dex_id: str) -> Any:
        """Delete a DEX."""
        return await self._private_request("DELETE", f"/api/dex/{dex_id}")

    # ── Branding & Social ────────────────────────────────────────────────

    async def update_social_card(self, **kwargs) -> Any:
        """Update DEX social card / branding info."""
        return await self._private_request("PUT", "/api/dex/social-card", body=kwargs)

    async def set_custom_domain(self, dex_id: str, domain: str) -> Any:
        """Set a custom domain for a DEX."""
        return await self._private_request(
            "POST", f"/api/dex/{dex_id}/custom-domain", body={"domain": domain}
        )

    async def remove_custom_domain(self, dex_id: str) -> Any:
        """Remove custom domain from a DEX."""
        return await self._private_request(
            "DELETE", f"/api/dex/{dex_id}/custom-domain"
        )

    async def set_board_visibility(self, dex_id: str, show: bool) -> Any:
        """Toggle leaderboard visibility for a DEX."""
        return await self._private_request(
            "POST", f"/api/dex/{dex_id}/board-visibility", body={"show": show}
        )

    # ── Deployment & Upgrades ────────────────────────────────────────────

    async def get_workflow_status(self, dex_id: str) -> Any:
        """Get current deployment workflow status."""
        return await self._private_request("GET", f"/api/dex/{dex_id}/workflow-status")

    async def get_workflow_run(self, dex_id: str, run_id: str) -> Any:
        """Get details of a specific workflow run."""
        return await self._private_request(
            "GET", f"/api/dex/{dex_id}/workflow-runs/{run_id}"
        )

    async def get_upgrade_status(self, dex_id: str) -> Any:
        """Check if a DEX upgrade is available."""
        return await self._private_request(
            "GET", f"/api/dex/{dex_id}/upgrade-status"
        )

    async def upgrade_dex(self, dex_id: str) -> Any:
        """Trigger a DEX upgrade to the latest version."""
        return await self._private_request("POST", f"/api/dex/{dex_id}/upgrade")

    async def get_rate_limit_status(self) -> Any:
        """Get current API rate limit status."""
        return await self._private_request("GET", "/api/dex/rate-limit-status")

    # ── Theme ────────────────────────────────────────────────────────────

    async def modify_theme(self, prompt: str) -> Any:
        """Generate a theme using AI from a text prompt."""
        return await self._private_request(
            "POST", "/api/theme/modify", body={"prompt": prompt}
        )

    async def fine_tune_theme(self, element: str, style: str) -> Any:
        """Fine-tune a specific theme element."""
        return await self._private_request(
            "POST", "/api/theme/fine-tune", body={"element": element, "style": style}
        )

    # ── Graduation ───────────────────────────────────────────────────────

    async def get_graduation_status(self) -> Any:
        """Get graduation eligibility status."""
        return await self._private_request("GET", "/api/graduation/status")

    async def get_graduation_fees(self) -> Any:
        """Get graduation fee options."""
        return await self._private_request("GET", "/api/graduation/fee-options")

    async def verify_graduation_tx(self, tx_hash: str, chain_id: int) -> Any:
        """Verify a graduation payment transaction."""
        return await self._private_request(
            "POST",
            "/api/graduation/verify-tx",
            body={"tx_hash": tx_hash, "chain_id": chain_id},
        )

    async def finalize_graduation(self, admin_wallet: str) -> Any:
        """Finalize graduation with admin wallet address."""
        return await self._private_request(
            "POST",
            "/api/graduation/finalize-admin-wallet",
            body={"admin_wallet": admin_wallet},
        )


# ── Module-level singleton ───────────────────────────────────────────────────

_client: Optional[OrderlyOneClient] = None


def _get_client() -> OrderlyOneClient:
    global _client
    if _client is None:
        _client = OrderlyOneClient()
    return _client
