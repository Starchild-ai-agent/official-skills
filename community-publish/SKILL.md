---
name: community-publish
version: 0.16.4
description: |
  Publish previews to a public URL, open-source projects to community GitHub, and list services (free or paid) on the Service Marketplace.

  Use when the user wants to share, publish, list, open-source, or monetize what they built (e.g. make this dashboard public, share my project, push to GitHub, 上架到服务市场, 上架付费服务, 提交审核).
delivery: script
metadata:
  starchild:
    emoji: 📦
    skillKey: community-publish
user-invocable: true
disable-model-invocation: false

---

## Two concepts: PUBLISH vs LIST — never confuse them

This skill handles two fundamentally different concepts. Mixing them up is the #1 source of wrong answers.

| Concept | What it means | Functions |
|---|---|---|
| **PUBLISH (发布)** | Make something **accessible** — a URL works, or code is on GitHub | `publish_preview`, `unpublish_preview`, `list_published_previews`, `open_source`, `remove_open_source`, `list_open_source`, `get_open_source`, `fork`, `validate_open_source` |
| **LIST (上架)** | Make something **discoverable/purchasable** on the marketplace | Free: `list_in_dashboard`, `unlist_from_dashboard`, `get_listing_status`<br>Paid: `create_paid_service`, `submit_for_review`, `get_review_status`, `publish_service`, `unpublish_service`, `list_my_services`, `get_service`, `update_service`, `delete_service`, `restore_service`<br>Browse + consumer: `explore_services`, `get_service_detail`, `get_service_pricing`, `get_service_reviews`, `write_service_review`, `favorite_service`, `unfavorite_service`, `get_favorite_services`, `get_user_services`, `get_service_earnings`, `get_earnings_summary` |

**Publishing does NOT auto-list.** `publish_preview()` only allocates the URL. `open_source()` only pushes code. Neither makes the project discoverable on the marketplace — that requires a separate, deliberate LIST call.

### Listing has two flows

| Flow | When to use | Review? | Pricing? | Functions |
|---|---|---|---|---|
| **Free listing** | Free project, show on `/projects` gallery | No | No | `list_in_dashboard()` |
| **Paid listing** | Charge for access via x402 | Yes (5 checks) | Yes (USDC on Base) | `create_paid_service()` → `submit_for_review()` → `publish_service()` |

> **`POST /api/services` no longer accepts `service_type: "free_project"`.** Free listing is done by `list_in_dashboard()` (the project gallery flow). Paid listing uses `create_paid_service()` + review + publish (the service API flow).

---

## Visibility model — read this before answering "can others see it?"

A project's "publicness" is **three orthogonal switches**, not one:

| Switch | Off state | On state | Flipped by |
|---|---|---|---|
| **URL access** | Visiting the URL returns 404 | URL works for anyone who has the link | `publish_preview` / `unpublish_preview` |
| **Gallery discoverability** | Not on `/projects` gallery | Appears in the gallery | `list_in_dashboard` / `unlist_from_dashboard` |
| **Marketplace listing** | Not on the Service Marketplace | Discoverable + purchasable | `create_paid_service` + `publish_service` / `unpublish_service` |

A project can be in any combination. Never collapse these into "is it public yet".

**Status questions are read-only operations.** Whenever the user asks:
- "is it visible / public / discoverable yet?"
- "上架了吗 / 在 dashboard 上吗 / 别人能看到吗"
- "is the listing live?"

The authoritative answer comes ONLY from a fresh `get_listing_status(slug)` (free) or `get_review_status(service_id)` (paid) call. Do NOT infer from past actions.

---

## Project types — three only

| type | What it is | Eligible for `publish_preview()`? |
|---|---|---|
| `task` | Scheduled cron/interval job | No (no HTTP port) |
| `service` | Long-running HTTP service (dashboard, API, page) | **Yes** |
| `script` | One-shot script | No (no HTTP port) |

---

## Routing — match user intent to the right action

### A. Status intents — user wants to know current state

| Sample phrasing | Action |
|---|---|
| "is it visible / public / discoverable / live?" | `get_listing_status(slug)` |
| "上架了吗 / 在 dashboard 上吗 / 别人能不能看到" | `get_listing_status(slug)` |
| "what URLs do I have published?" / "我发布了哪些" | `list_published_previews()` |
| "what's open-sourced?" / "都有哪些开源代码" | `list_open_source(...)` |
| "我的服务" / "my services" / "我的付费服务" | `list_my_services()` |
| "审核状态" / "审核通过了吗" / "review status" | `get_review_status(service_id)` |

### B. Action intents — user wants to change state

| Sample phrasing | Action | Notes |
|---|---|---|
| "publish" / "share" / "make public" / "公开" / "发布" (no qualifier) | `publish_preview(preview_id)` | Allocates the URL only. Listing is NOT auto-flipped. |
| "list on the dashboard" / "上架" / "show on community" / "make discoverable" / "发到广场" | `list_in_dashboard(slug)` | Free listing. Requires the preview to already exist. |
| "上架付费服务" / "make this a paid service" / "上架到服务市场（付费）" | `create_paid_service(...)` → `submit_for_review()` → `publish_service()` | Paid listing. Needs x402 config first. |
| "publish AND list" / "发布并上架" | `publish_preview()` THEN `list_in_dashboard()` | Two separate calls in order. |
| "remove from dashboard" / "下架" / "unlist" / "hide from gallery" | `unlist_from_dashboard(slug)` | Free listing only. Preview URL stays alive. |
| "下架付费服务" / "unpublish service" | `unpublish_service(service_id)` | Paid listing only. |
| "open source" / "open-source the code" / "开源代码" | `open_source(project_dir)` | Pushes code to GitHub. Does NOT list. |
| "unpublish the URL" / "take down the link" | `unpublish_preview(slug)` | Listing row stays. |
| "remove the open source" / "delete from GitHub" | `remove_open_source(slug)` | |
| "fork" / "install someone's project" | `fork(source)` | |
| "提交审核" / "submit for review" | `submit_for_review(service_id)` | Paid only |
| "发布服务" / "publish my service" | `publish_service(service_id)` | Paid only, requires approved |
| "更新服务" / "update service" | `update_service(service_id, ...)` | Paid only |
| "删除服务" / "delete service" | `delete_service(service_id)` | Paid only |
| Ambiguous after rereading | Ask one question | "你是要 (a) 发布公开 URL，(b) 免费上架到广场，(c) 付费上架到服务市场，还是 (d) 开源代码？" |

---

## Cross-link via `publisher:` binding

When the same project has BOTH a public URL AND open-sourced code, you want them paired so the frontend renders "View Source" on the listing card and "Visit Live Demo" on the code card. This skill drives that pairing through one explicit binding in project.yaml.

### How to declare the binding

Add a `publisher:` block to `project.yaml`:

```yaml
name: my-app
type: service
version: 1.0.0
publisher:
  code_slug: my-app               # OPTIONAL — defaults to manifest.name
  public_slug: my-app-pub         # OPTIONAL — URL suffix; defaults to code_slug
```

Both fields are optional. If omitted, both default to `manifest.name`.

### Either side can be published first

The gateway holds a pending entry until the second side arrives. **No ordering requirement**, no manual link step.

| Order | What happens |
|---|---|
| `open_source` first → `publish_preview` second | open_source records pending entry; publish_preview consumes it and links |
| `publish_preview` first → `open_source` second | publish_preview records pending entry (needs `publisher_code_slug` arg); open_source consumes it and links |

### Manual repair (rare)

If a pairing was wired wrong (e.g. after a rename), use:

```python
link_to_listing(listing_slug="2004-my-app-pub", code_slug="my-app")
```

---

## Architecture

```
                community.iamstarchild.com (single gateway domain)
                              │
            ┌─────────────────┼─────────────────────┐
            │                 │                     │
   ┌────────▼─────────┐  ┌───▼────────────┐  ┌─────▼──────────┐
   │  /api/register   │  │/api/code-      │  │ /api/services  │
   │  /api/unregister │  │ projects/*     │  │ /api/projects- │
   │  /api/list       │  │ (GitHub-backed)│  │ query/*        │
   └────────┬─────────┘  └───┬────────────┘  └─────┬──────────┘
            │                │                     │
   ┌────────▼─────────┐  ┌───▼────────────┐  ┌─────▼──────────┐
   │ DB: route table  │  │ GitHub:        │  │ DB:            │
   │ + project_       │  │ community-     │  │ service_       │
   │   listings       │  │ projects repo  │  │ listings       │
   └──────────────────┘  └────────────────┘  │ (paid services)│
     publish_preview()    open_source()      └────────────────┘
                                              list_in_dashboard()
                                              create_paid_service()
```

---

## PUBLISH: `publish_preview()` — public URL

`publish_preview(preview_id, slug="", title="", publisher_code_slug="")`

Map a running service to `https://community.iamstarchild.com/{user_id}-{slug}`.

- `preview_id`: from `preview(action='serve')`. Must be `status=running`.
- `slug`: URL suffix only (lowercase alphanumeric + hyphens, 3-50 chars). User_id prefix is added automatically.
- `title`: display name for the listing.
- `publisher_code_slug`: optional cross-link binding to a code project's slug.

Returns `{"ok": True, "url": "...", "publisher": {...}, "hint": "...",
"x402_detected": bool}` — plus a `next_step` warning when `x402_detected`
is true (complete the paid-listing chain).

**Constraints:**
- **`publish_preview` does NOT create a paid listing.** If the endpoint
  charges via x402 (returns 402), the publish flow is INCOMPLETE until you
  also run `create_paid_service` → `submit_for_review` → `publish_service`
  — otherwise the marketplace shows nothing or "free". The return value
  flags this (`x402_detected: true` + `next_step`) when billing is detected.
- Max 20 published previews per user (gateway returns 429 over).
- Service must be running. Stops working when the container goes down.
- Only works inside the Starchild Fly container (needs `FLY_MACHINE_ID`).
- **Listing visibility default is `is_public=false`.** A successful `publish_preview` allocates the URL but does NOT make it discoverable. Discovery requires a separate `list_in_dashboard()` call.

**Companions:**
- `unpublish_preview(slug)` — remove the public URL.
- `list_published_previews()` — all currently published preview URLs for this user.

---

## PUBLISH: `open_source()` — push code to GitHub

`open_source(project_dir, version_bump="patch", message="")`

Push project source to `community-projects/projects/{user_id}/{slug}/` on GitHub.

- `project_dir`: e.g. `output/projects/my-task`
- `version_bump`: `patch` | `minor` | `major` | `none`
- `message`: commit message body describing what this version changed.
  **You (the agent) should always compose this** based on the actual code
  changes you made in this session — never leave it blank if you know
  what changed. Aim for one to three short lines describing the user-visible
  change.

**This is a PUBLISH action only — it does NOT list anything on the marketplace.**
To make a project discoverable, call `list_in_dashboard()` (free) or
`create_paid_service()` (paid) separately after publishing.

**Companions:**
- `fork(source, dest_dir=None)` — install someone else's open-sourced project locally
- `list_open_source(type=None, tag=None, user=None, q=None)` — browse the GitHub catalog
- `get_open_source(source)` — fetch one project's full metadata
- `remove_open_source(slug)` — delete project directory from GitHub catalog (owner only)
- `validate_open_source(project_dir)` — pre-flight check before publishing

### Project structure

Every project under `output/projects/{slug}/`:

```
project.yaml      # metadata (name, version, type, env_required, sc_proxy, publisher)
PROJECT.md        # required sections: What / Required env / How to start / Outputs / Troubleshooting
.env.example      # all env vars with placeholder values
.gitignore        # secrets blacklist
src/
  ├── run.py       # for type=task (must start: # -*- task-system: v3 -*-)
  ├── index.html   # for type=service (or app.py + frontend)
  └── main.py      # for type=script
```

---

## LIST (FREE): `list_in_dashboard()` — show on /projects gallery

`list_in_dashboard(slug, name=None, description="", cover_url=None, tags=None)`

Make a published preview discoverable in the public gallery at `https://community.iamstarchild.com/projects`. Without this, the preview URL works but is invisible to anyone who doesn't already know it.

- `slug`: the **full** slug returned by `publish_preview()` (i.e. `{user_id}-{suffix}`).
- `name`: gallery card display name. Defaults to `slug`.
- `description`: ≤500 chars.
- `cover_url`: must be on `storage.googleapis.com`, `image.thum.io`, or `api.microlink.io`.
- `tags`: ≤5 tags, ≤20 chars each.

Returns `{"ok": True, "listing": {...}, "url": "...", "dashboard_url": "..."}`.

**Constraints:**
- Requires `publish_preview()` to have run first for the same slug — returns 404 otherwise.
- Idempotent: calling again with different name/tags updates the existing listing.
- No review, no pricing — this is the free listing flow.

**Companions:**
- `unlist_from_dashboard(slug)` — remove from gallery, keep URL alive.
- `get_listing_status(slug)` — read-only check: returns `{ok, exists, is_public, listing}`.

---

## LIST (PAID): Paid service listing on the Service Marketplace

Paid services charge for access via x402 (on-chain USDC settlement on Base). They require automated review before going live.

### Service lifecycle & review states

```
                ┌─────────────────────────────────────────────┐
                │                                             │
  create ──▶ draft ──▶ pending ──▶ approved ──▶ published ◀──┤
                │            │           │          │         │
                │            └──▶ rejected ────────┤         │
                │                               (fix & resubmit)│
                │                                             │
                └──────────────────────────────────────────────┘
                                              │
                                              ▼
                                     unavailable ──▶ restore ──▶ published
                                        (auto, health-check failures)
```

All paid services must pass review: `draft` → `pending` → `approved` → `published`.

### Flow B — Paid Project listing

1. **Have a running project** with a public URL (via `publish_preview()`).
2. **Configure x402 charging** on the project's access endpoint using the **x402 skill**.
   The endpoint must return `402 Payment Required` when unpaid, and `200` + data after payment.
3. **Create the service record:**

```python
create_paid_service(
    name="Premium Trading Signals",
    description="Real-time trading signals with on-chain confirmation.",
    category="数据服务",
    service_type="paid_project",
    project_slug="33-premium-signals",  # FULL published slug WITH user prefix (the URL path segment)
    api_endpoint="https://community.iamstarchild.com/33-premium-signals",
    provider_wallet="0xAbC...yourBaseWallet",
    pricing_model="monthly",
    price=10,
    service_description="Subscribers get a dashboard with live trading signals.",
)
```

   Required paid-project fields: `name`, `description`, `category`, `service_type`,
   `project_slug`, `api_endpoint`, `provider_wallet`, `pricing_model`, `price`,
   `service_description`.

   ⚠️ `project_slug` must be the **full published slug including the user prefix**
   (e.g. `33-premium-signals`, exactly the path segment in the project URL
   `https://community.iamstarchild.com/<slug>/`). The gateway derives the API
   endpoint as `publicUrl + "/" + project_slug` when `api_endpoint` is not set,
   so an unprefixed or wrong slug breaks endpoint derivation and the
   project↔service association. Fix an existing record with
   `update_service(service_id, project_slug="<full-slug>")` — no re-listing needed.

4. **Submit for review:**

```python
submit_for_review(service_id)
```

   This kicks off the automated review asynchronously. The service moves to `pending`.

5. **Poll review status** until it's no longer `pending`:

```python
get_review_status(service_id)
```

6. **If approved → publish:**

```python
publish_service(service_id)
```

7. **If rejected → read feedback, fix, resubmit:**
   The `review_feedback` field and `latest_task.checks` explain which of the 5 checks failed.
   Call `update_service(service_id, ...)` to fix, then `submit_for_review()` again.

### Flow C — Paid API listing

A paid API is an external API service that already implements x402 charging.

> **⚠️ Choose `paid_project` if the API belongs to a published Starchild project.**
> If your API has a landing page / dashboard published via `publish_preview()` (i.e. it
> exists as a project on community.iamstarchild.com), use `service_type="paid_project"`
> + `project_slug=<full published slug WITH user prefix>` (Flow B) — NOT `paid_api`. The `project_slug` is what
> links the service to the project card (pricing badge, cross-navigation). A `paid_api`
> listing has no project association, so the project card will keep showing "Free".
> Use `paid_api` only for truly external/standalone APIs with no Starchild project.
> Forgot the link? `update` the service record with `project_slug` — no need to re-list.

1. **Have an x402-enabled API** — the endpoint must return `402` when unpaid and `200` + data
   after a valid `X-PAYMENT` header. Use the **x402 skill** to implement this if needed.
2. **Create the service record** (`service_type = "paid_api"`):

```python
create_paid_service(
    name="On-chain Whale Tracker API",
    description="REST API returning real-time whale wallet movements across 12 chains.",
    category="数据服务",
    service_type="paid_api",
    api_endpoint="https://api.example.com/v1/whales",
    provider_wallet="0xAbC...yourBaseWallet",
    pricing_model="pay_per_use",
    price=0.01,
    free_trial_count=3,
    api_documentation="# Whale Tracker API\n\n## GET /v1/whales\n\nReturns recent whale transactions.\n\n### Parameters\n| name | type | required | description |\n|---|---|---|---|\n| chain | string | no | Filter by chain id (default: all) |\n| limit | int | no | Max results (default: 50, max: 200) |\n\n### Response\n```json\n[{\"hash\":\"0x...\",\"from\":\"0x...\",\"to\":\"0x...\",\"value\":\"1000000\",\"token\":\"USDC\",\"chain\":\"base\",\"ts\":1700000000}]\n```",
    example_request="curl https://api.example.com/v1/whales?chain=base&limit=10",
    example_response='[{"hash":"0xabc...","from":"0x111...","to":"0x222...","value":"5000000","token":"USDC","chain":"base","ts":1700000000}]',
)
```

   Required paid-API fields: `name`, `description`, `category`, `service_type`, `api_endpoint`,
   `provider_wallet`, `pricing_model`, `price`, `api_documentation`, `example_request`,
   `example_response`. Optional: `free_trial_count` (only for `pay_per_use`).

3. **Submit for review** → same as Flow B step 4.
4. **Poll review status** → same as Flow B step 5.
5. **If approved → publish** → same as Flow B step 6.
6. **If rejected → fix & resubmit** → same as Flow B step 7.

### Review checks (5 items, all must pass for paid services)

The automated reviewer runs these checks against the `api_endpoint`:

| # | Check | What it verifies |
|---|---|---|
| 1 | `api_reachable` | The endpoint returns `402 Payment Required` when no `X-PAYMENT` header is sent |
| 2 | `pricing_consistency` | The `amount` in the 402 response's `accepts` matches the `price` you declared (in USDC base units) |
| 3 | `x402_payment` | After a valid x402 payment, the endpoint returns `200` + data |
| 4 | `response_match` | The actual response's key fields match your `example_response` |
| 5 | `doc_completeness` | `api_documentation` includes parameter descriptions, response format, and at least one example |

   Check #5 is keyword-matched: the doc must contain a "Response" (or "响应格式")
   section with actual body text under the heading — an empty section fails review.
   `service_description` (paid_project) and `api_documentation` / `example_request` /
   `example_response` (paid_api) are enforced at call time by `create_paid_service()`,
   which errors before creating an unreviewable record.

**Common rejection causes:**
- 402 response `amount` doesn't match declared `price` (off by decimals / wrong unit).
- Endpoint doesn't return 402 at all (x402 not wired up, or returns 200 to unauthenticated requests).
- `example_response` doesn't match what the API actually returns after payment.
- Documentation missing parameter table or response schema.

### Pricing models

All paid services use the x402 `exact` payment scheme (on-chain USDC settlement on Base).

| `pricing_model` | Meaning | x402 behavior | Typical use |
|---|---|---|---|
| `pay_per_use` | Per-call charge | Every request with valid `X-PAYMENT` → settle (charge) | API calls |
| `lifetime` | One-time buyout | First payment settles; subsequent requests verify past settlement, no re-charge | One-time purchases |
| `monthly` | Monthly subscription | Settles once per billing month; re-charge after expiry | Web subscriptions, API monthly plans |
| `weekly` | Weekly subscription | Settles once per 7 days; re-charge after expiry | Short-term subscriptions |
| `quarterly` | Quarterly subscription | Settles once per 90 days; re-charge after expiry | Quarterly plans |
| `yearly` | Yearly subscription | Settles once per 365 days; re-charge after expiry | Annual plans (often discounted) |
| `prepaid` | Prepaid balance | User deposits via `deposit-settle` (one on-chain tx), then each call debits balance off-chain (zero gas) | High-frequency micro-payments |

> `free_trial_count` is only valid for `pay_per_use` — allows N free calls before charging.

#### Multi-plan (multiple pricing options)

A service can offer multiple pricing plans simultaneously (e.g. weekly + monthly + yearly). Pass `pricing_options` array when creating the service:

```python
create_paid_service(
    ...,
    pricing_options=[
        {"pricing_model": "weekly", "price": 3, "is_default": True, "label": "Weekly"},
        {"pricing_model": "monthly", "price": 10, "label": "Monthly"},
        {"pricing_model": "yearly", "price": 90, "label": "Yearly (Save 42%)"},
    ],
)
```

**Rules**:
- `pay_per_use` cannot be combined with other pricing models.
- Subscription models (weekly/monthly/quarterly/yearly) can be freely combined.
- `lifetime` and `prepaid` can be combined with subscription models.
- One option must be marked `is_default: True` (or the first is auto-marked).
- The service's `pricing_model` and `price` fields are auto-synced to the default option.

**Multi-plan 402 requirement**: The service's x402 middleware must support the `X-Pricing-Model` header — when a client sends `X-Pricing-Model: yearly`, the 402 response must return the yearly plan's price. Review verifies each plan's 402 amount individually.

**Reference**: See `x402-facilitator/docs/pricing-models.md` for the full specification.

### Paid service management functions

| Function | Purpose |
|---|---|
| `create_paid_service(...)` | Create a service record (draft state) |
| `submit_for_review(service_id)` | Submit for automated review |
| `get_review_status(service_id)` | Poll review progress + per-check details |
| `publish_service(service_id)` | Go live (requires approved) |
| `unpublish_service(service_id)` | Take down (published → draft) |
| `list_my_services(cursor, limit)` | List your services (paginated) |
| `get_service(service_id)` | Fetch one service by ID |
| `update_service(service_id, **fields)` | Update service fields (e.g. fix after rejection) |
| `delete_service(service_id)` | Permanently delete a service |
| `restore_service(service_id)` | Restore an unavailable service back to published |

### Marketplace browse & consumer functions

These functions let the agent browse the Service Marketplace, read reviews,
write reviews, manage favorites, and check earnings — same as the web frontend.

| Function | Purpose |
|---|---|
| `explore_services(search, category, sort, ...)` | Browse the marketplace with filtering + pagination |
| `get_service_categories()` | List all categories with counts |
| `get_service_detail(service_id)` | Public detail for a published service (includes docs, increments views) |
| `get_service_pricing(service_id)` | Verified pricing with real-time x402 check |
| `get_service_reviews(service_id, sort)` | List reviews for a service (public) |
| `write_service_review(service_id, rating, comment)` | Submit/update a review (must have purchased or used first) |
| `get_user_services(user_id)` | Get a user's published paid services (public, for profile display) |
| `favorite_service(service_id)` | Add a service to favorites |
| `unfavorite_service(service_id)` | Remove a service from favorites |
| `get_favorite_services(cursor, limit)` | List the current user's favorite services |
| `get_service_purchase_status(service_id)` | Check if the current user has purchased/used a service |
| `get_service_earnings(service_id)` | Earnings stats for a single service (owner only) |
| `get_earnings_summary()` | Earnings summary across all services (owner only) |
| `get_service_onchain_records(service_id)` | On-chain USDC settlement records (owner only) |

---

## Usage from a bash block

```bash
python3 - <<'EOF'
import sys
# Prefer the registered skill tools (read this SKILL.md via read_file to
# load them) over hand-written imports of exports.py. If you DO need a
# direct import: the directory name has a HYPHEN, so dotted imports
# (`from skills.community_publish import ...`) raise ModuleNotFoundError.
# Use this sys.path pattern (or importlib.util.spec_from_file_location).
sys.path.insert(0, "/data/workspace/skills/community-publish")
from exports import (
    # PUBLISH: public URL
    publish_preview, unpublish_preview, list_published_previews,
    # PUBLISH: open source code
    open_source, remove_open_source, fork,
    list_open_source, get_open_source, validate_open_source,
    # LIST: free (project gallery)
    list_in_dashboard, unlist_from_dashboard, get_listing_status,
    # LIST: paid (service marketplace)
    create_paid_service, submit_for_review, get_review_status,
    publish_service, unpublish_service,
    list_my_services, get_service, update_service, delete_service,
    restore_service,
    # MARKETPLACE: browse + consumer actions
    explore_services, get_service_categories, get_service_detail,
    get_service_pricing, get_service_reviews, write_service_review,
    get_user_services, favorite_service, unfavorite_service,
    get_favorite_services, get_service_purchase_status,
    get_service_earnings, get_earnings_summary, get_service_onchain_records,
    # Manual repair (rare)
    link_to_listing,
)

# Step 1: Publish the URL
print(publish_preview(preview_id="my-app-a3f1", slug="my-app"))

# Step 2a: Free listing — show on gallery
print(list_in_dashboard(slug="33-my-app", name="My App", description="A cool app"))

# OR Step 2b: Paid listing — create service + review + publish
res = create_paid_service(
    name="My Paid App",
    description="Premium features",
    category="工具服务",
    service_type="paid_project",
    project_slug="33-my-app",  # full published slug WITH user prefix
    api_endpoint="https://community.iamstarchild.com/33-my-app",
    provider_wallet="0xAbC...",
    pricing_model="monthly",
    price=5,
    service_description="Subscribers get premium features.",
)
print(res)
# Then: submit_for_review(res["service_id"]) → poll get_review_status() → publish_service()
EOF
```

---

## Behavioral rules

- **Show the diff before `open_source()`**. After `validate_open_source`, summarize what's about to be pushed and ask for confirmation. Exception: explicit "publish without confirmation" or re-publish of a known good project.
- **Never auto-run setup.sh on fork**. Show the command, let the user confirm.
- **Always collect env in one batch on fork**. Read project's `env_required`, diff against `workspace/.env`, call `request_env_input` ONCE with the missing keys.
- **Never skip review for paid services.** All paid services must pass review. `publish_service()` will reject a service that isn't `approved`.
- **`api_endpoint` must be the x402 charge endpoint.** For paid projects this is the project's public URL. For paid APIs it's the external API URL. The reviewer hits this URL expecting a `402`.
- **Price unit is USDC.** The 402 response's `accepts.amount` is in **base units** (6 decimals for USDC). A `$0.01` price → `amount: "10000"`. Mismatch here is the #1 review failure.
- **Don't fabricate review results.** Always call `get_review_status()` to check — never assume the review passed because you submitted it.
- **Don't conflate publish and list.** `publish_preview()` allocates a URL. `list_in_dashboard()` / `create_paid_service()` makes it discoverable. These are separate, deliberate steps.
- **Slug rules**: lowercase alphanumeric + hyphens, 3-50 chars, no leading/trailing hyphen.
- **Version rules** (`open_source`): strict semver. Re-publishing same version is rejected.
- **URL ≠ code ≠ listing**: a public URL going down does NOT remove the open-source code or the marketplace listing, and vice versa. They're independent.

---

## Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `publish_preview`: `Preview not found` | Wrong preview_id, or service was stopped | Check `/data/previews.json`, restart with `preview(action='serve')` |
| `publish_preview`: `429 Too many published previews` | Hit 20-per-user gateway cap | `unpublish_preview()` something old first |
| `publish_preview`: `FLY_MACHINE_ID not set` | Running locally, not in Starchild container | URL publish only works in the production container |
| `list_in_dashboard`: `404 No preview found` | `publish_preview()` hasn't run for this slug yet | Call `publish_preview()` first |
| `open_source`: `400 Validation failed: env names not in .env.example` | Listed `MY_KEY` in `env_required` but forgot `.env.example` | Add the missing key to `.env.example` |
| `open_source`: `400 Possible secret detected` | Secret scanner found a real-looking API key | Move to env var; `.env.example` value should be `your-key-here` |
| Marketplace shows service as free / missing after publish | Only `publish_preview()` was run — URL publish ≠ paid listing | Complete the chain: `create_paid_service` → `submit_for_review` → `publish_service` |
| `create_paid_service`: `400 Free services should be published through the Project publish flow` | Tried `service_type: "free_project"` | Use `list_in_dashboard()` for free projects, not `create_paid_service()` |
| `publish_service`: `400 not in a publishable state` | Service isn't `approved` yet | Poll `get_review_status()` — if rejected, fix and re-submit |
| Review rejected: `pricing_consistency` failed | 402 response `amount` doesn't match declared `price` | Ensure `amount` = `price * 1000000` (USDC 6 decimals) |
| Review rejected: `api_reachable` failed | Endpoint doesn't return 402 | Wire up x402 charging on the endpoint first |

---

## References

- `lib/manifest.py` — project.yaml parser/writer + semver helpers
- `lib/validate.py` — local pre-publish validation (mirrors gateway-side checks)
- `lib/install.py` — type-specific install handlers (task/service/script)
- `lib/gateway.py` — HTTP client for `/api/register` (URL), `/api/code-projects/*` (code), `/api/projects-query/*` (free listing), `/api/services/*` (paid listing)
