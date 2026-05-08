"""OpenOcean skill exports for Starchild.

Read tools:
- openocean_gas_price
- openocean_quote

Write tools:
- openocean_swap

Notes:
- API calls use sc-proxy via proxied_get
- Execution uses wallet service (/agent/transfer)
- Verification uses balance-delta polling because tx hash may be delayed
"""

from __future__ import annotations

import asyncio
import os
import time
from decimal import Decimal, getcontext
from typing import Any, Dict

from core.http_client import proxied_get
from tools.wallet import _wallet_request, DEBANK_CHAIN_MAP

getcontext().prec = 50

SC_CALLER_ID = "skill:openocean"
OPENOCEAN_BASE = "https://open-api.openocean.finance/v4"

NATIVE = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
MAX_UINT256 = (1 << 256) - 1

CHAIN_MAP = {
    "ethereum": 1,
    "eth": 1,
    "bsc": 56,
    "arbitrum": 42161,
    "base": 8453,
    "polygon": 137,
    "optimism": 10,
    "avalanche": 43114,
}


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _wallet_call(method: str, path: str, body: dict | None = None):
    return _run(_wallet_request(method, path, body))


# ---- helpers ---------------------------------------------------------------

def _chain_id(chain: str | int) -> int:
    if isinstance(chain, int):
        return chain
    key = str(chain).strip().lower()
    if key.isdigit():
        return int(key)
    if key in CHAIN_MAP:
        return CHAIN_MAP[key]
    raise ValueError(f"Unsupported chain: {chain}")


def _api_get(chain_id: int, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any] | list:
    url = f"{OPENOCEAN_BASE}/{chain_id}/{endpoint}"
    resp = proxied_get(url, params=params, headers={"SC-CALLER-ID": SC_CALLER_ID})
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 200:
        raise RuntimeError(f"OpenOcean API error: {data}")
    return data.get("data", {})


def _wallet_evm_address() -> str:
    info = _wallet_call("GET", "/agent/wallet")
    wallets = info.get("wallets", []) if isinstance(info, dict) else []
    for w in wallets:
        if w.get("chain_type") == "ethereum":
            return w.get("wallet_address", "")
    raise RuntimeError("No ethereum wallet found")


def _wallet_tokens_ethereum() -> list[dict]:
    debank_key = os.environ.get("DEBANK_API_KEY", "")
    if debank_key:
        addr = _wallet_evm_address()
        resp = proxied_get(
            "https://pro-openapi.debank.com/v1/user/token_list",
            params={
                "id": addr,
                "chain_id": DEBANK_CHAIN_MAP.get("ethereum", "eth"),
                "is_all": "false",
            },
            headers={"AccessKey": debank_key, "SC-CALLER-ID": SC_CALLER_ID},
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    data = _wallet_call("GET", "/agent/balance?chain_type=ethereum&chain=ethereum")
    return data.get("tokens", []) if isinstance(data, dict) else []


def _find_token_amount(tokens: list[dict], token_addr: str, symbol_hint: str = "") -> Decimal:
    token_addr_l = (token_addr or "").lower()
    symbol_u = (symbol_hint or "").upper()
    for t in tokens:
        tid = str(t.get("id", "")).lower()
        sym = str(t.get("symbol", "")).upper()
        if token_addr_l and tid == token_addr_l:
            return Decimal(str(t.get("amount", "0")))
        if token_addr_l == NATIVE.lower() and sym == "ETH":
            return Decimal(str(t.get("amount", "0")))
        if symbol_u and sym == symbol_u:
            return Decimal(str(t.get("amount", "0")))
    return Decimal("0")


def _to_decimal_amount(raw_amount: str | int, decimals: int) -> Decimal:
    return Decimal(str(raw_amount)) / (Decimal(10) ** int(decimals))


def _erc20_approve_data(spender: str, amount: int) -> str:
    # approve(address,uint256) selector
    selector = "095ea7b3"
    spender_clean = spender.lower().replace("0x", "")
    if len(spender_clean) != 40:
        raise ValueError(f"Invalid spender address: {spender}")
    spender_word = spender_clean.rjust(64, "0")
    amount_word = hex(int(amount))[2:].rjust(64, "0")
    return "0x" + selector + spender_word + amount_word


def _get_allowance_raw(chain_id: int, account: str, token: str) -> int:
    rows = _api_get(chain_id, "allowance", {
        "account": account,
        "inTokenAddress": token,
    })
    if isinstance(rows, list) and rows:
        v = rows[0].get("raw") or rows[0].get("allowance") or "0"
        return int(str(v))
    return 0


def _ensure_erc20_allowance(chain_id: int, account: str, token: str, spender: str, needed_raw: int) -> dict:
    current = _get_allowance_raw(chain_id, account, token)
    if current >= needed_raw:
        return {"approved": False, "allowance_before": str(current), "allowance_after": str(current)}

    approve_data = _erc20_approve_data(spender=spender, amount=MAX_UINT256)
    tx_res = _wallet_call(
        "POST",
        "/agent/transfer",
        {
            "to": token,
            "amount": "0",
            "chain_id": chain_id,
            "data": approve_data,
        },
    )

    end_at = time.time() + 120
    after = current
    while time.time() < end_at:
        after = _get_allowance_raw(chain_id, account, token)
        if after >= needed_raw:
            break
        time.sleep(5)

    return {
        "approved": True,
        "allowance_before": str(current),
        "allowance_after": str(after),
        "approve_submission": tx_res,
    }


# ---- public tools ----------------------------------------------------------

def openocean_gas_price(chain: str = "ethereum") -> dict:
    cid = _chain_id(chain)
    data = _api_get(cid, "gasPrice", {})
    return {
        "chain": chain,
        "chain_id": cid,
        "base_wei": data.get("base"),
        "standard": data.get("standard"),
        "fast": data.get("fast"),
        "instant": data.get("instant"),
    }


def openocean_quote(
    chain: str,
    in_token: str,
    out_token: str,
    amount_wei: str,
    slippage: str = "1",
) -> dict:
    cid = _chain_id(chain)
    gas = _api_get(cid, "gasPrice", {})
    gas_wei = int(gas.get("base", 0))

    quote = _api_get(
        cid,
        "quote",
        {
            "inTokenAddress": in_token,
            "outTokenAddress": out_token,
            "amountDecimals": str(amount_wei),
            "gasPriceDecimals": str(gas_wei),
            "slippage": str(slippage),
        },
    )

    in_dec = int(quote.get("inToken", {}).get("decimals", 18))
    out_dec = int(quote.get("outToken", {}).get("decimals", 18))

    return {
        "chain": chain,
        "chain_id": cid,
        "in_token": quote.get("inToken"),
        "out_token": quote.get("outToken"),
        "in_amount_raw": quote.get("inAmount"),
        "out_amount_raw": quote.get("outAmount"),
        "in_amount": str(_to_decimal_amount(quote.get("inAmount", "0"), in_dec)),
        "out_amount": str(_to_decimal_amount(quote.get("outAmount", "0"), out_dec)),
        "estimated_gas": quote.get("estimatedGas"),
        "price_impact": quote.get("price_impact"),
        "router": quote.get("exchange"),
    }


def openocean_swap(
    chain: str,
    in_token: str,
    out_token: str,
    amount_wei: str,
    slippage: str = "1",
    verify_timeout_seconds: int = 90,
    poll_interval_seconds: int = 5,
) -> dict:
    cid = _chain_id(chain)
    if cid != 1:
        return {"error": "Current version verifies using ethereum wallet balance only. Use ethereum first."}

    account = _wallet_evm_address()

    gas = _api_get(cid, "gasPrice", {})
    gas_wei = int(gas.get("base", 0))

    params = {
        "inTokenAddress": in_token,
        "outTokenAddress": out_token,
        "amountDecimals": str(amount_wei),
        "gasPriceDecimals": str(gas_wei),
        "slippage": str(slippage),
    }

    quote = _api_get(cid, "quote", params)
    swap = _api_get(cid, "swap", {**params, "account": account})

    router = str(swap.get("to", ""))
    approve_info = {"approved": False}

    in_addr_norm = str(in_token).lower()
    if in_addr_norm != NATIVE.lower():
        approve_info = _ensure_erc20_allowance(
            chain_id=cid,
            account=account,
            token=str(in_token),
            spender=router,
            needed_raw=int(str(amount_wei)),
        )

    in_symbol = str(quote.get("inToken", {}).get("symbol", "")).upper()
    out_symbol = str(quote.get("outToken", {}).get("symbol", "")).upper()

    in_addr = str(quote.get("inToken", {}).get("address", in_token))
    out_addr = str(quote.get("outToken", {}).get("address", out_token))

    before_tokens = _wallet_tokens_ethereum()
    before_in = _find_token_amount(before_tokens, in_addr, in_symbol)
    before_out = _find_token_amount(before_tokens, out_addr, out_symbol)

    tx_res = _wallet_call(
        "POST",
        "/agent/transfer",
        {
            "to": str(swap["to"]),
            "amount": str(swap.get("value", "0")),
            "chain_id": int(swap["chainId"]),
            "data": str(swap["data"]),
        },
    )

    end_at = time.time() + max(5, int(verify_timeout_seconds))
    verified = False
    after_in = before_in
    after_out = before_out

    while time.time() < end_at:
        now_tokens = _wallet_tokens_ethereum()
        after_in = _find_token_amount(now_tokens, in_addr, in_symbol)
        after_out = _find_token_amount(now_tokens, out_addr, out_symbol)

        if (after_in < before_in) or (after_out > before_out):
            verified = True
            break

        time.sleep(max(1, int(poll_interval_seconds)))

    return {
        "chain": chain,
        "chain_id": cid,
        "wallet": account,
        "quote": {
            "in_amount_raw": quote.get("inAmount"),
            "out_amount_raw": quote.get("outAmount"),
            "estimated_gas": quote.get("estimatedGas"),
            "price_impact": quote.get("price_impact"),
        },
        "approval": approve_info,
        "swap": {
            "to": swap.get("to"),
            "chainId": swap.get("chainId"),
            "estimatedGas": swap.get("estimatedGas"),
            "minOutAmount": swap.get("minOutAmount"),
        },
        "submission": tx_res,
        "verification": {
            "verified_by_balance_delta": verified,
            "before_in": str(before_in),
            "after_in": str(after_in),
            "delta_in": str(after_in - before_in),
            "before_out": str(before_out),
            "after_out": str(after_out),
            "delta_out": str(after_out - before_out),
            "in_symbol": in_symbol,
            "out_symbol": out_symbol,
        },
    }
