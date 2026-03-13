---
name: tg-bot-binding
version: 1.0.0
description: "Guide users through the Telegram Bot binding process — creating a bot, adding it to Starchild, verifying ownership, and troubleshooting common issues."

metadata:
  starchild:
    emoji: "🤖"
    skillKey: tg-bot-binding

user-invocable: true
disable-model-invocation: false
---

# Telegram Bot Binding Guide

When the user asks about Telegram Bot binding, setup, connection, verification, or any related topic, provide them with the following guide. **Always respond in the user's language.**

## Overview

Starchild allows you to connect your own Telegram Bot so you can interact with your AI agent directly in Telegram. The binding process involves 3 main steps:

1. Create a Bot on Telegram
2. Add the Bot Token in Starchild Dashboard
3. Verify ownership in Telegram

---

## Step-by-Step Binding Process

### Step 1: Create a Telegram Bot via BotFather

1. Open Telegram and search for **@BotFather** (the official Telegram bot for creating bots).
2. Send `/newbot` to BotFather.
3. Follow the prompts:
   - Enter a **display name** for your bot (e.g., "My Starchild Agent").
   - Enter a **username** for your bot (must end in `bot`, e.g., `my_starchild_bot`).
4. BotFather will reply with your **Bot Token** — a string like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`. **Copy this token and keep it safe.** Do not share it publicly.

### Step 2: Add the Bot Token in Starchild Dashboard

1. Go to the **Starchild Dashboard** (web interface).
2. Click your **avatar** at the **bottom-left corner** of the page.
3. In the **Account Management** popup, find the **Telegram Bot** section.
4. Paste your **Bot Token** and submit.
5. The system will:
   - Verify the token with Telegram's API (calling `getMe`).
   - Generate a **6-digit verification code** (valid for 5 minutes).
   - Set the bot status to **"pending"**.
5. You will see the verification code displayed on the dashboard. **Copy this code.**

### Step 3: Verify Bot Ownership in Telegram

You have two ways to verify:

#### Option A: Deep Link (Recommended)

Click the verification link provided on the dashboard. It will open your bot in Telegram and automatically submit the verification code. The link format is:

```
https://t.me/<your_bot_username>?start=verify_<CODE>
```

#### Option B: Manual Verification

1. Open your bot in Telegram (search for `@<your_bot_username>`).
2. Send `/start` — the bot will prompt you to enter the verification code.
3. Type the **6-digit code** and send it.

### Step 4: Done!

Once verified, the bot status changes to **"active"** briefly, then automatically transitions to **"running"** — meaning your bot is live and ready. You can start chatting with your AI agent through Telegram. Send `/start` to see the welcome message and available commands.

---

## Bot Status Reference

| Status | Meaning |
|--------|---------|
| `pending` | Bot token added, awaiting ownership verification |
| `active` | Ownership verified, transitioning to running |
| `running` | Bot is live and ready to use |
| `deleted` | Bot has been removed by the user |

---

## Troubleshooting

### "Verification code expired"

The verification code is valid for **5 minutes**. If it expires:
- Go back to the Dashboard and click **"Refresh Code"** to generate a new one.
- Then verify again in Telegram with the new code.

### "Too many failed attempts"

After **5 incorrect attempts**, the verification code is invalidated for security:
- Go to the Dashboard, **delete the bot**, and **add it again** to get a fresh code.

### "Bot token is already registered by another user"

Each Bot Token can only be bound to one Starchild account. If you see this error:
- Make sure you're using a **new, unused bot token**.
- If you previously used this token, the old binding may still exist. Create a new bot via @BotFather.

### "You already have an active bot"

Each account can only have **one active bot** at a time:
- To switch bots, first **delete** the current bot from the Dashboard, then add the new one.
- Note: After deleting a bot, there is a **1-hour cooldown** before you can add a new one.

### "Cooldown active — Please wait before adding a new bot"

After deleting a bot, you must wait **1 hour** before adding a new one. The dashboard will show the cooldown expiration time.

### Bot is not responding in Telegram

- Check the bot status on the Dashboard — it should be **"running"**.
- If the status is **"pending"**, complete the verification step.
- Try sending `/start` to the bot.
- If the issue persists, try deleting and re-adding the bot (after the 1-hour cooldown).

---

## Quick Reference

| Action | Where |
|--------|-------|
| Create a new Telegram bot | Telegram → @BotFather → `/newbot` |
| Add bot token | Starchild Dashboard → bottom-left avatar → Account Management → Telegram Bot |
| Verify ownership | Telegram → Your bot → enter verification code |
| Refresh verification code | Starchild Dashboard → Account Management → Telegram Bot → "Refresh Code" |
| Delete bot | Starchild Dashboard → Account Management → Telegram Bot → "Delete Bot" |
| Check bot status | Starchild Dashboard → Account Management → Telegram Bot |

---

## Important Notes

- **Security**: Your Bot Token is encrypted (AES-256) before storage. It is never exposed in API responses.
- **One bot per account**: You can only have one active Telegram bot at a time.
- **Cooldown**: After deleting a bot, wait 1 hour before adding a new one.
- **Rate limits**: Adding a bot and refreshing codes are limited to 3 requests per minute.
- **Verification attempts**: You have 5 attempts to enter the correct code before it's invalidated.
