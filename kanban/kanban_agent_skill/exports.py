"""
Kanban Agent Skill — exports.py

Self-configuring: this agent connects to ITS OWN Kanban board with zero edits.
The board URL is resolved at runtime, in this priority order:

  1. explicit `base_url=` argument on any function      (per-call override / collaboration)
  2. KANBAN_URL env var                                  (set-once override)
  3. DISTRIBUTED_BOARD_URL constant (if stamped)         (a shared board this copy was handed off for)
  4. https://community.iamstarchild.com/{USER_ID}-{slug} (auto — your OWN published board)
  5. http://localhost:5555                               (local dev fallback)

Candidates 4 and 5 are health-pinged; the first that answers wins, and the
result is cached for the process. So: run locally before publishing → hits
localhost; publish your board via community-publish → the same code hits your
own community URL automatically. No file edits, no collisions with other users.

DISTRIBUTION: to give a colleague a copy pre-wired to YOUR board, call
kb_export_for_sharing() — it writes a stamped copy of this folder with
DISTRIBUTED_BOARD_URL filled in, so when they drop it into their skills/ it
connects to your board automatically (no env var, no kb_use_board needed). A
recipient can still override with their own KANBAN_URL if they want their own.

Override the auto slug with the KANBAN_SLUG env var (default: "kanban-board").
"""

import os
import json
import urllib.request
import urllib.error

DEFAULT_BOARD = "board-001"
DEFAULT_SLUG = os.environ.get("KANBAN_SLUG", "kanban-board")

# Stamped by kb_export_for_sharing() when this folder is prepared for handoff.
# When non-empty, this copy connects to that specific (distributor's) board by
# default. Leave "" in the canonical source — only distribution copies get it.
DISTRIBUTED_BOARD_URL = ""

# Resolved lazily and cached here.
_RESOLVED_BASE = None


def _candidates() -> list:
    """Ordered list of base URLs to try (highest priority first)."""
    out = []
    env_url = os.environ.get("KANBAN_URL")
    if env_url:
        out.append(env_url.rstrip("/"))
    if DISTRIBUTED_BOARD_URL:
        out.append(DISTRIBUTED_BOARD_URL.rstrip("/"))
    uid = os.environ.get("USER_ID")
    if uid:
        out.append(f"https://community.iamstarchild.com/{uid}-{DEFAULT_SLUG}")
    out.append("http://localhost:5555")
    return out


def _reachable(base: str, timeout: float = 4.0) -> bool:
    """True if `base` answers the board API with valid JSON."""
    try:
        req = urllib.request.Request(
            f"{base}/ajax/tasks/board/get",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            json.loads(resp.read().decode("utf-8"))
        return True
    except Exception:
        return False


def _resolve_base() -> str:
    """Resolve (and cache) the board base URL per the priority order."""
    global _RESOLVED_BASE
    if _RESOLVED_BASE:
        return _RESOLVED_BASE

    cands = _candidates()
    # KANBAN_URL is trusted without a ping (explicit user intent).
    if os.environ.get("KANBAN_URL"):
        _RESOLVED_BASE = cands[0]
        return _RESOLVED_BASE

    for c in cands:
        if _reachable(c):
            _RESOLVED_BASE = c
            return _RESOLVED_BASE

    # Nothing reachable — return best guess (community URL if we have a USER_ID,
    # else localhost) so callers get a coherent error rather than a crash.
    _RESOLVED_BASE = cands[0]
    return _RESOLVED_BASE


def _base_for(base_url: str = None) -> str:
    """Per-call override wins; otherwise use the resolved/cached base."""
    if base_url:
        return base_url.rstrip("/")
    return _resolve_base()


def _post(path: str, payload: dict, base_url: str = None) -> dict:
    url = f"{_base_for(base_url)}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def kb_use_board(url: str) -> dict:
    """
    Point every subsequent call at a specific board URL (overrides auto-detect).

    Use this to work with a board that isn't your own — e.g. a shared/team board,
    or another agent's published board for collaboration. Pass the full public URL
    (e.g. "https://community.iamstarchild.com/{THEIR_USER_ID}-kanban-board"). Call
    kb_reset_board() to return to automatic resolution.
    """
    global _RESOLVED_BASE
    _RESOLVED_BASE = url.rstrip("/")
    return {"ok": True, "using": _RESOLVED_BASE}


def kb_reset_board() -> dict:
    """Clear any override and re-resolve the board URL automatically."""
    global _RESOLVED_BASE
    _RESOLVED_BASE = None
    return {"ok": True, "resolved_url": _resolve_base()}


def kb_health() -> dict:
    """
    Self-check: which board is this agent wired to, and can it be reached?

    Call this FIRST after installing the skill or publishing your board.
    Returns the resolved URL, how it was chosen, reachability, and a board count.
    """
    global _RESOLVED_BASE
    _RESOLVED_BASE = None  # force a fresh resolve

    cands = _candidates()
    uid = os.environ.get("USER_ID")
    checks = []
    if os.environ.get("KANBAN_URL"):
        checks.append({"source": "KANBAN_URL env", "url": cands[0], "trusted": True})
    for c in cands:
        if os.environ.get("KANBAN_URL") and c == cands[0]:
            continue
        checks.append({"source": "auto", "url": c, "reachable": _reachable(c)})

    base = _resolve_base()
    boards = _post("/ajax/tasks/board/get", {}).get("data", [])
    ok = isinstance(boards, list)

    how = "KANBAN_URL env" if os.environ.get("KANBAN_URL") else (
        "community (auto)" if base.startswith("https://community.") else "localhost (dev)"
    )
    return {
        "ok": ok and not (isinstance(boards, dict) and boards.get("error")),
        "resolved_url": base,
        "resolved_via": how,
        "user_id": uid,
        "expected_community_url": f"https://community.iamstarchild.com/{uid}-{DEFAULT_SLUG}" if uid else None,
        "board_count": len(boards) if ok else None,
        "candidates": checks,
        "hint": (
            "Connected. You're good to go."
            if ok else
            "No board reachable. If you haven't published yet: serve kanban/ then "
            "publish_preview() via the community-publish skill. For local dev, run "
            "`node server.js` in kanban/. Set KANBAN_URL to force a specific board."
        ),
    }


# ── Boards ────────────────────────────────────────────────────────────────────

def kb_list_boards() -> list:
    """Return all boards."""
    res = _post("/ajax/tasks/board/get", {})
    return res.get("data", [])


def kb_create_board(title: str, emoji: str = ":clipboard:") -> dict:
    """Create a new board."""
    res = _post("/ajax/tasks/board/save", {
        "object": {
            "workspace_id": "ws-001",
            "title": title,
            "emoji": emoji,
            "view_mode": "grid",
            "active_tasks": 0,
            "connectors": [],
        }
    })
    return res.get("data", {}).get("object", res)


def kb_delete_board(board_id: str) -> dict:
    """Delete a board and all its columns and tasks."""
    res = _post("/ajax/tasks/board/remove", {"object": {"id": board_id}})
    return res.get("data", {})


# ── Columns ───────────────────────────────────────────────────────────────────

def kb_list_columns(board_id: str = DEFAULT_BOARD) -> list:
    """Return all columns on a board."""
    res = _post("/ajax/tasks/list/get", {"options": {"board_id": board_id}})
    return res.get("data", [])


def kb_create_column(title: str, board_id: str = DEFAULT_BOARD, color: str = "#BDBDBD") -> dict:
    """Add a new column to a board."""
    res = _post("/ajax/tasks/list/save", {
        "object": {
            "board_id": board_id,
            "title": title,
            "color": color,
            "auto_participants": [],
        }
    })
    return res.get("data", {}).get("object", res)


def kb_rename_column(list_id: str, title: str) -> dict:
    """Rename a column."""
    res = _post("/ajax/tasks/list/save", {"object": {"id": list_id, "title": title}})
    return res.get("data", {}).get("object", res)


def kb_set_column_color(list_id: str, color: str) -> dict:
    """Set the color of a column. color is a hex string e.g. '#f84600'."""
    res = _post("/ajax/tasks/list/save", {"object": {"id": list_id, "color": color}})
    return res.get("data", {}).get("object", res)


def kb_delete_column(list_id: str) -> dict:
    """Delete a column (and all its tasks)."""
    res = _post("/ajax/tasks/list/remove", {"object": {"id": list_id}})
    return res.get("data", {})


# ── Tasks ─────────────────────────────────────────────────────────────────────

def kb_list_tasks(
    board_id: str = DEFAULT_BOARD,
    list_id: str = None,
    owner: str = None,
    status: str = None,
    priority: str = None,
    archived: bool = False,
    due_before: int = None,
    due_after: int = None,
    search: str = None,
) -> list:
    """List tasks on a board with optional filters.

    Args:
        board_id: Board ID (default: board-001)
        list_id: Column ID (exact match) to filter by
        owner: Name/email substring — matches any participant (case-insensitive)
        status: Column name or ID e.g. "In Progress", "done"
        priority: "low" | "normal" | "medium" | "high" | "urgent"
        archived: False (default, active only) | True (archived only)
        due_before: Unix timestamp — only tasks due on or before this time
        due_after: Unix timestamp — only tasks due on or after this time
        search: Full-text search across title, description, tags, owners
    """
    opts: dict = {"board_id": board_id}
    if list_id:
        opts["list_id"] = list_id
    if owner:
        opts["owner"] = owner
    if status:
        opts["status"] = status
    if priority:
        opts["priority"] = priority
    if archived:
        opts["archived"] = "true"
    if due_before is not None:
        opts["due_before"] = due_before
    if due_after is not None:
        opts["due_after"] = due_after
    if search:
        opts["search"] = search
    res = _post("/ajax/tasks/task/get", {"options": opts})
    return res.get("data", [])


def kb_get_task(task_id: str, board_id: str = DEFAULT_BOARD) -> dict | None:
    """Get a single task by ID."""
    tasks = _post("/ajax/tasks/task/get", {"options": {"board_id": board_id}}).get("data", [])
    for t in tasks:
        if t.get("id") == task_id or t.get("front_id") == task_id:
            return t
    return None


def kb_create_task(
    title: str,
    list_id: str,
    board_id: str = DEFAULT_BOARD,
    description: str = "",
    tags: list = None,
    priority: str = "normal",
    due_date: int = 0,
    start_date: int = 0,
    checklist: list = None,
) -> dict:
    """
    Create a new task.

    Args:
        title: Task title
        list_id: Column ID to place the task in
        board_id: Board ID (default: board-001)
        description: Plain text description
        tags: List of tag strings e.g. ["bug", "frontend"]
        priority: "low" | "normal" | "high" | "urgent"
        due_date: Unix timestamp for due date (0 = none)
        start_date: Unix timestamp for start date (0 = none)
        checklist: List of strings for checklist items
    """
    obj = {
        "board_id": board_id,
        "list_id": list_id,
        "title": title,
        "description": {"original_str": description},
        "tags": tags or [],
        "participants": [],
        "checklist": [{"text": i, "value": False} for i in (checklist or [])],
        "before": due_date,
        "start": start_date,
        "archived": False,
        "_custom_fields": {"priority": priority, "status": "todo"},
    }
    res = _post("/ajax/tasks/task/save", {"object": obj})
    return res.get("data", {}).get("object", res)


def kb_update_task(task_id: str, board_id: str = DEFAULT_BOARD, **fields) -> dict:
    """
    Update any fields on an existing task.

    Common fields: title, description (str), tags (list), priority, due_date, list_id
    Pass description as a plain string — it gets wrapped automatically.
    """
    task = kb_get_task(task_id, board_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}

    # Allow passing description as a plain string
    if "description" in fields and isinstance(fields["description"], str):
        fields["description"] = {"original_str": fields["description"]}

    # Map due_date / start_date sugar
    if "due_date" in fields:
        fields["before"] = fields.pop("due_date")
    if "start_date" in fields:
        fields["start"] = fields.pop("start_date")

    # Merge priority into _custom_fields
    if "priority" in fields:
        cf = task.get("_custom_fields", {})
        cf["priority"] = fields.pop("priority")
        fields["_custom_fields"] = cf

    updated = {**task, **fields}
    res = _post("/ajax/tasks/task/save", {"object": updated})
    return res.get("data", {}).get("object", res)


def kb_move_task(task_id: str, list_id: str, board_id: str = DEFAULT_BOARD) -> dict:
    """Move a task to a different column."""
    return kb_update_task(task_id, board_id, list_id=list_id)


def kb_delete_task(task_id: str) -> dict:
    """Permanently delete a task."""
    res = _post("/ajax/tasks/task/remove", {"object": {"id": task_id}})
    return res.get("data", {})


def kb_archive_task(task_id: str, board_id: str = DEFAULT_BOARD) -> dict:
    """Archive a task (soft delete — hidden but not gone)."""
    return kb_update_task(task_id, board_id, archived=True)


def kb_unarchive_task(task_id: str, board_id: str = DEFAULT_BOARD) -> dict:
    """Restore an archived task back to its column."""
    return kb_update_task(task_id, board_id, archived=False)


def kb_assign_owners(task_id: str, owners: list, board_id: str = DEFAULT_BOARD) -> dict:
    """
    Set the owners (participants) on a task. Replaces existing owners.

    Args:
        owners: List of name/email strings e.g. ['alice', 'bob@example.com']
    """
    participants = [{"user_id_or_mail": o} for o in owners]
    return kb_update_task(task_id, board_id, participants=participants)


def kb_bulk_move(from_list_id: str, to_list_id: str, board_id: str = DEFAULT_BOARD) -> dict:
    """
    Move all tasks from one column to another.
    Returns a summary of how many tasks were moved.
    """
    tasks = kb_list_tasks(board_id=board_id, list_id=from_list_id)
    moved = 0
    errors = []
    for t in tasks:
        result = kb_move_task(t["id"], to_list_id, board_id)
        if "error" in result:
            errors.append({"id": t["id"], "error": result["error"]})
        else:
            moved += 1
    return {"moved": moved, "errors": errors}


# ── Checklist ─────────────────────────────────────────────────────────────────

def kb_add_checklist_item(task_id: str, text: str, board_id: str = DEFAULT_BOARD) -> dict:
    """Add an item to a task's checklist."""
    task = kb_get_task(task_id, board_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}
    checklist = task.get("checklist", [])
    checklist.append({"text": text, "value": False})
    return kb_update_task(task_id, board_id, checklist=checklist)


def kb_toggle_checklist_item(
    task_id: str, index: int, checked: bool, board_id: str = DEFAULT_BOARD
) -> dict:
    """Check or uncheck a checklist item by index (0-based)."""
    task = kb_get_task(task_id, board_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}
    checklist = task.get("checklist", [])
    if index >= len(checklist):
        return {"error": f"Index {index} out of range (task has {len(checklist)} items)"}
    checklist[index]["value"] = checked
    return kb_update_task(task_id, board_id, checklist=checklist)


# ── Helpers ───────────────────────────────────────────────────────────────────

def kb_summary(board_id: str = DEFAULT_BOARD) -> dict:
    """
    Quick overview: board info, column names + task counts.
    Good for an agent to orient itself before taking action.
    """
    boards = kb_list_boards()
    board = next((b for b in boards if b["id"] == board_id), None)
    columns = kb_list_columns(board_id)
    tasks = kb_list_tasks(board_id)

    col_summary = []
    for col in columns:
        col_tasks = [t for t in tasks if t.get("list_id") == col["id"]]
        col_summary.append({
            "id": col["id"],
            "title": col["title"],
            "color": col.get("color"),
            "task_count": len(col_tasks),
            "tasks": [{"id": t["id"], "title": t["title"], "priority": t.get("_custom_fields", {}).get("priority", "normal")} for t in col_tasks],
        })

    return {
        "board": board,
        "columns": col_summary,
        "total_tasks": len(tasks),
    }


def kb_my_board_url() -> str | None:
    """
    The public, shareable URL of THIS agent's own community board — i.e. the URL
    you hand to a collaborator. Built from USER_ID; returns None if unavailable
    (e.g. running purely local with no USER_ID set).
    """
    uid = os.environ.get("USER_ID")
    if not uid:
        return None
    return f"https://community.iamstarchild.com/{uid}-{DEFAULT_SLUG}"


def kb_export_for_sharing(dest: str = None, board_url: str = None) -> dict:
    """
    Prepare a ready-to-send copy of THIS connector folder, pre-wired to a board
    so the recipient's agent connects automatically — no env var, no kb_use_board.

    What it does:
      1. Resolves the board URL to stamp (arg `board_url` > your own community
         board via USER_ID). Fails clearly if neither is available.
      2. Copies this skill folder (SKILL.md + exports.py) to `dest`.
      3. Stamps DISTRIBUTED_BOARD_URL in the copied exports.py with that URL.
      4. Zips the folder for easy handoff.

    Args:
      dest:      output folder (default: output/kanban-agent-share/kanban_agent_skill)
      board_url: board to wire the copy to (default: your own community board URL)

    Returns dict with the stamped URL, folder path, zip path, and next steps.
    The recipient: drop the folder into their skills/, then their agent runs
    skill_refresh — done. (This function does NOT touch YOUR installed skills.)
    """
    import shutil

    url = (board_url or kb_my_board_url())
    if not url:
        return {
            "error": "No board URL to stamp. Publish your board first (so USER_ID "
                     "maps to a community URL), or pass board_url= explicitly.",
        }
    url = url.rstrip("/")

    here = os.path.dirname(os.path.abspath(__file__))
    if dest is None:
        # Resolve workspace root (…/skills/kanban/kanban_agent_skill → up 3)
        ws = os.path.abspath(os.path.join(here, "..", "..", ".."))
        dest = os.path.join(ws, "output", "kanban-agent-share", "kanban_agent_skill")

    dest = os.path.abspath(dest)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest, exist_ok=True)

    # Copy the two source files only (no __pycache__, no board server files).
    for fname in ("SKILL.md", "exports.py"):
        src = os.path.join(here, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, fname))

    # Stamp the copied exports.py with the board URL.
    stamped_path = os.path.join(dest, "exports.py")
    with open(stamped_path, "r", encoding="utf-8") as f:
        code = f.read()
    needle = 'DISTRIBUTED_BOARD_URL = ""'
    if needle not in code:
        return {"error": f"Could not find stamp anchor in copied exports.py ({needle!r})."}
    code = code.replace(needle, f'DISTRIBUTED_BOARD_URL = "{url}"', 1)
    with open(stamped_path, "w", encoding="utf-8") as f:
        f.write(code)

    # Zip for handoff.
    zip_base = dest  # e.g. …/kanban_agent_skill
    zip_path = shutil.make_archive(zip_base, "zip", root_dir=os.path.dirname(dest),
                                   base_dir=os.path.basename(dest))

    return {
        "ok": True,
        "stamped_board_url": url,
        "folder": dest,
        "zip": zip_path,
        "next_steps": [
            f"Send the folder (or zip) to your colleague.",
            "They drop 'kanban_agent_skill/' into their skills/ directory.",
            "Their agent runs skill_refresh — it registers as 'kanban-agent'.",
            f"It auto-connects to {url} (verify with kb_health()).",
            "They can override with their own KANBAN_URL to use their own board instead.",
        ],
    }
