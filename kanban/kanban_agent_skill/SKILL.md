---
name: kanban-agent
version: 1.0.0
description: |
  Full read/write access to YOUR OWN published Kanban board. The board URL is
  resolved automatically at runtime (community URL when published, localhost for
  dev) — no hardcoding, no edits.

  Use when an agent needs to manage tasks on its board — list tasks,
  create/update/move/delete tasks, manage columns, or check checklists.
delivery: script
metadata:
  starchild:
    emoji: 📋
    skillKey: kanban-agent
---

## Overview

This skill connects to **your own** Kanban board. The board URL is resolved
automatically at runtime — you never hardcode or edit it:

1. `KANBAN_URL` env var (if set) — trusted, no ping.
2. `https://community.iamstarchild.com/{USER_ID}-kanban-board` — your published board, if reachable.
3. `http://localhost:5555` — local dev fallback (`node server.js` in `skills/kanban/`).

The first candidate that answers a health ping wins, and the result is cached.
So the *same code* hits localhost before you publish and your community board
after — zero edits. No auth, no collisions with other users' boards.

The default board ID is `board-001`. All functions default to it — you don't need to pass it unless working with multiple boards.

---

## Quick Start

```python
from exports import kb_health, kb_summary, kb_list_tasks, kb_create_task, kb_move_task

kb_health()   # ← call FIRST: shows which board you're wired to + reachability
kb_summary()  # then orient: columns + task counts
```

### Connecting / targeting a board

```python
kb_health()                       # what am I connected to?
kb_use_board("https://community.iamstarchild.com/{THEIR_USER_ID}-kanban-board")  # target another board (collab)
kb_reset_board()                  # back to automatic resolution
```
Auto-detect needs no setup. Use `kb_use_board()` only to reach a board that
isn't your own (a shared/team board, or another agent's for collaboration).

### Sharing your board with a colleague (pre-wired handoff)

Don't hand over a raw copy — a raw copy auto-detects the *recipient's* own board,
not yours. Instead stamp a copy with your board URL first:

```python
kb_export_for_sharing()   # writes a copy pre-wired to YOUR board + a zip
```

It resolves your own community board URL, copies this folder to
`output/kanban-agent-share/kanban_agent_skill/`, stamps `DISTRIBUTED_BOARD_URL`
into it, and zips it. Send that folder/zip. The recipient:

1. Drops `kanban_agent_skill/` into their `skills/` directory.
2. Their agent runs **skill_refresh** (registers it as `kanban-agent`).
3. `kb_health()` — it auto-connects to *your* board, no config.

(To wire the copy to a different board, pass `kb_export_for_sharing(board_url=...)`.
The recipient can still set their own `KANBAN_URL` to use their own board.)

---

## Functions

### Board Overview

```python
kb_summary(board_id="board-001")
```
Returns board info + all columns with task counts and task titles. **Always call this first** to orient yourself — get column IDs before creating or moving tasks.

```python
kb_list_boards()
```
Returns all boards. Each has an `id` field — pass it as `board_id` to scope all other calls.

```python
kb_create_board(title="Sprint 3", emoji=":fire:")
```
Creates a new board. Returns the new board object including its `id`.

```python
kb_delete_board(board_id="b-123")
```
Deletes a board and all its columns and tasks. Irreversible.

---

### Columns

```python
kb_list_columns(board_id="board-001")
```
Returns all columns. Each has an `id` field you'll need for `kb_create_task` and `kb_move_task`.

```python
kb_create_column(title="QA", board_id="board-001", color="#FF8607")
```
Add a new column. Color is a hex string.

```python
kb_delete_column(list_id="list-backlog")
```
⚠️ Deletes the column and all its tasks permanently.

---

### Tasks — Reading

```python
kb_list_tasks(
    board_id="board-001",
    list_id=None,       # column ID (exact)
    owner=None,         # name/email substring e.g. "Eric", "ole"
    status=None,        # column name or ID e.g. "In Progress", "done"
    priority=None,      # "low" | "normal" | "medium" | "high" | "urgent"
    archived=False,     # True = archived only, False = active only (default)
    due_before=None,    # unix timestamp
    due_after=None,     # unix timestamp
    search=None,        # full-text across title, description, tags, owners
)
```
List tasks with filters. All args are optional — combine freely. Examples:
- `kb_list_tasks(owner="Eric")` — all of Eric's tasks
- `kb_list_tasks(status="In Progress")` — tasks in the In Progress column
- `kb_list_tasks(owner="ole", status="In Progress")` — Ole's in-progress tasks
- `kb_list_tasks(priority="high")` — high priority tasks
- `kb_list_tasks(search="auth")` — full-text search

```python
kb_get_task(task_id="t1")
```
Get full details of a single task by ID.

---

### Tasks — Writing

```python
kb_create_task(
    title="Fix login bug",
    list_id="list-backlog",          # required — get from kb_list_columns()
    board_id="board-001",
    description="Users can't log in on mobile",
    tags=["bug", "auth"],
    priority="high",                 # low | normal | high | urgent
    due_date=1782014400,             # unix timestamp, 0 = none
    checklist=["Reproduce", "Fix", "Test"],
)
```

```python
kb_update_task(
    task_id="t1",
    title="New title",
    description="Updated description",
    tags=["frontend"],
    priority="urgent",
)
```
Pass only the fields you want to change — the rest are preserved.

```python
kb_move_task(task_id="t1", list_id="list-done")
```
Move a task to a different column (equivalent to drag-and-drop).

```python
kb_delete_task(task_id="t1")
```
Permanent delete.

```python
kb_archive_task(task_id="t1")
```
Soft delete — hides the task without destroying it.

```python
kb_unarchive_task(task_id="t1")
```
Restore an archived task.

```python
kb_assign_owners(task_id="t1", owners=["alice", "bob@example.com"])
```
Set (replace) all owners on a task.

```python
kb_bulk_move(from_list_id="list-progress", to_list_id="list-backlog")
```
Move every task from one column to another in one call. Returns `{"moved": N, "errors": [...]}`.

---

### Checklist

```python
kb_add_checklist_item(task_id="t1", text="Write tests")
```

```python
kb_toggle_checklist_item(task_id="t1", index=0, checked=True)
```
Index is 0-based.

---

## Typical Agent Workflow

```python
# 1. Orient — see the board state
summary = kb_summary()

# 2. Find the column you need
columns = {c["title"]: c["id"] for c in summary["columns"]}
# e.g. columns = {"Backlog": "list-backlog", "In Progress": "list-progress", ...}

# 3. Create a task
task = kb_create_task(
    title="Investigate memory leak",
    list_id=columns["Backlog"],
    priority="high",
    tags=["performance"],
)

# 4. Move it when work starts
kb_move_task(task["id"], columns["In Progress"])

# 5. Mark done when complete
kb_move_task(task["id"], columns["Done"])
```

---

## Notes

- All writes go to the live board — changes are visible immediately in the UI.
- No authentication required — anyone with this skill (and reach to the URL) has full read/write access.
- **The board URL is auto-resolved** (see Overview) — no editing needed. Override with the `KANBAN_URL` env var, or at runtime with `kb_use_board(url)` / `kb_reset_board()`.
- **No password gate.** The board UI loads directly. (Note: the API is open — anyone who knows your published URL can read/write it. Don't publish a board with sensitive data unless you're comfortable with that.)

---

## UI Features (kanban.html)

Key front-end behaviours to be aware of when editing `kanban-board/kanban.html`:

- **Done column treatment:** Cards in any column titled "Done" (case-insensitive) automatically get `card-done` class: 90% opacity, orange top-border highlight, diagonal sheen via `::before`, orange glow on hover, and a small `✓` pill badge (`.done-badge`) in the top-right corner. Controlled by the `isDone` prop on `<Card>`.
- **Multi-owner chip input:** Modal Owners field is a chip input — Enter/comma adds, ×removes. Stored as `task.participants[]`.
- **Avatar hover tooltip:** Tooltips render via a fixed-position `#avatar-tooltip-portal` div (plain JS, not React) to avoid clipping by `overflow:hidden` column containers. `showAvatarTip(e, name, role)` / `hideAvatarTip()` are global functions added in a `<script>` block before React.
- **Column drag-and-drop:** Columns can be reordered by dragging their header.
- **Status field removed:** Status was removed from both card face and modal (column = status). Do not re-add it.
- **API_BASE:** Derived from `window.location.pathname` at runtime, so the same `kanban.html` works at `localhost:5555/` and behind any published path prefix (`/{USER_ID}-kanban-board/`). Do not hardcode a prefix.
