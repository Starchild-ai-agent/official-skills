---
name: preview-dev
version: 1.0.0
description: "Frontend & fullstack development with live preview. Use when the user wants to build a web page, frontend app, fullstack project, or any web UI — including React, Vue, Vite, static HTML, Express, FastAPI, or any framework that produces a browser-viewable result. Also use when the user wants to deploy, publish, or share a preview to the public internet (community publish)."

metadata:
  starchild:
    emoji: "🖥️"
    skillKey: preview-dev

user-invocable: true
disable-model-invocation: false
---

# Preview Dev — Frontend & Fullstack Development

Write code, start previews, let users see results in the Browser panel. No templates, no placeholders — working code only. **Always respond in user's language.**

Tools: `read_file`, `write_file`, `edit_file`, `bash`, `preview_serve`, `preview_stop`, `preview_check`

## ⛔ Mandatory Checklist

**After `preview_serve`:**
1. Check `health_check.ok` — if false, fix before telling user it's ready
2. Common issues: `directory_listing` (need command+port), `blank_page` (JS error), `connection_failed` (wrong port)

**On user-reported problems:** diagnose (`preview_check` + `read_file`) → fix in place (`edit_file`) → restart same preview → verify

**Find preview IDs:** `bash("cat /data/previews.json")` — never guess IDs

**NEVER:** create new files when old ones have bugs | guess preview IDs | tell user "ready" when health_check fails | call API via bash when a tool exists

## Error Recovery

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| White/blank page | JS error, CDN blocked | Read HTML, fix script tag |
| Directory listing | Missing command+port | Add command+port or fix dir |
| 404 on resources | Absolute paths | Change `/path` to `./path` |
| CORS error | Direct external API call | Add backend proxy endpoint |
| Connection failed | Wrong port/command | Check command matches code |

**Flow:** Diagnose → `edit_file` fix → `preview_stop` + `preview_serve` (same dir/port) → verify health_check

## Project Type Reference

| Type | command | port | Example |
|------|---------|------|---------|
| Static HTML/CSS/JS | _(omit)_ | _(omit)_ | `preview_serve(title="X", dir="my-dir")` |
| Vite/React/Vue | `npm install && npm run dev` | 5173 | |
| Python backend | `pip install ... && python main.py` | from code | |
| Node backend | `npm install && node server.js` | from code | |
| Fullstack | build frontend + start backend | backend port | See below |
| Streamlit | `pip install streamlit && streamlit run app.py --server.port 8501 --server.address 127.0.0.1` | 8501 | |

## Fullstack Projects

**Single port:** Backend serves both API and frontend static files.

1. Build frontend: `cd frontend && npm install && npm run build`
2. Configure backend to serve `frontend/dist/` as static files
3. Start backend only

**FastAPI:** `app.mount("/", StaticFiles(directory="../frontend/dist", html=True))`
**Express:** `app.use(express.static(...))` + SPA fallback `app.get('*', ...)`

## ⚠️ Common Issues

**Relative paths required** — preview runs at `/preview/{id}/`, absolute paths bypass proxy:
- ❌ `"/static/app.js"`, `fetch('/api/users')` | ✅ `"./static/app.js"`, `fetch('api/users')`
- Vite: `base: './'` | CRA: `"homepage": "."`

**Third-party API calls** — browsers block cross-origin from iframes. Use backend proxy endpoint, never call external APIs from frontend JS. Backend scripts can't import `core/` — use `requests` + proxy env vars.

**API polling costs credits** — if code uses `setInterval`, notify user. Prefer manual refresh buttons.

**Never tell users to access localhost** — say "Check the Browser panel"

## Rules

1. **Fix in-place**, don't create new projects
2. **Detect duplicate versions** (`app-v2`, `app-v3`) — list and ask before cleanup
3. **Same port on restart** — don't change port numbers
4. **port MUST match code** — read code to confirm listen port
5. **Listen on 127.0.0.1** — not 0.0.0.0
6. **Backend projects need command + port** — only pure static can omit
7. **No placeholders** — every line must work
8. **Verify after starting** — check health_check before declaring ready
9. **One preview, one port** — fullstack = single port serves everything
10. **Max 3 command-based previews** — oldest auto-stopped when exceeded
11. **SPA needs fallback** — custom backends need catch-all route returning index.html

## Community Publish

Share a working preview publicly via `community_publish`.

**Workflow:**
1. `preview_serve` → verify `health_check.ok` is true
2. Generate slug from title: "Macro Dashboard" → `macro-dashboard`
3. `community_publish(preview_id="xxx", slug="macro-dashboard")`
4. URL: `https://community.iamstarchild.com/{user_id}-{slug}/`

| Tool | Purpose |
|------|---------|
| `community_publish(preview_id, slug?, title?)` | Publish to public URL |
| `community_unpublish(slug)` | Remove public URL |
| `community_list()` | List published previews |

**Notes:** preview must be running | one port = one slug | max 10 published | no auth on public URL | re-publish same slug to update | URL valid while container runs
