#!/usr/bin/env python3
"""
1inch Limit Order 全流程测试脚本
测试: create → get → cancel

用法:
  python3 run_limit_order_flow.py

参数固定（测试用）:
  - chain: ethereum
  - maker_asset: USDC (2 USDC, 略高于市价 ~9%, 不会立刻成交)
  - taker_asset: WETH
  - expiry: 1h
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

from _oneinch_lib import (
    get_evm_wallet_address,
    wallet_request,
    _build_requests_proxies,
    _require_env,
)

# ── Constants ─────────────────────────────────────────────────────────────────

CHAIN_ID = 1  # Ethereum mainnet
ROUTER_V6 = "0x111111125421cA6dc452d289314280a0f8842A65"
ORDERBOOK_BASE = "https://api.1inch.dev/orderbook/v4.0"

USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

MAKING_AMOUNT = 2_000_000           # 2 USDC
TAKING_AMOUNT = 920_000_000_000_000  # 0.00092 WETH (~9% above market @ $2366)

ORDER_TYPES = {
    "Order": [
        {"name": "salt",         "type": "uint256"},
        {"name": "maker",        "type": "address"},
        {"name": "receiver",     "type": "address"},
        {"name": "makerAsset",   "type": "address"},
        {"name": "takerAsset",   "type": "address"},
        {"name": "makingAmount", "type": "uint256"},
        {"name": "takingAmount", "type": "uint256"},
        {"name": "makerTraits",  "type": "uint256"},
    ]
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def ob_get(path: str, params: dict = None) -> dict:
    api_key = _require_env("ONEINCH_API_KEY")
    url = f"{ORDERBOOK_BASE}/{CHAIN_ID}{path}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    proxies = _build_requests_proxies(require_proxy=True, service_name="1inch Orderbook")
    resp = requests.get(url, params=params or {}, headers=headers, timeout=30, proxies=proxies)
    if resp.status_code >= 400:
        raise RuntimeError(f"Orderbook GET {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def ob_post(path: str, body: dict) -> dict:
    api_key = _require_env("ONEINCH_API_KEY")
    url = f"{ORDERBOOK_BASE}/{CHAIN_ID}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    proxies = _build_requests_proxies(require_proxy=True, service_name="1inch Orderbook")
    resp = requests.post(url, json=body, headers=headers, timeout=30, proxies=proxies)
    if resp.status_code >= 400:
        raise RuntimeError(f"Orderbook POST {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def build_maker_traits(expiry_seconds: int = 0, allow_partial: bool = True) -> int:
    traits = 0
    if not allow_partial:
        traits |= (1 << 255)
    if expiry_seconds > 0:
        expiry_ts = int(time.time()) + expiry_seconds
        traits |= ((expiry_ts & 0xFFFFFFFFFF) << 80)
    return traits


def sign_typed_data(domain: dict, types: dict, primary_type: str, message: dict) -> str:
    """Sign EIP-712 via platform wallet (requests sync path)."""
    result = wallet_request("POST", "/agent/sign-typed-data", json_body={
        "domain": domain,
        "types": types,
        "primaryType": primary_type,
        "message": message,
    })
    sig = result.get("signature", result.get("data", ""))
    if not sig:
        raise RuntimeError(f"No signature returned: {result}")
    # Normalize v
    sig_hex = sig.replace("0x", "")
    if len(sig_hex) == 130:
        v = int(sig_hex[-2:], 16)
        if v < 27:
            sig = "0x" + sig_hex[:-2] + format(v + 27, "02x")
            print(f"  Normalized v: {v} → {v+27}")
    return sig


# ── Main flow ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("1inch Limit Order 全流程测试")
    print("=" * 60)

    # Step 1: Get wallet address
    print("\n[1/5] 获取钱包地址...")
    wallet_address = get_evm_wallet_address()
    print(f"  wallet: {wallet_address}")

    # Step 2: Build order struct
    print("\n[2/5] 构建限价单...")
    salt = int.from_bytes(os.urandom(32), "big")
    traits = build_maker_traits(expiry_seconds=3600, allow_partial=True)

    order_struct = {
        "salt": str(salt),
        "maker": wallet_address,
        "receiver": "0x0000000000000000000000000000000000000000",
        "makerAsset": USDC,
        "takerAsset": WETH,
        "makingAmount": str(MAKING_AMOUNT),
        "takingAmount": str(TAKING_AMOUNT),
        "makerTraits": str(traits),
    }
    typed_data_message = {
        "salt": salt,
        "maker": wallet_address,
        "receiver": "0x0000000000000000000000000000000000000000",
        "makerAsset": USDC,
        "takerAsset": WETH,
        "makingAmount": MAKING_AMOUNT,
        "takingAmount": TAKING_AMOUNT,
        "makerTraits": traits,
    }
    domain = {
        "name": "1inch Aggregation Router",
        "version": "6",
        "chainId": CHAIN_ID,
        "verifyingContract": ROUTER_V6,
    }
    print(f"  making: {MAKING_AMOUNT} USDC-wei = 2 USDC")
    print(f"  taking: {TAKING_AMOUNT} WETH-wei = 0.00092 WETH")
    print(f"  expiry: 1h, partial fill: yes")

    # Step 3: Sign EIP-712
    print("\n[3/5] EIP-712 签名...")
    signature = sign_typed_data(domain, ORDER_TYPES, "Order", typed_data_message)
    print(f"  signature: {signature[:20]}...{signature[-8:]}")

    # Step 4: Submit to Orderbook
    print("\n[4/5] 提交到 1inch Orderbook...")
    payload = {"signature": signature, "data": order_struct}
    result = ob_post("", payload)
    order_hash = result.get("orderHash", result.get("hash", ""))
    print(f"  ✅ order_hash: {order_hash}")
    print(f"  raw: {json.dumps(result, indent=2)}")

    if not order_hash:
        print("❌ 未返回 order_hash，测试失败")
        sys.exit(1)

    # Step 5: Query order
    print("\n[5/5] 查询限价单状态...")
    time.sleep(2)
    order_data = ob_get(f"/{order_hash}")
    status = order_data.get("status", order_data.get("orderStatus", "unknown"))
    print(f"  status: {status}")
    print(f"  raw: {json.dumps(order_data, indent=2, default=str)[:500]}")

    # Step 6: Cancel
    print("\n[BONUS] 取消限价单 (on-chain calldata)...")
    order_d = order_data.get("data", order_data)
    maker_traits_val = int(order_d.get("makerTraits", "0"))
    order_hash_bytes = bytes.fromhex(order_hash.replace("0x", "").zfill(64))

    # cancelOrder(uint256 makerTraits, bytes32 orderHash) selector = 0x2b155166
    selector = bytes.fromhex("2b155166")
    calldata = selector + maker_traits_val.to_bytes(32, "big") + order_hash_bytes

    cancel_result = wallet_request("POST", "/agent/send-transaction", json_body={
        "to": ROUTER_V6,
        "data": "0x" + calldata.hex(),
        "value": "0",
        "chain_id": CHAIN_ID,
    })
    cancel_tx = cancel_result.get("tx_hash", cancel_result.get("hash", cancel_result.get("transactionHash", "")))
    print(f"  cancel tx: {cancel_tx or cancel_result}")

    print("\n" + "=" * 60)
    print("✅ 限价单全流程测试完成")
    print(f"  order_hash:  {order_hash}")
    print(f"  cancel tx:   {cancel_tx or 'N/A'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
