---
name: rootdata
version: 1.0.0
description: RootData Web3 intelligence API for crypto projects, investors, funding rounds, trending rankings, and personnel job changes. Use for project/investor research and dealflow tracking.
delivery: script
metadata:
  starchild:
    emoji: "🧩"
    skillKey: rootdata
    requires:
      env:
        - ROOTDATA_SKILL_KEY
user-invocable: false
disable-model-invocation: false
---

# RootData

RootData Web3 intelligence API for:
- project / investor / person search
- project detail lookup
- recent funding rounds
- trending projects (daily / weekly)
- personnel job changes

## Script Usage

This is a script-mode skill. Use from a `bash` block:

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/rootdata")
from exports import rd_search, rd_project_detail, rd_funding_rounds

print(rd_search(query="berachain")[:2])
print(rd_project_detail(project_id=3375, include_investors=True).get("project_name"))
print(rd_funding_rounds(page=1, page_size=5).get("total"))
EOF
```

Available functions in `exports.py`:
`rd_init_key`, `rd_search`, `rd_id_map`, `rd_project_detail`, `rd_funding_rounds`, `rd_hot_index`, `rd_job_changes`.

## First-Time Setup (auto-init key)

RootData provides an anonymous low-privilege key via init API.

- Env var used by this skill: `ROOTDATA_SKILL_KEY`
- If the var is missing, call `rd_init_key()` once and persist it to your environment.

Init endpoint:
- `POST https://api.rootdata.com/open/skill/init`
- body: `{}`
- returns `api_key`

## Functions

### `rd_init_key()`
Get a new anonymous API key from RootData init endpoint.

Returns dict:
- `api_key`
- `message`

### `rd_search(query, precise_x_search=False, language='en')`
Search projects / investors / people by keyword.

Endpoint: `POST /open/skill/ser_inv`

Body:
- `query`: string
- `precise_x_search`: bool

Returns list of entities. Common fields:
- `id`
- `type` (1=project, 2=institution, 3=person)
- `name`
- `one_liner`
- `introduce`
- `rootdataurl`

### `rd_id_map(type, language='en')`
Get all IDs by type.

Endpoint: `POST /open/skill/id_map`

Body:
- `type`: 1 (project) | 2 (institution) | 3 (person)

Returns list with `id`, `name`.

### `rd_project_detail(project_id=None, contract_address=None, include_investors=True, language='en')`
Get project detail by project_id or contract address.

Endpoint: `POST /open/skill/get_item`

Body (one of):
- `project_id`: int
- `contract_address`: string
- `include_investors`: bool

Returns project detail (fields vary), often including:
- `project_id`, `project_name`, `token_symbol`
- `one_liner`, `description`, `tags`
- `contracts`, `social_media`
- `total_funding`
- `investors` (when requested)

### `rd_funding_rounds(page=1, page_size=20, project_id=None, start_time=None, end_time=None, min_amount=None, max_amount=None, language='en')`
Get funding round list with filters.

Endpoint: `POST /open/skill/get_fac`

Notes:
- data covers past 365 days
- max 3 investors per round
- `valuation` field removed upstream

Returns dict:
- `total`
- `items` (list)

### `rd_hot_index(days=1, language='en')`
Get trending project ranking.

Endpoint: `POST /open/skill/hot_index`

Body:
- `days`: 1 (today) | 7 (this week)

Returns list, common fields:
- `rank`, `project_id`, `project_name`, `token_symbol`, `one_liner`, `tags`, `X`, `rootdataurl`

### `rd_job_changes(recent_joinees=True, recent_resignations=True, language='en')`
Get recent personnel moves.

Endpoint: `POST /open/skill/job_changes`

Body:
- `recent_joinees`: bool
- `recent_resignations`: bool

Returns dict with:
- `recent_joinees` (max 20)
- `recent_resignations` (max 20)

## Language Header

Pass `language` header:
- `en` (default)
- `cn`

## Error Handling

HTTP codes:
- 200 success
- 400 bad params
- 401 invalid key
- 404 not found
- 429 rate limit
- 500 internal error

Rate limit:
- 200 requests / minute / key
- on 429, use `Retry-After` header before retry

## Usage Notes

- Keep a cached `ROOTDATA_SKILL_KEY` to avoid frequent init calls.
- For research tasks, preferred flow:
  1) `rd_search` → find entity ID
  2) `rd_project_detail` / `rd_funding_rounds` for deeper analysis
- Funding rounds endpoint is recent-window only (365 days), mention this explicitly in outputs.
