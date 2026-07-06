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

Contract points (must match the platform audit checklist, doc §12):
  * 402 JSON body: {x402Version:2, error, accepts:{...,"pricingModel":<mode>}}
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
import time
from datetime import datetime, timezone

import httpx

PLATFORM_MODES = ("pay_per_use", "lifetime", "monthly", "prepaid")

# network -> (usdc_asset, extra name/version) — mirror of facilitator KNOWN_ASSETS
ASSETS = {
    "eip155:8453": ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", {"name": "USD Coin", "version": "2"}),
    "eip155:84532": ("0x036CbD53842c5426634e7929541eC2318f3dCF7e", {"name": "USDC", "version": "2"}),
}

_access_cache: dict = {}  # payer -> (expires_ts, has_access)
_CACHE_TTL = 60


class PlatformBilling:
    def __init__(self, cfg: dict):
        self.mode = cfg["mode"]
        self.pay_to = cfg["pay_to"]
        self.network = cfg.get("network", "eip155:8453")
        if self.network not in ASSETS:
            raise ValueError(f"unsupported network {self.network}")
        self.asset, self.extra = ASSETS[self.network]
        price = str(cfg.get("price_usd", "0.01")).lstrip("$")
        self.amount_atomic = str(int(round(float(price) * 1_000_000)))
        self.facilitator = (cfg.get("facilitator") or "").rstrip("/")
        if not self.facilitator:
            raise ValueError("platform modes require an explicit `facilitator` URL")
        self.fac_token = cfg.get("facilitator_token") or ""
        # settlements/access-status are admin-gated on the platform facilitator
        self.fac_admin_token = cfg.get("facilitator_admin_token") or ""
        # prepaid: suggested deposit size. Default 100 calls worth, floored at
        # the facilitator's default minimum deposit ($0.10 = 100000 atomic).
        dep = cfg.get("deposit_usd")
        if dep is not None:
            self.deposit_atomic = int(round(float(str(dep).lstrip("$")) * 1_000_000))
        else:
            self.deposit_atomic = max(int(self.amount_atomic) * 100, 100_000)
        self._verify_cache: dict = {}  # signature -> (valid_until_ts, payer)

    # -- requirements / 402 -------------------------------------------------
    def requirements(self, resource: str = "") -> dict:
        req = {
            "scheme": "exact",
            "network": self.network,
            "amount": self.amount_atomic,
            "asset": self.asset,
            "payTo": self.pay_to,
            "maxTimeoutSeconds": 300,
            "extra": dict(self.extra),
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

    def challenge_body(self, resource: str = "", error: str = "X-PAYMENT header is required",
                       deposit: bool = False) -> dict:
        """402 body. deposit=True (prepaid only) swaps accepts.amount to the
        deposit size — the client signs accepts.amount, so this is how the
        gateway asks for a top-up instead of an auth signature."""
        acc = self.requirements(resource)
        if deposit and self.mode == "prepaid":
            acc["amount"] = str(self.deposit_atomic)
        return {"x402Version": 2, "error": error, "accepts": acc}

    # -- facilitator calls ---------------------------------------------------
    def _headers(self, admin: bool = False) -> dict:
        h = {"Content-Type": "application/json"}
        if self.fac_token:
            h["Authorization"] = f"Bearer {self.fac_token}"
        if admin and self.fac_admin_token:
            h["X-Admin-Token"] = self.fac_admin_token
        return h

    async def verify(self, payload: dict, resource: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(f"{self.facilitator}/verify", headers=self._headers(),
                             json={"x402Version": 2, "paymentPayload": payload,
                                   "paymentRequirements": self.requirements(resource)})
            return r.json()

    async def settle(self, payload: dict, resource: str) -> dict:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{self.facilitator}/settle", headers=self._headers(),
                             json={"x402Version": 2, "paymentPayload": payload,
                                   "paymentRequirements": self.requirements(resource)})
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
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{self.facilitator}/facilitator/balance",
                            params={"payer": payer, "pay_to": self.pay_to},
                            headers=self._headers())
            r.raise_for_status()
            return int(r.json().get("balance_atomic", 0))

    async def deposit(self, payload: dict, resource: str) -> dict:
        """Forward the signed payload to /facilitator/deposit-settle (on-chain
        settle that credits the payer/pay_to prepaid balance)."""
        auth = payload.get("payload", {}).get("authorization", {}) or {}
        req = self.requirements(resource)
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
            r = await c.post(f"{self.facilitator}/facilitator/debit",
                             headers=self._headers(),
                             json={"payer": payer, "pay_to": self.pay_to,
                                   "amount_atomic": amount,
                                   "request_id": request_id, "route": route})
            return r.json()

    async def refund(self, payer: str, request_id: str, units: int = 1,
                     route: str = "") -> None:
        """Credit back a debit after an upstream failure (negative debit with a
        derived request_id, so it is idempotent and never collides)."""
        amount = -int(self.amount_atomic) * max(int(units), 1)
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                await c.post(f"{self.facilitator}/facilitator/debit",
                             headers=self._headers(),
                             json={"payer": payer, "pay_to": self.pay_to,
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
        hit = _access_cache.get(payer)
        if hit and hit[0] > now:
            return hit[1]

        has = False
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                # Single endpoint for both models. min_amount = the service
                # price, so historic smaller payments to the same pay_to
                # (e.g. old pay_per_use calls) can never unlock this service.
                # For monthly the facilitator computes natural-month expiry
                # server-side and returns expires_at.
                r = await c.get(f"{self.facilitator}/facilitator/access-status",
                                params={"payer": payer, "pay_to": self.pay_to,
                                        "min_amount": self.amount_atomic,
                                        "pricing_model": self.mode},
                                headers=self._headers(admin=True))
                if r.status_code == 200:
                    has = bool(r.json().get("has_access"))
                elif self.mode == "monthly":
                    # fallback for facilitators without pricing_model support:
                    # pull this payer/pay_to pair's settlements and compute expiry
                    since = now - 40 * 86400  # covers any natural month
                    r = await c.get(f"{self.facilitator}/facilitator/settlements",
                                    params={"since": since, "limit": 1000,
                                            "payer": payer, "pay_to": self.pay_to},
                                    headers=self._headers(admin=True))
                    if r.status_code == 200:
                        for s in r.json().get("settlements", []):
                            if (int(s.get("amount_atomic") or 0) >= int(self.amount_atomic)
                                    and s.get("status") == "confirmed"
                                    and self._monthly_valid(float(s.get("confirmed_at") or 0))):
                                has = True
                                break
        except Exception as e:  # facilitator unreachable -> treat as unpaid (will 402)
            print(f"[x402-platform] already_paid check failed: {e}", flush=True)

        # only cache positives — negatives must re-check right after a settle
        if has:
            _access_cache[payer] = (now + _CACHE_TTL, True)
            if len(_access_cache) > 10000:
                _access_cache.clear()
        return has

    def grant_cache(self, payer: str) -> None:
        """Called right after a successful settle so the next request skips the lookup."""
        _access_cache[payer.lower()] = (time.time() + _CACHE_TTL, True)


def decode_payment_header(raw: str) -> tuple[dict, str]:
    """Returns (payload_dict, payer_address) or ({}, '') if undecodable."""
    try:
        payload = json.loads(base64.b64decode(raw))
        payer = (payload.get("payload", {}).get("authorization", {}) or {}).get("from", "")
        return payload, payer
    except Exception:
        return {}, ""
