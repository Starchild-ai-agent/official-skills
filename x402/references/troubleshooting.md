# x402 Troubleshooting Reference — errors, security model, diagnostics

Read this BEFORE debugging any x402 error (payment failures, facilitator
errors, gateway issues, port conflicts).

## Security model (what protects whom)

| Layer | Protection | Where |
|---|---|---|
| Payment forgery | EIP-3009 signature verified off-chain + on-chain `eth_call` simulation before any gas is spent | facilitator |
| Double-credit / replay | settlement `tx_hash` UNIQUE in gateway ledger; facilitator idempotency on `(payer, nonce, asset, network)` — EIP-3009 nonces are per-payer, NOT global; confirmed replays echo success only when pay_to/amount/resource all match (`nonce_reuse_mismatch` otherwise) | ledger + facilitator |
| Gas-drain via open facilitator | `X402_PAYTO_ALLOWLIST` (recipient allowlist) and/or `X402_GATEWAY_TOKENS` (bearer auth) — set at least one on any public deployment; plus per-payer settle rate limit | facilitator |
| Gateway ↔ token-auth facilitator wiring | gateway config `facilitator_token` (env fallback `X402_FACILITATOR_TOKEN`) sends `Authorization: Bearer …` on verify/settle/supported; `monetize.py` / `make_public.py` accept `--facilitator-token`. Templates and scripts default to the PLATFORM facilitator (`https://starchild-x402-facilitator.fly.dev`); its access control (`X402_GATEWAY_TOKENS` / `X402_PAYTO_ALLOWLIST`) is opt-in env config on the deployment — currently open, so no token needed; if the platform later enables tokens, set `facilitator_token` | gateway config |
| API key theft | keys are per-payer deterministic HMAC (salt on disk, 0600); no key material in logs | gateway ledger |
| Request flooding | sliding-window rate limit per caller (X-API-Key else IP), `rate_limit_per_min` (default 120) → 429 | gateway |
| Key brute-force | ≥`ban_after_invalid_keys` (default 20) 401s/min from one IP → `ban_seconds` (default 300) temp ban | gateway |
| Settler key risk | key only pays gas — fund flow fixed by buyer signature; can never redirect funds | protocol |
| Buyer overspend | session-EOA budget IS the hard cap + `X402_MAX_ATOMIC` guard | client |
| Admin endpoints | `/x402/stats` + facilitator `/facilitator/stats` are deny-by-default: 503 until an admin token is configured, 401 on mismatch | config |
| Upstream header leak | gateway strips `X-API-Key`, `X-Admin-Token`, `PAYMENT-*` before forwarding to the upstream service | gateway |

Free endpoints (`/x402/info`, `/x402/health`, `/.well-known/x402`) are rate-limited
but unauthenticated by design (discovery must be public).

## Error contract (uniform across all modes)

| Status | `error.code` | Meaning / action |
|--------|--------------|------------------|
| 402 + `PAYMENT-REQUIRED` header | (x402 challenge) | pay & retry (clients do this automatically) |
| 402 | `insufficient_credits` | body has `topup` hint → buyer tops up |
| 401 | `invalid_key` | missing/unknown/revoked X-API-Key |
| 502 | `upstream_error` | upstream dead; units auto-refunded; keepalive will report |
| 502 | `facilitator_error` | facilitator unreachable — check outbound proxy env, retry later |

Common facilitator verify errors (2nd 402's `error` field):
- `invalid_exact_evm_insufficient_balance` — buyer wallet lacks USDC (sig was VALID)
- `invalid_signature` — wrong domain (name/version/chainId) or corrupted sig
- expired `validBefore` — client clock skew; SDK uses `maxTimeoutSeconds` (default 300s)

## Troubleshooting

- **Facilitator calls fail from container**: outbound must go through sc-proxy.
  `gateway/app.py` and `client.py` self-configure `HTTPS_PROXY`/`SSL_CERT_FILE`
  from `STARCHILD_API_PROXY_*` env. Set `X402_NO_PROXY=1` only outside Starchild.
- **Verify e2e anytime**: `python3 skills/x402/scripts/verify_setup.py`
  (fund-free checks incl. multi-accepts; add `--funded` for a real on-chain
  settlement once the wallet holds USDC on the target network).
- **Ledger inspection**: `sqlite3 /data/workspace/.x402/<name>/state/ledger.db 'select * from payments'`.
- **Gateway logs**: `/data/workspace/.x402/<name>/gateway.log`.
- **Gateway lifecycle — ONE owner per port (hard rule)**: `monetize.py`
  STARTS a background gateway (registered in `.x402/services.json`, revived
  by keepalive). Starting it AGAIN under `preview(serve)` collides: the new
  process fails `address already in use` while the old one keeps answering.
  Pick ONE owner:
  - **preview-managed** (recommended for anything published): run
    `monetize.py ... --no-start` — writes config only and prints the
    `gateway_command`; wrap upstream + gateway in a start.py and
    `preview(action='serve', command='python3 start.py', port=<gateway_port>)`.
    Preview then owns restarts across reboots.
  - **monetize-managed** (local/dev): default behavior. Manage with
    `monetize.py --stop <name>` / `--restart <name>` — restart is REQUIRED
    after editing `x402.config.json` (e.g. networks switch).
- **Preview "running" ≠ payments working**: preview health checks hit `/`,
  which the gateway proxies to the upstream — 200 there says nothing about
  billing. Verify the gateway itself: `GET /x402/info` returns 200 JSON (with
  a `networks` list) and an unpaid paid-route returns 402. If responses look
  stale, suspect an old process still holding the port (see port hygiene below).
- **Testing gateways locally — port ownership checks**: a uvicorn gateway
  whose port is already held FAILS TO BIND while the old process keeps
  answering, so a test against that port exercises the OLD process (and its
  60s access cache), not the new code. Rules:
  1. After starting a test gateway, ALWAYS check its log for
     `address already in use` BEFORE trusting any response from that port.
  2. Kill test processes by LISTENING-PORT PID, never by `ps | grep` name
     matching — backgrounded shells and renamed configs escape name matches.
     NOTE: `ss`/`netstat` are NOT installed in the container. Use:
     `python3 -c "import socket; s=socket.socket(); print('busy' if s.connect_ex(('127.0.0.1',PORT))==0 else 'free')"`
     to test a port, and find the holder by scanning cmdlines:
     `for d in /proc/[0-9]*; do grep -q CONFIG_OR_PORT_HINT $d/cmdline 2>/dev/null && echo $d; done`
     — or simply `monetize.py --stop <name>` which does this for you.
  3. When in doubt, move to brand-new port numbers instead of reusing ones a
     dead-looking process might still hold.
- Python SDK is `x402` v2.10+ (V2 headers `PAYMENT-REQUIRED`/`PAYMENT-SIGNATURE`/
  `PAYMENT-RESPONSE`). Deps are NOT auto-installed: run
  `bash skills/x402/setup.sh` once per machine (also append it to
  `/data/workspace/setup.sh` so restarts reinstall).

## Multi-chain troubleshooting (Base + Monad + Robinhood + X Layer)

- **402 `accepts` is a list, not a single object**: platform-mode 402 challenges
  return `accepts` as an **array** (one entry per network). Buyers pick one
  chain per payment. If your client expects a single object, update it to
  handle a list. The x402 skill's `client.py` ranks multi-accepts with
  `network_rank` (prefer plain-ECDSA rails like Monad over delegated Base)
  — it does **not** hard-code `accepts[0]`.
- **Legacy modes (`payperuse` / `subscription` / `metered` / `timepass`) only
  advertise one network**: even with `networks_mode: all`, the SDK middleware
  path uses `NETWORKS[0]` (Base). Multi-accepts require **platform** modes
  (`pay_per_use` / `lifetime` / `weekly` / `monthly` / `quarterly` / `yearly` /
  `prepaid`). Prefer platform modes for new marketplace listings.
- **A chain's gas is empty / settle fails on Monad or Robinhood**: the platform
  settler pays gas on every chain (ETH on Base, MON on Monad, ETH on
  Robinhood). If the gas pool for a chain is depleted, settles on that chain
  fail with a facilitator error while other chains keep working. Check the
  facilitator's `/facilitator/stats` (admin token) for per-chain gas balances.
  This is a platform-ops issue, not a seller issue — the seller never pays gas.
- **`networks_mode: custom` with an empty list fails at startup**:
  `resolve_networks` raises `ValueError("networks_mode=custom requires a
  non-empty networks list")`. Either switch to `all` or provide a non-empty
  `networks: ["eip155:8453", ...]` list.
- **Old config with `"network": "eip155:8453"` (single field)**: the gateway
  no longer reads the legacy single `network` field for platform modes — it
  uses `resolve_networks(CFG)` which looks at `networks_mode`/`networks`.
  Migrate old configs: remove `"network"` and add `"networks_mode": "all"`
  (or `"networks_mode": "custom", "networks": ["eip155:8453"]` to lock).
  `resolve_networks` deliberately does NOT guess "bare Base means all" —
  historical configs are migrated once (plans-280-04 §5.6.1.1).
- **Listing says `all` but gateway returns single-chain accepts**: the
  marketplace listing's `networks_mode=all` means "follow the platform full
  set", but the gateway config may still be `custom`. They must match: if the
  listing is `all`, the gateway config should be `networks_mode: all` (or
  absent). Restart the gateway after editing `x402.config.json`.
- **Buyer paid on Monad but the gateway tried to settle on Base**: this should
  never happen — `verify`/`settle` bind to the buyer's chosen accept (parsed
  from the `X-PAYMENT` payload's `network` field). If it does, the gateway is
  running an old version that ignores the payload network; upgrade and restart.
- **Prepaid balance not shared across chains**: the facilitator ledger key is
  `(payer, pay_to)`, not per-network. If a buyer's Monad deposit doesn't show
  up on Base, the facilitator may be running an old version with per-network
  balances — upgrade the facilitator (plans-280-04 Phase A).
- **Adding a new chain**: extend `ASSETS` + `MAINNET_NETWORKS` in
  `platform_modes.py` (and the facilitator's `KNOWN_ASSETS`). Every
  `all`-configured service picks up the new chain on its next 402 — no
  business-table update, no listing edit, no gateway restart needed (the
  network list is resolved at startup, so a restart IS needed for running
  gateways to see the new chain).
- **Robinhood USDG buyer signing**: the USDG contract uses a Diamond proxy
  with a non-standard EIP-712 domain. Both the facilitator (verify) and the
  buyer (`client.py`) now read `DOMAIN_SEPARATOR()` from chain and produce
  raw EIP-712 digests for signing/verification. This ensures the signature
  matches regardless of the on-chain domain structure. If buyer payments on
  Robinhood still fail with `invalid_signature`, check that the buyer's
  `client.py` has the chain-read path (v2.20.1+) and that the Robinhood RPC
  is reachable from the container.
