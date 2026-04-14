#!/usr/bin/env python3
"""
1inch Limit Order 全流程测试 v2
策略：复用链上真实 extension（固定不变），正确计算 salt
"""

import json, os, sys, time
import requests
from eth_hash.auto import keccak

from _oneinch_lib import (
    get_evm_wallet_address,
    wallet_request,
    _build_requests_proxies,
    _require_env,
)

CHAIN_ID = 1
ROUTER_V6 = "0x111111125421cA6dc452d289314280a0f8842A65"
ORDERBOOK_BASE = "https://api.1inch.dev/orderbook/v4.0"

USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

MAKING_AMOUNT = 2_000_000
TAKING_AMOUNT = 920_000_000_000_000  # ~9% above market, won't fill

# 从链上真实 order 提取的固定 extension (354 bytes)
FIXED_EXTENSION = "0x00000142000000ae000000ae000000ae000000ae000000570000000000000000c0dfdb9e7a392c3dbbe7c6fbe8fbc1789c9fe05e000000012c6406b09498030ae3416b66dc74db31d09524fa87b1f76ea9a11ae13b29f5c555d18bd45f0b94f54a968fc90ed87a54c23dc480b395770895ad27ad6b0d95c0dfdb9e7a392c3dbbe7c6fbe8fbc1789c9fe05e000000012c6406b09498030ae3416b66dc74db31d09524fa87b1f76ea9a11ae13b29f5c555d18bd45f0b94f54a968fc90ed87a54c23dc480b395770895ad27ad6b0d95c0dfdb9e7a392c3dbbe7c6fbe8fbc1789c9fe05e01000000000000000000000000000000000000000090cbe4bdd538d6e9b379bff5fe72c3d67a521de5d18e5e7dc9b58ec02204d3b88277d7a54510981b000000012c6406b09498030ae3416b66dc74db31d09524fa87b1f76ea9a11ae13b29f5c555d18bd45f0b94f54a968fc90ed87a54c23dc480b395770895ad27ad6b0d95"

# makerTraits from real order
FIXED_MAKER_TRAITS = "0x4a000000000000000000000000000000000069ddce8b00000000000000000000"

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


def ob_get(path, params=None):
    api_key = _require_env("ONEINCH_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    proxies = _build_requests_proxies(require_proxy=True, service_name="1inch Orderbook")
    resp = requests.get(f"{ORDERBOOK_BASE}/{CHAIN_ID}{path}", params=params or {}, headers=headers, timeout=30, proxies=proxies)
    if resp.status_code >= 400:
        raise RuntimeError(f"GET {resp.status_code}: {resp.text[:400]}")
    return resp.json()


def ob_post_raw(path, body):
    api_key = _require_env("ONEINCH_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json", "Content-Type": "application/json"}
    proxies = _build_requests_proxies(require_proxy=True, service_name="1inch Orderbook")
    resp = requests.post(f"{ORDERBOOK_BASE}/{CHAIN_ID}{path}", json=body, headers=headers, timeout=30, proxies=proxies)
    return resp


def compute_salt(extension_hex: str) -> int:
    ext_bytes = bytes.fromhex(extension_hex[2:] if extension_hex.startswith("0x") else extension_hex)
    ext_hash = keccak(ext_bytes)
    low160 = int.from_bytes(ext_hash, "big") & ((1 << 160) - 1)
    high96 = int.from_bytes(os.urandom(12), "big") << 160
    return high96 | low160


def sign_typed_data(domain, types, primary_type, message):
    result = wallet_request("POST", "/agent/sign-typed-data", json_body={
        "domain": domain, "types": types,
        "primaryType": primary_type, "message": message,
    })
    sig = result.get("signature", result.get("data", ""))
    if not sig:
        raise RuntimeError(f"No signature: {result}")
    sig_hex = sig.replace("0x", "")
    if len(sig_hex) == 130:
        v = int(sig_hex[-2:], 16)
        if v < 27:
            sig = "0x" + sig_hex[:-2] + format(v + 27, "02x")
    return sig


def main():
    print("=" * 60)
    print("1inch Limit Order 全流程测试 v2")
    print("=" * 60)

    print("\n[1/6] 钱包地址...")
    wallet = get_evm_wallet_address()
    print(f"  {wallet}")

    print("\n[2/6] 计算 salt (keccak160 of extension)...")
    salt = compute_salt(FIXED_EXTENSION)
    maker_traits_int = int(FIXED_MAKER_TRAITS, 16)
    ext_bytes = bytes.fromhex(FIXED_EXTENSION[2:])
    ext_hash = keccak(ext_bytes)
    low160 = int.from_bytes(ext_hash, "big") & ((1 << 160) - 1)
    assert (salt & ((1 << 160) - 1)) == low160, "salt-extension mismatch!"
    print(f"  salt = {salt}")
    print(f"  ✅ salt low160 == keccak160(extension)")

    print("\n[3/6] 构建限价单 (2 USDC → 0.00092 WETH, ~9% above market)...")
    domain = {
        "name": "1inch Aggregation Router",
        "version": "6",
        "chainId": CHAIN_ID,
        "verifyingContract": ROUTER_V6,
    }
    order_msg = {
        "salt": salt,
        "maker": wallet,
        "receiver": "0xc0dfdb9e7a392c3dbbe7c6fbe8fbc1789c9fe05e",
        "makerAsset": USDC,
        "takerAsset": WETH,
        "makingAmount": MAKING_AMOUNT,
        "takingAmount": TAKING_AMOUNT,
        "makerTraits": maker_traits_int,
    }
    order_data_str = {
        "salt": str(salt),
        "maker": wallet,
        "receiver": "0xc0dfdb9e7a392c3dbbe7c6fbe8fbc1789c9fe05e",
        "makerAsset": USDC,
        "takerAsset": WETH,
        "makingAmount": str(MAKING_AMOUNT),
        "takingAmount": str(TAKING_AMOUNT),
        "makerTraits": FIXED_MAKER_TRAITS,
        "extension": FIXED_EXTENSION,
    }

    print("\n[4/6] EIP-712 签名...")
    sig = sign_typed_data(domain, ORDER_TYPES, "Order", order_msg)
    print(f"  sig: {sig[:20]}...{sig[-8:]}")

    print("\n[5/6] 提交到 Orderbook...")
    payload = {"signature": sig, "data": order_data_str}
    resp = ob_post_raw("", payload)
    print(f"  HTTP {resp.status_code}")
    print(f"  body: {resp.text[:600]}")

    if not resp.ok:
        print("\n❌ 提交失败，分析错误...")
        try:
            err = resp.json()
            print(f"  code: {err.get('code', '?')}")
            print(f"  description: {err.get('description', '?')}")
        except:
            pass
        sys.exit(1)

    result = resp.json()
    order_hash = result.get("orderHash", result.get("hash", ""))
    print(f"  ✅ order_hash: {order_hash}")

    print("\n[6/6] 查询状态...")
    time.sleep(2)
    od = ob_get(f"/{order_hash}")
    status = od.get("orderStatus", od.get("status", "?"))
    print(f"  orderStatus: {status}")

    print("\n[BONUS] Cancel order (on-chain calldata)...")
    oh_bytes = bytes.fromhex(order_hash.replace("0x", "").zfill(64))
    selector = bytes.fromhex("2b155166")
    calldata = selector + maker_traits_int.to_bytes(32, "big") + oh_bytes
    cancel = wallet_request("POST", "/agent/send-transaction", json_body={
        "to": ROUTER_V6,
        "data": "0x" + calldata.hex(),
        "value": "0",
        "chain_id": CHAIN_ID,
    })
    cancel_tx = cancel.get("tx_hash", cancel.get("hash", cancel.get("transactionHash", "")))
    print(f"  cancel tx: {cancel_tx or cancel}")

    print("\n" + "=" * 60)
    print("✅ 全流程完成")
    print(f"  order_hash: {order_hash}")
    print(f"  cancel_tx:  {cancel_tx or 'N/A'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
