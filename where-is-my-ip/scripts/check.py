#!/usr/bin/env python3
"""where-is-my-ip — exit-IP geolocator with byo-proxy integration.

Demonstrates both byo-proxy patterns:
    --via iproyal:jp        Pattern A (explicit get_proxy_url)
    --use-binding           Pattern B (get_proxy_for_skill)
    --compare iproyal:jp    side-by-side direct vs proxied
    (no flag)               direct, no proxy

When --use-binding is passed and the user hasn't onboarded yet, byo-proxy's
ProxyNotConfiguredError carries a complete onboarding guide — we print it
verbatim and exit non-zero.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

# ── byo-proxy integration (lazy: only imported if a proxy mode is requested) ──

def _import_byo_proxy():
    """Import byo-proxy on demand. Isolated so the direct-mode path has zero
    dependency on byo-proxy being installed."""
    sys.path.insert(0, "/data/workspace/skills/byo-proxy")
    try:
        from exports import (  # type: ignore
            get_proxy_url, get_proxy_for_skill, ProxyNotConfiguredError,
        )
    except ImportError as e:
        print(
            f"ERROR: byo-proxy is not installed at /data/workspace/skills/byo-proxy ({e}).\n"
            "where-is-my-ip can still run in direct mode — drop the --via / --use-binding flag.",
            file=sys.stderr,
        )
        sys.exit(2)
    return get_proxy_url, get_proxy_for_skill, ProxyNotConfiguredError


# ── core lookup ──────────────────────────────────────────────────────────────

LOOKUP_URL = "https://ifconfig.co/json"


def lookup(proxy: str | None = None, timeout: int = 15) -> dict:
    """Hit ifconfig.co/json. Returns {ok, exit_ip, country_iso, country, city,
    region, asn, asn_org, latency_ms, error?}."""
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(
        LOOKUP_URL, headers={"User-Agent": "where-is-my-ip/0.1"}
    )
    started = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        return {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
    return {
        "ok": True,
        "exit_ip": data.get("ip", ""),
        "country_iso": (data.get("country_iso") or "").upper(),
        "country": data.get("country", ""),
        "city": data.get("city", ""),
        "region": data.get("region_name", ""),
        "asn": data.get("asn", ""),
        "asn_org": data.get("asn_org", ""),
        "latency_ms": int((time.monotonic() - started) * 1000),
    }


# ── output formatting ───────────────────────────────────────────────────────

def _print_single(result: dict, via_label: str | None = None,
                  expected_country: str | None = None) -> None:
    if not result["ok"]:
        print(f"FAIL ({result['latency_ms']}ms): {result.get('error')}", file=sys.stderr)
        return
    print(f"📍 exit  {result['exit_ip']}")
    print(f"   country  {result['country_iso']} ({result['country']})")
    city = result["city"]
    region = result["region"]
    locale = ", ".join(p for p in (city, region) if p) or "(unknown)"
    print(f"   city     {locale}")
    asn = result["asn"]
    asn_org = result["asn_org"]
    print(f"   asn      {asn}  {asn_org}".rstrip())
    print(f"   latency  {result['latency_ms']} ms")
    if via_label:
        print(f"   via      {via_label}")
    if expected_country and result["country_iso"].lower() != expected_country.lower():
        print(
            f"   ⚠️  geo mismatch: requested {expected_country!r}, got {result['country_iso'].lower()!r}",
            file=sys.stderr,
        )


def _print_compare(direct: dict, proxied: dict, label: str,
                   expected_country: str) -> None:
    headers = ("", "exit_ip", "country", "city", "asn")
    rows = [
        ("direct", direct),
        (label, proxied),
    ]
    widths = [max(len(headers[0]), max(len(r[0]) for r in rows)) + 2,
              17, 10, 14, 0]
    fmt = "{:<" + str(widths[0]) + "}{:<" + str(widths[1]) + "}{:<" + str(widths[2]) + "}{:<" + str(widths[3]) + "}{}"
    print(fmt.format(*headers))
    for name, r in rows:
        if not r["ok"]:
            print(f"{name:<{widths[0]}}FAIL — {r.get('error')}")
            continue
        match_note = ""
        if name != "direct":
            ok = r["country_iso"].lower() == expected_country.lower()
            match_note = "  ✅ matches request" if ok else f"  ⚠️  expected {expected_country.upper()}"
        asn_combined = f"{r['asn']} {r['asn_org']}".strip()
        print(fmt.format(
            name,
            r["exit_ip"],
            r["country_iso"],
            (r["city"] or "?")[:14],
            asn_combined + match_note,
        ))


# ── main ─────────────────────────────────────────────────────────────────────

SKILL_NAME = "where-is-my-ip"


def _parse_via(spec: str) -> tuple[str, str]:
    if ":" not in spec:
        raise SystemExit(
            f"--via expects 'provider:country', got {spec!r} "
            f"(e.g. iproyal:jp)"
        )
    provider, country = spec.split(":", 1)
    return provider.strip(), country.strip()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Look up the current outbound exit IP and its geolocation.",
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--via", metavar="PROVIDER:COUNTRY",
                      help="Route through byo-proxy explicitly, e.g. iproyal:jp")
    mode.add_argument("--use-binding", action="store_true",
                      help=f"Use whatever proxy {SKILL_NAME!r} is bound to in byo-proxy")
    mode.add_argument("--compare", metavar="PROVIDER:COUNTRY",
                      help="Show direct exit and proxied exit side-by-side")
    ap.add_argument("--sticky", type=int, default=None,
                    help="Sticky-session lifetime in minutes (Pattern A only)")
    ap.add_argument("--json", action="store_true",
                    help="Emit raw JSON instead of formatted output")
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args()

    # Resolve which proxy URL to use.
    proxy: str | None = None
    via_label: str | None = None
    expected_country: str | None = None

    if args.via:
        provider, country = _parse_via(args.via)
        get_proxy_url, _, ProxyNotConfiguredError = _import_byo_proxy()
        try:
            proxy = get_proxy_url(provider=provider, country=country,
                                  sticky_minutes=args.sticky)
        except ProxyNotConfiguredError as e:
            print(str(e), file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        sticky_note = f" (sticky {args.sticky}m)" if args.sticky else ""
        via_label = f"{provider}/{country}{sticky_note}"
        expected_country = country

    elif args.use_binding:
        _, get_proxy_for_skill, ProxyNotConfiguredError = _import_byo_proxy()
        try:
            proxy = get_proxy_for_skill(SKILL_NAME)
        except ProxyNotConfiguredError as e:
            # The exception message IS the onboarding guide — print verbatim.
            print(str(e), file=sys.stderr)
            return 2
        via_label = f"binding for {SKILL_NAME!r}"

    elif args.compare:
        provider, country = _parse_via(args.compare)
        get_proxy_url, _, ProxyNotConfiguredError = _import_byo_proxy()
        try:
            proxy = get_proxy_url(provider=provider, country=country,
                                  sticky_minutes=args.sticky)
        except ProxyNotConfiguredError as e:
            print(str(e), file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2

        direct = lookup(proxy=None, timeout=args.timeout)
        proxied = lookup(proxy=proxy, timeout=args.timeout)
        if args.json:
            print(json.dumps(
                {"direct": direct, f"{provider}/{country}": proxied}, indent=2))
        else:
            _print_compare(direct, proxied, f"{provider}/{country}",
                           expected_country=country)
        return 0 if (direct["ok"] and proxied["ok"]) else 1

    # Single-lookup path (covers direct, --via, --use-binding).
    result = lookup(proxy=proxy, timeout=args.timeout)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    _print_single(result, via_label=via_label, expected_country=expected_country)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
