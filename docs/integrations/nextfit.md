# NextFit (Next Fit) — integration dossier

**Status: 🔴 NOT A BUILD TARGET — reclassified 2026-10-13.**

Two independent reasons, and only the first one is fixable:

1. **Blocked on customer-side access** — needs a gym account with the paid
   *"API Next Fit"* add-on activated, plus the in-panel documentation. Only a
   customer or a vendor demo tenant can supply this.
2. **Structurally read-only** — even fully unblocked, the API cannot write. The
   vendor's own help article says so in as many words (quoted below). **Booking
   writes are impossible**, which is precisely the use case that put NextFit in
   Leonardo's Phase 1.

Because (2) is not a matter of access, NextFit is **dropped from the Phase-1
build queue**. It is a *read-only reporting source*, not a system of record we
can act on. See "Verdict for us" below for the connector shape it would take if
a client ever asks for the reports.

> ⚠️ This changes the phase table in `README.md`, where NextFit sits at #4. That
> table is a *product-value* ordering, not a build order — but the entry now
> needs a footnote, and Leonardo has not been told yet.

## What it is

Brazilian gym/studio/box management SaaS aimed at **small gyms, boutique
studios, boxes, martial arts, swim schools, pilates and sports courts**.

| Item | Value |
|---|---|
| Vendor | DLG TECNOLOGIA LTDA, Criciúma/SC (CNPJ 31.265.901/0001-39) |
| Brand history | rebrand of **Fitastic** — `fitastic.com.br` now serves "Fitastic agora é Next Fit" |
| Student app | Google Play `br.com.fitastic.appaluno`, 1M+ downloads, 185K reviews, 4.6 |
| Product scope | plans/contracts, finance, sales/store, agenda & class booking, check-in, workouts, physical assessments, CRM, NFS-e/NFC-e, Next Fit Pay, AI WhatsApp agents, self-service totem, facial recognition |
| Manager SPA | `app.nextfit.com.br` |
| Help center | `ajuda.nextfit.com.br` (Freshdesk) |

## The API: `API Next Fit`

Read from the vendor's own help article
*"Como ativar e utilizar a API do Next Fit?"*
(`ajuda.nextfit.com.br/support/solutions/articles/69000875320-…`).

**The decisive sentence, verbatim:**

> "Atualmente, a API Next Fit possui **apenas endpoints GET** para a consulta
> de dados, **não sendo possível realizar alterações (INSERT, UPDATE...)** por
> meio da API."

| Item | Value |
|---|---|
| Nature | **paid add-on**, activated inside the panel: *Loja ▸ card "API Next Fit" ▸ CONHEÇA ▸ ATIVAR AGORA ▸ CONTRATAR* |
| Credentials | **access keys** ("chaves de acesso") created and managed in the panel (`+ CHAVE ACESSO`, rename, delete) — no OAuth |
| Data domains exposed | **agenda, financeiro, contratos, vendas, CRM, clientes** |
| Writes | **NONE** (GET-only) |
| Webhooks | **NOT FOUND** — help-center search for "webhook" returns nothing |
| Sandbox | **NOT FOUND** |
| Public docs / OpenAPI | **NOT FOUND** — documentation lives *inside the customer panel*: *Loja ▸ API Next Fit ▸ CONHEÇA ▸ ACESSAR DOCUMENTAÇÃO* |
| Public endpoint paths | **NOT FOUND** — do not invent them |
| Rate limits / API price | **NOT FOUND** — article refers to an in-panel "tabela de preços" |
| Cancellation | service stays active until the end of the billing period ("Em cancelamento"), one final charge, **no pro-rata** |

API host exists but serves nothing: `https://api.nextfit.com.br/` returns the
literal body `Api Next Fit` (GET only, behind Cloudflare; `/swagger`, `/docs`,
`/api` all empty). The manager SPA's `env-config.js` also reveals
`apiadm`, `signalrfront` (SignalR realtime), `publico`, `venda`, `agendamento`,
`notificacoes`, `totem`, `conversacao` backends — internal, undocumented.

## Aggregators (native, not API)

All confirmed from NextFit's own help center, all **free** and configured
in-platform — these are product integrations, not developer APIs:

- **TotalPass** — `articles/69000841617-…`; TotalPass portal ▸ Integrações ▸
  Integrações Novas ▸ select gym + partner Next Fit ▸ copy API Key → paste into
  NextFit's TotalPass card; optional booking
- **Wellhub/Gympass** — `articles/69000811140-…`; uses the Gym ID
  ("Código Wellhub para parceiros"), supports check-in and booking
- **ClassPass**, **MGB** (Metodologia Gustavo Borges) — additional integrations
- Also: GoNutri, WhatsApp message integrator (Pinggo.ai), CRM automations

## Test credentials needed

1. A **gym account on NextFit with the "API Next Fit" add-on activated**
   (a paying customer, or a vendor-provided demo tenant).
2. At least one **access key** generated in that panel.
3. The **in-panel API documentation** (screenshots or the doc URL), since it is
   the only source of endpoint paths.

Without #3 we cannot write this skill honestly — the whole endpoint surface is
behind the customer login.

## Reclassification (2026-10-13)

| | |
|---|---|
| **Was** | Phase 1, #4 — "system of record" alongside EVO / Angulare / Tecnofit |
| **Is now** | read-only reporting source; **not** in the build queue |
| **Why** | the public API is GET-only. No INSERT, no UPDATE, no booking, no check-in |
| **Consequence** | NextFit cannot host the core booking loop. Any future work here is reporting/dashboards, and only if a client asks |
| **Notified?** | **No** — Leonardo has not been told; the phase table still shows it at #4 |

The distinction that matters: **EVO and Angulare are systems of record we can
write to; Tecnofit and NextFit are not.** Tecnofit's public API is two
access-control endpoints, NextFit's is read-only. Four vendors in Phase 1, but
only **two** of them can carry a booking.

---

## Verdict for us

| Use case | Feasible? |
|---|---|
| Read agenda / contracts / sales / finance / CRM (reporting, BI, reconciliation) | ✅ via the paid add-on |
| Create/cancel a booking | ❌ GET-only |
| Check-in write | ❌ GET-only |
| Check-in webhook | ❌ none |
| Booking automation | ❌ → would require **RPA** against the panel, with the usual fragility caveats |

Skill shape when unblocked: a **read-only reporting connector** —
`nextfit_clients()`, `nextfit_contracts()`, `nextfit_agenda(date)`,
`nextfit_sales(since)`, `nextfit_finance(since)`, `nextfit_crm()` — with an
explicit "no write capability" section so an agent never promises a booking.

## Sources

- `https://ajuda.nextfit.com.br/support/solutions/articles/69000875320-como-ativar-e-utilizar-a-api-do-next-fit-`
- `https://ajuda.nextfit.com.br/support/solutions/articles/69000841617-…` (TotalPass), `…/69000811140-…` (Wellhub)
- `https://nextfit.com.br/` (scope, footer CNPJ)
- `https://play.google.com/store/apps/details?id=br.com.fitastic.appaluno`
- `https://fitastic.com.br` (rebrand)
- `https://api.nextfit.com.br/` (body `Api Next Fit`)
- `https://app.nextfit.com.br/env-config.js` (backend list)
- Help-center searches for `API`, `integração`, `webhook`
