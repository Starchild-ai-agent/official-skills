---
name: chatgpt-codex-onboarding
version: 2.0.2
description: "Connect ChatGPT / Codex subscription via OAuth device-code login (NOT BYOK)"
author: starchild
delivery: script
protected: true
tags: [openai, oauth, chatgpt, codex, gpt-5, login, subscription]
---

# 🔐 ChatGPT / Codex OAuth Onboarding

Use the user's existing **ChatGPT or Codex subscription** for `gpt-5-codex`, `gpt-5`, `gpt-5-mini` access — without an API key.

This is a **script-mode skill** — no tools registered. Read this file, then call the exports from a `bash` block.

## See also
- `byok-custom-model` skill — for vendor-key BYOK setup (DIFFERENT mechanism, NOT OAuth)
- `config/context/references/model-onboarding.md` — overall model-selection landscape

---

## When to use this skill

✅ **Use** when the user EXPLICITLY says one of:
- "Sign in with my ChatGPT account"
- "Use my Codex subscription"
- "Connect my ChatGPT Plus / Pro / Team / Enterprise"
- "Login with OpenAI / ChatGPT"

❌ **Do NOT use** for:
- BYOK / API-key-based setup ("Add OpenAI API key", "I have an OpenAI key")
- Other vendors that sound similar (Anthropic, Gemini, Qwen, etc.) → use `byok-custom-model`
- "Add the OpenAI model" without subscription context — ASK first whether they want OAuth (subscription) or BYOK (API key)

⚠️ Vendor names that sound similar (Codex, OpenAI, GPT) are **NOT a signal** to start OAuth on their own. Only an explicit user mention of "subscription / sign in / login with ChatGPT" qualifies.

---

## Onboarding flow

1. **status** — check if a credential already exists (resume vs fresh).
2. **start** — get a verification URL + user code from OpenAI; persisted to disk.
3. Tell the user: open the URL in a browser, log in to their ChatGPT / Codex account, and enter the code. Do NOT auto-poll.
4. Wait for the user to confirm they approved the device.
5. **poll** — finalize the OAuth handshake; on success, the new model becomes available.

If poll returns `status='pending'`, the user hasn't finished yet — wait for them, then poll again. Don't loop poll automatically.

---

## Script usage

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/chatgpt-codex-onboarding")
from exports import status, start, poll, logout, refresh, models, usage

# Check current state
print(json.dumps(status(), indent=2))

# Start a flow
result = start()
print(f"Open: {result['verification_url']}\nCode: {result['user_code']}")
EOF
```

After the user approves:

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/chatgpt-codex-onboarding")
from exports import poll
print(json.dumps(poll(), indent=2))
EOF
```

---

## Functions

| Function | Required args | Purpose |
|---|---|---|
| `status()` | — | Inspect current OAuth state, expiry, model list |
| `start()` | — | Begin device-code flow → verification_url + user_code |
| `poll(pending_id=None)` | — | Check authorization (call after user confirms approval) |
| `logout()` | — | Disconnect + remove credentials |
| `refresh()` | — | Force-refresh access token (debug; normally automatic) |
| `models(force=False)` | — | List available models from the OAuth endpoint |
| `usage(force=False)` | — | Subscription usage stats |

`force=True` on `models` / `usage` bypasses the cache TTL.

All functions return a dict with `ok: True` on success or `ok: False, error: "..."` on failure.

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
1. `refresh()` — try the manual refresh path.
2. If still failing, `logout()` + restart from `start()`.

---

## Critical rules

- **Never paste user_code in the verification_url.** They're separate — user must enter the code manually after opening the URL.
- **Never start the flow without explicit user request.** "I want to use ChatGPT" is enough; "I have an OpenAI key" is NOT (that's BYOK).
- **Wait for user confirmation between `start` and `poll`.** Auto-polling wastes API calls and gives stale "pending" responses.
