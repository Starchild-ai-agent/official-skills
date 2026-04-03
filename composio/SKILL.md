---
name: composio
version: 1.2.0
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

### 4. List User's Connections

```bash
curl -s $GATEWAY/internal/connections
```

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

### Gmail Nested JSON Parsing

Gmail returns complex JSON structure with multiple levels of HTML content. **Do not** try to parse nested strings with `json.loads`. Access directly as dict in Python — gateway already returns parsed JSON.

---
