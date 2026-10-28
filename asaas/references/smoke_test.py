#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asaas sandbox smoke test — fill in the block below and run it.

    python3 smoke_test.py

Covers the whole skill end to end: register the payer, create a charge, read the
Pix code, simulate the payment, watch the status flip, read balance and
statement, then clean up. Nothing real moves — it is the sandbox.

Use YOUR OWN details. Asaas warns that the sandbox sends real messages, so an
invented e-mail or phone means test traffic going to a stranger.
"""

import json
import os
import sys

# ═══════════════════════════════════════════════════════════════════════════
#  FILL THESE IN  —  replace everything between the angle brackets
# ═══════════════════════════════════════════════════════════════════════════

ASAAS_API_KEY = os.environ.get("ASAAS_API_KEY") or "<PASTE_YOUR_SANDBOX_API_KEY_HERE>"
#   preferred: export it (`export ASAAS_API_KEY=...`) so the key never lives in
#   this file. Pasting works too — the export wins.
ASAAS_ENV     = os.environ.get("ASAAS_ENV") or "sandbox"   # leave as sandbox

FULL_NAME     = os.environ.get("SMOKE_FULL_NAME") or "<YOUR_FULL_NAME_AS_ON_DOCUMENT>"
#   any name works in sandbox, e.g. "Teste Sandbox"
CPF           = os.environ.get("SMOKE_CPF") or "<YOUR_CPF_DIGITS_ONLY_NO_PUNCTUATION>"
#   best: your own CPF - you are already the sandbox account holder.
#   throwaway: a valid-format one, e.g. 83584053242 / 86568732702 / 46023907814
#   Asaas validates the check digit, so a made-up 11 digits will be rejected.
#   generate more:
#     python3 -c "import random;f=lambda b:(lambda d:[d.append(0 if (s:=sum(x*y for x,y in zip(d,range(len(d)+1,1,-1)))%11)<2 else 11-s) for _ in range(2)] and ''.join(map(str,d)))([int(x) for x in b]);print(f(''.join(random.choice('0123456789') for _ in range(9))))"
EMAIL         = os.environ.get("SMOKE_EMAIL") or ""
#   yours only - Asaas sends real messages during sandbox tests.
#   leave empty and nothing is sent at all (the safest option).
MOBILE        = os.environ.get("SMOKE_MOBILE") or ""
#   yours only, digits with area code. Empty = no SMS.

VALUE         = 80.00                            # BRL; 80 is the gym price point
DESCRIPTION   = "Sandbox smoke test"
REFERENCE     = "sandbox-smoke-1"                # your marker, for cleanup

# ═══════════════════════════════════════════════════════════════════════════
#  Nothing to edit below here.
# ═══════════════════════════════════════════════════════════════════════════

def check_filled():
    """Fail loudly on an unfilled placeholder rather than sending junk to Asaas."""
    missing = []
    if ASAAS_API_KEY.startswith("<"):
        missing.append("ASAAS_API_KEY")
    if FULL_NAME.startswith("<"):
        missing.append("FULL_NAME")
    if CPF.startswith("<"):
        missing.append("CPF")
    if missing:
        print("Fill these in first:")
        for name in missing:
            print(f"  - {name}")
        print("\nOpen this file and replace the <...> placeholders at the top.")
        raise SystemExit(2)


def show(label, res, limit=1400):
    print(f"\n{'=' * 66}\n## {label}\n{'=' * 66}")
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str)[:limit])


def main():
    check_filled()
    os.environ["ASAAS_API_KEY"] = ASAAS_API_KEY
    os.environ["ASAAS_ENV"] = ASAAS_ENV

    here = os.path.dirname(os.path.abspath(__file__))
    skill_root = os.path.dirname(here)          # asaas/references/ -> asaas/
    sys.path.insert(0, skill_root)

    from exports import (  # noqa: E402
        asaas_balance,
        asaas_charge_by_pix,
        asaas_check_credentials,
        asaas_confirm_payment,
        asaas_delete_charge,
        asaas_did_they_pay,
        asaas_environment,
        asaas_statement,
    )

    # ── 0. which environment are we actually on? ────────────────────────────
    show("0. check_credentials", asaas_check_credentials())
    if asaas_environment() != "sandbox":
        print("\n!! This is not sandbox. Stop and fix ASAAS_ENV before continuing.")
        raise SystemExit(3)

    # ── 1-3. payer -> charge -> Pix code, in one call ───────────────────────
    sale = asaas_charge_by_pix(
        name=FULL_NAME,
        cpf_cnpj=CPF,
        value=VALUE,
        email=EMAIL,
        mobile_phone=MOBILE,
        external_reference=REFERENCE,
        description=DESCRIPTION,
        confirm=True,
    )
    show("1. charge_by_pix", sale)

    data = sale.get("data") or {}
    payment_id = data.get("payment_id")
    if not payment_id:
        print("\nNo payment_id — read the error above before going further.")
        raise SystemExit(4)

    print(f"\n  customer_created : {data.get('customer_created')}")
    print(f"  pix_payload      : {str(data.get('pix_payload'))[:60]}…")
    print(f"  pix_expires_at   : {data.get('pix_expiration_date')}")

    # ── 4. it should be PENDING: the charge exists, nobody has paid ─────────
    show("2. did_they_pay  (before payment)", asaas_did_they_pay(payment_id))

    # ── 5. simulate the payment — sandbox only, enforced by the client ──────
    show("3. confirm_payment  (sandbox simulation)",
         asaas_confirm_payment(payment_id, confirm=True))

    # ── 6. now it should be settled ─────────────────────────────────────────
    after = asaas_did_they_pay(payment_id)
    show("4. did_they_pay  (after payment)", after)

    # ── 7. the money should have landed ─────────────────────────────────────
    show("5. balance", asaas_balance())
    show("6. statement", asaas_statement(start_date="-1"))

    # ── 8. clean up ─────────────────────────────────────────────────────────
    # Asaas only removes charges still PENDING/OVERDUE. Ours just went RECEIVED
    # (we simulated it), so it stays as sandbox residue — that is the rule, not
    # a failure. A run that stops before the simulation can delete here.
    status_now = (after.get("data") or {}).get("status")
    if status_now in ("PENDING", "OVERDUE"):
        show("7. delete_charge (cleanup)",
             asaas_delete_charge(payment_id, confirm=True))
    else:
        print(f"\n7. cleanup: the charge is {status_now} — Asaas keeps received")
        print(f"   charges; left as residue, findable by '{REFERENCE}'.")

    # ── verdict ─────────────────────────────────────────────────────────────
    print(f"\n{'=' * 66}\n## RESULT\n{'=' * 66}")
    settled = (after.get("data") or {}).get("settled")
    print(f"  charge created : {'yes' if payment_id else 'no'}")
    print(f"  pix code read  : {'yes' if data.get('pix_payload') else 'no'}")
    print(f"  payment simulated and settled : {'yes' if settled else 'NO'}")
    print("\n  Send this whole output back — it is the verification.")
    return 0 if settled else 5


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        print("\nSMOKE TEST CRASHED — send this back:")
        traceback.print_exc()
        sys.exit(0)
