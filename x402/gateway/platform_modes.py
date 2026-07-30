"""Platform pricing modes for the x402 gateway — Starchild community-gateway contract.

Implements the three platform-standard pricing models from
x402-facilitator/docs/pricing-models.md:

  pay_per_use  verify -> settle on EVERY request (no history check)
  lifetime     verify -> settle once; later requests check facilitator
               settlements (payer paid pay_to before = permanent access)
  monthly      like lifetime but access expires one natural month after
               payment (same day next month, clamped to month end)
  prepaid      one on-chain deposit (/facilitator/deposit-settle) credits a
               (payer, pay_to) balance held by the facilitator; every call is
               then a millisecond off-chain /facilitator/debit — no per-call
               settle, no per-payer settle rate limit, per-call price can be
               metered via route units. The per-call X-PAYMENT signature is
               used for AUTHENTICATION only (verify, never settled) unless the
               balance is insufficient AND the signed value covers the deposit
               minimum, in which case it IS the deposit.

Multi-chain support (plans-280-04 §5.6):
  * ASSETS mirrors the facilitator KNOWN_ASSETS across Base + Monad + Robinhood + X Layer (mainnet
    and testnet).
  * resolve_networks(cfg) implements the all/custom model — "all" follows the
    platform mainnet (or testnet) full set; "custom" locks to an explicit list.
    No "legacy Base -> all" guessing: historical configs are migrated once
    (§5.6.1.1), resolve_networks never infers "all" from a bare network field.
  * 402 challenge_body returns accepts as a LIST (standard x402 multi-accepts,
    one entry per network). The buyer picks one rail per payment.
  * verify/settle/deposit bind the buyer's chosen accept (parsed from the
    payment payload's network field) — never re-derive from a single config
    network.
  * prepaid balance is cumulative across chains (facilitator ledger key is
    (payer, pay_to), not per-network).

Contract points (must match the platform audit checklist, doc §12):
  * 402 JSON body: {x402Version:2, error, accepts:[{...,"pricingModel":<mode>}]}
  * client sends X-PAYMENT header (base64 JSON payload); PAYMENT-SIGNATURE
    is accepted as an alias for x402 SDK buyers
  * facilitator is the single source of truth for "already paid"
    (/facilitator/access-status for lifetime, /facilitator/settlements
    for monthly) — the gateway keeps NO local payment state
"""
from __future__ import annotations

import base64
import calendar
import json
import os
import time
from datetime import datetime, timezone

import httpx

PLATFORM_MODES = ("pay_per_use", "lifetime", "monthly", "weekly", "quarterly",
                  "yearly", "prepaid")

# time-limited subscriptions expressed as fixed-length passes. The facilitator
# validates pricing_model in (lifetime, monthly) only; weekly/quarterly/yearly
# are queried as pricing_model=monthly + period_days=N (facilitator contract,
# docs/pricing-models.md — access expires N days after the newest qualifying
# payment). monthly WITHOUT period_days keeps natural-month semantics.
PERIOD_DAYS = {"weekly": 7, "quarterly": 90, "yearly": 365}
SUBSCRIPTION_MODES = ("lifetime", "monthly", "weekly", "quarterly", "yearly")


class AccessCheckError(Exception):
    """already_paid() could not get an authoritative answer (auth failure,
    facilitator down, ...). Callers MUST surface an error instead of settling —
    'unknown' is not 'unpaid'; treating it as unpaid re-settles on every
    request and silently double-charges the buyer."""


# ---------------------------------------------------------------------------
# Multi-chain asset registry — mirror of facilitator KNOWN_ASSETS
# (x402-facilitator/server.py). When the facilitator adds a chain, add it
# here AND to MAINNET_NETWORKS / TESTNET_NETWORKS below.
# ---------------------------------------------------------------------------
# network -> (usdc_asset, extra name/version)
ASSETS = {
    # Base mainnet: USDC name is "USD Coin" (verified on-chain).
    "eip155:8453":  ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", {"name": "USD Coin", "version": "2"}),
    # Base Sepolia (testnet): USDC name is "USDC".
    "eip155:84532": ("0x036CbD53842c5426634e7929541eC2318f3dCF7e", {"name": "USDC", "version": "2"}),
    # Monad mainnet: USDC name is "USDC" (verified via cast call, plans-280-04 §13.2).
    "eip155:143":   ("0x754704bc059f8c67012fed69bc8a327a5aafb603", {"name": "USDC", "version": "2"}),
    # Monad testnet: USDC name is "USDC".
    "eip155:10143": ("0x534b2f3A21130d7a60830c2Df862319e593943A3", {"name": "USDC", "version": "2"}),
    # Robinhood mainnet: USDG (Global Dollar), Diamond proxy, non-standard EIP-712 domain.
    # The buyer must use chain-read DOMAIN_SEPARATOR() for signing (see client.py).
    "eip155:4663":  ("0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168",
                     {"name": "Global Dollar", "version": "1"}),
    # Robinhood testnet: USDG (Global Dollar).
    "eip155:46630": ("0x7E955252E15c84f5768B83c41a71F9eba181802F",
                     {"name": "Global Dollar", "version": "1"}),
    # X Layer mainnet: USDC (Circle FiatTokenV2, standard EIP-712 domain).
    "eip155:196":   ("0x74b7F16337b8972027F6196A17a631aC6dE26d22",
                     {"name": "USD Coin", "version": "2"}),
    # X Layer testnet: USDC_TEST (FiatTokenV2, different contract + name from mainnet).
    "eip155:1952":  ("0xcb8bf24c6ce16ad21d707c9505421a17f2bec79d",
                     {"name": "USDC_TEST", "version": "2"}),
}

# Solana: SPL Token USDC (not EIP-3009; uses x402 SDK ExactSvmScheme).
# feePayer is the platform facilitator's Solana public key. Hardcoded here
# so all agent containers automatically include Solana in their 402 accepts
# without needing any extra env var. Override via X402_SOLANA_FEE_PAYER if
# the facilitator key ever changes.
_PLATFORM_SOL_FEE_PAYER = "FYgkFMkvHwVhUJBm9zhboJPtHxZT5Qtx1TN59zxPpQ7g"
_sol_fee_payer = os.environ.get("X402_SOLANA_FEE_PAYER", "").strip() or _PLATFORM_SOL_FEE_PAYER
ASSETS["solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"] = (
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    {"feePayer": _sol_fee_payer},
)
# Solana devnet (optional, for local testing only — requires explicit env var)
_sol_devnet_fee_payer = os.environ.get("X402_SOLANA_DEVNET_FEE_PAYER", "").strip()
if _sol_devnet_fee_payer:
    ASSETS["solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1"] = (
        "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
        {"feePayer": _sol_devnet_fee_payer},
    )

# Platform network full sets — "all" resolves to these. Extend here when the
# facilitator adds a new mainnet/testnet chain (no business-table UPDATE needed:
# all-configured services pick up the new chain on next 402 automatically).
_evm_mainnet = ("eip155:8453", "eip155:143", "eip155:4663", "eip155:196")     # Base + Monad + Robinhood + X Layer
_evm_testnet = ("eip155:84532", "eip155:10143", "eip155:46630", "eip155:1952")  # Base Sepolia + Monad + Robinhood + X Layer
# Solana mainnet is always included (feePayer defaults to platform facilitator key)
MAINNET_NETWORKS = _evm_mainnet + ("solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",)
TESTNET_NETWORKS = _evm_testnet + (("solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1",) if _sol_devnet_fee_payer else ())


def platform_mainnet_networks() -> list[str]:
    """Current platform mainnet set (filtered to chains present in ASSETS)."""
    return [n for n in MAINNET_NETWORKS if n in ASSETS]


def platform_testnet_networks() -> list[str]:
    """Current platform testnet set (filtered to chains present in ASSETS)."""
    return [n for n in TESTNET_NETWORKS if n in ASSETS]


def _is_testnet_profile(cfg: dict) -> bool:
    """Detect whether this config targets testnets. Explicit flag wins;
    otherwise auto-detect from the facilitator URL (x402.org is testnet-only).
    The old single ``network`` field is NOT consulted here — resolve_networks
    does not do "legacy Base -> all" guessing (plans-280-04 §5.6.1)."""
    profile = cfg.get("networks_profile")
    if profile == "testnet":
        return True
    if profile == "mainnet":
        return False
    # Auto-detect: the x402.org facilitator is testnet-only.
    fac = cfg.get("facilitator") or ""
    if "x402.org" in fac:
        return True
    return False


def _validate_custom(nets: list) -> list[str]:
    """Validate a custom network list: every entry must be a known asset,
    de-duplicated, order-preserved."""
    out: list[str] = []
    for n in nets:
        if n not in ASSETS:
            raise ValueError(
                f"unsupported network {n!r} (known: {list(ASSETS)})")
        if n not in out:
            out.append(n)
    return out


def resolve_networks(cfg: dict) -> list[str]:
    """Resolve the configured network list (plans-280-04 §5.6.1).

    cfg keys:
      networks_mode: "all" | "custom"  (absent -> treated as "all" when
                                        networks is also absent/empty)
      networks: "all" | ["eip155:…", …]
      networks_profile: "mainnet" | "testnet" | absent (auto-detect)

    Returns a non-empty list of CAIP-2 network ids. Raises ValueError on
    illegal combinations (e.g. networks_mode=custom with empty list).

    Deliberately does NOT implement "legacy network=Base -> all": historical
    configs are migrated once (§5.6.1.1); resolve_networks never guesses that
    a bare Base config means "all networks".
    """
    mode = cfg.get("networks_mode")
    nets = cfg.get("networks")
    is_testnet = _is_testnet_profile(cfg)
    base = platform_testnet_networks if is_testnet else platform_mainnet_networks

    if nets == "all" or mode == "all" or (mode is None and not nets):
        return base()
    if isinstance(nets, list) and len(nets) > 0:
        return _validate_custom(nets)
    if mode == "custom":
        raise ValueError("networks_mode=custom requires a non-empty networks list")
    # Fallback: treat as "all" (shouldn't reach here with well-formed configs).
    return base()


# ─── Dynamic asset-info lookup (plans-290) ────────────────────────────
# Cache: {network: {"asset": ..., "extra": ...}} or {network: None}
_asset_info_cache: dict = {}
_ASSET_INFO_CACHE_TTL = 300  # 5 minutes


def _fetch_asset_info(network: str, community_gateway_url: str) -> dict | None:
    """Fetch asset info for a network from community-gateway's /asset-info API.

    Used by _match_accept when the buyer signs for a network this gateway
    doesn't know about (added after startup). The community-gateway maintains
    the authoritative X402_ASSETS registry and exposes it via a public API.

    Returns {"asset": "0x...", "extra": {"name": ..., "version": ...}} or None.
    Cached for 5 minutes to avoid per-request HTTP calls.
    """
    cached = _asset_info_cache.get(network)
    if cached is not None:
        ts, info = cached
        if time.time() - ts < _ASSET_INFO_CACHE_TTL:
            return info

    if not community_gateway_url:
        # Try the default production URL
        community_gateway_url = os.environ.get(
            "COMMUNITY_PUBLIC_URL", "https://community.iamstarchild.com")

    try:
        url = f"{community_gateway_url}/api/x402-facilitator/asset-info/{network}"
        resp = httpx.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            info = {"asset": data["asset"], "extra": data.get("extra", {})}
            _asset_info_cache[network] = (time.time(), info)
            return info
        _asset_info_cache[network] = (time.time(), None)
        return None
    except Exception:
        # Network error — don't cache failures, fall through to legacy matching
        return None


_access_cache: dict = {}  # (payer, mode) -> (expires_ts, has_access)
_CACHE_TTL = 60


class PlatformBilling:
    def __init__(self, cfg: dict):
        self.mode = cfg["mode"]
        self.pay_to = cfg["pay_to"]
        # Solana pay_to: Base58 address for Solana networks. If absent, Solana
        # networks are excluded from the 402 accepts list (plans-292).
        self.sol_pay_to = cfg.get("sol_pay_to", "")
        # Multi-chain: resolve the full network list from config. The price is
        # the same across all networks (same amount_atomic); only the asset
        # address and EIP-712 domain differ per chain.
        self.networks = resolve_networks(cfg)
        if not self.networks:
            raise ValueError("config resolved to an empty networks list")
        # Backward compat: single-network field (first of the list). Used by
        # app.py info/discovery endpoints that still expose a scalar `network`.
        self.network = self.networks[0]
        price = str(cfg.get("price_usd", "0.01")).lstrip("$")
        self.amount_atomic = str(int(round(float(price) * 1_000_000)))
        self.facilitator = (cfg.get("facilitator") or "").rstrip("/")
        if not self.facilitator:
            raise ValueError("platform modes require an explicit `facilitator` URL")
        self.fac_token = cfg.get("facilitator_token") or ""
        # settlements/access-status are admin-gated on the platform facilitator
        self.fac_admin_token = cfg.get("facilitator_admin_token") or ""
        # community-gateway proxy: when the gateway doesn't have the admin
        # token (user containers), it can query access-status through the
        # community-gateway proxy which holds the token server-side.
        self.community_gateway_url = (
            cfg.get("community_gateway_url")
            or os.environ.get("COMMUNITY_PUBLIC_URL", "")
        ).rstrip("/")
        # Internal API key for authenticating to community-gateway proxy
        self._internal_api_key = (
            cfg.get("internal_api_key")
            or os.environ.get("INTERNAL_API_KEY", "")
        )
        if self.mode in SUBSCRIPTION_MODES and not self.fac_admin_token and not self.community_gateway_url:
            # fail-closed at STARTUP: without either the admin token (direct)
            # or a community-gateway URL (proxy), every already_paid() lookup
            # would fail and, if treated as unpaid, the gateway would re-settle
            # on EVERY request — silently double-charging buyers.
            raise ValueError(
                f"mode '{self.mode}' requires either `facilitator_admin_token` "
                "or COMMUNITY_PUBLIC_URL (for proxied access-status checks)")
        # prepaid: suggested deposit size. Default 100 calls worth, floored at
        # the facilitator's default minimum deposit ($0.10 = 100000 atomic).
        dep = cfg.get("deposit_usd")
        if dep is not None:
            self.deposit_atomic = int(round(float(str(dep).lstrip("$")) * 1_000_000))
        else:
            self.deposit_atomic = max(int(self.amount_atomic) * 100, 100_000)
        self._verify_cache: dict = {}  # signature -> (valid_until_ts, payer)

    # -- requirements / 402 -------------------------------------------------

    def _pay_to_for_network(self, network: str) -> str | None:
        """Return the correct payTo address for a network, or None if unavailable.
        Solana networks require a Base58 address; EVM networks use 0x addresses."""
        if network.startswith("solana:"):
            return self.sol_pay_to or None
        return self.pay_to

    def requirements_for(self, network: str, resource: str = "") -> dict | None:
        """Build a single accept object for a specific network (plans-280-04
        §5.6.2). Returns None if the network requires an address we don't have
        (e.g. Solana without sol_pay_to — plans-292)."""
        if network not in ASSETS:
            raise ValueError(f"unsupported network {network}")
        pay_to = self._pay_to_for_network(network)
        if pay_to is None:
            return None  # no Solana address configured, skip this network
        asset, extra = ASSETS[network]
        req = {
            "scheme": "exact",
            "network": network,
            "amount": self.amount_atomic,
            "asset": asset,
            "payTo": pay_to,
            "maxTimeoutSeconds": 300,
            "extra": dict(extra),
            "pricingModel": self.mode,
        }
        if resource:
            req["resource"] = resource
        if self.mode == "prepaid":
            # what the buyer signs by default is the PER-CALL price (auth-only
            # signature); depositAtomic tells them what to sign when the
            # gateway answers insufficient_balance.
            req["depositAtomic"] = str(self.deposit_atomic)
            req["pricePerCallAtomic"] = self.amount_atomic
        return req

    def requirements(self, resource: str = "") -> list[dict]:
        """Multi-accepts: one accept object per configured network. The 402
        challenge and discovery endpoint return this list; the buyer picks one
        rail per payment (plans-280-04 §5.6.2)."""
        return [r for n in self.networks if (r := self.requirements_for(n, resource)) is not None]

    def challenge_body(self, resource: str = "", error: str = "X-PAYMENT header is required",
                       deposit: bool = False) -> dict:
        """402 body with accepts as a LIST (one entry per network). deposit=True
        (prepaid only) swaps each accept's amount to the deposit size — the
        client signs accepts.amount, so this is how the gateway asks for a
        top-up instead of an auth signature."""
        accepts = self.requirements(resource)
        if deposit and self.mode == "prepaid":
            for acc in accepts:
                acc["amount"] = str(self.deposit_atomic)
        return {"x402Version": 2, "error": error, "accepts": accepts}

    def _match_accept(self, payload: dict, resource: str) -> dict:
        """Find the accept that matches the buyer's signed payload. The buyer
        signs exactly one accept (one network); we must send THAT accept as
        paymentRequirements to the facilitator — never a different chain's
        asset/domain (plans-280-04 §5.6.3).

        Matching priority:
        1. payload.network (set by the client SDK on the X-PAYMENT header)
        2. authorization verifying asset (EIP-712 domain / top-level asset)
        3. authorization.to + value (fallback for clients that omit network;
           value may be deposit size for prepaid top-up, so amount is not
           required to equal the per-call price)
        4. first network (last resort; facilitator rejects asset mismatch)
        """
        net = payload.get("network", "")
        if net and net in self.networks:
            req = self.requirements_for(net, resource)
            if req is not None:
                return req
        # Graceful handling for networks added to the platform AFTER this
        # gateway process started (plans-290). The community-gateway proxy
        # supplements 402 accepts with new-chain entries, so a buyer may sign
        # for a network this running gateway doesn't know about. Fetch the
        # asset info dynamically from community-gateway's /asset-info API
        # so the facilitator receives the correct chain/asset — no dependency
        # on ASSETS or self.networks being up to date.
        if net and net not in self.networks:
            asset_info = _fetch_asset_info(net, self.community_gateway_url)
            if asset_info:
                pay_to = self._pay_to_for_network(net)
                if pay_to is None:
                    pass  # no address for this network, fall through
                else:
                    req = {
                        "scheme": "exact",
                        "network": net,
                        "amount": self.amount_atomic,
                        "asset": asset_info["asset"],
                        "payTo": pay_to,
                        "maxTimeoutSeconds": 300,
                        "extra": asset_info.get("extra", {}),
                        "pricingModel": self.mode,
                    }
                    if resource:
                        req["resource"] = resource
                    if self.mode == "prepaid":
                        req["depositAtomic"] = str(self.deposit_atomic)
                        req["pricePerCallAtomic"] = self.amount_atomic
                    return req
        auth = payload.get("payload", {}).get("authorization", {}) or {}
        to = (auth.get("to") or "").lower()
        val = str(auth.get("value", ""))
        # Prefer matching the signed asset address when present (covers prepaid
        # deposits where value != per-call amount, and clients that omit network).
        asset_hint = (
            str(payload.get("asset") or "").lower()
            or str((payload.get("payload") or {}).get("asset") or "").lower()
        )
        if asset_hint:
            for n in self.networks:
                req = self.requirements_for(n, resource)
                if req["asset"].lower() == asset_hint and req["payTo"].lower() == (to or req["payTo"].lower()):
                    return req
        for n in self.networks:
            req = self.requirements_for(n, resource)
            if req["payTo"].lower() == to and (not val or req["amount"] == val
                                               or val == str(self.deposit_atomic)):
                return req
        # Last resort: first network with a valid payTo. This should not happen
        # with well-formed clients; the facilitator will reject if the asset/domain mismatches.
        for n in self.networks:
            req = self.requirements_for(n, resource)
            if req is not None:
                return req
        # All networks skipped (no valid payTo) — return EVM first network as fallback
        # (facilitator will reject the mismatched payTo)
        return {"scheme": "exact", "network": self.networks[0], "amount": self.amount_atomic,
                "asset": ASSETS[self.networks[0]][0], "payTo": self.pay_to,
                "maxTimeoutSeconds": 300, "extra": dict(ASSETS[self.networks[0]][1]),
                "pricingModel": self.mode}

    # -- facilitator calls ---------------------------------------------------
    def _headers(self, admin: bool = False) -> dict:
        h = {"Content-Type": "application/json"}
        if self.fac_token:
            h["Authorization"] = f"Bearer {self.fac_token}"
        if admin and self.fac_admin_token:
            h["X-Admin-Token"] = self.fac_admin_token
        return h

    async def verify(self, payload: dict, resource: str) -> dict:
        req = self._match_accept(payload, resource)
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(f"{self.facilitator}/verify", headers=self._headers(),
                             json={"x402Version": 2, "paymentPayload": payload,
                                   "paymentRequirements": req})
            return r.json()

    async def settle(self, payload: dict, resource: str) -> dict:
        req = self._match_accept(payload, resource)
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{self.facilitator}/settle", headers=self._headers(),
                             json={"x402Version": 2, "paymentPayload": payload,
                                   "paymentRequirements": req})
            return r.json()

    # -- prepaid: balance / deposit / debit (facilitator holds the ledger) ---
    async def verify_cached(self, payload: dict, resource: str) -> dict:
        """Facilitator /verify with a signature cache: a buyer may reuse one
        signed payload within its validity window, so identical signatures
        skip the round-trip. Safe: the signature itself is the bearer secret
        (only the key holder ever had it), and the cache expires at the
        authorization's validBefore."""
        sig = str(payload.get("payload", {}).get("signature", ""))
        now = time.time()
        hit = self._verify_cache.get(sig)
        if hit and hit[0] > now:
            return {"isValid": True, "payer": hit[1], "cached": True}
        v = await self.verify(payload, resource)
        if v.get("isValid"):
            auth = payload.get("payload", {}).get("authorization", {}) or {}
            try:
                valid_until = min(float(auth.get("validBefore", 0)), now + 600)
            except (TypeError, ValueError):
                valid_until = now + 60
            self._verify_cache[sig] = (valid_until - 5, str(v.get("payer", "")))
            if len(self._verify_cache) > 10000:
                self._verify_cache.clear()
        return v

    async def balance(self, payer: str) -> int:
        # Balance query: EVM and Solana deposits use different pay_to addresses,
        # so we query both and sum them (plans-292). A buyer who deposits on
        # Monad draws from (payer, evm_pay_to); a Solana deposit draws from
        # (payer, sol_pay_to). The gateway sums both for a unified view.
        total = 0
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{self.facilitator}/facilitator/balance",
                            params={"payer": payer, "pay_to": self.pay_to},
                            headers=self._headers())
            r.raise_for_status()
            total += int(r.json().get("balance_atomic", 0))
            if self.sol_pay_to:
                try:
                    r2 = await c.get(f"{self.facilitator}/facilitator/balance",
                                     params={"payer": payer, "pay_to": self.sol_pay_to},
                                     headers=self._headers())
                    r2.raise_for_status()
                    total += int(r2.json().get("balance_atomic", 0))
                except Exception:
                    pass  # Solana balance query failed, use EVM balance only
        return total

    async def deposit(self, payload: dict, resource: str) -> dict:
        """Forward the signed payload to /facilitator/deposit-settle (on-chain
        settle that credits the payer/pay_to prepaid balance). The accept is
        matched to the buyer's chosen network; the signed value overrides the
        per-call amount so the facilitator settles the deposit size."""
        auth = payload.get("payload", {}).get("authorization", {}) or {}
        req = self._match_accept(payload, resource)
        req["amount"] = str(auth.get("value", req["amount"]))
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{self.facilitator}/facilitator/deposit-settle",
                             headers=self._headers(),
                             json={"x402Version": 2, "paymentPayload": payload,
                                   "paymentRequirements": req})
            return r.json()

    async def debit(self, payer: str, request_id: str, units: int = 1,
                    route: str = "") -> dict:
        amount = int(self.amount_atomic) * max(int(units), 1)
        async with httpx.AsyncClient(timeout=15) as c:
            # Try EVM pay_to first (most common)
            r = await c.post(f"{self.facilitator}/facilitator/debit",
                             headers=self._headers(),
                             json={"payer": payer, "pay_to": self.pay_to,
                                   "amount_atomic": amount,
                                   "request_id": request_id, "route": route})
            result = r.json()
            # If insufficient on EVM and Solana pay_to exists, try Solana balance
            if not result.get("ok") and result.get("error") == "insufficient_balance" and self.sol_pay_to:
                r2 = await c.post(f"{self.facilitator}/facilitator/debit",
                                  headers=self._headers(),
                                  json={"payer": payer, "pay_to": self.sol_pay_to,
                                        "amount_atomic": amount,
                                        "request_id": request_id, "route": route})
                sol_result = r2.json()
                if sol_result.get("ok"):
                    return sol_result
            return result

    async def refund(self, payer: str, request_id: str, units: int = 1,
                     route: str = "") -> None:
        """Credit back a debit after an upstream failure (negative debit with a
        derived request_id, so it is idempotent and never collides).
        Tries EVM pay_to first; if the original debit was against Solana
        pay_to, the refund must go there too (idempotent request_id ensures
        no double-credit)."""
        amount = -int(self.amount_atomic) * max(int(units), 1)
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(f"{self.facilitator}/facilitator/debit",
                                 headers=self._headers(),
                                 json={"payer": payer, "pay_to": self.pay_to,
                                       "amount_atomic": amount,
                                       "request_id": f"{request_id}:refund",
                                       "route": route})
                # If EVM refund was a replay (original debit was on Solana), try Solana
                if self.sol_pay_to and r.json().get("error") == "insufficient_balance":
                    await c.post(f"{self.facilitator}/facilitator/debit",
                                 headers=self._headers(),
                                 json={"payer": payer, "pay_to": self.sol_pay_to,
                                       "amount_atomic": amount,
                                       "request_id": f"{request_id}:refund",
                                       "route": route})
        except Exception as e:
            print(f"[x402-platform] prepaid refund failed: {e}", flush=True)

    # -- already-paid check (facilitator = source of truth) ------------------
    @staticmethod
    def _monthly_valid(confirmed_at: float) -> bool:
        """Natural month: expires same day next month, clamped to month end."""
        paid = datetime.fromtimestamp(confirmed_at, tz=timezone.utc)
        y, m = (paid.year + 1, 1) if paid.month == 12 else (paid.year, paid.month + 1)
        day = min(paid.day, calendar.monthrange(y, m)[1])
        expires = paid.replace(year=y, month=m, day=day)
        return datetime.now(tz=timezone.utc) < expires

    async def already_paid(self, payer: str) -> bool:
        if self.mode == "pay_per_use":
            return False
        payer = payer.lower()
        now = time.time()
        hit = _access_cache.get((payer, self.mode))
        if hit and hit[0] > now:
            return hit[1]

        # Choose the access-status endpoint:
        # 1. Direct facilitator (has admin token) — fastest, no extra hop
        # 2. Community-gateway proxy (no admin token) — gateway holds the
        #    token server-side, user containers call it with INTERNAL_API_KEY
        use_proxy = not self.fac_admin_token and self.community_gateway_url
        if use_proxy:
            access_url = f"{self.community_gateway_url}/api/x402-facilitator/access-status"
            access_headers: dict = {}
            if self._internal_api_key:
                access_headers["X-INTERNAL-API-KEY"] = self._internal_api_key
        else:
            access_url = f"{self.facilitator}/facilitator/access-status"
            access_headers = self._headers(admin=True)

        has = False
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                # Single endpoint for both models. min_amount = the service
                # price, so historic smaller payments to the same pay_to
                # (e.g. old pay_per_use calls) can never unlock this service.
                # For monthly the facilitator computes natural-month expiry
                # server-side and returns expires_at.
                # Access-status is network-agnostic: a payer who settled on
                # Monad has access on Base too (same pay_to, same price).
                # Query access-status for EVM pay_to first; if not found and
                # sol_pay_to exists, also check Solana pay_to (plans-292:
                # a Solana payment should grant access same as EVM).
                params = {"payer": payer, "pay_to": self.pay_to,
                          "min_amount": self.amount_atomic,
                          "pricing_model": ("monthly" if self.mode in PERIOD_DAYS
                                            else self.mode)}
                if self.mode in PERIOD_DAYS:
                    params["period_days"] = PERIOD_DAYS[self.mode]
                r = await c.get(access_url, params=params,
                                headers=access_headers)
                if r.status_code == 200:
                    has = bool(r.json().get("has_access"))
                # If EVM pay_to has no access and Solana pay_to exists, check Solana
                if not has and self.sol_pay_to:
                    try:
                        sol_params = dict(params)
                        sol_params["pay_to"] = self.sol_pay_to
                        r_sol = await c.get(access_url, params=sol_params,
                                            headers=access_headers)
                        if r_sol.status_code == 200:
                            has = bool(r_sol.json().get("has_access"))
                    except Exception:
                        pass  # Solana check failed, use EVM result
                if r.status_code == 200:
                    pass  # already handled above
                elif r.status_code == 400 and self.mode == "monthly" and not use_proxy:
                    # (weekly/quarterly/yearly deliberately have no fallback:
                    # a facilitator too old for period_days can't answer them)
                    # fallback ONLY for facilitators that reject the
                    # pricing_model param (pre-support versions): pull this
                    # payer/pay_to pair's settlements and compute expiry.
                    # NOTE: this fallback only works with direct facilitator
                    # access (admin token); the proxy doesn't expose /settlements.
                    since = now - 40 * 86400  # covers any natural month
                    r = await c.get(f"{self.facilitator}/facilitator/settlements",
                                    params={"since": since, "limit": 1000,
                                            "payer": payer, "pay_to": self.pay_to},
                                    headers=self._headers(admin=True))
                    if r.status_code != 200:
                        raise AccessCheckError(
                            f"settlements fallback -> HTTP {r.status_code}: {r.text[:200]}")
                    for s in r.json().get("settlements", []):
                        if (int(s.get("amount_atomic") or 0) >= int(self.amount_atomic)
                                and s.get("status") == "confirmed"
                                and self._monthly_valid(float(s.get("confirmed_at") or 0))):
                            has = True
                            break
                else:
                    # 401/403/5xx/anything: NOT an authoritative "unpaid".
                    # Treating it as unpaid would settle again -> double charge.
                    raise AccessCheckError(
                        f"access-status -> HTTP {r.status_code}: {r.text[:200]}")
        except AccessCheckError:
            raise
        except Exception as e:
            # facilitator unreachable is equally non-authoritative
            raise AccessCheckError(f"facilitator unreachable: {e}") from e

        # only cache positives — negatives must re-check right after a settle
        if has:
            _access_cache[(payer, self.mode)] = (now + _CACHE_TTL, True)
            if len(_access_cache) > 10000:
                _access_cache.clear()
        return has

    def grant_cache(self, payer: str) -> None:
        """Called right after a successful settle so the next request skips the lookup."""
        _access_cache[(payer.lower(), self.mode)] = (time.time() + _CACHE_TTL, True)


def decode_payment_header(raw: str) -> tuple[dict, str]:
    """Returns (payload_dict, payer_address) or ({}, '') if undecodable."""
    try:
        payload = json.loads(base64.b64decode(raw))
        payer = (payload.get("payload", {}).get("authorization", {}) or {}).get("from", "")
        return payload, payer
    except Exception:
        return {}, ""
