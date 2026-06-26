"""End-to-end status check after setup. Tells the user EXACTLY which stage
is still pending: DNS propagation, SSL cert provisioning, or service-side.

Run anytime after setup.py to see current state without bothering the user.
"""
from __future__ import annotations

import json
import socket
import ssl
import subprocess
import sys
import urllib.request

from cf_api import load_state


def doh_lookup(name: str) -> tuple[int, list[str], str]:
    """Returns (status, ip_list, authority_summary)."""
    req = urllib.request.Request(
        f"https://dns.google/resolve?name={name}&type=A",
        headers={"accept": "application/dns-json"},
    )
    d = json.loads(urllib.request.urlopen(req, timeout=10).read())
    ips = [a["data"] for a in d.get("Answer", []) if a.get("type") == 1]
    auth = ", ".join(a.get("data", "")[:60] for a in d.get("Authority", []))
    return d.get("Status", -1), ips, auth


def tls_check(host: str) -> tuple[bool, str]:
    """True if TLS handshake completes and a cert is presented."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                cn = dict(x[0] for x in cert.get("subject", []))
                return True, f"cert CN={cn.get('commonName', '?')}, issuer={cert.get('issuer', [[('?',)]])[0][0][1]}"
    except ssl.SSLError as e:
        return False, f"SSL error: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def http_check(host: str) -> tuple[int, int, str]:
    """Returns (status_code, body_size, server_header)."""
    req = urllib.request.Request(
        f"https://{host}/",
        headers={
            "user-agent": "Mozilla/5.0 (compatible; StarchildStatusCheck/1.0)",
            "accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read()
            return r.status, len(body), (r.headers.get("server") or "")
    except urllib.error.HTTPError as e:
        body = e.read() or b""
        return e.code, len(body), (e.headers.get("server") or "")
    except Exception:
        return 0, 0, ""


def main() -> int:
    state = load_state()
    host = state.get("hostname")
    if not host:
        print("❌ No hostname in state. Run setup.py first.")
        return 2

    print(f"🔍 Diagnosing {host}\n")

    # Stage 1: DNS
    status, ips, auth = doh_lookup(host)
    if status == 0 and ips:
        print(f"✅ DNS:   {host} → {', '.join(ips)}")
    elif status == 3:
        if "trs-dns" in auth or "tucows" in auth or "verisign" in auth:
            print(f"⏳ DNS:   TLD registry hasn't propagated the new domain yet.")
            print(f"         Authority = {auth}")
            print(f"         → Wait 30 min – 24 h for new domains. Nothing to fix.")
        else:
            print(f"⏳ DNS:   NXDOMAIN. Authority = {auth or '(none)'}")
        return 0
    else:
        print(f"⚠ DNS:   Status={status}, IPs={ips}, Authority={auth}")
        return 0

    # Stage 2: TLS
    ok, info = tls_check(host)
    if ok:
        print(f"✅ TLS:   {info}")
    else:
        print(f"⏳ TLS:   {info}")
        print(f"         → Cloudflare Universal SSL not issued yet for this hostname.")
        print(f"         → Check: dash.cloudflare.com → {state.get('zone_name','<domain>')} → SSL/TLS → Edge Certificates")
        print(f"         → Typical wait for new domains: 15 min – 24 h. Nothing else to fix.")
        return 0

    # Stage 3: HTTP
    code, size, server = http_check(host)
    if code == 200:
        print(f"✅ HTTP:  200 OK ({size} bytes)")
        print(f"\n🎉 https://{host}/ is LIVE.")
    elif code in (301, 302):
        print(f"✅ HTTP:  {code} redirect")
    elif code in (403, 429):
        if "cloudflare" in (server or "").lower():
            print(f"✅ HTTP:  {code} from Cloudflare edge (bot/rate-limit challenge in checker)")
            print(f"         → Real browsers can still access the site normally.")
            print(f"         → If your browser also gets 403, disable WAF/Bot Fight for this hostname.")
        else:
            print(f"⚠ HTTP:  {code}")
    elif code in (502, 521, 522, 523, 530):
        print(f"❌ HTTP:  {code} — Tunnel up but local service unreachable.")
        print(f"         → Make sure your service is running on port {state.get('port')}")
    else:
        print(f"⚠ HTTP:  {code}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
