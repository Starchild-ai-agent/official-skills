---
name: chatgpt-codex-onboarding
version: 1.0.0
description: "Connect ChatGPT / Codex subscription via OAuth device-code login (NOT BYOK)"
author: starchild
tags: [openai, oauth, chatgpt, codex, gpt-5, login, subscription]
---

# 🔐 ChatGPT / Codex OAuth Onboarding

Use the user's existing **ChatGPT or Codex subscription** for `gpt-5-codex`, `gpt-5`, `gpt-5-mini` access — without an API key.

The `openai_oauth` tool stays built-in. This SKILL.md is the reference doc.

## See also
- `skills/byok-custom-model/SKILL.md` — for vendor-key BYOK setup (DIFFERENT mechanism, NOT OAuth)
- `config/context/references/model-onboarding.md` — overall model-selection landscape

---

## When to use this tool

✅ **Use** when the user EXPLICITLY says one of:
- "Sign in with my ChatGPT account"
- "Use my Codex subscription"
- "Connect my ChatGPT Plus / Pro / Team / Enterprise"
- "Login with OpenAI / ChatGPT"

❌ **Do NOT use** for:
- BYOK / API-key-based setup ("Add OpenAI API key", "I have an OpenAI key")
- Other vendors that sound similar (Anthropic, Gemini, Qwen, etc.) → use `custom_models`
- "Add the OpenAI model" without subscription context — ASK first whether they want OAuth (subscription) or BYOK (API key)

⚠️ Vendor names that sound similar (Codex, OpenAI, GPT) are **NOT a signal** to start OAuth on their own. Only an explicit user request to sign in with their ChatGPT/Codex subscription triggers this flow.

---

## Connect flow

1. **Pre-check:** call `openai_oauth(action="status")`. If already connected, tell the user and stop.
2. **Start:** call `openai_oauth(action="start")`. The response contains:
   - `verification_url` — show this to the user
   - `user_code` — show this to the user
   - `pending_id` — keep for the next step
3. **Display to user** (both fields, clearly labeled):
   ```
   Open this URL in your browser:
     <verification_url>
   And enter this code:
     <user_code>
   ```
4. **Wait for the user to confirm** they approved in the browser. Don't auto-loop on `poll` — let the user say "I'm done" / "approved" first.
5. **Poll once:** `openai_oauth(action="poll", pending_id=<id from step 2>)`.
   - Success → `openai-codex/gpt-5-codex`, `openai-codex/gpt-5`, `openai-codex/gpt-5-mini` appear in the model selector.
   - Pending → ask the user if they completed the browser step; poll again only on confirmation.
   - Failed → start over from step 2.
6. **Confirm to user:** "Connected as <email>. You can switch with `/model openai-codex/gpt-5-codex`."

---

## Actions reference

| action | required | purpose |
|---|---|---|
| `status` | — | Current state, email, account_id, token expiry |
| `start` | — | Begin device-code flow → returns `verification_url` + `user_code` + `pending_id` |
| `poll` | `pending_id` | Check authorization status (call after user confirms approval) |
| `logout` | — | Disconnect + remove credentials |
| `refresh` | — | Force-refresh access token (debug; normally automatic) |
| `models` | (optional `force`) | List available models from the OAuth endpoint |
| `usage` | (optional `force`) | Subscription usage stats |

`force=true` on `models` / `usage` bypasses the cache TTL.

---

## After connecting

Models appear with the `openai-codex/` prefix:
- `openai-codex/gpt-5-codex` — primary
- `openai-codex/gpt-5` — full GPT-5
- `openai-codex/gpt-5-mini` — smaller / faster

User switches via `/model openai-codex/gpt-5-codex` or the model picker UI.

Subsequent calls hit OpenAI directly using the OAuth token — bypasses the platform proxy. Subscription usage limits apply (not the platform's credit balance).

---

## Reauth

Tokens auto-refresh via `refresh_token`. If a 401 surfaces:
1. `openai_oauth(action="refresh")` — try the manual refresh path.
2. If still failing, `openai_oauth(action="logout")` + restart from `start`.

---

## Critical rules

- **Never paste user_code in the verification_url.** They're separate — user must enter the code manually after opening the URL.
- **Never start the flow without explicit user request.** "I want to use ChatGPT" is enough; "I have an OpenAI key" is NOT (that's BYOK).
- **Wait for user confirmation between `start` and `poll`.** Auto-polling wastes API calls and gives stale "pending" responses.
