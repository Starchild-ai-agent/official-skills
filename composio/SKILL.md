---
name: composio
version: 1.2.1
description: "Universal tool gateway via Composio — connect to 1000+ external apps (Gmail, Slack, GitHub, Google Calendar, Notion, etc.) through the Composio Gateway. Use when the user wants to interact with external SaaS services, send emails, manage calendars, access documents, or any third-party app integration."

metadata:
  starchild:
    emoji: "🔌"
    skillKey: composio

user-invocable: true
---

# Composio — External App Integration via Gateway

Composio lets users connect 1000+ external apps (Gmail, Slack, GitHub, Google Calendar, Notion, etc.) to their Starchild agent. All operations go through the **Composio Gateway** (`composio-gateway.fly.dev`), which handles auth and API key management.

## Architecture

```
Agent (Fly 6PN network)
    ↓  HTTP (auto-authenticated by IPv6)
Composio Gateway (composio-gateway.fly.dev)
    ↓  Composio SDK
Composio Cloud → Target API (Gmail, Slack, etc.)
```

- **You never touch the COMPOSIO_API_KEY** — the gateway holds it
- **You never call Composio SDK directly** — use the gateway HTTP API
- **Authentication is automatic** — your Fly 6PN IPv6 resolves to a user_id via the billing DB
- **No env vars needed** — the gateway is always accessible from any agent container

## Gateway Base URL

```
GATEWAY = "http://composio-gateway.flycast"
```

All requests use **plain HTTP over Fly internal network** (flycast). No JWT needed.

## API Reference

### 1. Search Tools (compact)

Find the right tool slug for a task. Returns **compact** tool info — just slug, description, and parameter names. Enough to pick the right tool.

```bash
curl -s -X POST $GATEWAY/internal/search \
  -H "Content-Type: application/json" \
  -d '{"query": "send email via gmail"}'
```

**Response (compact):**
```json
{
  "results": [{"primary_tool_slugs": ["GMAIL_SEND_EMAIL"], "use_case": "send email", ...}],
  "tool_schemas": {
    "GMAIL_SEND_EMAIL": {
      "tool_slug": "GMAIL_SEND_EMAIL",
      "toolkit": "gmail",
      "description": "Send an email...",
      "parameters": ["to", "subject", "body", "cc", "bcc"],
      "required": ["to", "subject", "body"]
    }
  },
  "toolkit_connection_statuses": [...]
}
```

### 2. Get Tool Schema (full)

Get the **complete** parameter definitions for a specific tool — types, descriptions, enums, defaults. Use this **after** search when you need exact parameter formats.

```bash
curl -s -X POST $GATEWAY/internal/tool_schema \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLECALENDAR_EVENTS_LIST"}'
```

**Response:**
```json
{
  "data": {
    "tool_slug": "GOOGLECALENDAR_EVENTS_LIST",
    "description": "Returns events on the specified calendar.",
    "input_parameters": {
      "properties": {
        "timeMin": {"type": "string", "description": "RFC3339 timestamp..."},
        "timeMax": {"type": "string", "description": "RFC3339 timestamp..."},
        "calendarId": {"type": "string", "default": "primary"}
      },
      "required": ["calendarId"]
    }
  },
  "error": null
}
```

### 3. Execute a Tool

Execute a Composio tool. **Key name is `arguments`, not `params`.**

```bash
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GMAIL_SEND_EMAIL", "arguments": {"to": "x@example.com", "subject": "Hi", "body": "Hello!"}}'
```

**On success:**
```json
{"data": {"messages": [...]}, "error": null}
```

**On failure** — includes tool_schema so you can self-correct:
```json
{
  "data": null,
  "error": "Missing required parameter: calendarId",
  "tool_schema": {
    "tool_slug": "GOOGLECALENDAR_EVENTS_LIST",
    "description": "...",
    "input_parameters": {"properties": {...}, "required": [...]}
  }
}
```

### 4. List User's Connections (and confirm OAuth completion)

```bash
# Optional toolkit filter: oauth_completed_active only turns true
# when that toolkit status is ACTIVE.
curl -s "$GATEWAY/internal/connections?toolkit=gmail"
```

Response includes:
- `connections`: current deduplicated connection list
- `oauth_completed_active`: boolean, true only when OAuth completion is observed as `ACTIVE`

Cache invalidation is triggered only after ACTIVE is observed, and it targets the user's instance (`fly-force-instance-id=<user container_id from user_mapping>`), not composio-gateway's own instance.

### 5. Initiate New Connection

```bash
curl -s -X POST $GATEWAY/api/connect \
  -H "Content-Type: application/json" \
  -d '{"toolkit": "gmail"}'
```

Returns `connect_url` for the user to complete OAuth.

### 6. Disconnect

```bash
curl -s -X DELETE $GATEWAY/api/connections/{connection_id}
```

### Browserbase — Hybrid Workflow (Session Management + Playwright CDP)

**Composio's Browserbase tools ONLY manage session lifecycle (open/close/list). They do NOT control web pages.**

To actually operate a browser (navigate, click, fill forms, scrape data), use **Playwright `connect_over_cdp`** to connect to the session's WebSocket URL.

#### Step 1: Create a Browserbase Session via Composio

```bash
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "BROWSERBASE_TOOL_SESSIONS_CREATE", "arguments": {"projectId": "YOUR_PROJECT_ID"}}'
```

Response includes `id` (session_id), `status`, and timestamps.

#### Step 2: Build the CDP WebSocket URL

```python
import os
session_id = "<session_id from step 1>"
api_key = os.environ.get("BROWSERBASE_API_KEY")  # stored in workspace/.env
cdp_url = f"wss://connect.browserbase.com?apiKey={api_key}&sessionId={session_id}"
```

#### Step 3: Control the Browser with Playwright

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp(cdp_url)
    page = await browser.new_page()
    await page.goto("https://example.com")

    # Click, fill, screenshot — full Playwright API
    await page.click("button.submit")
    await page.fill("input[name='email']", "user@test.com")
    await page.screenshot(path="result.png")

    content = await page.content()
```

#### Step 4: Delete the Session (IMPORTANT — stops billing)

```bash
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "BROWSERBASE_TOOL_SESSIONS_DELETE", "arguments": {"id": "YOUR_SESSION_ID"}}'
```

#### Key Concepts

| Aspect | Detail |
|--------|--------|
| **Composio role** | Session lifecycle only — create, list, delete sessions |
| **Playwright role** | Page control — navigate, click, fill, scrape, screenshot |
| **Memory cost** | ~30-50MB locally (Playwright client only); Chromium runs on Browserbase servers |
| **Anti-detection** | Browserbase handles it server-side — fingerprint masking, captcha solving, Cloudflare bypass. Playwright client does nothing special. |
| **Billing** | Per-minute (rounded up). Always delete sessions when done. |

#### Full Example Script (Create → Control → Delete)

```python
#!/usr/bin/env python3
"""Browserbase: create session → control with Playwright → clean up."""
import asyncio, os, requests
from playwright.async_api import async_playwright

GATEWAY = "http://composio-gateway.flycast"
PROJECT_ID = os.environ.get("BROWSERBASE_PROJECT_ID")

async def main():
    # 1. Create session via Composio
    resp = requests.post(f"{GATEWAY}/internal/execute", json={
        "tool": "BROWSERBASE_TOOL_SESSIONS_CREATE",
        "arguments": {"projectId": PROJECT_ID}
    }).json()
    session_id = resp["data"]["id"]
    print(f"Session created: {session_id}")

    try:
        # 2. Connect via CDP
        api_key = os.environ["BROWSERBASE_API_KEY"]
        cdp_url = f"wss://connect.browserbase.com?apiKey={api_key}&sessionId={session_id}"

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            page = await browser.new_page()
            await page.goto("https://example.com")
            title = await page.title()
            print(f"Page title: {title}")
            await browser.close()

    finally:
        # 3. Always delete session to stop billing
        requests.post(f"{GATEWAY}/internal/execute", json={
            "tool": "BROWSERBASE_TOOL_SESSIONS_DELETE",
            "arguments": {"id": session_id}
        })
        print("Session deleted")

asyncio.run(main())
```

#### Available Browserbase Tools via Composio

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `BROWSERBASE_TOOL_SESSIONS_CREATE` | Create a browser session | `projectId` |
| `BROWSERBASE_TOOL_SESSIONS_DELETE` | Delete a session | `id` |
| `BROWSERBASE_TOOL_SESSIONS_GET` | Get session info | `id` |
| `BROWSERBASE_TOOL_SESSIONS_LIST` | List all sessions | (none) |
| `BROWSERBASE_TOOL_SESSIONS_GET_DEBUG_INFO` | Get debug info | `id` |
| `BROWSERBASE_TOOL_SESSIONS_STOP` | Stop a session | `id` |
| `BROWSERBASE_TOOL_CONTEXTS_CREATE` | Create persistent context | `projectId` |
| `BROWSERBASE_TOOL_CONTEXTS_DELETE` | Delete context | `id` |
| `BROWSERBASE_TOOL_CONTEXTS_GET` | Get context info | `id` |
| `BROWSERBASE_TOOL_CONTEXTS_LIST` | List contexts | (none) |
| `BROWSERBASE_TOOL_CONTEXTS_UPDATE` | Update context labels | `id`, `labels` |
| `BROWSERBASE_TOOL_UPLOADS_CREATE` | Upload file to session | `projectId`, file data |
| `BROWSERBASE_TOOL_UPLOADS_GET` | Get upload info | `id` |
| `BROWSERBASE_TOOL_UPLOADS_LIST` | List uploads | (none) |
| `BROWSERBASE_TOOL_UPLOADS_DELETE` | Delete upload | `id` |
| `BROWSERBASE_TOOL_DOWNLOADS_LIST` | List downloads | `sessionId` |
| `BROWSERBASE_TOOL_DOWNLOADS_GET` | Get download | `downloadId` |
| `BROWSERBASE_TOOL_DOWNLOADS_GET_STREAM` | Stream download | `downloadId` |
| `BROWSERBASE_TOOL_KB_GET_KNOWLEDGE` | Get KB article | `id` |

### Browserbase / Browser Tool troubleshooting

If Browserbase is connected but execution fails, check naming mismatches across **connection toolkit** vs **tool slug**:

- Connection may appear as toolkit `browserbase_tool`
- Search may return tool slugs like `BROWSER_TOOL_CREATE_TASK`
- Execute may still reject that slug (`Tool ... not found`) and only resolve legacy slugs under toolkit `browserbase`

Quick diagnosis:

```bash
# 1) Health + active connections
curl -s $GATEWAY/health
curl -s $GATEWAY/internal/connections

# 2) Search browser tool slugs
curl -s -X POST $GATEWAY/internal/search \
  -H "Content-Type: application/json" \
  -d '{"query":"browserbase create task"}'

# 3) Try execute and inspect exact error
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool":"BROWSER_TOOL_CREATE_TASK","arguments":{"task":"open https://example.com"}}'
```

If error says **No active connection found for toolkit 'browserbase'**, gateway should normalize Browserbase aliases server-side (`browser`/`browserbase`/`browserbase_tool`) and normalize execute slug variants (`BROWSERBASE_TOOL_*` ↔ `BROWSER_TOOL_*`) so both old/new clients work with a `browserbase_tool` active connection.

## Optimal Workflow (minimize tool calls)

### Known tool → Direct execute (1 call)

If you already know the tool slug and parameters from previous use or the Common Tools table below, **skip search entirely**:

```bash
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLECALENDAR_EVENTS_LIST", "arguments": {"calendarId": "primary", "timeMin": "2026-04-02T00:00:00+08:00", "timeMax": "2026-04-09T00:00:00+08:00", "singleEvents": true, "timeZone": "Asia/Hong_Kong"}}'
```

### Unknown tool → Search + Schema + Execute (2-3 calls)

1. **Search** (compact) → pick the right tool slug
2. **Get schema** (if param details unclear) → know exact argument format
3. **Execute** → with correct arguments

If execute fails, the error response **includes the full schema** — so you can retry immediately without an extra schema call.

### Wrap in a script for repeat use

For recurring queries, write a one-shot Python script:

```python
#!/usr/bin/env python3
import sys, json, requests
from datetime import datetime, timedelta, timezone

GATEWAY = "http://composio-gateway.flycast"
days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
tz_name = sys.argv[2] if len(sys.argv) > 2 else "UTC"

# ... build timeMin/timeMax ...
resp = requests.post(f"{GATEWAY}/internal/execute", json={
    "tool": "GOOGLECALENDAR_EVENTS_LIST",
    "arguments": {"calendarId": "primary", "timeMin": t_min, "timeMax": t_max,
                   "singleEvents": True, "timeZone": tz_name}
}).json()

# ... format and print ...
```

Then future calls are just: `bash("python3 scripts/calendar_events.py 7 Asia/Hong_Kong")` — **1 tool call**.

## Common Tools Quick Reference (skip search for these)

### 📧 Gmail

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `GMAIL_SEND_EMAIL` | Send email | `to`, `subject`, `body`, `cc`, `bcc` |
| `GMAIL_FETCH_EMAILS` | Fetch emails | `max_results` (int), `label_ids` (list), `q` (Gmail search syntax) |
| `GMAIL_CREATE_EMAIL_DRAFT` | Create draft | `to`, `subject`, `body` |

**Gmail Usage Examples:**

```bash
# Send email
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GMAIL_SEND_EMAIL", "arguments": {"to": "user@example.com", "subject": "Hello", "body": "Hi there!"}}'

# Fetch last 5 emails
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GMAIL_FETCH_EMAILS", "arguments": {"max_results": 5}}'

# Search specific emails (using Gmail search syntax)
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GMAIL_FETCH_EMAILS", "arguments": {"max_results": 10, "q": "from:github.com after:2026/03/01"}}'
```

**Gmail Response Parsing:** Email data is in `data.data.messages[]`, each email has `id`, `snippet`, `payload.headers[]` (From/Subject/Date are in headers, lookup by name).

### 🐦 Twitter

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `TWITTER_CREATION_OF_A_POST` | Create post | `text` (required), `media_media_ids`, `reply_in_reply_to_tweet_id` |
| `TWITTER_POST_DELETE_BY_POST_ID` | Delete post | `id` |
| `TWITTER_POST_LOOKUP_BY_POST_ID` | Get single tweet | `id`, `tweet_fields` |
| `TWITTER_RECENT_SEARCH` | Search last 7 days | `query`, `max_results` (min 10) |
| `TWITTER_USER_LOOKUP_ME` | Get own profile | (no params) |
| `TWITTER_USER_LOOKUP_BY_USERNAME` | Get user profile | `username` |

**Twitter Usage Examples:**

```bash
# Post tweet
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "TWITTER_CREATION_OF_A_POST", "arguments": {"text": "Hello from Composio!"}}'

# Delete tweet
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "TWITTER_POST_DELETE_BY_POST_ID", "arguments": {"id": "2039756730192601584"}}'
```

**Twitter Response Structure:** Post/create returns `data.data.data` (3-level nesting), contains `id`, `text`, `edit_history_tweet_ids`.

#### Twitter — Post with Image (FileUploadable flow)

**Key constraint:** the gateway's `/internal/execute` is a thin wrapper over Composio v2 `actions/{slug}/execute` — it does NOT support `version` pinning or `FileUploadable` synthesis. Twitter media upload tools (`TWITTER_UPLOAD_MEDIA`, `TWITTER_UPLOAD_LARGE_MEDIA`) require **both**, so they MUST be called via the `composio_client` Python SDK directly, not via gateway.

The gateway is intentionally generic — keep all per-tool flows (like this one) here in the skill.

**3-step flow (proven working):**

```python
import hashlib, httpx, json
from pathlib import Path
from composio_client import Composio

# COMPOSIO_API_KEY: read from /data/workspace/composio-gateway/.env
# (gateway owns the key; for skill scripts, source it the same way)
client = Composio(api_key=COMPOSIO_API_KEY)

USER_ID = f"starchild-{user_id}"   # NOTE: hyphen, not underscore
img = Path("output/images/foo.jpg")

# 1. Get presigned S3 upload URL
md5 = hashlib.md5(img.read_bytes()).hexdigest()
presigned = client.files.create_presigned_url(
    filename=img.name, md5=md5, mimetype="image/jpeg",
    tool_slug="TWITTER_UPLOAD_MEDIA", toolkit_slug="twitter",
)
# presigned.type == "new" → file is new, must PUT
# presigned.type == "existing" → cached, skip PUT
if presigned.type == "new":
    httpx.put(presigned.new_presigned_url, content=img.read_bytes(),
              headers={"Content-Type": "image/jpeg"}, timeout=60).raise_for_status()

# 2. Execute upload tool — MUST pass version="20260501_00" (or current latest)
#    media is a FileUploadable dict, NOT base64
upload_resp = client.tools.execute(
    tool_slug="TWITTER_UPLOAD_MEDIA",
    user_id=USER_ID,
    version="20260501_00",
    arguments={
        "media": {"name": img.name, "mimetype": "image/jpeg", "s3key": presigned.key},
        "media_type": "image/jpeg",
        "media_category": "tweet_image",   # or "dm_image", "subtitles"
    },
)
result = upload_resp.model_dump()
assert result["successful"], result["error"]
# Response nesting: data.data.id (NOT data.id, NOT data.media_id_string)
media_id = result["data"]["data"]["id"]

# 3. Create tweet with media_media_ids — this one is fine via gateway too
tweet_resp = client.tools.execute(
    tool_slug="TWITTER_CREATION_OF_A_POST",
    user_id=USER_ID,
    arguments={"text": "your tweet text", "media_media_ids": [str(media_id)]},
)
tweet_id = tweet_resp.model_dump()["data"]["data"]["id"]
url = f"https://x.com/i/web/status/{tweet_id}"
```

**Why this works (debugging notes — don't lose this knowledge):**
- `GET /api/v3/tools/TWITTER_UPLOAD_MEDIA` returns 404 without a version because it lives in toolkit version `20260501_00+`, not the default `00000000_00`.
- `client.tools.execute(version=...)` routes through `/api/v3/tools/execute/{slug}` which IS version-aware.
- Gateway uses v2 `/api/v2/actions/{slug}/execute` for execute — v2 has no version routing, so it can never reach versioned tools. Don't try to "fix" the gateway for this — adding version + FileUploadable would bloat it. Keep it thin.
- The `media` param expects `{name, mimetype, s3key}` (FileUploadable schema), NOT base64. Passing base64 returns: "Input should be a valid dictionary or instance of FileUploadable on parameter `media`".
- File size limit for `TWITTER_UPLOAD_MEDIA` is ~5 MB. For larger files / videos / GIFs, use `TWITTER_UPLOAD_LARGE_MEDIA` (chunked, same flow but additional segment params).

**⚠️ Twitter Limitations & Fallback:**
- `TWITTER_RECENT_SEARCH` only covers **last 7 days**, older tweets won't appear
- `TWITTER_FULL_ARCHIVE_SEARCH` requires Twitter API **Pro access**, regular OAuth App can't use it
- **When fetching user tweet history, prefer platform native tool `twitter_user_tweets`**, not limited to 7 days

### 📅 Google Calendar

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `GOOGLECALENDAR_EVENTS_LIST` | List events | `calendarId` (default: "primary"), `timeMin`, `timeMax` (RFC3339+tz), `singleEvents` (true), `timeZone` |
| `GOOGLECALENDAR_CREATE_EVENT` | Create event | `calendarId`, `summary`, `start`, `end`, `description`, `attendees` |
| `GOOGLECALENDAR_DELETE_EVENT` | Delete event | `calendarId`, `eventId` |

### 🐙 GitHub

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `GITHUB_CREATE_AN_ISSUE` | Create issue | `owner`, `repo`, `title`, `body`, `labels`, `assignees` |
| `GITHUB_LIST_REPOSITORY_ISSUES` | List issues | `owner`, `repo`, `sort`, `state` (open/closed/all), `page`, `per_page` |
| `GITHUB_GET_AN_ISSUE` | Get issue detail | `owner`, `repo`, `issue_number` |
| `GITHUB_CREATE_A_PULL_REQUEST` | Create PR | `owner`, `repo`, `title`, `head`, `base`, `body`, `draft` |
| `GITHUB_LIST_PULL_REQUESTS` | List PRs | `owner`, `repo`, `state`, `sort`, `head`, `base` |
| `GITHUB_MERGE_A_PULL_REQUEST` | Merge PR | `owner`, `repo`, `pull_number`, `commit_title`, `sha` |
| `GITHUB_GET_A_REPOSITORY` | Get repo info | `owner`, `repo` |
| `GITHUB_SEARCH_CODE` | Search code | `q` (GitHub search syntax), `sort`, `order`, `per_page` |
| `GITHUB_GET_REPOSITORY_CONTENT` | Get file content | `owner`, `repo`, `path`, `ref` |

```bash
# Create issue
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GITHUB_CREATE_AN_ISSUE", "arguments": {"owner": "myorg", "repo": "myrepo", "title": "Bug: login fails", "body": "Steps to reproduce..."}}'

# List open issues
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GITHUB_LIST_REPOSITORY_ISSUES", "arguments": {"owner": "myorg", "repo": "myrepo", "state": "open", "per_page": 10}}'
```

### 📝 Notion

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `NOTION_CREATE_NOTION_PAGE` | Create page | `parent_id`, `title`, `markdown`, `icon`, `cover` |
| `NOTION_SEARCH_NOTION_PAGE` | Search pages/DBs | `query`, `filter_value` (page/database), `page_size` |
| `NOTION_QUERY_DATABASE_WITH_FILTER` | Query DB rows | `database_id`, `filter`, `sorts`, `page_size` |
| `NOTION_INSERT_ROW_DATABASE` | Add DB row | `database_id`, `properties` |
| `NOTION_UPDATE_ROW_DATABASE` | Update DB row | `row_id`, `properties`, `icon`, `cover` |
| `NOTION_FETCH_DATABASE` | Get DB schema | `database_id` |
| `NOTION_FETCH_BLOCK_CONTENTS` | Get page content | `block_id` (= page_id) |
| `NOTION_ADD_MULTIPLE_PAGE_CONTENT` | Add blocks | `parent_block_id`, `content_blocks`, `after` |
| `NOTION_UPDATE_PAGE` | Update page props | `page_id`, `properties`, `icon`, `cover`, `archived` |
| `NOTION_DELETE_BLOCK` | Delete/archive block | `block_id` |

```bash
# Search pages
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "NOTION_SEARCH_NOTION_PAGE", "arguments": {"query": "Meeting Notes", "page_size": 5}}'

# Query database with filter
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "NOTION_QUERY_DATABASE_WITH_FILTER", "arguments": {"database_id": "abc123", "filter": {"property": "Status", "select": {"equals": "In Progress"}}, "page_size": 10}}'
```

### 📁 Google Drive

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `GOOGLEDRIVE_CREATE_FILE_FROM_TEXT` | Create file | `file_name`, `text_content`, `mime_type`, `parent_id` |
| `GOOGLEDRIVE_FIND_FILE` | Search files | `q` (Drive search syntax), `fields`, `spaces` |
| `GOOGLEDRIVE_DOWNLOAD_FILE` | Download file | `fileId`, `mime_type` |
| `GOOGLEDRIVE_COPY_FILE` | Copy file | `fileId` |
| `GOOGLEDRIVE_ADD_FILE_SHARING_PREFERENCE` | Share file | `fileId`, `role`, `type`, `emailAddress` |

```bash
# Search files by name
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLEDRIVE_FIND_FILE", "arguments": {"q": "name contains '\''report'\'' and mimeType != '\''application/vnd.google-apps.folder'\''"}}'

# Create text file
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLEDRIVE_CREATE_FILE_FROM_TEXT", "arguments": {"file_name": "notes.txt", "text_content": "Hello World"}}'
```

**Google Drive Search Syntax (`q` param):** `name contains 'keyword'`, `mimeType = 'application/vnd.google-apps.folder'` (folders), `'<folderId>' in parents` (files in folder), `modifiedTime > '2026-01-01'`.

### 📄 Google Docs

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `GOOGLEDOCS_CREATE_DOCUMENT_MARKDOWN` | Create doc from markdown | `title`, `markdown_text` |
| `GOOGLEDOCS_GET_DOCUMENT_PLAINTEXT` | Get doc as text | `document_id`, `include_tables`, `include_headers` |
| `GOOGLEDOCS_GET_DOCUMENT_BY_ID` | Get raw doc object | `id` |

```bash
# Create doc with markdown content
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLEDOCS_CREATE_DOCUMENT_MARKDOWN", "arguments": {"title": "Meeting Notes", "markdown_text": "# Q2 Planning\n\n- Item 1\n- Item 2"}}'

# Read doc as plain text
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLEDOCS_GET_DOCUMENT_PLAINTEXT", "arguments": {"document_id": "1abc...xyz"}}'
```

### 📊 Google Sheets

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `GOOGLESHEETS_CREATE_GOOGLE_SHEET1` | Create spreadsheet | `title` |
| `GOOGLESHEETS_GET_SHEET_NAMES` | List sheets in spreadsheet | `spreadsheet_id`, `exclude_hidden` |
| `GOOGLESHEETS_BATCH_GET` | Read cell values | `spreadsheet_id`, `ranges` (list, A1 notation), `majorDimension`, `valueRenderOption` |
| `GOOGLESHEETS_UPDATE_VALUES_BATCH` | Write cell values | `spreadsheet_id`, `data` (list of {range, values}), `valueInputOption` |
| `GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND` | Append rows | `spreadsheetId`, `range`, `values`, `valueInputOption`, `insertDataOption` |
| `GOOGLESHEETS_SPREADSHEETS_VALUES_BATCH_CLEAR` | Clear ranges | `spreadsheet_id`, `ranges` |
| `GOOGLESHEETS_GET_SPREADSHEET_INFO` | Get full spreadsheet metadata | `spreadsheet_id` |
| `GOOGLESHEETS_UPDATE_SHEET_PROPERTIES` | Update sheet props | `spreadsheet_id`, `sheet_id`, `title`, `index` |

```bash
# Read cells
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLESHEETS_BATCH_GET", "arguments": {"spreadsheet_id": "1abc...xyz", "ranges": ["Sheet1!A1:D10"]}}'

# Write cells
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLESHEETS_UPDATE_VALUES_BATCH", "arguments": {"spreadsheet_id": "1abc...xyz", "valueInputOption": "USER_ENTERED", "data": [{"range": "Sheet1!A1:B2", "values": [["Name", "Score"], ["Alice", 95]]}]}}'

# Append rows
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND", "arguments": {"spreadsheetId": "1abc...xyz", "range": "Sheet1!A:B", "valueInputOption": "USER_ENTERED", "values": [["Bob", 88], ["Charlie", 92]]}}'
```

**⚠️ Google Sheets Notes:**
- `valueInputOption`: `"USER_ENTERED"` (parses formulas/numbers) or `"RAW"` (literal text)
- `ranges` uses **A1 notation**: `"Sheet1!A1:D10"`, `"Sheet1!A:A"` (entire column)
- `BATCH_GET` returns `data.data.valueRanges[].values` (2D array)
- `spreadsheetId` vs `spreadsheet_id`: some tools use camelCase, some snake_case — check schema if unsure

## Important Notes

- **Tool slugs** are UPPERCASE: `GMAIL_SEND_EMAIL`
- **Toolkit slugs** are lowercase: `gmail`, `github`
- **Arguments key**: always use `"arguments"`, never `"params"` — `params` silently gets ignored
- **Time parameters**: use RFC3339 with timezone offset (`2026-04-08T00:00:00+08:00`), not UTC unless intended
- **OAuth tokens are managed by Composio** — auto-refreshed on expiry
- **Response nesting**: Composio execute response is usually `data.data`, but Twitter is `data.data.data` (3 levels). Parse by recursively accessing data.
- **Native tool fallback**: When Composio tools have limitations (e.g., Twitter search only 7 days), prefer platform built-in native tools (e.g., `twitter_user_tweets`)

## Common Issues

### Browserbase connection name mismatch

If `/internal/connections` shows toolkit `browserbase_tool` as ACTIVE, but executing `BROWSER_TOOL_*` returns "No active connection found for toolkit 'browser'", this is a gateway-side toolkit alias mismatch (`browserbase_tool` vs `browser`).

**What to do:**
1. For session management tools (`SESSIONS_*`, `CONTEXTS_*`, `UPLOADS_*`, etc.), the gateway should normalize Browserbase aliases server-side. If it doesn't, try both `BROWSER_TOOL_*` and `BROWSERBASE_TOOL_*` slugs.
2. For **actual browser control** (navigate, click, fill, scrape), **do NOT use Composio execute** — use Playwright `connect_over_cdp` as described in the Browserbase section above. Composio tools only manage sessions, not page interactions.

### Gmail Nested JSON Parsing

Gmail returns complex JSON structure with multiple levels of HTML content. **Do not** try to parse nested strings with `json.loads`. Access directly as dict in Python — gateway already returns parsed JSON.

---
