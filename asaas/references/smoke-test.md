# Asaas sandbox smoke test

One run covers the whole skill: register a payer, create a charge, read the Pix
code, **simulate the payment**, and watch the status flip. Nothing real moves.

First full live run: 2026-10-15 — green end to end (sandbox, Asaas's real API).
This script is how you re-verify in about two minutes.

---

## What you need

| Value | What to use | Why that one |
|---|---|---|
| `ASAAS_API_KEY` | a key from `sandbox.asaas.com` | export it (preferred) or paste it into the script; sandbox and production keys are not interchangeable |
| `name` | **your own full name** | you are already the sandbox account holder, so the payer can be you |
| `cpf_cnpj` | **your own CPF** | same reason — no third party's document goes into a financial account for a test |
| `email` | **your own**, or empty | empty = no e-mail is sent at all — the safest option |
| `mobile_phone` | **your own**, or empty | empty = no SMS is sent at all |
| `value` | `80.00` | small, and it is the price point the gym flows use |
| `external_reference` | `sandbox-smoke-1` | your own marker, so the test data is trivial to find and delete |

### ⚠️ Use your own contact details, not invented ones

Asaas says so explicitly in their sandbox guide:

> *"Evite cadastrar contatos aleatórios ou inválidos, pois as mensagens podem ser
> enviadas durante os testes."*

**The sandbox sends real messages.** A made-up address or phone number means
those messages go to a stranger. Your own details mean any test traffic lands in
your own inbox, where it belongs. Leaving both fields empty sends nothing to
anyone — nothing safer exists.

Set `ASAAS_ENV` to `sandbox` (or leave it — sandbox is the default).

---

## Run it

**Easiest: export, then run.** The script reads `ASAAS_API_KEY`,
`SMOKE_FULL_NAME` and `SMOKE_CPF` from the environment, so no file edit is
needed and the key never lands in a file that gets committed:

```bash
export ASAAS_API_KEY="<your sandbox key>"
export SMOKE_FULL_NAME="Teste Sandbox" SMOKE_CPF="<your or a test CPF>"
python3 smoke_test.py
```

**Or edit the script.** `references/smoke_test.py` has a fill-in block at the
top with `<...>` placeholders, and it refuses to run until they are replaced —
so a forgotten field is a clear message, not a junk request to Asaas.

**Or paste this inline** if you would rather not edit a file:

```bash
export ASAAS_API_KEY="<your sandbox key>"
export ASAAS_ENV=sandbox

python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/path/to/skills/asaas")
from exports import (
    asaas_check_credentials, asaas_charge_by_pix,
    asaas_did_they_pay, asaas_confirm_payment, asaas_balance, asaas_statement,
)

def show(label, res):
    print(f"\n--- {label} ---")
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str)[:1400])

# 0. the handshake, and which environment we are actually on
show("check_credentials", asaas_check_credentials())

# 1-3. payer -> charge -> Pix code, in one call
sale = asaas_charge_by_pix(
    name="<your full name>",
    cpf_cnpj="<your CPF>",
    value=80.00,
    email="<your email>",
    mobile_phone="<your mobile>",
    external_reference="sandbox-smoke-1",
    description="Sandbox smoke test",
    confirm=True,
)
show("charge_by_pix", sale)

payment_id = (sale.get("data") or {}).get("payment_id")
if not payment_id:
    raise SystemExit("no payment_id — read the error above before continuing")

# 4. it should be PENDING: the charge exists, nobody has paid
show("did_they_pay (before)", asaas_did_they_pay(payment_id))

# 5. simulate the payment — sandbox only, and the client enforces that
show("confirm_payment", asaas_confirm_payment(payment_id, confirm=True))

# 6. now it should be settled
show("did_they_pay (after)", asaas_did_they_pay(payment_id))

# 7. and the balance should have moved
show("balance", asaas_balance())
show("statement", asaas_statement(start_date="-1"))
EOF
```

---

## What a good run looks like

| Step | Expected |
|---|---|
| `check_credentials` | `ok: true`, `environment: "sandbox"`, a balance |
| `charge_by_pix` | `ok: true`, a `pix_payload` starting `00020101…`, an expiry |
| `did_they_pay` before | `status: "PENDING"`, `settled: false` |
| `confirm_payment` | `ok: true`, `simulated: true` |
| `did_they_pay` after | `status: "RECEIVED"`, `settled: true` |
| `balance` | non-zero |
| `statement` | two rows for the charge: the receipt (`PAYMENT_RECEIVED`) and the Pix fee (`PAYMENT_FEE`) |
| cleanup | charge kept — Asaas only removes `PENDING`/`OVERDUE` charges |

If `charge_by_pix` fails, the error names the field. The most likely:

- **`cpfCnpj`** — Asaas validates the check digit. A transposed digit is rejected.
- **`invalid_access_token`** — the key is from the other environment. Check
  `asaas_environment()` against where you generated it.
- **Pix QR lag** — a fresh charge's QR can lag its creation by a beat; the
  workflow now retries the read three times before reporting failure.

---

## Then clean up

**Asaas only removes a charge that is still `PENDING` or `OVERDUE`** — a paid or
simulated one answers `invalid_action` and stays:

> *"A cobrança não pode ser removida: só é possível remover cobranças
> pendentes ou vencidas."*

So after a green run the settled charge stays as sandbox residue — findable by
its `external_reference`, mixing with nothing. The script knows the rule and
only attempts the delete when the charge is still removable. The customer also
stays (harmless, and reusable for the next run — a second run reports
`customer_created: false`, which is the idempotency working).

---

## What this proves, and what it does not

**Proves:** the customer contract, the charge contract, the Pix QR read, the
status machine, the sandbox confirm endpoint, balance and statement — end to end,
against Asaas's real API.

**Does not prove:** webhook delivery, boleto, card, subscriptions, splits,
transfers. Those need their own runs. In particular, webhooks need a **publicly
reachable URL**, which is the usual reason that step gets skipped.
