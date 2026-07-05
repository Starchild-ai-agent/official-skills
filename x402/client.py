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


def _sign_platform_payment(accepts: dict, max_amount_atomic: int) -> str:
    """Sign an EIP-3009 authorization for a platform-shape 402 (JSON-body
    `accepts` dict with pricingModel — Starchild community-gateway contract).
    Returns the base64 X-PAYMENT header value. Session EOA only."""
    import time as _t

    from eth_account.messages import encode_typed_data

    signer = SessionEOASigner(max_amount_atomic=max_amount_atomic)
    amount = int(accepts["amount"])
    if amount > max_amount_atomic:
        raise ValueError(f"x402 spend guard: {amount} atomic units exceeds cap {max_amount_atomic}.")
    network = accepts["network"]
    chain_id = int(network.split(":")[1])
    extra = accepts.get("extra") or {}
    now = int(_t.time())
    auth = {
        "from": signer.address,
        "to": accepts["payTo"],
        "value": str(amount),
        "validAfter": "0",
        "validBefore": str(now + int(accepts.get("maxTimeoutSeconds", 300))),
        "nonce": "0x" + os.urandom(32).hex(),
    }
    typed = {
        "domain": {"name": extra.get("name", "USD Coin"), "version": extra.get("version", "2"),
                   "chainId": chain_id, "verifyingContract": accepts["asset"]},
        "types": {"EIP712Domain": [
            {"name": "name", "type": "string"}, {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"}],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"}, {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"}, {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"}, {"name": "nonce", "type": "bytes32"}]},
        "primaryType": "TransferWithAuthorization",
        "message": {"from": auth["from"], "to": auth["to"], "value": amount,
                    "validAfter": 0, "validBefore": int(auth["validBefore"]),
                    "nonce": auth["nonce"]},
    }
    sig = signer._acct.sign_message(encode_typed_data(full_message=typed)).signature
    payload = {"x402Version": 2, "scheme": "exact", "network": network,
               "payload": {"authorization": auth, "signature": "0x" + sig.hex()}}
    return base64.b64encode(json.dumps(payload).encode()).decode()


def paid_request(method: str, url: str, json_body=None, headers=None,
                 max_amount_atomic: int = 1_000_000, timeout: float = 60.0,
                 signer_mode: str = "auto"):
    """One-shot request with automatic x402 payment. Returns dict summary.

    Handles BOTH 402 flavors:
      * V2 header challenge (PAYMENT-REQUIRED) — x402 SDK path
      * platform JSON-body challenge ({x402Version, accepts:{...pricingModel}})
        — Starchild community-gateway contract; signs EIP-3009 manually and
        retries with the X-PAYMENT header. For lifetime/monthly the signature
        is reusable within its validity window (verify does not consume the
        nonce; only settle does).
    """
    import httpx as _httpx

    from x402.http.clients.httpx import x402HttpxClient

    async def run():
        # Probe with PLAIN httpx first: the SDK client raises on a 402 that
        # lacks the V2 PAYMENT-REQUIRED header, so flavor detection must
        # happen before the SDK ever sees the response.
        async with _httpx.AsyncClient(timeout=timeout, follow_redirects=True) as plain:
            r0 = await plain.request(method.upper(), url, json=json_body, headers=headers or {})

        if r0.status_code != 402:
            signer = SessionEOASigner(max_amount_atomic) if signer_mode != "privy" \
                else PrivySigner(max_amount_atomic)
            return {"status": r0.status_code, "payer": signer.address,
                    "body": (r0.text[:2000] if r0.text else ""), "paid": False}

        if r0.headers.get("PAYMENT-REQUIRED") or r0.headers.get("X-PAYMENT-REQUIRED"):
            # V2 header challenge -> x402 SDK path
            client, signer = _build_client(max_amount_atomic, signer_mode)
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

        # platform-shape challenge (Starchild community-gateway contract):
        # JSON body {x402Version, error, accepts:{...pricingModel}}
        try:
            challenge = json.loads(r0.text or "{}")
        except Exception:
            challenge = {}
        accepts = challenge.get("accepts")
        if isinstance(accepts, list):  # tolerate accepts as a list
            accepts = accepts[0] if accepts else None
        if not (isinstance(accepts, dict) and accepts.get("scheme") == "exact"):
            return {"status": 402, "error": "unrecognized 402 challenge",
                    "body": (r0.text[:2000] if r0.text else "")}
        signer = SessionEOASigner(max_amount_atomic)
        xp = _sign_platform_payment(accepts, max_amount_atomic)
        async with _httpx.AsyncClient(timeout=timeout, follow_redirects=True) as plain:
            r2 = await plain.request(method.upper(), url, json=json_body,
                                     headers={**(headers or {}), "X-PAYMENT": xp})
        return {"status": r2.status_code, "payer": signer.address, "paid": True,
                "pricing_model": accepts.get("pricingModel"),
                "body": (r2.text[:2000] if r2.text else "")}

    return asyncio.run(run())


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    method, url = sys.argv[1], sys.argv[2]
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    cap = int(os.environ.get("X402_MAX_ATOMIC", "1000000"))
    print(json.dumps(paid_request(method, url, body, max_amount_atomic=cap), indent=2))
