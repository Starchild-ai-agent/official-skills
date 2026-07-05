"""Platform pricing modes for the x402 gateway — Starchild community-gateway contract.

Implements the three platform-standard pricing models from
x402-facilitator/docs/pricing-models.md:

  pay_per_use  verify -> settle on EVERY request (no history check)
  lifetime     verify -> settle once; later requests check facilitator
               settlements (payer paid pay_to before = permanent access)
  monthly      like lifetime but access expires one natural month after
               payment (same day next month, clamped to month end)

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

PLATFORM_MODES = ("pay_per_use", "lifetime", "monthly")

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
        return req

    def challenge_body(self, resource: str = "", error: str = "X-PAYMENT header is required") -> dict:
        return {"x402Version": 2, "error": error, "accepts": self.requirements(resource)}

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
