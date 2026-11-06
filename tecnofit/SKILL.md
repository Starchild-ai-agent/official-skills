---
name: tecnofit
version: 1.0.0
description: |
  Tecnofit member lookup and entitlement: verify a student's identity and contract status, and decide whether they may enter.

  Use when checking a Tecnofit gym member at a turnstile or reception — is this student active, do they hold a valid contract, should access be granted (e.g. "check member 12345 at the gate", "is this student's plan still active"). Tecnofit's public API is access-control only: it has no schedule, booking or check-in endpoints.
delivery: script
author: starchild
tags: [gym, fitness, tecnofit, entitlement, access-control, members, brazil]
metadata:
  starchild:
    emoji: "\U0001F6AA"
    skillKey: tecnofit
    requires:
      env: [TECNOFIT_USER, TECNOFIT_PASS]
user-invocable: true
disable-model-invocation: false
---

# 🚪 Tecnofit — member lookup & entitlement

Member verification for **Tecnofit** (tecnofit.com.br), a Brazilian fitness
CRM/ERP for gyms, boxes, studios and courts.

**Tecnofit's public API has exactly two endpoints.** It is an access-control API
— the shape of a turnstile integration — not a gym-operations API. This skill is
therefore deliberately small, and it will not book classes, read a timetable or
write check-ins, because the API does not expose those.

## Credentials

| Var | What it is |
|---|---|
| `TECNOFIT_USER` | the tenant user |
| `TECNOFIT_PASS` | the tenant password |

Collected with `request_env_input` — never ask for them in chat. They come from
Tecnofit's partner programme: **there is no self-service signup and no sandbox.**

```
tecnofit_check_credentials()
# -> {"credentials": "ok", "token_expires_in": 3600, ...}
```

## How to Call

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/tecnofit")
from exports import tecnofit_check_credentials, tecnofit_entitlement

print(json.dumps(tecnofit_check_credentials(), indent=2, ensure_ascii=False))
print(json.dumps(tecnofit_entitlement(gate_token="…", member_id="…"), indent=2))
EOF
```

Or through the platform loader:

```python
from core.skill_tools import _modules
tecnofit = _modules["tecnofit"]
tecnofit.tecnofit_member(gate_token="…", member_id="…")
```

Standalone CLI:

```bash
python3 tecnofit/exports.py tecnofit_check_credentials
```

Every function returns `{"ok": True, "data": ...}` or
`{"ok": False, "status": ..., "error": ..., "hint": ...}`.

## Functions

| Function | Purpose |
|---|---|
| `tecnofit_check_credentials()` | Prove the tenant user/password work; report the token's 1-hour life. |
| `tecnofit_auth()` | Mint (and cache) the access token. Mostly for debugging — callers never handle the token. |
| `tecnofit_member(gate_token, member_id, auth_token=None)` | Look up one student through the ticket gate, normalised. |
| `tecnofit_entitlement(gate_token, member_id, auth_token=None)` | **Should this student be let in?** Verdict + reasons. |

The token is cached and re-minted automatically; it lives **1 hour**.

## Workflows

### Is this student allowed in?

```python
tecnofit_entitlement(gate_token="…", member_id="…")
```

```json
{
  "allowed": false,
  "verdict": "denied",
  "reasons": ["no active contract (canceled)"],
  "active_contracts": 0,
  "contracts": 1,
  "member": { "name": "…", "status": "active", "plans": [ { "status": "canceled" } ] }
}
```

`allowed` is true only when the student is `active` **and** holds at least one
`active` contract. Everything else — blocked, canceled, restricted, on leave,
no contract, pending payment — is surfaced as an explicit reason rather than
silently allowed.

### Who is this member?

```python
tecnofit_member(gate_token="…", member_id="…")
```

Returns the student (name, phones, gender, birth date, height, status) and their
contracts with human-readable status labels.

## Key Facts / Gotchas

- **Two endpoints, and that is the whole API.** No schedule, booking, check-in,
  payment or webhook endpoints are documented. Do not offer a Tecnofit booking
  connector.
- **The token expires after 1 hour.** The client re-mints it transparently, so a
  persistent `401` means the credentials are wrong, not that the token went stale.
- **A bad path value returns `404`, not `401`.** Tecnofit resolves the
  `{token}` segment before the auth header, so "not found" is *not* proof of bad
  credentials. Verify the gate token and member id first.
- **The `{token}` in the URL is a gate/aggregator credential, not the auth
  token.** Two different values are in play on the same call: the auth token in
  the `Authorization` header, and the gate token in the path.
- **The error envelope is `{"status_code": …, "reason_phrase": "…"}`** — not the
  `detail` shape most Brazilian APIs use. A `401` from `/auth` comes back with an
  **empty body**.
- **No sandbox.** The only declared server is production.
- **Gated commercially**: the API sits behind Tecnofit's partner programme, and
  "integração avançada" is a paid add-on module.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `missing Tecnofit credential(s)` | Env not set | `request_env_input` for `TECNOFIT_USER` / `TECNOFIT_PASS` |
| `401` with an empty body | Bad tenant credentials | Confirm them with Tecnofit — there is no self-service path |
| `404` on ticket-gate | The gate token or member id does not resolve | Check both path values; this is not an auth failure |
| `405` | Wrong verb | `/auth` is POST-only |
| `ProxyError` / connection errors | Local proxy configuration | The client falls back from `requests` to the stdlib automatically |

## References

- `references/api-reference.md` — both endpoints, the full `CustomerSummary`
  schema and status enums, the verified production behaviour table (404 vs 401,
  the error envelope shape), the explicit NOT-FOUND list, and the commercial gate.
- `docs/integrations/tecnofit.md` (repo root) — the research dossier.
- `docs/integrations/pt-br-glossary.md` — Portuguese → Chinese glossary.
