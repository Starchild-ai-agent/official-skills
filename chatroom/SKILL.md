---
name: chatroom
version: 0.2.0
description: DEPRECATED — renamed to workroom. This stub exists only so legacy `--skill chatroom` installs land on a clear redirect. Install `workroom` instead.
delivery: script
author: starchild
tags: [deprecated, redirect, workroom]
user-invocable: false
---

# chatroom — DEPRECATED, renamed to workroom

This skill has been **renamed to `workroom`**. Nothing else changed —
same scripts, same commands, same `chatroom-<room_id>` agent thread
prefix on the wire. Only the skill identity moved.

## What you should do

```bash
# Install the new skill:
npx skills add Starchild-ai-agent/official-skills --skill workroom

# Then call it the same way you used to call chatroom, just with the
# new name:
python3 skills/workroom/scripts/create.py "my room"
python3 skills/workroom/scripts/join.py <invite_code>
# …etc.
```

If you came here from a Starchild agent that's still running on
sc-chatroom: the server keeps `/skills/chatroom.tar.gz` aliased to the
workroom bundle, so `workroom self-update` will Just Work — but the
local `/data/workspace/skills/chatroom/` directory you may have on disk
is stale and should be removed.

## Why the rename

"Workroom" became the product-facing name; "chatroom" stays only as the
internal sc-chatroom service name + the `chatroom-<room_id>` thread_id
prefix (kept stable so deployed AKM keys and agent session memory keep
resolving).

## Common mistakes this stub catches

- `from skills.chatroom.exports import …` — there is no `exports` module
  and never was; the skill exposes no Python API surface. Use the CLI
  scripts via subprocess.
- Calling `python3 skills/chatroom/scripts/<command>.py` — if you got
  this file from a fresh install, the `scripts/` directory is gone on
  purpose. Switch to `skills/workroom/scripts/<command>.py`.

See `workroom/SKILL.md` in this same registry for the full command
reference, smoke test, and changelog.
