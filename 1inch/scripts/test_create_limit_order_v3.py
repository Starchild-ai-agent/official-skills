#!/usr/bin/env python3
"""
create_limit_order 实测 v3
策略：1inch 官方 Node.js SDK 构建 order（FeeTakerExtension + withRandomNonce）
      → Python 侧 EIP-712 签名 → 提交 Orderbook → 验证 → cancel

测试项：
  T1. SDK 构建 order（extension, receiver, makerTraits）
  T2. salt 正确（low160 == keccak160(extension)）
  T3. EIP-712 签名成功
  T4. HTTP 201 提交成功
  T5. 查询 order 状态
  T6. cancel order（on-chain calldata）
"""

import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
from eth_hash.auto import keccak

from _oneinch_lib import (
    _build_requests_proxies,
    _require_env,
    get_evm_wallet_address,
    wallet_request,
)

CHAIN_ID  = 1
ROUTER_V6 = "0x111111125421cA6dc452d289314280a0f8842A65"
ORDERBOOK = "https://api.1inch.dev/orderbook/v4.0"
PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

# SDK 只用于生成 FeeTaker extension（encode()），不用其 makerTraits（会带随机nonce→BIT_INVALIDATOR）
# makerTraits 由 Python 侧显式构建：bit254=allowMultipleFills, bits80-119=expiry, nonce=0
NODE_BUILD_EXT_SCRIPT = r"""
const sdk = require('/tmp/node_modules/@1inch/limit-order-sdk');
const {LimitOrderWithFee, FeeTakerExt, Address} = sdk;
const {FeeTakerExtension, ResolverFee, Fees, WhitelistHalfAddress} = FeeTakerExt;
const {Bps} = require('/tmp/node_modules/@1inch/limit-order-sdk/dist/cjs/bps.js');

const HALF_ADDRS = ['0xb09498030ae3416b66dc','0x74db31d09524fa87b1f7','0x6ea9a11ae13b29f5c555',
                    '0xd18bd45f0b94f54a968f','0xc90ed87a54c23dc480b3','0x95770895ad27ad6b0d95'];
const wl       = new WhitelistHalfAddress(HALF_ADDRS);
const FEETAKER = new Address('0xc0dfdb9e7a392c3dbbe7c6fbe8fbc1789c9fe05e');
const FEE_RECV = new Address('0x90cbe4bdd538d6e9b379bff5fe72c3d67a521de5');
const fees     = Fees.resolverFee(new ResolverFee(FEE_RECV, new Bps(30n)));
const feeExt   = new FeeTakerExtension(FEETAKER, fees, wl);

// Build a dummy order just to get extension.encode() — we override makerTraits later
const MAKER = new Address(process.env.MAKER_ADDRESS);
const order  = LimitOrderWithFee.withRandomNonce({
    makerAsset: new Address('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'),
    takerAsset: new Address('0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
    makingAmount: 2000000n, takingAmount: 750000000000000n, maker: MAKER,
}, feeExt);

const ext = order.extension.encode();
// Only output what we need: extension + receiver
process.stdout.write(JSON.stringify({
    extension: ext,
    receiver:  '0xc0dfdb9e7a392c3dbbe7c6fbe8fbc1789c9fe05e',
}) + '\n');
"""


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

DOMAIN = {
    "name":              "1inch Aggregation Router",
    "version":           "6",
    "chainId":           CHAIN_ID,
    "verifyingContract": ROUTER_V6,
}


def _compute_salt(ext_hex: str) -> int:
    ext_bytes = bytes.fromhex(ext_hex[2:] if ext_hex.startswith("0x") else ext_hex)
    ext_hash  = keccak(ext_bytes)
    low160    = int.from_bytes(ext_hash, "big") & ((1 << 160) - 1)
    high96    = int.from_bytes(os.urandom(12), "big") << 160
    return high96 | low160


def ob_get(path, params=None):
    api_key = _require_env("ONEINCH_API_KEY")
    h  = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    px = _build_requests_proxies(require_proxy=True, service_name="1inch")
    r  = requests.get(f"{ORDERBOOK}/{CHAIN_ID}{path}", params=params or {},
                      headers=h, proxies=px, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"GET {r.status_code}: {r.text[:300]}")
    return r.json()


def ob_post_raw(path, body):
    api_key = _require_env("ONEINCH_API_KEY")
    h  = {"Authorization": f"Bearer {api_key}", "Accept": "application/json",
          "Content-Type": "application/json"}
    px = _build_requests_proxies(require_proxy=True, service_name="1inch")
    return requests.post(f"{ORDERBOOK}/{CHAIN_ID}{path}", json=body,
                         headers=h, proxies=px, timeout=30)


def sign_typed(domain, types, primary_type, msg):
    res = wallet_request("POST", "/agent/sign-typed-data", json_body={
        "domain": domain, "types": types,
        "primaryType": primary_type, "message": msg,
    })
    sig = res.get("signature", res.get("data", ""))
    if not sig:
        raise RuntimeError(f"No signature: {res}")
    sig_hex = sig.replace("0x", "")
    if len(sig_hex) == 130:
        v = int(sig_hex[-2:], 16)
        if v < 27:
            sig = "0x" + sig_hex[:-2] + format(v + 27, "02x")
    return sig


def main():
    results = []
    print("=" * 65)
    print("create_limit_order 实测 v3 — SDK FeeTaker + Python 签名")
    print("=" * 65)

    wallet = get_evm_wallet_address()
    print(f"\n[INFO] wallet: {wallet}")

    # ── T1: Node SDK 生成 FeeTaker extension ─────────────────────────
    print("\n[T1] 1inch SDK 生成 FeeTaker extension...")
    env = os.environ.copy()
    env["MAKER_ADDRESS"] = wallet
    r = subprocess.run(
        ["node", "-e", NODE_BUILD_EXT_SCRIPT],
        capture_output=True, text=True, env=env,
    )
    if r.returncode != 0:
        print(f"  {FAIL} Node error: {r.stderr[:300]}")
        results.append(("T1 SDK extension", False, r.stderr[:80]))
        _print_summary(results)
        sys.exit(1)

    sdk_out   = json.loads(r.stdout.strip())
    extension = sdk_out["extension"]
    receiver  = sdk_out["receiver"]

    print(f"  {PASS} extension len = {len(extension)} chars ({(len(extension)-2)//2} bytes)")
    print(f"  receiver  = {receiver}")
    results.append(("T1 SDK extension", True, f"{len(extension)} chars"))

    # ── Build makerTraits in Python (nonce=0 → epoch mode, bit254=allowMultipleFills) ──
    # Bit layout (LOP v4):
    #   bit 255 = NO_PARTIAL_FILLS  (leave 0 = allow partial)
    #   bit 254 = ALLOW_MULTIPLE_FILLS (set to 1)
    #   bit 251 = POST_INTERACTION_CALL (set to 1 — FeeTaker requires it)
    #   bits 80-119 = expiry (40-bit unix ts)
    #   bits 120-159 = nonce/epoch (0 = epoch mode, no bit-invalidator)
    expiry_ts   = int(time.time()) + 86400
    # Start from 0x4a000... base (bit254=1, bit251=1 = allowMultipleFills + postInteraction)
    # 0x40 = bit254, 0x08 = bit251 → combined = 0x48 << 248 ... use direct bit math
    maker_traits_int = (
        (1 << 254)               # allowMultipleFills
        | (1 << 251)             # enablePostInteraction (FeeTaker hook)
        | (1 << 249)             # HAS_EXTENSION_FLAG — REQUIRED when extension != "0x"
        | ((expiry_ts & 0xFFFFFFFFFF) << 80)  # expiry
    )
    # DO NOT set bits 120-159 (nonce) — must be 0 to avoid BIT_INVALIDATOR mode

    # Build order fields
    salt_int    = _compute_salt(extension)
    USDC        = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    WETH        = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    MAKING      = 2_000_000
    TAKING      = 750_000_000_000_000

    data = {
        "salt":         str(salt_int),
        "maker":        wallet,
        "receiver":     receiver,
        "makerAsset":   USDC,
        "takerAsset":   WETH,
        "makingAmount": str(MAKING),
        "takingAmount": str(TAKING),
        "makerTraits":  hex(maker_traits_int),
        "extension":    extension,
    }
    print(f"  makerTraits = {hex(maker_traits_int)}")
    print(f"  salt        = {str(salt_int)[:20]}...")

    # ── T2: 验证 salt = (rand96<<160) | keccak160(extension) ─────────
    print("\n[T2] 验证 salt — keccak160(extension)...")
    ext_bytes = bytes.fromhex(extension[2:])
    ext_hash  = keccak(ext_bytes)
    low160    = int.from_bytes(ext_hash, "big") & ((1 << 160) - 1)
    salt_low  = salt_int & ((1 << 160) - 1)
    ok        = salt_low == low160
    print(f"  salt low160 == keccak160(ext): {ok}")
    results.append(("T2 salt keccak160", ok, ""))

    # ── T3: EIP-712 签名 ──────────────────────────────────────────────
    print("\n[T3] EIP-712 签名...")
    msg = {
        "salt":         salt_int,
        "maker":        wallet,
        "receiver":     receiver,
        "makerAsset":   data["makerAsset"],
        "takerAsset":   data["takerAsset"],
        "makingAmount": MAKING,
        "takingAmount": TAKING,
        "makerTraits":  maker_traits_int,
    }
    try:
        sig = sign_typed(DOMAIN, ORDER_TYPES, "Order", msg)
        print(f"  {PASS} sig: {sig[:20]}...{sig[-8:]}")
        results.append(("T3 EIP-712 sign", True, ""))
    except Exception as e:
        print(f"  {FAIL} {e}")
        results.append(("T3 EIP-712 sign", False, str(e)))
        _print_summary(results)
        sys.exit(1)

    # ── T4: 提交 ─────────────────────────────────────────────────────
    print("\n[T4] POST to 1inch Orderbook...")
    payload = {"signature": sig, "data": data}
    resp    = ob_post_raw("", payload)
    print(f"  HTTP {resp.status_code}")
    print(f"  body: {resp.text[:500]}")

    if resp.status_code in (200, 201):
        result     = resp.json()
        order_hash = result.get("orderHash", result.get("hash", ""))
        print(f"  {PASS} order_hash: {order_hash}")
        results.append(("T4 HTTP 201 submit", True, order_hash[:20] + "..."))
    else:
        try:
            e = resp.json()
            print(f"  code={e.get('code','?')} | {e.get('description','?')}")
        except Exception:
            pass
        results.append(("T4 HTTP 201 submit", False, f"HTTP {resp.status_code}"))
        _print_summary(results)
        sys.exit(1)

    # ── T5: 查询状态 ──────────────────────────────────────────────────
    print("\n[T5] 查询 order 状态...")
    time.sleep(2)
    try:
        od     = ob_get(f"/{order_hash}")
        status = od.get("orderStatus", od.get("status", "?"))
        print(f"  orderStatus: {status}")
        results.append(("T5 get_order", True, status))
    except Exception as e:
        print(f"  {FAIL} {e}")
        results.append(("T5 get_order", False, str(e)[:80]))

    # ── T6: Cancel (on-chain calldata) ────────────────────────────────
    print("\n[T6] Cancel order (on-chain calldata)...")
    try:
        traits_int = int(data["makerTraits"], 16)
        oh_bytes   = bytes.fromhex(order_hash.replace("0x", "").zfill(64))
        selector   = bytes.fromhex("2b155166")
        calldata   = selector + traits_int.to_bytes(32, "big") + oh_bytes
        cancel     = wallet_request("POST", "/agent/send-transaction", json_body={
            "to":       ROUTER_V6,
            "data":     "0x" + calldata.hex(),
            "value":    "0",
            "chain_id": CHAIN_ID,
        })
        cancel_tx = cancel.get("tx_hash", cancel.get("hash", cancel.get("transactionHash", "")))
        if cancel_tx:
            print(f"  {PASS} cancel tx: {cancel_tx}")
            results.append(("T6 cancel_order", True, cancel_tx[:20] + "..."))
        else:
            print(f"  {WARN} no tx_hash: {cancel}")
            results.append(("T6 cancel_order", False, "no tx_hash"))
    except Exception as e:
        print(f"  {WARN} {e}")
        results.append(("T6 cancel_order", False, str(e)[:80]))

    _print_summary(results)


def _print_summary(results):
    print("\n" + "=" * 65)
    print("测试报告")
    print("=" * 65)
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, note in results:
        icon  = PASS if ok else FAIL
        extra = f"  [{note}]" if note else ""
        print(f"  {icon} {name}{extra}")
    print("-" * 65)
    print(f"  通过: {passed}/{len(results)}")
    print("=" * 65)


if __name__ == "__main__":
    main()
