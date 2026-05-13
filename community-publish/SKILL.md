---
name: community-publish
version: 0.5.1
description: Publish to the Starchild community — open-source code to GitHub and/or expose a running preview at a public URL. Use either independently, or combine for the full project share. Also handles fork/install/browse of others' work.
delivery: script
metadata:
  starchild:
    emoji: 📦
    skillKey: community-publish
user-invocable: true
disable-model-invocation: false
---

## What this skill does

Two independent publish actions:

| Action | What it does | What others can do |
|---|---|---|
| `publish_project(project_dir)` | Pushes source code to the community GitHub repo | Fork the code and run their own copy |
| `publish_preview(preview_id)` | Maps a running preview to `https://community.iamstarchild.com/{user_id}-{slug}` | Visit the live URL in their browser |

These are **independent**. Use one, the other, or both. They share a gateway domain but otherwise don't reference each other — each has its own datastore, lifetime, and undo path.

> **Note:** Preview lifecycle (start / stop / health check) lives in the `preview` tool. This skill only handles the **publish** side.

---

## Two typical scenarios

### Scenario A — Pure code share

User wants others to be able to fork and run code. There may not be any running service; the code is the artifact.

**Flow:** organize the project dir → `publish_project()`. Done.

Examples: a scheduled task, a one-off analysis script, a CLI tool, an SDK wrapper, a library.

### Scenario B — Project share (comprehensive)

User has a running thing (preview, web app, dashboard) AND wants to make it both **usable** (anyone can open the URL) and **forkable** (anyone can run their own).

**Recommended flow** — also the smoothest user-facing path:

1. `preview(action='serve', dir=Y, ...)` — get the preview running (preview tool, not this skill)
2. `publish_preview(preview_id=X, slug=...)` — live URL goes up
3. `publish_project(project_dir=Y)` — code goes to GitHub, with PROJECT.md mentioning the live URL

The two actions amplify each other — visitors try the live version first, then fork if they like it. But step 2 and step 3 are still independent: skip either one, the other still works.

---

## Routing — what the user is asking for

| User intent | Action |
|---|---|
| Open source / let others fork / share the code | `publish_project(project_dir)` |
| Share the link / make accessible / publish preview | `publish_preview(preview_id)` |
| Publish (no qualifier) | Ask: do they want others to visit a live URL, or fork and run the code themselves? Both can be done together. |
| Fork / install someone's project | `fork_project(source)` |
| Browse what others published | `list_projects(...)` |
| Unpublish the public URL | `unpublish_preview(slug)` |
| Take down open-sourced code | `unpublish_project(slug)` |
| List my own published preview URLs | `list_published_previews()` |

### When to mention the other action

After `publish_preview()` succeeds, if the project also has source code worth sharing:

> Live URL is up ✅. Want to open-source the code too, so others can fork and run their own copy?

After `publish_project()` succeeds, **only if** the project type is `preview` AND there's a running preview:

> Code is open-sourced ✅. The preview is still running — want to publish the live URL too, so visitors can try it without forking?

For pure-code project types (`task` / `script` / `service`): no need to mention preview publish — there's nothing to expose.

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
   │  /api/list       │                │ /unpublish, /... │
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
     publish_preview()                    publish_project()
```

Same gateway domain, separate API paths, separate datastores. A project can live in either side, both sides, or neither — they don't reference each other.

---

## `publish_project()` — open source code

`publish_project(project_dir, version_bump="patch")`

Push project source to GitHub at `community-projects/projects/{type}s/{user_id}/{slug}/{version}/`.

- `project_dir`: e.g. `output/projects/my-task`
- `version_bump`: `patch` | `minor` | `major`
- Returns `{"ok": True, "github_url": ..., "version": ..., "commit_sha": ...}`

**Other actions:**

- `update_project(project_dir, version_bump)` — alias for re-publishing
- `fork_project(source, dest_dir=None)` — install someone else's project locally
  - `source`: `"user_id/slug"` or `"user_id/slug@version"`
  - For `task` type: returns `job_id` of the registered (paused) task
  - For `preview` type: returns `preview_url`
- `list_projects(type=None, tag=None, user=None, q=None)` — filter the GitHub catalog
- `get_project(source)` — fetch one project's full metadata
- `unpublish_project(slug)` — remove from GitHub catalog (owner only)
- `validate_project(project_dir)` — pre-flight check (mirrors gateway validation)

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

---

## `publish_preview()` — expose live URL

`publish_preview(preview_id, slug=None, title=None)`

Map a running preview to a public URL.

- `preview_id`: from `preview(action='serve')` output. Must be `status=running`.
- `slug`: URL suffix only (lowercase alphanumeric + hyphens, 3-50 chars). User_id prefix is added automatically — pass `'my-app'`, NOT `'1463-my-app'`.
- `title`: display name for the listing.

Returns `{"ok": True, "url": "https://community.iamstarchild.com/{user_id}-{slug}", ...}`.

**Constraints:**
- Max 20 published previews per user (gateway rate-limit, returns 429 over).
- Preview must be running. Stops working when the container goes down (visitors see offline page).
- Slug stays bound to the port — you can stop and re-serve the preview, the URL stays valid.
- Only works inside the Starchild Fly container (needs `FLY_MACHINE_ID`).

**Other actions:**
- `unpublish_preview(slug)` — remove the public URL. Slug accepts full `{user_id}-{suffix}` or just suffix.
- `list_published_previews()` — all currently published preview URLs for this user.

### Don't conflate the two list functions

`list_published_previews()` returns live URLs (preview side). `list_projects()` returns open-sourced code (project side). Different datasets — never quote one number to answer a question about the other.

---

## Usage from a bash block

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "/data/workspace/skills/community-publish")
from exports import (
    # Open source code (works on any project type)
    publish_project, update_project, fork_project,
    list_projects, get_project, unpublish_project, validate_project,
    # Live URL (preview type only)
    publish_preview, unpublish_preview, list_published_previews,
)

# Open source a task (no preview involved)
print(publish_project("output/projects/my-daily-digest", version_bump="patch"))

# Expose a running preview's URL
print(publish_preview(preview_id="price-dashboard-a3f1", slug="price-dashboard"))
EOF
```

---

## Behavioral rules

- **Never auto-publish without showing the user the diff first** (open source). After `validate_project`, summarize what's about to be pushed (file list, version, type, tags, env_required) and ask for confirmation. Exception: explicit `publish without confirmation` or re-publish of a known good project.
- **Never auto-run setup.sh on fork**. Show the command, let the user confirm.
- **Always collect env in one batch on fork**. Read project's `env_required`, diff against `workspace/.env`, call `request_env_input` ONCE with the missing keys. Don't ask one-by-one.
- **Slug rules**: lowercase alphanumeric + hyphens, 3-50 chars, no leading/trailing hyphen. Skill auto-strips duplicate `{user_id}-` prefix if you accidentally include it.
- **Version rules** (open source): strict semver. Re-publishing same version is rejected. New version must be > current latest.
- **Type immutability** (open source): once published as `task`, can't change to `preview` later. Pick a different slug.
- **URL ≠ code**: a published preview URL going down (container off) does NOT remove the open-source code, and vice versa. They're independent.

---

## Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `publish_preview`: `Preview not found` | Wrong preview_id, or preview was stopped | Check `/data/previews.json`, restart with `preview(action='serve')` |
| `publish_preview`: `429 Too many published previews` | Hit 20-per-user gateway cap | `unpublish_preview()` something old first |
| `publish_preview`: `FLY_MACHINE_ID not set` | Running locally, not in Starchild container | URL publish only works in the production container |
| `publish_project`: `400 Validation failed: env names not in .env.example` | Listed `MY_KEY` in `env_required` but forgot `.env.example` | Add the missing key to `.env.example` |
| `publish_project`: `400 Possible secret detected` | Secret scanner found a real-looking API key | Move to env var; `.env.example` value should be `your-key-here` |
| `publish_project`: `400 Version X must be greater than current latest Y` | Same-version republish or downgrade | Bump in `project.yaml` (`version_bump="minor"`) |
| `publish_project`: `403 Permission denied: only owner can unpublish` | Trying to unpublish someone else's project | Ask the original author |
| Forked task doesn't run | Auto-registered as **paused** | Tell user: `scheduled_task(action='activate', job_id={id})` |

---

## References

- `lib/manifest.py` — project.yaml parser/writer + semver helpers
- `lib/validate.py` — local pre-publish validation (mirrors gateway-side checks)
- `lib/install.py` — type-specific install handlers (task/preview/service/script)
- `lib/gateway.py` — HTTP client for `/api/register` (URL side) and `/api/code-projects/*` (code side)
