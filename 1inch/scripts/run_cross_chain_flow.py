#!/usr/bin/env python3
"""
1inch Fusion+ 跨链 Swap 流程脚本
使用 requests 同步路径（与 run_swap_flow.py 保持一致）

用法:
  python3 run_cross_chain_flow.py \
    --src-chain ethereum --dst-chain arbitrum \
    --src-token 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 \
    --dst-token 0xaf88d065e77c8cc2239327c5edb3a432268e5831 \
    --amount 2000000 \
    --preset medium
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List

import requests

from _oneinch_lib import (
    get_evm_wallet_address,
    wallet_request,
    _build_requests_proxies,
    _require_env,
)

# ── Constants ─────────────────────────────────────────────────────────────────

SUPPORTED_CHAINS = {
    "ethereum": 1,
    "arbitrum": 42161,
    "base": 8453,
    "optimism": 10,
    "polygon": 137,
    "bsc": 56,
    "avalanche": 43114,
    "gnosis": 100,
}

FUSION_API_BASE = "https://api.1inch.com/fusion-plus"
MAX_POLL_TIME = 300   # 5 minutes
POLL_INTERVAL = 15    # seconds

# ── Helpers ───────────────────────────────────────────────────────────────────

def fusion_get(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    api_key = _require_env("ONEINCH_API_KEY")
    url = f"{FUSION_API_BASE}{path}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    proxies = _build_requests_proxies(require_proxy=True, service_name="1inch Fusion+")
    resp = requests.get(url, params=params or {}, headers=headers, timeout=30, proxies=proxies)
    if resp.status_code >= 400:
        raise RuntimeError(f"Fusion+ GET {resp.status_code}: {resp.text}")
    return resp.json()


def fusion_post(path: str, body: Dict[str, Any], params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    api_key = _require_env("ONEINCH_API_KEY")
    url = f"{FUSION_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    proxies = _build_requests_proxies(require_proxy=True, service_name="1inch Fusion+")
    resp = requests.post(url, json=body, params=params or {}, headers=headers, timeout=30, proxies=proxies)
    if resp.status_code >= 400:
        raise RuntimeError(f"Fusion+ POST {resp.status_code}: {resp.text}")
    text = resp.text.strip()
    return resp.json() if text else {}


def generate_secrets(count: int) -> List[bytes]:
    return [os.urandom(32) for _ in range(count)]


def hash_secret(secret: bytes) -> str:
    from eth_utils import keccak
    return "0x" + keccak(secret).hex()


def sign_typed_data(typed_data: Dict[str, Any]) -> str:
    """Sign EIP-712 typed data via platform wallet (requests path)."""
    payload = {
        "domain": typed_data.get("domain", {}),
        "types": typed_data.get("types", {}),
        "primaryType": typed_data.get("primaryType", ""),
        "message": typed_data.get("message", {}),
    }
    result = wallet_request("POST", "/agent/sign-typed-data", json_body=payload)
    sig = result.get("signature", result.get("data", ""))
    if not sig:
        raise RuntimeError(f"No signature returned: {result}")
    return sig


def normalize_v(signature: str) -> str:
    """Ensure signature v = 27 or 28 (some wallets return 0/1)."""
    sig_hex = signature.replace("0x", "")
    if len(sig_hex) == 130:
        v = int(sig_hex[-2:], 16)
        if v < 27:
            signature = "0x" + sig_hex[:-2] + format(v + 27, "02x")
    return signature


# ── Main Flow ─────────────────────────────────────────────────────────────────

def run(
    src_chain: str,
    dst_chain: str,
    src_token: str,
    dst_token: str,
    amount: str,
    preset: str = "medium",
):
    src_chain_id = SUPPORTED_CHAINS[src_chain]
    dst_chain_id = SUPPORTED_CHAINS[dst_chain]

    print("=" * 60)
    print("🔗 1inch Fusion+ 跨链 Swap")
    print(f"   {src_chain.upper()} → {dst_chain.upper()}")
    print(f"   amount: {int(amount)/1e6:.2f} USDC  |  preset: {preset}")
    print("=" * 60)

    # 1. 钱包地址
    print("\n[1/6] 获取钱包地址...")
    wallet_address = get_evm_wallet_address()
    print(f"  ✅ {wallet_address}")

    # 2. 报价
    print(f"\n[2/6] 报价...")
    quote = fusion_get("/quoter/v1.1/quote/receive", {
        "srcChain": str(src_chain_id),
        "dstChain": str(dst_chain_id),
        "srcTokenAddress": src_token.lower(),
        "dstTokenAddress": dst_token.lower(),
        "amount": amount,
        "walletAddress": wallet_address,
        "enableEstimate": "true",
    })

    quote_id = quote.get("quoteId", "")
    dst_amount = quote.get("dstTokenAmount", "N/A")
    presets_data = quote.get("presets", {})
    preset_info = presets_data.get(preset, presets_data.get("medium", {}))
    secrets_count = preset_info.get("secretsCount", 1)

    print(f"  ✅ quoteId: {quote_id[:24]}...")
    print(f"  ✅ 预计收到: {int(dst_amount)/1e6:.4f} USDC" if dst_amount != "N/A" else f"  dst: {dst_amount}")
    print(f"  ✅ secretsCount: {secrets_count}")

    # 3. 生成 secrets
    print(f"\n[3/6] 生成 secrets ({secrets_count}个)...")
    secrets = generate_secrets(secrets_count)
    secret_hashes = [hash_secret(s) for s in secrets]
    print(f"  ✅ hashes: {[h[:12]+'...' for h in secret_hashes]}")

    # 4. Build order
    print(f"\n[4/6] Build order...")
    build_result = fusion_post(
        "/quoter/v1.1/quote/build/evm",
        body={"secretsHashList": secret_hashes, "preset": preset},
        params={"quoteId": quote_id},
    )

    order_hash = build_result.get("orderHash", "")
    typed_data = build_result.get("typedData", {})
    extension = build_result.get("extension", "")
    build_tx = build_result.get("transaction")

    print(f"  ✅ orderHash: {order_hash}")
    print(f"  ✅ extension: {len(extension)} chars")
    print(f"  ℹ️  native ETH flow: {build_tx is not None}")

    if not typed_data:
        print(f"  ❌ build_result keys: {list(build_result.keys())}")
        sys.exit(1)

    # 5. 签名
    print(f"\n[5/6] EIP-712 签名...")
    if build_tx:
        # Native ETH: 执行 deposit tx，使用 build API 预计算 signature
        tx_to = build_tx.get("to", "")
        tx_data = build_tx.get("data", "")
        tx_value = str(build_tx.get("value", "0"))
        tx_result = wallet_request("POST", "/agent/transfer", {
            "chain_id": src_chain_id,
            "to": tx_to,
            "value": tx_value,
            "data": tx_data,
        })
        print(f"  ✅ deposit tx: {tx_result.get('tx_hash', tx_result)}")
        signature = build_result.get("signature", "")
    else:
        # ERC-20: 用 EIP-712 签名
        signature = sign_typed_data(typed_data)

    signature = normalize_v(signature)
    print(f"  ✅ sig: {signature[:20]}...{signature[-8:]}")

    # 6. 提交
    print(f"\n[6/6] 提交订单...")
    submit_payload = {
        "order": typed_data.get("message", {}),
        "signature": signature,
        "quoteId": quote_id,
        "extension": extension,
        "srcChainId": src_chain_id,
    }
    if secrets_count > 1:
        submit_payload["secretHashes"] = secret_hashes

    result = fusion_post("/relayer/v1.1/submit", submit_payload)
    order_hash = result.get("orderHash", order_hash)

    print(f"\n{'='*60}")
    print(f"✅ 订单已提交!")
    print(f"   order_hash : {order_hash}")
    print(f"   src        : {int(amount)/1e6:.2f} USDC ({src_chain})")
    print(f"   dst        : ~{int(dst_amount)/1e6:.4f} USDC ({dst_chain})" if dst_amount != "N/A" else f"   dst: USDC ({dst_chain})")
    print(f"   撮合时间   : 1-3 分钟 (失败自动退款)")
    print(f"{'='*60}\n")

    # 持久化 order 信息
    order_file = os.path.join(os.path.dirname(__file__), "../../../output/cross_chain_order.json")
    os.makedirs(os.path.dirname(order_file), exist_ok=True)
    with open(order_file, "w") as f:
        json.dump({
            "order_hash": order_hash,
            "secrets": [s.hex() for s in secrets],
            "secret_hashes": secret_hashes,
            "src_chain": src_chain,
            "dst_chain": dst_chain,
            "src_token": src_token,
            "dst_token": dst_token,
            "amount": amount,
            "dst_amount_estimate": dst_amount,
            "submitted_at": time.time(),
        }, f, indent=2)
    print(f"📁 order 已保存: output/cross_chain_order.json")

    # ── 轮询状态 ──────────────────────────────────────────────────────────────
    print(f"\n⏳ 开始轮询 (最长 {MAX_POLL_TIME}s)...")
    revealed = set()
    start = time.time()

    while time.time() - start < MAX_POLL_TIME:
        # 检查可揭示的 secret
        if len(revealed) < secrets_count:
            try:
                fills = fusion_get(f"/orders/v1.1/order/ready-to-accept-secret-fills/{order_hash}")
                for fill in fills.get("fills", []):
                    idx = fill.get("idx", 0)
                    if idx not in revealed and idx < len(secrets):
                        secret_hex = "0x" + secrets[idx].hex()
                        fusion_post("/relayer/v1.1/submit/secret", {
                            "orderHash": order_hash,
                            "secret": secret_hex,
                        })
                        revealed.add(idx)
                        print(f"  🔑 secret[{idx}] 已揭示")
            except Exception as e:
                pass  # 正常

        # 查订单状态
        try:
            status = fusion_get(f"/orders/v1.1/order/status/{order_hash}")
            order_status = status.get("status", "").lower()
            elapsed = int(time.time() - start)
            print(f"  [{elapsed:3d}s] status: {order_status}")

            if order_status in ("executed", "expired", "refunded", "cancelled"):
                print(f"\n{'='*60}")
                if order_status == "executed":
                    dst_received = status.get("dstAmount", status.get("takingAmount", "?"))
                    print(f"✅ 跨链 Swap 成功!")
                    print(f"   dst 收到: {int(dst_received)/1e6:.4f} USDC ({dst_chain})")
                else:
                    print(f"❌ 订单状态: {order_status} (已自动退款)")
                print(f"   order_hash: {order_hash}")
                print(f"{'='*60}")
                return order_hash, order_status

        except Exception as e:
            print(f"  ⚠️  状态查询失败: {e}")

        time.sleep(POLL_INTERVAL)

    print(f"\n⏰ 超时 ({MAX_POLL_TIME}s)，请用 order_hash 手动查询:")
    print(f"   order_hash: {order_hash}")
    return order_hash, "timeout"


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="1inch Fusion+ 跨链 Swap")
    parser.add_argument("--src-chain", default="ethereum")
    parser.add_argument("--dst-chain", default="arbitrum")
    parser.add_argument("--src-token", default="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")  # USDC ETH
    parser.add_argument("--dst-token", default="0xaf88d065e77c8cc2239327c5edb3a432268e5831")  # USDC ARB
    parser.add_argument("--amount", default="2000000")  # 2 USDC
    parser.add_argument("--preset", default="medium", choices=["fast", "medium", "slow"])
    args = parser.parse_args()

    if args.src_chain not in SUPPORTED_CHAINS:
        print(f"❌ src_chain 不支持: {args.src_chain}")
        sys.exit(1)
    if args.dst_chain not in SUPPORTED_CHAINS:
        print(f"❌ dst_chain 不支持: {args.dst_chain}")
        sys.exit(1)

    run(
        src_chain=args.src_chain,
        dst_chain=args.dst_chain,
        src_token=args.src_token,
        dst_token=args.dst_token,
        amount=args.amount,
        preset=args.preset,
    )
