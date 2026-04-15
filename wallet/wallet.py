"""
Wallet Tool Wrappers — BaseTool classes for Agent framework.
Delegates to /app/tools/wallet core functions for single-source-of-truth maintenance.
"""

import logging
import os
import time
from core.tool import BaseTool, ToolContext, ToolResult

# ── Import core wallet functions from /app/tools/wallet ─────────────────────
from tools.wallet import (
    _is_fly_machine,
    _wallet_request,
    _get_wallet_addresses,
    _validate_and_clean_rules,
    DEBANK_CHAIN_MAP,
)
from core.http_client import proxied_get

logger = logging.getLogger(__name__)

EVM_CHAINS = list(DEBANK_CHAIN_MAP.keys())


def _fly_check():
    if not _is_fly_machine():
        return ToolResult(success=False, error="Not running on a Fly Machine — wallet unavailable")
    return None


def _proxied_get_with_retry(url, params=None, headers=None, timeout=30, max_retries=3):
    """proxied_get with retry on timeout / 429 / 5xx."""
    import requests
    last_exc = None
    for attempt in range(max_retries):
        try:
            resp = proxied_get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
            resp.raise_for_status()
            return resp
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(1)
        except requests.exceptions.HTTPError:
            raise
        except Exception as e:
            last_exc = e
            break
    raise last_exc or Exception("Max retries exceeded")


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
            return ToolResult(success=True, output=await _wallet_request("GET", "/agent/wallet"))
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

        debank_key = os.environ.get("DEBANK_API_KEY", "")
        if debank_key:
            evm_address = address
            if not evm_address:
                if err := _fly_check(): return err
                try:
                    addrs = await _get_wallet_addresses()
                    evm_address = addrs.get("evm", "")
                except Exception as e:
                    return ToolResult(success=False, error=f"Failed to get wallet address: {e}")
            if not evm_address:
                return ToolResult(success=False, error="Could not determine EVM wallet address")

            debank_chain_id = DEBANK_CHAIN_MAP.get(chain)
            try:
                resp = _proxied_get_with_retry(
                    "https://pro-openapi.debank.com/v1/user/token_list",
                    params={"id": evm_address, "chain_id": debank_chain_id, "is_all": "false"},
                    headers={"AccessKey": debank_key},
                )
                return ToolResult(success=True, output={
                    "address": evm_address, "chain": chain, "tokens": resp.json(), "source": "debank",
                })
            except Exception as e:
                return ToolResult(success=False, error=f"DeBank request failed: {e}")
        else:
            if err := _fly_check(): return err
            try:
                params = [f"chain_type=ethereum&chain={chain}"]
                if asset: params.append(f"asset={asset}")
                data = await _wallet_request("GET", f"/agent/balance?{'&'.join(params)}")
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
        birdeye_key = os.environ.get("BIRDEYE_API_KEY", "")
        if birdeye_key:
            sol_address = address
            if not sol_address:
                if err := _fly_check(): return err
                try:
                    addrs = await _get_wallet_addresses()
                    sol_address = addrs.get("sol", "")
                except Exception as e:
                    return ToolResult(success=False, error=f"Failed to get wallet address: {e}")
            if not sol_address:
                return ToolResult(success=False, error="Could not determine Solana wallet address")
            try:
                resp = _proxied_get_with_retry(
                    "https://public-api.birdeye.so/wallet/v2/net-worth",
                    params={"wallet": sol_address},
                    headers={"X-API-KEY": birdeye_key, "x-chain": "solana", "accept": "application/json"},
                )
                return ToolResult(success=True, output={"address": sol_address, "source": "birdeye", "data": resp.json()})
            except Exception as e:
                return ToolResult(success=False, error=f"Birdeye request failed: {e}")
        else:
            if err := _fly_check(): return err
            try:
                params = ["chain_type=solana"]
                if asset: params.append(f"asset={asset}")
                data = await _wallet_request("GET", f"/agent/balance?{'&'.join(params)}")
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
        import asyncio
        if not evm_address or not sol_address:
            if _is_fly_machine():
                try:
                    addrs = await _get_wallet_addresses()
                    evm_address = evm_address or addrs.get("evm", "")
                    sol_address = sol_address or addrs.get("sol", "")
                except Exception:
                    pass

        result = {}
        errors = []
        evm_usd = 0.0
        sol_usd = 0.0

        async def _fetch_evm():
            nonlocal evm_usd
            if not evm_address: return
            debank_key = os.environ.get("DEBANK_API_KEY", "")
            if not debank_key:
                errors.append("No DEBANK_API_KEY"); return
            try:
                resp = _proxied_get_with_retry(
                    "https://pro-openapi.debank.com/v1/user/all_token_list",
                    params={"id": evm_address, "is_all": "true"},
                    headers={"AccessKey": debank_key},
                )
                tokens = resp.json()
                by_chain = {}
                for t in tokens:
                    c = t.get("chain", "unknown")
                    if c not in by_chain:
                        by_chain[c] = {"tokens": [], "total_usd": 0.0}
                    usd = t.get("price", 0) * t.get("amount", 0)
                    by_chain[c]["tokens"].append(t)
                    by_chain[c]["total_usd"] = round(by_chain[c]["total_usd"] + usd, 2)
                    evm_usd += usd
                result["evm"] = {"address": evm_address, "chains": by_chain, "total_usd": round(evm_usd, 2), "source": "debank"}
            except Exception as e:
                errors.append(f"DeBank: {e}")

        async def _fetch_sol():
            nonlocal sol_usd
            if not sol_address: return
            birdeye_key = os.environ.get("BIRDEYE_API_KEY", "")
            if not birdeye_key:
                errors.append("No BIRDEYE_API_KEY"); return
            try:
                resp = _proxied_get_with_retry(
                    "https://public-api.birdeye.so/wallet/v2/net-worth",
                    params={"wallet": sol_address},
                    headers={"X-API-KEY": birdeye_key, "x-chain": "solana", "accept": "application/json"},
                )
                data = resp.json()
                sol_usd = data.get("data", {}).get("totalUsd", 0)
                result["solana"] = {"address": sol_address, "source": "birdeye", "data": data, "total_usd": round(sol_usd, 2)}
            except Exception as e:
                errors.append(f"Birdeye: {e}")

        await asyncio.gather(_fetch_evm(), _fetch_sol())
        result["total_usd_value"] = round(evm_usd + sol_usd, 2)
        if errors: result["errors"] = errors
        has_data = "evm" in result or "solana" in result
        if not has_data and errors:
            return ToolResult(success=False, error="All balance queries failed: " + "; ".join(errors))
        return ToolResult(success=True, output=result)



# ── EVM Transfer ─────────────────────────────────────────────────────────────

class WalletTransferTool(BaseTool):
    @property
    def name(self): return "wallet_transfer"
    @property
    def description(self): return """Sign and BROADCAST an EVM transaction. Gas is sponsored by default (falls back to user-paid if unavailable). Set sponsor=false to pay gas from wallet balance.
Use '0' amount for contract calls. Policy-gated if enabled."""
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Target address (0x...)"},
            "amount": {"type": "string", "description": "Amount in wei"},
            "chain_id": {"type": "integer", "description": "Chain ID (default: 1)"},
            "data": {"type": "string", "description": "Hex calldata for contract calls"},
            "gas_limit": {"type": "string"}, "gas_price": {"type": "string"},
            "max_fee_per_gas": {"type": "string"}, "max_priority_fee_per_gas": {"type": "string"},
            "nonce": {"type": "string"}, "tx_type": {"type": "integer", "description": "0=legacy, 2=EIP-1559"},
            "sponsor": {"type": "boolean", "description": "Gas sponsorship: true=platform pays gas, false=user pays gas from wallet. Omit for auto (try sponsor, fallback to user-paid)."},
        },
        "required": ["to", "amount"],
    }

    async def execute(self, ctx: ToolContext, to="", amount="", chain_id=1, data="",
                      gas_limit="", gas_price="", max_fee_per_gas="", max_priority_fee_per_gas="",
                      nonce="", tx_type=None, sponsor=None, **kw) -> ToolResult:
        if err := _fly_check(): return err
        if not to or not amount:
            return ToolResult(success=False, error="'to' and 'amount' required")
        body = {"to": to, "amount": amount, "chain_id": chain_id}
        if data: body["data"] = data
        if gas_limit: body["gas_limit"] = gas_limit
        if gas_price: body["gas_price"] = gas_price
        if max_fee_per_gas: body["max_fee_per_gas"] = max_fee_per_gas
        if max_priority_fee_per_gas: body["max_priority_fee_per_gas"] = max_priority_fee_per_gas
        if nonce: body["nonce"] = nonce
        if tx_type is not None: body["tx_type"] = tx_type
        if sponsor is not None: body["sponsor"] = sponsor
        try:
            return ToolResult(success=True, output=await _wallet_request("POST", "/agent/transfer", body))
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
            "chain_id": {"type": "integer"}, "data": {"type": "string"},
            "gas_limit": {"type": "string"}, "gas_price": {"type": "string"},
            "max_fee_per_gas": {"type": "string"}, "max_priority_fee_per_gas": {"type": "string"},
            "nonce": {"type": "string"}, "tx_type": {"type": "integer"},
        },
        "required": ["to", "amount"],
    }

    async def execute(self, ctx: ToolContext, to="", amount="", chain_id=1, data="",
                      gas_limit="", gas_price="", max_fee_per_gas="", max_priority_fee_per_gas="",
                      nonce="", tx_type=None, **kw) -> ToolResult:
        if err := _fly_check(): return err
        if not to: return ToolResult(success=False, error="'to' required")
        body = {"to": to, "amount": amount, "chain_id": chain_id}
        if data: body["data"] = data
        if gas_limit: body["gas_limit"] = gas_limit
        if gas_price: body["gas_price"] = gas_price
        if max_fee_per_gas: body["max_fee_per_gas"] = max_fee_per_gas
        if max_priority_fee_per_gas: body["max_priority_fee_per_gas"] = max_priority_fee_per_gas
        if nonce: body["nonce"] = nonce
        if tx_type is not None: body["tx_type"] = tx_type
        try:
            return ToolResult(success=True, output=await _wallet_request("POST", "/agent/sign-transaction", body))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── EVM Sign Message ────────────────────────────────────────────────────────

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
            return ToolResult(success=True, output=await _wallet_request("POST", "/agent/sign", {"message": message}))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── EVM Sign Typed Data ─────────────────────────────────────────────────────

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
            return ToolResult(success=False, error="All params required: domain, types, primaryType, message")
        try:
            return ToolResult(success=True, output=await _wallet_request("POST", "/agent/sign-typed-data", {
                "domain": domain, "types": types, "primaryType": primaryType, "message": message,
            }))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── EVM Transactions ────────────────────────────────────────────────────────

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

    async def execute(self, ctx: ToolContext, chain="ethereum", asset="eth", limit=20, **kw) -> ToolResult:
        if err := _fly_check(): return err
        try:
            qs = f"?chain_type=ethereum&chain={chain}&asset={asset}&limit={limit}"
            return ToolResult(success=True, output=await _wallet_request("GET", f"/agent/transactions{qs}"))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Solana Transfer ──────────────────────────────────────────────────────────

class WalletSolTransferTool(BaseTool):
    @property
    def name(self): return "wallet_sol_transfer"
    @property
    def description(self): return "Sign and BROADCAST a Solana transaction. User pays gas (SOL required for fees). Policy-gated if enabled."
    @property
    def parameters(self): return {
        "type": "object",
        "properties": {
            "transaction": {"type": "string", "description": "Base64-encoded Solana tx"},
            "caip2": {"type": "string", "description": "CAIP-2 chain ID (default: mainnet)"},
        },
        "required": ["transaction"],
    }

    async def execute(self, ctx: ToolContext, transaction="", caip2="solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp", **kw) -> ToolResult:
        if err := _fly_check(): return err
        if not transaction: return ToolResult(success=False, error="'transaction' required")
        try:
            return ToolResult(success=True, output=await _wallet_request("POST", "/agent/sol/transfer", {
                "transaction": transaction, "caip2": caip2,
            }))
        except Exception as e:
            msg = str(e)
            if "policy" in msg.lower():
                return ToolResult(success=False, error=f"Policy violation: {msg}")
            return ToolResult(success=False, error=msg)


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
            return ToolResult(success=True, output=await _wallet_request("POST", "/agent/sol/sign-transaction", {
                "transaction": transaction,
            }))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Solana Sign Message ─────────────────────────────────────────────────────

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
            return ToolResult(success=True, output=await _wallet_request("POST", "/agent/sol/sign", {"message": message}))
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
            qs = f"?chain_type=solana&chain={chain}&asset={asset}&limit={limit}"
            return ToolResult(success=True, output=await _wallet_request("GET", f"/agent/transactions{qs}"))
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
            return ToolResult(success=True, output=await _wallet_request("GET", f"/agent/policy?chain_type={chain_type}"))
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

        # Use system validation function
        cleaned_rules, validation_errors = _validate_and_clean_rules(rules, chain_type)
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
                description=description or title,
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
