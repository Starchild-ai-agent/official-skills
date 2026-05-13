---
name: community-project-publish
version: 0.4.0
description: Share Starchild projects with the community in two stages — Stage 1 publishes a running preview to a public URL (others can use it in their browser); Stage 2 open-sources the project's code to GitHub (others can fork and run their own instance). Stages are independent and can be combined. Also handles fork/install/browse of others' published projects.
delivery: script
metadata:
  starchild:
    emoji: 📦
    skillKey: community-project-publish
user-invocable: true
disable-model-invocation: false
---

## What this skill does

The single entry point for sharing anything to the Starchild community. Covers both:

| Stage | Function | What others can do |
|---|---|---|
| **① Service URL Publish** | `publish_preview()` | Visit your live preview at `https://community.iamstarchild.com/{user_id}-{slug}` |
| **② Code Open Source** | `publish_project()` | Fork the source code from GitHub and run their own instance |

Both stages are **independent**. Use one, the other, or both. They are NOT mutually exclusive — most publishers eventually want both.

> **Note:** Preview lifecycle (start / stop / health check) lives in the `preview` tool. Anything **publish-related** — for previews or code — lives in this skill.

---

## When to call which function

### "How do I read what the user wants?"

| User says | Stage | Function |
|---|---|---|
| 公开 / 发布 preview / share the link / make accessible | ① | `publish_preview(preview_id)` |
| 开源 / open source / let others fork / share the code | ② | `publish_project(project_dir)` |
| Fork / 拉取 / install someone's project | ② (consume) | `fork_project(source)` |
| Browse / 看看别人发布的 / list community projects | ② (browse) | `list_projects(...)` |
| 取消公开 / unpublish URL | ① undo | `unpublish_preview(slug)` |
| 撤销开源 / take down code | ② undo | `unpublish_project(slug)` |
| 我的公开 preview 列表 | ① | `list_published_previews()` |
| 发布 / publish (no qualifier) | ① first, then offer ② | `publish_preview()` then ask |
| Truly ambiguous | ask once | "想公开访问（别人能打开链接看），还是开源代码（别人能 fork 到自己机器跑）？两个可以一起。" |

### After Stage ① — casually offer Stage ②

After `publish_preview()` succeeds, mention Stage ② once, don't push:

> 已经公开访问 ✅。要不要顺便把代码也开源出去？这样别人不光能访问，还能 fork 一份跑在自己机器上。

If yes → run `publish_project()` on the same project_dir. If no, drop it.

### Combined workflow (the cleanest publisher path)

1. `preview(action='serve', dir=Y, ...)` — run the project locally (preview tool, NOT this skill)
2. `publish_preview(preview_id=X, slug=...)` — Stage ①, live URL goes up
3. `publish_project(project_dir=Y)` — Stage ②, code goes to GitHub
4. The PROJECT.md generated in step 3 should mention the live URL from step 2, so anyone browsing the GitHub catalog can try the running version before forking.

### Don't conflate the two list functions

When the user asks "how many community projects are there?", clarify which catalog:

- `list_published_previews()` — Stage ① entries (the gateway's live-URL registry)
- `list_projects()` — Stage ② entries (GitHub-backed code archive)

Different datasets; never quote one number to answer a question about the other.

---

## Architecture

```
                   community.iamstarchild.com (single gateway domain)
                            │
            ┌───────────────┴───────────────┐
            │                               │
   ┌────────▼─────────┐           ┌─────────▼──────────┐
   │  /api/register   │           │ /api/code-projects │
   │  /api/unregister │           │ /publish, /list,   │
   │  /api/list       │           │ /unpublish, /...   │
   └────────┬─────────┘           └─────────┬──────────┘
            │                               │
   ┌────────▼─────────┐           ┌─────────▼──────────┐
   │ In-memory routing│           │ GitHub repo:       │
   │ table (preview-> │           │ Starchild-ai-agent/│
   │ machine:port)    │           │ community-projects │
   │                  │           │                    │
   │ Lives only while │           │ Permanent storage. │
   │ container is up. │           │ Survives restarts. │
   └──────────────────┘           └────────────────────┘
        Stage ①                          Stage ②
```

Both stages share the same gateway domain but use **separate API paths and separate datastores**. A preview can be in either, both, or neither — they don't reference each other.

---

## Stage ① — Service URL Publish

### `publish_preview(preview_id, slug=None, title=None)`

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

### `unpublish_preview(slug)`

Remove a preview's public URL. Slug can be either the full `{user_id}-{suffix}` or just the suffix.

### `list_published_previews()`

Return all of the current user's published preview URLs.

---

## Stage ② — Code Open Source

### `publish_project(project_dir, version_bump="patch")`

Push project source to GitHub at `community-projects/projects/{type}s/{user_id}/{slug}/{version}/`.

- `project_dir`: e.g. `output/projects/my-task`
- `version_bump`: `patch` | `minor` | `major`
- Returns `{"ok": True, "github_url": ..., "version": ..., "commit_sha": ...}`

### `update_project(project_dir, version_bump="patch")`

Alias for `publish_project` — same behavior, semantically clearer for re-publishing.

### `fork_project(source, dest_dir=None)`

Install someone else's project locally.

- `source`: `"user_id/slug"` or `"user_id/slug@version"`
- Returns metadata + `next_step` hint
- For `task` type: also returns `job_id` of the registered (paused) task
- For `preview` type: also returns `preview_url`

### `list_projects(type=None, tag=None, user=None, q=None)`

Filter the GitHub-backed catalog. Returns `{"ok": True, "count": N, "projects": [...]}`.

### `get_project(source)`

Fetch one project's full metadata.

### `unpublish_project(slug)`

Remove your project from the GitHub catalog (only the owner can).

### `validate_project(project_dir)`

Pre-flight check — runs the same validation as the gateway. Returns `{"ok": True/False, "errors": [...], "warnings": [...]}`.

---

## Project structure (Stage ② only)

Every project in `output/projects/{slug}/`:

```
project.yaml      # metadata (name, version, type, env_required, sc_proxy)
PROJECT.md        # required 4 sections: What / Required env / How to start / Outputs / Troubleshooting
.env.example      # all env vars with placeholder values
.gitignore        # secrets blacklist
src/
  ├── run.py       # for type=task (must start: # -*- task-system: v3 -*-)
  ├── index.html   # for type=preview (or app.py + frontend)
  ├── server.py    # for type=service
  └── main.py      # for type=script
```

| type | What it is | Auto-install behavior on fork |
|---|---|---|
| `task` | Scheduled cron/interval job | Registered as **paused**; user activates manually |
| `preview` | Web dashboard / app | `preview(action='serve')` and return URL |
| `service` | Long-running background process | Show command, ask user to confirm |
| `script` | One-shot script | Show command for user to run |

---

## Usage from a bash block

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "/data/workspace/skills/community-project-publish")
from exports import (
    # Stage 1: service URL
    publish_preview, unpublish_preview, list_published_previews,
    # Stage 2: code open source
    publish_project, update_project, fork_project,
    list_projects, get_project, unpublish_project, validate_project,
)

# Stage 1 example
print(publish_preview(preview_id="price-dashboard-a3f1", slug="price-dashboard"))

# Stage 2 example
print(publish_project("output/projects/my-thing", version_bump="patch"))
EOF
```

---

## Behavioral rules

- **Never auto-publish without showing the user the diff first** (Stage ②). After `validate_project`, summarize what's about to be pushed (file list, version, type, tags, env_required) and ask for confirmation. Exception: explicit `publish without confirmation` or re-publish of a known good project.
- **Never auto-run setup.sh on fork**. Show the command, let the user confirm.
- **Always collect env in one batch on fork**. Read project's `env_required`, diff against `workspace/.env`, call `request_env_input` ONCE with the missing keys. Don't ask one-by-one.
- **Slug rules**: lowercase alphanumeric + hyphens, 3-50 chars, no leading/trailing hyphen. Skill auto-strips duplicate `{user_id}-` prefix if you accidentally include it.
- **Version rules** (Stage ②): strict semver. Re-publishing same version is rejected. New version must be > current latest.
- **Type immutability** (Stage ②): once published as `task`, can't change to `preview` later. Pick a different slug.
- **Stage ① ≠ Stage ②**: a published preview URL going down (container off) does NOT remove the open-source code, and vice versa. They're independent.

---

## Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Stage ①: `Preview not found` | Wrong preview_id, or preview was stopped | Check `/data/previews.json`, restart with `preview(action='serve')` |
| Stage ①: `429 Too many published previews` | Hit 20-per-user gateway cap | `unpublish_preview()` something old first |
| Stage ①: `FLY_MACHINE_ID not set` | Running locally, not in Starchild container | Service URL publish only works in the production container |
| Stage ②: `400 Validation failed: env names not in .env.example` | Listed `MY_KEY` in `env_required` but forgot `.env.example` | Add the missing key to `.env.example` |
| Stage ②: `400 Possible secret detected` | Secret scanner found a real-looking API key | Move to env var; `.env.example` value should be `your-key-here` |
| Stage ②: `400 Version X must be greater than current latest Y` | Same-version republish or downgrade | Bump in `project.yaml` (`version_bump="minor"`) |
| Stage ②: `403 Permission denied: only owner can unpublish` | Trying to unpublish someone else's project | Ask the original author |
| Forked task doesn't run | Auto-registered as **paused** | Tell user: `scheduled_task(action='activate', job_id={id})` |

---

## References

- `lib/manifest.py` — project.yaml parser/writer + semver helpers
- `lib/validate.py` — local pre-publish validation (mirrors gateway-side checks)
- `lib/install.py` — type-specific install handlers (task/preview/service/script)
- `lib/gateway.py` — HTTP client for both `/api/register` (Stage ①) and `/api/code-projects/*` (Stage ②)
