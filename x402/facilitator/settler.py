"""On-chain settlement engine: submits EIP-3009 transferWithAuthorization.

The settlement key ONLY pays gas — it cannot move any user funds. Fund flow
(from/to/value) is fixed by the buyer's signature; a compromised key can at
worst waste its own gas ETH.

Key loading order:
  1. X402_SETTLER_PRIVATE_KEY env (fly.io secret in platform deployment)
  2. key file at {state_dir}/settler.key (0600, local Phase-1 mode; generated
     on first run if missing)
"""
from __future__ import annotations

import json
import os
import threading
import time

from eth_account import Account
from web3 import Web3

# transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)
EIP3009_ABI = json.loads("""[{
  "name": "transferWithAuthorization", "type": "function",
  "stateMutability": "nonpayable",
  "inputs": [
    {"name": "from", "type": "address"}, {"name": "to", "type": "address"},
    {"name": "value", "type": "uint256"}, {"name": "validAfter", "type": "uint256"},
    {"name": "validBefore", "type": "uint256"}, {"name": "nonce", "type": "bytes32"},
    {"name": "v", "type": "uint8"}, {"name": "r", "type": "bytes32"}, {"name": "s", "type": "bytes32"}
  ], "outputs": []
}, {
  "name": "authorizationState", "type": "function", "stateMutability": "view",
  "inputs": [{"name": "authorizer", "type": "address"}, {"name": "nonce", "type": "bytes32"}],
  "outputs": [{"name": "", "type": "bool"}]
}, {
  "name": "balanceOf", "type": "function", "stateMutability": "view",
  "inputs": [{"name": "account", "type": "address"}],
  "outputs": [{"name": "", "type": "uint256"}]
}]""")

RPC_URLS = {
    "eip155:8453": os.environ.get("X402_RPC_BASE", "https://mainnet.base.org"),
    "eip155:84532": os.environ.get("X402_RPC_BASE_SEPOLIA", "https://sepolia.base.org"),
}


class Settler:
    def __init__(self, state_dir: str):
        self._lock = threading.Lock()  # serialize nonce usage
        self._w3_cache: dict[str, Web3] = {}
        key = os.environ.get("X402_SETTLER_PRIVATE_KEY", "").strip()
        if not key:
            key_path = os.path.join(state_dir, "settler.key")
            if os.path.exists(key_path):
                key = open(key_path).read().strip()
            else:
                acct = Account.create()
                key = acct.key.hex()
                os.makedirs(state_dir, exist_ok=True)
                with open(key_path, "w") as f:
                    f.write(key)
                os.chmod(key_path, 0o600)
        self.account = Account.from_key(key)

    @property
    def address(self) -> str:
        return self.account.address

    def w3(self, network: str) -> Web3:
        if network not in self._w3_cache:
            url = RPC_URLS.get(network)
            if not url:
                raise ValueError(f"unsupported network {network}")
            self._w3_cache[network] = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 30}))
        return self._w3_cache[network]

    def gas_balance(self, network: str) -> int:
        return self.w3(network).eth.get_balance(self.address)

    # ------------------------------------------------------------------
    def check_onchain(self, network: str, asset: str, payer: str,
                      value: int, auth_nonce: bytes) -> tuple[bool, str]:
        """Pre-settlement on-chain checks: balance + authorization unused."""
        w3 = self.w3(network)
        token = w3.eth.contract(address=Web3.to_checksum_address(asset), abi=EIP3009_ABI)
        bal = token.functions.balanceOf(Web3.to_checksum_address(payer)).call()
        if bal < value:
            return False, f"insufficient_balance ({bal} < {value})"
        used = token.functions.authorizationState(
            Web3.to_checksum_address(payer), auth_nonce).call()
        if used:
            return False, "authorization_already_used"
        return True, ""

    def settle(self, network: str, asset: str, auth: dict, signature: str) -> dict:
        """Simulate then submit transferWithAuthorization. Returns settlement result."""
        w3 = self.w3(network)
        token = w3.eth.contract(address=Web3.to_checksum_address(asset), abi=EIP3009_ABI)

        sig = bytes.fromhex(signature[2:] if signature.startswith("0x") else signature)
        if len(sig) != 65:
            return {"success": False, "error": "bad_signature_length"}
        r, s, v = sig[:32], sig[32:64], sig[64]
        if v < 27:
            v += 27

        nonce_b = bytes.fromhex(auth["nonce"][2:])
        fn = token.functions.transferWithAuthorization(
            Web3.to_checksum_address(auth["from"]), Web3.to_checksum_address(auth["to"]),
            int(auth["value"]), int(auth["validAfter"]), int(auth["validBefore"]),
            nonce_b, v, r, s)

        with self._lock:
            # 1) mandatory simulation — refuse to spend gas on a failing tx
            try:
                fn.call({"from": self.address})
            except Exception as e:
                return {"success": False, "error": f"simulation_failed: {e}"}

            # 2) build + submit
            try:
                tx_nonce = w3.eth.get_transaction_count(self.address)
                base_fee = w3.eth.get_block("latest").get("baseFeePerGas", w3.to_wei(0.01, "gwei"))
                tx = fn.build_transaction({
                    "from": self.address,
                    "nonce": tx_nonce,
                    "maxFeePerGas": int(base_fee * 2) + w3.to_wei(0.001, "gwei"),
                    "maxPriorityFeePerGas": w3.to_wei(0.001, "gwei"),
                    "gas": 120_000,
                    "chainId": int(network.split(":")[1]),
                })
                signed = self.account.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            except Exception as e:
                return {"success": False, "error": f"submit_failed: {e}"}

        # 3) wait for confirmation (outside nonce lock)
        try:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90)
        except Exception:
            return {"success": False, "error": "confirmation_timeout",
                    "tx_hash": tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)}

        h = receipt.transactionHash.hex()
        if not h.startswith("0x"):
            h = "0x" + h
        return {"success": receipt.status == 1,
                "tx_hash": h,
                "gas_used": receipt.gasUsed,
                "block": receipt.blockNumber,
                "error": None if receipt.status == 1 else "tx_reverted"}
