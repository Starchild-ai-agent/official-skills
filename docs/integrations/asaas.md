# Asaas — integration dossier

**Status: 🟢 buildable — the cheapest access in the census, with one caveat.**

No contract, no sales call, no approval queue, no CNPJ. But the sandbox signup
form is **not anonymous**: it asks for a full name *as on the document*, a
personal mobile that receives the activation code, and a full address (CEP, city,
street, neighbourhood, number). So "self-service" means *no gatekeeper*, not
*no data* — someone has to volunteer their own details, and a real phone has to
receive an SMS. Worth saying out loud before asking anyone to sign up.

That matters for who owns the account, and it matters more for production: a
payment account is a regulated thing tied to a real person or company.

**And none of this is hypothetical — Asaas is the acquirer NUMA already charges
through.**

Researched 2026-10-13 from the vendor's own machine-readable index
(`docs.asaas.com/llms.txt` → `reference/llms.txt`, 481 entries).

---

## Why this one first

Two independent reasons, and they reinforce each other.

**1. It is the cheapest access in the whole census** — with one caveat worth
stating plainly. Sandbox signup is self-service at `sandbox.asaas.com`, the
account is independent of production, and approval is automatic when the fields
are valid. No CNPJ, no contract, no partner programme, no waiting on a human.
Compare with Stone (partner programme + homologation) or TotalPass (Termo de
Adesão).

**The caveat: the signup form is not anonymous.** It requires

    Nome completo   as on the document
    Celular         a personal mobile — it receives the activation code
    CEP / Cidade / Rua / Bairro / Número / Complemento

so a real person's identity and a phone that can receive an SMS go into it. That
is still far cheaper than a partner programme, but it is not "no ask needed" —
someone has to volunteer their own details, and they should know they are doing
it. A CPF is not on the screen captured so far; a Brazilian financial account
almost certainly requires one somewhere in the flow.

**2. We have already hit it in production, from the wrong side.** While
debugging NUMA's checkout we got this out of the Angular Pay gateway:

```
Problema ao decodificar resposta asaas: 404 - b''
```

NUMA's payments run on Asaas. Everything the gateway does is an Asaas call — we
were reading Asaas errors through a wrapper that swallows them.

---

## ⚠️ The finding: Angular Pay is a thin Asaas wrapper

Asaas's Pix QR response, verbatim from the docs:

```
GET /v3/payments/{id}/pixQrCode
{
  "encodedImage":   "<base64 QR>",
  "payload":        "<copia e cola>",
  "expirationDate": "<expiry>"
}
```

And what Angular Pay's gateway returned to us:

```
pix_qrcode        ← encodedImage
pix_copy_paste    ← payload
pix_expires_at    ← expirationDate
```

**Field-for-field rename, nothing added.** That single fact explains every
opaque failure we spent days on:

| What we saw | What it actually was |
|---|---|
| `not-authorized` with an empty `error_code` | Angular Pay swallowing Asaas's rejection |
| `Problema ao decodificar resposta asaas: 404` | Asaas refusing a lookup Angular Pay made on our behalf |
| `CPF é obrigatório para pagamento via Pix` | Asaas requires `cpfCnpj` on the customer |
| `payments[0].split[1].amount must be >= 0` | **Asaas Splits** — the tenant has split rules configured |
| `valor não permitido` below R$100 | an Angular Pay-side rule, not an Asaas one |

**Consequence for debugging:** anything that goes wrong in NUMA's payment path is
ultimately an Asaas behaviour. Reading Asaas's own docs turns guesswork into
lookups — that alone justified this dossier.

---

## Authentication

| | |
|---|---|
| Header | **`access_token: <key>`** (not `Authorization: Bearer`) |
| Sandbox base | `https://api-sandbox.asaas.com/v3` |
| Production base | `https://api.asaas.com/v3` |
| Key scope | keys are **per-environment**; a production key against sandbox returns `401 Unauthorized` |

Sandbox and production share nothing — not accounts, not data, not keys. The docs
are explicit that even an existing Asaas customer must create a **separate**
sandbox account.

---

## The resources that matter to us

Asaas exposes ~35 resource groups. These are the ones a connector would need:

| Group | Endpoints | Why we care |
|---|---|---|
| **Clientes** | create / list / retrieve / update / remove / restore | the Asaas customer record — the thing whose absence caused the 404 |
| **Cobranças** | create / list / retrieve / status / update / delete | the charge itself; `billingType` selects the rail |
| **Cobranças → Pix QR** | `GET /payments/{id}/pixQrCode` | the `payload` is what you send over WhatsApp |
| **Webhooks** | create / list / retrieve / update / delete | event-driven payment confirmation |
| **Extrato** | statement | reconciliation — the job `sync_occupancy`-style tasks would run |
| **Informações financeiras** | balance | |
| **Assinaturas** | subscriptions | recurring plans (a studio's core product) |
| **Link de pagamentos** | payment links | the equivalent of Angulare's "Link de Pagamento" |
| **Estornos / Chargeback** | refunds, disputes | after-sales |
| **Splits** | split rules and paid splits | multi-recipient — **this is what the tenant has configured** |
| **Transferências / Antecipações** | payouts, receivables advance | |

Also present, not needed now: Notas fiscais, Negativações, Consulta Serasa,
Pix Automático/Recorrente, Subcontas (BaaS), Registro de Recebíveis, Recargas.

---

## Contracts worth pinning down

**Create a customer** — required: **`name`, `cpfCnpj`**. That is all.
(Which is exactly why an incomplete member 404s: Asaas cannot create the customer
without a CPF, so the lookup fails.)

**Create a charge** — required: **`customer`, `billingType`, `value`, `dueDate`**.

```
billingType ∈ { PIX, BOLETO, CREDIT_CARD, DEBIT_CARD, UNDEFINED }
```

`UNDEFINED` lets the payer choose at the checkout page — the rail-selection
pattern Angulare's cart also uses.

**Charge status** — a real state machine, unlike the gateway's single
`not-authorized`:

```
PENDING · AWAITING_RISK_ANALYSIS · AWAITING_CHARGEBACK_REVERSAL
CONFIRMED · RECEIVED · RECEIVED_IN_CASH
OVERDUE · DUNNING_REQUESTED · DUNNING_RECEIVED
REFUND_REQUESTED · REFUND_IN_PROGRESS · REFUNDED
CHARGEBACK_REQUESTED · CHARGEBACK_DISPUTE
```

**Webhook events** — the payment family alone is large and granular:

```
PAYMENT_CREATED · PAYMENT_AWAITING_RISK_ANALYSIS · PAYMENT_APPROVED_BY_RISK_ANALYSIS
PAYMENT_AUTHORIZED · PAYMENT_CONFIRMED · PAYMENT_RECEIVED
PAYMENT_OVERDUE · PAYMENT_DELETED
PAYMENT_REFUNDED · PAYMENT_PARTIALLY_REFUNDED
PAYMENT_CHARGEBACK_REQUESTED · PAYMENT_CHARGEBACK_DISPUTE
PAYMENT_DUNNING_REQUESTED · PAYMENT_DUNNING_RECEIVED
PAYMENT_CHECKOUT_VIEWED · PAYMENT_BANK_SLIP_VIEWED · PAYMENT_BANK_SLIP_CANCELLED
PAYMENT_CREDIT_CARD_CAPTURE_REFUSED · PAYMENT_ANTICIPATED
```

`PAYMENT_CONFIRMED` / `PAYMENT_RECEIVED` are the two that close the loop.

---

## What a skill would look like

Following the `evo` / `angulare` shape — thin client, gated writes, read-first:

```
asaas_check_credentials()          auth + which environment the key belongs to
asaas_customer(...)                find by cpfCnpj / externalReference; create
asaas_charge_create(...)           billingType, value, dueDate → charge
asaas_pix_qr(payment_id)           payload + encodedImage + expirationDate
asaas_charge_status(payment_id)    the real state machine
asaas_charges(...)                 list/filter for reconciliation
asaas_balance() / asaas_statement(...)
asaas_webhook_create/list/delete(...)
```

Writes gated behind `confirm=True`, same convention as the other two.

---

## ⚠️ The caveat that decides scope

**The tenant's Asaas key is held server-side by Angular Pay. We do not have it,
and we should not ask for it casually** — it is the merchant's acquirer
credential, and it can move money.

So this skill does **not** let us take over NUMA's payments tomorrow. What it
does give us:

1. **A correct mental model of the payment path we are debugging.** Already
   earned — see the wrapper table above.
2. **A sandbox to prototype against** — no permission needed, but a real
   person's name, mobile and address are.
3. **The option of a direct integration** if a client ever wants to cut out the
   gateway: same Pix artefacts, one less hop, and errors that say what happened.

That last one is a *product* decision, not a technical one. Worth putting to
Leonardo once he has read this.

---

## Credentials needed

| Environment | What | Where |
|---|---|---|
| Sandbox | one API key | self-service at `sandbox.asaas.com` — **requires a real name, a personal mobile for the activation code, and a full address** |
| Production | one API key | the client's Asaas account (or ours, if we become the merchant) |

Nothing else. No partner programme, no homologation, no sales call.

---

## Sources

- `https://docs.asaas.com/llms.txt` — machine-readable index
- `https://docs.asaas.com/reference/comece-por-aqui.md` — environments, auth header
- `https://docs.asaas.com/reference/criar-novo-cliente.md` — customer schema
- `https://docs.asaas.com/reference/criar-nova-cobranca.md` — charge schema, status enum
- `https://docs.asaas.com/reference/obter-qr-code-para-pagamentos-via-pix.md` — Pix QR response
- `https://docs.asaas.com/docs/webhook-para-cobrancas.md` — webhook event names
- `https://docs.asaas.com/docs/sandbox.md` — sandbox signup
