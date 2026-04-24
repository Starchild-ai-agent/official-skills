---
name: agent-import
description: Import a migration bundle into Starchild. Downloads from relay, validates, and loads all components using native tools.
version: 1.1.0
author: starchild
tags: [migration, import, onboarding]
---

# Agent Import — Migration Bundle Loader

Download and load a migration bundle into this Starchild agent. The bundle is created by another agent using the `agent-export` skill.

## Quick Start

When user provides a migration code and download token:

```
1. Run the import script to download & extract
2. Review the extracted data with the user
3. Apply each component using native tools
```

## Step 1 — Download & Extract

The user will provide two values from the source agent: a **CODE** (8 chars) and a **DOWNLOAD_TOKEN**.

```bash
python3 skills/agent-import/scripts/download.py <CODE> <DOWNLOAD_TOKEN>
```

The script downloads through the **Fly internal network only** (`sc-agent-migration.fly.internal`). Public download is forbidden by relay policy. If the internal network is unreachable, import fails and must be retried from a Fly machine. The download token authorizes the download; it is single-use and expires with the code (1 hour TTL).

On success the script extracts the bundle to `migration/` and prints a summary of what's included.

## Step 2 — Review Contents

Read and summarize what the bundle contains before applying anything:

```bash
cat migration/manifest.json
cat migration/memory/agent.json 2>/dev/null
cat migration/memory/user.json 2>/dev/null
cat migration/identity/profile.json 2>/dev/null
cat migration/identity/soul.md 2>/dev/null
cat migration/user/settings.json 2>/dev/null
cat migration/tasks/tasks.json 2>/dev/null
cat migration/env/keys.json 2>/dev/null
find migration/files/ -type f 2>/dev/null
```

**Always show the user a summary and ask for confirmation before applying.**

## Step 3 — Apply Components

Apply each component using Starchild native tools. The order matters:

### 3a. User Settings (first — sets timezone/language for everything else)

Read `migration/user/settings.json`, then call:

```
user_settings(action="update", settings={
  "name": "...",
  "what_to_call": "...",
  "timezone": "...",
  "language": "..."
})
```

Only include fields that are present in the JSON.

### 3b. Agent Identity

Read `migration/identity/profile.json`, then call:

```
agent_profile(action="update", profile={
  "name": "...",
  "vibe": "...",
  "emoji": "...",
  "creature": "..."
})
```

### 3c. SOUL.md

If `migration/identity/soul.md` exists, read it and write to `prompt/SOUL.md`.

Merge with existing SOUL.md if it has content. Don't overwrite platform defaults blindly — integrate the personality bits.

### 3d. Memory — Agent

Read `migration/memory/agent.json`, for each entry call:

```
memory(action="add", target="memory", content="<entry>")
```

⚠️ Memory has a 5000 char limit. If the bundle has many entries, prioritize the most useful ones. Check current usage with `memory(action="read")` first.

### 3e. Memory — User

Read `migration/memory/user.json`, for each entry call:

```
memory(action="add", target="user", content="<entry>")
```

⚠️ User memory has a 3000 char limit. Prioritize preferences and corrections.

### 3f. Tasks

Read `migration/tasks/tasks.json`, for each task:

1. `scheduled_task(action="register", title=..., schedule=..., description=..., channels=...)`
2. Write the `run.py` script based on the description
3. Test it: `bash("python3 tasks/{job_id}/run.py")`
4. `scheduled_task(action="activate", job_id=...)`

Tasks need actual implementation — the description is a spec, not runnable code. Use your judgment to build each task's script.

### 3g. Environment Keys

Read `migration/env/keys.json`, then call:

```
request_env_input(env_vars=[...], reason="Migration from <source>")
```

This prompts the user to enter values securely.

### 3h. Files

Copy files from `migration/files/` to the workspace:

```bash
cp -r migration/files/* . 2>/dev/null
```

Review what's being copied and skip anything that would overwrite important existing files.

## Step 4 — Cleanup

```bash
rm -rf migration/ migration-bundle.tar.gz
```

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `401 unauthorized` | Wrong or missing download token | Re-check the token from the source agent output |
| `404 not found` | Code already used or never existed | Ask source agent to re-export |
| `410 expired` | Code older than 1 hour | Ask source agent to re-export |
| `403 internal_only` | Download attempted from non-Fly-internal network | Run import from a Fly machine / internal network |
| `429 rate limited` | Too many failed attempts | Wait 1 hour |
| Invalid tar.gz | Corrupted upload | Re-export from source agent |
| No manifest.json | Invalid bundle structure | Bundle must have manifest.json at root |
