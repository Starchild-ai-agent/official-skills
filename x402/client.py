"""x402 buyer client — lets THIS agent pay other agents' x402 services.

Default signer (signer_mode="auto"): the PRIVY wallet. PrivySigner detects
EIP-7702 delegation on the payer address (Privy gas sponsorship installs
ZeroDev Kernel) and transparently signs through Kernel's EIP-712 wrapper
(0x00 sudo prefix + 65B ECDSA), which USDC accepts via ERC-1271. By default,
auto FAILS CLOSED if the Privy signer is unavailable — no payment is signed.
Use allow_fallback_eoa=True, env X402_FALLBACK_EOA=1, or signer_mode="eoa" /
env X402_SIGNER=eoa to explicitly pay from the session EOA
(`.x402/buyer.key`). NOTE: the two signers are different payer identities —
subscriptions/prepaid balances don't transfer.

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


class PrivySigner:
    """ClientEvmSigner backed by the Starchild wallet skill (Privy)."""

    REGISTERED_PATH = "/data/workspace/.x402/privy.registered"

    def __init__(self, max_amount_atomic: int = 1_000_000):
        """max_amount_atomic: refuse to sign payments above this (default 1 USDC)."""
        from core.skill_tools import wallet
        self._wallet = wallet
        self.max_amount_atomic = max_amount_atomic
        info = wallet.wallet_info()
        self._address = next(w["wallet_address"] for w in info["wallets"]
                             if w["chain_type"] == "ethereum")
        # Register the Privy payer address to ai-agent's session_wallets so
        # community-gateway can attribute payments (by-wallet lookup only
        # covers user_info login wallets + session_wallets — the Privy AGENT
        # wallet lives in the wallet service's own DB and is NOT resolvable
        # otherwise; without this, purchases record buyer_user_id=NULL).
        # Best-effort: a failed registration must not block payments.
        try:
            self._register_privy_wallet()
        except Exception:
            pass

    def _register_privy_wallet(self) -> None:
        if os.path.exists(self.REGISTERED_PATH):
            return
        jwt = os.environ.get("CONTAINER_JWT", "") or os.environ.get("USER_JWT", "")
        base = os.environ.get("AI_AGENT_API_URL", "").rstrip("/")
        if not jwt or not base:
            return  # outside the platform — nothing to register against
        payload = {"wallet_address": self._address,
                   "wallet_type": "x402_privy_wallet",
                   "chain_type": "ethereum"}
        cid = os.environ.get("CONTAINER_ID") or os.environ.get("FLY_MACHINE_ID") or ""
        if cid:
            payload["container_id"] = cid
        req = urllib.request.Request(
            base + "/v1/agent/profile/register-session-wallet",
            data=json.dumps(payload).encode(), method="POST")
        req.add_header("Authorization", f"Bearer {jwt}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode() or "{}")
        if result.get("status") in ("created", "updated"):
            os.makedirs(os.path.dirname(self.REGISTERED_PATH), exist_ok=True)
            with open(self.REGISTERED_PATH, "w") as f:
                f.write(self._address)

    @property
    def address(self) -> str:
        return self._address

    # EIP-7702 delegation handling: when the Privy address carries delegated
    # code (Privy gas sponsorship installs ZeroDev Kernel), USDC verifies via
    # ERC-1271, so the payment must be signed through Kernel's EIP-712 wrapper:
    #   inner = EIP-3009 digest -> sign Kernel(bytes32 hash) under Kernel's
    #   domain -> final sig = 0x00 (root/sudo validator prefix) + 65B ECDSA.
    # Public RPCs for EIP-1271 / EIP-7702 delegation probe only (signing is off-chain).
    _RPC = {
        1: "https://ethereum.publicnode.com",
        10: "https://optimism.publicnode.com",
        130: "https://mainnet.unichain.org",
        137: "https://polygon-bor.publicnode.com",
        143: "https://rpc.monad.xyz",
        480: "https://worldchain-mainnet.g.alchemy.com/public",
        8453: "https://mainnet.base.org",
        84532: "https://sepolia.base.org",
        42161: "https://arbitrum-one.publicnode.com",
        42220: "https://forno.celo.org",
        43114: "https://avalanche-c-chain-rpc.publicnode.com",
        59144: "https://rpc.linea.build",
    }

    def _delegation(self, chain_id: int):
        """Returns (name, version) of the delegate's EIP-712 domain, or None."""
        if not hasattr(self, "_deleg_cache"):
            self._deleg_cache = {}
        if chain_id in self._deleg_cache:
            return self._deleg_cache[chain_id]
        result = None
        rpc = self._RPC.get(chain_id)
        if rpc:
            try:
                from web3 import Web3
                w3 = Web3(Web3.HTTPProvider(rpc))
                addr = Web3.to_checksum_address(self._address)
                if w3.eth.get_code(addr):
                    dom = w3.eth.contract(address=addr, abi=[{
                        "name": "eip712Domain", "type": "function",
                        "stateMutability": "view", "inputs": [],
                        "outputs": [{"type": "bytes1"}, {"type": "string"},
                                    {"type": "string"}, {"type": "uint256"},
                                    {"type": "address"}, {"type": "bytes32"},
                                    {"type": "uint256[]"}]}]).functions.eip712Domain().call()
                    result = (dom[1], dom[2])  # e.g. ("Kernel", "0.3.3")
            except Exception:
                result = None  # RPC hiccup -> fall through to raw signing
        self._deleg_cache[chain_id] = result
        return result

    def _sign_raw(self, d, t, primary_type, msg) -> bytes:
        res = self._wallet.wallet_sign_typed_data(
            domain=d, types=t, primaryType=primary_type, message=msg)
        sig = res.get("signature") if isinstance(res, dict) else None
        if not sig:
            raise RuntimeError(f"wallet signing failed: {res}")
        return bytes.fromhex(sig[2:] if sig.startswith("0x") else sig)

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

        deleg = self._delegation(int(domain.chain_id))
        if deleg is None:
            return self._sign_raw(d, t, primary_type, msg)

        # Delegated (smart) account: sign the wrapper over the inner digest.
        from eth_account.messages import encode_typed_data, _hash_eip191_message
        inner = _hash_eip191_message(encode_typed_data(full_message={
            "domain": {**d, "chainId": int(domain.chain_id)},
            "types": {**{tn: fields for tn, fields in t.items()},
                      "EIP712Domain": [
                          {"name": "name", "type": "string"},
                          {"name": "version", "type": "string"},
                          {"name": "chainId", "type": "uint256"},
                          {"name": "verifyingContract", "type": "address"}]},
            "primaryType": primary_type,
            "message": message}))
        wrap_sig = self._sign_raw(
            {"name": deleg[0], "version": deleg[1],
             "chainId": int(domain.chain_id), "verifyingContract": self._address},
            {"Kernel": [{"name": "hash", "type": "bytes32"}]},
            "Kernel", {"hash": "0x" + inner.hex()})
        return b"\x00" + wrap_sig  # 0x00 = Kernel root (sudo) validator prefix


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
            # with a Privy wallet — that's a real error, block usage.
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

def _make_signer(signer_mode: str, max_amount_atomic: int,
                 allow_fallback_eoa: bool = False):
    """signer_mode: 'privy' | 'eoa' | 'auto'.

    'auto' -> Privy wallet (PrivySigner transparently handles the smart-account
    ERC-1271 wrapping). FAIL-CLOSED: if the Privy signer cannot be initialized,
    auto raises instead of silently paying from a different identity. To allow
    the session-EOA fallback, opt in explicitly with allow_fallback_eoa=True
    or env X402_FALLBACK_EOA=1.
    Env override: X402_SIGNER=privy|eoa forces a mode in 'auto'.

    ⚠️ Payer identity: Privy wallet and session EOA are DIFFERENT payer
    addresses. Subscriptions / prepaid balances bought under one do NOT
    carry over to the other — pin signer_mode explicitly for such services.
    """
    if signer_mode == "privy":
        s = PrivySigner(max_amount_atomic=max_amount_atomic)
        s.signer_type, s.signer_warning = "privy", None
        return s
    if signer_mode == "eoa":
        s = SessionEOASigner(max_amount_atomic=max_amount_atomic)
        s.signer_type, s.signer_warning = "session_eoa", None
        return s
    env = os.environ.get("X402_SIGNER", "").strip().lower()
    if env in ("privy", "eoa"):
        return _make_signer(env, max_amount_atomic)
    try:
        s = PrivySigner(max_amount_atomic=max_amount_atomic)
        s.signer_type, s.signer_warning = "privy", None
        return s
    except Exception as e:
        # Most common cause: `from core.skill_tools import wallet` fails when
        # PYTHONPATH lacks /app (script run outside the agent runtime) — NOT a
        # protocol incompatibility.
        if not (allow_fallback_eoa
                or os.environ.get("X402_FALLBACK_EOA", "").strip() == "1"):
            raise RuntimeError(
                f"Privy signer unavailable ({type(e).__name__}: {e}). "
                f"Refusing to pay from the session EOA (different payer "
                f"identity). Fix the wallet-service access (ImportError → "
                f"run with PYTHONPATH=/app), or opt in explicitly with "
                f"allow_fallback_eoa=True / X402_FALLBACK_EOA=1 / "
                f"X402_SIGNER=eoa.") from e
        warn = (f"Privy signer unavailable ({type(e).__name__}: {e}) — "
                f"fell back to session EOA (DIFFERENT payer identity) "
                f"per explicit opt-in.")
        print(f"[x402] auto: {warn}", file=sys.stderr)
        s = SessionEOASigner(max_amount_atomic=max_amount_atomic)
        s.signer_type, s.signer_warning = "session_eoa", warn
        return s


def _register_session_wallet(address: str, chain_type: str, marker: str) -> None:
    """Register a payer address to ai-agent session_wallets so the community
    proxy can attribute payments to this user (buyer_user_id). Best-effort."""
    if os.path.exists(marker):
        return
    jwt = os.environ.get("CONTAINER_JWT", "") or os.environ.get("USER_JWT", "")
    base = os.environ.get("AI_AGENT_API_URL", "").rstrip("/")
    if not jwt or not base:
        return
    payload = {"wallet_address": address,
               "wallet_type": "x402_privy_wallet",
               "chain_type": chain_type}
    cid = os.environ.get("CONTAINER_ID") or os.environ.get("FLY_MACHINE_ID") or ""
    if cid:
        payload["container_id"] = cid
    req = urllib.request.Request(
        base + "/v1/agent/profile/register-session-wallet",
        data=json.dumps(payload).encode(), method="POST")
    req.add_header("Authorization", f"Bearer {jwt}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode() or "{}")
    if result.get("status") in ("created", "updated"):
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w") as f:
            f.write(address)


class PrivySvmSigner:
    """Solana buyer signer via Privy wallet_sol_sign (base64 raw message bytes).

    ExactSvmScheme only needs `.address` + `.keypair.sign_message(bytes)`.
    We don't expose the Privy key; sign_message proxies to wallet skill.
    """

    REGISTERED_PATH = "/data/workspace/.x402/privy.sol.registered"

    def __init__(self):
        from core.skill_tools import wallet as _w
        info = _w.wallet_info()
        wallets = info.get("wallets") if isinstance(info, dict) else info
        addr = None
        for w in wallets or []:
            if isinstance(w, dict) and w.get("chain_type") == "solana":
                addr = w.get("wallet_address") or w.get("address")
                break
        if not addr:
            raise RuntimeError("no Solana wallet address from wallet_info()")
        self._address = addr
        self._wallet = _w
        self.keypair = self  # ExactSvmScheme calls signer.keypair.sign_message
        # Register the Solana payer for buyer attribution (mirrors PrivySigner;
        # without this, Solana purchases record buyer_user_id=NULL).
        try:
            _register_session_wallet(addr, "solana", self.REGISTERED_PATH)
        except Exception:
            pass

    @property
    def address(self) -> str:
        return self._address

    def sign_message(self, message: bytes):
        import base64
        from solders.signature import Signature
        # wallet_sol_sign accepts base64 of raw bytes and returns base64 sig.
        r = self._wallet.wallet_sol_sign(
            message=base64.b64encode(bytes(message)).decode())
        sig_b64 = r.get("signature") if isinstance(r, dict) else None
        if not sig_b64:
            raise RuntimeError(f"wallet_sol_sign failed: {r!r}")
        return Signature.from_bytes(base64.b64decode(sig_b64))

    def sign_transaction(self, tx):
        # Not used by ExactSvmScheme.create_payment_payload (signs msg directly).
        raise NotImplementedError("use ExactSvmScheme partial-sign path")


def network_rank(network: str, signer=None, signer_mode: str = "auto") -> int:
    """Shared rail preference (lower = preferred). Used by BOTH paid_request
    routing and bazaar probe display so the rail a user sees/confirms at probe
    time is the rail actually selected for payment.

    auto: ① Solana (Privy ed25519, universally accepted) → ② EVM where the
    payer has NO 7702 delegation code (plain ECDSA, e.g. Monad) → ③ delegated
    EVM (Kernel EIP-1271, e.g. Base) — spec-correct but some facilitators
    reject it. eoa: EVM only; Solana is excluded (session EOA can't sign SVM).
    """
    net = "eip155:8453" if network == "base" else str(network or "")
    if signer_mode == "eoa":
        return 0 if net.startswith("eip155:") else 9
    if net.startswith("solana"):
        return 0
    if net.startswith("eip155:"):
        try:
            cid = int(net.split(":", 1)[1])
            deleg = getattr(signer, "_delegation", None)
            if deleg is not None and signer._delegation(cid) is None:
                return 1  # no 7702 code -> plain ECDSA
        except Exception:
            pass
        return 2  # delegated (EIP-1271) or unknown -> last resort
    return 3


_RANK_SIGNER = None


def rank_signer_cached():
    """Best-effort Privy signer used ONLY for delegation probing in
    network_rank (never signs). Raises outside the agent runtime."""
    global _RANK_SIGNER
    if _RANK_SIGNER is None:
        _RANK_SIGNER = PrivySigner(max_amount_atomic=1)
    return _RANK_SIGNER


def _build_client(max_amount_atomic: int = 1_000_000, signer_mode: str = "auto",
                  allow_fallback_eoa: bool = False, prefer_network: str = ""):
    from x402 import x402Client
    from x402.client_base import max_amount, prefer_network, prefer_scheme
    from x402.mechanisms.evm.exact.register import register_exact_evm_client
    signer = _make_signer(signer_mode, max_amount_atomic, allow_fallback_eoa)
    is_eoa = getattr(signer, "signer_type", "") == "session_eoa"
    client = x402Client()
    # EVM rails (Base/Polygon/Arbitrum/Monad/…).
    register_exact_evm_client(client, signer)
    # Solana mainnet exact (Privy SVM signer). Best-effort: skip if
    # solders/wallet missing. NEVER registered in explicit-EOA mode — the
    # session EOA cannot sign SVM, and paying from the Privy Solana wallet
    # would violate the user's pinned payer identity.
    svm_signer = None
    if not is_eoa:
        try:
            from x402.mechanisms.svm.exact.register import register_exact_svm_client
            svm_signer = PrivySvmSigner()
            register_exact_svm_client(
                client, svm_signer,
                networks=["solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp", "solana"])
        except Exception as e:
            print(f"[x402] SVM buyer register skipped: {e}", file=sys.stderr)
    # Rail preference: see network_rank() — shared with bazaar probe so the
    # rail shown/confirmed at probe time is the rail actually paid.
    client.register_policy(prefer_scheme("exact"))
    _mode = "eoa" if is_eoa else "auto"

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
        return 0

    def _prefer_privy_native(version, reqs):
        if is_eoa:  # hard-filter non-EVM: pinned payer cannot sign these
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
                evm_addr=getattr(signer, "address", None),
                sol_addr=(getattr(svm_signer, "address", None)
                          if svm_signer is not None else None))
        except Exception:
            bals, _cn = {}, (lambda n: n)
        return sorted(reqs, key=lambda r: (
            0 if _pn and _net_of(r) == _pn else 1,
            _rail_funded_state(_cn(_net_of(r)), _amt_of(r), bals),
            0 if _cn(_net_of(r)) == "eip155:8453" else 1,
            network_rank(_net_of(r), signer=signer, signer_mode=_mode),
            _amt_of(r)))  # cheapest wins within the same rail rank
            # (matches bazaar._sort_payable so probe display == paid rail)

    client.register_policy(_prefer_privy_native)
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
                "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp":
                    "epjfwdd5aufqssqem2qn1xzybapc8g4weggkzwytdt1v",
            }
            def _canon_network(n):  # noqa: E306
                return "eip155:8453" if n == "base" else (
                    "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp" if n == "solana" else n)
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
    # Return EVM signer for payer metadata; attach svm for diagnostics.
    if svm_signer is not None:
        try:
            signer.svm_address = svm_signer.address
        except Exception:
            pass
    return client, signer


def _sign_platform_payment(accepts: dict, max_amount_atomic: int, signer=None) -> str:
    """Sign an EIP-3009 authorization for a platform-shape 402 (JSON-body
    `accepts` dict with pricingModel — Starchild community-gateway contract).
    Returns the base64 X-PAYMENT header value. Works with any signer that
    implements sign_typed_data (SessionEOASigner or PrivySigner)."""
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
                 allow_fallback_eoa: bool = False,
                 prefer_network: str = ""):
    """One-shot request with automatic x402 payment. Returns dict summary.

    allow_fallback_eoa: 'auto' signer mode is FAIL-CLOSED — if the Privy
    signer cannot be initialized it raises rather than paying from the
    session EOA (a different payer identity). Pass True (or set env
    X402_FALLBACK_EOA=1) to permit the fallback; the result then carries
    signer_type="session_eoa" and a signer_warning.

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
            # No payment happens on this path — report identity best-effort
            # (fallback allowed here since nothing is signed).
            out = {"status": r0.status_code, "body": _body(r0.text),
                   "paid": False}
            try:
                signer = _make_signer(signer_mode, max_amount_atomic,
                                      allow_fallback_eoa=True)
                out.update({"payer": signer.address, **_signer_meta(signer)})
            except Exception:
                pass
            return out

        if r0.headers.get("PAYMENT-REQUIRED") or r0.headers.get("X-PAYMENT-REQUIRED"):
            # V2 header challenge -> x402 SDK path
            client, signer = _build_client(max_amount_atomic, signer_mode,
                                           allow_fallback_eoa, prefer_network)
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
                # Report the ACTUAL selected rail/payer — the SDK may have
                # paid on a different network (e.g. Solana) than the EVM
                # signer's address implies.
                sett = out.get("settlement") if isinstance(out.get("settlement"), dict) else {}
                net = sett.get("network")
                if net:
                    out["network"] = net
                    if str(net).startswith("solana") \
                            and getattr(signer, "svm_address", None):
                        out["payer"] = signer.svm_address
                        out["signer_type"] = "privy_svm"
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
        signer = _make_signer(signer_mode, max_amount_atomic,
                              allow_fallback_eoa)
        _mode = ("eoa" if getattr(signer, "signer_type", "") == "session_eoa"
                 else "auto")

        def _pick_accept(cands: list, prefer_network: str | None = None) -> dict | None:
            """Select one accept for the platform JSON-body path.

            This path signs EIP-3009 via _sign_platform_payment (EVM only) —
            Solana/SVM accepts are never candidates here. External multi-chain
            services that include Solana pay through the V2 header + SDK path
            above (unchanged), which registers the SVM signer.

            Selection: keep prefer_network on prepaid deposit retry; else rank
            EVM rails with network_rank (plain-ECDSA e.g. Monad before
            delegated Base).
            """
            exact = [a for a in cands
                     if isinstance(a, dict) and a.get("scheme") == "exact"]
            if not exact:
                return None
            # Platform path = EVM EIP-3009 only. Drop Solana/other non-EVM so
            # network_rank cannot pick a rail we cannot sign here.
            exact = [a for a in exact
                     if str(a.get("network") or "").startswith("eip155:")
                     or str(a.get("network") or "") == "base"]
            if not exact:
                return None
            def _amt(a):
                try:
                    return int(str(a.get("amount") or 0))
                except (TypeError, ValueError):
                    return 0
            if prefer_network:
                same = [a for a in exact
                        if str(a.get("network") or "") == prefer_network]
                if same:
                    return sorted(same, key=_amt)[0]  # cheapest on that chain
            # Funded rails first, Base as default chain, then network_rank
            # (see _prefer_privy_native for rationale — same ordering).
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
                network_rank(str(a.get("network") or ""),
                             signer=signer, signer_mode=_mode),
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
            xp = _sign_platform_payment(accepts, max_amount_atomic, signer=signer)
            _ledger_append({"event": "signed", "url": url,
                            "method": method.upper(), "payer": signer.address,
                            "amount_atomic": accepts.get("amount"),
                            "pricing_model": accepts.get("pricingModel"),
                            "network": accepts.get("network"),
                            "pay_to": accepts.get("payTo"),
                            "flavor": "platform", **_signer_meta(signer)})
            async with _httpx.AsyncClient(timeout=timeout, follow_redirects=True) as plain:
                r2 = await plain.request(method.upper(), url, json=json_body,
                                         headers={**(headers or {}), "X-PAYMENT": xp})
            _ledger_append({"event": "result", "url": url,
                            "method": method.upper(), "payer": signer.address,
                            "amount_atomic": accepts.get("amount"),
                            "status": r2.status_code,
                            "paid": r2.status_code == 200,
                            "network": accepts.get("network"),
                            "flavor": "platform", **_signer_meta(signer)})
            if r2.status_code != 402:
                break
            try:
                nxt_raw = json.loads(r2.text or "{}").get("accepts")
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
        return {"status": r2.status_code, "payer": signer.address, "paid": True,
                **_signer_meta(signer),
                "pricing_model": accepts.get("pricingModel"),
                "network": accepts.get("network"),
                "body": _body(r2.text, full=True)}

    return asyncio.run(run())


_BAL_CACHE: dict = {}   # (canonical_net, payer_addr) -> (ts, atomic_balance)


def usdc_balances(networks, evm_addr=None, sol_addr=None,
                  ttl: float = 60.0) -> dict:
    """Best-effort USDC balance (atomic units) per canonical network.

    None = unknown (RPC failure, unsupported network, or no address for that
    chain type). Cached ``ttl`` seconds per (network, address) so the several
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
        addr = sol_addr if net.startswith("solana") else evm_addr
        if not usdc or not addr:
            out[net] = None
            continue
        ck = (net, addr)
        hit = _BAL_CACHE.get(ck)
        if hit and ttl > 0 and _t.time() - hit[0] < ttl:
            out[net] = hit[1]
            continue
        bal = None
        try:
            if net.startswith("solana"):
                import httpx
                resp = httpx.post("https://api.mainnet-beta.solana.com", json={
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [addr,
                               {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"},
                               {"encoding": "jsonParsed"}]}, timeout=15)
                resp.raise_for_status()
                r = resp.json()
                # RPC error / malformed result = UNKNOWN, never zero —
                # a flaky RPC must not demote a funded rail.
                if "error" in r or not isinstance(
                        r.get("result", {}).get("value"), list):
                    raise RuntimeError(f"solana rpc error: "
                                       f"{str(r.get('error'))[:120]}")
                bal = sum(int(v["account"]["data"]["parsed"]["info"]
                              ["tokenAmount"]["amount"])
                          for v in r["result"]["value"])
            else:
                from web3 import Web3
                rpc = PrivySigner._RPC.get(int(net.split(":")[1]))
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
    selected signer cannot sign is NOT a candidate) ② wallet policy sanity
    (an ENABLED policy with EMPTY rules = deny-all → blocks every signature;
    new Privy wallets should be allow-all, so this is an anomaly to fix via
    a policy card BEFORE payment) ③ USDC balance per signable rail — ok
    requires at least ONE rail that is both signable AND verified funded;
    unknown (RPC-failed) balances never count as funded.

    networks: candidate rails from the service's 402 accepts (canonical ids,
    e.g. ["eip155:8453", "solana:5eykt..."]). Default: Base+Monad+Solana.
    Returns {ok, blockers[], warnings[], payer{}, funded_rails[], balances{}}.
    """
    from bazaar import PAYABLE_USDC, _canon_network, SOLANA_MAINNET
    out = {"ok": True, "blockers": [], "warnings": [], "payer": {},
           "balances": {}, "funded_rails": []}
    nets = [_canon_network(n) for n in (networks or
            ["eip155:8453", "eip155:143", SOLANA_MAINNET])]

    # ① signers — branch by signer_mode FIRST. Explicit EOA never touches
    # the Privy wallet service or its policy.
    evm_addr = sol_addr = None
    if signer_mode == "eoa":
        try:
            eoa = SessionEOASigner()
            evm_addr = eoa.address
        except Exception as e:
            out["blockers"].append(f"session EOA signer unavailable: {e}")
    else:
        try:
            from core.skill_tools import wallet as _w
            info = _w.wallet_info()
            for w in (info.get("wallets") if isinstance(info, dict) else info) or []:
                if w.get("chain_type") == "ethereum":
                    evm_addr = w.get("wallet_address") or w.get("address")
                elif w.get("chain_type") == "solana":
                    sol_addr = w.get("wallet_address") or w.get("address")
        except Exception as e:
            out["blockers"].append(f"wallet skill unavailable: {e}")
    out["payer"] = {"evm": evm_addr, "solana": sol_addr}

    # Capability filter: keep only rails the selected signer can sign.
    def _signable(net):
        if net.startswith("eip155:"):
            return evm_addr is not None
        if net.startswith("solana"):
            return signer_mode != "eoa" and sol_addr is not None
        return False

    unsignable = [n for n in nets if PAYABLE_USDC.get(n) and not _signable(n)]
    nets = [n for n in nets if PAYABLE_USDC.get(n) and _signable(n)]
    if unsignable:
        out["warnings"].append(
            f"rails excluded (signer '{signer_mode}' cannot sign them): "
            f"{unsignable}")
    if not nets:
        out["blockers"].append(
            f"no signable payment rail: signer_mode='{signer_mode}' cannot "
            f"sign any of the service's accepted networks "
            f"({unsignable or networks}). "
            + ("Session EOA is EVM-only — use signer_mode='auto' for Solana."
               if signer_mode == "eoa" else
               "Check wallet availability for the required chain types."))

    # ② policy sanity — PER-RAIL, not global. The Ethereum policy only
    # gates EVM rails: a deny-all EVM policy must not block a payment that
    # will route via Solana. A rail whose policy blocks signing is removed
    # from the candidates (with a warning); it escalates to a blocker only
    # if NO signable rail remains.
    evm_nets = [n for n in nets if n.startswith("eip155:")]
    if signer_mode != "eoa" and evm_addr and evm_nets:
        try:
            from core.skill_tools import wallet as _w
            pol = _w.wallet_get_policy(chain_type="ethereum")
            rules = (pol or {}).get("rules") or []
            if (pol or {}).get("enabled") and not rules:
                nets = [n for n in nets if not n.startswith("eip155:")]
                msg = ("EVM wallet policy is ENABLED with EMPTY rules "
                       "(deny-all) — EVM payment signatures will be "
                       "rejected. Propose a policy update (deny "
                       "exportPrivateKey, allow rest) and have the user "
                       "sign it before paying on an EVM rail.")
                if nets:  # other rails (e.g. Solana) remain usable
                    out["warnings"].append(
                        msg + f" EVM rails excluded: {evm_nets}; "
                        f"continuing with {nets}.")
                else:
                    out["blockers"].append(
                        msg + " No non-EVM rail is available for this "
                        "service, so this blocks the payment.")
            elif rules and not any(
                    r.get("action") == "ALLOW" and r.get("method") in ("*",
                    "signTypedData", "eth_signTypedData_v4") for r in rules):
                out["warnings"].append(
                    "wallet policy has no ALLOW rule covering typed-data "
                    "signing — EVM payment may be denied.")
        except Exception as e:
            out["warnings"].append(f"policy check failed (non-fatal): {e}")

    # ③ balances per signable rail (direct RPC; no DeBank round-trip).
    # ttl=0: preflight always reads LIVE, but refreshes the shared routing
    # cache so the payment that follows reuses these balances for rail
    # selection (funded-first ordering in _prefer_privy_native).
    out["balances"] = usdc_balances(nets, evm_addr=evm_addr,
                                    sol_addr=sol_addr, ttl=0)
    for net, bal in out["balances"].items():
        if bal is not None and bal >= amount_atomic:
            out["funded_rails"].append(net)

    # ④ dependency sanity: buyer path needs web3>=7. NEVER upgrade a pinned
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
                "Retry, or verify balances via the wallet skill before "
                "proceeding.")
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
