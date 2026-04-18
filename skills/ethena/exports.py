"""
Ethena native tool exports.
Tools: ethena_rate, ethena_apy, ethena_balance, ethena_stake,
       ethena_cooldown_start, ethena_unstake
"""
from __future__ import annotations
import json
import sys
import os

# ── stdlib path shim for skill tool runner ──────────────────────────────────
_SKILL_DIR = os.path.dirname(__file__)
if _SKILL_DIR not in sys.path:
    sys.path.insert(0, _SKILL_DIR)

from core.http_client import proxied_get, proxied_post  # noqa: E402

# ── Constants ────────────────────────────────────────────────────────────────
RPC_URL   = "https://ethereum.publicnode.com"
SUSDE     = "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497"
USDE      = "0x4c9EDD5852cd905f086C759E8383e09bff1E68B3"
DEFILLAMA_POOL = "66985a81-4b3f-417b-8e53-b6e9cee0d83a"
CALLER_ID = "chat:ethena-skill"

# Function selectors (keccak256 verified)
SEL_TOTAL_ASSETS   = "0x01e1d114"   # totalAssets()
SEL_TOTAL_SUPPLY   = "0x18160ddd"   # totalSupply()
SEL_COOLDOWN_DUR   = "0x35269315"   # cooldownDuration()
SEL_VESTING_AMT    = "0x00728f76"   # vestingAmount()
SEL_COOLDOWN_END   = "0x525f3146"   # cooldownEnd(address)
SEL_USDE_BALANCE   = "0x70a08231"   # balanceOf(address)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _eth_call(to: str, data: str) -> str:
    """Single eth_call via sc-proxy RPC."""
    resp = proxied_post(RPC_URL, json={
        "jsonrpc": "2.0", "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"], "id": 1
    }, headers={"SC-CALLER-ID": CALLER_ID}, timeout=15)
    return resp.json().get("result", "0x0")


def _to_int(hex_str: str) -> int:
    if not hex_str or hex_str in ("0x", "0x0"):
        return 0
    return int(hex_str, 16)


def _encode_addr(addr: str) -> str:
    return addr.lower().replace("0x", "").zfill(64)


# ── Tool: ethena_rate ────────────────────────────────────────────────────────

def ethena_rate() -> dict:
    """
    Query real-time sUSDe/USDe exchange rate and cooldown duration from chain.

    Returns:
        rate (float): how many USDe per 1 sUSDe
        total_assets (float): total USDe in vault
        total_supply (float): total sUSDe minted
        cooldown_seconds (int): current cooldown period in seconds
        cooldown_hours (float): cooldown in hours
        vesting_amount (float): USDe rewards currently vesting
    """
    ta_hex = _eth_call(SUSDE, SEL_TOTAL_ASSETS)
    ts_hex = _eth_call(SUSDE, SEL_TOTAL_SUPPLY)
    cd_hex = _eth_call(SUSDE, SEL_COOLDOWN_DUR)
    va_hex = _eth_call(SUSDE, SEL_VESTING_AMT)

    ta = _to_int(ta_hex) / 1e18
    ts = _to_int(ts_hex) / 1e18
    cd = _to_int(cd_hex)
    va = _to_int(va_hex) / 1e18
    rate = ta / ts if ts else 0.0

    return {
        "rate": round(rate, 8),
        "total_assets": round(ta, 4),
        "total_supply": round(ts, 4),
        "cooldown_seconds": cd,
        "cooldown_hours": round(cd / 3600, 1),
        "vesting_amount": round(va, 4),
        "note": f"1 sUSDe = {rate:.6f} USDe | cooldown = {cd//3600}h"
    }


# ── Tool: ethena_apy ─────────────────────────────────────────────────────────

def ethena_apy() -> dict:
    """
    Fetch current sUSDe APY from DefiLlama (live pool data).

    Returns:
        apy_current (float): current APY %
        apy_7d (float | None): 7-day average APY %
        apy_30d (float | None): 30-day average APY %
        tvl_usd (float): total value locked in USD
        pool_id (str): DefiLlama pool identifier
    """
    resp = proxied_get(
        f"https://yields.llama.fi/chart/{DEFILLAMA_POOL}",
        headers={"SC-CALLER-ID": CALLER_ID}, timeout=15
    )
    data = resp.json().get("data", [])

    if not data:
        # Fallback: search pools list
        resp2 = proxied_get("https://yields.llama.fi/pools",
                             headers={"SC-CALLER-ID": CALLER_ID}, timeout=15)
        pools = resp2.json().get("data", [])
        pool = next((p for p in pools if p.get("pool") == DEFILLAMA_POOL), None)
        if not pool:
            pool = next((p for p in pools
                         if "susde" in p.get("symbol", "").lower()
                         and p.get("chain") == "Ethereum"), None)
        if pool:
            return {
                "apy_current": round(pool.get("apy", 0), 4),
                "apy_7d": pool.get("apy7d"),
                "apy_30d": pool.get("apy30d"),
                "tvl_usd": pool.get("tvlUsd"),
                "pool_id": pool.get("pool"),
            }
        return {"error": "Could not fetch APY data from DefiLlama"}

    # Use latest data point from chart
    latest = data[-1]
    # 7d/30d from rolling window of chart data
    apy_7d  = round(sum(d["apy"] for d in data[-7:])  / min(7,  len(data)), 4) if len(data) >= 2 else None
    apy_30d = round(sum(d["apy"] for d in data[-30:]) / min(30, len(data)), 4) if len(data) >= 7 else None

    return {
        "apy_current": round(latest.get("apy", 0), 4),
        "apy_7d": apy_7d,
        "apy_30d": apy_30d,
        "tvl_usd": latest.get("tvlUsd"),
        "pool_id": DEFILLAMA_POOL,
        "data_date": latest.get("timestamp"),
    }


# ── Tool: ethena_balance ─────────────────────────────────────────────────────

def ethena_balance(wallet_address: str) -> dict:
    """
    Query USDe and sUSDe balances for a given wallet address.

    Args:
        wallet_address: EVM wallet address (0x...)

    Returns:
        usde_balance (float): USDe token balance
        susde_balance (float): sUSDe token balance
        susde_in_usde (float): sUSDe balance converted to USDe at current rate
        cooldown_end (int): Unix timestamp when cooldown ends (0 = no active cooldown)
    """
    enc = _encode_addr(wallet_address)

    usde_hex   = _eth_call(USDE,  f"{SEL_USDE_BALANCE}{enc}")
    susde_hex  = _eth_call(SUSDE, f"{SEL_USDE_BALANCE}{enc}")
    cd_end_hex = _eth_call(SUSDE, f"{SEL_COOLDOWN_END}{enc}")

    usde_bal  = _to_int(usde_hex)  / 1e18
    susde_bal = _to_int(susde_hex) / 1e18
    cd_end    = _to_int(cd_end_hex)

    # Get rate for conversion
    ta = _to_int(_eth_call(SUSDE, SEL_TOTAL_ASSETS)) / 1e18
    ts = _to_int(_eth_call(SUSDE, SEL_TOTAL_SUPPLY)) / 1e18
    rate = ta / ts if ts else 1.0

    return {
        "wallet": wallet_address,
        "usde_balance": round(usde_bal, 6),
        "susde_balance": round(susde_bal, 6),
        "susde_in_usde": round(susde_bal * rate, 6),
        "cooldown_end_ts": cd_end,
        "has_active_cooldown": cd_end > 0,
        "rate": round(rate, 8),
    }


# ── Tool: ethena_stake ───────────────────────────────────────────────────────

def ethena_stake(amount_usde: str, receiver: str) -> dict:
    """
    Generate approve + deposit calldata to stake USDe for sUSDe.
    Returns two transactions that must be executed in order.

    Args:
        amount_usde: amount of USDe to stake (e.g. "100" or "100.5")
        receiver: wallet address to receive sUSDe

    Returns:
        transactions: list of two tx dicts (approve, then deposit)
        amount_wei: amount in wei
        expected_susde: estimated sUSDe received at current rate
    """
    from scripts.ethena_ops import approve_calldata, deposit_calldata, to_wei, validate_address

    validate_address(receiver)
    wei = to_wei(amount_usde)

    # Get current rate for estimate
    ta = _to_int(_eth_call(SUSDE, SEL_TOTAL_ASSETS)) / 1e18
    ts = _to_int(_eth_call(SUSDE, SEL_TOTAL_SUPPLY)) / 1e18
    rate = ta / ts if ts else 1.0
    expected_susde = float(amount_usde) / rate if rate else 0.0

    return {
        "action": "stake",
        "amount_usde": amount_usde,
        "amount_wei": wei,
        "receiver": receiver,
        "expected_susde": round(expected_susde, 6),
        "current_rate": round(rate, 8),
        "transactions": [
            approve_calldata(wei),
            deposit_calldata(wei, receiver),
        ],
        "note": "Execute tx[0] (approve) first, then tx[1] (deposit). Both on Ethereum mainnet."
    }


# ── Tool: ethena_cooldown_start ──────────────────────────────────────────────

def ethena_cooldown_start(amount_usde: str) -> dict:
    """
    Generate calldata to start the cooldown period for unstaking sUSDe.
    The actual cooldown duration is fetched live from chain (currently ~24h).

    Args:
        amount_usde: USDe-denominated amount of sUSDe to redeem (e.g. "100")

    Returns:
        transaction: tx dict for cooldownAssets
        cooldown_seconds: current cooldown duration
        cooldown_hours: cooldown in hours
    """
    from scripts.ethena_ops import cooldown_calldata, to_wei

    wei = to_wei(amount_usde)
    cd_sec = _to_int(_eth_call(SUSDE, SEL_COOLDOWN_DUR))

    return {
        "action": "cooldown_start",
        "amount_usde": amount_usde,
        "amount_wei": wei,
        "cooldown_seconds": cd_sec,
        "cooldown_hours": round(cd_sec / 3600, 1),
        "transaction": cooldown_calldata(wei),
        "note": f"After executing, wait {cd_sec//3600}h then call ethena_unstake."
    }


# ── Tool: ethena_unstake ─────────────────────────────────────────────────────

def ethena_unstake(receiver: str) -> dict:
    """
    Generate calldata to claim USDe after cooldown has completed.

    Args:
        receiver: wallet address to receive the USDe

    Returns:
        transaction: tx dict for unstake
    """
    from scripts.ethena_ops import unstake_calldata, validate_address

    validate_address(receiver)
    cd_sec = _to_int(_eth_call(SUSDE, SEL_COOLDOWN_DUR))

    return {
        "action": "unstake",
        "receiver": receiver,
        "transaction": unstake_calldata(receiver),
        "note": f"Only call after cooldown ({cd_sec//3600}h) has passed. USDe goes to {receiver}."
    }


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS = {
    "ethena_rate":           ethena_rate,
    "ethena_apy":            ethena_apy,
    "ethena_balance":        ethena_balance,
    "ethena_stake":          ethena_stake,
    "ethena_cooldown_start": ethena_cooldown_start,
    "ethena_unstake":        ethena_unstake,
}
