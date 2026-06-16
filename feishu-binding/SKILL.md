---
name: feishu-binding
version: 1.0.0
description: |
  Feishu/Lark binding: device flow authorization, connect, disconnect, status check.

  Use when setting up or managing Feishu/Lark connection (e.g. connect Feishu, connect Lark, bind 飞书, check Feishu status, disconnect Lark).
author: starchild
tags: [feishu, lark, binding, connection, device-flow]

metadata:
  starchild:
    emoji: "💬"
    skillKey: feishu-binding

user-invocable: true
disable-model-invocation: false

---

# 📱 Feishu/Lark Binding

Connect / disconnect the user's Feishu (飞书) or Lark account so the agent can chat via the Feishu/Lark app.

The `feishu` tool stays built-in. This SKILL.md is the reference doc.

## See also
- `config/context/references/messaging-channels.md` — how messages are routed across channels
- `skills/wechat-binding/SKILL.md` — analogous WeChat flow
- `skills/tg-bot-binding/SKILL.md` — analogous Telegram flow

---

## Brand selection

| Brand | Region | Domain |
|---|---|---|
| `feishu` | China mainland (中国大陆) | feishu.cn / accounts.feishu.cn |
| `lark` | International | larksuite.com / accounts.larksuite.com |

Ask the user which brand they use. Default to `feishu` if unclear. Chinese-speaking users almost always use `feishu`.

---

## Typical binding flow

```
connect(brand) → user scans QR / opens link → poll(device_code) → done
```

1. **Start device flow:** `feishu(action="connect", brand="feishu")` — returns `verification_uri`, `device_code`, and a QR code image saved to workspace.
2. **Show BOTH options to the user:**
   - **QR code scan:** Display the QR code image inline using the `markdown_image` from the result (e.g. `![Feishu QR Code](feishu_qrcode_xxx.png)`). The user scans it with their Feishu/Lark app.
   - **Direct link:** Show the `verification_url` as a clickable link. The user opens it in their browser, logs in to Feishu/Lark, and confirms.
3. **Wait for the user to confirm.** Don't auto-poll — let them say "done" / "confirmed" / "已确认" / "scanned" first.
4. **Poll for completion:** `feishu(action="poll", device_code=<from step 1>, brand=<same brand>)`.
   - `status: "done"` → binding complete, congratulate the user.
   - `status: "pending"` → ask the user if they've scanned the QR code or opened the link and confirmed.
   - `status: "expired"` → the device flow expired (typically 5 minutes). Start over with `connect`.
5. **Confirm to user:** "Feishu/Lark connected! You can now chat with your agent on Feishu/Lark."

---

## Actions

| action | required params | purpose |
|---|---|---|
| `status` | — | Current Feishu/Lark app state. Use to check if already connected. |
| `connect` | `brand` (optional, default "feishu") | Start device flow. Returns verification URL + device_code. |
| `poll` | `device_code`, `brand` | Check if user has confirmed authorization. Returns status. |
| `disconnect` | — | Unbind Feishu/Lark app (destructive — confirm with user first). |

---

## Channel-aware QR / link display

| User channel | How to show |
|---|---|
| **Web** | Include `file_path` (QR image) in your reply — frontend renders it inline. Also show the link. |
| **Telegram** | `send_to_telegram(file_path=<qr_path>, message_type="photo")` + include the link in the caption |
| **WeChat** | Show the link only (user can't scan a QR inside WeChat for Feishu) |
| **Feishu** | (User is already on Feishu — they don't need to bind. Tell them it's already connected or check `status`.) |

---

## Key differences from WeChat / Telegram

| Aspect | Feishu/Lark | WeChat | Telegram |
|---|---|---|---|
| Auth method | Device flow (URL) | QR code scan | Bot token |
| User action | Open URL + confirm in app | Scan QR + confirm | Create bot via @BotFather |
| Credential | None (device flow handles it) | bot_token (from QR) | bot_token (from BotFather) |
| Brand choice | feishu / lark | N/A | N/A |

---

## Critical rules

- **Don't auto-poll** after `connect`. Wait for user confirmation that they've opened the link and confirmed in Feishu/Lark. Auto-polling wastes API calls.
- **Device flow expires** in ~5 minutes. If `poll` returns `expired`, tell the user and start a new `connect`.
- **`disconnect` is destructive** — confirm with the user before calling it. It will stop the Feishu/Lark gateway instance.
- **Brand matters** — `feishu` and `lark` use different API domains. Using the wrong brand will fail silently or redirect to the wrong login page.
- **One app per user** — a user can only have one Feishu/Lark app at a time. If they want to switch brands, they must `disconnect` first, then `connect` with the new brand.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `connect` returns error | User already has an active app | Call `status` first; if active, ask if they want to `disconnect` and rebind |
| `poll` returns `expired` | User took too long to confirm | Start a new `connect` |
| `poll` returns `pending` repeatedly | User hasn't opened the URL yet | Remind them to open the verification URL |
| User says "I can't find the link" | URL was in a previous message | Re-run `connect` to get a fresh URL |
