---
name: tg-bot-binding
version: 1.0.0
description: "Guide users through the Telegram Bot binding process — creating a bot, adding it to Starchild, verifying ownership, and troubleshooting."

metadata:
  starchild:
    emoji: "🤖"
    skillKey: tg-bot-binding

user-invocable: true
disable-model-invocation: false
---

# Telegram Bot Binding

Connect your own Telegram Bot to interact with your Starchild agent via Telegram.

## Setup Process

### 1. Create Bot
Telegram → @BotFather → `/newbot` → name it → get **Bot Token** (e.g. `123456789:ABCdef...`). Keep it safe.

### 2. Add Token
Starchild Dashboard → bottom-left avatar → Account Management → Telegram Bot → paste token → submit.

System verifies via `getMe`, generates a **6-digit code** (5 min expiry), sets status to "pending".

### 3. Verify Ownership

**Option A (recommended):** Click the deep link on dashboard → opens bot in Telegram, auto-submits code.

**Option B:** Open bot in Telegram → `/start` → enter 6-digit code manually.

### 4. Done
Status changes: pending → active → **running**. Chat with your agent via Telegram.

## Status Reference

| Status | Meaning |
|--------|---------|
| `pending` | Awaiting verification |
| `active` | Verified, transitioning |
| `running` | Live and ready |
| `deleted` | Removed by user |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Code expired | Dashboard → "Refresh Code" (5 min validity) |
| Too many failed attempts | After 5 wrong codes → delete bot, re-add for fresh code |
| Token already registered | Each token = one account. Create new bot via @BotFather |
| Already have active bot | Delete current bot first (1 account = 1 bot) |
| Cooldown active | Wait 1 hour after deleting before adding new bot |
| Bot not responding | Check status is "running". Try `/start`. Re-add if persists |

## Notes

- **Security:** Token encrypted (AES-256), never exposed in API responses
- **Limits:** 1 bot per account | 1-hour cooldown after deletion | 3 req/min for add/refresh | 5 verification attempts
