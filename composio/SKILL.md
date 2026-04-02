---
name: composio
version: 1.1.0
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
| `GMAIL_SEND_EMAIL` | 发邮件 | `to`, `subject`, `body`, `cc`, `bcc` |
| `GMAIL_FETCH_EMAILS` | 查邮件 | `max_results` (int), `label_ids` (list), `q` (Gmail search syntax) |
| `GMAIL_CREATE_EMAIL_DRAFT` | 创建草稿 | `to`, `subject`, `body` |

**Gmail 使用示例：**

```bash
# 发送邮件
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GMAIL_SEND_EMAIL", "arguments": {"to": "user@example.com", "subject": "Hello", "body": "Hi there!"}}'

# 查最近 5 封邮件
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GMAIL_FETCH_EMAILS", "arguments": {"max_results": 5}}'

# 搜索特定邮件（使用 Gmail 搜索语法）
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GMAIL_FETCH_EMAILS", "arguments": {"max_results": 10, "q": "from:github.com after:2026/03/01"}}'
```

**Gmail 响应解析：** 邮件数据在 `data.data.messages[]` 中，每封邮件有 `id`, `snippet`, `payload.headers[]`（From/Subject/Date 在 headers 里按 name 查找）。

### 🐦 Twitter

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `TWITTER_CREATION_OF_A_POST` | 发推 | `text` (必选), `media_media_ids`, `reply_in_reply_to_tweet_id` |
| `TWITTER_POST_DELETE_BY_POST_ID` | 删推 | `id` |
| `TWITTER_POST_LOOKUP_BY_POST_ID` | 查单条推文 | `id`, `tweet_fields` |
| `TWITTER_RECENT_SEARCH` | 搜索最近 7 天推文 | `query`, `max_results` (min 10) |
| `TWITTER_USER_LOOKUP_ME` | 获取自己的资料 | (无参数) |
| `TWITTER_USER_LOOKUP_BY_USERNAME` | 查用户资料 | `username` |

**Twitter 使用示例：**

```bash
# 发推文
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "TWITTER_CREATION_OF_A_POST", "arguments": {"text": "Hello from Composio!"}}'

# 删推文
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "TWITTER_POST_DELETE_BY_POST_ID", "arguments": {"id": "2039756730192601584"}}'
```

**Twitter 响应结构：** 发推/查推返回 `data.data.data` (三层嵌套)，内含 `id`, `text`, `edit_history_tweet_ids`。

**⚠️ Twitter 限制与 Fallback：**
- `TWITTER_RECENT_SEARCH` 只覆盖**最近 7 天**，超过就搜不到
- `TWITTER_FULL_ARCHIVE_SEARCH` 需要 Twitter API **Pro 权限**，普通 OAuth App 用不了
- **获取用户历史推文时，优先使用平台 native tool `twitter_user_tweets`**，不受 7 天限制

### 📅 Google Calendar

| Tool Slug | Purpose | Key Arguments |
|-----------|---------|---------------|
| `GOOGLECALENDAR_EVENTS_LIST` | 查事件 | `calendarId` (default: "primary"), `timeMin`, `timeMax` (RFC3339+tz), `singleEvents` (true), `timeZone` |
| `GOOGLECALENDAR_CREATE_EVENT` | 创建事件 | `calendarId`, `summary`, `start`, `end`, `description`, `attendees` |
| `GOOGLECALENDAR_DELETE_EVENT` | 删除事件 | `calendarId`, `eventId` |

### 其他 App

| App | Tool Slug | Key Arguments |
|-----|-----------|---------------|
| GitHub | `GITHUB_CREATE_ISSUE` | `owner`, `repo`, `title`, `body` |
| Slack | `SLACK_SEND_MESSAGE` | `channel`, `text` |
| Notion | `NOTION_CREATE_PAGE` | `parent_id`, `title`, `content` |

## Important Notes

- **Tool slugs** are UPPERCASE: `GMAIL_SEND_EMAIL`
- **Toolkit slugs** are lowercase: `gmail`, `github`
- **Arguments key**: always use `"arguments"`, never `"params"` — `params` silently gets ignored
- **Time parameters**: use RFC3339 with timezone offset (`2026-04-08T00:00:00+08:00`), not UTC unless intended
- **OAuth tokens are managed by Composio** — auto-refreshed on expiry
- **响应嵌套**: Composio execute 的响应一般是 `data.data`，但 Twitter 是 `data.data.data`（三层）。解析时注意递归取 data。
- **Native tool fallback**: 当 Composio 的工具有限制（如 Twitter 搜索只 7 天），优先用平台自带的 native tool（如 `twitter_user_tweets`）

## Common Issues

### Gmail 嵌套 JSON 解析
Gmail 返回的 JSON 结构复杂，包含多层 HTML 内容。**不要**尝试用 `json.loads` 解析嵌套字符串。直接在 Python 中用 dict 访问即可，gateway 已返回 parsed JSON。

### Twitter OAuth 权限不足
如果遇到 `"you must use keys and tokens from a Twitter developer App that is attached to a Project"` 错误，说明该 API endpoint 需要更高权限（如 Pro/Enterprise）。改用替代工具或 native tool。

### execute 返回 "No active connection found"
Gateway 已修复此问题（使用 REST API v2 + connectedAccountId）。如果仍出现，检查 `/internal/connections` 确认该 toolkit 有 ACTIVE 状态的连接。

---
