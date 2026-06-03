---
name: project-builder
version: 1.5.8
description: |
  End-to-end project engineering: design, incremental build, verify, debug systematically.

  Use when building software, dashboards, scheduled jobs, or web apps the user has asked for (e.g. build a price monitor, daily summary task, ship an API).
tags:
- engineering
- development
- tasks
- dashboards
- preview
- debugging
tools:
- read_file
- write_file
- edit_file
- bash
- preview_serve
- preview_stop
- preview_check
- community_publish
- community_unpublish
- community_list
- register_task
- activate_task
- cancel_scheduled_task
- update_scheduled_task
- list_scheduled_tasks
- get_scheduled_task_log
delivery: script
triggers:
- build me
- create a dashboard
- set up monitoring
- schedule a task
- make a web app
- write a script
- something is broken
- it's not working
- debug this
- fix this
- preview
- publish

---

## Phase 0: SKILL DISCOVERY & REQUIRED READING

**⚠️ CRITICAL — UI Design Quality Gate:** If the project produces ANY visual HTML output (dashboard, web app, landing page, portfolio, any page the user will see), you MUST `read_file` the `ui-design` skill's SKILL.md and follow it BEFORE writing any HTML/CSS. This is not optional. project-builder handles engineering; ui-design handles visual quality (and tells you when to reach for a component library like shadcn/ui, HeroUI, or coss ui instead of hand-writing). Skipping ui-design produces generic AI slop.

**A. Pick the skills.** Gather every data source the project needs. For each one, prefer a skill: check `<available_skills>`, and if nothing fits, try `search_skills(query)` for official + marketplace coverage. Skills are the most reliable layer — they ship tested clients, auth, and rate-limit handling. Web search is a last resort. Only write raw HTTP / SDK code when no skill can cover the source.

**B. Read the platform rules for what the project touches.** These rules live in references (not in your system prompt) so you must `read_file` them before writing code. Skipping this is the #1 cause of 401s, broken paths, and "worked locally, fails in preview" bugs.

| If the project includes... | `read_file` before Phase 2 |
|---|---|
| Any external API call | `config/context/references/sc-proxy.md` |
| Preview / dashboard / web app | `config/context/references/preview-guide.md` |
| Scheduled task | `config/context/references/scheduled-tasks-guide.md` |
| Long-running background job | `config/context/references/background-tasks.md` |
| File writing >300 lines | `config/context/references/tool-writing-guide.md` |
| **Any visual HTML output** (dashboard, web app, landing page, portfolio) | **`ui-design` skill SKILL.md** — load it and follow it for all visual decisions (track choice, color, typography, layout, animation, and when to use a component library). This skill is the UI quality gate; skipping it produces generic AI slop. |

---

## Phase 1: DESIGN
**Translate vague requests into concrete specs.** If intent is ambiguous, ask ONE question.

Architecture decision tree:
```
Periodic alerts/reports?  → Scheduled Task
Live visual interface?    → Preview Server (dashboard)
One-time analysis?        → Inline (no build needed)
Reusable tool?            → Script in workspace
```

For medium+ projects, present to user BEFORE writing code:
1. Data flow — sources → processing → output
2. Architecture choice and why
3. Cost estimate — (cost/run) × frequency × 30 = monthly
4. Known limitations

**UI Design Gate (required, blocking — for visual projects):**
If the architecture choice is Preview Server or any project that outputs HTML the user will see:
1. `read_file` the `ui-design` skill's SKILL.md **now** (if you haven't already in this session) and pick a track (hand-built vs component library).
2. For hand-built UI, run the Design Dials (in ui-design's `references/design-process.md`) to determine Surface, Accent, Typography, and Aesthetic Family.
3. Include the Design Dials output line in your phase plan below.
If you skip this step, the UI will look like generic AI output. This gate is blocking — do not proceed to Phase 2 without completing it.

**Design Gate (required, blocking):**
After Phase 1, STOP and present a short phase plan (milestones for DESIGN/BUILD/DEBUG). Ask explicitly: **"Approve this plan and proceed to Phase 2 BUILD?"** Match the user's language when phrasing the question — never inject a hardcoded non-English string.
- If user confirms: proceed to Phase 2.
- If user requests changes: revise design and re-confirm.
- If no confirmation: do not write/modify code.

---

## Phase 1.5: SCAFFOLD (mandatory for shareable projects)

After design is confirmed, **before writing any code**, scaffold the project under the standard layout. This makes the project shareable via `community-publish` skill from day one — no migration later.

**Standard project location:** `output/projects/{slug}/`

```
output/projects/{slug}/
├── project.yaml          # name, version (start 0.1.0), type, description, license, entry, env_required
├── PROJECT.md            # 4 required sections: What / Required env / How to start / Outputs / Troubleshooting
├── .env.example          # every env var the code reads, with placeholder values
├── .gitignore            # at minimum: .env, *.key, *.pem, __pycache__, node_modules
└── src/                  # all code lives here, NOT scattered
    ├── run.py            # type=task — first line MUST be: # -*- task-system: v3 -*-
    ├── server.py         # type=service
    ├── main.py           # type=script
    └── index.html / app.py + frontend  # type=preview
```

**Project type → entry mapping:**

| Architecture choice | type | entry path |
|---|---|---|
| Scheduled Task | `task` | `src/run.py` |
| Preview Server | `preview` | `src/index.html` (static) or `src/app.py` |
| Background daemon | `service` | `src/server.py` |
| One-shot tool | `script` | `src/main.py` |

**Skip scaffold only when:**
- Pure inline analysis with no persistent code
- Modifying an existing `output/projects/...` project (keep its layout)
- User explicitly says "just throw a script in /tmp" or similar

**During Phase 2 BUILD, maintain the scaffold:**
- Every new env var read by code → add to `.env.example` in same edit
- Every behavioral change → update PROJECT.md
- Never write code outside `src/` (configs, fixtures: project root or `src/data/`)

**Why this matters:** Projects already in standard layout publish in one command. Projects scattered across `tasks/`, `output/scripts/`, `dashboards/`, etc. need `tidy_project()` migration before they can be shared, and the user often doesn't want to rebuild PROJECT.md from memory.

**For existing scattered code:** call `community-publish` skill → `tidy_project(any_dir)` to reorganize before publishing.

---

**API cost & rate limits:**
All external API calls go through sc-proxy, which bills per request and enforces rate limits.
Before designing, **read `config/context/references/sc-proxy.md`** for pricing table and limits.
- Estimate cost: `credits_per_request × requests_per_run × runs_per_day × 30`
- Respect rate limits: e.g. CoinGecko 60 req/min — a task polling 10 coins every minute is fine; 100 coins is not
- Prefer batch endpoints over N single calls (e.g. `coin_price` with multiple ids vs N separate calls)
- Pure script tasks (no API): ~0 credits/run
- **LLM cost warning:** high-end models can exceed **$0.10 per single call**. Pricing varies dramatically by model tier; expensive models can be **100x+** the cost of budget models for the same workflow.
- **Model-aware estimate required:** break LLM cost down by model (`model_price_per_call × expected_calls_per_run × runs_per_day × 30`) instead of using a single generic number.
- Dashboard auto-refresh costs credits — default to manual refresh unless user asks otherwise
- **Spending protection:** if projected monthly LLM cost is high, explicitly ask whether to enforce per-caller limits before implementation.
- **Per-caller tracking (required):** every proxied request must include `SC-CALLER-ID` (e.g. `job:{JOB_ID}`, `preview:{preview_id}`, `chat:{thread_id}`) so usage can be traced and capped. Details in `config/context/references/sc-proxy.md` § Caller Credit Limit

**Data reliability:** Native tools > proxied APIs > direct requests > web scraping > LLM numbers (never).
**Iron rule: Scripts fetch data. LLMs analyze text. Final output = script variables + LLM prose.**

**Task scripts can import skill functions directly:**
```python
from core.skill_tools import coingecko, coinglass  # auto-discovers skills/*/exports.py
prices = coingecko.coin_price(coin_ids=["bitcoin"], timestamps=["now"])
```
Tool names = SKILL.md frontmatter `tools:` list. See `build-patterns.md § Using Skill Functions`.

---

## Phase 2: BUILD
Every piece follows this cycle:
```
Build one small piece → Run it → Verify output → ✅ Next piece / ❌ Fix first
```

| Built | Verify how | Pass |
|-------|-----------|------|
| Data fetcher | Run, print raw response | Non-empty, recent, plausible |
| API endpoint | `curl localhost:{port}/api/...` | Correct JSON |
| HTML page | `preview_serve` + `preview_check` | `ok = true` |
| Task script | `python3 tasks/{id}/run.py` | Numbers match source |
| LLM analysis | Numbers from script vars, not LLM text | Template pattern used |

**Verification layering:**
- **Critical** (must pass before preview/activate): data correctness, core logic, no crashes
- **Informational** (can fix after delivery): styling, edge case messages, minor UX polish

**Anti-patterns:**
- ❌ "Done!" without running anything
- ❌ Writing 200+ lines then testing for the first time
- ❌ "It should work"

→ Detailed patterns: **read `references/build-patterns.md`**

### Code Practices

- `read_file` before `edit_file` — understand what's there
- `edit_file` > `write_file` for modifications
- Check `ls` before `write_file` — avoid duplicating existing files
- Large files (>300 lines): split into multiple files, or skeleton-first + bash inject
- Env vars: `os.environ["KEY"]`, persist installs to `setup.sh`

### Dashboard UX Defaults (`type=preview`)

Decide sensible defaults yourself and render real data on first load. Treat filters as optional refinements users can adjust later — never as prerequisites that gate the initial view. Auto-refresh on a sensible interval. No "Click to load" / "Enter address" / "Select symbol" before anything appears.

**Visual design quality (MANDATORY for all HTML output):** If the `ui-design` skill is installed, you MUST `read_file` its SKILL.md and follow it before writing any HTML/CSS. project-builder owns the engineering workflow; ui-design owns the visual quality. Using project-builder alone produces functional but visually generic output.

---

### Platform Rules

- Agent tools are tool calls only — not importable in scripts
- Preview paths must be relative (`./path` not `/path`)
- **Hardcode the preview port in code, do not read from env.** Each preview runs in its own pod and the env-port contract is not reliable across pods. Pick any free port (e.g. `8765`), write it directly into the app, and pass the same number to `preview(action="serve", port=...)`. The two must match exactly.
- **Concurrent previews need different IDs.** If two previews share the same `dir`, the newer one auto-kills the older one (same-dir replacement rule). When iterating, reuse the same id rather than inventing variants, or use distinct dirs.
- Fullstack = one port (backend serves API + static files)
- Cron times are UTC — convert from user timezone
- Preview serving & publishing → read platform reference `config/context/references/preview-guide.md`
- localhost APIs → read `config/context/references/localhost-api.md`
  - Task scripts decide WHEN to invoke the agent, WHAT data/context to pass, WHICH model to use
  - Pattern: script fetches data → evaluates if noteworthy → calls LLM only when needed → prints result
- **LLM in scripts — two options** (details in `references/build-patterns.md`):
  - **OpenRouter** (via sc-proxy): lightweight, for summarize/translate/format text. Direct API call, no agent overhead.
  - **localhost /chat/stream**: full agent with tools. Use only when LLM needs tool access.
- **Data template rule**: Script owns the numbers, LLM owns the words. Final output assembles data from script variables + analysis from LLM. Never let LLM output be the sole source of numbers the user sees.
- API costs & rate limits → read platform reference `config/context/references/sc-proxy.md`

---

## Phase 3: DEBUG
```
CHECK LOGS → REPRODUCE → ISOLATE → DIAGNOSE → FIX → VERIFY → REGRESS
```

- **CHECK LOGS** first — task logs, preview diagnostics, stderr. If logs reveal a clear cause, skip to FIX.
- **REPRODUCE** only when logs are insufficient — see the failure yourself
- **ISOLATE** which layer is broken (data? logic? LLM? output? frontend? backend?)
- **FIX** the root cause, then **VERIFY** with the same repro steps. Don't just fix — fix and confirm.

**Three-Strike Rule:** Same approach fails twice → STOP → rethink → explain to user → different approach.

→ Full debug procedures: **read `references/debug-handbook.md`**

---

## Quick Checklists
**Kickoff:** ☐ Clarified intent ☐ Proposed architecture ☐ Estimated cost ☐ User confirmed (**required before Phase 2**)

**Build:** ☐ Each component tested ☐ Numbers match source ☐ Errors handled ☐ Preview healthy (web)

**Debug:** ☐ Logs checked ☐ Reproduced (or skipped — logs sufficient) ☐ Isolated layer ☐ Root cause found ☐ Fix verified ☐ Regressions checked