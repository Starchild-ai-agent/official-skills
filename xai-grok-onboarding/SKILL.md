---
name: xai-grok-onboarding
version: 1.1.0
description: |
  Connect an xAI account (X Premium / X Premium+ / SuperGrok / SuperGrok Heavy) via OAuth 2.0 device-code login.

  Use when the user wants to sign in with their xAI account (e.g. "use my SuperGrok", "log in with Grok", "connect my X Premium").
author: starchild
delivery: script
protected: true
tags: [xai, grok, oauth, supergrok, x-premium, login, subscription, multi-agent]

---

# 🟢 xAI OAuth Onboarding

Use any active **xAI account** — X Premium, X Premium+, SuperGrok, or SuperGrok Heavy — for `grok-4.3`, `grok-build-0.1`, `grok-4.20-*` and multi-agent models. No separate API key needed.

This is **standard OAuth 2.0** (RFC 8628 Device Authorization Grant), not a vendor-custom flow.

## Tier → model access

The JWT issued by `auth.x.ai` carries a `tier` claim; higher tiers unlock more models from `/v1/models`. Observed mapping (xAI does not publish this officially):

| Tier | Subscription | Approx. model access |
|---|---|---|
| 1 | X Premium ($8/mo) | grok-4.3 baseline |
| 2 | X Premium+ ($16/mo) | + grok-4.20-0309 variants |
| 3 | SuperGrok ($30/mo) | + reasoning models |
| 4 | SuperGrok Heavy ($300/mo) | + grok-build-0.1 + multi-agent |

`status()` reports the user's tier so they know which models will be available.

This is a **script-mode skill** — no tools registered. Read this file, then call the exports from a `bash` block.

## See also
- `byok-custom-model` skill — for vendor-key BYOK setup (xAI API key from console.x.ai, different mechanism — bills per-token, NOT subscription-backed)
- `chatgpt-codex-onboarding` skill — same pattern, for ChatGPT/Codex subscription
- `config/context/references/model-onboarding.md` — overall model-selection landscape

---

## When to use this skill

✅ **Use** when the user EXPLICITLY says one of:
- "Sign in with my Grok / SuperGrok account"
- "Use my SuperGrok / X Premium subscription"
- "Connect SuperGrok Heavy"
- "Login with xAI / Grok"
- "Use my Grok Heavy subscription"

❌ **Do NOT use** for:
- "Add Grok via API key" / "I have an xAI API key" → use `byok-custom-model` (the xAI template)
- Other vendors (Anthropic, OpenAI, Gemini, Qwen, etc.) → use `byok-custom-model`
- "Add the Grok model" without subscription mention → ASK the user which path they want (subscription OAuth vs. API key BYOK)

The two paths are mutually exclusive billing-wise. Subscription OAuth uses the user's monthly quota; BYOK API key uses console.x.ai pay-per-token credits.

---

## Critical preflight — account gate awareness

xAI has a known backend gate that **denies OAuth grants for some accounts even with an active SuperGrok subscription**. This is upstream xAI behavior, not a client bug. Symptoms:

- Verification page loads, but clicking "Approve" returns `access_denied` from the token endpoint
- Hermes Agent has documented the same in [issue #26847](https://github.com/NousResearch/hermes-agent/issues/26847)

If `poll()` returns `AccountAccessDenied`:
1. Verify the user's SuperGrok subscription is active (grok.com / settings)
2. Suggest they try the verification URL in their already-logged-in browser (not a fresh incognito)
3. If still denied → fall back to BYOK API key path (`byok-custom-model` skill, xAI template, key from https://console.x.ai)

Do NOT silently retry — the gate is deterministic per account, retrying wastes time.

---

## Flow

The flow has 4 user-visible steps. Drive it like this:

### 1. start() — generate the verification URL

```bash
python3 - <<'EOF'
import json, sys
sys.path.insert(0, '/data/workspace/skills/xai-grok-onboarding')
from exports import start
print(json.dumps(start(), indent=2))
EOF
```

Returns `verification_url_with_code` — tell the user to open it in their browser, log in (if needed), and click Approve.

⚠️ **Wait for explicit user confirmation before calling poll().** Polling too eagerly burns tokens for a "still pending" state.

### 2. poll() — confirm approval (after the user says "done")

```bash
python3 - <<'EOF'
import json, sys
sys.path.insert(0, '/data/workspace/skills/xai-grok-onboarding')
from exports import poll
print(json.dumps(poll(), indent=2))
EOF
```

Three terminal outcomes:
- `status="connected"` → success; show the user `default_model_id` to switch to
- `status="pending"` → user hasn't approved yet; ask them to confirm before re-polling
- `ok=false` with `access_denied` → see "account gate" section above
- `ok=false` with `expired` → device code timed out (15 min); call `start()` again

### 3. After successful connect — tell the user

The frontend model picker refreshes after connect. The default model is `xai-grok/grok-4.3`. Other available models depend on the subscription tier (SuperGrok Heavy unlocks `grok-build-0.1`).

To switch: `/model xai-grok/grok-4.3` or use the picker.

---

## Function reference

| Function | Args | Returns |
|---|---|---|
| `status()` | — | Current credential state + available models + expiry |
| `start()` | — | Device code prompt: `{verification_url_with_code, user_code, expires_in_seconds}` |
| `poll(pending_id=None)` | optional `pending_id` | `{status: connected/pending}` + credential info |
| `logout()` | — | Delete credential + flush agent cache |
| `refresh()` | — | Force-refresh access token (debug; normally automatic) |
| `models(force=False)` | — | List available models from the OAuth endpoint |

`force=True` on `models` bypasses the cache TTL.

All functions return a dict with `ok: True` on success or `ok: False, error: "..."` on failure.

---

## After connecting

Models surface with the `xai-grok/` prefix:
- `xai-grok/grok-4.3` — primary chat model (default)
- `xai-grok/grok-build-0.1` — Grok Build coding model (SuperGrok Heavy tier only)
- `xai-grok/grok-4.20-0309-reasoning` — reasoning variant
- `xai-grok/grok-4.20-0309-non-reasoning` — faster, no reasoning
- `xai-grok/grok-4.20-multi-agent-0309` — multi-agent variant (uses /v1/responses internally)

User switches via `/model xai-grok/grok-4.3` or the model picker UI.

### Lane routing (transparent)

The provider auto-routes based on model id:
- Multi-agent models → `https://api.x.ai/v1/responses` (Responses API)
- All other Grok models → `https://api.x.ai/v1/chat/completions` (OpenAI-compatible)

Users do not need to know which dialect each model speaks — passing the standard `messages=[...]` shape works for both. For multi-agent, an optional `thinking={"effort": "low"|"medium"|"high"}` controls how many agents collaborate.

Subsequent chat calls hit `https://api.x.ai/v1` directly using the OAuth bearer — bypasses the platform proxy. **Subscription usage limits apply** (not the platform credit balance). Image / video models (`grok-imagine-*`) are filtered out of the chat picker but accessible via image generation tools.

---

## Reauth

Tokens auto-refresh via `refresh_token` (6h access token TTL — relatively generous vs Codex's 1h). If a 401 surfaces:
1. `refresh()` — try the manual refresh path
2. If still failing, `logout()` + restart from `start()`

---

## Critical rules

- **Never paste user_code into the verification URL field for the user.** The URL `accounts.x.ai/oauth2/device?user_code=XXXX` already embeds the code — just open it.
- **Never start the flow without explicit user request.** "I want to use Grok" needs a follow-up question about subscription vs. API key; "use my SuperGrok subscription" is enough.
- **Wait for user confirmation between `start` and `poll`.** Auto-polling wastes API calls and produces stale "pending" responses.
- **On `access_denied`, do NOT retry blindly.** Explain the gate, suggest BYOK fallback.
- **Never log or echo the access_token / refresh_token.** They're persistent credentials. The exports never include them in return values either.
