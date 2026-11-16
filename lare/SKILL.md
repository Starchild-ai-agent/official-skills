---
name: lare
version: 1.0.0
description: |
  Lare studio operations platform (system of record): schedule, class seats,
  bookings, waitlist, attendance/check-in, members, credit ledger, front-desk
  sales/Pix payment links, and financial/occupancy reports.
  Use for any studio running on Lare to query real-time classes, member credits,
  bookings, orders, or execute bookings/cancellations/check-ins/sales.
delivery: script
author: starchild
tags: [gym, fitness, studio, lare, booking, attendance, credits, pos, pix]
metadata:
  starchild:
    skillKey: lare
    requires:
      env: [LARE_API_URL, LARE_TENANT_CODE, LARE_TENANT_API_KEY]
user-invocable: true
disable-model-invocation: false
---

# Lare Studio Operations

Real-time read & write operations against Lare (`/api/v1/*`) scoped strictly to
this studio (`LARE_TENANT_CODE`) using the per-tenant key (`LARE_TENANT_API_KEY`).

## How to Call

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/lare")
from exports import lare_sessions, lare_find_members

print(json.dumps(lare_sessions(), indent=2, ensure_ascii=False)[:1500])
print(json.dumps(lare_find_members("Ana"), indent=2, ensure_ascii=False)[:1500])
EOF
```

Every function returns `{"ok": True, "data": ...}` or `{"ok": False, "status": ..., "error": ...}`.

## Functions

- `lare_sessions(date_value=None)` — List sessions for a day (`YYYY-MM-DD`, defaults to today)
- `lare_session_detail(session_token)` — Seats, capacity, and booking roster for a session
- `lare_find_members(search="", page=1)` — Search members with credit balances
- `lare_member_detail(member_id)` — Profile, credits, bookings, and orders for one member
- `lare_book(session_token, user_id, spot=None)` — Book a member into a session
- `lare_waitlist(session_token, user_id)` — Add a member to a session waitlist
- `lare_cancel_booking(booking_token)` — Cancel an active booking
- `lare_check_in(booking_token)` / `lare_no_show(booking_token)` — Attendance updates
- `lare_products()` — Catalog products and payment methods
- `lare_create_payment_link(member_id, product_id, mode="pix")` — Add product to cart and checkout (`pix` | `link` | `frontdesk`)
- `lare_orders(status=None, page=1)` — List studio orders
- `lare_reports_sales(date_from=None, date_to=None)` — Sales summary report
