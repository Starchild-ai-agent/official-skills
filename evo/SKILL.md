---
name: evo
version: 1.0.0
description: |
  EVO (W12 / ABC Evo) gym management: class schedule, member bookings, plans, check-ins, webhooks.

  Use when working with an EVO-run gym or studio — booking or cancelling a class for a member (e.g. "book Ana into Pilates tomorrow at 7am"), checking who is enrolled and how many spots are left, looking up a member by CPF/e-mail/phone, listing plans and a member's contracts, or pulling gym and Wellhub/TotalPass check-ins.
delivery: script
author: starchild
tags: [gym, fitness, evo, w12, abcevo, booking, scheduling, checkin, members, brazil]
metadata:
  starchild:
    emoji: "\U0001F3CB\uFE0F"
    skillKey: evo
    requires:
      env: [EVO_DNS, EVO_API_TOKEN]
user-invocable: true
disable-model-invocation: false
---

# 🏋️ EVO (W12 / ABC Evo)

Gym and studio management for **EVO** (ABC Evo, by W12 — Brazil/LATAM), through
EVO's own public REST API: class agenda, member enrollment/booking, plans and
contracts, check-ins and webhooks.

Everything lives under one gateway: **one function = one intent**, and every
function returns the same envelope, so you never have to unwrap EVO-specific
shapes to know whether a call worked:

```
{"ok": true,  "status": 200, "data": ...}
{"ok": false, "status": 401, "error": "...", "hint": "..."}
```

## Credentials

EVO uses **HTTP Basic**: username = the **gym DNS** used to sign into EVO,
password = a **token** generated inside EVO.

The gym owner creates it at *Configurações ▸ Integrações ▸ card EVO ▸ Tokens ▸
NOVO TOKEN*, ticking the permissions for the endpoints you need (GET = read,
POST/PUT/PATCH/DELETE = write). Tokens last **2 years** and are scoped either to
one branch or, for ADM keys, to many branches (those keys must receive an
explicit `id_branch`).

Collect them with `request_env_input` for `EVO_DNS` and `EVO_API_TOKEN` —
**never ask for credentials in chat**. Then prove the pair works before doing
anything else:

```
evo_check_credentials()   # → branch name + branch groups, or a clear 401 hint
```

API access is an EVO Black feature: **API Plus** is free but capped at 1,000
requests/month and 100/day per branch; **API Pro** is metered (see Gotchas).

## How to Call

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/evo")
from exports import evo_check_credentials, evo_schedule, evo_book_by_name

print(json.dumps(evo_check_credentials(), indent=2, ensure_ascii=False))
print(json.dumps(evo_schedule(date="today"), indent=2, ensure_ascii=False)[:1500])
print(evo_book_by_name(member="Ana Silva", activity="Pilates",
                       date="tomorrow", time="19:00"))
EOF
```

Or through the platform loader (hyphen-free name, but keep the habit):

```python
from core.skill_tools import _modules
evo = _modules["evo"]
evo.evo_spots(id_configuration=111, date="2026-10-09")
```

Standalone CLI, handy while debugging:

```bash
python3 evo/exports.py evo_schedule date=2026-10-09 only_available=true
```

## Functions

### Read — safe to call freely

| Function | Purpose |
|---|---|
| `evo_check_credentials()` | Prove EVO_DNS + EVO_API_TOKEN work; returns branch + groups. |
| `evo_configuration()` / `evo_branches()` | Raw branch settings / branch groups. |
| `evo_schedule(date=None, id_branch=None, only_available=False, id_member=None, show_full_week=False, experimental_class=False, activity_ids=None, audience_ids=None, origin=None, take=None)` | Agenda for a day (`show_full_week=True` → Sun..Sat). |
| `evo_session_detail(id_configuration=None, activity_date=None, id_activity_session=None)` | One session incl. `enrollments[]` and every spot. |
| `evo_find_session(activity=None, date=None, time=None, id_branch=None, only_available=True, id_member=None)` | Resolve "Pilates at 19:00" to one session (or report candidates). |
| `evo_spots(id_configuration, date)` | Taken spot numbers + free seat count. |
| `evo_find_members(name=None, cpf=None, email=None, phone=None, id_member=None, status=None, take=50, skip=0, id_branch=None, show_memberships=False)` | Raw member search. |
| `evo_resolve_member(query)` | One identifier (id/CPF/e-mail/phone/name) → one member, or candidates. |
| `evo_member(id_member, memberships=True, responsibles=False, access_qr_code=False)` | Member profile. |
| `evo_member_services(id_member)` | Services the member's contracts entitle them to. |
| `evo_membership_plans(name=None, active=None, id_branch=None, take=25, skip=0)` | Plan catalogue. |
| `evo_member_memberships(id_member=None, name=None, status=None, take=25, skip=0)` | A member's contracts (active/cancelled/expired/suspended/queued). |
| `evo_my_bookings(id_member, status=None)` | A member's enrollments, with `id_configuration_enroll` for cancelling. |
| `evo_member_sessions(id_member, date_start=None, date_end=None, take=50, skip=0, id_branch=None, activity_ids=None)` | Session history with attendance outcome. |
| `evo_entries(start=None, end=None, id_member=None, ..., take=100, skip=0)` | Raw entry/attendance log. |
| `evo_aggregator_checkins(start, end, id_branch=None, aggregators=None, checkin_branch_ids=None, take=100, skip=0)` | Wellhub/TotalPass check-in report. |
| `evo_turnstiles(id_branch=None, serial_number=None)` | Turnstiles/door controllers. |
| `evo_api_usage()` | API Pro hits/cost for this token this month. |

### Write — mutate the gym

| Function | Purpose |
|---|---|
| `evo_book_by_name(member, activity, date=None, time=None, slot_number=None, id_branch=None, origin=None)` | **Preferred.** "Book Ana into Pilates tomorrow 19:00" — resolves member + session, books, verifies. |
| `evo_book(id_member, id_configuration, activity_date, slot_number=None, origin=None, verify=True)` | Book when you already hold the ids. |
| `evo_cancel(id_member, id_configuration=None, id_configuration_enroll=None, id_configuration_participation=None, id_branch=None, verify=True)` | Cancel an enrollment; resolves the enrollment id for you when given `id_configuration`. |
| `evo_set_attendance(status, id_member=None, id_prospect=None, id_configuration=None, activity_date=None, id_activity_session=None, id_branch=None)` | Mark attending / absent / justified-absent. |
| `evo_authorize_entry(id_turnstile, person_type=None, record_id=None, device=None, climate_id=None, temperature=None, id_manual_entry=None)` | Authorize one turnstile entry. |
| `evo_webhooks()` / `evo_webhook_create(event_type, url_callback, headers=None, filters=None)` / `evo_webhook_delete(id_webhook)` | Manage webhooks. |

`date` accepts `"2026-10-09"`, `"09/10/2026"`, `"today"/"hoje"`,
`"tomorrow"/"amanhã"`, `"yesterday"`, or a day offset like `"+3"`.

## Workflows

### "What's on today?" (read-only)

```python
evo_schedule(date="today", only_available=True)
```
Each session carries `name`, `start`/`end`, `capacity`, `occupancy`,
`available`, `instructor`, `status`, and `spots[]` when the class uses a spot
map. Narrow with `evo_find_session(activity="Spinning", date="today", time="19:00")`.

### Booking a member (the common case)

```python
evo_book_by_name(member="123.456.789-09", activity="Pilates",
                 date="tomorrow", time="19:00")
```

It resolves the member (CPF beats e-mail/phone beats name), resolves the
session, POSTs the enrollment, then **re-reads the session to confirm the member
is actually in it**. A class that is full, outside its booking window, or beyond
the member's entitlement comes back as `ok: false` with an explanation rather
than a false success.

Classes with a spot map need a seat: call `evo_spots(id_configuration, date)`
first and pass `slot_number`.

### Cancelling

```python
evo_cancel(id_member=5001, id_configuration=111)        # enrollment id resolved for you
evo_cancel(id_member=5001, id_configuration_enroll="abc-123")   # or explicit
```
Read `evo_my_bookings(id_member)` if you need the ids up front.

### Entitlement before booking

```python
m = evo_resolve_member("Ana Silva")["data"]["member"]
evo_member_memberships(id_member=m["id_member"], status="active")
evo_member_services(id_member=m["id_member"])
```

### Check-in picture

```python
evo_aggregator_checkins(start="2026-10-01", end="2026-10-07")   # Wellhub/TotalPass
evo_entries(start="2026-10-07", end="2026-10-07", take=200)     # raw entries
```

### Watching for changes

```python
evo_webhook_create("NewSale", "https://my.app/evo/hook",
                   headers={"Authorization": "Bearer s3cr3t"})
evo_webhooks()
```

### Budget check (EVO charges per request on API Pro)

```python
evo_api_usage()   # hits + cost for daytime/nighttime, plus the configured cap
```

## Key Facts / Gotchas

- **Read the write response, then verify.** EVO answers `{"result": "..."}` for a
  booking whether or not the member really ended up enrolled. The `*_book*`
  functions re-read the session and report `confirmed`; treat `ok: false` there
  as "did not happen", not as a network error.
- **A class occurrence is `id_configuration` + `activity_date`**, never a session
  id. `id_activity_session` works only where the endpoint accepts it.
- **Free seats = `capacity - ocupation`** (EVO spells it `ocupation`).
- **No sandbox.** EVO's "Testar"/Apidog runner hits production data. Prefer
  read-only calls while exploring, and run heavy reads between 01:00–06:00.
- **Quotas bite quietly**: API Plus is 1,000/month and 100/day per branch; when
  it runs out you get a `401` whose text mentions the daily limit. API Pro is
  metered (daytime R$2.72/100 req, nighttime R$1.36/100 req, R$39.90 monthly
  minimum) with a cost cap that pauses the key. Rate limits are 5 req/s and
  40 req/min per IP, 10,000 req/h per token, 20,000 req/h per gym DNS.
- **Per-endpoint permissions**: a token can read members and still be denied the
  agenda. A `401 Unauthorized` on one call while others work means "regenerate
  the token with that permission ticked" — not "the credentials are wrong".
- **Aggregator traffic bypasses this API.** Wellhub/TotalPass bookings and
  check-ins are configured in each aggregator's per-branch card inside EVO; the
  API exposes the *report* (`evo_aggregator_checkins`) and the raw entry log.
- `origin` (`EOrigemAgendamento`) and `EStatusAtividade` value labels are not
  published — pass through what EVO's integration team gives you, and read the
  accompanying `statusName` string when you need something human.
- Webhook `headers` must be sent as `[{nome, valor}]` on the wire; this skill
  accepts `{"Name": "value"}` and converts. Callbacks must be HTTPS.
- `DELETE`/`PUT`/`PATCH` calls do not go through the platform HTTP proxy (it
  only exposes GET/POST); they use the EVO Basic credentials directly.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `missing EVO credential(s)` | Env not set | `request_env_input` for `EVO_DNS` + `EVO_API_TOKEN` |
| `401 Unauthorized` | Wrong DNS/token, or missing permission for that endpoint | `evo_check_credentials()`; regenerate the token ticking that endpoint |
| `401 … Daily request limit reached` | API Plus quota exhausted | Wait for the next period, or upgrade to API Pro |
| `401 … API_COST_LIMIT_REACHED` | API Pro cost cap hit | Raise the cap in EVO or wait for the new billing period |
| `book` returns `confirmed: false` | Class full / outside booking window / no entitlement | `evo_spots()`, `evo_member_services()` |
| `no unique session matched` | Ambiguous or wrong date | Pass `time`, widen `date`, or use `evo_schedule` and pick explicitly |
| `no unique member matched` | Name matched several people | Use CPF or e-mail instead of the name |
| `429` | Rate limit | Back off ~1s (minute cap: 1min); 00:00–05:59 is exempt from the hourly caps |

## References

- `references/api-reference.md` — curated endpoint/enum index, quotas, and the
  parts of EVO's 134-path spec this skill does not wrap (billing, workouts,
  fitness assessments, prospects, appointments).
- Full spec: `https://evo-integracao.w12app.com.br/swagger/v1/swagger.json`
- Human docs: `https://api.abcevo.com/`