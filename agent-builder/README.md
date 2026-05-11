# Agent Builder

Build focused micro-agents that do 1-2 things exceptionally well. Each agent gets its own directory with a prompt, tasks, memory, and output folder. They run as background tasks via `sessions_spawn`.

## Tools

| Tool | Purpose |
|------|---------|
| `agent_build` | Create or update a micro-agent (name, role, goal, skills, template, schedule) |
| `agent_task` | Add, update, complete, remove, or list tasks for an agent |
| `agent_run` | Execute an agent's next pending task in the background |
| `agent_list` | List all agents with status, task counts, and due dates |
| `agent_team` | Create and run leader+worker teams (cost-optimized models) |
| `agent_loop` | Run iterative research loops with diminishing returns detection |
| `agent_message` | Send messages to an always-on agent's inbox |

## How It Works

### Creating an Agent

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

This creates:

```
workspace/agents/market-scout/
├── agent.yaml         # Spec: name, role, goal, model, status, schedule
├── PROMPT.md          # Rendered from template with role/goal injected
├── tasks.json         # Task list with priorities and dependencies
├── memory/
│   └── MEMORY.md      # Agent learns across runs (patterns, quirks, mistakes)
├── references/
│   ├── general-guide.md
│   └── monitoring-guide.md
├── scripts/           # Deterministic scripts the agent can run
└── output/            # Deliverables (reports, data files)
```

### Running an Agent

```
agent_run(agent="market-scout")
```

What happens:
1. Loads `agent.yaml` and checks status is "active"
2. Reads `tasks.json` and picks the highest priority pending task (respects `depends_on`)
3. Builds a prompt from `PROMPT.md` + `memory/MEMORY.md` + task details + resource budget
4. Calls `sessions_spawn` to run the task in the background
5. Agent does the work, saves results to `output/`, updates `memory/MEMORY.md`
6. Push notification when done

### Task System

Tasks have priorities that control how much resources the agent gets:

| Priority | Timeout | Max Tool Calls | Strategy |
|----------|---------|----------------|----------|
| `low` | 60s | 2 | Quick check |
| `medium` | 120s | 5 | Standard work |
| `high` | 180s | 10 | Deep analysis |
| `critical` | 300s | 20 | Intensive |

```
agent_task(agent="market-scout", action="add",
  title="Check BTC price",
  priority="high",
  due_date="2026-04-26",
  recurring=True,
  depends_on=["task-id-of-prerequisite"]
)
```

Features:
- **`depends_on`** — Task chaining. Task B waits until Task A completes.
- **`recurring`** — Resets to pending after completion. Logs history of past runs.
- **`max_retries`** — Dead-letters a task after N consecutive failures (default: 3).

### Managing Tasks

```
agent_task(agent="market-scout", action="list")              # See all tasks
agent_task(agent="market-scout", action="complete", task_id="task-abc123")
agent_task(agent="market-scout", action="update", task_id="task-abc123", priority="critical")
agent_task(agent="market-scout", action="remove", task_id="task-abc123")
agent_task(agent="market-scout", action="set_status", status="paused")  # Pause the agent
```

## 3 Prompt Templates

| Template | For | Method |
|----------|-----|--------|
| `default` | General focused tasks | Simple rules: stay focused, use skills, save to output/ |
| `monitor` | Surveillance and alerting | Baseline -> Compare -> Detect -> Trend. Severity: INFO / WARNING / ALERT |
| `researcher` | Research and analysis | Scope -> Gather -> Cross-reference -> Synthesize -> Recommend |

## 2 Modes

| Mode | Behavior |
|------|----------|
| `default` | Free thinking. No constraints on reasoning. |
| `research` | Hallucination guardrails enforced: must say "I don't know" when uncertain, cite sources for every claim, extract direct quotes before analyzing. |

## 4 Execution Patterns

### 1. Singular Agent

One agent, one task at a time. The simplest and cheapest pattern.

```
agent_build(name="btc-watcher", ...)
agent_task(agent="btc-watcher", action="add", title="Check BTC price", recurring=True)
agent_run(agent="btc-watcher")
```

### 2. Team (Leader + Workers)

Leader delegates to workers, waits for results, synthesizes a final deliverable.

```
agent_team(action="create",
  name="market-sentiment",
  leader={"name": "analyst", "display_name": "Analyst", "role": "Synthesize cross-chain sentiment", "skills": ["chart"]},
  workers=[
    {"name": "btc-fetcher", "display_name": "BTC Fetcher", "role": "Fetch BTC tweets", "skills": ["twitter"]},
    {"name": "eth-fetcher", "display_name": "ETH Fetcher", "role": "Fetch ETH tweets", "skills": ["twitter"]},
  ]
)

agent_team(action="run", name="market-sentiment",
  goal="Cross-chain sentiment comparison for BTC and ETH")
```

How it works:
1. Leader creates tasks for each worker via `agent_task`
2. Leader runs all workers via `agent_run` (parallel)
3. Leader waits with a bash poll loop (checks if workers wrote to `output/`)
4. Leader reads worker outputs
5. Leader synthesizes final deliverable

Cost optimization:
- Leader uses Sonnet ($3/$15 per M tokens) — plans and synthesizes
- Workers use Haiku ($1/$5 per M tokens) — execute subtasks
- ~67% savings vs using Sonnet for everything

Directory structure:
```
workspace/agents/market-sentiment/
├── team.json           # Team config (leader, workers, models)
├── analyst/            # Leader agent directory
├── btc-fetcher/        # Worker agent directory
└── eth-fetcher/        # Worker agent directory
```

### 3. Loop Mode (Iterative Research)

For open-ended tasks with no fixed endpoint. The agent iterates until the goal is satisfied or budget is exhausted.

```
agent_loop(agent="uni-scout",
  goal="Find universities with AI programs open to collaboration",
  max_iterations=10,
  output_file="candidates.json",
  timeout=1800
)
```

Each iteration:
1. **Diagnose** — Read past iteration traces to identify patterns
2. **Plan** — Decide strategy based on diagnosis (avoid repeated failures)
3. **Execute** — Search, fetch, analyze
4. **Update** — Add findings to output file
5. **Log** — Create `iterations/iter-NNN/trace.md` and `score.json`
6. **Evaluate** — Continue or stop?

Budget regimes adapt strategy as iterations progress:
- **EXPLORE** (early) — Cast a wide net, try different approaches
- **CONVERGE** (middle) — Focus on what's working
- **FOCUS** (late) — Fill remaining gaps
- **FINALIZE** (end) — Polish and verify

Stopping conditions:
- Agent declares goal satisfied
- Max iterations reached
- 2 consecutive dry iterations (0 new items found)

### 4. Always-On Daemon

An agent that runs 24/7, polling every 5 minutes for messages and tasks.

```
agent_build(name="ai-scout", display_name="AI Scout",
  role="Research AI content creators on Twitter",
  goal="Build a database of high-quality AI creators",
  skills=["twitter"],
  template="researcher",
  mode="research",
  always_on=True
)

# Activate the daemon (job_id is in the build output)
scheduled_task(action="activate", job_id="<daemon_job_id>")
```

Every 5 minutes, the daemon checks (in priority order):
1. **Inbox** — New messages? Process them, respond, push to user
2. **Tasks** — Pending tasks? Run the highest priority one
3. **Autonomous work** — Nothing queued? Proactively advance its goal (30-min cooldown to prevent burning tokens)

If the agent has nothing productive to do, it outputs `AUTONOMOUS_IDLE` and costs nothing.

Send messages to the agent at any time:
```
agent_message(agent="ai-scout", message="Focus on creators with 100K+ followers who post about LLMs")
```

Messages queue in `inbox.json`. The daemon processes them on its next poll (max 5 min wait). Responses appear in `outbox.json` and push to the user.

## Scheduling

Agents can be scheduled to run automatically:

| Format | Example | Description |
|--------|---------|-------------|
| Cron | `"0 8 * * *"` | Daily at 8:00 UTC |
| Interval | `"every 30 minutes"` | Repeating interval |
| Delay | `"in 2 hours"` | One-shot after delay |
| At | `"at 2026-05-01 14:00"` | One-shot at specific time |

Set timezone with `timezone="Asia/Kuala_Lumpur"` (default: UTC).

## Self-Improving Memory

After every run, agents update `memory/MEMORY.md` with:
- Approaches that worked or failed
- API quirks discovered
- Thresholds and patterns found
- Mistakes to avoid

**NOT stored**: raw data, timestamps, intermediate results.

The next run reads this memory, so the agent gets better over time. Memory is scoped to each agent — no cross-contamination.

## Managing Agents

| Action | Command |
|--------|---------|
| List all agents | `agent_list()` |
| List by team | `agent_list(team="market-sentiment")` |
| Pause an agent | `agent_task(agent="x", action="set_status", status="paused")` |
| Resume | `agent_task(agent="x", action="set_status", status="active")` |
| Archive | `agent_task(agent="x", action="set_status", status="archived")` |
| Kill daemon | `scheduled_task(action="cancel", job_id="<id>")` |
| Change config | Re-run `agent_build` with new params (overwrites) |
| Send instructions | `agent_message(agent="x", message="change focus to...")` |
| Check output | `read_file("agents/x/output/results.json")` |
| Delete | Remove the agent's directory — agents are just files |

## Design Principles

1. **Focused** — Each agent does 1-2 things. Resist scope creep.
2. **Isolated** — Each agent has its own memory. Writes only to its own space.
3. **Observable** — Tasks have statuses, priorities, due dates, retry counts, history.
4. **Composable** — Create, pause, archive, delete independently.
5. **Progressive** — Context loads in layers: L1 metadata -> L2 prompt -> L3 references on demand.
6. **Self-improving** — Agents write learnings to memory after every run.
7. **Cost-aware** — Priority determines timeout, tool call budget, and model hint.

## File Reference

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill frontmatter + routing guide for the main agent |
| `__init__.py` | Registers 7 tools with the Star Child tool registry |
| `tools.py` | All 7 tool implementations (~2,000 lines) |
| `templates/default.md` | General-purpose agent prompt template |
| `templates/monitor.md` | Monitoring/surveillance agent prompt template |
| `templates/researcher.md` | Research/analysis agent prompt template |
| `templates/scheduled_run.py` | Self-contained script for scheduled agent execution |
| `templates/daemon_run.py` | Self-contained script for always-on daemon agents |
| `references/general-guide.md` | Universal guide: output format, skills, scripts, memory |
| `references/monitoring-guide.md` | Guide for monitor-template agents: baselines, severity, trends |
| `references/research-guide.md` | Guide for researcher-template agents: sources, conflicts, citations |
