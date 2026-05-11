#!/usr/bin/env python3
# -*- task-system: v3 -*-
"""
Always-on daemon for: __DISPLAY_NAME__
Agent: __AGENT_NAME__
Polls inbox for messages, runs pending tasks, writes to outbox.
"""
import requests, os, json, sys, re
from datetime import datetime, timezone as tz

JOB_ID = os.environ.get("JOB_ID")
AGENT_NAME = "__AGENT_NAME__"
AGENT_TEAM = "__TEAM_NAME__"  # empty string if no team
WORKSPACE = os.environ.get("WORKSPACE_DIR", os.environ.get("PWD", "."))
BASE_URL = "http://localhost:8000"

# Resolve agent directory — use exact path baked at build time
if AGENT_TEAM:
    AGENT_DIR = os.path.join(WORKSPACE, "agents", AGENT_TEAM, AGENT_NAME)
else:
    AGENT_DIR = os.path.join(WORKSPACE, "agents", AGENT_NAME)

# Verify agent.yaml exists, otherwise search for the real location
if not os.path.exists(os.path.join(AGENT_DIR, "agent.yaml")):
    found = False
    agents_root = os.path.join(WORKSPACE, "agents")
    if os.path.isdir(agents_root):
        # Check flat first
        flat = os.path.join(agents_root, AGENT_NAME, "agent.yaml")
        if os.path.exists(flat):
            AGENT_DIR = os.path.join(agents_root, AGENT_NAME)
            found = True
        else:
            # Search team directories
            for d in os.listdir(agents_root):
                candidate = os.path.join(agents_root, d, AGENT_NAME, "agent.yaml")
                if os.path.exists(candidate):
                    AGENT_DIR = os.path.join(agents_root, d, AGENT_NAME)
                    found = True
                    break
    if not found:
        print(f"Agent directory not found for {AGENT_NAME}", file=sys.stderr)
        sys.exit(0)

INBOX = os.path.join(AGENT_DIR, "inbox.json")
OUTBOX = os.path.join(AGENT_DIR, "outbox.json")
OUTPUT_FILE = os.path.join(AGENT_DIR, "output", f"{AGENT_NAME}.json")
CHAT_ROOM = os.path.join(WORKSPACE, "agents", AGENT_TEAM, "chat.json") if AGENT_TEAM else None

RESPONSE_FORMAT = '\n\nIMPORTANT: Respond with ONLY JSON: {"summary": "...", "content": "..."}'

def get_chat_timeout():
    """Read agent-specific timeout from agent.yaml. Falls back to 300s."""
    spec = read_yaml_simple(os.path.join(AGENT_DIR, "agent.yaml"))
    t = spec.get("timeout", 300)
    try:
        return (10, int(t))
    except (ValueError, TypeError):
        return (10, 300)
DELEGATE_FORMAT = '\n\nIf you need to delegate subtasks to your workers, respond with ONLY JSON:\n{"action": "delegate", "tasks": [{"to": "worker-name", "content": "what to do"}, ...]}\nIf you are synthesizing final results, respond with:\n{"action": "synthesize", "summary": "...", "content": "..."}'


# ---------------------------------------------------------------------------
# Team Chat Room — shared message bus for inter-agent coordination
# ---------------------------------------------------------------------------

def read_chat():
    """Read team chat room. Returns list of messages."""
    if not CHAT_ROOM or not os.path.exists(CHAT_ROOM):
        return []
    try:
        with open(CHAT_ROOM, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []


def post_chat(to, content, msg_type="task"):
    """Post a message to the team chat room."""
    if not CHAT_ROOM:
        return
    msgs = read_chat()
    msgs.append({
        "id": f"chat-{AGENT_NAME}-{datetime.now(tz.utc).strftime('%H%M%S')}",
        "from": AGENT_NAME,
        "to": to,
        "content": content,
        "type": msg_type,  # "task", "result", "info"
        "status": "pending",
        "timestamp": datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    write_json(CHAT_ROOM, msgs)


def claim_chat_message(msg_id):
    """Atomically claim a pending message. Returns True only if THIS agent got the claim.

    Uses read-claim-verify pattern: write our claim, then re-read to verify nobody
    else claimed it between our read and write. 5-min polling makes collision unlikely
    but this handles it gracefully if it happens.
    """
    if not CHAT_ROOM:
        return False
    msgs = read_chat()
    for m in msgs:
        if m["id"] == msg_id and m.get("status") == "pending":
            m["status"] = "picked_up"
            m["claimed_by"] = AGENT_NAME
            m["claimed_at"] = datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            write_json(CHAT_ROOM, msgs)
            # Verify our claim stuck (another agent might have written between our read and write)
            verify = read_chat()
            for v in verify:
                if v["id"] == msg_id:
                    if v.get("claimed_by") == AGENT_NAME:
                        return True
                    else:
                        print(f"[chat] Claim conflict on {msg_id} — {v.get('claimed_by')} got it", file=sys.stderr)
                        return False
    return False


TASK_TIMEOUT_MINUTES = 15  # leader stops waiting for a worker after this


def complete_chat_message(msg_id, result_content):
    """Post result back to chat room AND nudge the leader's inbox for faster pickup."""
    if not CHAT_ROOM:
        return
    msgs = read_chat()
    original = None
    for m in msgs:
        if m["id"] == msg_id:
            m["status"] = "done"
            m["completed_at"] = datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            original = m
            break
    # Post result as a new message back to the sender
    if original:
        result_id = f"result-{AGENT_NAME}-{datetime.now(tz.utc).strftime('%H%M%S')}"
        msgs.append({
            "id": result_id,
            "from": AGENT_NAME,
            "to": original["from"],
            "content": result_content,
            "type": "result",
            "in_reply_to": msg_id,
            "status": "pending",
            "timestamp": datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        write_json(CHAT_ROOM, msgs)

        # Push-notify the leader — write a nudge to their inbox so they process
        # results on their NEXT poll instead of waiting for process_team_chat
        leader_name = original["from"]
        if leader_name != AGENT_NAME:
            leader_dir = None
            if AGENT_TEAM:
                candidate = os.path.join(WORKSPACE, "agents", AGENT_TEAM, leader_name)
                if os.path.isdir(candidate):
                    leader_dir = candidate
            if not leader_dir:
                candidate = os.path.join(WORKSPACE, "agents", leader_name)
                if os.path.isdir(candidate):
                    leader_dir = candidate
            if leader_dir:
                leader_inbox = os.path.join(leader_dir, "inbox.json")
                inbox = read_json(leader_inbox)
                inbox.append({
                    "id": f"nudge-{AGENT_NAME}-{datetime.now(tz.utc).strftime('%H%M%S')}",
                    "from": AGENT_NAME,
                    "message": f"[CHAT_RESULT] Task complete. Check chat room for results.",
                    "type": "chat_nudge",
                    "timestamp": datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "processed": False,
                })
                write_json(leader_inbox, inbox)
                print(f"[chat] Nudged leader {leader_name} via inbox", file=sys.stderr)


def get_my_pending_chat():
    """Get pending chat messages addressed to this agent."""
    msgs = read_chat()
    return [m for m in msgs if m.get("to") == AGENT_NAME and m.get("status") == "pending" and m.get("type") == "task"]


def get_my_results():
    """Get result messages addressed to this agent (responses from workers)."""
    msgs = read_chat()
    return [m for m in msgs if m.get("to") == AGENT_NAME and m.get("status") == "pending" and m.get("type") == "result"]


def get_teammates():
    """Find teammates in the same team. Returns list of (name, display_name, dir_path)."""
    if not AGENT_TEAM:
        return []
    teammates = []
    team_dir = os.path.join(WORKSPACE, "agents", AGENT_TEAM)
    if not os.path.isdir(team_dir):
        return []
    for entry in sorted(os.listdir(team_dir)):
        if entry == AGENT_NAME or entry.startswith("."):
            continue
        mate_yaml = os.path.join(team_dir, entry, "agent.yaml")
        if os.path.exists(mate_yaml):
            mate_spec = read_yaml_simple(mate_yaml)
            if mate_spec.get("status") == "active":
                teammates.append((entry, mate_spec.get("display_name", entry), os.path.join(team_dir, entry)))
    return teammates


def build_team_context():
    """Build team context string for prompts."""
    teammates = get_teammates()
    if not teammates:
        return ""
    lines = [f"\n\n## Team: {AGENT_TEAM}", "You are part of a team. Teammates' output is available:"]
    for name, display, path in teammates:
        rel = f"agents/{AGENT_TEAM}/{name}"
        lines.append(f"- **{display}** (`{name}`) → `{rel}/output/`")
    lines.append("Use `read_file` to access their deliverables.")
    lines.append(f"To message a teammate: use `agent_message(agent=\"<name>\", message=\"...\", from_agent=\"{AGENT_NAME}\")`")
    return "\n".join(lines)


def notify_teammates(summary):
    """Notify all teammates that this agent has new output."""
    teammates = get_teammates()
    for name, display, path in teammates:
        mate_inbox = os.path.join(path, "inbox.json")
        inbox = read_json(mate_inbox)
        inbox.append({
            "id": f"auto-{AGENT_NAME}-{datetime.now(tz.utc).strftime('%H%M%S')}",
            "from": AGENT_NAME,
            "message": f"[AUTO] I've updated my output. Summary: {summary}",
            "timestamp": datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "processed": False,
        })
        write_json(mate_inbox, inbox)


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


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def read_yaml_simple(path):
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


def process_inbox(spec):
    """Check inbox for messages, process them, write responses to outbox."""
    inbox = read_json(INBOX)
    if not inbox:
        return False  # nothing to do

    # Take unprocessed messages
    unprocessed = [m for m in inbox if not m.get("processed")]
    if not unprocessed:
        return False

    display = spec.get("display_name", AGENT_NAME)
    prompt_base = read_file(os.path.join(AGENT_DIR, "PROMPT.md"))
    memory = read_file(os.path.join(AGENT_DIR, "memory", "MEMORY.md")) or "(No memory yet)"

    for msg in unprocessed:
        # Chat nudges — just mark processed, let process_team_chat handle the actual results
        if msg.get("type") == "chat_nudge":
            msg["processed"] = True
            msg["processed_at"] = datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"[inbox] Chat nudge from {msg.get('from')} — will check chat room next", file=sys.stderr)
            continue

        # Build prompt — leaders with teams get delegation format
        teammates = get_teammates()
        if CHAT_ROOM and teammates:
            # Leader mode — can delegate to workers via chat room
            worker_list = "\n".join(f"- `{n}`: {d}" for n, d, _ in teammates)
            prompt = f"""# {display} — Message Processing (Team Leader)

{prompt_base}

## Your Memory
{memory}

## Your Workers
{worker_list}

## Incoming Message
From: {msg.get('from', 'user')}
Message: {msg.get('message', '')}

## How to Respond
If this task needs multiple workers, delegate by responding with:
{{"action": "delegate", "tasks": [{{"to": "worker-name", "content": "what to do"}}, ...]}}

If you can handle it yourself or are synthesizing results, respond with:
{{"summary": "...", "content": "..."}}
"""
        else:
            # Regular agent — just respond
            prompt = f"""# {display} — Message Processing

{prompt_base}

## Your Memory
{memory}

## Incoming Message
From: {msg.get('from', 'user')}
Message: {msg.get('message', '')}

Respond to this message based on your role and goal.
"""
        prompt += RESPONSE_FORMAT

        try:
            resp = requests.post(f"{BASE_URL}/chat", json={
                "message": prompt,
                "call_source": "task",
                "internal_options": {"job_id": JOB_ID},
            }, timeout=get_chat_timeout())

            reply = ""
            content = ""
            summary = display
            if resp.ok:
                reply = resp.json().get("reply", "")
                data = extract_json_response(reply)

                # Check if leader is delegating
                if data and isinstance(data, dict) and data.get("action") == "delegate" and CHAT_ROOM:
                    tasks_to_delegate = data.get("tasks", [])
                    for t in tasks_to_delegate:
                        post_chat(to=t["to"], content=t["content"], msg_type="task")
                        print(f"[inbox] Delegated to {t['to']}: {t['content'][:60]}", file=sys.stderr)
                    content = f"Delegated {len(tasks_to_delegate)} tasks to workers. Waiting for results."
                    summary = f"{display}: delegated"
                elif data and isinstance(data, dict) and data.get("content"):
                    summary = data.get("summary", display)
                    content = data["content"]
                else:
                    content = reply
            else:
                content = f"Error: {resp.status_code}"

            # Write to outbox
            outbox = read_json(OUTBOX)
            outbox.append({
                "from": AGENT_NAME,
                "to": msg.get("from", "user"),
                "in_reply_to": msg.get("id"),
                "message": content,
                "summary": summary,
                "timestamp": datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            write_json(OUTBOX, outbox)

            # Push to user if message was from user (but not delegation confirmations)
            if msg.get("from", "user") == "user" and content.strip() and "Delegated" not in content:
                push(content, title=summary)

        except Exception as e:
            print(f"Error processing message: {e}", file=sys.stderr)

        # Mark as processed
        msg["processed"] = True
        msg["processed_at"] = datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Trim processed messages older than 50 entries to prevent unbounded growth
    processed = [m for m in inbox if m.get("processed")]
    if len(processed) > 50:
        # Keep only the 20 most recent processed messages + all unprocessed
        recent_processed = sorted(processed, key=lambda m: m.get("processed_at", ""), reverse=True)[:20]
        unprocessed = [m for m in inbox if not m.get("processed")]
        inbox = unprocessed + recent_processed

    write_json(INBOX, inbox)
    return True


def process_team_chat(spec):
    """Check team chat room for tasks addressed to this agent. Workers pick up tasks, leaders check for results."""
    if not CHAT_ROOM:
        return False

    display = spec.get("display_name", AGENT_NAME)
    role = spec.get("role", "")

    # --- WORKER PATH: Pick up pending tasks from the chat room ---
    pending_tasks = get_my_pending_chat()
    if pending_tasks:
        task_msg = pending_tasks[0]  # process one per poll cycle
        if not claim_chat_message(task_msg["id"]):
            return False  # someone else claimed it

        print(f"[chat] Processing task from {task_msg['from']}: {task_msg['content'][:80]}", file=sys.stderr)

        # Build worker prompt
        prompt_base = read_file(os.path.join(AGENT_DIR, "PROMPT.md"))
        memory = read_file(os.path.join(AGENT_DIR, "memory", "MEMORY.md")) or "(No memory yet)"

        task_section = f"**Task from team chat:** {task_msg['content']}\n**Assigned by:** {task_msg['from']}"
        prompt = prompt_base
        prompt = prompt.replace("{task_section}", task_section)
        prompt = prompt.replace("{memory_content}", memory)
        prompt = prompt.replace("{memory_path}", os.path.join(AGENT_DIR, "memory", "MEMORY.md"))
        prompt = prompt.replace("{output_path}", os.path.join(AGENT_DIR, "output"))
        prompt = prompt.replace("{output_file}", f"{AGENT_NAME}.json")
        prompt = prompt.replace("{references_section}", "(load from references/ if needed)")
        prompt += build_team_context()
        prompt += RESPONSE_FORMAT

        try:
            resp = requests.post(f"{BASE_URL}/chat", json={
                "message": prompt,
                "call_source": "task",
                "internal_options": {"job_id": JOB_ID},
            }, timeout=get_chat_timeout())

            if resp.ok:
                reply = resp.json().get("reply", "")
                data = extract_json_response(reply)
                if data and isinstance(data, dict) and data.get("content"):
                    content = data["content"]
                else:
                    content = reply
                complete_chat_message(task_msg["id"], content)
                print(f"[chat] Completed task, posted result back to {task_msg['from']}", file=sys.stderr)
            else:
                complete_chat_message(task_msg["id"], f"Error: /chat returned {resp.status_code}")
        except Exception as e:
            print(f"[chat] Error processing task: {e}", file=sys.stderr)
            complete_chat_message(task_msg["id"], f"Error: {e}")

        return True

    # --- LEADER PATH: Check for results from workers ---
    results = get_my_results()
    if results:
        # Collect all pending results
        result_texts = []
        for r in results:
            result_texts.append(f"**{r['from']}:** {r['content']}")
            claim_chat_message(r["id"])

        # Check if there are still outstanding tasks we sent that haven't been completed
        all_msgs = read_chat()
        my_outgoing = [m for m in all_msgs if m.get("from") == AGENT_NAME and m.get("type") == "task"]
        still_pending = [m for m in my_outgoing if m.get("status") in ("pending", "picked_up")]

        # Check for timed-out tasks — don't wait forever for silent failures
        timed_out = []
        truly_pending = []
        for sp in still_pending:
            ts = sp.get("timestamp", "")
            try:
                task_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                now = datetime.now(tz.utc)
                elapsed = (now - task_time).total_seconds() / 60
                if elapsed > TASK_TIMEOUT_MINUTES:
                    sp["status"] = "timed_out"
                    timed_out.append(sp)
                else:
                    truly_pending.append(sp)
            except (ValueError, TypeError):
                truly_pending.append(sp)

        if timed_out:
            write_json(CHAT_ROOM, all_msgs)
            for t in timed_out:
                result_texts.append(f"**{t['to']}:** (TIMED OUT — no response after {TASK_TIMEOUT_MINUTES} min)")
                print(f"[chat] Task to {t['to']} timed out after {TASK_TIMEOUT_MINUTES} min", file=sys.stderr)

        if truly_pending:
            print(f"[chat] Have {len(results)} results but {len(truly_pending)} tasks still pending, waiting...", file=sys.stderr)
            return False  # wait for remaining workers

        # All workers done — synthesize
        print(f"[chat] All workers done ({len(result_texts)} results). Synthesizing...", file=sys.stderr)

        memory = read_file(os.path.join(AGENT_DIR, "memory", "MEMORY.md")) or "(No memory yet)"
        synthesis_prompt = f"""# {display} — Synthesis

You are **{display}**, the team leader. Your workers have completed their tasks.

**Role:** {role}

## Worker Results
{chr(10).join(result_texts)}

## Instructions
Synthesize all worker results into a single coherent deliverable.
Save the synthesis to your output directory.
Write learnings to your memory file.

"""
        synthesis_prompt += RESPONSE_FORMAT

        try:
            resp = requests.post(f"{BASE_URL}/chat", json={
                "message": synthesis_prompt,
                "call_source": "task",
                "internal_options": {"job_id": JOB_ID},
            }, timeout=get_chat_timeout())

            if resp.ok:
                reply = resp.json().get("reply", "")
                data = extract_json_response(reply)
                if data and isinstance(data, dict) and data.get("content"):
                    content = data["content"]
                    summary = data.get("summary", f"{display} Brief")
                else:
                    content = reply
                    summary = f"{display} Brief"

                if content.strip():
                    push(content, title=summary)
                    print(f"[chat] Synthesis complete, pushed to user", file=sys.stderr)
        except Exception as e:
            print(f"[chat] Synthesis error: {e}", file=sys.stderr)

        return True

    return False


def process_tasks(spec):
    """Pick and run the next pending task, same as scheduled_run.py."""
    tasks_path = os.path.join(AGENT_DIR, "tasks.json")
    try:
        with open(tasks_path) as f:
            tasks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    pending = [t for t in tasks if t.get("status") == "pending"]

    # Check depends_on
    completed_ids = set()
    for t in tasks:
        if t.get("status") == "completed":
            completed_ids.add(t["id"])
        elif t.get("recurring") and t.get("history"):
            completed_ids.add(t["id"])

    eligible = []
    for t in pending:
        deps = t.get("depends_on") or []
        if isinstance(deps, str):
            deps = [deps]
        if all(d in completed_ids for d in deps):
            eligible.append(t)

    if not eligible:
        return False

    eligible.sort(key=lambda t: (
        priority_order.get(t.get("priority", "medium"), 2),
        t.get("due_date") or "9999-12-31",
    ))
    task = eligible[0]

    # Build prompt
    display = spec.get("display_name", AGENT_NAME)
    prompt_base = read_file(os.path.join(AGENT_DIR, "PROMPT.md"))
    memory = read_file(os.path.join(AGENT_DIR, "memory", "MEMORY.md")) or "(No memory yet)"
    memory_path = os.path.join(AGENT_DIR, "memory", "MEMORY.md")

    task_section = (
        f"**Task:** {task['title']}\n"
        f"**Description:** {task.get('description', 'N/A')}\n"
        f"**Priority:** {task.get('priority', 'medium')}\n"
        f"**Due:** {task.get('due_date') or 'No deadline'}"
    )

    # Mark in progress
    task["status"] = "in_progress"
    with open(tasks_path, "w") as f:
        json.dump(tasks, f, indent=2)

    prompt = prompt_base
    prompt = prompt.replace("{task_section}", task_section)
    prompt = prompt.replace("{memory_content}", memory)
    prompt = prompt.replace("{memory_path}", memory_path)
    prompt = prompt.replace("{output_path}", os.path.join(AGENT_DIR, "output"))
    prompt = prompt.replace("{output_file}", f"{AGENT_NAME}.json")
    prompt = prompt.replace("{references_section}", "(load from references/ if needed)")

    # Team context — so agent can see and message teammates
    prompt += build_team_context()

    # Research mode
    if spec.get("mode") == "research":
        guardrails_path = os.path.join(AGENT_DIR, "references", "research-guardrails.md")
        guardrails = read_file(guardrails_path)
        if guardrails.strip():
            prompt += "\n\n" + guardrails

    prompt += f"\n\nAfter completing, write learnings to `{memory_path}`.\n"
    prompt += RESPONSE_FORMAT

    try:
        resp = requests.post(f"{BASE_URL}/chat", json={
            "message": prompt,
            "call_source": "task",
            "internal_options": {"job_id": JOB_ID},
        }, timeout=get_chat_timeout())

        content = ""
        summary = display
        if resp.ok:
            reply = resp.json().get("reply", "")
            data = extract_json_response(reply)
            if data and isinstance(data, dict) and data.get("content"):
                content = data["content"]
                summary = data.get("summary", display)
            else:
                content = reply

            if content.strip():
                push(content, title=summary)

        # Complete task
        now = datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result_text = (content[:500] + "...") if len(content) > 500 else content
        if "history" not in task:
            task["history"] = []
        task["history"].append({"completed": now, "result": result_text})
        task["result"] = result_text

        if task.get("recurring"):
            task["status"] = "pending"
            task["completed"] = None
        else:
            task["status"] = "completed"
            task["completed"] = now

        with open(tasks_path, "w") as f:
            json.dump(tasks, f, indent=2)

        # Auto-notify teammates that we have new output
        if AGENT_TEAM and content.strip():
            try:
                notify_teammates(summary)
                print(f"[daemon] Notified teammates of completion: {summary}", file=sys.stderr)
            except Exception as ne:
                print(f"[daemon] Failed to notify teammates: {ne}", file=sys.stderr)

    except Exception as e:
        print(f"Error running task: {e}", file=sys.stderr)
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

    return True


AUTONOMOUS_COOLDOWN_MINUTES = 30  # don't do autonomous work more than once per 30 min


def do_autonomous_work(spec):
    """Proactively pursue the agent's goal when there are no messages or tasks."""
    state_file = os.path.join(AGENT_DIR, ".daemon_state.json")
    now_str = datetime.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Update timestamp FIRST — even if we crash, don't retry for another 30 min
    state = {}
    try:
        with open(state_file) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Check cooldown
    last_run_str = state.get("last_autonomous", "")
    if last_run_str:
        try:
            # Parse ISO timestamp — handle both +00:00 and Z suffixes
            last_ts = last_run_str.replace("Z", "+00:00")
            now_ts = now_str.replace("Z", "+00:00")
            from datetime import datetime as dt_cls
            last_dt = dt_cls.fromisoformat(last_ts)
            now_dt = dt_cls.fromisoformat(now_ts)
            elapsed = (now_dt - last_dt).total_seconds() / 60
            if elapsed < AUTONOMOUS_COOLDOWN_MINUTES:
                return False  # too soon
        except Exception as e:
            print(f"[autonomous] Cooldown parse error: {e}, running anyway", file=sys.stderr)

    # Write timestamp NOW — prevents re-entry on crash
    state["last_autonomous"] = now_str
    state["last_status"] = "started"
    write_json(state_file, state)

    goal = spec.get("goal", "")
    if not goal:
        print(f"[autonomous] No goal set for {AGENT_NAME}, skipping", file=sys.stderr)
        state["last_status"] = "no_goal"
        write_json(state_file, state)
        return False

    print(f"[autonomous] Starting autonomous work for {AGENT_NAME}", file=sys.stderr)

    try:
        display = spec.get("display_name", AGENT_NAME)
        role = spec.get("role", "")
        memory = read_file(os.path.join(AGENT_DIR, "memory", "MEMORY.md")) or "(No memory yet)"

        # Check existing output
        output_dir = os.path.join(AGENT_DIR, "output")
        existing_files = []
        if os.path.isdir(output_dir):
            existing_files = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]

        output_summary = ""
        if existing_files:
            output_summary = f"\n\nYou have existing output files: {', '.join(existing_files)}"
            output_summary += "\nRead them with read_file to see what you've already collected."
        else:
            output_summary = "\n\nNo output files yet — this may be your first autonomous run."

        # Build team context
        team_context = build_team_context()

        # Build output contract
        output_rel = f"agents/{AGENT_TEAM}/{AGENT_NAME}" if AGENT_TEAM else f"agents/{AGENT_NAME}"
        output_contract = f"""
## Output Contract
- **Primary output:** `{output_rel}/output/{AGENT_NAME}.json` (JSON array)
- Read existing file before writing. Append new items. NEVER overwrite from scratch.
- Deduplicate: check primary identifier before adding.
"""

        prompt = f"""# {display} — Autonomous Work

You are **{display}**. You are always on, proactively pursuing your goal.

**Role:** {role}
**Goal:** {goal}

## Your Memory
{memory}
{output_summary}
{output_contract}
{team_context}

## Instructions
You have no pending tasks or messages. Use this time to proactively advance your goal:

1. Read your memory to see what you've done before
2. Read your existing output files to see current state
3. Decide what would be most valuable to do next
4. Do it — search, fetch, analyze, whatever advances your goal
5. Update your output files with any new findings (JSON first)
6. Update your memory with what you learned

If you have nothing productive to do (goal is fully satisfied), just output: AUTONOMOUS_IDLE

Be efficient — you get one autonomous work session every {AUTONOMOUS_COOLDOWN_MINUTES} minutes.
"""

        # Research mode guardrails
        if spec.get("mode") == "research":
            guardrails_path = os.path.join(AGENT_DIR, "references", "research-guardrails.md")
            guardrails = read_file(guardrails_path)
            if guardrails.strip():
                prompt += "\n\n" + guardrails

        prompt += RESPONSE_FORMAT

        print(f"[autonomous] Calling /chat for {AGENT_NAME} (prompt: {len(prompt)} chars)", file=sys.stderr)

        resp = requests.post(f"{BASE_URL}/chat", json={
            "message": prompt,
            "call_source": "task",
            "internal_options": {"job_id": JOB_ID},
        }, timeout=get_chat_timeout())

        print(f"[autonomous] /chat response: status={resp.status_code}", file=sys.stderr)

        if not resp.ok:
            print(f"[autonomous] /chat failed: {resp.status_code} {resp.text[:200]}", file=sys.stderr)
            state["last_status"] = f"chat_error_{resp.status_code}"
            write_json(state_file, state)
            return False

        reply = resp.json().get("reply", "")
        print(f"[autonomous] Reply length: {len(reply)} chars", file=sys.stderr)

        if not reply.strip():
            print(f"[autonomous] Empty reply from /chat", file=sys.stderr)
            state["last_status"] = "empty_reply"
            write_json(state_file, state)
            return False

        if "AUTONOMOUS_IDLE" in reply:
            print(f"[autonomous] Agent says idle", file=sys.stderr)
            state["last_status"] = "idle"
            write_json(state_file, state)
            return True

        # Parse and push response
        data = extract_json_response(reply)
        if data and isinstance(data, dict) and data.get("content"):
            content = data["content"]
            summary = data.get("summary", f"{display} update")
        else:
            content = reply
            summary = f"{display} update"

        if content.strip():
            push(content, title=summary)
            print(f"[autonomous] Pushed result: {summary}", file=sys.stderr)

        # Auto-notify teammates
        if AGENT_TEAM and content.strip() and "AUTONOMOUS_IDLE" not in reply:
            try:
                notify_teammates(summary)
                print(f"[autonomous] Notified teammates", file=sys.stderr)
            except Exception as ne:
                print(f"[autonomous] Notify failed: {ne}", file=sys.stderr)

        state["last_status"] = "success"
        write_json(state_file, state)
        return True

    except Exception as e:
        print(f"[autonomous] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        state["last_status"] = f"error: {str(e)[:100]}"
        write_json(state_file, state)
        return False


def main():
    spec = read_yaml_simple(os.path.join(AGENT_DIR, "agent.yaml"))
    if spec.get("status") != "active":
        return  # silent exit — agent paused/archived

    # Priority order:
    # 1. Direct inbox messages (user → agent)
    # 2. Team chat room (inter-agent coordination)
    # 3. Pending tasks (explicit task queue)
    # 4. Autonomous work (proactive goal pursuit)

    did_inbox = process_inbox(spec)
    if did_inbox:
        return

    did_chat = process_team_chat(spec)
    if did_chat:
        return

    did_task = process_tasks(spec)
    if did_task:
        return

    do_autonomous_work(spec)


if __name__ == "__main__":
    main()
