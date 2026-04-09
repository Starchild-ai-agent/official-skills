"""
Transfer & signing tools — EVM and Solana.
"""

try:
    from .common import is_fly_machine, wallet_request, logger
except ImportError:
    from common import is_fly_machine, wallet_request, logger


async def evm_transfer(
    to: str, amount: str, chain_id: int = 1,
    data: str = "", gas_limit: str = "", gas_price: str = "",
    max_fee_per_gas: str = "", max_priority_fee_per_gas: str = "",
    nonce: str = "", tx_type: int = None,
) -> dict:
    """Sign and BROADCAST an EVM transaction. Gas is sponsored."""
    body = {"to": to, "amount": amount, "chain_id": chain_id}
    if data:
        body["data"] = data
    if gas_limit:
        body["gas_limit"] = gas_limit
    if gas_price:
        body["gas_price"] = gas_price
    if max_fee_per_gas:
        body["max_fee_per_gas"] = max_fee_per_gas
    if max_priority_fee_per_gas:
        body["max_priority_fee_per_gas"] = max_priority_fee_per_gas
    if nonce:
        body["nonce"] = nonce
    if tx_type is not None:
        body["tx_type"] = tx_type
    return await wallet_request("POST", "/agent/transfer", body)


async def evm_sign_transaction(
    to: str, amount: str, chain_id: int = 1,
    data: str = "", gas_limit: str = "", gas_price: str = "",
    max_fee_per_gas: str = "", max_priority_fee_per_gas: str = "",
    nonce: str = "", tx_type: int = None,
) -> dict:
    """Sign an EVM transaction WITHOUT broadcasting."""
    body = {"to": to, "amount": amount, "chain_id": chain_id}
    if data:
        body["data"] = data
    if gas_limit:
        body["gas_limit"] = gas_limit
    if gas_price:
        body["gas_price"] = gas_price
    if max_fee_per_gas:
        body["max_fee_per_gas"] = max_fee_per_gas
    if max_priority_fee_per_gas:
        body["max_priority_fee_per_gas"] = max_priority_fee_per_gas
    if nonce:
        body["nonce"] = nonce
    if tx_type is not None:
        body["tx_type"] = tx_type
    return await wallet_request("POST", "/agent/sign-transaction", body)


async def evm_sign_message(message: str) -> dict:
    """EIP-191 personal_sign."""
    return await wallet_request("POST", "/agent/sign", {"message": message})


async def evm_sign_typed_data(
    domain: dict, types: dict, primaryType: str, message: dict,
) -> dict:
    """Sign EIP-712 structured data."""
    return await wallet_request("POST", "/agent/sign-typed-data", {
        "domain": domain, "types": types,
        "primaryType": primaryType, "message": message,
    })


_CHAIN_NATIVE_ASSET = {
    "ethereum": "eth", "base": "eth", "arbitrum": "eth",
    "optimism": "eth", "linea": "eth",
    "polygon": "pol", "matic": "pol",
    "bnb": "bnb", "bsc": "bnb",
    "avalanche": "avax", "fantom": "ftm",
}

async def evm_transactions(chain: str = "ethereum", asset: str = "", limit: int = 20) -> dict:
    """Get EVM transaction history. Asset auto-detected from chain if empty."""
    if not asset:
        asset = _CHAIN_NATIVE_ASSET.get(chain.lower(), "eth")
    qs = f"?chain_type=ethereum&chain={chain}&asset={asset}&limit={limit}"
    return await wallet_request("GET", f"/agent/transactions{qs}")


# ── Solana ───────────────────────────────────────────────────────────────────

async def sol_transfer(transaction: str, rpc_url: str = "https://api.mainnet-beta.solana.com") -> dict:
    """Sign and BROADCAST a Solana transaction (no gas sponsorship).
    Signs via wallet-service, then broadcasts via Solana RPC.
    """
    import httpx
    # Step 1: sign
    sign_result = await wallet_request("POST", "/agent/sol/sign-transaction", {
        "transaction": transaction,
    })
    signed_tx = sign_result.get("signed_transaction")
    if not signed_tx:
        return {"error": "signing failed", "details": sign_result}
    # Step 2: broadcast via RPC
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
            "params": [signed_tx, {"encoding": "base64"}],
        })
    rpc = resp.json()
    if "error" in rpc:
        return {"error": "broadcast failed", "details": rpc["error"]}
    return {"tx_hash": rpc.get("result"), "signed_transaction": signed_tx}


async def sol_sign_transaction(transaction: str) -> dict:
    """Sign a Solana transaction WITHOUT broadcasting."""
    return await wallet_request("POST", "/agent/sol/sign-transaction", {
        "transaction": transaction,
    })


async def sol_sign_message(message: str) -> dict:
    """Sign a message with Solana wallet (base64)."""
    return await wallet_request("POST", "/agent/sol/sign", {"message": message})


async def sol_transactions(chain: str = "solana", asset: str = "sol", limit: int = 20) -> dict:
    """Get Solana transaction history."""
    qs = f"?chain_type=solana&chain={chain}&asset={asset}&limit={limit}"
    return await wallet_request("GET", f"/agent/transactions{qs}")
