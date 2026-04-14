"""
1inch DEX Aggregator — Native tool exports for agent routing.

Tools registered:
  READ  (7): oneinch_quote, oneinch_tokens, oneinch_check_allowance
             oneinch_cross_chain_quote, oneinch_cross_chain_status
             oneinch_get_orders, oneinch_get_order
  WRITE (5): oneinch_approve, oneinch_swap
             oneinch_cross_chain_swap
             oneinch_create_limit_order, oneinch_cancel_limit_order

All API calls via sc-proxy (credentials auto-injected).
No Fly Machine dependency. Works in any Starchild container.
Cross-chain swap: requests sync path (wallet_sign_typed_data), verified ETH→ARB 2025.
"""

import os
import time

from core.http_client import proxied_get, proxied_post

SC_CALLER_ID = "skill:1inch"

SUPPORTED_CHAINS = {
    "ethereum": 1, "arbitrum": 42161, "base": 8453,
    "optimism": 10, "polygon": 137, "bsc": 56,
    "avalanche": 43114, "gnosis": 100,
}
NATIVE_TOKEN = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
ROUTER_V6 = "0x111111125421cA6dc452d289314280a0f8842A65"
ORDERBOOK_BASE = "https://api.1inch.dev/orderbook/v4.0"
FUSION_BASE = "https://api.1inch.dev/fusion-plus"

# Limit Order Protocol v4 — same address as Router v6
LOP_CONTRACTS = {v: ROUTER_V6 for v in SUPPORTED_CHAINS.values()}


def _chain_id(chain: str) -> int:
    c = chain.lower().strip()
    if c not in SUPPORTED_CHAINS:
        raise ValueError(f"Unknown chain '{chain}'. Supported: {', '.join(sorted(SUPPORTED_CHAINS))}")
    return SUPPORTED_CHAINS[c]


def _api(chain_id: int, path: str, params: dict = None) -> dict:
    url = f"https://api.1inch.dev/swap/v6.0/{chain_id}{path}"
    resp = proxied_get(url, params=params or {}, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        raise Exception(f"1inch API {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _ob_get(chain_id: int, path: str, params: dict = None) -> dict:
    url = f"{ORDERBOOK_BASE}/{chain_id}{path}"
    resp = proxied_get(url, params=params or {}, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        raise Exception(f"Orderbook API {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _ob_post(chain_id: int, path: str, body: dict) -> dict:
    url = f"{ORDERBOOK_BASE}/{chain_id}{path}"
    resp = proxied_post(url, json=body, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        raise Exception(f"Orderbook API {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _get_wallet_address() -> str:
    """Get agent EVM address from platform wallet."""
    try:
        from tools.wallet import wallet_info
        info = wallet_info()
        for w in (info if isinstance(info, list) else info.get("wallets", [])):
            if w.get("chain_type") == "ethereum":
                return w["wallet_address"]
    except Exception:
        pass
    return ""


# ══════════════════════════════════════════════════════════════════════════════
# SAME-CHAIN SWAP TOOLS
# ══════════════════════════════════════════════════════════════════════════════

def oneinch_quote(chain: str, src: str, dst: str, amount: str) -> dict:
    """Get a swap price quote from 1inch DEX aggregator (read-only, no tx sent).

    Returns estimated output amount and route info WITHOUT executing a swap.
    Use before swapping to check rates. Token addresses must be checksummed ERC-20 addresses.

    Args:
        chain: Network name — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        src: Source token address (use 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE for native ETH)
        dst: Destination token address
        amount: Amount in wei (1 USDC = 1000000, 1 ETH = 1000000000000000000)
    """
    cid = _chain_id(chain)
    data = _api(cid, "/quote", {"src": src, "dst": dst, "amount": amount})
    return {
        "chain": chain,
        "src": src, "dst": dst,
        "srcAmount": amount,
        "dstAmount": data.get("dstAmount", "0"),
        "gas": data.get("gas"),
        "protocols": data.get("protocols", []),
    }


def oneinch_tokens(chain: str, search: str = "") -> dict:
    """Search or list supported tokens on a network via 1inch.

    Use to find token contract addresses before quoting or swapping.
    Token addresses differ between networks.

    Args:
        chain: Network name — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        search: Filter by token name or symbol (case-insensitive). Omit to list popular tokens.
    """
    cid = _chain_id(chain)
    data = _api(cid, "/tokens")
    token_map = data.get("tokens", data) if isinstance(data, dict) else data
    tokens = list(token_map.values()) if isinstance(token_map, dict) else token_map

    if search:
        q = search.lower()
        tokens = [t for t in tokens if q in t.get("symbol", "").lower() or q in t.get("name", "").lower()]

    result = [
        {"address": t.get("address"), "symbol": t.get("symbol"),
         "name": t.get("name"), "decimals": t.get("decimals")}
        for t in tokens[:20]
    ]
    return {"chain": chain, "tokens": result, "count": len(result)}


def oneinch_check_allowance(chain: str, token_address: str, wallet_address: str = "") -> dict:
    """Check if a token has sufficient allowance for the 1inch router.

    Native ETH does not need approval. ERC-20 tokens must be approved before swapping.

    Args:
        chain: Network name — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        token_address: ERC-20 token address to check
        wallet_address: Wallet to check (uses agent wallet if omitted)
    """
    if token_address.lower() == NATIVE_TOKEN.lower():
        return {"allowance": "unlimited", "needs_approval": False, "note": "Native ETH needs no approval"}

    cid = _chain_id(chain)
    if not wallet_address:
        wallet_address = _get_wallet_address()
    if not wallet_address:
        return {"error": "wallet_address required"}

    data = _api(cid, "/approve/allowance", {
        "tokenAddress": token_address,
        "walletAddress": wallet_address,
    })
    allowance = data.get("allowance", "0")
    return {
        "chain": chain, "token": token_address, "wallet": wallet_address,
        "allowance": allowance, "needs_approval": allowance == "0",
    }


def oneinch_approve(chain: str, token_address: str, amount: str = "") -> dict:
    """Approve an ERC-20 token for the 1inch router (on-chain tx).

    Required before swapping ERC-20 tokens (not needed for native ETH).
    Sends approval transaction via agent wallet (wallet_sign_transaction).

    Args:
        chain: Network name — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        token_address: ERC-20 token address to approve
        amount: Amount to approve in wei (omit for unlimited approval)
    """
    cid = _chain_id(chain)
    params = {"tokenAddress": token_address}
    if amount:
        params["amount"] = amount
    tx_data = _api(cid, "/approve/transaction", params)

    try:
        from tools.wallet import wallet_sign_transaction
        result = wallet_sign_transaction({
            "to": tx_data["to"],
            "data": tx_data.get("data", "0x"),
            "value": tx_data.get("value", "0"),
            "chain_id": cid,
        })
        return {"status": "approval_sent", "chain": chain, "token": token_address, "tx": result}
    except Exception as e:
        return {"error": str(e), "tx_data": tx_data}


def oneinch_swap(chain: str, src: str, dst: str, amount: str, slippage: float = 1.0) -> dict:
    """Execute a token swap via 1inch DEX aggregator (on-chain tx).

    1inch finds the best route across 200+ DEXes and executes the swap.
    For ERC-20 src tokens, check allowance first with oneinch_check_allowance.
    Native ETH swaps do not need approval.

    Args:
        chain: Network name — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        src: Source token address (0xEeee...EEeE for native ETH)
        dst: Destination token address
        amount: Amount in wei
        slippage: Slippage tolerance in percent (default 1.0)
    """
    cid = _chain_id(chain)
    wallet_address = _get_wallet_address()
    if not wallet_address:
        return {"error": "No ethereum wallet configured"}

    swap_data = _api(cid, "/swap", {
        "src": src, "dst": dst, "amount": amount,
        "from": wallet_address, "slippage": str(slippage),
    })

    tx = swap_data.get("tx", {})
    if not tx:
        return {"error": "1inch returned no transaction data", "raw": swap_data}

    try:
        from tools.wallet import wallet_sign_transaction
        result = wallet_sign_transaction({
            "to": tx["to"],
            "data": tx.get("data", "0x"),
            "value": tx.get("value", "0"),
            "chain_id": cid,
        })
        return {
            "status": "swap_sent", "chain": chain,
            "src": src, "dst": dst,
            "srcAmount": amount, "dstAmount": swap_data.get("dstAmount"),
            "tx": result,
        }
    except Exception as e:
        err = str(e)
        if "policy" in err.lower():
            return {"error": f"Policy violation: {err}. Use wallet_propose_policy to allow this swap."}
        return {"error": err}


# ══════════════════════════════════════════════════════════════════════════════
# CROSS-CHAIN SWAP TOOLS (Fusion+)
# ══════════════════════════════════════════════════════════════════════════════

def oneinch_cross_chain_quote(
    src_chain: str, dst_chain: str,
    src_token: str, dst_token: str, amount: str
) -> dict:
    """Get a cross-chain swap quote via 1inch Fusion+ (read-only).

    Returns estimated output for swapping tokens across different chains
    (e.g., ETH on Ethereum → USDC on Arbitrum). No transaction executed.
    Fusion+ is intent-based — resolvers handle gas on both chains.

    Args:
        src_chain: Source network — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        dst_chain: Destination network — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        src_token: Source token address on the source chain
        dst_token: Destination token address on the destination chain
        amount: Amount in wei
    """
    src_id = _chain_id(src_chain)
    dst_id = _chain_id(dst_chain)
    if src_id == dst_id:
        return {"error": f"Same chain ({src_chain}). Use oneinch_quote for same-chain swaps."}

    wallet = _get_wallet_address() or "0x0000000000000000000000000000000000000000"
    url = f"{FUSION_BASE}/quoter/v1.0/{src_id}/quote/receive"
    resp = proxied_get(url, params={
        "srcChainId": src_id, "dstChainId": dst_id,
        "srcTokenAddress": src_token, "dstTokenAddress": dst_token,
        "amount": amount, "walletAddress": wallet,
        "enableEstimate": "true",
    }, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        return {"error": f"Fusion+ API {resp.status_code}: {resp.text[:300]}"}
    return resp.json()


def oneinch_cross_chain_status(order_hash: str) -> dict:
    """Check the status of a Fusion+ cross-chain swap order.

    Args:
        order_hash: The order hash returned from oneinch_cross_chain_swap
    """
    if not order_hash:
        return {"error": "order_hash required"}
    url = f"{FUSION_BASE}/orders/v1.0/order/status/{order_hash}"
    resp = proxied_get(url, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        return {"error": f"Fusion+ API {resp.status_code}: {resp.text[:300]}"}
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# LIMIT ORDER TOOLS (Orderbook)
# ══════════════════════════════════════════════════════════════════════════════

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


def _maker_traits(expiry_seconds: int = 0, allow_partial: bool = True) -> int:
    traits = 0
    if not allow_partial:
        traits |= (1 << 255)
    if expiry_seconds > 0:
        expiry_ts = int(time.time()) + expiry_seconds
        traits |= ((expiry_ts & 0xFFFFFFFFFF) << 80)
    return traits


def oneinch_get_orders(chain: str, wallet_address: str = "", page: int = 1, limit: int = 10) -> dict:
    """Get open limit orders on 1inch Orderbook for a wallet.

    Args:
        chain: Network name — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        wallet_address: Wallet to query (defaults to agent wallet)
        page: Page number (default: 1)
        limit: Results per page (default: 10, max: 100)
    """
    cid = _chain_id(chain)
    if not wallet_address:
        wallet_address = _get_wallet_address()
    if not wallet_address:
        return {"error": "wallet_address required"}
    data = _ob_get(cid, f"/address/{wallet_address}", {
        "page": page, "limit": min(limit, 100), "sortBy": "createDateTime",
    })
    return {"chain": chain, "wallet": wallet_address, "orders": data}


def oneinch_get_order(chain: str, order_hash: str) -> dict:
    """Get a specific limit order by hash on 1inch Orderbook.

    Args:
        chain: Network name — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        order_hash: The order hash
    """
    cid = _chain_id(chain)
    return _ob_get(cid, f"/{order_hash}")


def oneinch_create_limit_order(
    chain: str,
    maker_asset: str, taker_asset: str,
    making_amount: str, taking_amount: str,
    expiry_seconds: int = 86400,
    allow_partial_fill: bool = True,
) -> dict:
    """Create and submit a limit order on 1inch Orderbook.

    Signs an EIP-712 order off-chain and submits it to 1inch Orderbook.
    Resolvers fill it when market price matches your target.

    Before creating: check allowance with oneinch_check_allowance,
    approve if needed with oneinch_approve.

    Args:
        chain: Network name — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        maker_asset: Token address you are selling
        taker_asset: Token address you want to receive
        making_amount: Amount of maker_asset to sell, in wei
        taking_amount: Minimum amount of taker_asset to receive, in wei
        expiry_seconds: Order validity in seconds (default: 86400 = 24h, 0 = no expiry)
        allow_partial_fill: Allow partial fills (default: True)
    """
    cid = _chain_id(chain)
    contract = LOP_CONTRACTS.get(cid)
    if not contract:
        return {"error": f"Limit orders not supported on chain {chain}"}

    wallet_address = _get_wallet_address()
    if not wallet_address:
        return {"error": "No ethereum wallet configured"}

    salt = int.from_bytes(os.urandom(32), "big")
    traits = _maker_traits(expiry_seconds, allow_partial_fill)

    order_struct = {
        "salt": str(salt),
        "maker": wallet_address,
        "receiver": "0x0000000000000000000000000000000000000000",
        "makerAsset": maker_asset,
        "takerAsset": taker_asset,
        "makingAmount": str(making_amount),
        "takingAmount": str(taking_amount),
        "makerTraits": str(traits),
    }

    typed_data_message = {
        "salt": salt,
        "maker": wallet_address,
        "receiver": "0x0000000000000000000000000000000000000000",
        "makerAsset": maker_asset,
        "takerAsset": taker_asset,
        "makingAmount": int(making_amount),
        "takingAmount": int(taking_amount),
        "makerTraits": traits,
    }

    try:
        from tools.wallet import wallet_sign_typed_data
        sig_result = wallet_sign_typed_data(
            domain={
                "name": "1inch Aggregation Router",
                "version": "6",
                "chainId": cid,
                "verifyingContract": contract,
            },
            types=ORDER_TYPES,
            primary_type="Order",
            message=typed_data_message,
        )
        signature = sig_result.get("signature", "")
        if not signature:
            return {"error": f"Wallet sign failed: {sig_result}"}

        result = _ob_post(cid, "", {"signature": signature, "data": order_struct})
        return {
            "status": "order_submitted",
            "chain": chain,
            "order_hash": result.get("orderHash", result.get("hash", "")),
            "maker_asset": maker_asset, "taker_asset": taker_asset,
            "making_amount": making_amount, "taking_amount": taking_amount,
            "expiry_seconds": expiry_seconds,
            "raw": result,
        }
    except Exception as e:
        err = str(e)
        if "policy" in err.lower():
            return {"error": f"Policy violation: {err}. Use wallet_propose_policy to allow signing."}
        return {"error": err}


def oneinch_cancel_limit_order(chain: str, order_hash: str) -> dict:
    """Cancel a limit order on-chain via 1inch Limit Order Protocol.

    Sends an on-chain cancellation transaction. Requires gas.

    Args:
        chain: Network name — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        order_hash: The order hash to cancel
    """
    cid = _chain_id(chain)
    contract = LOP_CONTRACTS.get(cid)
    if not contract:
        return {"error": f"Limit orders not supported on chain {chain}"}

    try:
        # Fetch order to get makerTraits
        order_data = _ob_get(cid, f"/{order_hash}")
        order_struct = order_data.get("data", {})
        if not order_struct:
            return {"error": f"Order {order_hash} not found"}

        maker_traits = int(order_struct.get("makerTraits", "0"))
        order_hash_bytes = bytes.fromhex(order_hash.replace("0x", "").zfill(64))

        # cancelOrder(uint256 makerTraits, bytes32 orderHash)
        selector = bytes.fromhex("2b155166")
        calldata = selector + maker_traits.to_bytes(32, "big") + order_hash_bytes

        from tools.wallet import wallet_sign_transaction
        result = wallet_sign_transaction({
            "to": contract,
            "data": "0x" + calldata.hex(),
            "value": "0",
            "chain_id": cid,
        })
        return {"status": "cancel_sent", "order_hash": order_hash, "tx": result}
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# CROSS-CHAIN SWAP EXECUTION (Fusion+)
# ══════════════════════════════════════════════════════════════════════════════

def _fusion_get(path: str, params: dict = None) -> dict:
    """Fusion+ API GET via sc-proxy."""
    url = f"https://api.1inch.com/fusion-plus{path}"
    resp = proxied_get(url, params=params or {}, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        raise RuntimeError(f"Fusion+ GET {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _fusion_post(path: str, body: dict, params: dict = None) -> dict:
    """Fusion+ API POST via sc-proxy."""
    url = f"https://api.1inch.com/fusion-plus{path}"
    resp = proxied_post(url, json=body, params=params or {}, headers={"SC-CALLER-ID": SC_CALLER_ID})
    if resp.status_code >= 400:
        raise RuntimeError(f"Fusion+ POST {resp.status_code}: {resp.text[:300]}")
    text = resp.text.strip()
    return resp.json() if text else {}


def _generate_secrets(count: int) -> list:
    return [os.urandom(32) for _ in range(count)]


def _hash_secret(secret: bytes) -> str:
    try:
        from eth_utils import keccak
        return "0x" + keccak(secret).hex()
    except ImportError:
        import hashlib
        return "0x" + hashlib.sha3_256(secret).hexdigest()


def _normalize_v(signature: str) -> str:
    sig_hex = signature.replace("0x", "")
    if len(sig_hex) == 130:
        v = int(sig_hex[-2:], 16)
        if v < 27:
            signature = "0x" + sig_hex[:-2] + format(v + 27, "02x")
    return signature


def oneinch_cross_chain_swap(
    src_chain: str, dst_chain: str,
    src_token: str, dst_token: str,
    amount: str, preset: str = "medium"
) -> dict:
    """Execute a cross-chain token swap via 1inch Fusion+ (intent-based atomic swap).

    Fusion+ is gasless on the destination chain — resolvers handle gas on both sides.
    Uses requests sync path + wallet_sign_typed_data (verified ETH→ARB, ~76s settlement).

    Flow: quote → generate secrets → build order → sign EIP-712 → submit → poll → reveal secrets.

    ⚠️ Polling up to 5 minutes. For long waits, use sessions_spawn for background execution.

    Args:
        src_chain: Source network — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        dst_chain: Destination network — ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis
        src_token: Source token address on source chain
        dst_token: Destination token address on destination chain
        amount: Amount in wei (e.g. 2 USDC = "2000000")
        preset: Speed — "fast", "medium" (default), or "slow"
    """
    src_id = _chain_id(src_chain)
    dst_id = _chain_id(dst_chain)
    if src_id == dst_id:
        return {"error": f"Same chain ({src_chain}). Use oneinch_swap for same-chain swaps."}
    if preset not in ("fast", "medium", "slow"):
        return {"error": f"Invalid preset '{preset}'. Use: fast, medium, slow"}

    wallet_address = _get_wallet_address()
    if not wallet_address:
        return {"error": "No ethereum wallet configured"}

    src_token = src_token.lower()
    dst_token = dst_token.lower()

    try:
        # 1. Quote
        quote = _fusion_get("/quoter/v1.1/quote/receive", {
            "srcChain": str(src_id),
            "dstChain": str(dst_id),
            "srcTokenAddress": src_token,
            "dstTokenAddress": dst_token,
            "amount": amount,
            "walletAddress": wallet_address,
            "enableEstimate": "true",
        })
        quote_id = quote.get("quoteId", "")
        if not quote_id:
            return {"error": "Quote missing quoteId — ensure enableEstimate=true"}
        dst_amount_est = quote.get("dstTokenAmount", "")
        presets_data = quote.get("presets", {})
        preset_info = presets_data.get(preset, presets_data.get("medium", {}))
        secrets_count = preset_info.get("secretsCount", 1)

        # 2. Generate secrets
        secrets = _generate_secrets(secrets_count)
        secret_hashes = [_hash_secret(s) for s in secrets]

        # 3. Build order
        build_result = _fusion_post(
            "/quoter/v1.1/quote/build/evm",
            body={"secretsHashList": secret_hashes, "preset": preset},
            params={"quoteId": quote_id},
        )
        order_hash = build_result.get("orderHash", "")
        typed_data = build_result.get("typedData", {})
        extension = build_result.get("extension", "")
        build_tx = build_result.get("transaction")
        build_signature = build_result.get("signature")

        if not typed_data:
            return {"error": "Build API returned no typedData", "build_keys": list(build_result.keys())}

        # 4. Sign
        if build_tx:
            # Native ETH flow: execute deposit tx, use pre-computed signature
            from tools.wallet import wallet_sign_transaction
            tx_result = wallet_sign_transaction({
                "to": build_tx.get("to", ""),
                "value": str(build_tx.get("value", "0")),
                "chain_id": src_id,
                "data": build_tx.get("data", ""),
            })
            if not build_signature:
                return {"error": "Build API returned transaction but no pre-computed signature"}
            signature = build_signature
        else:
            # ERC-20 flow: sign EIP-712 typed data
            from tools.wallet import wallet_sign_typed_data
            sig_result = wallet_sign_typed_data(
                domain=typed_data.get("domain", {}),
                types=typed_data.get("types", {}),
                primary_type=typed_data.get("primaryType", ""),
                message=typed_data.get("message", {}),
            )
            signature = sig_result.get("signature", "")
            if not signature:
                return {"error": f"Wallet returned no signature: {sig_result}"}

        signature = _normalize_v(signature)

        # 5. Submit
        submit_payload = {
            "order": typed_data.get("message", {}),
            "signature": signature,
            "quoteId": quote_id,
            "extension": extension,
            "srcChainId": src_id,
        }
        if secrets_count > 1:
            submit_payload["secretHashes"] = secret_hashes

        submit_result = _fusion_post("/relayer/v1.1/submit", submit_payload)
        order_hash = submit_result.get("orderHash", order_hash)

        if not order_hash:
            return {"error": "Order submission returned no order hash"}

        # 6. Poll (max 5 min)
        MAX_POLL = 300
        INTERVAL = 15
        revealed = set()
        start = time.time()

        while time.time() - start < MAX_POLL:
            # Reveal secrets if fills ready
            if len(revealed) < secrets_count:
                try:
                    fills = _fusion_get(f"/orders/v1.1/order/ready-to-accept-secret-fills/{order_hash}")
                    for fill in fills.get("fills", []):
                        idx = fill.get("idx", 0)
                        if idx not in revealed and idx < len(secrets):
                            _fusion_post("/relayer/v1.1/submit/secret", {
                                "orderHash": order_hash,
                                "secret": "0x" + secrets[idx].hex(),
                            })
                            revealed.add(idx)
                except Exception:
                    pass

            # Check status
            try:
                status = _fusion_get(f"/orders/v1.1/order/status/{order_hash}")
                order_status = status.get("status", "").lower()
                if order_status in ("executed", "expired", "refunded", "cancelled"):
                    return {
                        "status": order_status,
                        "order_hash": order_hash,
                        "src_chain": src_chain, "dst_chain": dst_chain,
                        "src_token": src_token, "dst_token": dst_token,
                        "src_amount": amount,
                        "dst_amount": status.get("dstAmount", status.get("takingAmount", dst_amount_est)),
                        "secrets_revealed": len(revealed),
                        "elapsed_seconds": int(time.time() - start),
                    }
            except Exception:
                pass

            time.sleep(INTERVAL)

        # Timeout — order is submitted, just didn't confirm in time
        return {
            "status": "submitted_polling_timeout",
            "order_hash": order_hash,
            "src_chain": src_chain, "dst_chain": dst_chain,
            "src_amount": amount, "dst_amount_estimate": dst_amount_est,
            "message": f"Order submitted but did not confirm within {MAX_POLL}s. "
                       "Use oneinch_cross_chain_status(order_hash) to check later.",
        }

    except Exception as e:
        err = str(e)
        if "policy" in err.lower():
            return {"error": f"Policy violation: {err}. Use wallet_propose_policy to allow this operation."}
        return {"error": err}
