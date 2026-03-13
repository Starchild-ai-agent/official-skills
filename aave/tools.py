"""
Aave V3 Tools — BaseTool subclasses for Aave V3 yield farming.

Tools (3): aave_supply, aave_withdraw, aave_positions
"""

import logging

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


class AaveSupplyTool(BaseTool):
    """Supply tokens to Aave V3 lending pool."""

    @property
    def name(self) -> str:
        return "aave_supply"

    @property
    def description(self) -> str:
        return """Supply (deposit) tokens into Aave V3 lending pool to earn yield.

Sends two on-chain transactions: ERC-20 approve + Aave pool supply.
Tokens begin earning interest immediately after supply.

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, avalanche
- token: Token symbol (required) — USDC, USDT, DAI, WETH, WBTC (availability varies by chain)
- amount: Amount in human-readable units (required) — e.g. "100" for 100 USDC, "0.5" for 0.5 WETH

Returns: approve_tx_hash, supply_tx_hash, amount, token, chain"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {
                    "type": "string",
                    "description": "Network: ethereum, arbitrum, base, optimism, polygon, avalanche",
                },
                "token": {
                    "type": "string",
                    "description": "Token symbol: USDC, USDT, DAI, WETH, WBTC",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount in human-readable units (e.g. '100' for 100 USDC)",
                },
            },
            "required": ["chain", "token", "amount"],
        }

    async def execute(
        self, ctx: ToolContext, chain: str = "", token: str = "", amount: str = "", **kwargs
    ) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        if not token:
            return ToolResult(success=False, error="'token' is required")
        if not amount:
            return ToolResult(success=False, error="'amount' is required")

        try:
            amount_float = float(amount)
        except ValueError:
            return ToolResult(success=False, error=f"Invalid amount: '{amount}'")

        try:
            from .aave import supply_token
            result = await supply_token(chain, token, amount_float)
            return ToolResult(success=True, output=result)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            error_msg = str(e)
            if "policy" in error_msg.lower():
                return ToolResult(
                    success=False,
                    error=f"Policy violation: {error_msg}. "
                          f"The wallet policy does not allow this operation. "
                          f"Use wallet_propose_policy to propose a policy that allows "
                          f"this transaction. Inform the user what policy change is needed."
                )
            return ToolResult(success=False, error=error_msg)


class AaveWithdrawTool(BaseTool):
    """Withdraw tokens from Aave V3 lending pool."""

    @property
    def name(self) -> str:
        return "aave_withdraw"

    @property
    def description(self) -> str:
        return """Withdraw tokens from Aave V3 lending pool.

Sends a single on-chain transaction to withdraw supplied tokens plus earned interest.
Use max=true to withdraw the entire balance of a token.

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, avalanche
- token: Token symbol (required) — USDC, USDT, DAI, WETH, WBTC (availability varies by chain)
- amount: Amount in human-readable units (required unless max=true) — e.g. "100" for 100 USDC
- max: Set to true to withdraw all (optional, default: false)

Returns: withdraw_tx_hash, amount, token, chain"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {
                    "type": "string",
                    "description": "Network: ethereum, arbitrum, base, optimism, polygon, avalanche",
                },
                "token": {
                    "type": "string",
                    "description": "Token symbol: USDC, USDT, DAI, WETH, WBTC",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount in human-readable units (e.g. '100' for 100 USDC)",
                },
                "max": {
                    "type": "boolean",
                    "description": "Withdraw entire balance (default: false)",
                },
            },
            "required": ["chain", "token"],
        }

    async def execute(
        self, ctx: ToolContext, chain: str = "", token: str = "", amount: str = "",
        max: bool = False, **kwargs
    ) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")
        if not token:
            return ToolResult(success=False, error="'token' is required")
        if not max and not amount:
            return ToolResult(success=False, error="'amount' is required unless max=true")

        amount_float = 0.0
        if not max:
            try:
                amount_float = float(amount)
            except ValueError:
                return ToolResult(success=False, error=f"Invalid amount: '{amount}'")

        try:
            from .aave import withdraw_token
            result = await withdraw_token(chain, token, amount_float, max_withdraw=max)
            return ToolResult(success=True, output=result)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            error_msg = str(e)
            if "policy" in error_msg.lower():
                return ToolResult(
                    success=False,
                    error=f"Policy violation: {error_msg}. "
                          f"The wallet policy does not allow this operation. "
                          f"Use wallet_propose_policy to propose a policy that allows "
                          f"this transaction. Inform the user what policy change is needed."
                )
            return ToolResult(success=False, error=error_msg)


class AavePositionsTool(BaseTool):
    """View Aave V3 account positions."""

    @property
    def name(self) -> str:
        return "aave_positions"

    @property
    def description(self) -> str:
        return """View your Aave V3 lending positions on a specific chain.

Read-only — queries the Aave V3 pool contract via eth_call (no transaction sent).
Returns total collateral, debt, available borrows, health factor, and LTV.

Parameters:
- chain: Network name (required) — ethereum, arbitrum, base, optimism, polygon, avalanche

Returns: total_collateral_usd, total_debt_usd, available_borrows_usd, health_factor, ltv"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chain": {
                    "type": "string",
                    "description": "Network: ethereum, arbitrum, base, optimism, polygon, avalanche",
                },
            },
            "required": ["chain"],
        }

    async def execute(self, ctx: ToolContext, chain: str = "", **kwargs) -> ToolResult:
        if not chain:
            return ToolResult(success=False, error="'chain' is required")

        try:
            from .aave import get_user_positions
            result = await get_user_positions(chain)
            return ToolResult(success=True, output=result)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=str(e))
