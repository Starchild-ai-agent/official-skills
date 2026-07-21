"""
x402 buyer discovery + safe-pay helpers.

Payment priority (product rule):
  1. Starchild marketplace / community proxy URL when the service is listed
  2. Direct URL only if marketplace has no match (no community bookkeeping)

Discovery:
  Track 1 (primary): community-publish.explore_marketplace
  Track 2 (fallback): Coinbase CDP Bazaar (api.cdp.coinbase.com)
  Never scrape third-party x402 directories.

Usage:
    python3 - <<'EOF'
    import sys; sys.path.insert(0, "/data/workspace/skills/x402")
    from bazaar import discover_services, probe_402, bazaar_pay
    for s in discover_services("weather")["results"]:
        print(s["pay_url"], s["via"], s.get("price_usd"))
    EOF

Safety gates before money moves:
  1. Prefer marketplace proxy URL when resolvable.
  2. probe_402(pay_url) — only standard-v2 is payable.
  3. paid_request(pay_url) under max_usd; community books on 200 for proxy hits.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from urllib.parse import urlparse

_BAZAAR = "https://api.cdp.coinbase.com/platform/v2/x402/discovery"
_SKILL_DIR = "/data/workspace/skills/x402"
_COMMUNITY_PUBLISH = "/data/workspace/skills/community-publish"
_COMMUNITY_HOST = "community.iamstarchild.com"

# Networks the buyer client can sign. Settlement is seller-side facilitator.
# EVM = EIP-3009 exact + native Circle USDC. SVM = exact + mainnet USDC mint.
# No testnets in prod pay path.
PAYABLE_SCHEMES = {"exact"}
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_SOLANA = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOLANA_MAINNET = "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
# Canonical network id → native Circle USDC (comparisons always .lower()).
PAYABLE_USDC = {
    "eip155:8453": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",   # Base
    "base":        "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "eip155:137":  "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359",   # Polygon
    "eip155:42161":"0xaf88d065e77c8cc2239327c5edb3a432268e5831",   # Arbitrum One
    "eip155:480":  "0x79a02482a880bce3f13e09da970dc34db4cd24d1",   # World Chain
    "eip155:143":  "0x754704bc059f8c67012fed69bc8a327a5aafb603",   # Monad
    "eip155:43114":"0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e",   # Avalanche C
    "eip155:1":    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",   # Ethereum
    "eip155:10":   "0x0b2c639c533813f4aa9d7837caf62653d097ff85",   # Optimism
    "eip155:59144":"0x176211869ca2b568f2a7d4ee941e073a821ee1ff",   # Linea
    "eip155:42220":"0xceba9300f2b948710d2653dd7b07f33a8b32118c",   # Celo
    "eip155:130":  "0x078d782b760474a361dda0af3839290b0ef57ad6",   # Unichain
    SOLANA_MAINNET: USDC_SOLANA.lower(),
    "solana": USDC_SOLANA.lower(),  # V1 alias
}
PAYABLE_NETWORKS = set(PAYABLE_USDC.keys())
# Static FALLBACK preference, used only when client.network_rank is
# unavailable (outside the agent runtime). Mirrors the client's auto
# routing: Solana → no-delegation EVM (Monad) → delegated/major EVM.
NETWORK_PREFERENCE = (
    SOLANA_MAINNET, "solana",
    "eip155:143",
    "eip155:8453", "base",
    "eip155:137", "eip155:42161", "eip155:480",
    "eip155:43114", "eip155:1", "eip155:10",
    "eip155:59144", "eip155:42220", "eip155:130",
)


def _canon_network(network) -> str:
    n = (network or "").strip()
    if n == "base":
        return "eip155:8453"
    if n == "solana":
        return SOLANA_MAINNET
    return n


def _is_payable_accept(acc: dict) -> bool:
    if not isinstance(acc, dict):
        return False
    if acc.get("scheme") not in PAYABLE_SCHEMES:
        return False
    net = _canon_network(acc.get("network"))
    if net not in PAYABLE_NETWORKS and acc.get("network") not in PAYABLE_NETWORKS:
        return False
    asset = str(acc.get("asset") or "").lower()
    want = PAYABLE_USDC.get(net) or PAYABLE_USDC.get(acc.get("network") or "")
    return bool(want) and asset == str(want).lower()


def _amount_int(a: dict) -> int:
    """Numeric amount for sorting; unparseable amounts sort LAST (never let a
    malformed quote look cheapest)."""
    try:
        return int(str(a.get("amount")))
    except (TypeError, ValueError):
        return 1 << 62


def _sort_payable(accepts: list, signer_mode: str = "auto") -> list:
    """Order accepts exactly like paid_request's routing policy (shared
    selector: client.network_rank), so the rail shown by probe_402 is the
    rail auto actually pays. Falls back to the static NETWORK_PREFERENCE
    when the client/signer is unavailable."""
    try:
        from client import network_rank, rank_signer_cached
        signer = rank_signer_cached()
        return sorted(accepts, key=lambda a: (
            network_rank(_canon_network(a.get("network")),
                         signer=signer, signer_mode=signer_mode),
            _amount_int(a)))
    except Exception:
        pass
    pref = {n: i for i, n in enumerate(NETWORK_PREFERENCE)}

    def key(a):
        n = _canon_network(a.get("network"))
        return (pref.get(n, pref.get(a.get("network"), 99)), _amount_int(a))

    return sorted(accepts, key=key)


def _decode_payment_required_header(headers) -> list:
    """Decode V2 PAYMENT-REQUIRED (or X-PAYMENT-REQUIRED) → accepts list."""
    raw = None
    try:
        raw = headers.get("PAYMENT-REQUIRED") or headers.get("payment-required")
        if not raw:
            raw = headers.get("X-PAYMENT-REQUIRED") or headers.get("x-payment-required")
    except Exception:
        raw = None
    if not raw:
        return []
    try:
        import base64
        s = raw.strip()
        pad = "=" * (-len(s) % 4)
        data = json.loads(base64.urlsafe_b64decode(s + pad))
        accepts = data.get("accepts") or []
        if isinstance(accepts, dict):
            accepts = [accepts]
        return accepts if isinstance(accepts, list) else []
    except Exception:
        return []


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
        ok = _is_payable_accept(acc)
        (payable if ok else other).append(entry)
    payable = _sort_payable(payable)
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
        "network": best.get("network") if best else None,
        "accepts_payable": payable,
        "accepts_other": other[:3],
        "last_updated": item.get("lastUpdated"),
    }


def _normalize_host(host: str) -> str:
    h = (host or "").lower()
    if h.startswith("www."):
        h = h[4:]
    return h


def _is_community_url(url: str) -> bool:
    try:
        return _normalize_host(urlparse(url).netloc) == _COMMUNITY_HOST
    except Exception:
        return False


def _search_queries_for_url(url: str) -> list[str]:
    """Build marketplace search queries from an external resource URL.

    Marketplace search does not always match full host strings (e.g.
    jokes-endpoint.vercel.app → 0 hits) but often matches a meaningful
    label token (jokes, x402joker). Prefer host, then host labels.
    """
    p = urlparse(url)
    host = _normalize_host(p.netloc)
    path = p.path or ""
    qs: list[str] = []

    def add(q: str) -> None:
        q = (q or "").strip()
        if q and len(q) >= 3 and q not in qs:
            # skip ultra-generic path tokens
            if q.lower() in {"api", "v1", "v2", "www", "com", "org", "net", "app"}:
                return
            qs.append(q)

    add(host)
    labels = [x for x in re.split(r"[.\-_/]+", host) if x]
    # longest label first (jokes-endpoint before jokes)
    for lab in sorted(set(labels), key=len, reverse=True):
        if lab not in {"vercel", "netlify", "railway", "heroku", "fly", "xyz",
                       "com", "org", "net", "app", "io", "dev", "www"}:
            add(lab)
    for seg in [s for s in path.split("/") if s]:
        add(seg)
        # strip method-ish prefixes if present
        add(seg.split(":")[0])
    return qs


def _load_explore_marketplace():
    if _COMMUNITY_PUBLISH not in sys.path:
        sys.path.insert(0, _COMMUNITY_PUBLISH)
    from exports import explore_marketplace, get_service_detail  # type: ignore
    return explore_marketplace, get_service_detail


def resolve_marketplace(url: str, limit_per_query: int = 20) -> dict:
    """Map a resource URL to the Starchild marketplace proxy pay URL when listed.

    Returns:
      ok + via=community_proxy|community_slug|direct
      pay_url: URL to pass to probe_402 / paid_request
      service_id / name / source when matched
    """
    if not url:
        return {"ok": False, "error": "empty url"}

    # Already a community URL — pay as-is (proxy or user-slug).
    if _is_community_url(url):
        via = "community_proxy" if "/proxy/" in url else "community_slug"
        return {"ok": True, "via": via, "pay_url": url, "original_url": url,
                "matched": True}

    explore_marketplace, get_service_detail = _load_explore_marketplace()
    p = urlparse(url)
    host = _normalize_host(p.netloc)
    path = p.path or ""
    best = None
    tried = []

    for q in _search_queries_for_url(url):
        try:
            r = explore_marketplace(search=q, paid_only=True, limit=limit_per_query)
        except Exception as e:
            tried.append({"q": q, "error": str(e)})
            continue
        items = r.get("items") or []
        tried.append({"q": q, "n": len(items)})
        for it in items:
            list_ep = (it.get("api_endpoint") or "").rstrip("/")
            list_p = urlparse(list_ep)
            list_host = _normalize_host(list_p.netloc)
            # Exact resource match preferred; same host is candidate.
            exact = list_ep == url.rstrip("/")
            host_ok = list_host == host and list_host != ""
            if not exact and not host_ok:
                continue
            try:
                d = get_service_detail(it["id"])
            except Exception:
                continue
            svc = (d.get("service") or {}) if d.get("ok", True) else {}
            proxy = (svc.get("api_endpoint") or "").rstrip("/")
            if not proxy:
                continue
            if "/proxy/" in proxy:
                pay_url = proxy + path
                via = "community_proxy"
            elif _is_community_url(proxy):
                pay_url = proxy  # internal slug often already includes path
                via = "community_slug"
            else:
                continue
            score = 3 if exact else 1
            # Prefer path match when list_ep path equals request path
            if list_p.path == path:
                score += 1
            cand = {
                "score": score,
                "service_id": it.get("id"),
                "name": it.get("name") or svc.get("name"),
                "source": it.get("source") or svc.get("source"),
                "list_endpoint": list_ep,
                "proxy_base": proxy,
                "pay_url": pay_url,
                "via": via,
                "query": q,
            }
            if not best or cand["score"] > best["score"]:
                best = cand
        if best and best["score"] >= 3:
            break

    if not best:
        return {"ok": True, "matched": False, "via": "direct",
                "pay_url": url, "original_url": url, "tried": tried}

    return {
        "ok": True,
        "matched": True,
        "via": best["via"],
        "pay_url": best["pay_url"],
        "original_url": url,
        "service_id": best["service_id"],
        "name": best["name"],
        "source": best["source"],
        "list_endpoint": best["list_endpoint"],
        "proxy_base": best["proxy_base"],
        "query": best["query"],
        "tried": tried,
    }


def discover_services(query: str, limit: int = 10,
                      include_cdp_fallback: bool = True) -> dict:
    """Marketplace-first discovery; optional CDP fallback for misses.

    Each result has:
      pay_url  — URL to probe/pay (community proxy preferred when listed)
      via      — community_proxy | community_slug | cdp_direct
      source   — marketplace item source (cdp/internal) or 'cdp_catalog'
    """
    results = []
    seen_pay = set()
    explore_marketplace, get_service_detail = _load_explore_marketplace()

    try:
        m = explore_marketplace(search=query, paid_only=True, limit=limit)
    except Exception as e:
        m = {"ok": False, "error": str(e), "items": []}

    for it in (m.get("items") or []):
        list_ep = it.get("api_endpoint") or ""
        sid = it.get("id")
        try:
            d = get_service_detail(sid) if sid else {"service": {}}
        except Exception:
            d = {"service": {}}
        svc = d.get("service") or {}
        proxy = (svc.get("api_endpoint") or "").rstrip("/")
        # Prefer detail proxy; fall back to list endpoint only if already community
        if proxy and _is_community_url(proxy):
            if "/proxy/" in proxy:
                # Append path from list external endpoint when present
                path = urlparse(list_ep).path if list_ep and not _is_community_url(list_ep) else ""
                # Prefer first api_endpoints path when list_ep empty
                if not path:
                    for ep in (svc.get("api_endpoints") or it.get("api_endpoints") or []):
                        if isinstance(ep, dict) and ep.get("path"):
                            raw = ep["path"].split()[-1]
                            if raw.startswith("/") and ":" not in raw:
                                path = raw
                                break
                pay_url = proxy + path
                via = "community_proxy"
            else:
                pay_url = proxy
                via = "community_slug"
        elif list_ep and _is_community_url(list_ep):
            pay_url = list_ep
            via = "community_slug"
        elif list_ep:
            # Marketplace listed but detail missing proxy — still try resolve
            res = resolve_marketplace(list_ep)
            pay_url = res.get("pay_url") or list_ep
            via = res.get("via") or "direct"
        else:
            continue
        if pay_url in seen_pay:
            continue
        seen_pay.add(pay_url)
        price = it.get("price")
        try:
            price_usd = float(price) if price is not None else None
        except (TypeError, ValueError):
            price_usd = None
        results.append({
            "name": it.get("name") or svc.get("name"),
            "service_id": sid,
            "pay_url": pay_url,
            "list_endpoint": list_ep,
            "via": via,
            "source": it.get("source") or svc.get("source") or "marketplace",
            "price_usd": price_usd,
            "marketplace": True,
        })
        if len(results) >= limit:
            break

    cdp_added = 0
    if include_cdp_fallback and len(results) < limit:
        need = limit - len(results)
        cdp = bazaar_search(query, limit=need * 2, only_payable=True)
        for s in (cdp.get("results") or []):
            resource = s.get("resource")
            if not resource:
                continue
            res = resolve_marketplace(resource)
            pay_url = res.get("pay_url") or resource
            if pay_url in seen_pay or resource in seen_pay:
                continue
            seen_pay.add(pay_url)
            via = res.get("via") if res.get("matched") else "cdp_direct"
            results.append({
                "name": None,
                "service_id": res.get("service_id"),
                "pay_url": pay_url,
                "list_endpoint": resource,
                "via": via,
                "source": "cdp_catalog" if via == "cdp_direct" else res.get("source") or "cdp",
                "price_usd": s.get("price_usd"),
                "marketplace": bool(res.get("matched")),
                "cdp_description": s.get("description"),
            })
            cdp_added += 1
            if len(results) >= limit:
                break

    return {
        "ok": True,
        "query": query,
        "results": results[:limit],
        "marketplace_count": sum(1 for r in results if r.get("marketplace")),
        "cdp_fallback_count": cdp_added,
        "note": "Prefer pay_url (community proxy when listed). "
                "bazaar_pay() re-resolves and probes before paying.",
    }


def bazaar_search(query: str, limit: int = 10, only_payable: bool = True,
                  network: str = "eip155:8453") -> dict:
    """Hybrid search of the Coinbase CDP Bazaar only (Track 2). Free, no key.

    Prefer discover_services() for buyer flows (marketplace first).
    This function is the external catalog fallback only.
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
            "note": "CDP catalog only. Prefer discover_services() so marketplace "
                    "proxy URLs are used when the service is listed."}


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

    Prefer community proxy pay_url from resolve_marketplace / discover_services.
    Only `standard-v2` is payable.

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

    # Prefer body accepts; fall back to PAYMENT-REQUIRED header payload.
    if not accepts:
        accepts = _decode_payment_required_header(r.headers)

    if has_v2_header or accepts:
        payable = _sort_payable([a for a in (accepts or []) if _is_payable_accept(a)])
        if payable:
            best = payable[0]
            amt = best.get("amount") or best.get("maxAmountRequired")
            flavor = "v2-header" if has_v2_header else "json-accepts"
            out.update({"classification": "standard-v2", "payable": True,
                        "flavor": flavor,
                        "network": best.get("network"),
                        "asset": best.get("asset"),
                        "live_price_atomic": amt,
                        "live_price_usd": (int(amt) / 1e6) if amt else None,
                        "pay_to": best.get("payTo")})
            return out
        # Header-only 402 with undecodable accepts: do not auto-pay (unknown rail).
        out.update({"classification": "wrong-rail", "payable": False,
                    "reason": "standard x402 but no accept on a known EVM USDC exact rail",
                    "accepts_seen": [(a.get("scheme"), a.get("network"), a.get("asset"))
                                     for a in (accepts or [])][:5]})
        return out

    out.update({"classification": "non-standard", "payable": False,
                "body_head": body_text[:400]})
    return out


def bazaar_pay(url: str, method: str = "GET", json_body=None,
               max_usd: float = 0.05, timeout: int = 60,
               prefer_marketplace: bool = True,
               prefer_network: str = "") -> dict:
    """Probe-then-pay. Unified community-proxy route.

    Product rule:
      - Community URLs (internal /{user}-{slug}/ or /proxy/{id}/) pay as-is.
      - External URLs are resolved to their marketplace proxy URL
        (transparent passthrough; community books on HTTP 200).
      - Unlisted external URLs are REFUSED (no community bookkeeping).
        The fix is to list the service on the marketplace, not to bypass.

    prefer_network: CAIP-2 network id (e.g. "eip155:8453") to prefer when
    the service offers multiple chains. Passed through to paid_request.

    Payment runs through client.paid_request (Privy signer, fail-closed).
    """
    resolution = {"via": "direct", "pay_url": url, "matched": False,
                  "original_url": url}
    pay_url = url
    if prefer_marketplace:
        try:
            resolution = resolve_marketplace(url)
            if resolution.get("ok") and resolution.get("pay_url"):
                pay_url = resolution["pay_url"]
        except Exception as e:
            resolution = {"via": "direct", "pay_url": url, "matched": False,
                          "original_url": url, "resolve_error": str(e)}

    # Unlisted external URLs: community proxy is the only supported pay
    # route. Escape hatch is an env gate for platform debugging only —
    # never surface it to agents or docs.
    _direct_ok = os.environ.get("X402_INTERNAL_DIRECT_PAY") == "1"
    if resolution.get("via") == "direct" and not _direct_ok:
        return {"ok": False, "paid": False, "resolution": resolution,
                "error": ("refused: URL is not listed on the Starchild "
                          "marketplace, so payment cannot go through the "
                          "community proxy (no purchase bookkeeping). "
                          "List the service on the marketplace first, "
                          "then pay its proxy URL.")}

    probe = probe_402(pay_url, method=method, json_body=json_body)
    # If proxy path failed to 402 but original might work, try original only
    # when resolution was a rewrite (not already community) — still prefer
    # reporting the proxy failure when matched (agent should fix path).
    if (not probe.get("payable")
            and resolution.get("matched")
            and pay_url != url
            and probe.get("classification") == "no-payment"):
        # One fallback: if path was wrong on proxy root, already appended path;
        # do not silently pay external when marketplace matched.
        return {"ok": False, "paid": False, "probe": probe,
                "resolution": resolution,
                "error": (f"marketplace matched but proxy not payable "
                          f"(classification={probe.get('classification')}). "
                          f"Fix path on pay_url or check upstream; "
                          f"refusing external bypass when listed.")}

    if not probe.get("payable"):
        return {"ok": False, "paid": False, "probe": probe,
                "resolution": resolution,
                "error": f"refused: classification={probe.get('classification')}"}
    live = probe.get("live_price_usd")
    if live is not None and live > max_usd:
        return {"ok": False, "paid": False, "probe": probe,
                "resolution": resolution,
                "error": f"refused: live price ${live} > max_usd ${max_usd}"}

    if _SKILL_DIR not in sys.path:
        sys.path.insert(0, _SKILL_DIR)
    from client import paid_request
    max_atomic = int(max_usd * 1_000_000)
    res = paid_request(method, pay_url, json_body=json_body,
                       max_amount_atomic=max_atomic, timeout=timeout,
                       prefer_network=prefer_network)
    res["probe"] = {k: probe[k] for k in ("classification", "live_price_usd")
                    if k in probe}
    res["resolution"] = {
        "via": resolution.get("via"),
        "matched": resolution.get("matched"),
        "pay_url": pay_url,
        "original_url": resolution.get("original_url") or url,
        "service_id": resolution.get("service_id"),
        "name": resolution.get("name"),
        "bookkeeping": (
            "community_on_200" if resolution.get("via") in (
                "community_proxy", "community_slug") else "local_ledger_only"
        ),
    }
    return res
