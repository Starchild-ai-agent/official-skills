# EVO API reference (curated)

Base URL: `https://evo-integracao-api.w12app.com.br`
Spec: `https://evo-integracao.w12app.com.br/swagger/v1/swagger.json` (OpenAPI 3.0.1, 134 paths)
Docs: `https://api.abcevo.com/`

Auth: **HTTP Basic** — username = gym DNS, password = token.
Tokens: 2-year TTL, created at *Configuracoes > Integracoes > card EVO > Tokens*.
Scope: single-branch keys only see their branch; **multi-branch (ADM) keys only
work on calls that take `idBranch`** — pass it explicitly.
Permissions are per endpoint: GET = read, POST/PUT/PATCH/DELETE = write.

Errors come back as JSON. Read/query failures use `{"mensagens": ["..."]}`
(`HttpResponseError`); auth/quota failures use `{"status": 401, "error": "..."}`.

## Enums

| Enum | Values |
|---|---|
| Member status (`/api/v2/members?status=`) | 1 Active, 2 Inactive |
| `EStatusAtividadeSessao` (attendance) | 0 Attending, 1 Absent, 2 Justified absence |
| MemberMembership status | 1 Active, 2 Canceled, 3 Expired, 4 Suspended, 5 In queue |
| Contract status (per member contract) | 1 Active, 2 Blocked, 3 Canceled, 5 On leave, 6 Pending payment, 7 Finished, 8 Awaiting start |
| `EOrigemAgendamento` | 0..18 — labels are **not published**; pass what EVO's integration team gives you |
| `EStatusAtividade` | 0..15 — labels not published; use the sibling `statusName` string |

## Wrapped by this skill

### Schedule / booking

| Method | Path | Key params |
|---|---|---|
| GET | `/api/v1/activities/schedule` | `date`, `idBranch`, `onlyAvailables`, `idMember`, `showFullWeek`, `idActivities` (csv), `idAudiences` (csv), `origin`, `take` |
| GET | `/api/v1/activities/schedule/detail` | `idConfiguration` + `activityDate` (yyyy-MM-dd), **or** `idActivitySession` |
| GET | `/api/v1/activities/list-unavailable-spots` | `idConfiguration`, `date` → `{unavailableSpots: [int]}` |
| POST | `/api/v1/activities/schedule/enroll` | `idConfiguration`, `activityDate`, `slotNumber`, `idMember` or `idProspect`, `origin` |
| POST | `/api/v2/activities/booking` | same as above (v2 twin; identical params) |
| POST | `/api/v1/activities/schedule/enroll/change-status` | `status` 0/1/2, `idMember`, `idConfiguration`+`activityDate` or `idActivitySession`, `idBranch` |
| DELETE | `/api/v1/activities/enrollment` | `idMember`, `idConfigurationParticipation`, `idBranch` |
| DELETE | `/api/v2/activities/enroll` | `idMember`, `idConfigurationEnroll`, `idBranch` |
| GET | `/api/v2/activities/enroll/member` | `idMember`, `status` |
| GET | `/api/v2/activities/member/sessions` | `idMember`, `dateStart`, `dateEnd`, `idActivities`, `take`, `skip` |
| POST | `/api/v1/activities/schedule/experimental-class` | trial class + enroll in one shot |
| GET | `/api/v1/activities/schedule/by-service-or-membership` | `idService` / `idMembership` |

`AtividadeAgendaApiViewModel` highlights: `idConfiguration`, `idActivity`,
`idAtividadeSessao`, `name`, `activityDate`, `startTime`, `endTime`, `capacity`,
`ocupation` (sic), `allowChoosingSpot`, `spots[] {number, available, nameSpot}`,
`bookingStartTime`, `bookingEndTime`, `status`, `statusName`, `memberStatus`.

`MatriculaDetalhesApiV2ViewModel` (what `my_bookings` returns) highlights:
`idConfigurationEnroll`, `idConfiguration`, `activityName`, `activityGroup`,
`enrollDate`, `startDate`, `endDate`, `weekDay`, `startTime`, `endTime`,
`spotNumber`, `status`.

### Members / contracts

| Method | Path | Key params |
|---|---|---|
| GET | `/api/v2/members` | `name`, `document` (CPF), `email`, `phone`, `status`, `idsMembers` (csv), `idBranch`, `take` (≤10000), `skip`, `showMemberships`, `showsResponsibles`, `tokenGympass`, `codeTotalpass`, `updateDate` |
| GET | `/api/v2/members/{idMember}` | `showMemberships`, `showsResponsibles`, `showAccessControlQRcode` |
| GET | `/api/v2/members/active-members` | `idBranch` (0/null = all, multi-branch key) |
| GET | `/api/v1/members/basic` | `idMember`, `document`, `email`, `phone` |
| GET | `/api/v1/members/services` | `idMember` → entitled services |
| GET | `/api/v3/membership` | `name`, `active`, `showActivitiesGroups`, `showAccessBranches` |
| GET | `/api/v3/membermembership` | `idMember`, `memberName`, `statusMemberMembership`, `contractType` |
| GET | `/api/v1/membermembership/{idMemberMembership}` | single contract summary |
| POST | `/api/v1/membermembership/cancellation` | cancel a contract |
| POST | `/api/v1/membermembership/cancellation/scheduled-revert` | undo a scheduled cancellation |
| PATCH | `/api/v1/members/update-member-data/{idMember}` | basic member fields |
| PUT | `/api/v1/members/block-unblock/{idMember}` | block/unblock access |

`MembersApiViewModel` highlights: `idMember`, `firstName`/`lastName`,
`registerName`/`registerLastName`, `cpf`, `document`, `contacts[] {description}`,
`status` (string "1"/"2"), `membershipStatus`, `accessBlocked`, `blockedReason`,
`lastAccessDate`, `registerDate`, `gympassId`, `codeTotalpass`, `memberships[]`.

### Check-ins / access

| Method | Path | Key params |
|---|---|---|
| GET | `/api/v1/entries` | `registerDateStart`, `registerDateEnd`, `idMember`, `IdEntry` |
| GET | `/api/v1/management/aggregators/checkins/search` | `DtStart`, `DtEnd`, `IdBranch`, `Aggregators[]`, `CheckinBranchIds[]` |
| GET | `/api/v2/accessControl/turnstiles` | `idBranch`, `serialNumber` |
| POST | `/api/v2/accessControl/entryAuthorize` | body `{id, personType, device, idTurnstile, idManualEntry, temperature, climateId}` |
| POST | `/api/v2/accessControl/insertManualLiberation` | manual release |
| PUT | `/api/v2/accessControl/turnstiles` | set turnstile serial |
| GET | `/api/v2/accessControl/facial-photo` | `idPhoto` from the `FacialPhotoRegistered` webhook |
| GET | `/api/v1/configuration/api-usage` | API Pro hits/cost for the key's scope |

### Webhooks

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/webhook` | body `{idBranch, eventType, urlCallback, headers: [{nome, valor}], filters: [{filterType, value}]}`; `urlCallback` **must be https** |
| GET | `/api/v2/webhook` | list |
| DELETE | `/api/v1/webhook` | `IdWebhook` |

`eventType` values are only partly published (`NewSale`, `CreateMember`,
`AlterMember`, `NewInvoice`, ...). The `W12UtilsWebhookViewModel` schema is
referenced by the spec but **absent from the published components**, and the
full `eventType` enum is not published — ask EVO support for the list.

### Configuration

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/configuration` | branch settings — cheapest credential smoke test |
| GET | `/api/v1/configuration/group-branches` | branch groups (ADM keys) |
| GET | `/api/v1/configuration/occupation` | occupancy/area catalogue |

## Documented but NOT wrapped here

Billing (`/api/v1/receivables*`, `/api/v1/payables`, `/api/v2/invoices/get-invoices`,
`/api/v1/carts`, `/api/v2/sales`, `/api/v1/voucher`, `/api/v1/bank-accounts`,
`/api/v1/pix/qr-code`), workouts (`/api/v1|v2/workout/*`), fitness assessments
(`/api/v2/fitness-assessment/*`), prospects (`/api/v1|v2/prospects*`), employees
(`/api/v1|v2/employees`), appointments (`/api/v1/appointment*`,
`/api/v1/appointments*`), notifications and push
(`/api/v1/notifications`, `/api/v1/members/push`), parking
(`/api/v1/parking/*`). Read them from the spec URL above — the shapes are all
there.

## Quotas and rate limits

| Limit | Value |
|---|---|
| API Plus (free, EVO Black) | 1,000 req/month, 100 req/day **per branch**; reset at period rollover |
| API Pro (paid) | min. monthly billing R$ 39.90; first 1,000 monthly requests free; daytime 06:00–23:59 R$ 2.72 / 100 req, nighttime 00:00–05:59 R$ 1.36 / 100 req; configurable cost cap (90% alert, 100% key pause) |
| Per IP | 5 req/s, 40 req/min (API Pro is exempt from the per-minute cap) |
| Per token | 10,000 req/h |
| Per gym DNS | 20,000 req/h |
| Exemption window | 00:00–05:59 lifts the hourly/DNS caps (per-second/per-minute still apply) |

Over-quota errors:
- `401 {"error": "Daily request limit reached. Upgrade to API Pro to get unlimited requests."}`
- `401` with `API_COST_LIMIT_REACHED` when the API Pro cost cap is hit (the key is paused)
- `429` on rate limits (`{"status":429, ...}`)

## Gotchas

- **No sandbox.** EVO's docs call the Apidog/Swagger "Testar" runner a sandbox,
  but the same docs state the API consumes production data. Run heavy reads
  between 01:00–06:00 and never experiment on a live class roster.
- The class key is **`idConfiguration` + `activityDate`** — not a session id.
  Use `idActivitySession` only where the endpoint accepts it.
- Spot booking (`allowChoosingSpot`) requires `slotNumber`; call
  `/api/v1/activities/list-unavailable-spots` to see what is taken.
- `ocupation` is EVO's spelling; free seats = `capacity - ocupation`.
- Aggregator (Wellhub/TotalPass) booking and check-in traffic does **not** flow
  through this API — it goes through each aggregator's per-branch integration
  card. The API gives you the aggregator check-in *report* and the raw entry log.
- `DELETE` and `PATCH`/`PUT` calls in this skill bypass the platform HTTP proxy
  (the proxy exposes GET/POST only); they used `urllib`/`requests` directly with
  the EVO Basic credentials.