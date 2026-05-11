#!/usr/bin/env python3
# -*- task-system: v3 -*-
"""
Scheduled runner for: __DISPLAY_NAME__
Agent: __AGENT_NAME__
"""
import requests, os, json, sys, re
from datetime import datetime, timezone as tz

JOB_ID = os.environ.get("JOB_ID")
AGENT_NAME = "__AGENT_NAME__"
AGENT_TEAM = "__TEAM_NAME__"
WORKSPACE = os.environ.get("WORKSPACE_DIR", os.environ.get("PWD", "."))
BASE_URL = "http://localhost:8000"

# Resolve agent directory — exact path baked at build time
if AGENT_TEAM:
    AGENT_DIR = os.path.join(WORKSPACE, "agents", AGENT_TEAM, AGENT_NAME)
else:
    AGENT_DIR = os.path.join(WORKSPACE, "agents", AGENT_NAME)

# Verify agent.yaml exists, otherwise search
if not os.path.exists(os.path.join(AGENT_DIR, "agent.yaml")):
    agents_root = os.path.join(WORKSPACE, "agents")
    found = False
    if os.path.isdir(agents_root):
        flat = os.path.join(agents_root, AGENT_NAME, "agent.yaml")
        if os.path.exists(flat):
            AGENT_DIR = os.path.join(agents_root, AGENT_NAME)
            found = True
        else:
            for d in os.listdir(agents_root):
                candidate = os.path.join(agents_root, d, AGENT_NAME, "agent.yaml")
                if os.path.exists(candidate):
                    AGENT_DIR = os.path.join(agents_root, d, AGENT_NAME)
                    found = True
                    break
    if not found:
        print(f"Agent directory not found for {AGENT_NAME}", file=sys.stderr)
        sys.exit(0)

RESPONSE_FORMAT = '\n\nIMPORTANT: You must respond with ONLY a JSON object, no markdown fences, no other text:\n{"summary": "<short one-line title>", "content": "<full detailed response>"}'


def push(message, channel="all", title=None):
    payload = {"message": message, "channel": channel, "job_id": JOB_ID}
    if title:
        payload["title"] = title
    try:
        requests.post(f"{BASE_URL}/push", json=payload, timeout=10)
    except Exception as e:
        print(f"Push failed: {e}", file=sys.stderr)


def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def read_yaml_simple(path):
    """Read flat key:value YAML."""
    data = {}
    content = read_file(path)
    current_key = None
    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("- ") and current_key and isinstance(data.get(current_key), list):
            data[current_key].append(s[2:].strip().strip("'\""))
            continue
        if ":" in s:
            k, _, v = s.partition(":")
            k, v = k.strip(), v.strip().strip("'\"")
            if not v:
                data[k] = []
                current_key = k
            elif v.lower() == "true":
                data[k] = True
            elif v.lower() == "false":
                data[k] = False
            else:
                data[k] = v
            if v:
                current_key = k
    return data


def extract_json_response(text):
    """Parse JSON from agent response, handling markdown fences."""
    if not text:
        return None
    s = text.strip()
    fence = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(s[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


def main():
    # 1. Load agent spec
    spec = read_yaml_simple(os.path.join(AGENT_DIR, "agent.yaml"))
    if spec.get("status") != "active":
        print(f"Agent {AGENT_NAME} is {spec.get('status', 'unknown')}, skipping", file=sys.stderr)
        return

    # 2. Pick next pending task
    tasks_path = os.path.join(AGENT_DIR, "tasks.json")
    try:
        with open(tasks_path) as f:
            tasks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        tasks = []

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    pending = [t for t in tasks if t.get("status") == "pending"]
    pending.sort(key=lambda t: (
        priority_order.get(t.get("priority", "medium"), 2),
        t.get("due_date") or "9999-12-31",
    ))
    task = pending[0] if pending else None

    if task:
        task_section = (
            f"**Task:** {task['title']}\n"
            f"**Description:** {task.get('description', 'N/A')}\n"
            f"**Priority:** {task.get('priority', 'medium')}\n"
            f"**Due:** {task.get('due_date') or 'No deadline'}"
        )
        task["status"] = "in_progress"
        with open(tasks_path, "w") as f:
            json.dump(tasks, f, indent=2)
    else:
        task_section = "No pending tasks. Review your goal and identify what needs to be done next."

    # 3. Build prompt from PROMPT.md + runtime context
    base_prompt = read_file(os.path.join(AGENT_DIR, "PROMPT.md"))
    memory = read_file(os.path.join(AGENT_DIR, "memory", "MEMORY.md")) or "(No memory yet)"
    memory_path = f"agents/{AGENT_NAME}/memory/MEMORY.md"
    output_path = f"agents/{AGENT_NAME}/output"

    # References
    refs_dir = os.path.join(AGENT_DIR, "references")
    refs = sorted(f for f in os.listdir(refs_dir) if f.endswith(".md")) if os.path.isdir(refs_dir) else []
    refs_section = "\n".join(f"- `agents/{AGENT_NAME}/references/{r}`" for r in refs) if refs else "- (none)"

    # Scripts
    scripts_dir = os.path.join(AGENT_DIR, "scripts")
    scripts = sorted(f for f in os.listdir(scripts_dir) if os.path.isfile(os.path.join(scripts_dir, f))) if os.path.isdir(scripts_dir) else []

    prompt = base_prompt
    prompt = prompt.replace("{task_section}", task_section)
    prompt = prompt.replace("{memory_content}", memory)
    prompt = prompt.replace("{memory_path}", memory_path)
    prompt = prompt.replace("{output_path}", output_path)
    prompt = prompt.replace("{references_section}", refs_section)

    # Skills
    skills = spec.get("skills", [])
    if isinstance(skills, str):
        skills = [skills]
    if skills:
        prompt += f"\n\n## Available Skills\nYou have access to: {', '.join(skills)}\nUse read_file to load a skill's SKILL.md.\n"

    # Scripts in prompt
    if scripts:
        prompt += "\n\n## Available Scripts\n"
        for s in scripts:
            prompt += f"- `agents/{AGENT_NAME}/scripts/{s}`\n"

    # Post-run learning
    prompt += f"\n\n## Post-Run Instructions\nAfter completing your task, write learnings to `{memory_path}`.\n"

    # Research mode guardrails — read from file (single source of truth with tools.py)
    if spec.get("mode") == "research":
        guardrails_path = os.path.join(AGENT_DIR, "references", "research-guardrails.md")
        guardrails = read_file(guardrails_path)
        if guardrails.strip():
            prompt += "\n\n" + guardrails
        else:
            # Fallback if file missing
            prompt += "\n\n## Research Mode Guardrails (ACTIVE)\n"
            prompt += "1. Say 'I don't have enough information' when uncertain.\n"
            prompt += "2. Every claim needs a citation. No quote = retract the claim.\n"
            prompt += "3. Extract direct quotes before analyzing. No paraphrase drift.\n"

    # 4. Call agent via /chat
    display = spec.get("display_name", AGENT_NAME)
    try:
        resp = requests.post(f"{BASE_URL}/chat", json={
            "message": prompt + RESPONSE_FORMAT,
            "call_source": "task",
            "internal_options": {"job_id": JOB_ID},
        }, timeout=(10, 300))

        if not resp.ok:
            print(f"Agent call failed: {resp.status_code}", file=sys.stderr)
            if task:
                task["status"] = "pending"
                with open(tasks_path, "w") as f:
                    json.dump(tasks, f, indent=2)
            return

        reply = resp.json().get("reply", "")
        data = extract_json_response(reply)

        if data and isinstance(data, dict) and data.get("content"):
            summary = data.get("summary", display)
            content = data["content"]
        else:
            summary = display
            content = reply

        # 5. Push result to user
        if content.strip():
            push(content, title=summary)

        # 6. Mark task completed (recurring tasks reset to pending)
        if task:
            now = datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            result_text = (content[:500] + "...") if len(content) > 500 else content
            # Log to history
            if "history" not in task:
                task["history"] = []
            task["history"].append({"completed": now, "result": result_text})
            task["result"] = result_text

            if task.get("recurring"):
                task["status"] = "pending"  # reset for next scheduled run
                task["completed"] = None
            else:
                task["status"] = "completed"
                task["completed"] = now

            with open(tasks_path, "w") as f:
                json.dump(tasks, f, indent=2)

    except Exception as e:
        print(f"Error running agent: {e}", file=sys.stderr)
        if task:
            retry_count = task.get("retry_count", 0) + 1
            max_retries = task.get("max_retries", 3)
            task["retry_count"] = retry_count
            if retry_count >= max_retries:
                task["status"] = "failed"
                task["result"] = f"Dead-lettered after {retry_count} attempts: {e}"
            else:
                task["status"] = "pending"
            with open(tasks_path, "w") as f:
                json.dump(tasks, f, indent=2)
        sys.exit(1)


if __name__ == "__main__":
    main()
