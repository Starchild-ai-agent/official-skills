---
name: agent-builder
version: 2.0.1
description: |
  Build focused micro-agents with names, tasks, schedules, and team coordination.

  Use when spinning up specialized sub-agents that run on a schedule (e.g. create a market-scout, set up a research team, daemon that polls inbox).

tools:
  - agent_build
  - agent_task
  - agent_run
  - agent_list
  - agent_team
  - agent_loop
  - agent_message

metadata:
  starchild:
    emoji: "🏗️"
    skillKey: agent-builder
    requires:
      bins: [python3]

user-invocable: true

---

# Agent Builder

Build focused micro-agents that do 1-2 things exceptionally well.

## Routing (YOU MUST DECIDE)

When the user asks to create an agent, pick the right path:

**`agent_build` (singular)** — 1 skill, 1 data source, simple recurring tasks, 1-5 tool calls.

**`agent_build` + `always_on=True`** — Agent that runs 24/7, polls inbox for messages every 5 min. Like an employee at their desk.

**`agent_team` (team)** — 2+ skills, parallel data gathering, synthesis needed, 10+ tool calls.

**`agent_loop` (long-running)** — Open-ended research, iterative accumulation, no fixed endpoint.

**`agent_message`** — Send a message to any agent's inbox. Works for user→agent and agent→agent.

**When unsure:** Start singular. Cheapest. User can upgrade later.

## Tools

| Tool | Use |
|------|-----|
| `agent_build` | Create or update an agent. Set `always_on=True` for daemon mode. |
| `agent_task` | Add/update/complete/remove/list tasks. Also `set_status` to pause/archive/reactivate. |
| `agent_run` | Execute agent once (picks highest-priority pending task) |
| `agent_list` | List all agents with status, task counts. Filter by team/status. |
| `agent_team` | Create and run teams (leader + workers with cost-optimized models) |
| `agent_loop` | Run agent in loop mode — iterates until goal satisfied or budget exhausted |
| `agent_message` | Send a message to an agent's inbox. Daemon picks it up on next poll. |

## Singular Agent Workflow

### 1. Create

```
agent_build(
  name="market-scout",
  display_name="Market Scout",
  role="Crypto market surveillance specialist",
  goal="Monitor BTC and ETH prices, flag anomalies",
  skills=["coingecko", "chart"],
  template="monitor",
  mode="research",
  schedule="0 8 * * *",
  timezone="Asia/Kuala_Lumpur"
)
```

**Templates:** `default`, `monitor`, `researcher`

**Modes:**
- `default` — Free thinking
- `research` — Hallucination guardrails: must say "I don't know", cite sources, extract quotes before analysis

**Schedule:** Cron (`"0 8 * * *"`), interval (`"every 30 minutes"`), delay (`"in 2 hours"`), at (`"at 2026-05-01 14:00"`)

### 2. Add Tasks

```
agent_task(agent="market-scout", action="add",
  title="Check BTC price",
  priority="high",
  due_date="2026-04-26",
  recurring=True,
  depends_on=["task-id-of-prerequisite"]
)
```

- **Priority:** `low` (60s, 2 calls), `medium` (120s, 5 calls), `high` (180s, 10 calls), `critical` (300s, 20 calls)
- **Recurring:** Resets to pending after completion, logs history
- **depends_on:** Task chaining — blocked until dependencies complete

### 3. Run

```
agent_run(agent="market-scout")
```

### 4. Manage

```
agent_task(agent="market-scout", action="set_status", status="paused")
agent_list(team="market-sentiment", verbose=True)
```

## Team Workflow

### 1. Create Team

```
agent_team(action="create",
  name="market-sentiment",
  leader={"name": "analyst", "role": "Synthesize sentiment", "skills": ["chart"]},
  workers=[
    {"name": "btc-fetcher", "role": "Fetch BTC tweets", "skills": ["twitter"]},
    {"name": "eth-fetcher", "role": "Fetch ETH tweets", "skills": ["twitter"]},
  ]
)
```

Leader: Sonnet ($3/$15). Workers: Haiku ($1/$5). ~67% savings.

### 2. Run Team

```
agent_team(action="run", name="market-sentiment",
  goal="Cross-chain sentiment comparison for BTC and ETH"
)
```

Leader owns the full pipeline: creates worker tasks → runs workers → waits (bash poll) → reads outputs → synthesizes.

## Loop Mode (Long-Running)

For open-ended tasks with no fixed endpoint:

```
agent_loop(agent="uni-scout",
  goal="Find universities with AI programs open to collaboration",
  max_iterations=10,
  output_file="candidates.json",
  timeout=1800
)
```

The agent iterates: read progress → search → add results → evaluate → continue/stop.

**Budget regimes** adapt strategy as iterations progress:
- EXPLORE (early) → CONVERGE (middle) → FOCUS (late) → FINALIZE (end)

**Stopping:** Agent says done, max iterations, or 2 consecutive dry iterations.

## Always-On Agents (Daemon Mode)

Create agents that run 24/7, polling for messages and tasks:

```
agent_build(name="ai-scout", display_name="AI Scout",
    role="Research AI content creators on Twitter",
    goal="Build a database of high-quality AI creators",
    skills=["twitter"], template="researcher", mode="research",
    always_on=True, team="marketing"
)
```

Then activate the daemon:
```
scheduled_task(action="activate", job_id="<daemon_job_id from output>")
```

Every 5 minutes, the daemon:
1. Checks `inbox.json` — new messages? Process them, respond, push to user.
2. Checks `tasks.json` — pending tasks? Run the highest priority one.
3. Neither? **Autonomous work** — reads its goal, memory, and existing output, then proactively does the next most valuable thing to advance its goal. Runs every 30 min (cooldown prevents burning tokens every poll).

If the agent has nothing productive to do (goal fully satisfied), it outputs `AUTONOMOUS_IDLE` and costs $0.00.

## Messaging

Send messages to any agent — user to agent or agent to agent:

```
agent_message(agent="ai-scout", message="Focus on creators with 100K+ followers who post about LLMs")
agent_message(agent="marketing-lead", message="5 new creators found", from_agent="ai-scout")
```

Messages queue in `inbox.json`. The agent's daemon processes them on next poll (~5 min max).
Responses appear in `outbox.json` and push to user.

## Managing Agents

Everything is mutable at any time:
- **Pause:** `agent_task(agent="x", action="set_status", status="paused")` — daemon skips paused agents
- **Resume:** `agent_task(agent="x", action="set_status", status="active")`
- **Kill daemon:** `scheduled_task(action="cancel", job_id="<id>")` — **cancel is permanent**, see Daemon Lifecycle below
- **Change role/skills/mode:** Re-run `agent_build` with new params — overwrites config
- **Send new instructions:** `agent_message(agent="x", message="change focus to...")`
- **Check findings:** `read_file("agents/team/agent/output/results.json")`
- **Delete:** Remove the directory — agents are just files

### Daemon Lifecycle (IMPORTANT)

**Cancel is permanent.** `scheduled_task(action="cancel")` deletes the job. You cannot reactivate it. To restart a cancelled daemon:
1. Re-run `agent_build` with `always_on=True` — registers a new scheduled task
2. The new task gets a new `job_id` — the old run.py's `JOB_ID` is now stale
3. `agent_build` automatically writes the correct `JOB_ID` into the new run.py
4. Activate: `scheduled_task(action="activate", job_id="<new_id>")`

**JOB_ID must match the active task.** The `JOB_ID` inside run.py is how push notifications route to the right job. If you manually copy a run.py, update the `JOB_ID` constant or push notifications silently go to a dead job.

## Agent Pre-Action Reasoning

Every agent template now includes a mandatory reasoning framework before tool calls:
- **WHO** is affected?
- **WHAT** exactly will you do?
- **WHY** does this advance your goal?
- **RISK** — safe / moderate / destructive?

Destructive actions (delete, overwrite, clear) require the agent to STOP and generate a preview before executing. This prevents accidental data loss.

## Output Contract

Every agent has a **mandatory output contract** baked into its prompt:
- Primary output is always a JSON file (`output/results.json`)
- JSON first, human-readable summary second
- On every run: read existing → append new → write back (never overwrite from scratch)
- Downstream agents and systems read JSON, not markdown

This prevents the "beautiful report but empty database" problem where agents write prose but never update their structured output.

## Deduplication

All templates instruct agents to check for duplicates before adding items:
- Match on primary identifier (name, handle, URL, or ID)
- Skip duplicates, log skip count
- Design dedup in from run 1, not as a cleanup pass later

## Resource Ownership

One agent owns one resource. Rules baked into every template:
- Agents write ONLY to their own `output/`, `memory/`, and `scripts/` directories
- If multiple agents need to feed the same destination, each writes to their own output — a designated sync agent handles the merge
- No two agents should write to the same file

## Targeting Criteria

Researcher agents include explicit targeting bounds:
- **Fit score** 1-10, only include items scoring 6+
- **Reachability** — prefer contacts you can actually reach
- **Relevance** — must directly relate to goal, not adjacent/tangential
- Set explicit upper/lower bounds in task descriptions (follower range, geography, etc.)

## Destructive Operation Guards

Agents cannot delete, clear, or overwrite critical data without generating a preview first. The pre-action reasoning framework classifies every action as safe/moderate/destructive. Destructive actions require:
1. A preview of what would change
2. Explicit confirmation before execution

## Platform Tool Reliability

Platform tools (send_to_telegram, composio integrations, etc.) can silently fail if the underlying service is misconfigured or pending setup. For daemon agents that depend on external delivery:
- Always verify the tool works manually before relying on it in a daemon
- Build a direct API fallback for critical delivery paths
- Check tool output — silent failures return success with no actual delivery

## Loop Mode Stopping Signals

For `agent_loop`, a "dry iteration" means the agent searched but found zero new items to add to the output file. The agent signals this by writing `"new_items": 0` in its `score.json` for that iteration. Two consecutive dry iterations = stop.

The agent signals completion by outputting the text `LOOP_COMPLETE` as its final message. If it keeps running after goals are met, add explicit stopping criteria to the task description: "Stop when you have 20+ items" or "Stop when coverage includes US, UK, and Asia."

## GUARDRAILS.md

Every agent gets a `GUARDRAILS.md` file — a living document of learned constraints. Agents should append entries as they discover failure patterns:

```
## Trigger: Writing to output without reading existing content
Instruction: ALWAYS read the output file before writing
Reason: Previous run overwrote 15 valid entries with 3 new ones
```

## Directory Structure

```
agents/
├── marketing/                     ← team folder
│   ├── team.json                  ← team config (leader, workers, models)
│   ├── analyst/                   ← leader agent
│   │   ├── agent.yaml
│   │   ├── PROMPT.md
│   │   ├── GUARDRAILS.md          ← learned constraints
│   │   ├── tasks.json
│   │   ├── references/
│   │   ├── scripts/
│   │   ├── output/results.json    ← mandatory JSON output
│   │   ├── inbox.json             ← messages (always-on)
│   │   ├── outbox.json
│   │   └── memory/MEMORY.md
│   ├── btc-fetcher/               ← worker
│   └── eth-fetcher/               ← worker
├── btc-watcher/                   ← singular agent (flat)
└── hackathon-scout/               ← singular agent (flat)
```

## Design Principles

1. **Focused** — Each agent does 1-2 things. Resist scope creep.
2. **Isolated** — Each agent owns its own directories. No cross-agent writes.
3. **Observable** — Tasks have statuses, priorities, due dates, retry counts, history.
4. **Composable** — Create, pause, archive, delete independently.
5. **Progressive** — Context loads in layers (L1 metadata → L2 prompt → L3 references on demand).
6. **Self-improving** — Agents write learnings to memory and GUARDRAILS.md after every run.
7. **Cost-aware** — Priority determines timeout, tool call budget, and model hint.
8. **JSON-first** — Structured output before prose. Downstream systems read JSON.
9. **Dedup-first** — Check before inserting. Design deduplication from run 1.
10. **Safe-by-default** — Destructive actions require preview + confirmation. Dry-run mode.
