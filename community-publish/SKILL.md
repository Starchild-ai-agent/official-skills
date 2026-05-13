---
name: community-publish
version: 0.6.2
description: Share to the Starchild community in two independent ways — publish a running preview to a public URL, or open-source any project's code to the community GitHub repo. Also handles fork/install/browse.
delivery: script
metadata:
  starchild:
    emoji: 📦
    skillKey: community-publish
user-invocable: true
disable-model-invocation: false
---

## Two independent actions

This skill handles two completely different kinds of sharing. They are NOT the same action and NOT two stages of one action.

| Action | What "share" means here | Audience can | Applies to |
|---|---|---|---|
| `publish_preview(preview_id)` | Make a running preview visitable at `https://community.iamstarchild.com/{user_id}-{slug}` | Open the URL in a browser | type=preview only |
| `open_source(project_dir)` | Push project source to the community GitHub repo | Fork the code and run their own copy | Any type (task, preview, service, script) |

> Preview lifecycle (start / stop / health check) lives in the `preview` tool. This skill only handles the **share** side.

---

## Routing — read user intent carefully

The word "publish" is ambiguous. Default interpretation matters.

| User says | Action | Why |
|---|---|---|
| "publish" / "share" / "make public" / "公开" / "发布" (no qualifier) | `publish_preview(preview_id)` | Default user intent for "publish" is public URL access, not source code |
| "publish the URL" / "share the link" / "let people visit" / "公开访问" | `publish_preview(preview_id)` | Same |
| "open source" / "open-source the code" / "share the code" / "let others fork" / "开源代码" | `open_source(project_dir)` | Explicit code-sharing intent |
| Ambiguous after rereading | Ask one question, don't guess | "Do you want a public URL people can visit, or do you want the code on GitHub for others to fork?" |
| "fork" / "install someone's project" | `fork(source)` | Pull from catalog |
| "browse" / "see what others published" | `list_open_source(...)` | Catalog query |
| "unpublish the URL" / "take down the link" | `unpublish_preview(slug)` | Inverse of publish_preview |
| "remove the open source" / "delete from GitHub" | `remove_open_source(slug)` | Inverse of open_source |
| "list my public URLs" | `list_published_previews()` | User's own preview side |

### Mentioning the other action

After `publish_preview()` succeeds, if the project also has source code the user might want to share:

> Public URL is up. Want to open-source the code as well, so others can fork and run their own copy?

After `open_source()` succeeds, **only if** the project type is `preview` AND there's a running preview:

> Code is open-sourced. The preview is still running — want to publish the live URL too, so visitors can try it without forking?

For `task` / `script` / `service`: don't mention preview publish — there's nothing to expose.

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
   │ In-memory route  │                │ GitHub repo:     │
   │ table (preview-> │                │ Starchild-ai-    │
   │ machine:port)    │                │ agent/community- │
   │                  │                │ projects         │
   │ Lives only while │                │                  │
   │ container is up. │                │ Permanent.       │
   └──────────────────┘                └──────────────────┘
     publish_preview()                    open_source()
```

Same gateway domain, separate API paths, separate datastores. A project can live in either side, both sides, or neither. When both exist, the cross-reference is wired so the frontend renders "View Source" on preview cards and "Visit Live Demo" on code cards.

**Cross-link behavior:** Gateway auto-links at `open_source` time when a matching listing already exists. If the listing is created later (e.g. you `open_source` first, then `publish_preview`), this skill calls `/api/code-projects/link-listing` automatically from both `open_source()` and `publish_preview()` to wire the link in either order. No manual step needed.

---

## `publish_preview()` — public URL

`publish_preview(preview_id, slug="", title="")`

Map a running preview to `https://community.iamstarchild.com/{user_id}-{slug}`.

- `preview_id`: from `preview(action='serve')`. Must be `status=running`.
- `slug`: URL suffix only (lowercase alphanumeric + hyphens, 3-50 chars). User_id prefix is added automatically — pass `'my-app'`, NOT `'1463-my-app'`.
- `title`: display name for the listing.

Returns `{"ok": True, "url": "https://community.iamstarchild.com/{user_id}-{slug}", ...}`.

**Constraints:**
- Max 20 published previews per user (gateway returns 429 over).
- Preview must be running. Stops working when the container goes down (visitors see offline page).
- Slug stays bound to the port — stop and re-serve the preview, the URL stays valid.
- Only works inside the Starchild Fly container (needs `FLY_MACHINE_ID`).

**Companions:**
- `unpublish_preview(slug)` — remove the public URL. Slug accepts full `{user_id}-{suffix}` or just suffix.
- `list_published_previews()` — all currently published preview URLs for this user.

---

## `open_source()` — push code to GitHub

`open_source(project_dir, version_bump="patch")`

Push project source to `community-projects/projects/{type}s/{user_id}/{slug}/{version}/` on GitHub.

- `project_dir`: e.g. `output/projects/my-task`
- `version_bump`: `patch` | `minor` | `major` | `none`
- Returns `{"ok": True, "github_url": ..., "version": ..., "commit_sha": ...}`

**Companions:**
- `fork(source, dest_dir=None)` — install someone else's open-sourced project locally
  - `source`: `"user_id/slug"` or `"user_id/slug@version"`
  - For `task` type: registers as **paused**, returns `next_step` instructions
  - For `preview` type: returns ready-to-serve preview info
- `list_open_source(type=None, tag=None, user=None, q=None)` — browse the GitHub catalog
- `get_open_source(source)` — fetch one project's full metadata
- `remove_open_source(slug)` — delete from GitHub catalog (owner only, removes ALL versions)
- `validate_open_source(project_dir)` — pre-flight check before publishing

### Project structure

Every project under `output/projects/{slug}/`:

```
project.yaml      # metadata (name, version, type, env_required, sc_proxy)
PROJECT.md        # required sections: What / Required env / How to start / Outputs / Troubleshooting
.env.example      # all env vars with placeholder values
.gitignore        # secrets blacklist
src/
  ├── run.py       # for type=task (must start: # -*- task-system: v3 -*-)
  ├── index.html   # for type=preview (or app.py + frontend)
  ├── server.py    # for type=service
  └── main.py      # for type=script
```

| type | What it is | Auto-install behavior on fork | Eligible for `publish_preview()`? |
|---|---|---|---|
| `task` | Scheduled cron/interval job | Registered as **paused**; user activates manually | No |
| `preview` | Web dashboard / app | `preview(action='serve')` and return URL | **Yes** |
| `service` | Long-running background process | Show command, ask user to confirm | No |
| `script` | One-shot script | Show command for user to run | No |

> Only `preview` type has a live URL to expose. The other types are open-source-only.

### Don't conflate the two list functions

`list_published_previews()` returns live URLs (preview side). `list_open_source()` returns open-sourced code (GitHub side). Different datasets — never quote one number to answer a question about the other.

---

## Usage from a bash block

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "/data/workspace/skills/community-publish")
from exports import (
    # Public URL (preview type only)
    publish_preview, unpublish_preview, list_published_previews,
    # Open source code (any project type)
    open_source, remove_open_source, fork,
    list_open_source, get_open_source, validate_open_source,
)

# Publish a running preview to a public URL
print(publish_preview(preview_id="price-dashboard-a3f1", slug="price-dashboard"))

# Open-source a task (no preview involved)
print(open_source("output/projects/my-daily-digest", version_bump="patch"))
EOF
```

---

## Behavioral rules

- **Show the diff before `open_source()`**. After `validate_open_source`, summarize what's about to be pushed (file list, version, type, tags, env_required) and ask for confirmation. Exception: explicit "publish without confirmation" or re-publish of a known good project.
- **Never auto-run setup.sh on fork**. Show the command, let the user confirm.
- **Always collect env in one batch on fork**. Read project's `env_required`, diff against `workspace/.env`, call `request_env_input` ONCE with the missing keys. Don't ask one-by-one.
- **Slug rules**: lowercase alphanumeric + hyphens, 3-50 chars, no leading/trailing hyphen. Skill auto-strips duplicate `{user_id}-` prefix if you accidentally include it.
- **Version rules** (`open_source`): strict semver. Re-publishing same version is rejected. New version must be > current latest.
- **Type immutability** (`open_source`): once published as `task`, can't change to `preview` later. Pick a different slug.
- **URL ≠ code**: a public URL going down (container off) does NOT remove the open-source code, and vice versa. They're independent.

---

## Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `publish_preview`: `Preview not found` | Wrong preview_id, or preview was stopped | Check `/data/previews.json`, restart with `preview(action='serve')` |
| `publish_preview`: `429 Too many published previews` | Hit 20-per-user gateway cap | `unpublish_preview()` something old first |
| `publish_preview`: `FLY_MACHINE_ID not set` | Running locally, not in Starchild container | URL publish only works in the production container |
| `open_source`: `400 Validation failed: env names not in .env.example` | Listed `MY_KEY` in `env_required` but forgot `.env.example` | Add the missing key to `.env.example` |
| `open_source`: `400 Possible secret detected` | Secret scanner found a real-looking API key | Move to env var; `.env.example` value should be `your-key-here` |
| `open_source`: `400 Version X must be greater than current latest Y` | Same-version republish or downgrade | Bump in `project.yaml` (`version_bump="minor"`) |
| `remove_open_source`: `403 Permission denied` | Trying to remove someone else's project | Only the owner can remove |
| Forked task doesn't run | Auto-registered as **paused** | Tell user: `scheduled_task(action='activate', job_id={id})` |

---

## References

- `lib/manifest.py` — project.yaml parser/writer + semver helpers
- `lib/validate.py` — local pre-publish validation (mirrors gateway-side checks)
- `lib/install.py` — type-specific install handlers (task/preview/service/script)
- `lib/gateway.py` — HTTP client for `/api/register` (URL side) and `/api/code-projects/*` (code side)
