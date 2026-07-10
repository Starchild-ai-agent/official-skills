---
name: kanban
version: 1.0.1
description: |
  Stand up a personal Kanban board and wire this agent to it, end to end.
  Serve the board, publish it to a public URL, verify the connection, and hand
  the user their live link. Each user gets their OWN board at their OWN URL —
  self-contained, no shared server, no collisions.

  Use when the user wants to set up / publish / deploy their Kanban board, or
  connect their agent to it. For day-to-day task operations (create/move/list
  tasks) use the nested companion skill `kanban-agent` (in kanban_agent_skill/)
  instead — it is auto-discovered when this skill is installed.
metadata:
  starchild:
    emoji: 📋
    skillKey: kanban
---

## What this is

> **The official agent connector is `kanban_agent_skill/`.** This is THE skill
> to hand to any agent — your own, a teammate's, anyone's — to give it read/write
> access to a Kanban board. Give that folder out, install it, and the agent is
> wired to the board. Everything else in this directory (`server.js`,
> `kanban.html`) is for *hosting* a board; `kanban_agent_skill/` is for *using*
> one.

A self-contained Kanban system that lives in this skill's own folder
(`skills/kanban/`):

- **`kanban.html`** — the board UI (React, single file). `API_BASE` is derived
  from `window.location.pathname`, so the same file works locally and behind any
  published path prefix. No edits needed on publish.
- **`server.js`** — Node server on port **5555**, file-backed (`data.json`),
  exposing the `/ajax/tasks/*` API the UI and the agent both use.
- **`kanban_agent_skill/`** — the **connector skill for agents** (registered as
  `kanban-agent`, auto-discovered when this skill is installed). This is the folder
  an agent — yours or a collaborator's — uses to read/write the board. It
  **auto-resolves** the board URL at runtime (see its SKILL.md), so once you
  publish, the agent is wired up with zero edits and the file never needs updating.

**Deployment model — one board per user.** Each user serves their own
`server.js` and publishes it to `https://community.iamstarchild.com/{USER_ID}-kanban-board`.
Your agent connects to *your* board. There's no shared server and no shared
`data.json`, so two users never collide. (To collaborate on one board, use
`kb_use_board(url)` from the companion skill to point at someone else's URL.)

---

## Setup — publish your board (run these in order)

### 1. Serve the board locally

The board files (`server.js`, `kanban.html`) live in **this skill's own
directory** — normally `skills/kanban`. Serve from there; do NOT copy the files
anywhere else (copies drift). Use the `preview` tool (NOT a raw `node` call — the
preview registry is what `publish_preview` reads):

```
preview(action="serve", title="Kanban Board", dir="skills/kanban", command="node server.js", port=5555)
```

If a preview is already registered (check `/data/previews.json` for a
`kanban`-suffixed id), reuse its id and make sure its `dir` points at
`skills/kanban` — don't serve a duplicate.

### 2. Publish it to a public URL

Load the **community-publish** skill (`read_file` its SKILL.md), then:

```python
publish_preview(preview_id="<from step 1>", slug="kanban-board", title="Kanban Board")
```

This maps the running service to
`https://community.iamstarchild.com/{USER_ID}-kanban-board`. The `USER_ID`
prefix is added automatically — keep the slug exactly `kanban-board` so the
companion skill's auto-detect finds it without extra config.

> Requires running inside the Starchild container (needs `FLY_MACHINE_ID`).
> Publishing only allocates the URL — it does NOT list the board on the public
> gallery. That's a separate, deliberate `list_in_dashboard()` call if wanted.

### 3. Record the published URL in the connector's SKILL.md

After publishing, take the **actual** public URL returned by `publish_preview`
(or read it from `/data/previews.json`) and write it into the connector skill's
doc so the live board link is captured in the skill itself, not just guessed.

Edit `skills/kanban/kanban_agent_skill/SKILL.md` and replace the placeholder
board URL with the real published URL. Specifically, in its **Overview** section
change the auto-detect line:

```
2. `https://community.iamstarchild.com/{USER_ID}-kanban-board` — your published board, if reachable.
```

to the concrete URL you just published, e.g.:

```
2. `https://community.iamstarchild.com/1357-kanban-board` — your published board (live).
```

Use `edit_file` for this, then run `skill_refresh` so the change is reloaded.
This keeps the connector's documentation pointing at the real live board rather
than a placeholder. (The runtime resolver still works either way — this is so
the URL is written down, per request.)

### 4. Verify the connection

Load the companion skill (`read_file skills/kanban/kanban_agent_skill/SKILL.md`) and run:

```python
kb_health()
```

Expect `resolved_via: "community (auto)"`, `ok: true`, and `resolved_url`
matching your `{USER_ID}-kanban-board` URL. If it resolved to `localhost`, the
publish didn't take — recheck step 2.

### 5. Hand the user their link

Give them the live URL from step 2, e.g.
`https://community.iamstarchild.com/{USER_ID}-kanban-board/`.
On Telegram/WeChat, send the full public URL (no preview panel there).

---

## After setup — using the board

Day-to-day task management is the companion skill's job. Its functions
auto-resolve to the board you just published — no arguments needed:

```python
from exports import kb_health, kb_summary, kb_create_task, kb_move_task
kb_summary()   # orient: columns + task counts
```

See `kanban_agent_skill/SKILL.md` for the full function reference.

---

## Collaborate — give a colleague's agent access to your board

Your board is one shared URL. To let a teammate's agent read/write it, they need
the **connector skill only** — not the whole board (they don't run a server).

**Prepare a pre-wired copy** (recommended — no manual config for the recipient).
From the connector skill, run:

```python
kb_export_for_sharing()
```

This stamps a copy of `kanban_agent_skill/` with **your** board URL and zips it to
`output/kanban-agent-share/`. Send that folder/zip. The recipient:

1. Drops `kanban_agent_skill/` into their own `skills/` directory.
2. Their agent runs **skill_refresh** (registers it as `kanban-agent`).
3. Runs `kb_health()` — it auto-connects to **your** board, zero config.

Why not just send the raw folder? A raw copy auto-detects the *recipient's own*
board, not yours — stamping is what wires it to your board. (Manual alternative:
send the folder and have them set `KANBAN_URL=<your board URL>` in their `.env`
or call `kb_use_board(<your board URL>)`.) Remember the API is open: anyone with
the URL has full read/write.

---

## Notes & gotchas

- **Keep the slug `kanban-board`.** The companion skill auto-detects
  `{USER_ID}-kanban-board`. A different slug means you must set the `KANBAN_URL`
  env var so the agent can find it.
- **The board must stay running.** `publish_preview` maps a *running* service;
  if the container restarts, the preview auto-starts from `/data/previews.json`
  (whose entry must point at `/data/workspace/skills/kanban`).
- **No password / open API.** The UI loads directly and the API is unauthenticated.
  Anyone who knows the published URL can read/write the board. Don't publish
  sensitive data unless you're comfortable with that. To lock it down you'd add
  auth on the `/ajax/tasks/*` routes in `server.js`.
- **Local dev without publishing:** run `node server.js` in `skills/kanban/` and open
  `http://localhost:5555` — the companion skill falls back to localhost
  automatically when no community board is reachable.
