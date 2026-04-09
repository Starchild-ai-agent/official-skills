"""
Wallet Tool Wrappers — BaseTool classes for Agent framework.
EVM + Solana: balances, transfers, signing, policy.
"""

import asyncio
import logging
import os
import time
from core.tool import BaseTool, ToolContext, ToolResult

from .tools.common import is_fly_machine
from .tools.info import get_wallet_info
from .tools.balance import get_evm_balance, get_sol_balance, get_all_balances
from .tools.transfer import (
    evm_transfer, evm_sign_transaction, evm_sign_message, evm_sign_typed_data,
    evm_transactions, sol_transfer, sol_sign_transaction, sol_sign_message,
    sol_transactions,
)
from .tools.policy import get_policy, validate_and_clean_rules

logger = logging.getLogger(__name__)

EVM_CHAINS = ["ethereum", "base", "arbitrum", "optimism", "polygon", "linea"]

def _fly_check():
    if not is_fly_machine():
        return ToolResult(success=False, error="Not running on a Fly Machine — wallet unavailable")
    return None


# ── Info ─────────────────────────────────────────────────────────────────────

class WalletInfoTool(BaseTool):
    @property
    def name(self): return "wallet_info"
    @property
    def description(self): return "Get all on-chain wallet addresses for this agent (one per chain)."
    @property
    def parameters(self): return {"type": "object", "properties": {}}

    async def execute(self, ctx: ToolContext, **kw) -> ToolResult:
        if err := _fly_check(): return err
        try:
            return ToolResult(success=True, output=await get_wallet_info())
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── EVM Balance ──────────────────────────────────────────────────────────────

class WalletBalanceTool(BaseTool):
    @property
    def name(self): return "wallet_balance"
    @property
    def description(self): return """Get EVM wallet balance on a specific chain. Omit 'asset' to discover ALL tokens.
Chains: ethereum, base, arbitrum, optimism, polygon, linea.
Use wallet_get_all_balances for all chains at once."""
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "chain": {"type": "string", "enum": EVM_CHAINS, "description": "Required. Blockchain network."},
            "address": {"type": "string", "description": "EVM address (0x...). Omit for own wallet."},
            "asset": {"type": "string", "description": "Asset filter. Omit for ALL tokens."},
        },
        "required": ["chain"],
    }

    async def execute(self, ctx: ToolContext, chain="", address="", asset="", **kw) -> ToolResult:
        if not chain or chain not in EVM_CHAINS:
            return ToolResult(success=False, error=f"'chain' required. One of: {', '.join(EVM_CHAINS)}")
        try:
            data = await get_evm_balance(chain, address, asset)
            if "error" in data:
                return ToolResult(success=False, error=data["error"])
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Solana Balance ───────────────────────────────────────────────────────────

class WalletSolBalanceTool(BaseTool):
    @property
    def name(self): return "wallet_sol_balance"
    @property
    def description(self): return "Get Solana wallet balance. Omit 'asset' to discover ALL SPL tokens."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "address": {"type": "string", "description": "Solana address. Omit for own wallet."},
            "asset": {"type": "string", "description": "Asset filter. Omit for ALL tokens."},
        },
    }

    async def execute(self, ctx: ToolContext, address="", asset="", **kw) -> ToolResult:
        try:
            data = await get_sol_balance(address, asset)
            if "error" in data:
                return ToolResult(success=False, error=data["error"])
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── All Balances ─────────────────────────────────────────────────────────────

class WalletGetAllBalancesTool(BaseTool):
    @property
    def name(self): return "wallet_get_all_balances"
    @property
    def description(self): return "Get complete balance snapshot across ALL chains (EVM + Solana) with USD values."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "evm_address": {"type": "string", "description": "EVM address (0x...). Omit for own."},
            "sol_address": {"type": "string", "description": "Solana address. Omit for own."},
        },
    }

    async def execute(self, ctx: ToolContext, evm_address="", sol_address="", **kw) -> ToolResult:
        try:
            data = await get_all_balances(evm_address, sol_address)
            if "error" in data:
                return ToolResult(success=False, error=data["error"])
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── EVM Transfer ─────────────────────────────────────────────────────────────

class WalletTransferTool(BaseTool):
    @property
    def name(self): return "wallet_transfer"
    @property
    def description(self): return """Sign and BROADCAST an EVM transaction. Gas is sponsored.
Use '0' amount for contract calls. Policy-gated if enabled."""
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Target address (0x...)"},
            "amount": {"type": "string", "description": "Amount in wei"},
            "chain_id": {"type": "string", "description": "Chain ID, e.g. '137' for Polygon (default: '1')"},
            "data": {"type": "string", "description": "Hex calldata for contract calls"},
            "gas_limit": {"type": "string"}, "gas_price": {"type": "string"},
            "max_fee_per_gas": {"type": "string"}, "max_priority_fee_per_gas": {"type": "string"},
            "nonce": {"type": "string"}, "tx_type": {"type": "string", "description": "0=legacy, 2=EIP-1559"},
        },
        "required": ["to", "amount"],
    }

    async def execute(self, ctx: ToolContext, to="", amount="", chain_id="1",
                      data="", gas_limit="", gas_price="",
                      max_fee_per_gas="", max_priority_fee_per_gas="",
                      nonce="", tx_type=None, **kw) -> ToolResult:
        if err := _fly_check(): return err
        if not to or not amount:
            return ToolResult(success=False, error="'to' and 'amount' required")
        try:
            chain_id = int(chain_id) if chain_id else 1
            if tx_type is not None:
                tx_type = int(tx_type)
            resp = await evm_transfer(to, amount, chain_id, data, gas_limit, gas_price,
                                      max_fee_per_gas, max_priority_fee_per_gas, nonce, tx_type)
            return ToolResult(success=True, output=resp)
        except Exception as e:
            msg = str(e)
            if "policy" in msg.lower():
                return ToolResult(success=False, error=f"Policy violation: {msg}")
            return ToolResult(success=False, error=msg)


# ── EVM Sign Transaction ────────────────────────────────────────────────────

class WalletSignTransactionTool(BaseTool):
    @property
    def name(self): return "wallet_sign_transaction"
    @property
    def description(self): return "Sign an EVM transaction WITHOUT broadcasting. Returns signed tx data."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "to": {"type": "string"}, "amount": {"type": "string"},
            "chain_id": {"type": "string", "description": "Chain ID (default: '1')"}, "data": {"type": "string"},
            "gas_limit": {"type": "string"}, "gas_price": {"type": "string"},
            "max_fee_per_gas": {"type": "string"}, "max_priority_fee_per_gas": {"type": "string"},
            "nonce": {"type": "string"}, "tx_type": {"type": "string"},
        },
        "required": ["to", "amount"],
    }

    async def execute(self, ctx: ToolContext, to="", amount="", chain_id="1",
                      data="", gas_limit="", gas_price="",
                      max_fee_per_gas="", max_priority_fee_per_gas="",
                      nonce="", tx_type=None, **kw) -> ToolResult:
        if err := _fly_check(): return err
        if not to or not amount:
            return ToolResult(success=False, error="'to' and 'amount' required")
        try:
            chain_id = int(chain_id) if chain_id else 1
            if tx_type is not None:
                tx_type = int(tx_type)
            resp = await evm_sign_transaction(to, amount, chain_id, data, gas_limit, gas_price,
                                              max_fee_per_gas, max_priority_fee_per_gas, nonce, tx_type)
            return ToolResult(success=True, output=resp)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── EVM Sign Message ─────────────────────────────────────────────────────────

class WalletSignTool(BaseTool):
    @property
    def name(self): return "wallet_sign"
    @property
    def description(self): return "Sign a message (EIP-191 personal_sign). Proves wallet ownership."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {"message": {"type": "string", "description": "Message to sign"}},
        "required": ["message"],
    }

    async def execute(self, ctx: ToolContext, message="", **kw) -> ToolResult:
        if err := _fly_check(): return err
        if not message: return ToolResult(success=False, error="'message' required")
        try:
            return ToolResult(success=True, output=await evm_sign_message(message))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── EVM Sign Typed Data ──────────────────────────────────────────────────────

class WalletSignTypedDataTool(BaseTool):
    @property
    def name(self): return "wallet_sign_typed_data"
    @property
    def description(self): return "Sign EIP-712 structured data (permits, orders, etc.)."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "domain": {"type": "object", "description": "EIP-712 domain separator"},
            "types": {"type": "object", "description": "Type definitions"},
            "primaryType": {"type": "string", "description": "Primary type name"},
            "message": {"type": "object", "description": "Data to sign"},
        },
        "required": ["domain", "types", "primaryType", "message"],
    }

    async def execute(self, ctx: ToolContext, domain=None, types=None,
                      primaryType="", message=None, **kw) -> ToolResult:
        if err := _fly_check(): return err
        if not all([domain, types, primaryType, message]):
            return ToolResult(success=False, error="All params required")
        try:
            return ToolResult(success=True, output=await evm_sign_typed_data(domain, types, primaryType, message))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── EVM Transactions ─────────────────────────────────────────────────────────

class WalletTransactionsTool(BaseTool):
    @property
    def name(self): return "wallet_transactions"
    @property
    def description(self): return "Get recent EVM transaction history."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "chain": {"type": "string"}, "asset": {"type": "string"},
            "limit": {"type": "integer", "description": "Max 100"},
        },
    }

    async def execute(self, ctx: ToolContext, **kw) -> ToolResult:
        if err := _fly_check(): return err
        try:
            chain = kw.get("chain", "ethereum")
            asset = kw.get("asset", "")
            limit = kw.get("limit", 20)
            return ToolResult(success=True, output=await evm_transactions(chain, asset, limit))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Solana Transfer ──────────────────────────────────────────────────────────

class WalletSolTransferTool(BaseTool):
    @property
    def name(self): return "wallet_sol_transfer"
    @property
    def description(self): return "Sign and BROADCAST a Solana transaction. No gas sponsorship — user pays gas. Signs via wallet-service, broadcasts via Solana RPC."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "transaction": {"type": "string", "description": "Base64-encoded Solana tx"},
        },
        "required": ["transaction"],
    }

    async def execute(self, ctx: ToolContext, transaction="", **kw) -> ToolResult:
        if err := _fly_check(): return err
        if not transaction: return ToolResult(success=False, error="'transaction' required")
        try:
            result = await sol_transfer(transaction)
            if "error" in result:
                return ToolResult(success=False, error=str(result))
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Solana Sign Transaction ─────────────────────────────────────────────────

class WalletSolSignTransactionTool(BaseTool):
    @property
    def name(self): return "wallet_sol_sign_transaction"
    @property
    def description(self): return "Sign a Solana transaction WITHOUT broadcasting."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {"transaction": {"type": "string", "description": "Base64-encoded Solana tx"}},
        "required": ["transaction"],
    }

    async def execute(self, ctx: ToolContext, transaction="", **kw) -> ToolResult:
        if err := _fly_check(): return err
        if not transaction: return ToolResult(success=False, error="'transaction' required")
        try:
            return ToolResult(success=True, output=await sol_sign_transaction(transaction))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Solana Sign Message ──────────────────────────────────────────────────────

class WalletSolSignTool(BaseTool):
    @property
    def name(self): return "wallet_sol_sign"
    @property
    def description(self): return "Sign a message with Solana wallet (base64)."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {"message": {"type": "string", "description": "Base64-encoded message"}},
        "required": ["message"],
    }

    async def execute(self, ctx: ToolContext, message="", **kw) -> ToolResult:
        if err := _fly_check(): return err
        if not message: return ToolResult(success=False, error="'message' required")
        try:
            return ToolResult(success=True, output=await sol_sign_message(message))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Solana Transactions ──────────────────────────────────────────────────────

class WalletSolTransactionsTool(BaseTool):
    @property
    def name(self): return "wallet_sol_transactions"
    @property
    def description(self): return "Get recent Solana transaction history."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "chain": {"type": "string"}, "asset": {"type": "string"},
            "limit": {"type": "integer"},
        },
    }

    async def execute(self, ctx: ToolContext, chain="solana", asset="sol", limit=20, **kw) -> ToolResult:
        if err := _fly_check(): return err
        try:
            return ToolResult(success=True, output=await sol_transactions(chain, asset, limit))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Get Policy ───────────────────────────────────────────────────────────────

class WalletGetPolicyTool(BaseTool):
    @property
    def name(self): return "wallet_get_policy"
    @property
    def description(self): return """Get wallet policy status.
- enabled=false → allow-all (default)
- enabled=true, rules=[] → deny-all
- enabled=true, rules=[...] → rules enforced"""
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "chain_type": {"type": "string", "enum": ["ethereum", "solana"], "default": "ethereum"},
        },
    }

    async def execute(self, ctx: ToolContext, chain_type="ethereum", **kw) -> ToolResult:
        if err := _fly_check(): return err
        try:
            return ToolResult(success=True, output=await get_policy(chain_type))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Propose Policy ───────────────────────────────────────────────────────────

class WalletProposePolicyTool(BaseTool):
    @property
    def name(self): return "wallet_propose_policy"
    @property
    def description(self): return """Propose a wallet policy update. Sends action_request to frontend for user confirmation.
For both EVM and Solana, call TWICE (once per chain_type)."""
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "chain_type": {"type": "string", "enum": ["ethereum", "solana"]},
            "rules": {"type": "array", "description": "Privy policy rule objects", "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}, "method": {"type": "string"},
                    "conditions": {"type": "array", "items": {"type": "object"}},
                    "action": {"type": "string", "enum": ["ALLOW", "DENY"]},
                },
            }},
            "title": {"type": "string", "description": "Short title (shown in UI)"},
            "description": {"type": "string", "description": "What this policy does"},
        },
        "required": ["chain_type", "rules", "title", "description"],
    }

    async def execute(self, ctx: ToolContext, chain_type="", rules=None,
                      title="", description="", **kw) -> ToolResult:
        if not chain_type or chain_type not in ("ethereum", "solana"):
            return ToolResult(success=False, error="chain_type must be 'ethereum' or 'solana'")
        if rules is None:
            return ToolResult(success=False, error="'rules' required")
        if not title:
            return ToolResult(success=False, error="'title' required")

        cleaned_rules, validation_errors = validate_and_clean_rules(rules, chain_type)
        if validation_errors:
            return ToolResult(
                success=False,
                error="Rule validation failed:\n" + "\n".join(f"- {e}" for e in validation_errors),
            )

        # Truncate names to Privy limit
        for rule in cleaned_rules:
            if isinstance(rule, dict) and "name" in rule and len(rule["name"]) > 50:
                rule["name"] = rule["name"][:50]

        container_id = os.environ.get("FLY_MACHINE_ID", "") or os.environ.get("FLY_ALLOC_ID", "") or "local-dev"
        action_id = f"act_{int(time.time())}_{os.urandom(4).hex()}"

        payload = {
            "container_id": container_id,
            "chain_type": chain_type,
            "rules": cleaned_rules,
        }

        streaming = getattr(ctx, "streaming", None)
        if streaming:
            streaming.action_request(
                action_id=action_id,
                action="update_wallet_policy",
                title=title,
                description=description,
                payload=payload,
                require_signature=True,
            )
            return ToolResult(success=True, output={
                "status": "action_request_sent",
                "action_id": action_id,
                "message": f"Policy proposal sent. Chain: {chain_type}, Rules: {len(cleaned_rules)}.",
            })
        else:
            return ToolResult(
                success=False,
                error="Streaming context not available — cannot send action_request.",
            )
