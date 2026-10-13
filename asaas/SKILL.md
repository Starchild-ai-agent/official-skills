---
name: asaas
version: 1.0.0
description: |
  Asaas payments (Brazil): customers, Pix and boleto charges, the Pix copy-and-paste
  code, charge status, webhooks, balance and statement.

  Use when charging a Brazilian customer, generating a Pix code to send in chat,
  asking whether a charge was actually paid and why not, reconciling received
  payments, or registering a webhook for payment events. Also the right place to
  look when a payment fails behind a gateway — Asaas is what several Brazilian
  gateways proxy, so its error vocabulary explains theirs.
delivery: script
author: starchild
tags: [payments, brazil, pix, boleto, asaas, charges, cobranca, webhooks, reconciliation, fintech]
metadata:
  starchild:
    emoji: "\U0001F4B3"
    skillKey: asaas
    requires:
      env: [ASAAS_API_KEY]
user-invocable: true
disable-model-invocation: false
---

# 💳 Asaas

Payments for Brazil: register the payer, create a charge, hand back a **Pix
copy-and-paste string**, and find out what actually happened to it.

Asaas is the acquirer behind a number of Brazilian payment gateways — including
Angular Pay, which several gym platforms use. When one of those gateways answers
`not-authorized` with no reason, the real reason is usually an Asaas one. This
skill speaks Asaas directly, so errors say what they mean.

Everything here was built from Asaas's own machine-readable docs
(`docs.asaas.com/reference/llms.txt`, 448 pages) and the transport was verified
against the live sandbox. See `references/api-reference.md` for the contracts.

## Credentials

One env var, collected with `request_env_input` — never ask for it in chat:

| Var | What it is |
|---|---|
| `ASAAS_API_KEY` | an API key from the Asaas dashboard |
| `ASAAS_ENV` | optional — `sandbox` (default) or `production` |
| `ASAAS_BASE_URL` | optional override; wins over `ASAAS_ENV` |

**It defaults to sandbox on purpose.** Pointing at production should be something
someone typed, not something someone forgot to change.

A sandbox key is self-service: create an account at `sandbox.asaas.com` and
generate one. **No CNPJ, no contract, no approval queue.**

⚠️ **But the signup form is not anonymous** — it asks for a full name as on the
document, a personal mobile that receives the activation code, and a full address
(CEP, city, street, neighbourhood, number). So it needs a real person's details
and a phone that can receive an SMS. Tell the user that before you ask them to
sign up, and make sure they are the one volunteering their own data.

Sandbox and production share nothing — different accounts, different data,
different keys, and a key from one is `401` on the other.

Then prove the handshake before anything else:

```
asaas_check_credentials()
# -> {"environment": "sandbox", "base_url": "...", "balance": 0}
```

## How to Call

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/asaas")
from exports import asaas_check_credentials, asaas_charge_by_pix

print(json.dumps(asaas_check_credentials(), indent=2, ensure_ascii=False))
print(json.dumps(asaas_charge_by_pix("Maria Silva", "12345678909", 80.0,
                                     email="maria@example.com"), indent=2)[:1200])
EOF
```

Or through the platform loader:

```python
from core.skill_tools import _modules
asaas = _modules["asaas"]
asaas.asaas_did_they_pay("pay_1234567890")
```

Standalone CLI while debugging:

```bash
python3 asaas/exports.py asaas_balance
python3 asaas/exports.py asaas_find_customers cpf_cnpj=12345678909
```

Every function returns `{"ok": True, "data": ...}` or
`{"ok": False, "status": ..., "error": ..., "hint": ...}`.

## Functions

### Auth / environment

| Function | Purpose |
|---|---|
| `asaas_check_credentials()` | Confirm the key works; report environment, base URL and balance. |
| `asaas_environment()` | `"sandbox"` or `"production"`, as resolved from the env. |

### Customers

| Function | Purpose |
|---|---|
| `asaas_find_customers(name=None, email=None, cpf_cnpj=None, external_reference=None, take=50, skip=0)` | Search payers. `external_reference` is the one to prefer — it is yours, and unique. |
| `asaas_customer(customer_id)` | One customer by Asaas id. |
| `asaas_find_or_create_customer(name, cpf_cnpj, email=None, mobile_phone=None, external_reference=None, confirm=False)` | **WRITE** — get the payer for this CPF/CNPJ, creating it if absent. Idempotent; this is the entry point that prevents the "customer not found" wall. |
| `asaas_update_customer(customer_id, …, confirm=False)` | **WRITE** — update e-mail / phone / external reference. |

### Charges

| Function | Purpose |
|---|---|
| `asaas_charges(customer=None, status=None, billing_type=None, external_reference=None, due_date_from=None, due_date_to=None, take=50, skip=0)` | List charges. `customer` is the Asaas id, not a CPF. |
| `asaas_charge(payment_id)` | One charge in full. |
| `asaas_charge_status(payment_id)` | Just the status, plus a `settled` boolean — cheap, and usually the actual question. |
| `asaas_create_charge(customer, value, due_date=None, billing_type="PIX", description=None, external_reference=None, confirm=False)` | **WRITE** — create a charge. `due_date` defaults to today. |
| `asaas_delete_charge(payment_id, confirm=False)` | **WRITE** — delete a charge (restorable for a while). |

### Pix

| Function | Purpose |
|---|---|
| `asaas_pix_qr_code(payment_id)` | The QR image (base64) **and the copy-and-paste string**. The charge must be `billingType: PIX`. |

### Webhooks

| Function | Purpose |
|---|---|
| `asaas_webhooks()` | Webhooks registered on this account. |
| `asaas_create_webhook(name, url, email, events=None, send_type="SEQUENTIALLY", auth_token=None, enabled=True, interrupted=False, confirm=False)` | **WRITE** — subscribe a URL. `events` defaults to the core payment set. |
| `asaas_delete_webhook(webhook_id, confirm=False)` | **WRITE** — remove it. Notifications stop immediately. |

### Finance

| Function | Purpose |
|---|---|
| `asaas_balance()` | Account balance, per bucket (available / blocked / scheduled). |
| `asaas_statement(start_date=None, finish_date=None, take=100, skip=0)` | Financial transactions — the reconciliation feed. Defaults to the last 30 days. |

### Workflows

| Function | Purpose |
|---|---|
| **`asaas_charge_by_pix(name, cpf_cnpj, value, email=None, mobile_phone=None, external_reference=None, description=None, due_date=None, confirm=False)`** | **WRITE** — the whole Pix sale in one call: ensure the payer → create the charge → read the QR. |
| `asaas_did_they_pay(payment_id)` | One-line verdict plus what to do next. |

## Workflows

### Charge someone by Pix (the one-call flow)

```python
asaas_charge_by_pix(
    name="Maria Silva",
    cpf_cnpj="12345678909",
    value=80.0,
    email="maria@example.com",
    external_reference="member-2246",   # your id, so you can find them next month
    confirm=True,
)
# -> {"payment_id": "pay_…", "customer_id": "cus_…", "customer_created": False,
#     "value": 80.0, "status": "PENDING",
#     "pix_payload": "00020101021226…63045E7A",   <- send this in chat
#     "pix_expiration_date": "2026-10-15T23:59:59-03:00",
#     "next": "Send `pix_payload` to the payer. Then poll charge_status(…)"}
```

Without `confirm=True` it returns the plan and writes nothing.

`pix_payload` is a **plain string** the customer pastes into their bank app —
unlike the card rail, whose artefact is a hosted page that cannot be forwarded as
text. That asymmetry is why Pix is the rail to prefer when the conversation
happens in a chat app.

### Did they pay?

```python
asaas_did_they_pay("pay_1234567890")
# -> {"status": "RECEIVED", "settled": True, "next": "settled — book the sale"}
```

`settled` is the machine-readable answer. `CONFIRMED` means paid but not yet
credited; `RECEIVED` means in the balance. Both are `settled: True`.

Unlike a gateway that collapses everything into one `not-authorized`, Asaas has a
real state machine — so "why did this fail" has an answer:

| Status | Means |
|---|---|
| `PENDING` | waiting for payment — **not** a failure |
| `AWAITING_RISK_ANALYSIS` | in analysis |
| `CONFIRMED` / `RECEIVED` / `RECEIVED_IN_CASH` | settled |
| `OVERDUE` | past the due date; send a fresh charge if they still want it |
| `REFUND_REQUESTED` / `REFUND_IN_PROGRESS` / `REFUNDED` | reversed |
| `CHARGEBACK_REQUESTED` / `CHARGEBACK_DISPUTE` | disputed — needs a human |
| `DUNNING_REQUESTED` / `DUNNING_RECEIVED` | dunning |

### Reconciling a day's takings

```python
asaas_statement(start_date="-7", finish_date="today")
# -> transactions with type, date, value, balance and the payment_id they came from
```

This is the only way to catch things no payment event describes: fees, transfers,
anticipations and manual adjustments. Run it on a schedule.

### Subscribing to payment events

```python
asaas_create_webhook(
    name="NUMA payments",
    url="https://…/webhooks/asaas",
    email="ops@example.com",       # where Asaas reports a failing endpoint
    confirm=True,
)
```

**All seven fields are required** — `name`, `url`, `email`, `interrupted`,
`enabled`, `events`, `sendType`. `email` is not decoration: Asaas trips its own
circuit breaker on an endpoint that keeps erroring and tells that address.
Registering a webhook without a monitored mailbox is how you silently stop
receiving payment confirmations.

Asaas exposes **112 events**; the default here is the seven that move a sale
(`PAYMENT_CREATED`, `PAYMENT_CONFIRMED`, `PAYMENT_RECEIVED`, `PAYMENT_OVERDUE`,
`PAYMENT_REFUNDED`, and the two chargeback ones). Pass `events=[…]` for more.

## Key Facts / Gotchas

- **`access_token: <key>` — not `Authorization: Bearer`.** Wrong header gives
  `401 invalid_access_token`.
- **Sandbox and production are different universes.** A `404` on a customer you
  just created almost always means you switched `ASAAS_ENV` between calls, or the
  key and the base URL disagree. Ids do not carry across.
- **A charge references a customer id, never a CPF.** Creating a charge for an
  unregistered payer fails. `asaas_find_or_create_customer` exists so you never
  hit that — call it, or use `asaas_charge_by_pix` which does.
- **`cpfCnpj` is one of only two required customer fields** (`name` and
  `cpfCnpj`). There is no way to charge a person without a valid document. If a
  member record has no CPF, fix that first — this is a hard requirement, not a
  preference.
- **A Pix QR only exists for a `PIX` charge.** Asking for one on a boleto or card
  charge is a `400`, not an empty result.
- **`value` is in BRL**, a number not a string (`80.0`, not `"80,00"`).
- **`dueDate` cannot be in the past** for boleto. Pix settles immediately, so its
  due date is bookkeeping.
- **Pagination is `offset` + `limit`** (limit max 100), and the response tells you
  `hasMore` and `totalCount`. There is no cursor.
- **A `400` can carry several errors at once** — read the whole `errors` array;
  the first one is not always the one blocking you.
- **Rate limits are per account and per endpoint.** On `429`, back off and retry;
  do not loop.

## References

- `references/api-reference.md` — endpoint index, request contracts, enums, and
  the evidence behind each claim here.
- Asaas docs index: `https://docs.asaas.com/reference/llms.txt` (448 pages,
  machine-readable).
- `docs/integrations/asaas.md` in the skills repo — why this skill exists, and
  the finding that Angular Pay is a thin wrapper over Asaas.
