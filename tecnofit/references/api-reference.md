# Tecnofit API reference

Tecnofit (tecnofit.com.br) is a Brazilian fitness SaaS — CRM/ERP for gyms, boxes,
studios, courts and personal trainers. Its **public API is deliberately small**:
the "Tecnofit API" documents exactly **two endpoints**, and both are shaped for
access control, not gym operations.

| Item | Value |
|---|---|
| Docs | `https://tecnofit.readme.io` (OpenAPI 3.0.0 per page; index at `/llms.txt`) |
| Server | `https://rest.tecnofit.com.br` (server description: "Fitmass") |
| Auth scheme | `tokenAuth` — `type: apiKey`, `name: Authorization`, `in: header` |
| Spec download | none (`/openapi.json`, `/swagger.json` → 404 on the docs host) |

## The two endpoints

```
POST /2024-09-01/auth
     body {"user": "...", "pass": "..."}  ->  200 {"token": "..."}
     "Esse token tem válida de 1 hora, após isso, será necessário gerar um novo token"

GET  /2024-09-01/ticket-gate/{token}/{id}
     -> CustomerSummary
```

Per-tenant `user`/`pass` exchange. **No OAuth, no scopes, no client_id/secret.**
The token lives **one hour**; the client in this skill caches and re-mints it.

### `CustomerSummary`

```
name            string
phones          string[]
gender          "F" | "M"
birthDate       date
status          int   1 Ativo · 2 Bloqueado · 3 Cancelado · 4 Em Restrição
                      5 Em Licença · 6 Sem Contrato
customerHeight  int   (cm)
plans[]         { id, name, startDate, endDate,
                  status: 1 Ativo · 2 Bloqueado · 3 Cancelado · 5 Em Licença
                          6 Pendente de Pagamento · 7 Finalizado · 8 Aguardando Início }
```

The endpoint name — **ticket gate** — and the payload say what it is for:
validating an entrant at a turnstile, with the member's contract status inline.

## Behaviour verified against production (beyond the published docs)

| Probe | Result | What it tells us |
|---|---|---|
| `POST /2024-09-01/auth` with bogus credentials | **401 with an empty body** | The endpoint exists and rejects; there is no error JSON to parse |
| `POST /2024-09-01/auth` with `{}` or partial body | 401 | Credentials are required, not defaulted |
| `GET /2024-09-01/auth` | **405** | POST-only route |
| `GET /2024-09-01/ticket-gate/x/y` (no auth) | **404** `{"status_code":404,"reason_phrase":"Not Found"}` | Unknown path values 404 — **not** 401 |
| `GET /2024-09-01/ticket-gate/x/y` (bogus auth header) | **404** (same) | The `{token}` segment is resolved before/instead of the auth header, which suggests it is itself a gate/aggregator credential |

**Error envelope is `{"status_code": …, "reason_phrase": "…"}`** — not DRF, not
the shape the docs imply. Do not assume a `detail` field.

⚠️ Because a bad path value yields **404** rather than 401, "not found" is not
proof that the credentials are wrong. Verify the gate token and member id first.

## Not available (explicit NOT FOUND)

- Class / schedule (`aulas`, `turmas`, `agenda`) reads
- Booking (`reserva`) create or cancel
- Check-in / attendance (`frequência`, `presença`) reads or writes
- Member create/update, enrollment (`matrícula`) create/cancel
- Payments / finance
- **Webhooks** — no event or callback surface
- **Sandbox** — only the production server is declared
- API pricing, quotas, rate limits
- Any plan/entitlement catalogue beyond the per-member contract summary

Dead or redirecting hosts: `developers.tecnofit.com.br`, `api.tecnofit.com.br`,
`docs.tecnofit.com.br`, `centraldeajuda.tecnofit.com.br` all 302 to the marketing
site; `ajuda.tecnofit.com.br` is unreachable; `tecnofit.github.io` 404s.

## Commercial gate

- Product plans Starter / Business / Pro (e.g. 50 active students ≈ R$269/mo plus
  an implementation fee).
- The pricing page carries the row **"Integração com Wellhub, TotalPass e
  ClassPass"** with the footnote **"*Integração avançada é um módulo adicional."**
  → advanced integration is a **paid add-on**.
- A partner programme exists at `tecnofit.com.br/seja-parceiro/`; the docs host
  shows a "Log In" affordance, so the API console may be account-gated.
- **No self-service signup and no sandbox** — the tenant `user`/`pass` come from
  Tecnofit.

## Implications for this skill

| Question | Answer |
|---|---|
| Verify a member's identity and contract status | ✅ this is what the API is for |
| Validate an entry at a turnstile | ✅ |
| Read the class schedule | ❌ not exposed |
| Create or cancel a booking | ❌ not exposed — needs RPA or the paid add-on |
| Receive a check-in webhook | ❌ none exists |

So the skill is intentionally four functions. Do not promise a Tecnofit booking
connector; the capability is not in the public API.
