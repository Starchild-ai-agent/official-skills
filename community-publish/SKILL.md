---
name: community-publish
version: 0.11.0
description: Share to the Starchild community in three independent ways — publish a running service to a public URL, list it on the public Project Dashboard for discovery, or open-source the project's code to the community GitHub repo.
delivery: script
metadata:
  starchild:
    emoji: 📦
    skillKey: community-publish
user-invocable: true
disable-model-invocation: false
---

## Three independent actions

This skill handles three completely different kinds of sharing. They are NOT stages of one flow and NOT mutually exclusive — a project can be in any combination.

| Action | What "share" means here | Audience can | Applies to |
|---|---|---|---|
| `publish_preview(preview_id)` | Allocate a public URL `https://community.iamstarchild.com/{user_id}-{slug}` | Open the URL **if they know it** — point-to-point access | Any running service |
| `list_in_dashboard(slug)` | Show the listing on the public Project Dashboard | **Discover and browse** to it from the gallery | A previously-published preview |
| `open_source(project_dir)` | Push project source to the community GitHub repo | Fork the code and run their own copy | Any project (task, service, script) |

**Critical: do NOT auto-list when publishing.** `publish_preview()` only allocates the URL. Listing is a separate, deliberate user decision. If the user just says "publish my preview" / "公开" without mentioning the dashboard, only call `publish_preview()`. After it succeeds, you may mention that `list_in_dashboard()` exists if they want others to discover it.

> Service lifecycle (start / stop / health check) lives in the `preview` tool. This skill only handles the **share** side.

---

## Project types — three only

| type | What it is | Eligible for `publish_preview()`? |
|---|---|---|
| `task` | Scheduled cron/interval job | No (no HTTP port) |
| `service` | Long-running HTTP service (dashboard, API, page) | **Yes** — any service can be exposed at a public URL |
| `script` | One-shot script | No (no HTTP port) |

Note: there is no `preview` type. If you encounter older docs mentioning it, treat as `service`.

---

## Routing — read user intent carefully

The word "publish" is ambiguous. Default interpretation matters.

| User says | Action | Why |
|---|---|---|
| "publish" / "share" / "make public" / "公开" / "发布" (no qualifier) | `publish_preview(preview_id)` | Default user intent for "publish" is public URL access, not source code, not dashboard listing |
| "publish the URL" / "share the link" / "let people visit" / "公开访问" | `publish_preview(preview_id)` | Same |
| "list on the dashboard" / "上架" / "show on community" / "make discoverable" / "let people find this" / "发到广场" | `list_in_dashboard(slug)` | Explicit dashboard-listing intent |
| "publish AND list" / "publish and put on dashboard" / "发布并上架" | `publish_preview()` THEN `list_in_dashboard()` | Two separate calls, in that order — preview must exist before listing |
| "remove from dashboard" / "下架" / "unlist" / "hide from gallery" | `unlist_from_dashboard(slug)` | Inverse of list_in_dashboard |
| "is this listed?" / "在 dashboard 上吗" / "show my listing status" | `get_listing_status(slug)` | Read-only status check |
| "open source" / "open-source the code" / "share the code" / "let others fork" / "开源代码" | `open_source(project_dir)` | Explicit code-sharing intent |
| Ambiguous after rereading | Ask one question, don't guess | "Do you want it (a) just shareable by URL, (b) also discoverable on the public dashboard, or (c) also have the code open-sourced on GitHub?" |
| "fork" / "install someone's project" | `fork(source)` | Pull from catalog |
| "browse" / "see what others published" | `list_open_source(...)` | Catalog query |
| "unpublish the URL" / "take down the link" | `unpublish_preview(slug)` | Inverse of publish_preview |
| "remove the open source" / "delete from GitHub" | `remove_open_source(slug)` | Inverse of open_source |
| "list my public URLs" | `list_published_previews()` | User's own preview side |

---

## Cross-link via `publisher:` binding

When the same project has BOTH a public URL AND open-sourced code, you want them paired so the frontend renders "View Source" on the listing card and "Visit Live Demo" on the code card. This skill drives that pairing through one explicit binding in project.yaml — no name guessing, no fuzzy matching, no follow-up dialogues.

### How to declare the binding

Add a `publisher:` block to `project.yaml`:

```yaml
name: my-app                      # GitHub catalog slug + default for both sides
type: service
version: 1.0.0
publisher:
  code_slug: my-app               # OPTIONAL — defaults to manifest.name
  public_slug: my-app-pub         # OPTIONAL — URL suffix; defaults to code_slug
```

Both fields are optional. If omitted, both default to `manifest.name`. Set them only when you want different slugs on each side (e.g. short URL `dash` for code `my-detailed-dashboard`).

### Either side can be published first

The gateway holds a pending entry until the second side arrives. **No ordering requirement**, no manual link step.

| Order | What happens |
|---|---|
| `open_source` first → `publish_preview` second | open_source records pending entry; publish_preview consumes it and links |
| `publish_preview` first → `open_source` second | publish_preview records pending entry (needs `publisher_code_slug` arg); open_source consumes it and links |
| Both at once / rename later | Re-run either side with updated binding; gateway re-links |

### Calling publish_preview with binding

When publishing the URL FIRST and the code will follow:

```python
publish_preview(
    preview_id="my-app-a3f1",
    slug="my-app-pub",
    publisher_code_slug="my-app",   # so future open_source(my-app) auto-links here
)
```

If `publisher_code_slug` is omitted, no pending entry is recorded — the code side will need to declare `publisher.public_slug` itself in project.yaml to wire the link.

### Return value

Both functions return a `publisher` field showing what binding was sent and a `hint` describing the cross-link state:

```python
{"ok": True, "url": "...", "publisher": {"code_slug": "my-app"},
 "hint": "Cross-link binding declared. If that code is already open-sourced, it's now linked. If not, the link is pending..."}
```

You don't need to react to the hint — it's informational. The gateway handles wiring automatically.

### Manual repair (rare)

If a pairing was wired wrong (e.g. after a rename or a slug typo), use:

```python
link_to_listing(listing_slug="2004-my-app-pub", code_slug="my-app")
```

This skips the binding flow and writes the link directly. Don't use this for normal publishing — fix project.yaml's `publisher:` block instead so the binding survives future republishes.

---

## Architecture

```
                community.iamstarchild.com (single gateway domain)
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
   ┌────────▼─────────┐                ┌────────▼─────────┐
   │  /api/register   │                │/api/code-projects│
   │  /api/unregister │                │ /publish, /list, │
   │  /api/list       │                │ /unpublish, ...  │
   └────────┬─────────┘                └────────┬─────────┘
            │                                   │
   ┌────────▼─────────┐                ┌────────▼─────────┐
   │ DB: route table  │                │ GitHub:          │
   │ + project_       │                │ Starchild-ai-    │
   │   listings       │                │ agent/community- │
   │ + publisher_     │                │ projects         │
   │   pending_links  │                │                  │
   │                  │                │ Permanent.       │
   │ Service stays up │                │                  │
   │ as long as your  │                │                  │
   │ container runs.  │                │                  │
   └──────────────────┘                └──────────────────┘
     publish_preview()                    open_source()
```

`publisher_pending_links` is the cross-link table. Either side writes a pending row, the other side consumes it on arrival.

---

## `publish_preview()` — public URL

`publish_preview(preview_id, slug="", title="", publisher_code_slug="")`

Map a running service to `https://community.iamstarchild.com/{user_id}-{slug}`.

- `preview_id`: from `preview(action='serve')`. Must be `status=running`.
- `slug`: URL suffix only (lowercase alphanumeric + hyphens, 3-50 chars). User_id prefix is added automatically — pass `'my-app'`, NOT `'1463-my-app'`.
- `title`: display name for the listing.
- `publisher_code_slug`: optional cross-link binding to a code project's slug. Sets up the pending entry so the eventual `open_source()` call auto-links.

Returns `{"ok": True, "url": "...", "publisher": {...}, "hint": "..."}`.

**Constraints:**
- Max 20 published previews per user (gateway returns 429 over).
- Service must be running. Stops working when the container goes down (visitors see offline page).
- Slug stays bound to the port — stop and re-serve, the URL stays valid.
- Only works inside the Starchild Fly container (needs `FLY_MACHINE_ID`).

**Companions:**
- `unpublish_preview(slug)` — remove the public URL. Slug accepts full `{user_id}-{suffix}` or just suffix.
- `list_published_previews()` — all currently published preview URLs for this user.

---

## `list_in_dashboard()` — show on Project Dashboard

`list_in_dashboard(slug, name=None, description="", cover_url=None, tags=None)`

Make a published preview discoverable in the public Project Dashboard at `https://community.iamstarchild.com/projects`. Without this, the preview URL works but is invisible to anyone who doesn't already know it.

- `slug`: the **full** slug returned by `publish_preview()` (i.e. `{user_id}-{suffix}`). The gateway's ownership check uses this exact value.
- `name`: dashboard card display name. Defaults to `slug`.
- `description`: ≤500 chars.
- `cover_url`: must be on `storage.googleapis.com`, `image.thum.io`, or `api.microlink.io`. Other domains rejected with 400. If omitted, the gateway captures a screenshot asynchronously.
- `tags`: ≤5 tags, ≤20 chars each.

Returns `{"ok": True, "listing": {...}, "url": "...", "dashboard_url": "..."}`.

**Constraints:**
- Requires `publish_preview()` to have run first for the same slug — returns 404 with a clear error otherwise.
- Idempotent: calling again with different name/tags updates the existing listing.
- Listings created via `publish_preview()` start as **private** (not on dashboard) — `list_in_dashboard()` is the ONLY way to make them discoverable.

**Companions:**
- `unlist_from_dashboard(slug)` — remove from dashboard, keep URL alive.
- `get_listing_status(slug)` — read-only check: returns `{ok, exists, is_public, listing}`. Note: only public listings are observable through this — if the gateway returns 404, the listing is either nonexistent OR private (no way to distinguish).

---

## `open_source()` — push code to GitHub

`open_source(project_dir, version_bump="patch", message="")`

Push project source to `community-projects/projects/{type}s/{user_id}/{slug}/{version}/` on GitHub.

- `project_dir`: e.g. `output/projects/my-task`
- `version_bump`: `patch` | `minor` | `major` | `none`
- `message`: commit message body describing what this version changed.
  **You (the agent) should always compose this** based on the actual code
  changes you made in this session — never leave it blank if you know
  what changed, never ask the user to write it. Aim for one to three short
  lines. Don't list every file; describe the user-visible change. If the
  user explicitly said "just publish", use a one-line summary like "Initial
  publish" or "Re-publish without changes".
- Returns `{"ok": True, "github_url": ..., "version": ..., "publisher": {...}, "hint": "..."}`

**Commit message style** — write like a normal git commit body:

  ✅ "Add WebSocket reconnect on dropped connections; refactor prompt builder for shared state."
  ✅ "Fix funding-rate sign convention; add unit test for negative-funding path."
  ❌ "Updated 3 files" (uninformative)
  ❌ "Modified src/index.html, src/main.py, project.yaml" (lists files instead of intent)
  ❌ "User asked to publish" (describes the request, not the change)

**Companions:**
- `fork(source, dest_dir=None)` — install someone else's open-sourced project locally
  - `source`: `"user_id/slug"` (always pulls current state — older snapshots live in GitHub commit history)
  - For `task` type: registers as **paused**, returns `next_step` instructions
  - For `service` type: returns ready-to-serve info
- `list_open_source(type=None, tag=None, user=None, q=None)` — browse the GitHub catalog
- `get_open_source(source)` — fetch one project's full metadata
- `remove_open_source(slug)` — delete project directory from GitHub catalog (owner only). Git history of the deletion + previous commits is preserved in the repo's commit log.
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

### Don't conflate the two list functions

`list_published_previews()` returns live URLs (preview side). `list_open_source()` returns open-sourced code (GitHub side). Different datasets — never quote one number to answer a question about the other.

---

## Usage from a bash block

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "/data/workspace/skills/community-publish")
from exports import (
    # Public URL
    publish_preview, unpublish_preview, list_published_previews,
    # Open source code
    open_source, remove_open_source, fork,
    list_open_source, get_open_source, validate_open_source,
    # Manual repair (rare)
    link_to_listing,
)

# Cross-linked publish: declare publisher in project.yaml first, then both
# sides auto-pair regardless of order.
print(publish_preview(preview_id="my-app-a3f1", slug="my-app",
                      publisher_code_slug="my-app"))
print(open_source("output/projects/my-app", version_bump="patch"))
EOF
```

---

## Behavioral rules

- **Show the diff before `open_source()`**. After `validate_open_source`, summarize what's about to be pushed (file list, version, type, tags, env_required) and ask for confirmation. Exception: explicit "publish without confirmation" or re-publish of a known good project.
- **Never auto-run setup.sh on fork**. Show the command, let the user confirm.
- **Always collect env in one batch on fork**. Read project's `env_required`, diff against `workspace/.env`, call `request_env_input` ONCE with the missing keys. Don't ask one-by-one.
- **Slug rules**: lowercase alphanumeric + hyphens, 3-50 chars, no leading/trailing hyphen. Skill auto-strips duplicate `{user_id}-` prefix if you accidentally include it.
- **Version rules** (`open_source`): strict semver. Re-publishing same version is rejected. New version must be > current latest.
- **Type immutability** (`open_source`): once published as `task`, can't change to `service` later. Pick a different slug.
- **URL ≠ code**: a public URL going down (container off) does NOT remove the open-source code, and vice versa. They're independent.
- **Don't manually call `link_to_listing()` in the normal flow**. The `publisher:` binding handles cross-linking. Manual link is only for repair.

---

## Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `publish_preview`: `Preview not found` | Wrong preview_id, or service was stopped | Check `/data/previews.json`, restart with `preview(action='serve')` |
| `publish_preview`: `429 Too many published previews` | Hit 20-per-user gateway cap | `unpublish_preview()` something old first |
| `publish_preview`: `FLY_MACHINE_ID not set` | Running locally, not in Starchild container | URL publish only works in the production container |
| `open_source`: `400 Validation failed: env names not in .env.example` | Listed `MY_KEY` in `env_required` but forgot `.env.example` | Add the missing key to `.env.example` |
| `open_source`: `400 Possible secret detected` | Secret scanner found a real-looking API key | Move to env var; `.env.example` value should be `your-key-here` |

| `open_source`: `400 Type cannot change after publish` | Trying to switch task ↔ service ↔ script | Pick a different slug |
| `remove_open_source`: `403 Permission denied` | Trying to remove someone else's project | Only the owner can remove |
| Cross-link not appearing on frontend | Binding mismatch between sides | Check both sides' slugs match the `publisher:` block; or use `link_to_listing` to repair |
| Forked task doesn't run | Auto-registered as **paused** | Tell user: `scheduled_task(action='activate', job_id={id})` |

---

## References

- `lib/manifest.py` — project.yaml parser/writer + semver helpers
- `lib/validate.py` — local pre-publish validation (mirrors gateway-side checks)
- `lib/install.py` — type-specific install handlers (task/service/script)
- `lib/gateway.py` — HTTP client for `/api/register` (URL side) and `/api/code-projects/*` (code side)
