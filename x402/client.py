"""x402 buyer client — lets THIS agent pay other agents' x402 services.

Signer: the local session EOA (`.x402/buyer.key`, created on first use).
EVM rails only (EIP-3009 USDC/USDG); fund the EOA address with a small USDC
budget from any wallet — the budget is the hard spend cap. signer_mode
"auto" and "eoa" both select it.

Usage (bash):
    python3 skills/x402/client.py GET  https://host/api/thing
    python3 skills/x402/client.py POST https://host/x402/topup '{"json":"body"}'

Or from Python:
    from client import paid_request
    r = paid_request("GET", url)            # auto-handles 402 -> sign -> retry
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request

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


# Public EVM RPCs for USDC balance reads and DOMAIN_SEPARATOR() reads.
_EVM_RPC = {
    1: "https://ethereum.publicnode.com",
    10: "https://optimism.publicnode.com",
    130: "https://mainnet.unichain.org",
    137: "https://polygon-bor.publicnode.com",
    143: "https://rpc.monad.xyz",
    480: "https://worldchain-mainnet.g.alchemy.com/public",
    4663: "https://rpc.mainnet.chain.robinhood.com",
    8453: "https://mainnet.base.org",
    196: "https://rpc.xlayer.tech",
    1952: "https://testrpc.xlayer.tech",
    42161: "https://arbitrum-one.publicnode.com",
    42220: "https://forno.celo.org",
    43114: "https://avalanche-c-chain-rpc.publicnode.com",
    46630: "https://rpc.testnet.chain.robinhood.com",
    59144: "https://rpc.linea.build",
    84532: "https://sepolia.base.org",
}


class SessionEOASigner:
    """Local session EOA buyer key (.x402/buyer.key).

    A plain EOA has no code and signs pure ECDSA, which USDC's
    transferWithAuthorization accepts. Fund it with a small USDC budget from
    any wallet; the budget itself acts as the hard spend cap.
    """

    KEY_PATH = "/data/workspace/.x402/buyer.key"
    # Marker file written after a successful registration. Its presence means
    # this EOA address is already mapped in ai-agent's session_wallets table,
    # so we skip the registration API call on subsequent instantiations.
    REGISTERED_PATH = "/data/workspace/.x402/buyer.key.registered"

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
        # Register the session EOA address to ai-agent so community-gateway can
        # resolve x402 payer addresses back to users. Synchronous — the
        # registration MUST succeed before the wallet can be used (otherwise
        # payments would be unresolvable). If already registered (marker file
        # exists), skip the API call. If JWT/API_URL is missing (local dev),
        # skip silently.
        try:
            self._register_session_wallet()
        except Exception:
            # Registration failed — invalidate the account so the signer
            # cannot be used even if the caller catches the exception.
            self._acct = None
            raise

    # ── Session wallet registration ──────────────────────────────────────────

    @classmethod
    def _register_session_wallet(cls) -> None:
        """Register this EOA address to ai-agent's session_wallets table.

        Behavior:
        - If the local marker file (REGISTERED_PATH) exists, registration was
          already done in a previous run — skip the API call.
        - If CONTAINER_JWT/USER_JWT or AI_AGENT_API_URL is missing (local dev
          outside the platform), skip silently — no registration possible.
        - Otherwise, call the registration API synchronously. On success,
          write the marker file. On failure, raise RuntimeError to block
          wallet usage — an unregistered EOA would produce unresolvable
          payments.

        Auth: CONTAINER_JWT / USER_JWT (Bearer) — the same identity token
        used by other skills (e.g. agentx). The user_id is extracted
        server-side from the JWT.
        """
        # Already registered in a previous run — skip.
        if os.path.exists(cls.REGISTERED_PATH):
            return

        jwt = os.environ.get("CONTAINER_JWT", "") or os.environ.get("USER_JWT", "")
        base = os.environ.get("AI_AGENT_API_URL", "").rstrip("/")
        if not jwt or not base:
            # Running outside the platform (local dev) — skip silently.
            return

        addr = cls._load_address()
        if not addr:
            raise RuntimeError(
                "x402: cannot read EOA address from key file for registration")

        container_id = (
            os.environ.get("CONTAINER_ID")
            or os.environ.get("FLY_MACHINE_ID")
            or ""
        )

        url = base + "/v1/agent/profile/register-session-wallet"
        payload = {
            "wallet_address": addr,
            "wallet_type": "x402_session_eoa",
            "chain_type": "ethereum",
        }
        if container_id:
            payload["container_id"] = container_id
        body = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {jwt}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")

        registration_ok = False
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_data = resp.read().decode()
                # 200 with status created/updated = success
                try:
                    result = json.loads(resp_data) if resp_data else {}
                except Exception:
                    result = {}
                if result.get("status") in ("created", "updated"):
                    registration_ok = True
                else:
                    raise RuntimeError(
                        f"x402: session wallet registration unexpected "
                        f"response: {resp_data[:200]}")
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode()[:300]
            except Exception:
                pass
            # The API is idempotent: if the address was already registered
            # (e.g. local marker file lost but ai-agent DB has the record),
            # a re-registration returns 200 with status=updated. However,
            # if we get a 400 with address_conflict, the EOA address collides
            # with another registered wallet — that's a real error, block usage.
            # Other 4xx/5xx errors also block usage.
            raise RuntimeError(
                f"x402: session wallet registration failed: "
                f"HTTP {e.code}: {detail}") from e
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"x402: session wallet registration error: "
                f"{type(e).__name__}: {e}") from e

        if not registration_ok:
            raise RuntimeError(
                "x402: session wallet registration did not confirm success")

        # Registration succeeded — write marker file so we skip next time.
        try:
            os.makedirs(os.path.dirname(cls.REGISTERED_PATH), exist_ok=True)
            with open(cls.REGISTERED_PATH, "w") as f:
                f.write(addr)
            os.chmod(cls.REGISTERED_PATH, 0o600)
        except Exception as e:
            # Marker write failed — not fatal, but log it. Next run will
            # re-register (idempotent API, so that's fine).
            sys.stderr.write(
                f"[x402] warning: could not write registration marker: {e}\n")

    @staticmethod
    def _load_address() -> str:
        """Read the EOA address from the key file without instantiating
        eth_account (avoids a circular import / heavy dep at module load)."""
        try:
            from eth_account import Account
            if os.path.exists(SessionEOASigner.KEY_PATH):
                acct = Account.from_key(
                    open(SessionEOASigner.KEY_PATH).read().strip())
                return acct.address
        except Exception:
            pass
        return ""

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



# Body cap for returned response bodies. Paid responses (line ~492) are the
# product the buyer just paid for — return them in full. Unpaid/error bodies
# stay capped to keep summaries small. Override: X402_BODY_MAX (0 = unlimited).
def _body(text: str, *, full: bool = False) -> str:
    if not text:
        return ""
    if full:
        return text
    try:
        cap = int(os.environ.get("X402_BODY_MAX", "2000"))
    except ValueError:
        cap = 2000
    return text if cap <= 0 else text[:cap]

def _make_signer(signer_mode: str, max_amount_atomic: int):
    """signer_mode: 'auto' | 'eoa' — both select the session EOA
    (`.x402/buyer.key`)."""
    if signer_mode not in ("auto", "eoa"):
        raise ValueError(f"unknown signer_mode {signer_mode!r} (use 'auto' or 'eoa')")
    s = SessionEOASigner(max_amount_atomic=max_amount_atomic)
    s.signer_type, s.signer_warning = "session_eoa", None
    return s


def network_rank(network: str) -> int:
    """Shared rail preference (lower = preferred). Used by BOTH paid_request
    routing and bazaar probe display so the rail a user sees/confirms at probe
    time is the rail actually selected for payment. The session EOA signs EVM
    rails only, so non-EVM rails (e.g. Solana) rank last and are never paid.
    """
    net = "eip155:8453" if network == "base" else str(network or "")
    return 0 if net.startswith("eip155:") else 9


def _build_client(max_amount_atomic: int = 1_000_000, signer_mode: str = "auto",
                  prefer_network: str = ""):
    from x402 import x402Client
    from x402.client_base import max_amount, prefer_network, prefer_scheme
    from x402.mechanisms.evm.exact.register import register_exact_evm_client
    signer = _make_signer(signer_mode, max_amount_atomic)
    client = x402Client()
    # EVM rails (Base/Polygon/Arbitrum/Monad/…). The session EOA cannot sign
    # SVM, so no Solana scheme is registered.
    register_exact_evm_client(client, signer)
    # Rail preference: see network_rank() — shared with bazaar probe so the
    # rail shown/confirmed at probe time is the rail actually paid.
    client.register_policy(prefer_scheme("exact"))

    def _net_of(r):
        return str(getattr(r, "network", None) or
                   (r.get("network") if isinstance(r, dict) else "") or "")

    def _amt_of(r):
        for k in ("max_amount_required", "maxAmountRequired", "amount"):
            v = r.get(k) if isinstance(r, dict) else getattr(r, k, None)
            if v is not None:
                try:
                    return int(str(v))
                except (TypeError, ValueError):
                    pass
        # Malformed/missing amount sorts LAST — never let a broken quote
        # look cheapest and shadow a valid candidate (mirrors
        # bazaar._amount_int).
        return 1 << 62

    def _prefer_funded_rail(version, reqs):
        # hard-filter non-EVM: the session EOA cannot sign these
        reqs = [r for r in reqs if _net_of(r).startswith("eip155:")
                or _net_of(r) == "base"]
        _pn = prefer_network
        # Priority: ① explicit prefer_network ② verified-funded rails first,
        # verified-empty last, unknown neutral (RPC flake must never block a
        # payment) ③ Base as default chain ④ network_rank. Incident 2026-07:
        # rank alone picked Monad while USDC sat on Base — settlement failed.
        try:
            from bazaar import _canon_network as _cn
            bals = usdc_balances(
                {_net_of(r) for r in reqs},
                evm_addr=getattr(signer, "address", None))
        except Exception:
            bals, _cn = {}, (lambda n: n)
        return sorted(reqs, key=lambda r: (
            0 if _pn and _net_of(r) == _pn else 1,
            _rail_funded_state(_cn(_net_of(r)), _amt_of(r), bals),
            0 if _cn(_net_of(r)) == "eip155:8453" else 1,
            network_rank(_net_of(r)),
            _amt_of(r)))  # cheapest wins within the same rail rank
            # (matches bazaar._sort_payable so probe display == paid rail)

    client.register_policy(_prefer_funded_rail)
    client.register_policy(max_amount(max_amount_atomic))

    def _only_known_usdc_rails(version, reqs):
        # Keep native Circle USDC exact rails only (see bazaar.PAYABLE_USDC).
        try:
            from bazaar import PAYABLE_USDC, _canon_network
            ok_assets = {k: str(v).lower() for k, v in PAYABLE_USDC.items()}
        except Exception:
            ok_assets = {
                "eip155:8453": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                "base": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            }
            def _canon_network(n):  # noqa: E306
                return "eip155:8453" if n == "base" else n
        kept = []
        for r in reqs:
            net = getattr(r, "network", None) or (r.get("network") if isinstance(r, dict) else None)
            asset = getattr(r, "asset", None) or (r.get("asset") if isinstance(r, dict) else None)
            net_c = _canon_network(net) if net else net
            want = ok_assets.get(net_c) or ok_assets.get(net)
            if want and str(asset or "").lower() == want:
                kept.append(r)
        return kept

    client.register_policy(_only_known_usdc_rails)
    return client, signer


# Networks requiring chain-read DOMAIN_SEPARATOR() for EIP-712 signing.
# These use Diamond proxy contracts where the on-chain domain may differ from
# the name/version metadata (e.g. Robinhood USDG).
# Robinhood USDG uses a Diamond proxy (EIP-2535) whose EIP-712 domain does
# NOT match the standard (name, version, chainId, verifyingContract) hash.
# For these chains, we read DOMAIN_SEPARATOR() from RPC, compute structHash
# locally, produce a raw EIP-712 digest, and sign it directly — matching the
# facilitator's verify path (server.py CHAIN_DOMAIN_SEPARATOR_NETWORKS).
_CHAIN_DOMAIN_SEP_CHAIN_IDS = frozenset({4663, 46630})

# TransferWithAuthorization type hash (EIP-3009, constant across all chains).
# keccak256("TransferWithAuthorization(address from,address to,uint256 value,
#            uint256 validAfter,uint256 validBefore,bytes32 nonce)")
_TRANSFER_WITH_AUTH_TYPEHASH: bytes | None = None

# DOMAIN_SEPARATOR() ABI for on-chain reads
_DOMAIN_SEP_ABI = [{"name": "DOMAIN_SEPARATOR", "type": "function",
                    "stateMutability": "view", "inputs": [],
                    "outputs": [{"type": "bytes32"}]}]

# Cache: {(chain_id, asset_lower): bytes32_domain_separator}
_domain_sep_cache: dict[tuple[int, str], bytes] = {}


def _get_transfer_with_auth_typehash() -> bytes:
    """Lazy-init the TransferWithAuthorization type hash (needs web3)."""
    global _TRANSFER_WITH_AUTH_TYPEHASH
    if _TRANSFER_WITH_AUTH_TYPEHASH is None:
        from web3 import Web3
        _TRANSFER_WITH_AUTH_TYPEHASH = Web3.keccak(
            text="TransferWithAuthorization(address from,address to,"
                 "uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)"
        )
    return _TRANSFER_WITH_AUTH_TYPEHASH


def _read_domain_separator(chain_id: int, asset: str) -> bytes:
    """Read DOMAIN_SEPARATOR() from chain via RPC (cached, immutable per contract)."""
    from web3 import Web3
    key = (chain_id, asset.lower())
    cached = _domain_sep_cache.get(key)
    if cached is not None:
        return cached

    rpc = _EVM_RPC.get(chain_id)
    if not rpc:
        raise RuntimeError(f"No RPC URL for chain {chain_id}")
    w3 = Web3(Web3.HTTPProvider(rpc))
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(asset), abi=_DOMAIN_SEP_ABI)
    ds = bytes(contract.functions.DOMAIN_SEPARATOR().call())
    _domain_sep_cache[key] = ds
    return ds


def _sign_raw_digest(signer, digest: bytes) -> bytes:
    """Sign a raw 32-byte EIP-712 digest with the signer's private key.

    SessionEOASigner: uses eth_account.unsafe_sign_hash directly.
    """
    # SessionEOASigner has _acct (eth_account.Account)
    acct = getattr(signer, "_acct", None)
    if acct is not None:
        sig_obj = acct.unsafe_sign_hash(digest)
        return sig_obj.signature

    raise RuntimeError(
        "Cannot sign raw EIP-712 digest: signer does not expose a private "
        "key (_acct). Robinhood USDG payments require SessionEOASigner or "
        "a signer with raw hash signing support.")


def _sign_platform_payment(accepts: dict, max_amount_atomic: int, signer=None) -> str:
    """Sign an EIP-3009 authorization for a platform-shape 402 (JSON-body
    `accepts` dict with pricingModel — Starchild community-gateway contract).
    Returns the base64 X-PAYMENT header value. Works with any signer that
    implements sign_typed_data (e.g. SessionEOASigner)."""
    import time as _t

    signer = signer or SessionEOASigner(max_amount_atomic=max_amount_atomic)
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

    # Chain-read DOMAIN_SEPARATOR path for Diamond proxy contracts (Robinhood
    # USDG). Only used when the signer exposes a private key (_acct) for raw
    # digest signing.
    _use_chain_read = (
        chain_id in _CHAIN_DOMAIN_SEP_CHAIN_IDS
        and getattr(signer, "_acct", None) is not None
    )

    if _use_chain_read:
        # Raw EIP-712 digest signing — mirrors facilitator server.py verify Mode B.
        from web3 import Web3
        domain_sep = _read_domain_separator(chain_id, accepts["asset"])
        typehash = _get_transfer_with_auth_typehash()
        struct_hash = Web3.keccak(
            typehash
            + bytes.fromhex(auth["from"][2:].lower().zfill(64))
            + bytes.fromhex(auth["to"][2:].lower().zfill(64))
            + int(auth["value"]).to_bytes(32, "big")
            + int(auth["validAfter"]).to_bytes(32, "big")
            + int(auth["validBefore"]).to_bytes(32, "big")
            + bytes.fromhex(auth["nonce"][2:])
        )
        digest = Web3.keccak(b"\x19\x01" + domain_sep + struct_hash)
        sig = _sign_raw_digest(signer, digest)
    else:
        # Standard EIP-712 typed-data signing (Base, Monad, …).
        class _NS:
            def __init__(self, **kw): self.__dict__.update(kw)
        domain = _NS(name=extra.get("name", "USD Coin"), version=extra.get("version", "2"),
                     chain_id=chain_id, verifying_contract=accepts["asset"])
        fields = [_NS(name=n, type=t) for n, t in [
            ("from", "address"), ("to", "address"), ("value", "uint256"),
            ("validAfter", "uint256"), ("validBefore", "uint256"), ("nonce", "bytes32")]]
        sig = signer.sign_typed_data(
            domain, {"TransferWithAuthorization": fields}, "TransferWithAuthorization",
            {"from": auth["from"], "to": auth["to"], "value": amount,
             "validAfter": 0, "validBefore": int(auth["validBefore"]),
             "nonce": auth["nonce"]})

    payload = {"x402Version": 2, "scheme": "exact", "network": network,
               "payload": {"authorization": auth, "signature": "0x" + sig.hex()}}
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _signer_meta(signer) -> dict:
    """signer_type / signer_warning for result dicts and ledger lines."""
    meta = {"signer_type": getattr(signer, "signer_type", "unknown")}
    warn = getattr(signer, "signer_warning", None)
    if warn:
        meta["signer_warning"] = warn
    return meta


def _ledger_append(entry: dict):
    """Append one payment record to the local ledger (best-effort, never raises).

    Every payment client.py signs is recorded in
    ``$WORKSPACE/.x402/payments.jsonl`` (override path with X402_LEDGER), so
    "where did the USDC go" is always answerable locally — including payments
    made from background sessions. Each line: ts, caller, event, url, method,
    amount_atomic, payer, status, paid, settlement tx when available.
    """
    try:
        path = os.environ.get("X402_LEDGER") or os.path.join(
            os.environ.get("WORKSPACE", "/data/workspace"),
            ".x402", "payments.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        import time as _time
        entry.setdefault("ts",
                         _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()))
        entry.setdefault("caller", os.environ.get("SC_CALLER_ID")
                         or os.environ.get("JOB_ID") or f"pid:{os.getpid()}")
        with open(path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:  # ledger must never break a payment
        print(f"[x402] WARNING: payment ledger write failed: {e}",
              file=sys.stderr)


def paid_request(method: str, url: str, json_body=None, headers=None,
                 max_amount_atomic: int = 1_000_000, timeout: float = 60.0,
                 signer_mode: str = "auto", pricing_model: str = "",
                 prefer_network: str = ""):
    """One-shot request with automatic x402 payment. Returns dict summary.
    Payer: the session EOA (EVM rails only).

    pricing_model: for MULTI-PLAN services — sends X-Pricing-Model so the
    gateway quotes that plan's price in its 402 (e.g. "weekly", "yearly").
    Empty = the service's default plan.

    prefer_network: CAIP-2 network id (e.g. "eip155:8453" for Base,
    "eip155:143" for Monad) to prefer when the 402 challenge offers multiple
    accepts. When set, the matching accept is selected first (if present in
    the challenge); otherwise falls back to the automatic network_rank
    ordering. Use this when the user explicitly asks to pay on a specific
    chain. Also accepted via env X402_PREFER_NETWORK.

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
        nonlocal headers, prefer_network, json_body
        # Resolve prefer_network: explicit param > env var
        if not prefer_network:
            prefer_network = os.environ.get("X402_PREFER_NETWORK", "").strip()
        # Defensive: if json_body is a string (caller did json.dumps before
        # passing), parse it back to a dict so httpx json= doesn't double-encode.
        if isinstance(json_body, str):
            try:
                json_body = json.loads(json_body)
            except (json.JSONDecodeError, ValueError):
                pass  # not valid JSON string — pass through as-is
        if pricing_model:
            headers = {**(headers or {}), "X-Pricing-Model": pricing_model}
        # Probe with PLAIN httpx first: the SDK client raises on a 402 that
        # lacks the V2 PAYMENT-REQUIRED header, so flavor detection must
        # happen before the SDK ever sees the response.
        async with _httpx.AsyncClient(timeout=timeout, follow_redirects=True) as plain:
            r0 = await plain.request(method.upper(), url, json=json_body, headers=headers or {})

        if r0.status_code != 402:
            # No payment happens on this path — report identity best-effort.
            out = {"status": r0.status_code, "body": _body(r0.text),
                   "paid": False}
            try:
                signer = _make_signer(signer_mode, max_amount_atomic)
                out.update({"payer": signer.address, **_signer_meta(signer)})
            except Exception:
                pass
            return out

        # Platform-shape detection: if the 402 body is a Starchild platform
        # challenge (accepts list with pricingModel), skip the V2 SDK path
        # and fall through to the platform path below (signed with
        # _sign_platform_payment); the V2 SDK does not handle
        # body-based V2 challenges (x402Version: 2 in JSON body without
        # PAYMENT-REQUIRED header), causing Invalid payment required response.
        _is_platform = False
        _is_v2_body = False
        try:
            _pb = json.loads(r0.text or "{}")
            _is_v2_body = _pb.get("x402Version") == 2
            _pa = _pb.get("accepts")
            if isinstance(_pa, list) and _pa:
                _f = _pa[0] if isinstance(_pa[0], dict) else {}
                _is_platform = bool(
                    _f.get("pricingModel")
                    or (_f.get("extra") or {}).get("pricingModel"))
        except Exception:
            pass

        if (not _is_platform) and (
                r0.headers.get("PAYMENT-REQUIRED")
                or r0.headers.get("X-PAYMENT-REQUIRED")
                or _is_v2_body):
            # V2 header challenge -> x402 SDK path (non-platform services)
            client, signer = _build_client(max_amount_atomic, signer_mode,
                                           prefer_network)
            _ledger_append({"event": "attempt", "url": url,
                            "method": method.upper(), "payer": signer.address,
                            "flavor": "v2-header", **_signer_meta(signer)})
            async with x402HttpxClient(client, timeout=timeout) as c:
                r = await c.request(method.upper(), url, json=json_body, headers=headers or {})
                out = {"status": r.status_code, "payer": signer.address,
                       **_signer_meta(signer),
                       "body": _body(r.text, full=True)}
                pr = r.headers.get("PAYMENT-RESPONSE") or r.headers.get("X-PAYMENT-RESPONSE")
                if pr:
                    try:
                        out["settlement"] = json.loads(base64.b64decode(pr))
                    except Exception:
                        out["settlement_raw"] = pr[:200]
                # Report the ACTUAL selected rail.
                sett = out.get("settlement") if isinstance(out.get("settlement"), dict) else {}
                net = sett.get("network")
                if net:
                    out["network"] = net
                _ledger_append({
                    "event": "result", "url": url, "method": method.upper(),
                    "payer": out["payer"], "status": r.status_code,
                    "paid": r.status_code == 200,
                    "network": out.get("network"),
                    "settlement_tx": (out.get("settlement") or {}).get("transaction"),
                    "flavor": "v2-header",
                    "signer_type": out.get("signer_type"),
                    **({"signer_warning": out["signer_warning"]}
                       if out.get("signer_warning") else {})})
                return out

        # platform-shape challenge (Starchild community-gateway contract):
        # JSON body {x402Version, error, accepts:[{...pricingModel}, ...]}
        # Multi-accepts (plans-280-04): accepts is a LIST — one entry per
        # network. Pick ONE rail with the same network_rank policy as the
        # V2 SDK path (do NOT hard-code accepts[0], which is usually Base).
        try:
            challenge = json.loads(r0.text or "{}")
        except Exception:
            challenge = {}
        accepts_raw = challenge.get("accepts")
        if isinstance(accepts_raw, dict):
            accepts_list = [accepts_raw]
        elif isinstance(accepts_raw, list):
            accepts_list = [a for a in accepts_raw
                            if isinstance(a, dict) and a.get("scheme") == "exact"]
        else:
            accepts_list = []
        if not accepts_list:
            return {"status": 402, "error": "unrecognized 402 challenge",
                    "body": _body(r0.text)}
        signer = _make_signer(signer_mode, max_amount_atomic)

        def _pick_accept(cands: list, prefer_network: str | None = None) -> dict | None:
            """Select one accept for the platform JSON-body path.

            EVM rails only, signed via _sign_platform_payment (EIP-3009);
            Solana / other non-EVM accepts are dropped (the session EOA
            cannot sign them).

            Selection: keep prefer_network on prepaid deposit retry; else rank
            rails with network_rank (Base first as primary USDC chain).
            """
            exact = [a for a in cands
                     if isinstance(a, dict) and a.get("scheme") == "exact"]
            if not exact:
                return None
            # EVM EIP-3009 path. Drop Solana/other non-EVM so network_rank
            # cannot pick a rail we cannot sign via _sign_platform_payment.
            exact = [a for a in exact
                     if str(a.get("network") or "").startswith("eip155:")
                     or str(a.get("network") or "") == "base"]
            if not exact:
                return None
            def _amt(a):
                try:
                    return int(str(a.get("amount")))
                except (TypeError, ValueError):
                    return 1 << 62  # malformed sorts last, never cheapest
            if prefer_network:
                same = [a for a in exact
                        if str(a.get("network") or "") == prefer_network]
                if same:
                    return sorted(same, key=_amt)[0]  # cheapest on that chain
            # Funded rails first, Base as default chain, then network_rank
            # (see _prefer_funded_rail for rationale — same ordering).
            try:
                from bazaar import _canon_network as _cn
                bals = usdc_balances(
                    {str(a.get("network") or "") for a in exact},
                    evm_addr=getattr(signer, "address", None))
            except Exception:
                bals, _cn = {}, (lambda n: n)
            return sorted(exact, key=lambda a: (
                _rail_funded_state(_cn(str(a.get("network") or "")),
                                   _amt(a), bals),
                0 if _cn(str(a.get("network") or "")) == "eip155:8453" else 1,
                network_rank(str(a.get("network") or "")),
                _amt(a),  # cheapest within same rank — matches probe sort
            ))[0]

        accepts = _pick_accept(accepts_list, prefer_network=prefer_network or None)
        if not accepts:
            return {"status": 402, "error": "no payable accept in 402 challenge",
                    "body": _body(r0.text)}
        # Up to 2 payment attempts. prepaid needs both: attempt 1 signs the
        # per-call price (authentication only — the gateway debits the prepaid
        # balance instead of settling); if the gateway answers 402
        # insufficient_balance, its new challenge carries accepts.amount =
        # deposit size, so attempt 2 signs the deposit (settled on-chain via
        # /facilitator/deposit-settle, then the call is debited and forwarded).
        # Other modes are unchanged: attempt 1 settles, a second 402 just
        # surfaces the gateway's error.
        r2 = r0
        chosen_network = str(accepts.get("network") or "")
        for _ in range(2):
            xp = _sign_platform_payment(accepts, max_amount_atomic,
                                        signer=signer)
            _ledger_append({"event": "signed", "url": url,
                            "method": method.upper(), "payer": signer.address,
                            "amount_atomic": accepts.get("amount"),
                            "pricing_model": accepts.get("pricingModel"),
                            "network": accepts.get("network"),
                            "pay_to": accepts.get("payTo"),
                            "flavor": "platform",
                            **_signer_meta(signer)})
            async with _httpx.AsyncClient(timeout=timeout, follow_redirects=True) as plain:
                r2 = await plain.request(method.upper(), url, json=json_body,
                                         headers={**(headers or {}), "X-PAYMENT": xp})
            _ledger_append({"event": "result", "url": url,
                            "method": method.upper(), "payer": signer.address,
                            "amount_atomic": accepts.get("amount"),
                            "status": r2.status_code,
                            "paid": r2.status_code == 200,
                            "network": accepts.get("network"),
                            "flavor": "platform",
                            **_signer_meta(signer)})
            if r2.status_code != 402:
                break
            try:
                nxt_body = json.loads(r2.text or "{}")
                nxt_raw = nxt_body.get("accepts")
            except Exception:
                break
            if isinstance(nxt_raw, dict):
                nxt_list = [nxt_raw]
            elif isinstance(nxt_raw, list):
                nxt_list = nxt_raw
            else:
                break
            # Deposit escalation: stay on the same chain the buyer already
            # chose (do not jump to accepts[0] / Base).
            nxt = _pick_accept(nxt_list, prefer_network=chosen_network)
            if not nxt:
                break
            if nxt.get("amount") == accepts.get("amount"):
                break  # same ask again -> not a deposit escalation, give up
            accepts = nxt
            chosen_network = str(accepts.get("network") or chosen_network)
        # Extract error from the last 402 body for diagnostics
        _last_error = ""
        if r2.status_code == 402:
            try:
                _last_error = json.loads(r2.text or "{}").get("error", "")
            except Exception:
                pass
        out = {"status": r2.status_code, "payer": signer.address,
               "paid": r2.status_code < 400,
               **_signer_meta(signer),
               "pricing_model": accepts.get("pricingModel"),
               "network": accepts.get("network"),
               "body": _body(r2.text, full=True)}
        if _last_error:
            out["error"] = _last_error
        return out

    return asyncio.run(run())


_BAL_CACHE: dict = {}   # (canonical_net, payer_addr) -> (ts, atomic_balance)


def usdc_balances(networks, evm_addr=None,
                  ttl: float = 60.0) -> dict:
    """Best-effort USDC balance (atomic units) per canonical EVM network.

    None = unknown (RPC failure, unsupported or non-EVM network, or no
    address). Cached ``ttl`` seconds per (network, address) so the several
    routing checks inside one payment share RPC round-trips. ``ttl=0`` forces
    live reads (preflight) while still refreshing the cache for the payment
    that follows.
    """
    import time as _t
    try:
        from bazaar import PAYABLE_USDC, _canon_network
    except Exception:
        return {}
    out: dict = {}
    for raw in networks or []:
        net = _canon_network(str(raw or ""))
        usdc = PAYABLE_USDC.get(net)
        addr = evm_addr
        if not usdc or not addr or not net.startswith("eip155:"):
            out[net] = None
            continue
        ck = (net, addr)
        hit = _BAL_CACHE.get(ck)
        if hit and ttl > 0 and _t.time() - hit[0] < ttl:
            out[net] = hit[1]
            continue
        bal = None
        try:
            from web3 import Web3
            rpc = _EVM_RPC.get(int(net.split(":")[1]))
            if rpc:
                w3 = Web3(Web3.HTTPProvider(
                    rpc, request_kwargs={"timeout": 10}))
                data = "0x70a08231" + addr[2:].lower().rjust(64, "0")
                raw_b = w3.eth.call({"to": Web3.to_checksum_address(usdc),
                                     "data": data})
                bal = int.from_bytes(raw_b, "big")
        except Exception:
            bal = None
        if bal is not None:
            _BAL_CACHE[ck] = (_t.time(), bal)
        out[net] = bal
    return out


def _rail_funded_state(net: str, amount_atomic: int, balances: dict) -> int:
    """Sort key for balance-aware routing: 0 = verified funded,
    1 = unknown (RPC hiccup must NEVER block a payment), 2 = verified
    insufficient. Incident 2026-07: static rank picked Monad while the
    payer's USDC sat on Base — settlement failed on a zero-balance rail."""
    b = balances.get(net)
    if b is None:
        return 1
    need = amount_atomic if amount_atomic and amount_atomic > 0 else 1
    return 0 if b >= need else 2


def payment_preflight(amount_atomic: int, networks=None,
                      signer_mode: str = "auto") -> dict:
    """ONE-SHOT pre-purchase check. Run this BEFORE asking the user to
    confirm a purchase, and surface ALL blockers together — never let the
    user fix funding, then hit a policy wall, then hit something else in
    serial round-trips.

    Checks: ① signer capability per candidate rail (fail-closed: a rail the
    session EOA cannot sign — any non-EVM rail — is NOT a candidate)
    ② USDC balance per signable rail — ok requires at least ONE rail that
    is both signable AND verified funded; unknown (RPC-failed) balances
    never count as funded.

    networks: candidate rails from the service's 402 accepts (canonical ids,
    e.g. ["eip155:8453", "eip155:143"]). Default: Base+Monad+Robinhood.
    Returns {ok, blockers[], warnings[], payer{}, funded_rails[], balances{}}.
    """
    from bazaar import PAYABLE_USDC, _canon_network
    out = {"ok": True, "blockers": [], "warnings": [], "payer": {},
           "balances": {}, "funded_rails": []}
    nets = [_canon_network(n) for n in (networks or
            ["eip155:8453", "eip155:143", "eip155:4663"])]

    # ① signer: the session EOA (EVM rails only).
    evm_addr = None
    if signer_mode not in ("auto", "eoa"):
        out["blockers"].append(
            f"unknown signer_mode {signer_mode!r} (use 'auto' or 'eoa')")
    else:
        try:
            evm_addr = SessionEOASigner().address
        except Exception as e:
            out["blockers"].append(f"session EOA signer unavailable: {e}")
    out["payer"] = {"evm": evm_addr}

    # Capability filter: keep only rails the session EOA can sign.
    def _signable(net):
        return net.startswith("eip155:") and evm_addr is not None

    unsignable = [n for n in nets if not (PAYABLE_USDC.get(n) and _signable(n))]
    nets = [n for n in nets if PAYABLE_USDC.get(n) and _signable(n)]
    if unsignable:
        out["warnings"].append(
            f"rails excluded (session EOA cannot sign them): {unsignable}")
    if not nets:
        out["blockers"].append(
            f"no signable payment rail: the session EOA (EVM-only) cannot "
            f"sign any of the service's accepted networks "
            f"({unsignable or networks}).")

    # ② balances per signable rail (direct RPC; no DeBank round-trip).
    # ttl=0: preflight always reads LIVE, but refreshes the shared routing
    # cache so the payment that follows reuses these balances for rail
    # selection (funded-first ordering in _prefer_funded_rail).
    out["balances"] = usdc_balances(nets, evm_addr=evm_addr, ttl=0)
    for net, bal in out["balances"].items():
        if bal is not None and bal >= amount_atomic:
            out["funded_rails"].append(net)

    # ③ dependency sanity: buyer path needs web3>=7. NEVER upgrade a pinned
    # global web3 (trading bots) — bootstrap the isolated venv instead.
    try:
        import web3 as _web3
        if int(_web3.__version__.split(".")[0]) < 7:
            out["blockers"].append(
                f"web3 {_web3.__version__} < 7 in this environment — run "
                "`bash skills/x402/scripts/ensure_env.sh` (zero-interaction: "
                "creates .venv-x402 without touching global packages) and "
                "use the interpreter it prints. Do NOT upgrade global web3.")
    except ImportError:
        out["blockers"].append(
            "web3 not installed — run `bash skills/x402/scripts/ensure_env.sh`.")

    # FAIL-CLOSED: ok requires ≥1 rail that is signable AND verified funded.
    # Unknown balances (RPC failures) never count as funded.
    if nets and not out["funded_rails"]:
        need = amount_atomic / 1e6
        bal_view = {k: (v / 1e6 if v is not None else "unverified")
                    for k, v in out["balances"].items()}
        known = [b for b in out["balances"].values() if b is not None]
        if not known:
            out["blockers"].append(
                f"could not verify USDC balance on ANY signable rail "
                f"(all RPC queries failed: {bal_view}) — fail-closed. "
                "Retry, or verify the payer's balances on a block explorer "
                "before proceeding.")
        else:
            out["blockers"].append(
                f"no signable rail holds ≥ {need} USDC "
                f"(balances: {bal_view}). "
                "Offer ALL funding options at once: pay on another funded "
                "chain, bridge (e.g. Relay/Across), or fiat-onramp — don't "
                "just say 'fund the wallet'.")
    out["ok"] = not out["blockers"]
    return out


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    method, url = sys.argv[1], sys.argv[2]
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    cap = int(os.environ.get("X402_MAX_ATOMIC", "1000000"))
    print(json.dumps(paid_request(method, url, body, max_amount_atomic=cap), indent=2))
