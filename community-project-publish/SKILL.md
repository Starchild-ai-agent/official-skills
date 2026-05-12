---
name: community-project-publish
version: 0.3.0
description: Publish runnable code projects (tasks, previews, services, scripts) to the Starchild community-projects repo, or fork someone else's project into your workspace. Use when the user wants to share their built project, install/fork a project from the community catalog, or browse/search published projects.
delivery: script
metadata:
  starchild:
    emoji: 📦
    skillKey: community-project-publish
user-invocable: true
disable-model-invocation: false
---

## What this is

Skill-side client for the **community-projects** ecosystem. Backed by:

- Gateway: `https://community.iamstarchild.com/api/code-projects/*` (X-Internal-Key auth)
- Storage: `Starchild-ai-agent/community-projects` GitHub repo
- Install target: `output/projects/{slug}/`

**Project ≠ Skill.** Skills are workflow instructions (this thing). Projects are runnable code (what this thing publishes/forks).

## Two stages of publishing — Public vs Open Source

Sharing a user's work has **two independent, progressive stages**. They are NOT mutually exclusive — most users naturally want both. Pick the one that matches what the user wants others to be able to *do*:

| Stage | What it does | Tool | Other users get |
|---|---|---|---|
| **① Public** (公开服务) | Exposes the running service at a public URL — others can visit/use it in their browser | `preview(action='publish')` | A live URL: `https://community.iamstarchild.com/{user_id}-{slug}` (slug stays put, content only while publisher's container is up) |
| **② Open Source** (开源代码) | Publishes the source code to a public GitHub repo — others can fork and run their own instance | `publish_project()` (this skill) | A `fork_project()`-able folder under `Starchild-ai-agent/community-projects` — code lives in GitHub, survives any container restart |

### How to read the user's "publish" request

| User says | Stage | Default action |
|---|---|---|
| "公开 / publish my preview / make it accessible / share the link" | ① only | `preview(action='publish')` |
| "开源 / open source / let others fork / share the code" | ② only | `publish_project()` |
| "发布 / publish" without qualifier | likely ① first | `preview(action='publish')`, then offer ② |
| Truly ambiguous | ask once | "想公开访问（别人能打开链接看），还是开源代码（别人能 fork 到自己机器跑）？两个可以一起。" |

### After Stage ① — casually offer Stage ②

After a successful `preview(action='publish')`, mention Stage ② once, don't push:

> 已经公开访问 ✅。要不要顺便把代码也开源出去？这样别人不光能访问，还能 fork 一份跑在自己机器上。

If the user says yes → run `publish_project()` on the same project_dir. If no, drop it.

### Both stages combined (the cleanest publisher workflow)

1. `preview(action='publish', slug=X)` — live URL goes up
2. `publish_project(project_dir=Y)` — code goes to GitHub
3. The PROJECT.md README in step 2 should mention the live URL from step 1, so anyone browsing the GitHub catalog can try the running version before forking

### Don't conflate the two list endpoints

When the user asks "how many community projects are there?", clarify which catalog:
- `projects(action='explore')` lists Stage ① entries (currently 44+ live preview slugs)
- `list_projects()` (this skill) lists Stage ② entries (GitHub-backed code repo)

These are separate datasets; never quote one number to answer a question about the other.

## When to use

| User says | Action |
|---|---|
| "Share / publish / 发布 my project" | `publish_project(project_dir)` |
| "Fork / install / 拉取 a project" | `fork_project(source)` |
| "Browse / list / search projects" | `list_projects(...)` |
| "I have some scattered code, make it a project" | `tidy_project(any_dir)` |
| "Update my published project" | `update_project(project_dir)` |

## Project structure (mandatory)

Every project lives in `output/projects/{slug}/` with this layout:

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

## Project types

| type | What it is | Auto-install behavior on fork |
|---|---|---|
| `task` | Scheduled cron/interval job | `scheduled_task(register, paused=true)` — user activates manually |
| `preview` | Web dashboard / app | `preview(serve)` and return URL |
| `service` | Long-running background process | Show command, ask user to confirm starting in background |
| `script` | One-shot script | Show command for user to run |

## Usage from a bash block

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "/data/workspace/skills/community-project-publish")
from exports import publish_project, fork_project, list_projects

# Publish
result = publish_project("output/projects/my-thing", version_bump="patch")
print(result)
EOF
```

## Function reference

### `publish_project(project_dir, version_bump="patch")`
- `project_dir`: path to the project folder (e.g. `output/projects/my-task`)
- `version_bump`: `patch` | `minor` | `major` — increments the version in `project.yaml`
- Returns: `{"ok": True, "github_url": ..., "version": ..., "commit_sha": ...}` on success

### `fork_project(source, dest_dir=None)`
- `source`: `"user_id/slug"` or `"user_id/slug@version"` (defaults to latest)
- `dest_dir`: where to install (default `output/projects/{slug}/`)
- Returns: `{"ok": True, "installed_at": ..., "type": ..., "next_step": ...}`
- For `task`: also returns `job_id` of the registered (paused) task
- For `preview`: also returns `preview_url`

### `list_projects(type=None, tag=None, user=None, q=None)`
- Filter by type (`task`/`preview`/`service`/`script`), tag, user_id, or text query
- Returns: `{"ok": True, "count": N, "projects": [...]}`

### `update_project(project_dir, version_bump="patch")`
- Alias for `publish_project` — same behavior, semantically clearer when bumping an existing project

### `tidy_project(any_dir, type=None)`
- Inspects an existing folder, infers the project type if not given, and reorganizes into the standard structure
- Creates missing files (PROJECT.md skeleton, .env.example, .gitignore)
- Does NOT publish — you call `publish_project` after reviewing

### `validate_project(project_dir)`
- Pre-flight check before publishing — catches schema errors, missing files, secret patterns
- Returns: `{"ok": True/False, "errors": [...], "warnings": [...]}`

## Behavioral rules

- **Never auto-publish without showing the user the diff first**. After validation, summarize what's about to be pushed (file list, version, type, tags, env_required) and ask for confirmation. Exception: if the user explicitly says "publish without confirmation" or this is a re-publish of a known good project.
- **Never auto-run setup.sh on fork**. Show the command, let user confirm.
- **Always collect env in one batch**. After fork, read the project's `env_required`, diff against `workspace/.env`, and call `request_env_input` ONCE with the missing keys. Don't ask one-by-one.
- **Slug rules**: lowercase alphanumeric + hyphens, 3-50 chars, no leading/trailing hyphen, must match the project folder name.
- **Version rules**: strict semver. Re-publishing same version is rejected. New version must be > current latest.
- **Type immutability**: once published as `task`, can't change to `preview` later. Pick a different slug if you need to change type.

## Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `400 Validation failed: env names not in .env.example` | Listed `MY_KEY` in `env_required` but forgot to add it to `.env.example` | Edit `.env.example` to add the missing key |
| `400 Possible secret detected` | Secret scanner found a real-looking API key in source | Move to env var, ensure `.env.example` value is a placeholder like `your-key-here` |
| `400 Version X must be greater than current latest Y` | Tried to republish same version, or downgrade | Bump version in `project.yaml` (`version_bump="minor"` etc.) |
| `403 Permission denied: only owner can unpublish` | Trying to unpublish someone else's project | Ask the original author |
| Fork installs but task doesn't start | Task is auto-registered as **paused** | Tell user: "Run `scheduled_task(action='activate', job_id={id})` to start" |

## References

- `lib/manifest.py` — project.yaml parser/writer + semver helpers
- `lib/validate.py` — local pre-publish validation (mirrors gateway-side checks)
- `lib/install.py` — type-specific install handlers (task/preview/service/script)
- `lib/gateway.py` — HTTP client for /api/code-projects/* endpoints
