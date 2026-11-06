#!/usr/bin/env python3
"""
Angulare API diagnostic — read-only, safe against production.

WHAT THE RECON SHOWED (2026-10-09), so you can skip the guessing:

  Angulare is NOT "one username/password that mints a key each time". It is a
  multi-surface API platform with two distinct authenticated surfaces on
  https://prd.angulare.app :

  (1) INTEGRATION / OPEN API  ->  /api/open/v1/...
      Purpose-built for partners. Requires TWO things, checked in this order:
        a. header  Tenant: <environment/studio slug>   (400 tenant_required /
           400 tenant_invalid if missing or unknown)
        b. header  Authorization: Api-Key <key>        (the "Chave de API Open")
      Keys are scope-enforced: an Open key used outside /api/open/ returns
      403 {"code":"open_api_key_scope"} — that error is Angulare telling you to
      move to this surface.

  (2) PANEL API  ->  /api/v1/...
      What the logged-in studio-manager browser session uses. Challenge is
      `WWW-Authenticate: JWT realm="api"`. It also accepts:
        Authorization: Basic <user:pass>   -> 401 "Usuário ou senha inválido."
        Authorization: Token <token>       -> 401 "Token inválido."
      Being a *panel* surface, its querysets are scoped to the authenticated
      identity's tenant/user. So `200 {"count": 0}` here means "authorised, but
      this identity sees no rows" — a SCOPING problem, not a DB permission
      problem. Permission failures look like 401/403, never 200+count:0.

  Separately, api.cms.sistemas.angulare.app is a PostgREST/Supabase read
  surface (?tenant=eq.<slug>&app_code=eq.web) used for site/CMS content — not
  the place to read class attendance.

KNOWN BUG worth reporting to Angulare: `Authorization: Bearer <garbage>` on
/api/v1/ returns HTTP 500 (unhandled exception) instead of 401.

Usage:
    export ANGULARE_TENANT='<studio slug>'      # e.g. what appears in their URLs
    export ANGULARE_API_KEY='<open api key>'
    python3 angulare_diagnose.py

    # panel surface instead (username/password):
    export ANGULARE_USERNAME='...' ANGULARE_PASSWORD='...'
    python3 angulare_diagnose.py

    # only the unauthenticated baseline (no secrets needed):
    python3 angulare_diagnose.py
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("ANGULARE_BASE_URL", "https://prd.angulare.app").rstrip("/")

# A path from each surface. Replace the token segment with a real one when you
# have it; the probe is meaningful even with a placeholder.
OPEN_PATH = "/api/open/v1/events/events/{token}/bookings/"
PANEL_PATH = "/api/v1/events/events/{token}/bookings/"


def call(path, headers=None, timeout=20):
    request = urllib.request.Request(BASE + path,
                                     headers={"Accept": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode("utf-8", "replace")
    except Exception as exc:
        return None, {}, f"{type(exc).__name__}: {exc}"


def show(label, path, headers=None):
    status, resp_headers, body = call(path, headers)
    www = resp_headers.get("WWW-Authenticate") or resp_headers.get("Www-Authenticate")
    flat = " ".join(body.split())[:300]
    print(f"\n  {label}")
    print(f"    GET {BASE}{path}")
    print(f"    -> {status}" + (f"   WWW-Authenticate: {www}" if www else ""))
    try:
        payload = json.loads(body)
        if isinstance(payload, dict) and "results" in payload:
            rows = payload.get("results") or []
            print(f"    count={payload.get('count')} next={payload.get('next')!r} "
                  f"results_len={len(rows)}")
            if rows and isinstance(rows[0], dict):
                print(f"    row_fields={sorted(rows[0].keys())}")
        else:
            print(f"    {json.dumps(payload, ensure_ascii=False)[:300]}")
    except Exception:
        print(f"    {flat}")
    return status, body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", default=os.environ.get("ANGULARE_TENANT", ""))
    parser.add_argument("--key", default=os.environ.get("ANGULARE_API_KEY", ""))
    parser.add_argument("--user", default=os.environ.get("ANGULARE_USERNAME", ""))
    parser.add_argument("--password", default=os.environ.get("ANGULARE_PASSWORD", ""))
    parser.add_argument("--token", default=os.environ.get("ANGULARE_SESSION_TOKEN", "placeholder"))
    args = parser.parse_args()

    print("=" * 76)
    print("STEP 1 — which surfaces exist (no credentials; this is the fingerprint)")
    print("=" * 76)
    show("panel surface", PANEL_PATH.format(token=args.token))
    show("open/integration surface", OPEN_PATH.format(token=args.token))

    if args.tenant or args.key:
        print("\n" + "=" * 76)
        print("STEP 2 — open API gate order (Tenant, then Api-Key)")
        print("=" * 76)
        show("no headers", OPEN_PATH.format(token=args.token))
        if args.tenant:
            show(f"Tenant: {args.tenant} only", OPEN_PATH.format(token=args.token),
                 {"Tenant": args.tenant})
        if args.tenant and args.key:
            show("Tenant + Api-Key", OPEN_PATH.format(token=args.token),
                 {"Tenant": args.tenant, "Authorization": f"Api-Key {args.key}"})
        if args.key and not args.tenant:
            print("  ! set --tenant too: the Tenant header is validated before the key")

    if args.user and args.password:
        print("\n" + "=" * 76)
        print("STEP 3 — panel surface with username/password")
        print("=" * 76)
        import base64
        blob = base64.b64encode(f"{args.user}:{args.password}".encode()).decode()
        show("Basic auth", PANEL_PATH.format(token=args.token),
             {"Authorization": f"Basic {blob}"})

    print("\n" + "=" * 76)
    print("HOW TO READ THIS")
    print("=" * 76)
    print("""  200 + count: 0        -> authenticated and routed, but this identity/tenant
                           sees no rows. That is SCOPING, not permissions.
                           Fix the Tenant header / the key's tenant, not the query.
  200 + count > 0       -> working. Read `row_fields` to see whether attendance
                           (attended / no_show / present) is in there.
  400 tenant_required   -> add the `Tenant` header.
  400 tenant_invalid    -> that slug is not an environment; get the real slug.
  403 open_api_key_scope-> you are using an Open key on the wrong surface; use
                           /api/open/v1/...
  401 JWT "não foram fornecidas" -> panel surface needs a session identity.
  500 on Bearer         -> Angulare-side bug (unhandled exception); report it.
""")


if __name__ == "__main__":
    main()