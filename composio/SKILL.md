---
name: composio
version: 1.0.0
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

## When to Use Composio

Use this skill when the user wants to:
- **Send/read emails** (Gmail, Outlook)
- **Manage calendar** (Google Calendar, Outlook Calendar)
- **Interact with code repos** (GitHub, GitLab)
- **Send messages** (Slack, Discord, Telegram)
- **Manage documents** (Notion, Google Docs)
- **Any external SaaS integration**

**How to know if a user has connections:** Check the system prompt — it includes a `## Composio Connections` section listing active app connections. If the section is absent or empty, the user has no connections yet.

## Gateway Base URL

```
GATEWAY = "http://composio-gateway.flycast"
```

All requests use **plain HTTP over Fly internal network** (flycast). No JWT needed — the gateway identifies the agent by its 6PN IPv6 address.

## API Reference

### 1. List User's Connections

Check what apps the user has already connected.

```bash
curl -s http://composio-gateway.flycast/internal/connections | python3 -m json.tool
```

**Response:**
```json
{
  "user_id": "554",
  "connections": [
    {"id": "ca_xxx", "toolkit": "gmail", "status": "ACTIVE", "created_at": "2025-03-19..."}
  ]
}
```

### 2. Search Tools

Find the right tool slug for a task using natural language.

```bash
curl -s -X POST http://composio-gateway.flycast/internal/search \
  -H "Content-Type: application/json" \
  -d '{"query": "send email via gmail"}' | python3 -m json.tool
```

### 3. Execute a Tool

Execute a Composio tool on behalf of the user.

```bash
curl -s -X POST http://composio-gateway.flycast/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GMAIL_SEND_EMAIL", "arguments": {"to": "x@example.com", "subject": "Hi", "body": "Hello!"}}' \
  | python3 -m json.tool
```

**Response:**
```json
{"data": {"messages": [...]}, "error": null}
```

### 4. Initiate New Connection

When the user wants to connect a new app.

```bash
curl -s -X POST http://composio-gateway.flycast/api/connect \
  -H "Content-Type: application/json" \
  -d '{"toolkit": "gmail"}' | python3 -m json.tool
```

**Response:**
```json
{"connect_url": "https://connect.composio.dev/link/lk_xxx", "connection_id": "ca_xxx"}
```

Give `connect_url` to the user — they click it to complete OAuth.

### 5. Disconnect (Delete) a Connection

```bash
curl -s -X DELETE http://composio-gateway.flycast/api/connections/{connection_id} \
  | python3 -m json.tool
```

**Response:**
```json
{"status": "disconnected", "connection_id": "ca_xxx"}
```

### 6. List Available Toolkits

```bash
curl -s http://composio-gateway.flycast/api/toolkits?limit=200 | python3 -m json.tool
```

## Workflows

### User wants to use an app (e.g. "send an email")

1. **Check system prompt** for `## Composio Connections` section
2. If Gmail is listed → skip to step 5
3. If not connected → call `/api/connect` with `{"toolkit": "gmail"}`
4. Give the user the `connect_url` link. Wait for them to confirm they've authorized.
5. Call `/internal/search` with `{"query": "send email gmail"}` to find the right tool slug
6. Call `/internal/execute` with the tool slug and arguments

### User asks "what apps can I connect?"

1. Call `/api/toolkits` to get the full list
2. Present a curated summary (there are 1000+, so filter to popular ones)

### User asks "what apps do I have connected?"

1. Call `/internal/connections`
2. Show the list with status

## Common Tool Slugs

| App | Tool | Description |
|-----|------|-------------|
| Gmail | `GMAIL_SEND_EMAIL` | Send an email |
| Gmail | `GMAIL_FETCH_EMAILS` | Fetch recent emails |
| Gmail | `GMAIL_GET_EMAIL` | Get a specific email |
| Google Calendar | `GOOGLECALENDAR_EVENTS_LIST` | List events |
| Google Calendar | `GOOGLECALENDAR_CREATE_EVENT` | Create an event |
| GitHub | `GITHUB_CREATE_ISSUE` | Create an issue |
| GitHub | `GITHUB_LIST_REPOS` | List repositories |
| Slack | `SLACK_SEND_MESSAGE` | Send a message |
| Notion | `NOTION_CREATE_PAGE` | Create a page |

When unsure of tool slug, always use `/internal/search` first — it supports semantic search.

## Important Notes

- **Tool slugs** are UPPERCASE: `GMAIL_SEND_EMAIL`, `GITHUB_CREATE_ISSUE`
- **Toolkit slugs** are lowercase: `gmail`, `github`, `slack`
- **Errors from Composio** are returned as `{"data": null, "error": "..."}` — show the error to the user
- **OAuth tokens are managed by Composio** — they auto-refresh expired tokens
- **Data flows through Composio cloud** — be mindful of sensitive data
