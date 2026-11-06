# Tecnofit — integration dossier

**Status: ✅ SKILL SHIPPED** — `tecnofit/` (4 functions, v1.0.0). Public API
exists, but it is a 2-endpoint **access-control** API, not a gym-ops API:
no schedule, booking, check-in or payment endpoints.

> The skill lives in `tecnofit/` at the repo root. Live-verified against
> production: the auth endpoint's 401-on-bad-credentials, the 405 on GET /auth,
> and the fact that ticket-gate answers **404 (not 401)** for unresolvable path
> values. This file is the research dossier behind it.

## What it is

Brazilian fitness SaaS/CRM+ERP for gyms, boxes (CrossFit), studios
(pilates/yoga/dance/martial arts), courts and personal trainers. Homepage claims
16,500+ fitness businesses. Scope: sales, agenda (fixed/drop-in enrollment,
attendance/absence/make-up tracking, waitlist), workouts & physical assessment,
student app, finance (cash flow, DRE, collections), staff/commissions, access
control, AI/CRM.

## API

| Item | Value |
|---|---|
| Docs | `https://tecnofit.readme.io` (ReadMe.io; machine index at `/llms.txt`) |
| Spec | OpenAPI 3.0.0 embedded per doc page, `info.title = "Tecnofit API"` v1.0.0 |
| Server | `https://rest.tecnofit.com.br` (server description: "Fitmass") |
| Endpoints | **exactly two** |
| Schema download | none (`/openapi.json`, `/swagger.json` → 404 on the docs host) |

### The two endpoints

```
POST /2024-09-01/auth
     body {"user": "...", "pass": "..."}  ->  200 {"token": "..."}   401 "Não autorizado"
     "Esse token tem válida de 1 hora, após isso, será necessário gerar um novo token"

GET  /2024-09-01/ticket-gate/{token}/{id}
     -> CustomerSummary
```

Auth scheme: `tokenAuth` — `type: apiKey`, `name: Authorization`, `in: header`.
Per-tenant `user`/`pass` exchange, **no OAuth, no scopes, no client_id/secret**.

`CustomerSummary` response:

```
name            string
phones          string[]
gender          "F" | "M"
birthDate       date
status          int   1 Ativo, 2 Bloqueado, 3 Cancelado, 4 Em Restrição,
                      5 Em Licença, 6 Sem Contrato
customerHeight  int   (cm)
plans[]         { id, name, startDate, endDate,
                  status: 1 Ativo, 2 Bloqueado, 3 Cancelado, 5 Em Licença,
                          6 Pendente de Pagamento, 7 Finalizado, 8 Aguardando Início }
```

The endpoint name — **"ticket gate"**, keyed by `{token}/{id}` — and the shape of
the payload say what this API was built for: **validating an entrant at a
turnstile / access-control point**, with the member's contract status inline.
It is an entitlement-verification API, not a class/booking API.

## Not available (explicit NOT FOUND)

- Class/schedule (`aulas`/`turmas`/`agenda`) read endpoints
- Booking (`reserva`) create or cancel
- Check-in / attendance (`frequência`/`presença`) read or write
- Member create/update, enrollment (`matrícula`) create/cancel
- Payments/finance
- **Webhooks** — no event/callback surface in the spec or index
- **Sandbox** — only the production server is declared
- API pricing, quotas, rate limits
- Any plan/entitlement catalogue beyond the per-member contract summary

Dead/redirecting hosts (checked): `developers.tecnofit.com.br`,
`api.tecnofit.com.br`, `docs.tecnofit.com.br`, `centraldeajuda.tecnofit.com.br`
all 302 to the marketing site; `ajuda.tecnofit.com.br` unreachable;
`tecnofit.github.io` 404.

## Commercial gate

- Product plans Starter / Business / Pro; example 50 active students = R$269/mo
  + implementation fee (from `tecnofit.com.br/precos/`).
- The pricing page carries the row **"Integração com Wellhub, TotalPass e
  ClassPass"** with a footnote **"*Integração avançada é um módulo adicional."**
  → advanced integration is a **paid add-on module**; Wellhub/TotalPass are
  checked on the upper plans.
- A partner program page exists at `tecnofit.com.br/seja-parceiro/`.
- The docs host shows a "Log In" affordance → the API console/try-it may be
  account-gated even though the spec text is public.

## Test credentials needed

A tenant `user` + `pass` — i.e. a Tecnofit customer login, or partner-program
credentials. Ask the vendor; there is no self-service signup and no sandbox.

## Verdict for us

| Use case | Feasible? |
|---|---|
| Verify a member's identity + contract status (entitlement) | ✅ yes |
| Validate an entry at a turnstile / access point | ✅ yes (that's its purpose) |
| Read the class schedule | ❌ not in the public API |
| Create/cancel a booking | ❌ not in the public API — would need RPA or the paid "integração avançada" module |
| Check-in webhook | ❌ none |

Skill shape when built: `tecnofit_auth()` (cached, 1h TTL),
`tecnofit_member(token_id)` → normalised member + contract status,
`tecnofit_entitlement(member_id)` → is the contract active / is access allowed.
~1 module, small.

## Sources

- `https://tecnofit.readme.io`, `/llms.txt`,
  `/reference/post_2024-09-01-auth`, `/reference/get_2024-09-01-ticket-gate-token-id`
- `https://www.tecnofit.com.br/`, `/precos/`, `/seja-parceiro/`,
  `/sitemap_index.xml`, `/page-sitemap.xml`, `/robots.txt`
- `https://totalpass.com/br/`, `https://totalpass.com/br/academias/`
