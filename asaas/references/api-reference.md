# Asaas API — reference

Everything here was extracted from Asaas's own machine-readable docs
(`https://docs.asaas.com/reference/llms.txt`, 448 pages) and, where marked,
verified against the live sandbox.

---

## Environments and authentication

| | |
|---|---|
| Sandbox | `https://api-sandbox.asaas.com/v3` |
| Production | `https://api.asaas.com/v3` |
| Header | **`access_token: <key>`** |

Not `Authorization: Bearer`. Asaas answers a wrong header with
`401 invalid_access_token` — the same error as a wrong key, which is worth
knowing before you go hunting for a bad key that was fine.

**Sandbox and production share nothing.** Different accounts, different data,
different keys. A production key sent to the sandbox is `401 Unauthorized`, and
ids are not portable. Almost every "the customer I just created does not exist"
is really "I switched environments between calls".

Sandbox signup is self-service at `sandbox.asaas.com`; approval is automatic when
the required fields are valid. No CNPJ, no contract, no waiting.

**But the signup form is not anonymous.** It requires:

| Field | Note |
|---|---|
| Nome completo | *igual ao documento* — the full legal name |
| Celular | a **personal mobile**; it receives the account activation code |
| CEP, Cidade, Rua, Bairro, Número, Complemento | a full address (complement optional) |

So the account is a real person's, and a real phone has to receive an SMS. No CPF
appears on that screen; a Brazilian financial account almost certainly requires
one somewhere in the flow. Treat this as *no gatekeeper*, not *no data*.

---

## Endpoints used by this skill

| Method | Path | Purpose |
|---|---|---|
| GET | `/customers` | list/search payers |
| POST | `/customers` | create a payer |
| GET | `/customers/{id}` | one payer |
| PUT | `/customers/{id}` | update a payer |
| GET | `/payments` | list/search charges |
| POST | `/payments` | create a charge |
| GET | `/payments/{id}` | one charge |
| GET | `/payments/{id}/status` | just the status |
| DELETE | `/payments/{id}` | delete a charge |
| GET | `/payments/{id}/pixQrCode` | **the Pix QR and copy-and-paste** |
| GET | `/webhooks` | list webhooks |
| POST | `/webhooks` | register a webhook |
| DELETE | `/webhooks/{id}` | remove a webhook |
| GET | `/finance/balance` | account balance |
| GET | `/financialTransactions` | statement |

GET requests must be sent **without a body** — Asaas rejects one that carries it.

The full API is ~35 resource groups. Also present, not wrapped here:
`/subscriptions`, `/paymentLinks`, `/checkouts`, `/transfers`, `/anticipations`,
`/escrow`, `/invoices` (NFS-e), `/pix` (keys, automatic, recurrent),
`/creditBureauReport`, `/negativations`, `/subaccounts`, `/splits`.

---

## Write contracts

### Create a customer

```
POST /customers
```

**Required: `name`, `cpfCnpj`. Nothing else.**

That is the whole reason a member record must be complete before it can be
charged — and the reason an incomplete member produces a 404 somewhere downstream
when a gateway tries to create the payer on your behalf.

| Field | Type | Notes |
|---|---|---|
| `name` | string | **required** |
| `cpfCnpj` | string | **required**; digits only, Asaas rejects punctuation |
| `email` | string | |
| `phone` / `mobilePhone` | string | |
| `address`, `addressNumber`, `complement`, `province`, `postalCode` | string | |
| `externalReference` | string | **your** id — use it, it is the stable handle |
| `notificationDisabled` | boolean | suppress Asaas's own notifications |
| `groupName`, `groupNames` | string / array | customer groups |
| `additionalEmails`, `municipalInscription`, `stateInscription`, `observations` | string | |

### Create a charge

```
POST /payments
```

**Required: `customer`, `billingType`, `value`, `dueDate`.**

| Field | Type | Notes |
|---|---|---|
| `customer` | string | **required** — the Asaas customer **id**, not a CPF |
| `billingType` | enum | **required** — see below |
| `value` | number | **required** — BRL, e.g. `80.0` |
| `dueDate` | string | **required** — `YYYY-MM-DD`; cannot be in the past for boleto |
| `description` | string | |
| `externalReference` | string | your id for the charge |
| `installmentCount`, `totalValue`, `installmentValue` | int/number | instalments |
| `discount`, `interest`, `fine` | object | |
| `split` | array | **splits** — several recipients |
| `callback` | object | |
| `pixAutomaticAuthorizationId` | string | |
| `postalService` | boolean | |

**`billingType` when creating** — only four values are accepted:

```
UNDEFINED  BOLETO  CREDIT_CARD  PIX
```

`UNDEFINED` lets the payer choose on the checkout page.

### Create a webhook

```
POST /webhooks
```

**Required — all seven:** `name`, `url`, `email`, `interrupted`, `enabled`,
`events`, `sendType`.

| Field | Type | Notes |
|---|---|---|
| `name` | string | **required** |
| `url` | string | **required** |
| `email` | string | **required** — where Asaas reports a failing endpoint |
| `interrupted` | boolean | **required** — its own circuit breaker state |
| `enabled` | boolean | **required** |
| `events` | array | **required** — 112 available |
| `sendType` | enum | **required** — `SEQUENTIALLY` \| `NON_SEQUENTIALLY` |
| `authToken` | string | sent back as a header on each delivery |
| `apiVersion` | integer | |

`interrupted` is Asaas's circuit breaker: an endpoint that keeps erroring gets
disabled and the `email` is told. **Registering a webhook without a monitored
mailbox is how you silently stop receiving payment confirmations.**

---

## The Pix QR response

```
GET /payments/{id}/pixQrCode
```

```json
{
  "encodedImage":   "<base64 PNG>",
  "payload":        "00020101021226730014br.gov.bcb.pix2551pix-h.asaas.com/…",
  "expirationDate": "2026-10-15T23:59:59-03:00",
  "description":    ""
}
```

`payload` is the **copy-and-paste string** — what you send a customer in chat.
`encodedImage` is the QR as a base64 PNG if you need to render it.

The charge must have `billingType: PIX`. Asking on a boleto or card charge is a
`400`, not an empty result.

### ⚠️ This is the shape Angular Pay renames

NUMA's payments run through Angular Pay, which proxies Asaas. Its gateway
response renames these fields and adds nothing:

| Asaas | Angular Pay |
|---|---|
| `encodedImage` | `pix_qrcode` |
| `payload` | `pix_copy_paste` |
| `expirationDate` | `pix_expires_at` |

So a failure that surfaces from Angular Pay as a bare `not-authorized`, or as
`Problema ao decodificar resposta asaas: 404`, is an Asaas behaviour underneath.
Reading Asaas's vocabulary is how you find out which.

---

## Enumerations

### Charge status

```
PENDING                        waiting for payment — not a failure
AWAITING_RISK_ANALYSIS         in analysis
CONFIRMED                      paid, not yet credited to the balance
RECEIVED                       credited to the balance
RECEIVED_IN_CASH               confirmed manually
OVERDUE                        past the due date
DUNNING_REQUESTED              dunning requested
DUNNING_RECEIVED               dunning paid
REFUND_REQUESTED               refund requested
REFUND_IN_PROGRESS             refund in progress
REFUNDED                       refunded
CHARGEBACK_REQUESTED           chargeback requested
CHARGEBACK_DISPUTE             chargeback under dispute
AWAITING_CHARGEBACK_REVERSAL   awaiting reversal
```

**Settled** = `CONFIRMED` | `RECEIVED` | `RECEIVED_IN_CASH`. `CONFIRMED`
precedes `RECEIVED` by the settlement delay; both mean the money is ours.

### `billingType` on read

Wider than on create — these two appear only in responses:

```
UNDEFINED  BOLETO  CREDIT_CARD  PIX  DEBIT_CARD  TRANSFER  DEPOSIT
```

### Webhook events

**112 in total.** The payment family is large and granular; these are the ones
that move a sale:

```
PAYMENT_CREATED                PAYMENT_UPDATED
PAYMENT_AWAITING_RISK_ANALYSIS PAYMENT_APPROVED_BY_RISK_ANALYSIS
PAYMENT_REPROVED_BY_RISK_ANALYSIS
PAYMENT_AUTHORIZED             PAYMENT_CONFIRMED
PAYMENT_RECEIVED               PAYMENT_ANTICIPATED
PAYMENT_OVERDUE                PAYMENT_DELETED / PAYMENT_RESTORED
PAYMENT_REFUNDED               PAYMENT_PARTIALLY_REFUNDED
PAYMENT_CHARGEBACK_REQUESTED   PAYMENT_CHARGEBACK_DISPUTE
PAYMENT_AWAITING_CHARGEBACK_REVERSAL
PAYMENT_DUNNING_REQUESTED      PAYMENT_DUNNING_RECEIVED
PAYMENT_CHECKOUT_VIEWED        PAYMENT_CREDIT_CARD_CAPTURE_REFUSED
PAYMENT_BANK_SLIP_VIEWED       PAYMENT_BANK_SLIP_CANCELLED
```

`PAYMENT_CONFIRMED` and `PAYMENT_RECEIVED` are the two that close a sale.

---

## Query parameters

### `GET /customers`

`name`, `email`, `cpfCnpj`, `groupName`, `externalReference`
plus `offset`, `limit`.

`externalReference` is the one to prefer — it is yours, and it is unique.

### `GET /payments`

`customer`, `billingType`, `status`, `subscription`, `installment`,
`externalReference`, `paymentDate`, `pixQrCodeId`, `anticipated`, `anticipable`,
`user`, `checkoutSession`, `customerGroupName`, `invoiceStatus`,
`estimatedCreditDate`, and the range pairs:

```
dateCreated[ge]  dateCreated[le]           dueDate[ge]      dueDate[le]
paymentDate[ge]  paymentDate[le]           estimatedCreditDate[ge]  estimatedCreditDate[le]
```

plus `offset`, `limit`.

### `GET /financialTransactions`

`startDate`, `finishDate`, `order`, plus `offset`, `limit`.

### Pagination

**`offset` + `limit`**, limit max 100. The response carries `totalCount` and
`hasMore`; advance `offset` by `limit`. There is no cursor.

---

## Error format

Asaas returns a **list**, and a `400` can carry several at once:

```json
{
  "errors": [
    {"code": "invalid_value",   "description": "O campo value deve ser informado"},
    {"code": "invalid_dueDate", "description": "A data de vencimento não pode ser inferior à hoje"}
  ]
}
```

Read the whole array — the first entry is not always the one blocking you.

The client flattens this to `"code: description; code: description"` in the
envelope's `error`, and adds a `hint` for the statuses worth explaining:

| Status | Hint |
|---|---|
| 401 | the key is missing, wrong, or from the other environment |
| 403 | authenticated but not allowed for that operation/account |
| 404 | no such resource **in this account** — check the environment |
| 429 | back off and retry; limits are per account and per endpoint |
| 400 + `cpf` in the text | Asaas needs a valid CPF/CNPJ on the customer |
| 400 + `billingType` | must be one of `UNDEFINED`, `BOLETO`, `CREDIT_CARD`, `PIX` |

---

## What was verified, and how

**Against the live sandbox, with a deliberately invalid key:** all eight read
paths (`/customers`, `/customers/{id}`, `/payments`, `/payments/{id}/status`,
`/financialTransactions`, `/finance/balance`, `/webhooks`,
`/payments/{id}/pixQrCode`) returned `401 invalid_access_token` in Asaas's own
error shape. That confirms the base URL resolves, every path exists, the
`access_token` header is being read, and the error parser handles the real
payload.

**Not yet verified live:** the write paths and a successful Pix QR read — those
need a real sandbox key. Everything documented above comes from Asaas's own
OpenAPI fragments for those endpoints, not from guessing.

---

## Sources

- `https://docs.asaas.com/reference/llms.txt` — the full index (448 pages)
- `.../reference/comece-por-aqui.md` — environments, auth header
- `.../reference/criar-novo-cliente.md` — `CustomerSaveRequestDTO`
- `.../reference/criar-nova-cobranca.md` — `PaymentSaveRequestDTO`, status enum
- `.../reference/criar-novo-webhook.md` — `WebhookConfigSaveRequestDTO`, 112 events
- `.../reference/obter-qr-code-para-pagamentos-via-pix.md` — `PaymentPixQrCodeResponseDTO`
- `.../reference/codigos-http-das-respostas.md` — error envelope
- `.../reference/listagem-e-paginacao.md`, `.../rate-e-quota-limit.md`
- `.../docs/sandbox.md` — sandbox signup
