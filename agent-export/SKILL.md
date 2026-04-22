---
name: agent-export
description: Export agent data into a Starchild migration bundle. For use by ANY agent (OpenClaw, Claude Code, Cursor, etc.) to migrate into Starchild.
version: 1.0.0
author: starchild
tags: [migration, export, onboarding]
---

# Agent Export — Migration Bundle Creator

Create a structured migration bundle from your current agent data and upload it to the Starchild migration relay. The receiving Starchild agent uses the `agent-import` skill to load it.

## Migration Bundle Format

The bundle is a **tar.gz** archive with this structure:

```
migration/
  manifest.json           # required — metadata
  memory/
    agent.json            # agent's own notes & knowledge
    user.json             # what the agent knows about the user
  identity/
    profile.json          # agent name, personality
    soul.md               # behavioral guidelines (free-form markdown)
  user/
    settings.json         # user preferences (name, timezone, language)
  tasks/
    tasks.json            # scheduled/recurring tasks
  env/
    keys.json             # environment variable names needed (NO values)
  files/                  # arbitrary files to carry over
    ...
```

All files are optional except `manifest.json`.

---

## File Specifications

### manifest.json (required)

```json
{
  "version": "1.0",
  "source": "openclaw",
  "created_at": "2025-07-13T10:00:00Z",
  "description": "Migration from OpenClaw agent"
}
```

- `source`: identifier of the originating agent/platform (free text)
- `version`: always `"1.0"` for now

### memory/agent.json

Agent's accumulated knowledge — things the agent learned about the environment, tool quirks, API notes, workflows, conventions.

```json
{
  "entries": [
    "Coinglass funding rate values are already in percent; do not multiply by 100.",
    "User's Hyperliquid account uses cross-margin by default.",
    "For Fly.io deploys, extract FLY_TOKEN via sed from .env in project dir."
  ]
}
```

Each entry: 1-3 sentences, one concern per entry. Think "what would I need to remember next session?"

### memory/user.json

What the agent knows about the user — their role, preferences, communication style, interests.

```json
{
  "entries": [
    "Prefers concise responses under 25 lines, direct conclusions, no hedges.",
    "Technical background in full-stack dev and crypto trading.",
    "Located in Argentina, primary language is Chinese."
  ]
}
```

### identity/profile.json

```json
{
  "name": "MyAgent",
  "vibe": "professional, concise, opinionated",
  "emoji": "🤖",
  "creature": "robot"
}
```

All fields optional. `vibe` is a short personality description.

### identity/soul.md

Free-form markdown describing how the agent should behave. Keep it under 50 lines. Example:

```markdown
# Behavior
- Be concise, skip filler phrases
- Have opinions, back them with data
- For trading: present analysis, not financial advice
```

### user/settings.json

```json
{
  "name": "Alice",
  "what_to_call": "Boss",
  "timezone": "Asia/Shanghai",
  "language": "zh-CN"
}
```

- `timezone`: IANA format (e.g., `America/New_York`, `Asia/Tokyo`)
- `language`: BCP-47 code (`en`, `zh-CN`, `ja`, etc.)

### tasks/tasks.json

```json
{
  "tasks": [
    {
      "title": "BTC Price Alert",
      "schedule": "every 30 minutes",
      "description": "Check BTC price, alert if > $100k or < $80k",
      "channels": ["web", "tg"]
    },
    {
      "title": "Daily Market Summary",
      "schedule": "0 1 * * *",
      "description": "Summarize crypto market at 9am Shanghai time"
    }
  ]
}
```

- `schedule`: cron expression (UTC), interval (`every 5 minutes`), or delay (`in 2 hours`)
- `channels`: optional, subset of `["web", "tg", "wechat"]`

### env/keys.json

List environment variable **names** the agent needs (values are entered separately for security).

```json
{
  "keys": [
    {"key": "OPENAI_API_KEY", "label": "OpenAI API Key", "required": true},
    {"key": "TELEGRAM_BOT_TOKEN", "label": "Telegram Bot Token", "required": false}
  ]
}
```

### files/

Put any arbitrary files here. They'll be copied to the Starchild workspace as-is, preserving subdirectory structure. Use for custom scripts, configs, dashboards, etc.

---

## Export Workflow

### Step 1 — Gather Data

Collect information from your current agent. Map your data to the formats above:

- **Chat history / memory** → extract key facts into `memory/agent.json` and `memory/user.json`
- **System prompt / persona** → transform into `identity/profile.json` + `identity/soul.md`
- **User preferences** → `user/settings.json`
- **Recurring automations** → `tasks/tasks.json`
- **API keys needed** → `env/keys.json` (names only!)
- **Custom files** → copy into `files/`

### Step 2 — Build the Bundle

```bash
# Create directory structure
mkdir -p migration/{memory,identity,user,tasks,env,files}

# Write your JSON files (examples — replace with real data)
cat > migration/manifest.json << 'EOF'
{"version": "1.0", "source": "my-agent", "created_at": "2025-07-13T10:00:00Z"}
EOF

# ... write other files ...

# Pack into tar.gz
cd migration && tar czf ../migration-bundle.tar.gz . && cd ..
```

### Step 3 — Upload to Relay

```bash
RESPONSE=$(curl -s -X POST https://sc-agent-migration.fly.dev/paste \
  -H "Content-Type: application/octet-stream" \
  --data-binary @migration-bundle.tar.gz)

CODE=$(echo "$RESPONSE" | grep -o '"code":"[^"]*"' | cut -d'"' -f4)
TOKEN=$(echo "$RESPONSE" | grep -o '"download_token":"[^"]*"' | cut -d'"' -f4)

echo "Migration code:   $CODE"
echo "Download token:   $TOKEN"
```

Give **both values** to the user — they need the code AND the token to import in Starchild.

⚠️ The code expires in **1 hour** and is **single-use** (deleted after first successful download).
⚠️ The token is the only authorization for download — do not lose it.

---

## Tips for Other Agents

- **Don't overthink it.** Even just `manifest.json` + `memory/user.json` with 5 entries is useful.
- **Summarize, don't dump.** Convert raw chat history into concise memory entries.
- **Timezone matters.** Get the user's timezone right — it affects all scheduled tasks.
- **No secrets in the bundle.** API keys go in `env/keys.json` as names only.
- **Test your tar.gz** — `tar tzf migration-bundle.tar.gz` should show paths starting with `./`.
