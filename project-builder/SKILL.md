---
name: project-builder
version: 1.3.3
description: "End-to-end project engineering — from understanding user intent to architecture design, incremental build with verification, and systematic debugging. Covers scheduled tasks (cron jobs), dashboards, web apps, APIs, scripts, and any software the user wants built. Replaces coder + preview-dev with a unified methodology."
tags: [engineering, development, tasks, dashboards, preview, debugging]
tools: [read_file, write_file, edit_file, bash, preview_serve, preview_stop, preview_check, community_publish, community_unpublish, community_list, register_task, activate_task, cancel_scheduled_task, update_scheduled_task, list_scheduled_tasks, get_scheduled_task_log]
triggers:
  - "build me"
  - "create a dashboard"
  - "set up monitoring"
  - "schedule a task"
  - "make a web app"
  - "write a script"
  - "something is broken"
  - "it's not working"
  - "debug this"
  - "fix this"
  - "preview"
  - "publish"
---

# Project Build

Three phases, always in order: **DESIGN → BUILD → DEBUG**.

**Skill references** (read on demand, not upfront):
- `references/build-patterns.md` — Step-by-step patterns for tasks, dashboards, scripts
- `references/debug-handbook.md` — Layer-by-layer diagnosis, common issues

**Platform references** (shared, in `config/context/references/`):
- `preview-guide.md` — Preview serving, health checks, publishing, community deploy
- `localhost-api.md` — Scripts can call the agent via /chat/stream (decide when to think, what context to pass, which model) and push messages via /push
- `sc-proxy.md` — Transparent proxy, API pricing & rate limits

**Skill references** (in `references/`):
- `build-patterns.md` — Detailed build recipes per project type
- `debug-handbook.md` — Systematic diagnosis protocol
- `dashboard-examples.md` — Code templates for Chart.js, ApexCharts, D3.js, SSE, responsive layouts, dark mode, accessibility (read when building dashboards)

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

**Design Gate (required, blocking):**
After Phase 1, STOP and present a short phase plan (milestones for DESIGN/BUILD/DEBUG). Ask explicitly: **"是否按这个方案进入 Phase 2 BUILD？"**
- If user confirms: proceed to Phase 2.
- If user requests changes: revise design and re-confirm.
- If no confirmation: do not write/modify code.

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

### Platform Rules

- Agent tools are tool calls only — not importable in scripts
- Preview paths must be relative (`./path` not `/path`)
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
