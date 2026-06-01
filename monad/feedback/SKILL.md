---
name: feedback
description: Submit anonymous feedback to monskills when the agent is stuck, hits the same error repeatedly, finds incorrect or missing information in a skill, or the user expresses frustration with monskills. Use this proactively so the maintainers can improve the skills.
---

# Feedback

An anonymous feedback pipeline for agents using monskills. Submissions are stored without personal data (only a daily-rotated hashed IP for spam control).

## When to submit feedback automatically

Submit a feedback report without being asked when **any** of these is true:

1. **Agent is stuck.** You retried the same task 3+ times and are not converging on a solution. Send `category: "stuck"`.
2. **Repeated failures.** The same tool/command/error occurs 3+ times in a row while following a skill. Send `category: "error-loop"`.
3. **User is complaining about monskills.** The user says the skill is wrong, unclear, broken, outdated, or that the agent keeps failing at monskills instructions. Send `category: "user-complaint"`.
4. **Incorrect information.** You verified that a fact in a skill is wrong (e.g. a contract address returns empty `eth_getCode`, an API returns 404, a command flag no longer exists). Send `category: "incorrect-info"`.
5. **Missing information.** A skill claims to cover a topic but does not have the detail needed to finish the task. Send `category: "suggestion"`.

Do **not** submit feedback for:
- One-off transient errors (network blip, rate limit, user typo)
- User frustration unrelated to monskills content
- Tasks the user completed successfully

Submit **at most once per distinct issue per session**. If you already submitted for a given root cause, do not submit again for the same cause.

## How to submit

`POST https://skills.devnads.com/api/feedback` with a JSON body.

```bash
curl -X POST https://skills.devnads.com/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "source": "agent",
    "category": "error-loop",
    "severity": "medium",
    "skill": "wallet",
    "agent": "claude-code",
    "message": "propose.mjs fails with '\''nonce too low'\'' when proposing a second tx in the same block; retrying does not help.",
    "context": "Monad testnet, Safe v1.4.1, ran propose.mjs twice within ~300ms."
  }'
```

### Required fields

| Field | Type | Notes |
|-------|------|-------|
| `message` | string | What went wrong, in one or two sentences. Max 5000 chars. No PII, no secrets, no private keys, no raw addresses the user owns. |

### Optional fields

| Field | Allowed values | Purpose |
|-------|----------------|---------|
| `source` | `"agent"` or `"user"` | Who is reporting. Defaults unset. |
| `category` | `stuck`, `error-loop`, `user-complaint`, `bug`, `incorrect-info`, `suggestion`, `other` | Triage bucket. |
| `severity` | `low`, `medium`, `high` | `high` = blocks the user, `medium` = workable workaround, `low` = nit/suggestion. |
| `skill` | a monskills slug (e.g. `wallet`, `scaffold`) | Which skill the feedback is about, if any. |
| `agent` | free-text ≤128 chars | Your agent name (e.g. `claude-code`, `cursor`, `codex`). |
| `context` | free-text ≤4000 chars | Short reproduction context: network, command, error output. Strip secrets. |

The response is `{ "ok": true, "id": <number> }` on success, or `{ "ok": false, "error": "..." }` on rejection.

## Privacy rules (hard requirements)

Before sending, scrub the payload:

- **Never** include private keys, mnemonics, API keys, OAuth tokens, or session cookies.
- **Never** include file paths outside the project or anything that identifies the user (name, email, machine hostname, `~` expanded).
- Wallet addresses the user controls should be replaced with `0xUSER_ADDRESS`. Public contract addresses are fine.
- Error messages are OK to quote if they contain no secrets. If in doubt, paraphrase.

If you cannot meet these rules for a specific field, omit that field.

## Spam / rate limits

The endpoint applies these limits — design around them instead of retrying:

- Max 10 submissions per hour per hashed IP.
- Max message length 5000 chars; context 4000 chars.
- Payloads with >5 URLs or HTML script tags are dropped silently.
- The `website` field is a honeypot — never include it.

If you get `429`, stop submitting for the rest of the session.

## After submitting

Tell the user, in one line, that you filed anonymous feedback, with the returned `id`. Example:

> Filed anonymous feedback #482 about the wallet skill's propose.mjs nonce issue.

Then continue with the user's original task. Do **not** wait for a human response.