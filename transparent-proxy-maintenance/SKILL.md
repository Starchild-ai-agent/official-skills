---
name: transparent-proxy-maintenance
version: 1.0.1
description: "Maintain and evolve transparent-proxy paid API plugins. Use when changing pricing/rate limits, switching billing model, adding/removing paid APIs, then validating and deploying to Fly."
metadata:
  starchild:
    emoji: "🧱"
    skillKey: transparent-proxy-maintenance
    requires:
      bins: [python, fly]
      env: [SC_PROXY_FLY_TOKEN]
user-invocable: true
disable-model-invocation: false
---

# transparent-proxy-maintenance

Use this skill for all paid-API lifecycle work in `transparent-proxy`.

## Scope

Covers 3 common tasks:
1. 修改价格和限频
2. 修改付费 API 的计价方式
3. 添加和移除付费 API

Also includes testing + Fly deployment workflow.

## Architecture you must respect

- Core proxy: `transparent-proxy/proxy.py`
- Plugin base: `transparent-proxy/apis/base.py`
- One paid API per plugin file: `transparent-proxy/apis/*.py`
- Static config snapshots (still kept for sync/ops):
  - `transparent-proxy/config/pricing.json`
  - `transparent-proxy/config/rate_limits.json`
  - `transparent-proxy/config/proxied_apis.json`
  - `transparent-proxy/config/keys.json`

Rule: each paid API should stay self-contained in its plugin (pricing, limit, key injection), and config snapshots must remain consistent.

## Standard workflow (always)

1. Read target plugin + related config files first.
2. Apply minimal edits (`edit_file` preferred).
3. Run tests (quick first, then full when needed).
4. Deploy to Fly (`fly deploy`, no hot reload assumptions).
5. Post-deploy smoke tests through `sc-proxy.internal:8080`.
6. Verify billing headers + DB charge behavior for changed APIs.

---

## A) 修改价格和限频

### Where to change

- Plugin file, e.g. `apis/twitterapi.py`
  - price: `pricing = Pricing.per_request(...)`
  - rate limit: `rate_limit = RateLimit(requests_per_minute=...)`
- Keep snapshot config aligned:
  - `config/pricing.json`
  - `config/rate_limits.json`

### Example patterns

- Per-request pricing:
  - `pricing = Pricing.per_request(0.001)`
- RPM:
  - `rate_limit = RateLimit(requests_per_minute=240)`

### Validate

- Functional: API still returns 200 via proxy.
- Billing headers exist on paid domains:
  - `X-Credits-Used`
  - `X-Credits-Balance`
- Rate limit works at new threshold with burst test (expect some 429 only beyond threshold/burst).

### INET/IPv6 null-safety (subscription-service specific)

When writing to `subscriptions.machine_ipv6` (type `INET`), never pass string placeholders like `"None"` or `"null"`.

- Normalize empty/placeholder values to Python `None` before SQL bind.
- Use parameterized SQL only; let psycopg2 map `None` to SQL `NULL`.
- Expected behavior for pre-machine subscription: insert succeeds with `machine_ipv6 = NULL`; downstream refresh jobs should skip these rows until IPv6 is backfilled.

### Stripe upgrade payment-gating (subscription-service specific)

For plan upgrades, do **not** switch local `subscriptions.plan` on `change-plan` response alone.

- Treat `change-plan` as initiating payment only; do not persist intermediate upgrade state.
- Only apply upgraded plan + higher daily credit after `invoice.paid` webhook.
- If `payment_intent_status` is `requires_action`, return a frontend redirect/confirmation hint and keep current plan unchanged.
- If payment is incomplete/failed (`requires_payment_method`, `requires_confirmation`, `canceled`), keep current plan unchanged.

This prevents unpaid/3DS-incomplete upgrades from being activated locally while keeping state handling minimal.

---

## B) 修改付费 API 的计价方式

### Available models (`apis/base.py`)

- `Pricing.per_request(x)`
- `Pricing.per_token(input_per_1k=..., output_per_1k=...)`
- `Pricing.openrouter_usage(multiplier=...)`

### Decision guide

- Fixed-cost APIs → `per_request`
- Token-based LLM APIs → `per_token`
- OpenRouter-like responses with usage cost → `openrouter_usage`

### Additional hooks when needed

- `extract_usage(flow)` for custom token/cost extraction
- `rewrite_response(flow, credits_used, sse_streamed)` for usage.cost rewrite
- `transform_sse_chunk(data)` for streaming chunk rewrite
- `charge_api_type(usage)` for per-model charge type (e.g. `openrouter/{model}`)

Important implementation detail: `proxy.py` only calls `extract_usage(...)` when `plugin.is_llm = True`. If you implement dynamic billing via `extract_usage` (even for non-LLM APIs like async video), set `is_llm = True` in that plugin or the extracted cost will be ignored and charges become 0.

### Critical checks for billing-model changes

- Non-stream response: `body.usage.cost` should match `X-Credits-Used` when rewrite is expected.
- SSE response: final usage chunk cost rewrite must be correct.
- Error responses (4xx/5xx): should not create positive charges.
- Twitterapi.io payload-shape guardrails for verification:
  - `/twitter/tweet/retweeters` returns `users[]` (not `retweeters[]`)
  - `/twitter/tweet/replies` commonly returns `tweets[]` (not `replies[]`)
  - `/twitter/user/search` returns `users[]`
  Confirm actual key shape before computing expected billed items, otherwise you may misdiagnose pricing bugs.

---

## E) fal.ai storage support (image/video reference uploads)

When user asks to support fal image-to-video/video-to-video reference files via fal storage:

1. Update `apis/falai.py` plugin to include both domains:
   - `queue.fal.run` (generation)
   - `api.fal.ai` (file storage API)

2. Add storage endpoint handling in plugin:
   - `POST /v1/serverless/files/file/local/{target_path}`
   - `POST /v1/serverless/files/file/url/{file}`
   - optional read/list endpoints as zero-cost

3. Enforce upload guards in plugin preflight (before upstream call):
   - Require `multipart/form-data` + `Content-Length` for local upload
   - Reject unsupported extensions
   - Enforce size limits (example policy):
     - image max 10MB
     - video max 100MB

4. Storage pricing policy (if requested):
   - image local upload = 0.01
   - video local upload = 0.1
   - queue poll/result/list/get can remain 0

5. Keep config snapshots/admin config aligned:
   - `config/proxied_apis.json` add `api.fal.ai`
   - `config/domains.json` add `api.fal.ai`
   - mirror to `admin-app/config/*` files

6. Validation checklist:
   - unit tests for plugin endpoint identification, size limits, pricing
   - `python -m py_compile` on modified files
   - proxy smoke: storage upload returns billing headers (`X-Credits-Used`) with expected fee

7. Abuse-prevention policy for fal integration:
   - Endpoint allowlist only (deny-by-default):
     - generation: only approved video endpoints needed for text-to-video / image-to-video / video-to-video / edit-video
     - storage: only `file/local`, `file/url`, optional `file/get` and `list`
   - Billing model scope:
     - charge generation only for `per_video_second` and `per_video`
     - unknown/unsupported generation endpoints should be rejected (403), not soft-charged with fallback
   - Storage upload anti-abuse:
     - both image and video upload operations are billable
     - enforce content-type + extension + size limits before upstream call

## C) 添加和移除付费 API

### Add a new paid API

1. Create `apis/<name>.py` plugin class inheriting `ApiPlugin`.
2. Define at minimum:
   - `name`
   - `domains`
   - `env_var`
   - `pricing`
   - `inject_key(...)`
3. Add/align config snapshots:
   - `config/keys.json` (fake_key + env_var)
   - `config/pricing.json`
   - `config/rate_limits.json`
   - `config/proxied_apis.json` (domains + type)
4. Verify plugin autoload logs show it loaded.
5. Smoke test against a real endpoint on that domain via proxy.

### Remove a paid API

1. Remove plugin file `apis/<name>.py`.
2. Remove entries from the 4 config snapshot files above.
3. Deploy and verify:
   - Plugin no longer appears in loaded list.
   - Requests to removed domain become passthrough or unhandled as designed.
   - No new charges for removed api_type.

---

## Testing playbook

## 1) Quick local/static checks

- Read edited files to confirm exact values.
- Run tests (start with fast suite).
- If full suite is required, run full pytest before deploy.

## 2) Post-deploy smoke checks (mandatory)

Use proxy endpoint:
- `http://sc-proxy.internal:8080`

For each changed API:
- Send real request with fake key header from config.
- Expect HTTP success and billing headers on paid API domains.

Passthrough control:
- Test `https://example.com` via proxy.
- Expect no billing headers.

## 3) Rate-limit verification (when RPM changed)

- Sequential test (sanity): medium volume should pass.
- Concurrent burst test: high volume should hit 429 near threshold/burst window.
- Use dedicated `SC-CALLER-ID` for traceability.

## 4) Billing verification (when pricing/model changed)

- Check `X-Credits-Used` precision and value shape.
- For LLM APIs, verify rewritten cost behavior (normal + SSE).
- Verify charges in DB for the specific caller id if needed.

---

## Deployment (Fly)

- Test app: `test-sc-proxy` with `TEST_SC_PROXY_FLY_TOKEN`
- Prod app: `sc-proxy` with `SC_PROXY_FLY_TOKEN`
- Team token file convention can be either `FLY.env` (workspace root) or repo-local `.env`; source whichever exists before deploy.

Deploy command pattern:

```bash
cd transparent-proxy
set -a; source /data/workspace/FLY.env; set +a   # or source .env
export FLY_API_TOKEN="$TEST_SC_PROXY_FLY_TOKEN"   # prod use SC_PROXY_FLY_TOKEN
fly deploy -c fly.test.toml --remote-only         # prod: fly.toml
```

Post-deploy checks:
- `fly status -a <app>` healthy.
- plugin load logs are clean.
- smoke tests immediately.

Non-interactive SSH smoke tip:
- Prefer `fly ssh console --machine <id> -a <app> -C "..."`
- Avoid `-s/--select` in scripts (it triggers interactive prompt).

---

## D) DB connection OOM / connection-growth triage (post-deploy)

When DB memory spikes after a deploy, check connection growth before changing billing logic.

### 1) Verify where connections come from (not only sc-proxy)

Use `pg_stat_activity` grouped by `application_name`, `client_addr`, and `state`.

Interpretation:
- If one process exceeds its own pool max, suspect leak/unchecked `getconn()` path.
- If each process stays near configured pool max but total is high, it's aggregate pool over-allocation across services/machines.

### 2) Compare against configured pool ceilings

Check pool max in each service, then sum by running machine count:
- sc-proxy (`DB_POOL_MAX`)
- starchild-credit-api (billing/user pools)
- subscription-service (primary/user pools)
- recharge-watcher (billing/user pools)
- admin-app (pool)

A common failure mode is each service being “correct” individually while aggregate connections exceed DB capacity.

### 3) sc-proxy code audit checklist

In `billing.py` / `proxy.py`, confirm:
- all DB access paths use `with db.get_conn()`
- no direct `db.pool.getconn()` in request/response hot paths
- failed/stale connections are returned with `close=True`
- singleton DB object is initialized once per process

### 4) Immediate mitigation

- Lower pool maxima first (fastest rollback-safe mitigation):
  - sc-proxy: reduce `DB_POOL_MAX` (e.g., 50 → 20)
  - also reduce secondary services' pool max where possible
- Temporarily scale down non-critical machines (admin/aux services)
- Redeploy and re-check `pg_stat_activity`

### 5) Completion criteria for incident

- Total DB connections stable under expected aggregate ceiling
- No monotonic connection growth over at least 20–30 minutes
- DB memory remains stable after traffic bursts

## Geo-restricted upstream debugging (use SC-VPN correctly)

When a target API blocks default region access, do not set global `HTTP_PROXY`/`HTTPS_PROXY` for the whole service.

- Use SC-VPN per request only (example: `http://jp:x@sc-vpn.internal:8080`).
- Keep `sc-proxy` as the primary path; SC-VPN is a fallback for region-specific failures.
- Current SC-VPN fixed country codes: `au,ch,de,jp,my,mx,th,za,br,ar,sg,hk,gb,nl,fr,se,es,it`.
- Unknown region returns `502 Bad Gateway`; switch to one of the fixed codes above.

## Guardrails

- No hot reload assumptions; use redeploy for stable updates.
- Prefer clean switch; avoid alias/compat hacks unless explicitly requested.
- One change set per deploy whenever possible (easy rollback and attribution).
- Never claim success without verifying with real proxy requests.
- Keep plugin code minimal and isolated.

---

## Done criteria

A change is done only when all are true:

1. File edits match requested business change.
2. Deploy succeeded on target Fly app.
3. Changed API requests pass through proxy.
4. Billing/rate-limit behavior matches requested outcome.
5. Passthrough non-paid domains still unbilled.
6. Results are validated with concrete request outputs.

---

## Recommended caller-id conventions for tests

- Chat smoke: `chat:<topic>`
- Burst/rate test: `chat:<api>-ratelimit`
- Pricing test: `chat:<api>-pricing`

This makes DB verification and incident tracing straightforward.