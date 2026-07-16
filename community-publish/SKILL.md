---
name: community-publish
version: 0.25.0
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
| **LIST (上架)** | Make something **discoverable/purchasable** on the marketplace | Free: `list_in_dashboard`, `unlist_from_dashboard`, `delete_listing`, `get_listing_status`<br>Paid: `create_paid_service`, `submit_for_review`, `get_review_status`, `publish_service`, `unpublish_service`, `list_my_services`, `get_service`, `update_service`, `delete_service`, `restore_service`<br>Browse + consumer: `explore_marketplace`, `explore_services`, `get_service_detail`, `get_service_pricing`, `get_service_reviews`, `write_service_review`, `favorite_service`, `unfavorite_service`, `get_favorite_services`, `get_user_services`, `get_service_earnings`, `get_earnings_summary` |

**Publishing does NOT auto-list.** `publish_preview()` only allocates the URL. `open_source()` only pushes code. Neither makes the project discoverable on the marketplace — that requires a separate, deliberate LIST call.

### Listing has two flows

| Flow | When to use | Review? | Pricing? | Functions |
|---|---|---|---|---|
| **Free listing** | Free project, show on `/projects` gallery | No | No | `list_in_dashboard()` |
| **Paid listing** | Charge for access via x402 | Optional (5-check self-report) | Yes (USDC on Base) | `create_paid_service()` → `submit_for_review()` (recommended pre-listing self-check) → `publish_service()` |

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
| "上架付费服务" / "make this a paid service" / "上架到服务市场（付费）" | `create_paid_service(...)` → `submit_for_review()` (recommended) → `publish_service()` | Paid listing. Needs x402 config first. |
| "publish AND list" / "发布并上架" | `publish_preview()` THEN `list_in_dashboard()` | Two separate calls in order. |
| "remove from dashboard" / "下架" / "unlist" / "hide from gallery" | `unlist_from_dashboard(slug)` | Free listing only. Soft-unlist (sets `is_public=false`, `review_status='unlisted'`, preserves stats). Preview URL stays alive. |
| "下架付费服务" / "unpublish service" | `unpublish_service(service_id)` | Paid listing only. |
| "open source" / "open-source the code" / "开源代码" | `open_source(project_dir)` | Pushes code to GitHub. Does NOT list. |
| "unpublish the URL" / "take down the link" / "停止服务" | `unpublish_preview(slug)` | Stops the preview container service only. Does NOT affect listing state (`is_public`/`review_status` unchanged). URL becomes inaccessible (404). |
| "remove the open source" / "delete from GitHub" | `remove_open_source(slug)` | |
| "fork" / "install someone's project" | `fork(source)` | |
| "提交审核" / "submit for review" | `submit_for_review(service_id)` | Paid only. Advisory self-check — never required for publishing |
| "发布服务" / "publish my service" | `publish_service(service_id)` | Paid only, works from any pre-listed state |
| "更新服务" / "update service" | `update_service(service_id, ...)` | Paid only |
| "删除服务" / "delete service" | `delete_service(service_id)` | Paid only |
| "删除项目" / "delete listing" / "permanently remove from marketplace" | `delete_listing(slug)` | Free listing only. Permanently deletes the listing row AND the `community_slugs` record. URL becomes inaccessible (404). Removes from both explore and my-projects. Use `unlist_from_dashboard()` to hide without deleting. |
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
  also run `create_paid_service` → `submit_for_review` (recommended) → `publish_service`
  — otherwise the marketplace shows nothing or "free". The return value
  flags this (`x402_detected: true` + `next_step`) when billing is detected.
- Max 20 published previews per user (gateway returns 429 over).
- Service must be running. Stops working when the container goes down.
- Only works inside the Starchild Fly container (needs `FLY_MACHINE_ID`).
- **Listing visibility default is `is_public=false`.** A successful `publish_preview` allocates the URL but does NOT make it discoverable. Discovery requires a separate `list_in_dashboard()` call.

**Companions:**
- `unpublish_preview(slug)` — stop the preview container service. URL becomes inaccessible (404). Does NOT affect listing state (`is_public`/`review_status` unchanged).
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
- `unlist_from_dashboard(slug)` — soft-unlist from gallery (sets `is_public=false`, `review_status='unlisted'`, preserves view/favorite counts). URL stays alive. To re-list, call `list_in_dashboard()` again.
- `delete_listing(slug)` — permanently delete the listing row AND the `community_slugs` record (removes view/favorite counts). URL becomes inaccessible (404). Removes from both explore and my-projects. Use `unlist_from_dashboard()` to hide without deleting.
- `get_listing_status(slug)` — read-only check: returns `{ok, exists, is_public, listing}`.

---

## LIST (PAID): Paid service listing on the Service Marketplace

Paid services charge for access via x402 (on-chain USDC settlement on Base). An automated 5-check self-report is available; the owner decides when to go live (review never blocks publishing).

### Service lifecycle & review states (review is ADVISORY)

```
  create ──▶ published ──▶ submit_for_review ─▶ pending ─▶ approved / rejected
                │            (recommended BEFORE listing — advisory, never blocks)
                │                                    │ fix via update_service(), re-check
                ▼                                    ▼
           publish_service() ─────────────────▶ listed ◀─▶ unlisted (owner takedown / re-list)
                                                     │
                                                     ▼
                                          unavailable ──▶ restore ──▶ listed
```

Review is a **self-check, not a gate**: `submit_for_review()` runs 5 automated
checks (api_reachable, pricing_consistency, x402_payment, response_match,
doc_completeness) and stores a report for the owner. `publish_service()` works
from any pre-listed state — the owner reads the report and decides when to go
live. **Recommended order: run the self-check BEFORE `publish_service()`** so a
broken endpoint is caught before buyers can pay for it. A `rejected` report does NOT block listing; a check run against an
already-`listed` service never delists it.

### ⚡ Scenario Selection Decision Tree — MUST follow before creating any paid service

**Step 1: Does the service have a Starchild project page (published via `publish_preview()`)?**
- **YES, and the page is free to browse** → Flow D. Use `service_type="paid_project"` + `project_slug`. The free page is published via `publish_preview()`, and the paid API sits behind x402 on `/api/*` routes. The upstream app serves the free intro page at `/` and the paid API at `/api/*`.
- **YES, but the entire page requires payment** → Flow B (Form 1). Use `service_type="paid_project"` + `project_slug`. The user implements their own access control (paywall + credential validation). See the x402 skill's "Paid Project: two forms" section.
- **NO (standalone API, no project page)** → Flow C or E. Use `service_type="paid_api"` WITHOUT `project_slug`. Do NOT create an index.html or publish a preview — there is no free page. The public URL root will show the x402 402 challenge or gateway info.

**Step 2: Does the user want multiple API endpoints at different prices?**
- **YES** → Use `api_endpoints` array in ONE `create_paid_service()` call (Flow E). Do NOT create multiple separate services.
- **NO** → Single endpoint, use `api_endpoint` only.

**Step 3: Combine the answers:**

| User wants | Free page? | Multi-endpoint? | Flow | service_type | project_slug | api_endpoints |
|------------|-----------|-----------------|------|-------------|--------------|---------------|
| Paid subscription project (entire site behind paywall) | YES | NO | B | `paid_project` | required | — |
| Standalone paid API (no webpage) | NO | NO | C | `paid_api` | **omit** | — |
| Free intro page + paid API | YES | NO | D | `paid_project` | required | — |
| Free intro page + multiple paid APIs | YES | YES | D+E | `paid_project` | required | required |
| Multiple paid APIs (no webpage) | NO | YES | E | `paid_api` | **omit** | required |

### ⚠️ Common Flow confusion mistakes (from real incidents)

| Mistake | What goes wrong | Correct action |
|---------|----------------|----------------|
| User says "write an intro page AND a paid API" but agent uses `paid_api` + creates a separate project preview | Service and project are disconnected — marketplace shows two items, one free (blank) and one paid | Use `paid_project` + `project_slug` (Flow D). The intro page and API are ONE service. |
| User says "pure paid API" but agent creates an index.html and publishes a preview | Unnecessary free project page clutters the marketplace; the intro page may show blank/JSON | Do NOT create index.html or publish_preview. Use `paid_api` (Flow C). The x402 gateway's 402 response IS the API's self-description. |
| User says "multiple API endpoints" but agent creates N separate services | N marketplace cards instead of 1; port conflicts; upstream confusion | Create ONE service with `api_endpoints` array (Flow E). |
| Agent reuses an upstream port already taken by another service | Gateway proxies to the WRONG upstream — responses are from a different service | Each service MUST have a unique upstream port. Check `.x402/services.json` for conflicts. |
| Agent creates start.py with `/docs` route that conflicts with upstream's `/docs` | Flask `AssertionError: View function mapping is overwriting an existing endpoint` | Do NOT define `/`, `/docs`, or `/index.html` routes in both start.py and the upstream app — define them in only one place. |

**Key rules:**
- **Do NOT pass `project_slug` for standalone paid APIs.** `project_slug` belongs to `paid_project` only — including the "free webpage + paid API" pattern (Flow D, which uses `paid_project`). Passing a preview slug or a non-existent slug for a standalone `paid_api` creates a phantom association — the backend will silently clear it, but you should not have passed it in the first place.
- **Routing rule: service tied to a project page → `paid_project`; `paid_api` is ONLY for standalone APIs with no project page.** If your API has a published Starchild project (landing page/dashboard) that users can browse for free, use `service_type="paid_project"` + `project_slug` — this merges the service into the project card in the marketplace. If there is NO free project page, use `paid_api` and do NOT set `project_slug`. Passing `paid_api` + `project_slug` is auto-upgraded to `paid_project` by `create_paid_service()` (with a `project_slug_warning` in the response) — the final listing is always `paid_project`.
- `project_slug` must be the **full published slug WITH user prefix** (e.g. `33-my-app`), and must correspond to an existing row in `project_listings` (i.e. `publish_preview()` + `list_in_dashboard()` must have been called first).
- `api_endpoints` is for services with multiple endpoints at different prices; each endpoint has its own `path`, `price`, and optional `label`.
- A project with `project_slug` set will NOT appear in the "Free" tab — it moves to "All" and "Paid" tabs.
- **Merged-into-project-card visibility:** when a listed service has `project_slug` pointing to a PUBLIC project, it is folded into that project's card in unified marketplace views. Consequence: the service will NOT appear as a standalone item in `explore_services()` or `list_my_services()` — this is by design, not a listing failure. It is still live and purchasable via the project card, `get_service(service_id)`, and `get_user_services(user_id)`, and it IS discoverable via `explore_marketplace()` (unified feed). To verify a merged service is listed, check `get_service()` → `review_status == "listed"`, not `explore_services()` results.
- **When the user asks for multiple APIs, create ONE service with `api_endpoints`** — do NOT create multiple separate services. See Flow E.

### Flow B — Paid Project listing

A paid project charges for access. There are two forms — both use
`service_type="paid_project"` + `project_slug`:

**Form 1: Entire page behind paywall** — the page itself requires payment.
The user implements their own access control (a login-like component with
credential validation). The platform provides the x402 payment protocol;
the user implements the paywall UI and credential logic. See the x402
skill's "Paid Project: two forms" section for implementation details and
the "How to pay with Agent" documentation template.

**Form 2: Free page + paid API** — the page is free to browse, API calls
cost money. This is Flow D (below). The upstream app serves the free intro
page at `/` and the paid API at `/api/*`.

Both forms are the same pattern — the only difference is what the user
implements (paywall interceptor for Form 1, nothing extra for Form 2).

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

4. **Recommended: run the self-check BEFORE listing** — a broken endpoint
   listed on the marketplace can take buyers' money before you notice:

```python
submit_for_review(service_id)   # kicks off 5 automated checks asynchronously
get_review_status(service_id)   # poll until no longer pending, then show the
                                # report to the user — THEY decide what to fix
```

   A `rejected` report does not block listing. Read `review_feedback` +
   `latest_task.checks`, fix with `update_service()` if the owner wants, and
   re-run `submit_for_review()`.

5. **Publish** once the report is clean (or the owner accepts the findings —
   review is advisory and never gates this step):

```python
publish_service(service_id)
```

   The check can also be run again later against a listed service — it never
   delists it.

### Flow C — Paid API listing

A paid API is an external API service that already implements x402 charging.

> **⚠️ Do NOT pass `project_slug` for standalone paid APIs.**
> `project_slug` is ONLY for `paid_project` (required) or the "free webpage + paid API"
> pattern (Flow D, where a published Starchild project page exists). For a standalone
> `paid_api` with no associated free project page, omit `project_slug` entirely.
> The backend validates `project_slug` against `project_listings` and silently clears
> non-existent slugs, but you should not pass it in the first place.
>
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

   #### Ensuring purchases are recorded by Starchild

   For the Starchild marketplace to track purchases, earnings, and usage stats,
   choose one of the two approaches below based on your facilitator setup:

   **Option A — Use the Starchild facilitator (recommended)**

   Set your x402 middleware's facilitator URL to:

   ```
   https://starchild-x402-facilitator.fly.dev
   ```

   On successful settle, the Starchild facilitator automatically calls back
   community-gateway to record the purchase. No extra setup needed — proceed
   to step 2 with the default `create_paid_service()` call.

   **Option B — Use your own facilitator + proxy mode**

   If you use your own facilitator (or a third-party one), Starchild cannot
   receive settlement callbacks. Instead, pass `source="manual"` when creating
   the service record (step 2):

   ```python
   create_paid_service(
       ...,
       source="manual",   # ← enables proxy mode
   )
   ```

   This tells the marketplace to generate a **proxy URL** for your API:

   ```
   https://community.iamstarchild.com/proxy/{service_id}/...
   ```

   Users access your API through this proxy URL. The proxy transparently
   forwards requests to your real `api_endpoint` and, on successful payment
   (HTTP 200 with a `payment-signature` header), automatically records the
   purchase in Starchild's database. You do NOT need to change your facilitator
   URL or set up any callbacks.

   **402 response requirements** (checked during review):

   - The `402` response body **must** include a `pricingModel` field (platform format).
   - `payTo` **must** be your actual receiving wallet address (Base USDC).
   - The response must be a valid x402 challenge that clients can parse.

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
   `example_response`. Optional: `free_trial_count` (only for `pay_per_use`),
   `source` (`"manual"` for proxy mode — see step 1 Option B above; omit for default
   Starchild facilitator mode),
   `cover_url` (custom cover image URL — must be on `storage.googleapis.com` or other
   allowed domains; if not provided, the agent should auto-generate a suitable cover
   image based on the service name and description, upload it via the image upload
   service, and pass the resulting URL).

   #### Cover image for paid services

   Paid services do NOT auto-generate a cover image (unlike free projects which get
   auto-captured screenshots). Pass `cover_url` in `create_paid_service()` — same rules
   as `list_in_dashboard()`: must be on `storage.googleapis.com`, `image.thum.io`, or
   `api.microlink.io`. If the user provides an image, upload it via the image upload
   service and use the resulting URL. If not provided, generate a suitable cover image
   based on the service name and description (e.g. using an image generation skill),
   upload it, and pass the URL. You can also use `update_service(cover_url=...)` later
   to add or change the cover.

3. **Publish** → same as Flow B step 4.
4. **Recommended self-check** → same as Flow B step 5.

### Flow D — Free Webpage + Paid API (hybrid)

Your project has a free landing page (published via `publish_preview()`) AND a paid API
endpoint. Users can browse the project page for free, but API calls cost money.
The marketplace shows a single merged card with both "Visit Project" and "Call API" buttons.

1. **Publish the project** via `publish_preview()` — this creates the free landing page.
2. **Configure x402 charging** on the API endpoint (e.g. `/api/random` returns 402).
3. **Create the service record** with `service_type="paid_project"` + `project_slug`:

```python
create_paid_service(
    name="Random9 API",
    description="Random 9-digit number API. Free docs page + paid API calls.",
    category="工具服务",
    service_type="paid_project",
    project_slug="33-random9-api",  # FULL slug WITH user prefix — links to the free project page
    api_endpoint="https://community.iamstarchild.com/33-random9-api/api/random",
    provider_wallet="0xAbC...yourBaseWallet",
    pricing_model="pay_per_use",
    price=0.01,
    service_description="Paid access to the Random9 API endpoint; the docs page stays free.",  # required for paid_project
    api_documentation="# Random9 API\n## GET /api/random\nReturns a random 9-digit number.",
    example_request="curl https://community.iamstarchild.com/33-random9-api/api/random",
    example_response='{"random":"482917365","digits":9}',
)
```

   The `project_slug` merges this service into the project card. The project page (`/`)
   stays free; only the API endpoint (`/api/random`) requires payment.

   > Note: if `service_type="paid_api"` is passed together with `project_slug`,
   > `create_paid_service()` auto-upgrades it to `paid_project` and returns a
   > `project_slug_warning` — the stored listing is always `paid_project`. Passing
   > `paid_project` directly (as above) is the canonical form.

4. **Publish + optional self-check** — same as Flow B steps 4–5.

### Flow E — Multi-Endpoint API

Your service has multiple API endpoints at different prices (e.g. basic $0.01, premium $0.10).
Each endpoint is listed separately in the marketplace detail view.

> **⚠️ When the user asks for multiple APIs, create ONE service with `api_endpoints` — NOT multiple separate services.**
> For example, if the user says "develop three paid APIs and list them", do NOT call
> `create_paid_service()` three times. Instead, create a single service with an
> `api_endpoints` array containing all three endpoints. This gives users a unified
> marketplace card where they can see and purchase individual endpoints.
> Only create multiple services if the APIs are truly unrelated (different domains,
> different audiences, different pricing models).

1. **Configure x402 charging** with per-route pricing:
   ```bash
   python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
     --mode pay_per_use --price 0.01 \
     --route "GET /api/basic=$0.01" --route "GET /api/premium=$0.10" \
     --route "POST /api/batch=$0.50" \
     --network eip155:8453 --facilitator $FAC
   ```

2. **Create the service record** with `api_endpoints`:

```python
create_paid_service(
    name="Data API Service",
    description="Multiple API endpoints at different prices.",
    category="数据服务",
    service_type="paid_api",
    api_endpoint="https://example.com/api/basic",  # primary endpoint for review
    api_endpoints=[
        {"path": "GET /api/basic", "price": 0.01, "label": "Basic Query"},
        {"path": "GET /api/premium", "price": 0.10, "label": "Premium Query"},
        {"path": "POST /api/batch", "price": 0.50, "label": "Batch Process"},
    ],
    provider_wallet="0xAbC...yourBaseWallet",
    pricing_model="pay_per_use",
    price=0.01,  # price of the primary/default endpoint
    api_documentation="# Data API\n## GET /api/basic\nBasic data.\n## GET /api/premium\nPremium analytics.",
    example_request="curl https://example.com/api/basic",
    example_response='{"data":"basic market info"}',
)
```

   You can combine Flow D + Flow E: use `service_type="paid_project"` + `project_slug`
   together with `api_endpoints` to link a free project page with multi-endpoint pricing.
   The marketplace shows a merged project card with an endpoint list in the detail view.

3. **Publish + optional self-check** — same as Flow B steps 4–5.

### Self-check items (5 automated checks — advisory report, not a gate)

`submit_for_review()` runs these checks against the `api_endpoint`; the report is for the owner — failures never block or take down a listing:

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
| `create_paid_service(...)` | Create a service record (published state) |
| `submit_for_review(service_id)` | Run the 5-check self-report (advisory) |
| `get_review_status(service_id)` | Poll review progress + per-check details |
| `publish_service(service_id)` | Go live (any pre-listed state) |
| `unpublish_service(service_id)` | Take down (listed → unlisted) |
| `list_my_services(cursor, limit)` | List your services (paginated) |
| `get_service(service_id)` | Fetch one service by ID |
| `update_service(service_id, **fields)` | Update service fields (e.g. fix after rejection) |
| `delete_service(service_id)` | Permanently delete a service |
| `restore_service(service_id)` | Restore an unavailable service back to listed |

### Marketplace browse & consumer functions

These functions let the agent browse the Service Marketplace, read reviews,
write reviews, manage favorites, and check earnings — same as the web frontend.

| Function | Purpose |
|---|---|
| `explore_marketplace(search, paid_only, ...)` | ⭐ **UNIFIED browse — use this FIRST to find paid services/APIs.** Project cards + standalone services in one feed (same as web All/Paid tabs); the only search path that surfaces services merged into public project cards. Items have `type`: `service` (use `id`) or `project` (paid cards carry `service_id`) — feed into `get_service_detail()` |
| `explore_services(search, category, sort, ...)` | Browse STANDALONE service items only (services API). ⚠️ Services merged into a public project card do NOT appear here — use `explore_marketplace()` for full coverage |
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
    explore_marketplace, explore_services, get_service_categories, get_service_detail,
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
# Then: publish_service(res["service_id"]) — optionally submit_for_review() first for a self-check report
EOF
```

---

## Behavioral rules

- **Show the diff before `open_source()`**. After `validate_open_source`, summarize what's about to be pushed and ask for confirmation. Exception: explicit "publish without confirmation" or re-publish of a known good project.
- **Never auto-run setup.sh on fork**. Show the command, let the user confirm.
- **Always collect env in one batch on fork**. Read project's `env_required`, diff against `workspace/.env`, call `request_env_input` ONCE with the missing keys.
- **Review is advisory.** `publish_service()` works without review; still OFFER the self-check (`submit_for_review()`) so the owner sees whether buyers can actually pay before/after going live. Show the report to the user — the decision is theirs.
- **`api_endpoint` must be the x402 charge endpoint.** For paid projects this is the project's public URL. For paid APIs it's the external API URL. The reviewer hits this URL expecting a `402`.
- **Price unit is USDC.** The 402 response's `accepts.amount` is in **base units** (6 decimals for USDC). A `$0.01` price → `amount: "10000"`. Mismatch here is the #1 review failure.
- **Don't fabricate review results.** Always call `get_review_status()` to check — never assume the review passed because you submitted it.
- **Don't conflate publish and list.** `publish_preview()` allocates a URL. `list_in_dashboard()` / `create_paid_service()` makes it discoverable. These are separate, deliberate steps.
- **Slug rules**: lowercase alphanumeric + hyphens, 3-50 chars, no leading/trailing hyphen.
- **Version rules** (`open_source`): strict semver. Re-publishing same version is rejected.
- **URL ≠ code ≠ listing**: a public URL going down does NOT remove the open-source code or the marketplace listing, and vice versa. They're independent.
- **Do NOT pass `project_slug` for standalone `paid_api` services.** `project_slug` belongs to `paid_project` only — including the "free webpage + paid API" pattern (Flow D, which uses `paid_project`; passing `paid_api` + `project_slug` gets auto-upgraded to `paid_project` with a `project_slug_warning`). Passing a preview slug or non-existent slug for a standalone API creates a phantom association. The backend silently clears non-existent slugs, but you should not pass `project_slug` unless the user explicitly wants to link a free project page with the paid API.
- **When the user asks for multiple APIs, create ONE service with `api_endpoints`.** Do NOT call `create_paid_service()` multiple times for related APIs. Use the `api_endpoints` array to list all endpoints in a single service (Flow E). Only create multiple services if the APIs are truly unrelated (different domains, different audiences, different pricing models).

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
| Marketplace shows service as free / missing after publish | Only `publish_preview()` was run — URL publish ≠ paid listing | Complete the chain: `create_paid_service` → `publish_service` |
| `create_paid_service`: `400 Free services should be published through the Project publish flow` | Tried `service_type: "free_project"` | Use `list_in_dashboard()` for free projects, not `create_paid_service()` |
| `publish_service`: `400 not in a publishable state` | Service is already listed, unavailable, or deleted | Check `get_service()` state; `unavailable` → `restore_service()` |
| `submit_for_review`: `400 Free services do not require review` | The service record was created as a FREE type — the paid payload was built by hand (missing `service_type`/wallet/pricing) instead of via `create_paid_service()` | Delete it and recreate with `create_paid_service()` (all paid fields are required positional args, so this cannot happen through the function) |
| Review rejected: `pricing_consistency` failed | 402 response `amount` doesn't match declared `price` | Ensure `amount` = `price * 1000000` (USDC 6 decimals) |
| Review rejected: `api_reachable` failed | Endpoint doesn't return 402 | Wire up x402 charging on the endpoint first |
| `create_paid_service` response has `project_slug_warning` | Passed `project_slug` for a `paid_api` but the slug doesn't exist in `project_listings` | Backend cleared it automatically. If this is a standalone API, don't pass `project_slug`. If you intended Flow D, `publish_preview()` + `list_in_dashboard()` the project first, then `update_service()` with the correct slug. |
| `create_paid_service`: `500 Failed to create service` after delete→create cycles with the SAME name | Deleted services keep their slug (soft delete), and slug generation only tries a limited number of suffixes — repeated delete/recreate with one name exhausts them | Do NOT wait and retry — the failure is permanent for that name. Use a different service name, or `restore_service(service_id)` + `update_service()` instead of delete+recreate |
| Created multiple services when user asked for "multiple APIs" | Called `create_paid_service()` once per API instead of using `api_endpoints` | Use Flow E: one `create_paid_service()` call with `api_endpoints=[...]` array. Only split into multiple services if the APIs are truly unrelated. |
| Purchases not recorded for external API (own facilitator) | Service was created without `source="manual"`, so no proxy URL is generated and Starchild has no way to observe payments | Either switch to the Starchild facilitator (Option A) or recreate the service with `source="manual"` (Option B) |
| Proxy URL returns 502 for `source="manual"` service | The `api_endpoint` URL is unreachable from Starchild servers | Verify the external API is publicly accessible and not behind a firewall |

---

## References

- `lib/manifest.py` — project.yaml parser/writer + semver helpers
- `lib/validate.py` — local pre-publish validation (mirrors gateway-side checks)
- `lib/install.py` — type-specific install handlers (task/service/script)
- `lib/gateway.py` — HTTP client for `/api/register` (URL), `/api/code-projects/*` (code), `/api/projects-query/*` (free listing), `/api/services/*` (paid listing)
