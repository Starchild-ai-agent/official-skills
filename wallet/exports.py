"""
Wallet skill exports — for use in task scripts via core.skill_tools.

Usage:
    from core.skill_tools import wallet
    info = wallet.wallet_info()
    bal = wallet.wallet_balance(chain="base")
    all_bal = wallet.wallet_get_all_balances()

Delegates to /app/tools/wallet core functions for single-source maintenance.
"""

import asyncio

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# Import core functions from /app/tools/wallet
from tools.wallet import (
    _wallet_request,
    _is_fly_machine,
    _get_wallet_addresses,
    _validate_and_clean_rules,
    DEBANK_CHAIN_MAP,
)
from core.http_client import proxied_get

EVM_CHAINS = list(DEBANK_CHAIN_MAP.keys())


def _run(coro):
    """Run async in sync context (works even if event loop is running)."""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ── Info ─────────────────────────────────────────────────────────────────────

def wallet_info():
    """Get all wallet addresses."""
    return _run(_wallet_request("GET", "/agent/wallet"))


# ── Balances ─────────────────────────────────────────────────────────────────

def wallet_balance(chain: str, address: str = "", asset: str = ""):
    """Get EVM balance on a chain (via DeBank or wallet-service fallback)."""
    import os
    async def _impl():
        if chain not in EVM_CHAINS:
            return {"error": f"Invalid chain '{chain}'. Must be one of: {', '.join(EVM_CHAINS)}"}
        debank_key = os.environ.get("DEBANK_API_KEY", "")
        if debank_key:
            evm_address = address
            if not evm_address:
                addrs = await _get_wallet_addresses()
                evm_address = addrs.get("evm", "")
            if not evm_address:
                return {"error": "Could not determine EVM wallet address"}
            resp = proxied_get(
                "https://pro-openapi.debank.com/v1/user/token_list",
                params={"id": evm_address, "chain_id": DEBANK_CHAIN_MAP.get(chain), "is_all": "false"},
                headers={"AccessKey": debank_key},
            )
            resp.raise_for_status()
            return {"address": evm_address, "chain": chain, "tokens": resp.json(), "source": "debank"}
        else:
            params = [f"chain_type=ethereum&chain={chain}"]
            if asset: params.append(f"asset={asset}")
            return await _wallet_request("GET", f"/agent/balance?{'&'.join(params)}")
    return _run(_impl())


def wallet_sol_balance(address: str = "", asset: str = ""):
    """Get Solana balance."""
    import os
    async def _impl():
        birdeye_key = os.environ.get("BIRDEYE_API_KEY", "")
        if birdeye_key:
            sol_address = address
            if not sol_address:
                addrs = await _get_wallet_addresses()
                sol_address = addrs.get("sol", "")
            if not sol_address:
                return {"error": "Could not determine Solana wallet address"}
            resp = proxied_get(
                "https://public-api.birdeye.so/wallet/v2/net-worth",
                params={"wallet": sol_address},
                headers={"X-API-KEY": birdeye_key, "x-chain": "solana", "accept": "application/json"},
            )
            resp.raise_for_status()
            return {"address": sol_address, "source": "birdeye", "data": resp.json()}
        else:
            params = ["chain_type=solana"]
            if asset: params.append(f"asset={asset}")
            return await _wallet_request("GET", f"/agent/balance?{'&'.join(params)}")
    return _run(_impl())


def wallet_get_all_balances(evm_address: str = "", sol_address: str = ""):
    """Get balances across all chains."""
    async def _impl():
        ea, sa = evm_address, sol_address
        if not ea or not sa:
            if _is_fly_machine():
                try:
                    addrs = await _get_wallet_addresses()
                    ea = ea or addrs.get("evm", "")
                    sa = sa or addrs.get("sol", "")
                except Exception:
                    pass
        # Delegate to per-chain balance calls
        result = {}
        if ea:
            for chain in EVM_CHAINS:
                try:
                    data = wallet_balance(chain, ea)
                    if "error" not in data:
                        result[chain] = data
                except Exception:
                    pass
        if sa:
            try:
                data = wallet_sol_balance(sa)
                if "error" not in data:
                    result["solana"] = data
            except Exception:
                pass
        return result
    return _run(_impl())


# ── Transfers ────────────────────────────────────────────────────────────────

def wallet_transfer(to, amount, chain_id=1, data="", **kw):
    """Sign and broadcast EVM tx."""
    async def _impl():
        body = {"to": to, "amount": str(amount), "chain_id": chain_id}
        if data: body["data"] = data
        for k in ("gas_limit", "gas_price", "max_fee_per_gas", "max_priority_fee_per_gas", "nonce"):
            if kw.get(k): body[k] = kw[k]
        if kw.get("tx_type") is not None: body["tx_type"] = kw["tx_type"]
        return await _wallet_request("POST", "/agent/transfer", body)
    return _run(_impl())


def wallet_sign_transaction(to, amount, chain_id=1, data="", **kw):
    """Sign EVM tx without broadcasting."""
    async def _impl():
        body = {"to": to, "amount": str(amount), "chain_id": chain_id}
        if data: body["data"] = data
        for k in ("gas_limit", "gas_price", "max_fee_per_gas", "max_priority_fee_per_gas", "nonce"):
            if kw.get(k): body[k] = kw[k]
        if kw.get("tx_type") is not None: body["tx_type"] = kw["tx_type"]
        return await _wallet_request("POST", "/agent/sign-transaction", body)
    return _run(_impl())


def wallet_sign(message):
    """EIP-191 personal_sign."""
    return _run(_wallet_request("POST", "/agent/sign", {"message": message}))


def wallet_sign_typed_data(domain, types, primaryType, message):
    """Sign EIP-712 typed data."""
    return _run(_wallet_request("POST", "/agent/sign-typed-data", {
        "domain": domain, "types": types, "primaryType": primaryType, "message": message,
    }))


def wallet_transactions(chain="ethereum", asset="", limit=20):
    """EVM tx history."""
    qs = f"?chain_type=ethereum&chain={chain}&asset={asset or 'eth'}&limit={limit}"
    return _run(_wallet_request("GET", f"/agent/transactions{qs}"))


# ── Solana ───────────────────────────────────────────────────────────────────

def wallet_sol_transfer(transaction, caip2="solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"):
    """Sign and broadcast Solana tx."""
    return _run(_wallet_request("POST", "/agent/sol/transfer", {
        "transaction": transaction, "caip2": caip2,
    }))


def wallet_sol_sign_transaction(transaction):
    """Sign Solana tx without broadcasting."""
    return _run(_wallet_request("POST", "/agent/sol/sign-transaction", {"transaction": transaction}))


def wallet_sol_sign(message):
    """Sign message with Solana wallet."""
    return _run(_wallet_request("POST", "/agent/sol/sign", {"message": message}))


def wallet_sol_transactions(chain="solana", asset="sol", limit=20):
    """Solana tx history."""
    qs = f"?chain_type=solana&chain={chain}&asset={asset}&limit={limit}"
    return _run(_wallet_request("GET", f"/agent/transactions{qs}"))


# ── Policy ───────────────────────────────────────────────────────────────────

def wallet_get_policy(chain_type="ethereum"):
    """Get current policy status."""
    return _run(_wallet_request("GET", f"/agent/policy?chain_type={chain_type}"))


def validate_and_clean_rules(rules, chain_type):
    """Validate rules (re-export from system)."""
    return _validate_and_clean_rules(rules, chain_type)
