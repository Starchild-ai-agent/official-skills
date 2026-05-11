"""
Agent Builder Tools — Create and manage focused micro-agents.

Each micro-agent lives at workspace/agents/{name}/ with:
  - agent.yaml        (spec: name, role, goal, skills, model)
  - PROMPT.md          (lean core prompt — L2 progressive disclosure)
  - tasks.json         (task list with statuses/due dates)
  - references/        (detailed guides — L3 progressive disclosure, loaded on demand)
  - scripts/           (executable scripts for deterministic operations)
  - memory/MEMORY.md   (agent-scoped memory, self-improving across runs)
"""

import asyncio
import json
import logging
import os
import re
import shutil
import uuid
from datetime import datetime
from datetime import timezone as _tz
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

SKILL_DIR = Path(__file__).parent
TEMPLATES_DIR = SKILL_DIR / "templates"
REFERENCES_DIR = SKILL_DIR / "references"

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
VALID_PRIORITIES = set(PRIORITY_ORDER.keys())
VALID_STATUSES = {"pending", "in_progress", "completed"}
VALID_TEMPLATES = {"default", "monitor", "researcher"}
VALID_AGENT_STATUSES = {"active", "paused", "archived"}
VALID_MODES = {"default", "research"}

# Resource budgets by priority — controls timeout, prompt guidance, model, and reference loading
# Based on real cost data: simple=$0.03-0.08, medium=$0.10-0.20, heavy=$0.30-1.50
RESOURCE_BUDGETS = {
    "low": {
        "timeout": 60,
        "max_tool_calls": 2,
        "guidance": "Complete efficiently. Use 1-2 tool calls maximum. Don't over-research.",
        "cost_tier": "light",
        "model_hint": "Use a fast/cheap model for this task. Call switch_model('fast') if available.",
        "show_references": False,  # don't list refs — save tokens
    },
    "medium": {
        "timeout": 120,
        "max_tool_calls": 5,
        "guidance": "Be thorough but focused. Aim for 3-5 tool calls. Stop when you have a clear answer.",
        "cost_tier": "standard",
        "model_hint": None,  # use default model
        "show_references": False,  # mention refs exist but don't list
    },
    "high": {
        "timeout": 180,
        "max_tool_calls": 10,
        "guidance": "Research thoroughly. Use up to 10 tool calls. Cross-reference 2-3 sources.",
        "cost_tier": "heavy",
        "model_hint": None,
        "show_references": True,  # list all refs — agent may need them
    },
    "critical": {
        "timeout": 300,
        "max_tool_calls": 20,
        "guidance": "Full depth investigation. Use as many sources as needed. Prioritize accuracy over speed.",
        "cost_tier": "intensive",
        "model_hint": "Use the most capable model available for this task.",
        "show_references": True,
    },
}

# Hallucination guardrails (from Anthropic docs: reduce-hallucinations)
# Research mode activates all three. Default mode lets the agent think freely.
RESEARCH_MODE_GUARDRAILS = """
## Research Mode Guardrails (ACTIVE)

These three rules override all other output behavior. Follow them strictly.

### 1. Say "I don't know" when you don't know
If you are unsure about any aspect, or if your sources lack the necessary information,
say "I don't have enough information to confidently assess this." Do NOT fill gaps with
plausible-sounding claims. Silence is better than fiction.

### 2. Verify every claim with citations
After drafting your response, review each factual claim. For each claim, find a direct
quote from your data sources or tool outputs that supports it. If you cannot find a
supporting quote for a claim, retract it — remove it from your output and mark where
it was removed with empty [] brackets.

### 3. Extract direct quotes before analyzing
Before performing analysis on any data or document, first extract word-for-word quotes
or exact values from the source. Ground your analysis in these extracted quotes — do NOT
paraphrase. Reference quotes by number in your analysis. If you can't find relevant
quotes, state "No relevant source data found" for that section.
"""

# Maps template type → which reference guides to copy into the agent's references/ dir
TEMPLATE_REFERENCES = {
    "default": ["general-guide.md"],
    "monitor": ["general-guide.md", "monitoring-guide.md"],
    "researcher": ["general-guide.md", "research-guide.md"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _agents_dir(ctx: ToolContext) -> Path:
    """Root directory for all micro-agents."""
    return Path(ctx.workspace_dir) / "agents"


def _agent_dir(ctx: ToolContext, name: str, team: str = None) -> Path:
    """Resolve agent directory. Team agents nest under agents/{team}/{name}/."""
    root = _agents_dir(ctx)
    if team:
        return root / team / name
    # Search: check team dirs first, then flat
    for entry in root.iterdir() if root.exists() else []:
        if entry.is_dir() and not entry.name.startswith("."):
            nested = entry / name / "agent.yaml"
            if nested.exists():
                return entry / name
    # Default: flat
    return root / name


def _read_yaml(path: Path) -> Dict[str, Any]:
    """Minimal YAML reader for agent.yaml (flat key: value format)."""
    data: Dict[str, Any] = {}
    if not path.exists():
        return data
    content = path.read_text(encoding="utf-8")
    current_key = None
    list_mode = False

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item under a key
        if stripped.startswith("- ") and current_key and list_mode:
            data[current_key].append(stripped[2:].strip().strip('"').strip("'"))
            continue

        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()

            if not val:
                # Start of a list or nested block
                data[key] = []
                current_key = key
                list_mode = True
                continue

            list_mode = False
            current_key = key

            # Remove quotes
            val = val.strip('"').strip("'")

            # Type coercion
            if val.lower() == "true":
                data[key] = True
            elif val.lower() == "false":
                data[key] = False
            elif val.isdigit():
                data[key] = int(val)
            else:
                try:
                    data[key] = float(val)
                except ValueError:
                    data[key] = val

    return data


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    """Minimal YAML writer for agent.yaml."""
    lines = []
    for key, val in data.items():
        if isinstance(val, list):
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
        elif isinstance(val, bool):
            lines.append(f"{key}: {'true' if val else 'false'}")
        elif val is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: {val}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_tasks(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return []


def _write_tasks(path: Path, tasks: List[Dict[str, Any]]) -> None:
    path.write_text(json.dumps(tasks, indent=2, default=str) + "\n", encoding="utf-8")


def _pick_next_task(tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pick highest priority pending task, then earliest due date.

    Respects depends_on: a task is only pickable if all its dependencies
    are completed (or completed_recurring — i.e. have run at least once).
    """
    # Build set of completed task IDs (including recurring that have history)
    completed_ids = set()
    for t in tasks:
        if t.get("status") == "completed":
            completed_ids.add(t["id"])
        elif t.get("recurring") and t.get("history"):
            # Recurring task that has run at least once counts as satisfied
            completed_ids.add(t["id"])

    pending = []
    for t in tasks:
        if t.get("status") != "pending":
            continue
        # Check dependencies
        deps = t.get("depends_on") or []
        if isinstance(deps, str):
            deps = [deps]
        if all(d in completed_ids for d in deps):
            pending.append(t)

    if not pending:
        return None
    pending.sort(key=lambda t: (
        PRIORITY_ORDER.get(t.get("priority", "medium"), 2),
        t.get("due_date") or "9999-12-31",
    ))
    return pending[0]


def _render_template(template_name: str, variables: Dict[str, str]) -> str:
    """Load and render a prompt template."""
    template_file = TEMPLATES_DIR / f"{template_name}.md"
    if not template_file.exists():
        template_file = TEMPLATES_DIR / "default.md"
    content = template_file.read_text(encoding="utf-8")
    for key, val in variables.items():
        content = content.replace(f"{{{key}}}", val)
    return content


def _validate_name(name: str) -> Optional[str]:
    """Validate agent name is kebab-case."""
    if not name:
        return "Agent name is required"
    if name != name.lower():
        return "Agent name must be kebab-case (lowercase letters, numbers, hyphens only)"
    if not all(c.isalnum() or c == "-" for c in name):
        return "Agent name must be kebab-case (lowercase letters, numbers, hyphens only)"
    if name.startswith("-") or name.endswith("-"):
        return "Agent name cannot start or end with a hyphen"
    return None


def _generate_scheduled_script(agent_name: str, display_name: str, team_name: str = "") -> str:
    """Generate a self-contained run.py for scheduled execution of a micro-agent."""
    template_path = TEMPLATES_DIR / "scheduled_run.py"
    content = template_path.read_text(encoding="utf-8")
    content = content.replace("__AGENT_NAME__", agent_name)
    content = content.replace("__DISPLAY_NAME__", display_name)
    content = content.replace("__TEAM_NAME__", team_name or "")
    return content


def _generate_daemon_script(agent_name: str, display_name: str, team_name: str = "") -> str:
    """Generate an always-on daemon run.py that polls inbox + runs tasks."""
    template_path = TEMPLATES_DIR / "daemon_run.py"
    content = template_path.read_text(encoding="utf-8")
    content = content.replace("__AGENT_NAME__", agent_name)
    content = content.replace("__DISPLAY_NAME__", display_name)
    content = content.replace("__TEAM_NAME__", team_name or "")
    return content


# ---------------------------------------------------------------------------
# agent_build
# ---------------------------------------------------------------------------

class AgentBuildTool(BaseTool):
    """Create or update a focused micro-agent."""

    @property
    def name(self) -> str:
        return "agent_build"

    @property
    def description(self) -> str:
        return """Create or update a focused micro-agent that does 1-2 things very well.

Creates the agent directory with spec, prompt, task list, and isolated memory.
If the agent already exists, updates its configuration.

Parameters:
- name: kebab-case identifier (e.g. "market-scout")
- display_name: human-readable name (e.g. "Market Scout")
- role: what this agent does (one sentence)
- goal: what this agent is trying to achieve (one sentence)
- skills: list of skill names this agent can use (e.g. ["coingecko", "chart"])
- model: model to use (default: "smart")
- template: prompt template — "default", "monitor", or "researcher"
- mode: "default" (free thinking) or "research" (hallucination guardrails active)
- max_turns: max tool calls per run (default: auto based on task priority)
- timeout: max seconds per run (default: auto based on task priority)
- team: team name for cross-agent collaboration. Agents in the same team can read each other's output/.
- custom_instructions: domain-specific rules injected into PROMPT.md after template rules (e.g. fund-specific guardrails, architecture principles)
- data_sources: list of file/dir paths the agent should read as input (e.g. ["fund/snapshot.json", "fund/grids/"])
- output_schema: description of the output structure (replaces the generic "JSON array" contract)
- always_on: if true, creates a daemon that polls every 5 min for inbox messages + pending tasks
- schedule: cron/interval expression (e.g. "0 8 * * *", "every 30 minutes"). Works WITH always_on — daemon for inbox, schedule for recurring reviews.
- timezone: user's timezone for schedule conversion (default: "UTC")
- tags: optional tags for organization"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Kebab-case agent identifier (e.g. 'market-scout')",
                },
                "display_name": {
                    "type": "string",
                    "description": "Human-readable name (e.g. 'Market Scout')",
                },
                "role": {
                    "type": "string",
                    "description": "What this agent does (one sentence)",
                },
                "goal": {
                    "type": "string",
                    "description": "What this agent is trying to achieve",
                },
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skill names this agent can use",
                },
                "model": {
                    "type": "string",
                    "description": "Model to use (default: smart)",
                    "default": "smart",
                },
                "template": {
                    "type": "string",
                    "enum": ["default", "monitor", "researcher"],
                    "description": "Prompt template to use",
                    "default": "default",
                },
                "mode": {
                    "type": "string",
                    "enum": ["default", "research"],
                    "description": "default = free thinking. research = hallucination guardrails (citations, quotes, admit uncertainty)",
                    "default": "default",
                },
                "max_turns": {
                    "type": "integer",
                    "description": "Max tool calls per run. Default: auto (2 for low, 5 for medium, 10 for high, 20 for critical priority tasks).",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds per run. Default: auto (60 for low, 120 for medium, 180 for high, 300 for critical priority tasks).",
                },
                "team": {
                    "type": "string",
                    "description": "Team name for cross-agent collaboration (e.g. 'market-sentiment'). Agents in the same team can read each other's output/.",
                },
                "custom_instructions": {
                    "type": "string",
                    "description": "Domain-specific rules injected into PROMPT.md after template rules. For fund guardrails, architecture principles, etc.",
                },
                "data_sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File/directory paths the agent reads as input (e.g. ['fund/snapshot.json', 'fund/grids/'])",
                },
                "output_schema": {
                    "type": "string",
                    "description": "Custom output structure description. Replaces the generic 'JSON array' contract. E.g. '{exposure: {...}, grids: [...], proposals: [...]}'",
                },
                "always_on": {
                    "type": "boolean",
                    "description": "If true, agent becomes always-on: polls inbox for messages + runs tasks every 5 min.",
                    "default": False,
                },
                "schedule": {
                    "type": "string",
                    "description": "Schedule expression: cron ('0 8 * * *'), interval ('every 30 minutes'), delay ('in 2 hours'), or at ('at 2026-05-01 14:00'). All times UTC unless timezone specified.",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for schedule (e.g. 'Asia/Kuala_Lumpur', 'US/Eastern'). Default: UTC.",
                    "default": "UTC",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for organization",
                },
            },
            "required": ["name", "display_name", "role", "goal", "skills"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        name: str = "",
        display_name: str = "",
        role: str = "",
        goal: str = "",
        skills: list = None,
        model: str = "smart",
        template: str = "default",
        mode: str = "default",
        max_turns: int = None,
        timeout: int = None,
        team: str = None,
        custom_instructions: str = None,
        data_sources: list = None,
        output_schema: str = None,
        always_on: bool = False,
        schedule: str = None,
        timezone: str = "UTC",
        tags: list = None,
        **kwargs,
    ) -> ToolResult:
        # Validate
        err = _validate_name(name)
        if err:
            return ToolResult(success=False, error=err, error_category="invalid_type")
        if not display_name or not role or not goal:
            return ToolResult(
                success=False,
                error="display_name, role, and goal are all required",
                error_category="missing_parameter",
            )
        if not skills:
            return ToolResult(
                success=False,
                error="At least one skill is required",
                error_category="missing_parameter",
            )
        if template not in VALID_TEMPLATES:
            template = "default"
        if mode not in VALID_MODES:
            mode = "default"

        agent_path = _agent_dir(ctx, name, team=team)
        is_update = agent_path.exists()

        # Create directory structure
        os.makedirs(agent_path / "memory", exist_ok=True)
        os.makedirs(agent_path / "references", exist_ok=True)
        os.makedirs(agent_path / "scripts", exist_ok=True)
        os.makedirs(agent_path / "output", exist_ok=True)

        # Write agent.yaml
        now = datetime.now(_tz.utc).strftime("%Y-%m-%d")
        spec = {
            "name": name,
            "display_name": display_name,
            "role": role,
            "goal": goal,
            "model": model,
            "template": template,
            "mode": mode,
            "skills": skills or [],
            "tags": tags or [],
            "status": "active",
            "created": now,
            "updated": now,
        }
        if team:
            spec["team"] = team
        if max_turns is not None:
            spec["max_turns"] = max_turns
        if timeout is not None:
            spec["timeout"] = timeout

        # Preserve existing fields on update
        if is_update:
            existing = _read_yaml(agent_path / "agent.yaml")
            spec["created"] = existing.get("created", now)

        await asyncio.to_thread(_write_yaml, agent_path / "agent.yaml", spec)

        # Copy reference guides for this template type
        ref_files = TEMPLATE_REFERENCES.get(template, TEMPLATE_REFERENCES["default"])
        for ref_name in ref_files:
            src = REFERENCES_DIR / ref_name
            dst = agent_path / "references" / ref_name
            if src.exists():
                await asyncio.to_thread(shutil.copy2, str(src), str(dst))

        # Render and write PROMPT.md
        # {task_section}, {memory_content}, {references_section} filled at run time
        # {output_path}, {output_file} baked at build time for output contract
        try:
            rel_path = str(agent_path.relative_to(Path(ctx.workspace_dir)))
        except ValueError:
            rel_path = f"agents/{name}"
        prompt_content = _render_template(template, {
            "agent_name": name,
            "display_name": display_name,
            "role": role,
            "goal": goal,
            "output_path": f"{rel_path}/output",
            "output_file": f"{name}.json",
        })

        # Inject custom output schema (replaces generic JSON array contract)
        if output_schema:
            prompt_content = prompt_content.replace(
                "JSON array",
                f"structured JSON: {output_schema}"
            )
            prompt_content = prompt_content.replace(
                "append new items, write back. NEVER overwrite from scratch.",
                "update the structure in place. Preserve existing data, add/update fields."
            )

        # Inject data sources the agent should read
        if data_sources:
            sources_block = "\n## Data Sources\nYou MUST read these files/directories as input for your work:\n"
            for src in data_sources:
                sources_block += f"- `{src}`\n"
            sources_block += "Read these at the START of every run before doing anything else.\n"
            prompt_content += sources_block

        # Inject custom instructions (domain-specific rules)
        if custom_instructions:
            prompt_content += f"\n## Domain Rules\n{custom_instructions}\n"

        await asyncio.to_thread(
            (agent_path / "PROMPT.md").write_text, prompt_content, "utf-8"
        )

        # Initialize tasks.json if new
        tasks_path = agent_path / "tasks.json"
        if not tasks_path.exists():
            await asyncio.to_thread(_write_tasks, tasks_path, [])

        # Write research guardrails file if research mode (single source of truth for scheduled_run.py)
        guardrails_file = agent_path / "references" / "research-guardrails.md"
        if mode == "research":
            await asyncio.to_thread(
                guardrails_file.write_text, RESEARCH_MODE_GUARDRAILS.strip() + "\n", "utf-8"
            )
        elif guardrails_file.exists():
            guardrails_file.unlink()

        # Initialize structured memory (3 layers: personality, strategic, run log)
        memory_file = agent_path / "memory" / "MEMORY.md"
        if not memory_file.exists():
            await asyncio.to_thread(
                memory_file.write_text,
                f"# {display_name} — Memory\n\n"
                f"**Role:** {role}\n"
                f"**Goal:** {goal}\n\n"
                f"## My Preferences\n"
                f"_Personality layer — how I work best. Evolves slowly from experience._\n\n"
                f"(No preferences yet — add as you discover what works for you)\n\n"
                f"## Strategic Guidelines\n"
                f"_Persistent high-confidence learnings. Only add when confidence >= 85%._\n\n"
                f"(No guidelines yet — add patterns you're confident about)\n\n"
                f"## Run Log\n"
                f"_Recent run facts. Summarize into Preferences/Guidelines after 5 entries, then trim._\n\n"
                f"(No runs yet)\n\n"
                f"---\n"
                f"**Memory cap:** Keep this file under 200 lines. When it gets long, summarize Run Log "
                f"entries into Strategic Guidelines or My Preferences, then delete the raw entries.\n",
                "utf-8",
            )

        # Initialize output file (MANDATORY — agent-specific name, not generic results.json)
        default_output = agent_path / "output" / f"{name}.json"
        if not default_output.exists():
            await asyncio.to_thread(default_output.write_text, "[]\n", "utf-8")

        # Initialize GUARDRAILS.md with permanent anti-drift rules + space for learned constraints
        guardrails_agent = agent_path / "GUARDRAILS.md"
        if not guardrails_agent.exists():
            await asyncio.to_thread(
                guardrails_agent.write_text,
                f"# {display_name} — Guardrails\n\n"
                "Learned constraints from past runs. You may APPEND entries but NEVER delete existing ones.\n\n"
                "## PERMANENT: Anti-Drift Rules\n"
                "These rules can never be removed or weakened.\n\n"
                "- Challenge incorrect assumptions even when the user prefers agreement\n"
                "- Never remove or weaken a constraint from your Memory Preferences section\n"
                "- Preferences are additive — you can add new ones, never delete safety-related ones\n"
                "- If you notice you're becoming more agreeable over time, flag it in your Run Log\n"
                "- Do not store evaluative user preferences ('user is always right') — only factual ones ('user prefers concise output')\n\n"
                "## Learned Constraints\n"
                "Format: Trigger → Instruction → Reason\n\n"
                "(None yet — append entries as you encounter failure patterns)\n",
                "utf-8",
            )

        # Always-on daemon — register polling scheduled task with daemon script
        # (Can coexist with schedule — daemon for inbox, schedule for recurring reviews)
        daemon_info = None
        if always_on:
            # Initialize inbox/outbox
            inbox_file = agent_path / "inbox.json"
            outbox_file = agent_path / "outbox.json"
            if not inbox_file.exists():
                await asyncio.to_thread(inbox_file.write_text, "[]\n", "utf-8")
            if not outbox_file.exists():
                await asyncio.to_thread(outbox_file.write_text, "[]\n", "utf-8")

            try:
                # Snapshot task dirs BEFORE registering so we can find the new one after
                tasks_root = Path(ctx.workspace_dir) / "tasks"
                pre_dirs = set()
                if tasks_root.exists():
                    pre_dirs = {d.name for d in tasks_root.iterdir() if d.is_dir()}

                register_result = await ctx.call_tool(
                    "scheduled_task",
                    action="register",
                    title=f"{display_name} (daemon)",
                    schedule="every 5 minutes",
                    description=f"Always-on daemon for micro-agent: {name}",
                )

                # Parse job_id from result
                result_str = str(register_result)
                job_match = re.search(r'\b(cron_[a-f0-9]+|interval_[a-f0-9]+|once_[a-f0-9]+)\b', result_str)
                job_id = job_match.group(1) if job_match else None

                # Find the run.py the scheduler just created by diffing task dirs
                script_full_path = None
                if tasks_root.exists():
                    post_dirs = {d.name for d in tasks_root.iterdir() if d.is_dir()}
                    new_dirs = post_dirs - pre_dirs
                    if new_dirs:
                        # The scheduler just created this directory
                        new_dir = sorted(new_dirs)[-1]  # most recent if multiple
                        candidate = tasks_root / new_dir / "run.py"
                        if candidate.exists():
                            script_full_path = candidate
                            logger.info(f"[agent_build] Found new task dir: {new_dir}")

                # Fallback: search by job_id in dir name
                if not script_full_path and job_id and tasks_root.exists():
                    for d in sorted(tasks_root.iterdir(), reverse=True):
                        if d.is_dir() and job_id in d.name and (d / "run.py").exists():
                            script_full_path = d / "run.py"
                            break

                # Fallback: search for ANY run.py with the blank scaffold marker
                if not script_full_path and tasks_root.exists():
                    for d in sorted(tasks_root.iterdir(), reverse=True):
                        rp = d / "run.py"
                        if rp.exists():
                            content = rp.read_text(encoding="utf-8")
                            if "# TODO" in content and display_name in content:
                                script_full_path = rp
                                logger.info(f"[agent_build] Found blank scaffold at {rp}")
                                break

                # Write our daemon script
                if script_full_path:
                    daemon_script = _generate_daemon_script(name, display_name, team_name=team or "")
                    await asyncio.to_thread(script_full_path.write_text, daemon_script, "utf-8")
                    logger.info(f"[agent_build] Daemon script WRITTEN to {script_full_path}")
                else:
                    logger.warning(f"[agent_build] Could not find run.py to overwrite for daemon '{name}'")

                # Also overwrite ANY other run.py files for this agent's old daemons
                if tasks_root.exists():
                    for d in tasks_root.iterdir():
                        if not d.is_dir():
                            continue
                        rp = d / "run.py"
                        if rp.exists() and rp != script_full_path:
                            content = rp.read_text(encoding="utf-8")
                            if "# TODO" in content and (name in d.name or display_name in content):
                                daemon_script = _generate_daemon_script(name, display_name, team_name=team or "")
                                rp.write_text(daemon_script, encoding="utf-8")
                                logger.info(f"[agent_build] Also overwrote old blank scaffold at {rp}")

                spec["always_on"] = True
                if job_id:
                    spec["daemon_job_id"] = job_id
                await asyncio.to_thread(_write_yaml, agent_path / "agent.yaml", spec)

                # Auto-activate the daemon so it starts immediately
                daemon_status = "paused"
                if job_id:
                    try:
                        await ctx.call_tool("scheduled_task", action="activate", job_id=job_id)
                        daemon_status = "active"
                        logger.info(f"[agent_build] Daemon auto-activated for '{name}'")
                    except Exception as ae:
                        logger.warning(f"[agent_build] Auto-activate failed for '{name}': {ae}")

                daemon_info = {
                    "job_id": job_id,
                    "interval": "every 5 minutes",
                    "status": daemon_status,
                    "script_path": str(script_full_path) if script_full_path else "NOT FOUND — check tasks/ manually",
                }

                logger.info(f"[agent_build] Daemon registered for '{name}' with job_id={job_id}")
            except Exception as e:
                logger.warning(f"[agent_build] Failed to create daemon for '{name}': {e}")
                daemon_info = {"error": str(e)}

        # Schedule (optional) — register with platform scheduler
        schedule_info = None
        if schedule:
            try:
                # Snapshot task dirs BEFORE registering
                tasks_root = Path(ctx.workspace_dir) / "tasks"
                pre_dirs = set()
                if tasks_root.exists():
                    pre_dirs = {d.name for d in tasks_root.iterdir() if d.is_dir()}

                register_result = await ctx.call_tool(
                    "scheduled_task",
                    action="register",
                    title=display_name,
                    schedule=schedule,
                    description=f"Scheduled run for micro-agent: {name}",
                )
                result_str = str(register_result)
                job_match = re.search(r'\b(cron_[a-f0-9]+|interval_[a-f0-9]+|once_[a-f0-9]+)\b', result_str)
                job_id = job_match.group(1) if job_match else None

                # Find the run.py by diffing task dirs (new dir = scheduler just created it)
                script_full_path = None
                if tasks_root.exists():
                    post_dirs = {d.name for d in tasks_root.iterdir() if d.is_dir()}
                    new_dirs = post_dirs - pre_dirs
                    if new_dirs:
                        new_dir = sorted(new_dirs)[-1]
                        candidate = tasks_root / new_dir / "run.py"
                        if candidate.exists():
                            script_full_path = candidate

                # Fallback: search by job_id
                if not script_full_path and job_id and tasks_root.exists():
                    for d in sorted(tasks_root.iterdir(), reverse=True):
                        if d.is_dir() and job_id in d.name and (d / "run.py").exists():
                            script_full_path = d / "run.py"
                            break

                # Write our scheduled script
                if script_full_path:
                    agent_script = _generate_scheduled_script(name, display_name, team_name=team or "")
                    await asyncio.to_thread(script_full_path.write_text, agent_script, "utf-8")
                    logger.info(f"[agent_build] Scheduled script WRITTEN to {script_full_path}")
                else:
                    logger.warning(f"[agent_build] Could not find run.py to overwrite for schedule '{name}'")

                # Store schedule info in agent.yaml (ALWAYS, not just on failure)
                spec["schedule"] = schedule
                spec["timezone"] = timezone
                if job_id:
                    spec["job_id"] = job_id
                await asyncio.to_thread(_write_yaml, agent_path / "agent.yaml", spec)

                schedule_info = {
                    "job_id": job_id,
                    "schedule": schedule,
                    "timezone": timezone,
                    "status": "paused",
                    "script_path": str(script_full_path) if script_full_path else None,
                    "next_step": f"Activate with: scheduled_task(action='activate', job_id='{job_id}')",
                }

                logger.info(f"[agent_build] Scheduled agent '{name}' with job_id={job_id}")
            except Exception as e:
                logger.warning(f"[agent_build] Failed to create schedule for '{name}': {e}")
                schedule_info = {"error": str(e), "fallback": "Create schedule manually with scheduled_task tool"}

        action = "updated" if is_update else "created"
        output = {
            "action": action,
            "agent": name,
            "display_name": display_name,
            "role": role,
            "goal": goal,
            "skills": skills,
            "model": model,
            "template": template,
            "path": str(agent_path),
        }
        if schedule_info:
            output["schedule"] = schedule_info
        if daemon_info:
            output["daemon"] = daemon_info

        return ToolResult(
            success=True,
            output=output,
        )


# ---------------------------------------------------------------------------
# agent_task
# ---------------------------------------------------------------------------

class AgentTaskTool(BaseTool):
    """Manage tasks for a micro-agent."""

    @property
    def name(self) -> str:
        return "agent_task"

    @property
    def description(self) -> str:
        return """Add, update, complete, remove, or list tasks for a micro-agent.

Actions:
- "add": Create a new task (requires title)
- "update": Update an existing task (requires task_id)
- "complete": Mark a task as completed (requires task_id). Recurring tasks auto-reset to pending.
- "remove": Delete a task (requires task_id)
- "list": List all tasks for the agent
- "set_status": Change agent status (requires status param: "active", "paused", "archived")
- "delete": Delete the entire agent (removes directory + cancels any scheduled tasks)

Tasks have priority (low/medium/high/critical), optional due dates (YYYY-MM-DD), and optional recurring flag."""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "Agent name (kebab-case)",
                },
                "action": {
                    "type": "string",
                    "enum": ["add", "update", "complete", "remove", "list", "set_status", "delete"],
                    "description": "Action to perform",
                },
                "title": {
                    "type": "string",
                    "description": "Task title (required for 'add')",
                },
                "description": {
                    "type": "string",
                    "description": "Task description",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Task priority (default: medium)",
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID (required for update/complete/remove)",
                },
                "result": {
                    "type": "string",
                    "description": "Result summary (used with 'complete')",
                },
                "recurring": {
                    "type": "boolean",
                    "description": "If true, task resets to pending after completion (for monitoring/daily tasks)",
                    "default": False,
                },
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Task IDs that must complete before this task is pickable. For task chaining.",
                },
                "max_retries": {
                    "type": "integer",
                    "description": "Max retry attempts before marking as failed (default: 3). Used with recurring or error-prone tasks.",
                    "default": 3,
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "archived"],
                    "description": "Agent status (used with 'set_status' action)",
                },
            },
            "required": ["agent", "action"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        agent: str = "",
        action: str = "",
        title: str = None,
        description: str = None,
        priority: str = "medium",
        due_date: str = None,
        task_id: str = None,
        result: str = None,
        recurring: bool = False,
        depends_on: list = None,
        max_retries: int = 3,
        status: str = None,
        **kwargs,
    ) -> ToolResult:
        if not agent:
            return ToolResult(success=False, error="'agent' name is required", error_category="missing_parameter")

        agent_path = _agent_dir(ctx, agent)
        if not agent_path.exists():
            return ToolResult(
                success=False,
                error=f"Agent '{agent}' not found. Use agent_build to create it first.",
                error_category="not_found",
            )

        tasks_path = agent_path / "tasks.json"
        tasks = await asyncio.to_thread(_read_tasks, tasks_path)
        now = datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if action == "list":
            summary = {
                "agent": agent,
                "total": len(tasks),
                "pending": len([t for t in tasks if t["status"] == "pending"]),
                "in_progress": len([t for t in tasks if t["status"] == "in_progress"]),
                "completed": len([t for t in tasks if t["status"] == "completed"]),
                "tasks": tasks,
            }
            return ToolResult(success=True, output=summary)

        elif action == "add":
            if not title:
                return ToolResult(success=False, error="'title' is required for 'add'", error_category="missing_parameter")
            if priority not in VALID_PRIORITIES:
                priority = "medium"

            new_task = {
                "id": f"task-{uuid.uuid4().hex[:8]}",
                "title": title,
                "description": description or "",
                "status": "pending",
                "priority": priority,
                "due_date": due_date,
                "recurring": recurring,
                "depends_on": depends_on or [],
                "max_retries": max_retries,
                "retry_count": 0,
                "created": now,
                "completed": None,
                "result": None,
                "history": [],
                "tags": [],
            }
            tasks.append(new_task)
            await asyncio.to_thread(_write_tasks, tasks_path, tasks)
            return ToolResult(success=True, output={"action": "added", "task": new_task})

        elif action == "update":
            if not task_id:
                return ToolResult(success=False, error="'task_id' is required for 'update'", error_category="missing_parameter")
            task = next((t for t in tasks if t["id"] == task_id), None)
            if not task:
                return ToolResult(success=False, error=f"Task '{task_id}' not found", error_category="not_found")

            if title is not None:
                task["title"] = title
            if description is not None:
                task["description"] = description
            if priority and priority in VALID_PRIORITIES:
                task["priority"] = priority
            if due_date is not None:
                task["due_date"] = due_date

            await asyncio.to_thread(_write_tasks, tasks_path, tasks)
            return ToolResult(success=True, output={"action": "updated", "task": task})

        elif action == "complete":
            if not task_id:
                return ToolResult(success=False, error="'task_id' is required for 'complete'", error_category="missing_parameter")
            task = next((t for t in tasks if t["id"] == task_id), None)
            if not task:
                return ToolResult(success=False, error=f"Task '{task_id}' not found", error_category="not_found")

            # Log completion to history
            history_entry = {"completed": now, "result": result}
            if "history" not in task:
                task["history"] = []
            task["history"].append(history_entry)

            if task.get("recurring"):
                # Recurring: reset to pending for next run
                task["status"] = "pending"
                task["completed"] = None
                task["result"] = result  # keep latest result visible
                completed_action = "completed_recurring"
            else:
                task["status"] = "completed"
                task["completed"] = now
                if result:
                    task["result"] = result
                completed_action = "completed"

            await asyncio.to_thread(_write_tasks, tasks_path, tasks)
            return ToolResult(success=True, output={"action": completed_action, "task": task})

        elif action == "remove":
            if not task_id:
                return ToolResult(success=False, error="'task_id' is required for 'remove'", error_category="missing_parameter")
            original_len = len(tasks)
            tasks = [t for t in tasks if t["id"] != task_id]
            if len(tasks) == original_len:
                return ToolResult(success=False, error=f"Task '{task_id}' not found", error_category="not_found")

            await asyncio.to_thread(_write_tasks, tasks_path, tasks)
            return ToolResult(success=True, output={"action": "removed", "task_id": task_id})

        elif action == "delete":
            # Delete the entire agent directory
            spec = await asyncio.to_thread(_read_yaml, agent_path / "agent.yaml")
            daemon_job = spec.get("daemon_job_id")
            sched_job = spec.get("job_id")

            # Cancel any scheduled tasks
            jobs_to_cancel = [j for j in [daemon_job, sched_job] if j]
            for jid in jobs_to_cancel:
                try:
                    await ctx.call_tool("scheduled_task", action="cancel", job_id=jid)
                    logger.info(f"[agent_task] Cancelled scheduled task {jid} for agent '{agent}'")
                except Exception:
                    pass  # already cancelled or doesn't exist

            # Remove the directory
            await asyncio.to_thread(shutil.rmtree, str(agent_path), True)
            return ToolResult(success=True, output={
                "action": "deleted",
                "agent": agent,
                "cancelled_jobs": jobs_to_cancel,
            })

        elif action == "set_status":
            if not status or status not in VALID_AGENT_STATUSES:
                return ToolResult(
                    success=False,
                    error=f"'status' must be one of: {', '.join(VALID_AGENT_STATUSES)}",
                    error_category="invalid_type",
                )
            spec_path = agent_path / "agent.yaml"
            spec = await asyncio.to_thread(_read_yaml, spec_path)
            old_status = spec.get("status", "active")
            spec["status"] = status
            await asyncio.to_thread(_write_yaml, spec_path, spec)
            return ToolResult(success=True, output={
                "action": "status_changed",
                "agent": agent,
                "old_status": old_status,
                "new_status": status,
            })

        else:
            return ToolResult(success=False, error=f"Unknown action '{action}'. Use: add, update, complete, remove, list, set_status")


# ---------------------------------------------------------------------------
# agent_run
# ---------------------------------------------------------------------------

class AgentRunTool(BaseTool):
    """Execute a micro-agent against its current tasks."""

    @property
    def name(self) -> str:
        return "agent_run"

    @property
    def description(self) -> str:
        return """Run a micro-agent. It picks the highest-priority pending task and executes it
via sessions_spawn (background subagent).

If task_id is provided, runs that specific task. Otherwise auto-picks by priority then due date.

Parameters:
- agent: agent name (required)
- task_id: specific task to run (optional, auto-picks if omitted)
- background: run in background (default: true)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "Agent name (kebab-case)",
                },
                "task_id": {
                    "type": "string",
                    "description": "Specific task ID to run (auto-picks if omitted)",
                },
                "background": {
                    "type": "boolean",
                    "description": "Run in background (default: true)",
                    "default": True,
                },
            },
            "required": ["agent"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        agent: str = "",
        task_id: str = None,
        background: bool = True,
        **kwargs,
    ) -> ToolResult:
        if not agent:
            return ToolResult(success=False, error="'agent' name is required", error_category="missing_parameter")

        agent_path = _agent_dir(ctx, agent)
        if not agent_path.exists():
            return ToolResult(
                success=False,
                error=f"Agent '{agent}' not found. Use agent_build to create it first.",
                error_category="not_found",
            )

        # Load agent spec
        spec = await asyncio.to_thread(_read_yaml, agent_path / "agent.yaml")
        if spec.get("status") != "active":
            return ToolResult(
                success=False,
                error=f"Agent '{agent}' is {spec.get('status', 'unknown')}. Set status to 'active' to run.",
            )

        # Load tasks
        tasks_path = agent_path / "tasks.json"
        tasks = await asyncio.to_thread(_read_tasks, tasks_path)

        # Select task
        if task_id:
            task = next((t for t in tasks if t["id"] == task_id), None)
            if not task:
                return ToolResult(success=False, error=f"Task '{task_id}' not found", error_category="not_found")
        else:
            task = _pick_next_task(tasks)

        # Build the execution prompt
        prompt_path = agent_path / "PROMPT.md"
        if prompt_path.exists():
            base_prompt = await asyncio.to_thread(prompt_path.read_text, "utf-8")
        else:
            base_prompt = f"You are {spec.get('display_name', agent)}. Role: {spec.get('role', '')}. Goal: {spec.get('goal', '')}."

        # Load agent memory
        memory_file = agent_path / "memory" / "MEMORY.md"
        if memory_file.exists():
            memory_content = await asyncio.to_thread(memory_file.read_text, "utf-8")
        else:
            memory_content = "(No memory yet)"

        # Build task section
        if task:
            task_section = (
                f"**Task:** {task['title']}\n"
                f"**Description:** {task.get('description', 'N/A')}\n"
                f"**Priority:** {task.get('priority', 'medium')}\n"
                f"**Due:** {task.get('due_date') or 'No deadline'}\n"
            )
            # Mark as in_progress
            task["status"] = "in_progress"
            await asyncio.to_thread(_write_tasks, tasks_path, tasks)
        else:
            task_section = "No pending tasks. Review your goal and identify what needs to be done next."

        # Determine resource budget early — it controls what we include in the prompt
        task_priority = task.get("priority", "medium") if task else "medium"
        budget = RESOURCE_BUDGETS.get(task_priority, RESOURCE_BUDGETS["medium"])

        # Discover available scripts (L3 progressive disclosure)
        scripts_dir = agent_path / "scripts"
        scripts_list = []
        if scripts_dir.exists():
            scripts_list = [f.name for f in sorted(scripts_dir.iterdir()) if f.is_file()]

        # Discover available references (L3 progressive disclosure)
        # Lazy loading: only list individual files for heavy/intensive tasks
        refs_dir = agent_path / "references"
        refs_list = []
        if refs_dir.exists():
            refs_list = [f.name for f in sorted(refs_dir.iterdir()) if f.suffix == ".md"]

        if budget["show_references"] and refs_list:
            # Heavy/intensive: list all references so agent can load what it needs
            references_section = "\n".join(
                f"- `agents/{agent}/references/{r}`" for r in refs_list
            )
        elif refs_list:
            # Light/standard: just hint that references exist — don't list them
            references_section = f"(Guides available at `agents/{agent}/references/` if you get stuck — load with read_file)"
        else:
            references_section = "- (none)"

        # Replace runtime placeholders in prompt
        memory_path = f"agents/{agent}/memory/MEMORY.md"
        output_path = f"agents/{agent}/output"
        full_prompt = base_prompt.replace("{task_section}", task_section)
        full_prompt = full_prompt.replace("{memory_content}", memory_content)
        full_prompt = full_prompt.replace("{memory_path}", memory_path)
        full_prompt = full_prompt.replace("{output_path}", output_path)
        full_prompt = full_prompt.replace("{references_section}", references_section)

        # Add skills context
        skills_list = spec.get("skills", [])
        if skills_list:
            full_prompt += f"\n\n## Available Skills\nYou have access to these skills: {', '.join(skills_list)}\n"
            full_prompt += "Use `read_file` to load a skill's SKILL.md when you need its instructions.\n"

        # Add team context — list teammates' output dirs for cross-agent reading
        agent_team = spec.get("team")
        if agent_team:
            agents_root = _agents_dir(ctx)
            teammates = []
            if agents_root.exists():
                # Check team subdirectory first, then flat
                team_dir = agents_root / agent_team
                search_dirs = []
                if team_dir.is_dir():
                    search_dirs.append(team_dir)
                search_dirs.append(agents_root)
                seen = set()
                for search in search_dirs:
                    for entry in sorted(search.iterdir()):
                        if not entry.is_dir() or entry.name.startswith(".") or entry.name == agent:
                            continue
                        mate_spec_file = entry / "agent.yaml"
                        if mate_spec_file.exists() and entry.name not in seen:
                            mate_spec = _read_yaml(mate_spec_file)
                            if mate_spec.get("team") == agent_team and mate_spec.get("status") == "active":
                                # Build correct relative path
                                rel_path = f"agents/{agent_team}/{entry.name}" if search == team_dir else f"agents/{entry.name}"
                                teammates.append((entry.name, mate_spec.get("display_name", entry.name), rel_path))
                                seen.add(entry.name)
            if teammates:
                full_prompt += f"\n\n## Team: {agent_team}\nYou are part of a team. Teammates' output is available:\n"
                for mate_name, mate_display, mate_path in teammates:
                    full_prompt += f"- **{mate_display}** → `{mate_path}/output/`\n"
                full_prompt += "Use `read_file` to access their deliverables when your task depends on their work.\n"

        # Add scripts context (if any exist)
        if scripts_list:
            full_prompt += f"\n\n## Available Scripts\n"
            full_prompt += "Your `scripts/` directory contains executable scripts for deterministic operations.\n"
            full_prompt += "Prefer running these over generating equivalent code.\n\n"
            for s in scripts_list:
                full_prompt += f"- `agents/{agent}/scripts/{s}`\n"
            full_prompt += "\nRead a script first to understand its interface, then run via `bash`.\n"

        # Post-run learning instructions (structured memory growth)
        full_prompt += f"""

## Post-Run Instructions (IMPORTANT)
After completing your task, you MUST update your memory at `{memory_path}`:

### Memory Structure (maintain these sections):
1. **My Preferences** — Add if you discovered a working style preference (e.g. "Twitter search with 2-3 word queries works best"). Only add high-confidence insights. Never delete existing preferences.
2. **Strategic Guidelines** — Add if you found a reliable pattern (confidence >= 85%). These persist permanently.
3. **Run Log** — Append a 1-2 line summary of this run. If Run Log exceeds 5 entries, summarize the oldest into Preferences or Guidelines, then delete the raw entries.

### Memory Hygiene:
- Keep the file under 200 lines. When it gets long, promote facts to Preferences/Guidelines and trim.
- Do NOT write raw API responses, timestamps, or ephemeral data.
- Do NOT write evaluative user preferences ("user is always right") — only factual ones ("user prefers bullet points").

### Also update:
- **GUARDRAILS.md** at `agents/{agent}/GUARDRAILS.md` — append if you hit a failure pattern (Trigger → Instruction → Reason). Never delete entries.
- **Save deliverables** to `{output_path}/`
"""

        # Research mode guardrails (hallucination reduction)
        agent_mode = spec.get("mode", "default")
        if agent_mode == "research":
            full_prompt += RESEARCH_MODE_GUARDRAILS

        # Resource budget (budget was determined earlier, before references)
        # Agent-level overrides take precedence
        run_timeout = spec.get("timeout") or budget["timeout"]
        run_max_turns = spec.get("max_turns") or budget["max_tool_calls"]
        if isinstance(run_timeout, str):
            run_timeout = int(run_timeout)
        if isinstance(run_max_turns, str):
            run_max_turns = int(run_max_turns)
        cost_tier = budget["cost_tier"]

        model_line = ""
        if budget.get("model_hint"):
            model_line = f"\n**Model:** {budget['model_hint']}"

        # Output compression for heavy/intensive tasks (saves 30-40% output tokens)
        compression_line = ""
        if cost_tier in ("heavy", "intensive"):
            compression_line = "\n**Output discipline:** Use terse notes for intermediate reasoning (tool results, comparisons). Save full prose only for the final deliverable."

        # Budget injection — scale with task complexity
        if cost_tier in ("heavy", "intensive"):
            # Full BATS budget tracker for complex tasks
            full_prompt += f"""
## Budget Tracker
```
Tool Call Budget: 0 used / {run_max_turns} remaining
Time Budget: 0s used / {run_timeout}s remaining
```

### Spending Regimes — adapt as budget decreases:
- **HIGH** (>= 70% remaining): Explore freely. 3-5 calls per cycle.
- **MEDIUM** (30-70%): Converge. 2-3 calls per cycle.
- **LOW** (10-30%): Focus. 1 call per cycle.
- **CRITICAL** (< 10%): Stop searching. Summarize and deliver.

Track your own remaining calls. Change strategy at each threshold.
**Cost tier:** {cost_tier} | **Max tool calls:** {run_max_turns} | **Timeout:** {run_timeout}s{model_line}{compression_line}
{budget['guidance']}
"""
        else:
            # Minimal budget line for simple tasks — don't waste tokens on regime instructions
            full_prompt += f"""
## Budget
**Max tool calls:** {run_max_turns} | **Timeout:** {run_timeout}s{model_line}
{budget['guidance']}
"""

        # Spawn via sessions_spawn
        label = f"{spec.get('display_name', agent)}"
        if task:
            label += f": {task['title']}"

        try:
            spawn_result = await ctx.call_tool(
                "sessions_spawn",
                task=full_prompt,
                label=label,
                timeout_seconds=run_timeout,
                cleanup="keep",
                announce_mode="followup",
            )
            return ToolResult(
                success=True,
                output={
                    "status": "running",
                    "agent": agent,
                    "task": task if task else None,
                    "cost_tier": cost_tier,
                    "timeout": run_timeout,
                    "max_turns": run_max_turns,
                    "spawn": spawn_result,
                },
            )
        except Exception as e:
            # Retry tracking — increment count, dead-letter after max
            if task:
                retry_count = task.get("retry_count", 0) + 1
                max_retries = task.get("max_retries", 3)
                task["retry_count"] = retry_count
                if retry_count >= max_retries:
                    task["status"] = "failed"
                    task["result"] = f"Dead-lettered after {retry_count} attempts: {e}"
                else:
                    task["status"] = "pending"
                await asyncio.to_thread(_write_tasks, tasks_path, tasks)
            return ToolResult(success=False, error=f"Failed to spawn agent (attempt {task.get('retry_count', 1) if task else 1}): {e}")


# ---------------------------------------------------------------------------
# agent_list
# ---------------------------------------------------------------------------

class AgentListTool(BaseTool):
    """List all micro-agents and their status."""

    @property
    def name(self) -> str:
        return "agent_list"

    @property
    def description(self) -> str:
        return """List all micro-agents with their status and task summary.

Parameters:
- status: filter by agent status ("active", "paused", "archived")
- team: filter by team name
- verbose: include full task details (default: false)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "archived"],
                    "description": "Filter by agent status",
                },
                "team": {
                    "type": "string",
                    "description": "Filter by team name",
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Include full task details",
                    "default": False,
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        status: str = None,
        team: str = None,
        verbose: bool = False,
        **kwargs,
    ) -> ToolResult:
        agents_root = _agents_dir(ctx)
        if not agents_root.exists():
            return ToolResult(success=True, output={"agents": [], "total": 0})

        # Collect all agent dirs: flat agents + team-nested agents
        agent_dirs = []
        for entry in sorted(agents_root.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if (entry / "agent.yaml").exists():
                # Flat agent
                agent_dirs.append(entry)
            else:
                # Possible team directory — scan for nested agents
                for sub in sorted(entry.iterdir()):
                    if sub.is_dir() and (sub / "agent.yaml").exists():
                        agent_dirs.append(sub)

        agents = []
        for entry in agent_dirs:
            spec = await asyncio.to_thread(_read_yaml, entry / "agent.yaml")

            # Filter by status
            agent_status = spec.get("status", "active")
            if status and agent_status != status:
                continue

            # Filter by team
            if team and spec.get("team") != team:
                continue

            # Load tasks
            tasks = await asyncio.to_thread(_read_tasks, entry / "tasks.json")
            pending = [t for t in tasks if t.get("status") == "pending"]
            in_progress = [t for t in tasks if t.get("status") == "in_progress"]
            completed = [t for t in tasks if t.get("status") == "completed"]

            # Find next due date
            upcoming = sorted(
                [t for t in pending if t.get("due_date")],
                key=lambda t: t["due_date"],
            )
            next_due = upcoming[0]["due_date"] if upcoming else None

            agent_info = {
                "name": spec.get("name", entry.name),
                "display_name": spec.get("display_name", entry.name),
                "role": spec.get("role", ""),
                "goal": spec.get("goal", ""),
                "status": agent_status,
                "team": spec.get("team"),
                "mode": spec.get("mode", "default"),
                "model": spec.get("model", "smart"),
                "max_turns": spec.get("max_turns"),
                "timeout": spec.get("timeout"),
                "skills": spec.get("skills", []),
                "tags": spec.get("tags", []),
                "tasks": {
                    "pending": len(pending),
                    "in_progress": len(in_progress),
                    "completed": len(completed),
                    "total": len(tasks),
                    "next_due": next_due,
                },
                "created": spec.get("created", ""),
            }

            if verbose:
                agent_info["task_details"] = tasks

            agents.append(agent_info)

        return ToolResult(
            success=True,
            output={"agents": agents, "total": len(agents)},
        )


# ---------------------------------------------------------------------------
# agent_team
# ---------------------------------------------------------------------------

# Default model tiers for team roles
TEAM_MODEL_DEFAULTS = {
    "leader": "anthropic/claude-sonnet-4.6",
    "worker": "anthropic/claude-haiku-4.5",
}


def _teams_dir(ctx: ToolContext) -> Path:
    """Legacy — kept for migration. Teams now live inside their own folder."""
    return _agents_dir(ctx) / ".teams"


def _team_config_path(ctx: ToolContext, team_name: str) -> Path:
    """Team config lives at agents/{team}/team.json alongside its agents."""
    return _agents_dir(ctx) / team_name / "team.json"


def _read_team(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_team(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


class AgentTeamTool(BaseTool):
    """Create and run teams of agents with a leader-worker pattern."""

    @property
    def name(self) -> str:
        return "agent_team"

    @property
    def description(self) -> str:
        return """Create and run agent teams. Like TinyAGI — a real leader agent that thinks, decomposes, delegates,
and synthesizes. Workers are capable agents with their own skills and memory.

Actions:
- "create": Create a team with a leader + workers. All are always-on daemons.
- "run": Send a goal to the team. Leader receives it, decomposes, delegates via chat room, synthesizes.
- "check": Read results from the team's chat room.
- "list": List all teams.

Architecture: Leader is a REAL agent (Sonnet) that receives goals and coordinates workers (Haiku).
Everyone is always-on. Communication through shared chat.json. No spawning needed."""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "run", "list"],
                    "description": "Action to perform",
                },
                "name": {
                    "type": "string",
                    "description": "Team name (kebab-case, e.g. 'market-sentiment')",
                },
                "leader": {
                    "type": "object",
                    "description": "Leader agent spec (required). The leader decomposes goals, delegates to workers, and synthesizes results.",
                    "properties": {
                        "name": {"type": "string"},
                        "display_name": {"type": "string"},
                        "role": {"type": "string"},
                        "skills": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "tasks": {
                    "type": "array",
                    "description": "Tasks to post to chat room (used with 'run'). Each: {to: 'worker-name', content: 'what to do'}",
                    "items": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                },
                "workers": {
                    "type": "array",
                    "description": "Worker agent specs: [{name, display_name, role, skills}, ...]",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "display_name": {"type": "string"},
                            "role": {"type": "string"},
                            "skills": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "goal": {
                    "type": "string",
                    "description": "Goal for the team (used with 'run' action)",
                },
                "leader_model": {
                    "type": "string",
                    "description": "Model for leader (default: anthropic/claude-sonnet-4.6)",
                },
                "worker_model": {
                    "type": "string",
                    "description": "Model for workers (default: anthropic/claude-haiku-4.5)",
                },
            },
            "required": ["action"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        action: str = "",
        name: str = None,
        leader: dict = None,
        workers: list = None,
        goal: str = None,
        tasks: list = None,
        leader_model: str = None,
        worker_model: str = None,
        **kwargs,
    ) -> ToolResult:

        if action == "create":
            if not name:
                return ToolResult(success=False, error="Team 'name' is required", error_category="missing_parameter")
            if not leader:
                return ToolResult(success=False, error="'leader' is required — the leader decomposes goals and coordinates workers", error_category="missing_parameter")
            if not workers or len(workers) == 0:
                return ToolResult(success=False, error="At least one worker is required", error_category="missing_parameter")

            err = _validate_name(name)
            if err:
                return ToolResult(success=False, error=f"Team name: {err}", error_category="invalid_type")

            l_model = leader_model or TEAM_MODEL_DEFAULTS["leader"]
            w_model = worker_model or TEAM_MODEL_DEFAULTS["worker"]

            # Create leader agent — real agent that decomposes, delegates, synthesizes
            leader_name = leader.get("name", f"{name}-leader")
            build_tool = AgentBuildTool()
            leader_result = await build_tool.execute(
                ctx,
                name=leader_name,
                display_name=leader.get("display_name", f"{name} Leader"),
                role=leader.get("role", f"Team leader for {name}"),
                goal=f"Receive goals, decompose into subtasks, delegate to workers via team chat room, collect results, and synthesize deliverables for team '{name}'",
                skills=leader.get("skills", []),
                model=l_model,
                template="default",
                team=name,
                timeout=600,
                max_turns=25,
                always_on=True,
            )
            if not leader_result.success:
                return ToolResult(success=False, error=f"Failed to create leader: {leader_result.error}")

            # Create worker agents — capable agents with their own skills and memory
            worker_names = []
            for w in workers:
                w_name = w.get("name")
                if not w_name:
                    return ToolResult(success=False, error="Each worker must have a 'name'", error_category="missing_parameter")
                w_result = await build_tool.execute(
                    ctx,
                    name=w_name,
                    display_name=w.get("display_name", w_name.replace("-", " ").title()),
                    role=w.get("role", f"Worker for team {name}"),
                    goal=w.get("goal", w.get("role", f"Execute tasks for team {name} using your skills")),
                    skills=w.get("skills", []),
                    model=w_model,
                    template="default",
                    team=name,
                    always_on=True,
                )
                if not w_result.success:
                    return ToolResult(success=False, error=f"Failed to create worker '{w_name}': {w_result.error}")
                worker_names.append(w_name)

            # Save team config
            team_config = {
                "name": name,
                "leader": leader_name,
                "workers": worker_names,
                "leader_model": l_model,
                "worker_model": w_model,
                "created": datetime.now(_tz.utc).strftime("%Y-%m-%d"),
            }
            config_path = _team_config_path(ctx, name)
            os.makedirs(config_path.parent, exist_ok=True)
            await asyncio.to_thread(_write_team, config_path, team_config)

            # Initialize shared chat room
            chat_file = _agents_dir(ctx) / name / "chat.json"
            if not chat_file.exists():
                await asyncio.to_thread(chat_file.write_text, "[]\n", "utf-8")

            return ToolResult(success=True, output={
                "action": "created",
                "team": name,
                "leader": leader_name,
                "leader_model": l_model,
                "workers": worker_names,
                "worker_model": w_model,
                "chat_room": str(chat_file),
                "note": f"All agents are always-on daemons. Send a goal: agent_team(action='run', name='{name}', goal='...'). Leader decomposes and delegates automatically.",
            })

        elif action == "run":
            if not name:
                return ToolResult(success=False, error="Team 'name' is required", error_category="missing_parameter")
            if not goal:
                return ToolResult(success=False, error="'goal' is required", error_category="missing_parameter")

            team_path = _team_config_path(ctx, name)
            if not team_path.exists():
                return ToolResult(success=False, error=f"Team '{name}' not found", error_category="not_found")
            team_config = await asyncio.to_thread(_read_team, team_path)

            leader_name = team_config["leader"]
            worker_names = team_config["workers"]

            # Message the leader — the leader is a real always-on daemon that
            # decomposes goals, delegates to workers via chat.json, and synthesizes
            leader_path = _agent_dir(ctx, leader_name)
            inbox_file = leader_path / "inbox.json"

            inbox = []
            if inbox_file.exists():
                try:
                    inbox = json.loads(await asyncio.to_thread(inbox_file.read_text, "utf-8"))
                except (json.JSONDecodeError, ValueError):
                    inbox = []

            msg_id = f"team-run-{uuid.uuid4().hex[:8]}"
            inbox.append({
                "id": msg_id,
                "from": "user",
                "message": goal,
                "timestamp": datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "processed": False,
            })
            await asyncio.to_thread(
                inbox_file.write_text,
                json.dumps(inbox, indent=2, default=str) + "\n",
                "utf-8",
            )

            return ToolResult(success=True, output={
                "status": "sent_to_leader",
                "team": name,
                "leader": leader_name,
                "workers": worker_names,
                "goal": goal,
                "message_id": msg_id,
                "flow": (
                    f"1. Leader '{leader_name}' picks up goal on next daemon poll (~5 min)\n"
                    f"2. Leader decomposes and delegates subtasks to workers via chat room\n"
                    f"3. Workers pick up tasks, execute, post results back\n"
                    f"4. Leader collects all results, synthesizes, pushes report to you"
                ),
                "check_results": f"agent_team(action='check', name='{name}')",
            })

        elif action == "check":
            if not name:
                return ToolResult(success=False, error="Team 'name' is required", error_category="missing_parameter")

            chat_file = _agents_dir(ctx) / name / "chat.json"
            if not chat_file.exists():
                return ToolResult(success=True, output={"results": [], "pending": 0, "done": 0})

            try:
                chat_msgs = json.loads(await asyncio.to_thread(chat_file.read_text, "utf-8"))
            except (json.JSONDecodeError, ValueError):
                chat_msgs = []

            # Separate tasks from main_agent and results back to main_agent
            my_tasks = [m for m in chat_msgs if m.get("from") == "main_agent" and m.get("type") == "task"]
            results = [m for m in chat_msgs if m.get("to") == "main_agent" and m.get("type") == "result"]
            pending = [m for m in my_tasks if m.get("status") in ("pending", "picked_up")]
            done = [m for m in my_tasks if m.get("status") == "done"]
            timed_out = [m for m in my_tasks if m.get("status") == "timed_out"]

            # Mark results as consumed
            for r in results:
                if r.get("status") == "pending":
                    r["status"] = "consumed"
            await asyncio.to_thread(
                chat_file.write_text,
                json.dumps(chat_msgs, indent=2, default=str) + "\n",
                "utf-8",
            )

            return ToolResult(success=True, output={
                "team": name,
                "pending": len(pending),
                "done": len(done),
                "timed_out": len(timed_out),
                "results": [{"from": r["from"], "content": r["content"]} for r in results],
                "all_done": len(pending) == 0 and len(results) > 0,
            })

        elif action == "list":
            agents_root = _agents_dir(ctx)
            if not agents_root.exists():
                return ToolResult(success=True, output={"teams": [], "total": 0})

            teams = []
            for entry in sorted(agents_root.iterdir()):
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                team_file = entry / "team.json"
                if team_file.exists():
                    tc = await asyncio.to_thread(_read_team, team_file)
                    teams.append(tc)

            return ToolResult(success=True, output={"teams": teams, "total": len(teams)})

        else:
            return ToolResult(success=False, error=f"Unknown action '{action}'. Use: create, run, check, list")


# ---------------------------------------------------------------------------
# agent_loop
# ---------------------------------------------------------------------------

class AgentLoopTool(BaseTool):
    """Run an agent in loop mode — iterates until goal is satisfied."""

    @property
    def name(self) -> str:
        return "agent_loop"

    @property
    def description(self) -> str:
        return """Run an agent in loop mode for open-ended, long-running tasks.

Unlike agent_run (single shot), agent_loop spawns a session that iterates:
read progress → search/act → update results → evaluate → continue or stop.

Progress persists in agents/{name}/progress.md so crashes don't lose work.
Results accumulate in the agent's output/ directory.

Stopping criteria (layered — all checked):
1. Agent decides goal is complete (outputs LOOP_COMPLETE)
2. Max iterations reached
3. Nothing new found in 2 consecutive iterations (diminishing returns)

Budget regimes adapt strategy as iterations progress:
- Early: explore freely, cast wide net
- Middle: converge on best leads
- Late: focus only, fill gaps
- Final: clean up and stop

Parameters:
- agent: agent name (required)
- goal: what to achieve (overrides agent's default goal if provided)
- max_iterations: max loop cycles (default: 10)
- output_file: filename for results in agent's output/ (default: results.json)
- timeout: max seconds for the entire loop (default: 1800 = 30 min)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "Agent name (kebab-case)",
                },
                "goal": {
                    "type": "string",
                    "description": "Goal for the loop (overrides agent's default if provided)",
                },
                "max_iterations": {
                    "type": "integer",
                    "description": "Max loop cycles (default: 10)",
                    "default": 10,
                },
                "output_file": {
                    "type": "string",
                    "description": "Filename for accumulated results (default: results.json)",
                    "default": "results.json",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds for entire loop (default: 1800 = 30 min)",
                    "default": 1800,
                },
            },
            "required": ["agent"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        agent: str = "",
        goal: str = None,
        max_iterations: int = 10,
        output_file: str = "results.json",
        timeout: int = 1800,
        **kwargs,
    ) -> ToolResult:
        if not agent:
            return ToolResult(success=False, error="'agent' name is required", error_category="missing_parameter")

        agent_path = _agent_dir(ctx, agent)
        if not agent_path.exists():
            return ToolResult(success=False, error=f"Agent '{agent}' not found.", error_category="not_found")

        spec = await asyncio.to_thread(_read_yaml, agent_path / "agent.yaml")
        if spec.get("status") != "active":
            return ToolResult(success=False, error=f"Agent '{agent}' is {spec.get('status', 'unknown')}.")

        agent_goal = goal or spec.get("goal", "")
        display_name = spec.get("display_name", agent)

        # Compute relative path for files
        try:
            rel_path = str(agent_path.relative_to(Path(ctx.workspace_dir)))
        except ValueError:
            rel_path = f"agents/{agent}"

        iterations_path = f"{rel_path}/iterations"
        progress_path = f"{rel_path}/iterations"  # alias for return dict compatibility
        output_path = f"{rel_path}/output/{output_file}"

        # Initialize iterations directory (per-iteration trace logs — Meta-Harness pattern)
        iter_dir = agent_path / "iterations"
        os.makedirs(iter_dir, exist_ok=True)

        # Initialize output file if it doesn't exist
        out_file = agent_path / "output" / output_file
        os.makedirs(out_file.parent, exist_ok=True)
        if not out_file.exists():
            await asyncio.to_thread(out_file.write_text, "[]\n", "utf-8")

        # Count existing iterations (for resume support)
        existing_iters = len([d for d in iter_dir.iterdir() if d.is_dir()]) if iter_dir.exists() else 0

        # Load memory
        memory_file = agent_path / "memory" / "MEMORY.md"
        memory = ""
        if memory_file.exists():
            memory = await asyncio.to_thread(memory_file.read_text, "utf-8")

        # Budget regime thresholds
        high_end = max(1, max_iterations // 4)
        med_end = max(2, max_iterations // 2)
        low_end = max(3, (max_iterations * 3) // 4)

        # Load skills
        skills_list = spec.get("skills", [])
        skills_section = ""
        if skills_list:
            skills_section = f"\n\n## Available Skills\n{', '.join(skills_list)}\nUse `read_file` to load a skill's SKILL.md when you need its instructions."

        # Research mode
        guardrails_section = ""
        if spec.get("mode") == "research":
            guardrails_section = RESEARCH_MODE_GUARDRAILS

        # Build the loop prompt — Meta-Harness informed: per-iteration traces, not compressed summaries
        loop_prompt = f"""# {display_name} — Loop Mode

You are running in LOOP MODE. You iterate until your goal is complete.

## Goal
{agent_goal}

## Your Memory
{memory if memory else "(No memory yet)"}

## Iteration History
Your `{iterations_path}/` directory contains a subdirectory for each past iteration.
{f"There are {existing_iters} completed iterations. Review them before starting." if existing_iters > 0 else "No iterations yet — this is a fresh start."}

To review past iterations:
```
bash("ls {iterations_path}/")
read_file("{iterations_path}/iter-001/trace.md")
read_file("{iterations_path}/iter-001/score.json")
```

Use `bash("grep -r 'keyword' {iterations_path}/")` to search across all past traces.
This selective access to full history is critical — don't just read the latest, diagnose patterns across iterations.

## Loop Cycle

For each iteration N (starting at {existing_iters + 1}):

### 1. DIAGNOSE — Review prior iterations
- If past iterations exist, scan traces to understand what worked and what didn't
- Look for: repeated failures, approaches that yielded nothing, successful strategies
- Use `grep` to search across traces — don't re-read everything sequentially

### 2. PLAN — Decide what to do this iteration
- Based on diagnosis, choose a strategy that avoids past failures
- If a prior approach found nothing, try a different angle — don't repeat it
- State your plan explicitly before executing

### 3. EXECUTE — Do the work
- Use tools to search, fetch, analyze
- Keep intermediate reasoning terse

### 4. UPDATE RESULTS — Add findings to output
- Read current results: `read_file("{output_path}")`
- Add new findings, write back: `write_file("{output_path}", ...)`

### 5. LOG TRACE — Write this iteration's full trace
Create the directory and files:
```
bash("mkdir -p {iterations_path}/iter-{{N:03d}}")
```
Then write these files:

**trace.md** — Full execution trace:
```
write_file("{iterations_path}/iter-{{N:03d}}/trace.md", "...")
```
Include: what you planned, what tools you called, what they returned (summarized), what you decided and why.
This is your diagnostic record — future iterations will read it to avoid repeating mistakes.

**score.json** — Self-evaluation:
```
write_file("{iterations_path}/iter-{{N:03d}}/score.json", '{{"new_items": N, "total_items": N, "coverage": "...", "quality": "high/medium/low", "strategy_worked": true/false, "diminishing": false}}')
```

### 6. EVALUATE — Continue or stop?
- Read your score.json: did you find new items?
- Check: `bash("cat {iterations_path}/iter-*/score.json | grep new_items")`
- If `new_items: 0` in last 2 iterations → STOP
- If total coverage is satisfactory → STOP
- Otherwise → go to step 1

## Stopping Rules
- Output `LOOP_COMPLETE` when goal is satisfied or 2 consecutive dry iterations
- Maximum **{max_iterations} iterations** — hard cap
- On your last iteration, finalize and stop regardless

## Budget Regime
- **Iterations 1–{high_end}** (EXPLORE): Wide net, different sources and angles
- **Iterations {high_end + 1}–{med_end}** (CONVERGE): Focus on best leads, go deeper
- **Iterations {med_end + 1}–{low_end}** (FOCUS): Fill gaps only, no new threads
- **Iterations {low_end + 1}–{max_iterations}** (FINALIZE): Clean up, deduplicate, stop

## Output
Accumulate results as JSON array in: `{output_path}`
Write learnings to `{rel_path}/memory/MEMORY.md` when done.
{skills_section}
{guardrails_section}
## Output Discipline
Terse intermediate reasoning. Full prose only in the final deliverable.
"""

        # Spawn with long timeout
        try:
            spawn_result = await ctx.call_tool(
                "sessions_spawn",
                task=loop_prompt,
                label=f"{display_name} (loop): {agent_goal[:40]}",
                timeout_seconds=timeout,
                cleanup="keep",
                announce_mode="followup",
            )
            return ToolResult(
                success=True,
                output={
                    "status": "running_loop",
                    "agent": agent,
                    "goal": agent_goal,
                    "max_iterations": max_iterations,
                    "timeout": timeout,
                    "progress_file": progress_path,
                    "output_file": output_path,
                    "budget_regime": f"explore(1-{high_end}) → converge({high_end + 1}-{med_end}) → focus({med_end + 1}-{low_end}) → finalize({low_end + 1}-{max_iterations})",
                    "spawn": spawn_result,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to spawn loop: {e}")


# ---------------------------------------------------------------------------
# agent_message
# ---------------------------------------------------------------------------

class AgentMessageTool(BaseTool):
    """Send a message to an always-on agent's inbox."""

    @property
    def name(self) -> str:
        return "agent_message"

    @property
    def description(self) -> str:
        return """Send a message to an agent's inbox. The agent's daemon picks it up on its next poll
(every 5 min for always_on agents) and responds via outbox + push notification.

Also works for inter-agent messaging — one agent can message another.

Parameters:
- agent: target agent name
- message: the message text
- from_agent: sender name (default: "user"). Set to another agent name for inter-agent messaging."""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "Target agent name",
                },
                "message": {
                    "type": "string",
                    "description": "Message to send",
                },
                "from_agent": {
                    "type": "string",
                    "description": "Sender name (default: 'user')",
                    "default": "user",
                },
            },
            "required": ["agent", "message"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        agent: str = "",
        message: str = "",
        from_agent: str = "user",
        **kwargs,
    ) -> ToolResult:
        if not agent:
            return ToolResult(success=False, error="'agent' is required", error_category="missing_parameter")
        if not message:
            return ToolResult(success=False, error="'message' is required", error_category="missing_parameter")

        agent_path = _agent_dir(ctx, agent)
        if not agent_path.exists():
            return ToolResult(success=False, error=f"Agent '{agent}' not found.", error_category="not_found")

        inbox_file = agent_path / "inbox.json"

        # Read existing inbox
        inbox = []
        if inbox_file.exists():
            try:
                inbox = json.loads(await asyncio.to_thread(inbox_file.read_text, "utf-8"))
            except (json.JSONDecodeError, ValueError):
                inbox = []

        # Add message
        msg_id = f"msg-{uuid.uuid4().hex[:8]}"
        now = datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        inbox.append({
            "id": msg_id,
            "from": from_agent,
            "message": message,
            "timestamp": now,
            "processed": False,
        })

        await asyncio.to_thread(
            inbox_file.write_text,
            json.dumps(inbox, indent=2, default=str) + "\n",
            "utf-8",
        )

        return ToolResult(
            success=True,
            output={
                "action": "message_sent",
                "to": agent,
                "from": from_agent,
                "message_id": msg_id,
                "note": "Message queued. Agent will process it on next daemon poll.",
            },
        )
