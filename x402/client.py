"""x402 buyer client — lets THIS agent pay other agents' x402 services.

Uses the user's Privy wallet (via the wallet skill) to sign EIP-3009
payment authorizations. No private key ever touches this process.

Usage (bash):
    python3 skills/x402/client.py GET  https://host/api/thing
    python3 skills/x402/client.py POST https://host/x402/topup '{"json":"body"}'

Or from Python:
    from client import paid_request, PrivySigner
    r = paid_request("GET", url)            # auto-handles 402 -> sign -> retry
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import tempfile

# outbound proxy (facilitator + remote service live outside the container)
_ca = os.environ.get("STARCHILD_API_PROXY_CA_BASE64")
if _ca and not os.environ.get("X402_NO_PROXY"):
    _caf = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    _caf.write(base64.b64decode(_ca)); _caf.close()
    os.environ.setdefault("SSL_CERT_FILE", _caf.name)
    _h, _p = os.environ["STARCHILD_API_PROXY_HOST"], os.environ["STARCHILD_API_PROXY_PORT"]
    _url = f"http://[{_h}]:{_p}" if ":" in _h else f"http://{_h}:{_p}"
    os.environ.setdefault("HTTPS_PROXY", _url); os.environ.setdefault("HTTP_PROXY", _url)
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",127.0.0.1,localhost"


class PrivySigner:
    """ClientEvmSigner backed by the Starchild wallet skill (Privy)."""

    def __init__(self, max_amount_atomic: int = 1_000_000):
        """max_amount_atomic: refuse to sign payments above this (default 1 USDC)."""
        from core.skill_tools import wallet
        self._wallet = wallet
        self.max_amount_atomic = max_amount_atomic
        info = wallet.wallet_info()
        self._address = next(w["wallet_address"] for w in info["wallets"]
                             if w["chain_type"] == "ethereum")

    @property
    def address(self) -> str:
        return self._address

    def sign_typed_data(self, domain, types, primary_type, message) -> bytes:
        # spending guard — hard cap per single signature
        val = int(message.get("value", 0)) if str(message.get("value", "0")).isdigit() else 0
        if val > self.max_amount_atomic:
            raise ValueError(
                f"x402 spend guard: {val} atomic units exceeds cap "
                f"{self.max_amount_atomic}. Raise PrivySigner(max_amount_atomic=...) explicitly.")
        d = {"name": domain.name, "version": domain.version,
             "chainId": domain.chain_id, "verifyingContract": domain.verifying_contract}
        t = {tn: [{"name": f.name, "type": f.type} for f in fields]
             for tn, fields in types.items()}
        # wallet API is JSON — normalize bytes -> 0x hex, int -> str
        msg = {}
        for k, v in message.items():
            if isinstance(v, (bytes, bytearray)):
                msg[k] = "0x" + v.hex()
            elif isinstance(v, int):
                msg[k] = str(v)
            else:
                msg[k] = v
        res = self._wallet.wallet_sign_typed_data(
            domain=d, types=t, primaryType=primary_type, message=msg)
        sig = res.get("signature") if isinstance(res, dict) else None
        if not sig:
            raise RuntimeError(f"wallet signing failed: {res}")
        return bytes.fromhex(sig[2:] if sig.startswith("0x") else sig)


class SessionEOASigner:
    """Local session EOA buyer key (.x402/buyer.key).

    Why this exists: the Privy wallet address carries EIP-7702 delegation code,
    so USDC's transferWithAuthorization verifies its signatures via EIP-1271
    (contract path) and REJECTS plain ECDSA — Privy signatures fail on-chain
    with 'FiatTokenV2: invalid signature'. A plain EOA has no code, signs pure
    ECDSA, and works. Fund it with a small USDC budget from the Privy wallet;
    the budget itself acts as the hard spend cap.
    """

    KEY_PATH = "/data/workspace/.x402/buyer.key"

    def __init__(self, max_amount_atomic: int = 1_000_000):
        from eth_account import Account
        if os.path.exists(self.KEY_PATH):
            self._acct = Account.from_key(open(self.KEY_PATH).read().strip())
        else:
            self._acct = Account.create()
            os.makedirs(os.path.dirname(self.KEY_PATH), exist_ok=True)
            with open(self.KEY_PATH, "w") as f:
                f.write(self._acct.key.hex())
            os.chmod(self.KEY_PATH, 0o600)
        self.max_amount_atomic = max_amount_atomic

    @property
    def address(self) -> str:
        return self._acct.address

    def sign_typed_data(self, domain, types, primary_type, message) -> bytes:
        val = int(message.get("value", 0)) if str(message.get("value", "0")).isdigit() else 0
        if val > self.max_amount_atomic:
            raise ValueError(
                f"x402 spend guard: {val} atomic units exceeds cap {self.max_amount_atomic}.")
        from eth_account.messages import encode_typed_data
        full = {
            "domain": {"name": domain.name, "version": domain.version,
                       "chainId": domain.chain_id,
                       "verifyingContract": domain.verifying_contract},
            "types": {"EIP712Domain": [
                {"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"}],
                **{tn: [{"name": f.name, "type": f.type} for f in fields]
                   for tn, fields in types.items()}},
            "primaryType": primary_type,
            "message": {k: (v if not isinstance(v, str) or not v.isdigit() else int(v))
                        for k, v in message.items()},
        }
        signed = self._acct.sign_message(encode_typed_data(full_message=full))
        return signed.signature


def _build_client(max_amount_atomic: int = 1_000_000, signer_mode: str = "auto"):
    """signer_mode: 'eoa' (session EOA, default for mainnet), 'privy', 'auto'.

    'auto' -> session EOA (works everywhere); Privy direct signing only works
    on chains/tokens that don't hit the EIP-7702/1271 path.
    """
    from x402 import x402Client
    from x402.mechanisms.evm.exact.register import register_exact_evm_client
    if signer_mode == "privy":
        signer = PrivySigner(max_amount_atomic=max_amount_atomic)
    else:
        signer = SessionEOASigner(max_amount_atomic=max_amount_atomic)
    client = x402Client()
    register_exact_evm_client(client, signer)
    return client, signer


def paid_request(method: str, url: str, json_body=None, headers=None,
                 max_amount_atomic: int = 1_000_000, timeout: float = 60.0,
                 signer_mode: str = "auto"):
    """One-shot request with automatic x402 payment. Returns dict summary."""
    from x402.http.clients.httpx import x402HttpxClient

    client, signer = _build_client(max_amount_atomic, signer_mode)

    async def run():
        async with x402HttpxClient(client, timeout=timeout) as c:
            r = await c.request(method.upper(), url, json=json_body, headers=headers or {})
            out = {"status": r.status_code, "payer": signer.address,
                   "body": (r.text[:2000] if r.text else "")}
            pr = r.headers.get("PAYMENT-RESPONSE") or r.headers.get("X-PAYMENT-RESPONSE")
            if pr:
                try:
                    out["settlement"] = json.loads(base64.b64decode(pr))
                except Exception:
                    out["settlement_raw"] = pr[:200]
            return out

    return asyncio.run(run())


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    method, url = sys.argv[1], sys.argv[2]
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    cap = int(os.environ.get("X402_MAX_ATOMIC", "1000000"))
    print(json.dumps(paid_request(method, url, body, max_amount_atomic=cap), indent=2))
