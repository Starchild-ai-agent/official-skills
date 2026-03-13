"""
Orderly One DEX Builder Tools — BaseTool subclasses for agent use.

Public tools (3):  orderly_one_networks, orderly_one_leaderboard, orderly_one_stats
DEX CRUD (4):      orderly_one_dex_get, orderly_one_dex_create, orderly_one_dex_update,
                   orderly_one_dex_delete
Branding (3):      orderly_one_social_card, orderly_one_domain, orderly_one_visibility
Operations (3):    orderly_one_deploy_status, orderly_one_theme, orderly_one_graduation
"""

import logging

from core.tool import BaseTool, ToolContext, ToolResult
from .client import _get_client

logger = logging.getLogger(__name__)


# ── Public Tools (3) — No Auth ───────────────────────────────────────────────


class OrderlyOneNetworksTool(BaseTool):
    """List available blockchain networks for DEX deployment."""

    @property
    def name(self) -> str:
        return "orderly_one_networks"

    @property
    def description(self) -> str:
        return """List available blockchain networks for deploying a DEX on Orderly One.

Use this to check which chains are supported before creating a DEX.

Returns: array of supported networks with chain IDs and names"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            data = await client.get_networks()
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOneLeaderboardTool(BaseTool):
    """Get DEX rankings and broker stats."""

    @property
    def name(self) -> str:
        return "orderly_one_leaderboard"

    @property
    def description(self) -> str:
        return """Get the Orderly One DEX leaderboard — rankings of DEXes by volume and activity.

Parameters:
- broker_id: (optional) Filter by specific broker/DEX ID for detailed stats
- page: Page number (default: 1)
- size: Results per page (default: 20)

Returns: ranked list of DEXes with volume, users, and performance metrics"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "broker_id": {
                    "type": "string",
                    "description": "Specific broker ID for detailed stats (optional)",
                },
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                },
                "size": {
                    "type": "integer",
                    "description": "Results per page (default: 20)",
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        broker_id: str = "",
        page: int = 1,
        size: int = 20,
        **kwargs,
    ) -> ToolResult:
        try:
            client = _get_client()
            if broker_id:
                data = await client.get_broker_stats(broker_id)
            else:
                data = await client.get_leaderboard(page=page, size=size)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOneStatsTool(BaseTool):
    """Get platform-wide statistics."""

    @property
    def name(self) -> str:
        return "orderly_one_stats"

    @property
    def description(self) -> str:
        return """Get Orderly One platform-wide statistics.

Returns: total volume, active DEXes, total users, and other aggregate metrics"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            data = await client.get_platform_stats()
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── DEX CRUD Tools (4) — JWT Auth ───────────────────────────────────────────


class OrderlyOneDexGetTool(BaseTool):
    """Get DEX configuration."""

    @property
    def name(self) -> str:
        return "orderly_one_dex_get"

    @property
    def description(self) -> str:
        return """Get DEX configuration from Orderly One.

If dex_id is omitted, returns the current user's DEX.
If dex_id is specified, returns that specific DEX.

Parameters:
- dex_id: (optional) Specific DEX ID. Omit to get your own DEX.

Returns: DEX configuration including broker name, chains, branding, domain, status"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "dex_id": {
                    "type": "string",
                    "description": "DEX ID (optional — omit for your own DEX)",
                },
            },
        }

    async def execute(self, ctx: ToolContext, dex_id: str = "", **kwargs) -> ToolResult:
        try:
            client = _get_client()
            if dex_id:
                data = await client.get_dex(dex_id)
            else:
                data = await client.get_my_dex()
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOneDexCreateTool(BaseTool):
    """Create a new DEX on Orderly One."""

    @property
    def name(self) -> str:
        return "orderly_one_dex_create"

    @property
    def description(self) -> str:
        return """Create a new DEX on Orderly One (DEX-as-a-Service).

This provisions a complete DEX with orderbook trading, powered by Orderly Network's
shared liquidity. The DEX will be deployed to the specified chains.

Parameters:
- broker_name: Name for your DEX/broker (required)
- chain_ids: Array of chain IDs to deploy on (required, e.g. [42161] for Arbitrum)
- logo_url: URL to your DEX logo (optional)
- description: Short description of your DEX (optional)
- primary_color: Brand primary color hex (optional, e.g. "#FF6B00")

Returns: DEX ID, broker ID, deployment status"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "broker_name": {
                    "type": "string",
                    "description": "Name for your DEX (e.g. 'MyDEX')",
                },
                "chain_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Chain IDs to deploy on (e.g. [42161] for Arbitrum)",
                },
                "logo_url": {
                    "type": "string",
                    "description": "URL to DEX logo image (optional)",
                },
                "description": {
                    "type": "string",
                    "description": "Short description of the DEX (optional)",
                },
                "primary_color": {
                    "type": "string",
                    "description": "Brand primary color hex (e.g. '#FF6B00')",
                },
            },
            "required": ["broker_name", "chain_ids"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        broker_name: str = "",
        chain_ids: list = None,
        logo_url: str = "",
        description: str = "",
        primary_color: str = "",
        **kwargs,
    ) -> ToolResult:
        if not broker_name or not chain_ids:
            return ToolResult(
                success=False, error="'broker_name' and 'chain_ids' are required"
            )
        try:
            client = _get_client()
            extra = {}
            if logo_url:
                extra["logo_url"] = logo_url
            if description:
                extra["description"] = description
            if primary_color:
                extra["primary_color"] = primary_color
            data = await client.create_dex(
                broker_name=broker_name, chain_ids=chain_ids, **extra
            )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOneDexUpdateTool(BaseTool):
    """Update DEX configuration."""

    @property
    def name(self) -> str:
        return "orderly_one_dex_update"

    @property
    def description(self) -> str:
        return """Update an existing DEX configuration on Orderly One.

Parameters:
- dex_id: DEX ID to update (required)
- broker_name: New broker name (optional)
- chain_ids: Updated chain IDs (optional)
- logo_url: New logo URL (optional)
- description: New description (optional)
- primary_color: New primary color hex (optional)

Returns: updated DEX configuration"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "dex_id": {
                    "type": "string",
                    "description": "DEX ID to update",
                },
                "broker_name": {
                    "type": "string",
                    "description": "New broker name (optional)",
                },
                "chain_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Updated chain IDs (optional)",
                },
                "logo_url": {
                    "type": "string",
                    "description": "New logo URL (optional)",
                },
                "description": {
                    "type": "string",
                    "description": "New description (optional)",
                },
                "primary_color": {
                    "type": "string",
                    "description": "New primary color hex (optional)",
                },
            },
            "required": ["dex_id"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        dex_id: str = "",
        broker_name: str = "",
        chain_ids: list = None,
        logo_url: str = "",
        description: str = "",
        primary_color: str = "",
        **kwargs,
    ) -> ToolResult:
        if not dex_id:
            return ToolResult(success=False, error="'dex_id' is required")
        try:
            client = _get_client()
            updates = {}
            if broker_name:
                updates["broker_name"] = broker_name
            if chain_ids:
                updates["chain_ids"] = chain_ids
            if logo_url:
                updates["logo_url"] = logo_url
            if description:
                updates["description"] = description
            if primary_color:
                updates["primary_color"] = primary_color
            if not updates:
                return ToolResult(
                    success=False, error="At least one field to update is required"
                )
            data = await client.update_dex(dex_id, **updates)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOneDexDeleteTool(BaseTool):
    """Delete a DEX."""

    @property
    def name(self) -> str:
        return "orderly_one_dex_delete"

    @property
    def description(self) -> str:
        return """Delete a DEX from Orderly One.

WARNING: This is a destructive action. The DEX and its configuration will be removed.

Parameters:
- dex_id: DEX ID to delete (required)

Returns: deletion confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "dex_id": {
                    "type": "string",
                    "description": "DEX ID to delete",
                },
            },
            "required": ["dex_id"],
        }

    async def execute(self, ctx: ToolContext, dex_id: str = "", **kwargs) -> ToolResult:
        if not dex_id:
            return ToolResult(success=False, error="'dex_id' is required")
        try:
            client = _get_client()
            data = await client.delete_dex(dex_id)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Branding Tools (3) — JWT Auth ────────────────────────────────────────────


class OrderlyOneSocialCardTool(BaseTool):
    """Update DEX branding and social links."""

    @property
    def name(self) -> str:
        return "orderly_one_social_card"

    @property
    def description(self) -> str:
        return """Update the social card and branding for your DEX on Orderly One.

Configure social links, OG image, and other branding metadata for your DEX.

Parameters:
- title: Social card title (optional)
- description: Social card description (optional)
- og_image_url: Open Graph image URL (optional)
- twitter_url: Twitter/X profile URL (optional)
- discord_url: Discord invite URL (optional)
- telegram_url: Telegram group URL (optional)
- website_url: Website URL (optional)

Returns: updated social card configuration"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Social card title",
                },
                "description": {
                    "type": "string",
                    "description": "Social card description",
                },
                "og_image_url": {
                    "type": "string",
                    "description": "Open Graph image URL",
                },
                "twitter_url": {
                    "type": "string",
                    "description": "Twitter/X profile URL",
                },
                "discord_url": {
                    "type": "string",
                    "description": "Discord invite URL",
                },
                "telegram_url": {
                    "type": "string",
                    "description": "Telegram group URL",
                },
                "website_url": {
                    "type": "string",
                    "description": "Website URL",
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        title: str = "",
        description: str = "",
        og_image_url: str = "",
        twitter_url: str = "",
        discord_url: str = "",
        telegram_url: str = "",
        website_url: str = "",
        **kwargs,
    ) -> ToolResult:
        try:
            client = _get_client()
            updates = {}
            if title:
                updates["title"] = title
            if description:
                updates["description"] = description
            if og_image_url:
                updates["og_image_url"] = og_image_url
            if twitter_url:
                updates["twitter_url"] = twitter_url
            if discord_url:
                updates["discord_url"] = discord_url
            if telegram_url:
                updates["telegram_url"] = telegram_url
            if website_url:
                updates["website_url"] = website_url
            if not updates:
                return ToolResult(
                    success=False, error="At least one field to update is required"
                )
            data = await client.update_social_card(**updates)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOneDomainTool(BaseTool):
    """Set or remove a custom domain for a DEX."""

    @property
    def name(self) -> str:
        return "orderly_one_domain"

    @property
    def description(self) -> str:
        return """Manage custom domain for your Orderly One DEX.

Set a custom domain (e.g. "trade.mydex.com") or remove the current custom domain
to revert to the default Orderly subdomain.

Parameters:
- dex_id: DEX ID (required)
- action: "set" or "remove" (required)
- domain: Custom domain to set (required when action is "set", e.g. "trade.mydex.com")

Returns: domain configuration status"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "dex_id": {
                    "type": "string",
                    "description": "DEX ID",
                },
                "action": {
                    "type": "string",
                    "enum": ["set", "remove"],
                    "description": "Set or remove custom domain",
                },
                "domain": {
                    "type": "string",
                    "description": "Custom domain (required for 'set' action)",
                },
            },
            "required": ["dex_id", "action"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        dex_id: str = "",
        action: str = "",
        domain: str = "",
        **kwargs,
    ) -> ToolResult:
        if not dex_id or not action:
            return ToolResult(
                success=False, error="'dex_id' and 'action' are required"
            )
        try:
            client = _get_client()
            if action == "set":
                if not domain:
                    return ToolResult(
                        success=False,
                        error="'domain' is required when action is 'set'",
                    )
                data = await client.set_custom_domain(dex_id, domain)
            elif action == "remove":
                data = await client.remove_custom_domain(dex_id)
            else:
                return ToolResult(
                    success=False, error="'action' must be 'set' or 'remove'"
                )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOneVisibilityTool(BaseTool):
    """Toggle leaderboard visibility."""

    @property
    def name(self) -> str:
        return "orderly_one_visibility"

    @property
    def description(self) -> str:
        return """Toggle your DEX's visibility on the Orderly One leaderboard.

Parameters:
- dex_id: DEX ID (required)
- show: true to show on leaderboard, false to hide (required)

Returns: visibility update confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "dex_id": {
                    "type": "string",
                    "description": "DEX ID",
                },
                "show": {
                    "type": "boolean",
                    "description": "true = show on leaderboard, false = hide",
                },
            },
            "required": ["dex_id", "show"],
        }

    async def execute(
        self, ctx: ToolContext, dex_id: str = "", show: bool = True, **kwargs
    ) -> ToolResult:
        if not dex_id:
            return ToolResult(success=False, error="'dex_id' is required")
        try:
            client = _get_client()
            data = await client.set_board_visibility(dex_id, show)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Operations Tools (3) — JWT Auth ─────────────────────────────────────────


class OrderlyOneDeployStatusTool(BaseTool):
    """Check deployment status and trigger upgrades."""

    @property
    def name(self) -> str:
        return "orderly_one_deploy_status"

    @property
    def description(self) -> str:
        return """Check DEX deployment status or trigger an upgrade on Orderly One.

Actions:
- "status": Check current deployment workflow status
- "workflow": Get details of a specific workflow run
- "upgrade_check": Check if an upgrade is available
- "upgrade": Trigger a DEX upgrade to the latest version

Parameters:
- dex_id: DEX ID (required)
- action: "status", "workflow", "upgrade_check", or "upgrade" (default: "status")
- run_id: Workflow run ID (required when action is "workflow")

Returns: deployment status, workflow details, or upgrade information"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "dex_id": {
                    "type": "string",
                    "description": "DEX ID",
                },
                "action": {
                    "type": "string",
                    "enum": ["status", "workflow", "upgrade_check", "upgrade"],
                    "description": "Action to perform (default: status)",
                },
                "run_id": {
                    "type": "string",
                    "description": "Workflow run ID (for 'workflow' action)",
                },
            },
            "required": ["dex_id"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        dex_id: str = "",
        action: str = "status",
        run_id: str = "",
        **kwargs,
    ) -> ToolResult:
        if not dex_id:
            return ToolResult(success=False, error="'dex_id' is required")
        try:
            client = _get_client()
            if action == "status":
                data = await client.get_workflow_status(dex_id)
            elif action == "workflow":
                if not run_id:
                    return ToolResult(
                        success=False,
                        error="'run_id' is required for 'workflow' action",
                    )
                data = await client.get_workflow_run(dex_id, run_id)
            elif action == "upgrade_check":
                data = await client.get_upgrade_status(dex_id)
            elif action == "upgrade":
                data = await client.upgrade_dex(dex_id)
            else:
                return ToolResult(
                    success=False,
                    error="'action' must be 'status', 'workflow', 'upgrade_check', or 'upgrade'",
                )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOneThemeTool(BaseTool):
    """AI-powered theme generation and fine-tuning."""

    @property
    def name(self) -> str:
        return "orderly_one_theme"

    @property
    def description(self) -> str:
        return """Generate or fine-tune your DEX theme using Orderly One's AI theme engine.

Actions:
- "generate": Create a full theme from a text prompt (e.g. "dark cyberpunk with neon green accents")
- "fine_tune": Adjust a specific element's style

Parameters:
- action: "generate" or "fine_tune" (default: "generate")
- prompt: Text description for theme generation (required for "generate")
- element: UI element to fine-tune (required for "fine_tune", e.g. "header", "button", "sidebar")
- style: Style description for the element (required for "fine_tune", e.g. "rounded corners, gradient background")

Returns: generated theme configuration or fine-tuned element styles"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["generate", "fine_tune"],
                    "description": "Generate full theme or fine-tune an element (default: generate)",
                },
                "prompt": {
                    "type": "string",
                    "description": "Text prompt for theme generation (e.g. 'dark mode with blue accents')",
                },
                "element": {
                    "type": "string",
                    "description": "UI element to fine-tune (e.g. 'header', 'button')",
                },
                "style": {
                    "type": "string",
                    "description": "Style description for the element",
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        action: str = "generate",
        prompt: str = "",
        element: str = "",
        style: str = "",
        **kwargs,
    ) -> ToolResult:
        try:
            client = _get_client()
            if action == "generate":
                if not prompt:
                    return ToolResult(
                        success=False,
                        error="'prompt' is required for theme generation",
                    )
                data = await client.modify_theme(prompt)
            elif action == "fine_tune":
                if not element or not style:
                    return ToolResult(
                        success=False,
                        error="'element' and 'style' are required for fine-tuning",
                    )
                data = await client.fine_tune_theme(element, style)
            else:
                return ToolResult(
                    success=False,
                    error="'action' must be 'generate' or 'fine_tune'",
                )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OrderlyOneGraduationTool(BaseTool):
    """Graduate DEX to production."""

    @property
    def name(self) -> str:
        return "orderly_one_graduation"

    @property
    def description(self) -> str:
        return """Manage DEX graduation to production on Orderly One.

Graduation moves your DEX from testnet/sandbox to production with its own broker ID
and full Orderly Network integration.

Actions:
- "status": Check graduation eligibility and progress
- "fees": Get graduation fee options and payment methods
- "verify": Verify a graduation payment transaction
- "finalize": Complete graduation with admin wallet assignment

Parameters:
- action: "status", "fees", "verify", or "finalize" (default: "status")
- tx_hash: Transaction hash to verify (required for "verify")
- chain_id: Chain ID of the payment transaction (required for "verify")
- admin_wallet: Admin wallet address (required for "finalize")

Returns: graduation status, fee options, verification result, or finalization confirmation"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "fees", "verify", "finalize"],
                    "description": "Graduation action (default: status)",
                },
                "tx_hash": {
                    "type": "string",
                    "description": "Payment transaction hash (for 'verify')",
                },
                "chain_id": {
                    "type": "integer",
                    "description": "Chain ID of payment tx (for 'verify')",
                },
                "admin_wallet": {
                    "type": "string",
                    "description": "Admin wallet address (for 'finalize')",
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        action: str = "status",
        tx_hash: str = "",
        chain_id: int = 0,
        admin_wallet: str = "",
        **kwargs,
    ) -> ToolResult:
        try:
            client = _get_client()
            if action == "status":
                data = await client.get_graduation_status()
            elif action == "fees":
                data = await client.get_graduation_fees()
            elif action == "verify":
                if not tx_hash or not chain_id:
                    return ToolResult(
                        success=False,
                        error="'tx_hash' and 'chain_id' are required for 'verify'",
                    )
                data = await client.verify_graduation_tx(tx_hash, chain_id)
            elif action == "finalize":
                if not admin_wallet:
                    return ToolResult(
                        success=False,
                        error="'admin_wallet' is required for 'finalize'",
                    )
                data = await client.finalize_graduation(admin_wallet)
            else:
                return ToolResult(
                    success=False,
                    error="'action' must be 'status', 'fees', 'verify', or 'finalize'",
                )
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
