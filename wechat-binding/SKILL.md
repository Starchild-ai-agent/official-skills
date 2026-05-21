---
name: wechat-binding
version: 1.0.1
description: |
  WeChat binding: QR scan, bind, unbind, reconnect, status check.

  Use when setting up or repairing WeChat delivery (e.g. connect WeChat, scan QR, why isn't WeChat pushing, disconnect WeChat).
author: starchild
tags: [wechat, binding, connection, qrcode, ilink]

---

# 📱 WeChat Binding

Connect / reconnect / disconnect the user's WeChat account so the agent can push messages via `send_to_wechat`.

The `wechat` tool stays built-in. This SKILL.md is the reference doc.

## See also
- `config/context/references/messaging-channels.md` — how to actually send messages once bound
- `skills/tg-bot-binding/SKILL.md` — analogous Telegram flow

---

## Typical binding flow

```
qrcode → user scans → qrcode_status(qrcode=...) → connect(bot_token=...)
```

1. **Generate QR:** `wechat(action="qrcode")` — saves an image to workspace, returns `qrcode` (id) + `file_path`.
2. **Show the QR to the user.** On web channel: include the `file_path` so the frontend renders the image. On TG/WeChat channel: send the image via `send_to_telegram` with the `file_path`.
3. **Wait for the user to scan + confirm in WeChat.** Don't auto-poll — let them say "scanned" / "done" first.
4. **Poll for completion:** `wechat(action="qrcode_status", qrcode=<id from step 1>)`. Returns `bot_token` once scan + confirm completes.
5. **Connect:** `wechat(action="connect", bot_token=<from step 4>)`. Optional: `ilink_bot_id`, `ilink_user_id` if the user has multiple WeChat accounts.
6. **Confirm to user:** "WeChat connected. You can now push messages with send_to_wechat."

---

## Actions

| action | required | purpose |
|---|---|---|
| `status` | — | Current WeChat connection state. Use before reconnect, to verify binding. |
| `qrcode` | — | Generate QR code image (saved to workspace). Returns `qrcode` id + `file_path`. |
| `qrcode_status` | `qrcode` | Poll whether user has scanned + confirmed. Returns `bot_token` on success. |
| `connect` | `bot_token` | Complete a NEW WeChat connection (after first-ever QR scan). Optional: `ilink_bot_id`, `ilink_user_id`. |
| `disconnect` | — | Terminate current WeChat session (unlink). |
| `reconnect` | `bot_token` | Re-establish a previously-bound WeChat (token from a fresh QR scan). |

---

## connect vs. reconnect

- **`connect`** — first-time binding. The user has NEVER bound this WeChat before.
- **`reconnect`** — the user was previously connected, the connection dropped (e.g. ilink session expired), and they just scanned a fresh QR.

When in doubt, call `status` first:
- `connected: false` + no prior history → `connect`
- `connected: false` + prior history exists → `reconnect`

---

## Channel-aware QR display

| User channel | How to show the QR |
|---|---|
| **Web** | Include `file_path` in your reply — frontend renders it inline |
| **Telegram** | `send_to_telegram(file_path=<qr_path>, message_type="photo")` |
| **WeChat** | (You can't — they're trying to bind WeChat in the first place. Tell them to open the web app.) |

---

## Critical rules

- **Don't auto-poll** `qrcode_status` after `qrcode`. Wait for user confirmation that they scanned + confirmed in WeChat. Auto-polling spams the upstream API.
- **Each `qrcode` call generates a fresh image.** Don't re-use an old `qrcode` id with a new image — the upstream session is tied to the id.
- **Never paste `bot_token` in chat.** It's a credential. Once you have it from `qrcode_status`, immediately pass it to `connect` / `reconnect` and don't echo it back to the user.
- **`disconnect` is destructive** — confirm with the user before calling it.
