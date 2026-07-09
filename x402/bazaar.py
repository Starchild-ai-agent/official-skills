"""
Coinbase CDP x402 Bazaar — discovery + safe-pay helpers (buyer side).

Discovery is scoped to CDP only:
  https://api.cdp.coinbase.com/platform/v2/x402/discovery
Do not scrape third-party x402 directories or other “Bazaar” sites.

Payment goes through our own client.py (Privy signer, EIP-3009) — CDP is
never in the payment path. Discovery API needs no key/auth.

Usage:
    python3 - <<'EOF'
    import sys; sys.path.insert(0, "/data/workspace/skills/x402")
    from bazaar import bazaar_search, probe_402, bazaar_pay
    for s in bazaar_search("weather")["results"]:
        print(s["resource"], s["price_usd"])
    EOF

Safety model (three gates before money moves):
  1. bazaar_search / bazaar_list — free CDP catalog only; filters to rails
     we can pay (Base USDC exact).
  2. probe_402(url) — free; only `standard-v2` is payable; refuse others.
  3. bazaar_pay(url) — probes first, then pays under max_usd cap.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

_BAZAAR = "https://api.cdp.coinbase.com/platform/v2/x402/discovery"
_SKILL_DIR = "/data/workspace/skills/x402"

# Networks our client/facilitator path is verified on.
PAYABLE_NETWORKS = {"eip155:8453", "base"}          # Base mainnet
PAYABLE_SCHEMES = {"exact"}                          # EIP-3009 standard
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/json", "User-Agent": "starchild-x402-buyer"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def _summarize(item: dict) -> dict:
    """Normalize a Bazaar catalog item into a buyer-facing summary."""
    payable = []
    other = []
    for acc in item.get("accepts") or []:
        entry = {"scheme": acc.get("scheme"), "network": acc.get("network"),
                 "amount_atomic": acc.get("amount") or acc.get("maxAmountRequired"),
                 "asset": acc.get("asset")}
        ok = (entry["scheme"] in PAYABLE_SCHEMES
              and entry["network"] in PAYABLE_NETWORKS
              and str(entry["asset"]).lower() == USDC_BASE.lower())
        (payable if ok else other).append(entry)
    best = payable[0] if payable else None
    price_usd = None
    if best and best["amount_atomic"]:
        try:
            price_usd = int(best["amount_atomic"]) / 1_000_000
        except (TypeError, ValueError):
            pass
    return {
        "resource": item.get("resource"),
        "description": (item.get("description") or "")[:200],
        "x402_version": item.get("x402Version"),
        "payable_by_us": bool(payable),
        "price_usd": price_usd,
        "accepts_payable": payable,
        "accepts_other": other[:3],
        "last_updated": item.get("lastUpdated"),
    }


def bazaar_search(query: str, limit: int = 10, only_payable: bool = True,
                  network: str = "eip155:8453") -> dict:
    """Hybrid search of the Coinbase CDP Bazaar only. Free, no key.

    Do not substitute third-party x402 directories — this skill's discovery
    path is CDP (`api.cdp.coinbase.com`) exclusively.
    """
    q = urllib.parse.urlencode({"query": query, "limit": min(limit * 3, 50),
                                "network": network})
    try:
        data = _get(f"{_BAZAAR}/search?{q}")
    except Exception as e:
        return {"ok": False, "error": f"bazaar search failed: {e}"}
    results = [_summarize(it) for it in data.get("resources") or []]
    if only_payable:
        results = [r for r in results if r["payable_by_us"]]
    return {"ok": True, "query": query, "search_method": data.get("searchMethod"),
            "results": results[:limit],
            "note": "price_usd is the catalog quote; probe_402() re-confirms "
                    "live price and shape before paying."}


def bazaar_list(limit: int = 20, offset: int = 0,
                only_payable: bool = True) -> dict:
    """Paginated browse of the Coinbase CDP Bazaar catalog only."""
    try:
        data = _get(f"{_BAZAAR}/resources?limit={min(limit * 3, 100)}&offset={offset}")
    except Exception as e:
        return {"ok": False, "error": f"bazaar list failed: {e}"}
    results = [_summarize(it) for it in data.get("items") or []]
    if only_payable:
        results = [r for r in results if r["payable_by_us"]]
    return {"ok": True, "total_indexed": (data.get("pagination") or {}).get("total"),
            "results": results[:limit]}


def probe_402(url: str, method: str = "GET", json_body=None, headers=None,
              timeout: int = 20) -> dict:
    """FREE probe: classify the endpoint's 402 shape before any payment.

    Prefer URLs from bazaar_search/bazaar_list (CDP). Still probe any URL
    a user supplies — only `standard-v2` is payable.

    Classifications:
      standard-v2  -> payable (accepts + exact + Base USDC)
      wrong-rail   -> x402 but not Base USDC exact
      tx-hash      -> non-standard transfer+hash flow; refuse, do not pay
      non-standard -> other unpayable 402 shapes
      no-payment   -> endpoint did not return 402
    """
    import httpx
    try:
        r = httpx.request(method, url, json=json_body, headers=headers,
                          timeout=timeout, follow_redirects=True)
    except Exception as e:
        return {"ok": False, "classification": "unreachable", "error": str(e)}

    out = {"ok": True, "status": r.status_code, "url": url}
    if r.status_code != 402:
        out["classification"] = "no-payment"
        out["note"] = "No 402 — endpoint is free, requires other auth, or method/params are wrong."
        return out

    body_text = r.text[:2000]
    try:
        body = r.json()
    except Exception:
        body = {}

    has_v2_header = bool(r.headers.get("PAYMENT-REQUIRED")
                         or r.headers.get("X-PAYMENT-REQUIRED"))
    accepts = body.get("accepts")
    if isinstance(accepts, dict):
        accepts = [accepts]

    # tx-hash pseudo-protocol detection
    low = body_text.lower()
    if not accepts and not has_v2_header and (
            "tx-hash" in low or "txhash" in low or "x-payment-txhash" in low
            or ("transfer" in low and "hash" in low)):
        out.update({"classification": "tx-hash",
                    "payable": False,
                    "reason": "non-standard transfer+tx-hash payment — refuse, do not pay"})
        return out

    if has_v2_header or accepts:
        payable = []
        for acc in accepts or []:
            if (acc.get("scheme") in PAYABLE_SCHEMES
                    and acc.get("network") in PAYABLE_NETWORKS
                    and str(acc.get("asset", "")).lower() == USDC_BASE.lower()):
                payable.append(acc)
        if has_v2_header and not accepts:
            out.update({"classification": "standard-v2", "payable": True,
                        "flavor": "v2-header"})
            return out
        if payable:
            amt = payable[0].get("amount") or payable[0].get("maxAmountRequired")
            out.update({"classification": "standard-v2", "payable": True,
                        "flavor": "json-accepts",
                        "live_price_atomic": amt,
                        "live_price_usd": (int(amt) / 1e6) if amt else None,
                        "pay_to": payable[0].get("payTo")})
            return out
        out.update({"classification": "wrong-rail", "payable": False,
                    "reason": "standard x402 but no accept on Base USDC exact",
                    "accepts_seen": [(a.get("scheme"), a.get("network"))
                                     for a in (accepts or [])][:5]})
        return out

    out.update({"classification": "non-standard", "payable": False,
                "body_head": body_text[:400]})
    return out


def bazaar_pay(url: str, method: str = "GET", json_body=None,
               max_usd: float = 0.05, timeout: int = 60) -> dict:
    """Probe-then-pay. Refuses non-standard shapes and prices above max_usd.

    Payment runs through client.paid_request (Privy signer, fail-closed).
    """
    # Probe with the SAME request shape as the payment call — POST services
    # that only 402 when given a valid JSON body would otherwise be
    # misclassified as no-payment / non-standard.
    probe = probe_402(url, method=method, json_body=json_body)
    if not probe.get("payable"):
        return {"ok": False, "paid": False, "probe": probe,
                "error": f"refused: classification={probe.get('classification')}"}
    live = probe.get("live_price_usd")
    if live is not None and live > max_usd:
        return {"ok": False, "paid": False, "probe": probe,
                "error": f"refused: live price ${live} > max_usd ${max_usd}"}

    if _SKILL_DIR not in sys.path:
        sys.path.insert(0, _SKILL_DIR)
    from client import paid_request
    max_atomic = int(max_usd * 1_000_000)
    res = paid_request(method, url, json_body=json_body,
                       max_amount_atomic=max_atomic, timeout=timeout)
    res["probe"] = {k: probe[k] for k in ("classification", "live_price_usd")
                    if k in probe}
    return res
