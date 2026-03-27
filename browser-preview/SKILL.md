---
name: browser-preview
version: 1.0.0
description: "Browser preview panel knowledge — the iframe-based Browser tab in the right panel. Use when the user mentions browser, preview, tab disappeared, page broken, blank screen, white screen, 白屏, 页面挂了, tab 不见了, preview not loading, or asks about running services."

metadata:
  starchild:
    emoji: "🌐"
    skillKey: browser-preview

user-invocable: true
disable-model-invocation: false
---

# Browser Preview

What happens **after** `preview_serve` — how users see previews in the Browser panel.

## Architecture

Right panel has **Workspace** and **Browser** tabs. Browser renders preview URLs in an iframe. Each `preview_serve` creates one Browser tab. URL: `https://<host>/preview/{id}/`.

**Reverse proxy flow:** User's Browser → `https://<host>/preview/{id}/path` → `127.0.0.1:{port}/path`

## Critical Rules

**NEVER tell users to access localhost** — they can't reach it. Always say "Check the Browser panel" or give the `/preview/{id}/` URL. `curl localhost:{port}` is for your server-side diagnostics only.

**Relative paths required** — previews served under `/preview/{id}/`, absolute paths bypass proxy:

| ❌ Broken | ✅ Fixed |
|-----------|---------|
| `"/static/app.js"` | `"./static/app.js"` |
| `fetch('/api/users')` | `fetch('api/users')` |
| `url('/fonts/x.woff')` | `url('./fonts/x.woff')` |

Check ALL places: HTML src/href, JS fetch/imports, CSS url(), string literals, framework config (publicPath, base).

**Don't browse filesystem to debug** — only sources of truth: `/data/previews.json` (registry), `/data/preview_history.json` (history), and port checks via curl.

## Diagnosing Browser Issues

### Step 1: Read registry
```bash
cat /data/previews.json 2>/dev/null || echo "NO_REGISTRY"
```
⚠️ Absolute path `/data/previews.json` (not in workspace).

### Step 2: Branch

**Registry has entries →** verify each port:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:{port}
```
- Port responds: service running. Tell user to click ⋮ menu → RUNNING SERVICES to reopen. If ⋮ empty, recreate: `preview_stop(id)` + `preview_serve(same params)`.
- Port dead: process crashed. Recreate same way.

**Registry empty →** check history:
```bash
cat /data/preview_history.json 2>/dev/null || echo "NO_HISTORY"
```
History persists across restarts. List entries, ask which to restart.

**No history →** scan workspace:
```bash
find /data/workspace -maxdepth 2 \( -name "package.json" -o -name "index.html" -o -name "app.py" -o -name "main.py" \) -not -path "*/node_modules/*" -not -path "*/skills/*" -not -path "*/.git/*" 2>/dev/null
```
List discovered projects, ask which to preview. **Don't just say "no services" and stop.**

## Quick Reference

| User says | Action |
|-----------|--------|
| "tab disappeared" | Check registry → verify port → reopen or recreate |
| "blank page" / "白屏" | Check port; if alive, check absolute paths; if dead, recreate |
| "not updating" | Suggest refresh button or recreate preview |
| "⋮ menu empty" | `preview_stop` + `preview_serve` to force re-register |
| "where's my project" | Read `/data/preview_history.json`, list entries |
| "JS/CSS 404" | Fix absolute paths → relative, restart preview |

## Limitations

Cannot directly open/close/refresh Browser tabs or read iframe content. Tell user the manual action, or recreate preview if manual action doesn't work.
