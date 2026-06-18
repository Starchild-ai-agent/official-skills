---
name: agent-hooks
version: 1.0.0
description: "Manage shell hooks — user scripts that run at agent lifecycle points to block, rewrite, or warn on actions, via the /hooks command."
author: starchild
tags: [hooks, automation, security, lifecycle, scripts]

metadata:
  starchild:
    emoji: "🪝"
    skillKey: agent-hooks
    requires:
      bins: [bash, python3]

user-invocable: true
disable-model-invocation: false
---

# Agent Hooks

Shell hooks let a user run **their own script** at fixed points in the agent's
lifecycle — to **block** a dangerous action, **rewrite** an input or an outbound
message, **inject context** into the model, or **warn the user**. The script can
be written in any language; it talks to the agent over a simple JSON-on-stdin,
JSON-on-stdout protocol.

Tools: `read_file`, `write_file`, `bash`

## When to use

Reach for hooks when the user wants the agent to **automatically enforce a rule
or react to an event** without being asked each time. Examples:

- "Stop me from running `rm -rf` / destructive bash" → `pre_tool_call` block
- "Never let a private key get pushed to Telegram" → `on_outbound_message` block
- "Log every tool call for audit" → `post_tool_call` observe
- "Remind the agent of X at the start of every model call" → `pre_llm_call` context
- "Don't let the agent claim it published when it didn't" → `on_completion_claim`

If the user just wants a one-off check, that's not a hook — hooks are for
**recurring, automatic** lifecycle enforcement.

## How configuration works (who does what)

**The agent prepares everything; the user activates.** This split is a
deliberate security property — slash commands are parsed *before* the LLM sees
them, so prompt injection cannot forge an activation.

| Agent does (in conversation) | User must type (activation) |
|---|---|
| Write the hook script (any language) | `/hooks approve <event> <command>` |
| Write/extend `workspace/config/shell_hooks.yaml` | `/hooks on` (or the Preferences toggle) |
| Test with `/hooks doctor` | |
| Explain / debug | |

A hook is arbitrary code execution in the container, so the **"who may activate"**
gate is reserved for a real human. Always finish by handing the user the exact
`/hooks approve …` and `/hooks on` commands to paste.

## The two gates

A hook fires only when **BOTH** hold:

1. **Master switch ON** — `shell_hooks.enabled: true` in
   `workspace/config/agent.yaml` (flipped by `/hooks on|off` or the Preferences
   toggle; legacy env `STARCHILD_SHELL_HOOKS=1` forces it on as a fallback).
2. **Per-hook approval** — each `(event, command)` pair approved once via
   `/hooks approve` (recorded with the script's mtime, so a later edit is flagged
   "changed since approval" — a swap-the-script attack is visible).

Switch on but unapproved → inert (shows ✗ in `/hooks list`). Approved but switch
off → inert until `/hooks on`.

## The `/hooks` command

Plain text on web / Telegram / WeChat (no LLM, no cost):

| Command | What it does |
|---|---|
| `/hooks` or `/hooks list` | master switch state, config path, every hook + approval/health |
| `/hooks on` \| `/hooks off` | flip the master switch (hot mount/unmount, no restart) |
| `/hooks doctor` | run each approved hook against a synthetic payload, check JSON |
| `/hooks approve <event> <command>` | approve + activate live (no restart) |
| `/hooks revoke <command>` | revoke + detach live (no restart) |
| `/hooks help` | usage |

## Events (9) and what each can do

| Event | Fires | Capability | stdin gives the script |
|---|---|---|---|
| `pre_tool_call` | before a tool runs | **block / rewrite input** | `tool_name`, `tool_input` |
| `post_tool_call` | after a tool runs | observe (log/metrics) | `tool_name`, `tool_result` |
| `transform_tool_result` | result before agent sees it | **append a note** | `tool_name`, `tool_result` |
| `pre_llm_call` | before a model call | **inject context / block** | `system`, `last_user_message`, `model` |
| `post_llm_call` | after a model reply | observe | `model` |
| `on_outbound_message` | before a TG/WeChat push | **block / rewrite outbound** | `notification`, `type` |
| `on_completion_claim` | agent claims "done" | **refuse a fake completion** | `goal`, `summary`, `response`, `tool_names` |
| `on_session_start` | session begins | observe / inject | `status` |
| `on_session_end` | session ends | observe / cleanup | `status` |

Every payload also includes `event`, `session_id`, `agent_id`, `cwd`.

## Output protocol (what the script prints on stdout)

JSON object, or empty for "continue". Fields:

```jsonc
{"decision": "block", "reason": "..."}   // deny the action / refuse completion
{"tool_input": {...}}                     // pre_tool_call: rewrite EXISTING input keys
{"notification": "..."}                   // on_outbound_message: rewrite the message
{"context": "..."}                        // pre_llm_call: inject into prompt (AGENT-facing)
{"systemMessage": "..."}                  // allow, but show the USER a note
{"add_warning": "..."}                    //   same user-facing note channel
<empty>                                   // continue, no change
```

**`context` is agent-facing** (goes into the prompt, `pre_llm_call` only).
**`systemMessage` / `add_warning` is user-facing** (shown to the human on the
tool-result / completion / outbound surfaces) — never injected into the prompt.

Safety: scripts run with `shell=False` + argv split (no shell injection) and a
per-hook timeout. A script that errors, times out, or prints non-JSON falls
through to **continue** — a broken hook can never break the agent.

## Config file format

`workspace/config/shell_hooks.yaml`:

```yaml
hooks:
  - event: pre_tool_call
    matcher: "rm -rf|dd if=|mkfs"      # optional regex; script only spawns on a match (perf gate)
    command: ./extensions/shell_hooks/examples/guard_dangerous_commands.sh
    timeout: 10                          # seconds, default 20, max 120
```

## Standard workflow (the agent's checklist)

1. **Clarify** the rule and pick the event from the table above.
2. **Write the script** — read JSON on stdin, print a decision on stdout.
   Exit non-zero / non-JSON = continue. Make it executable (`chmod +x`).
3. **Add a config entry** in `workspace/config/shell_hooks.yaml` (add a `matcher`
   regex when possible so the script only spawns when relevant).
4. **Dry-run**: `/hooks doctor` (checks the script runs and returns valid JSON).
5. **Hand the user the activation commands** to paste:
   ```
   /hooks approve <event> <command>
   /hooks on
   ```
6. Confirm with `/hooks list` that it shows ✓ approved and live.

## Ready-made example scripts

Shipped in-repo under `extensions/shell_hooks/examples/` (copy + adapt):

| Script | Event | Purpose |
|---|---|---|
| `guard_dangerous_commands.sh` | `pre_tool_call` | block `rm -rf /`, `dd`, `mkfs`, `chmod 777`, fork bombs |
| `block_secrets.py` | multi | private-key / seed-phrase guard (inbound warn + outbound/tool hard-block) |
| `audit_tool_calls.py` | `post_tool_call` | append every tool call to `workspace/logs/tool-audit.jsonl` |
| `redact_outbound.py` | `on_outbound_message` | mask emails / phones / internal IPs before a push (or block on secrets) |
| `warn_on_prod_writes.sh` | `pre_tool_call` | allow writes to `.env` / prod config but `systemMessage`-warn the user |
| `check_publish.sh` | `on_completion_claim` | block "claimed published but no publish tool ran / cited a fake URL" |
| `inject_website_reminder.sh` | `pre_llm_call` | inject a context note when a published site exists |

### Minimal block example (`pre_tool_call`, any language)

```bash
#!/usr/bin/env bash
payload="$(cat)"
python3 - "$payload" <<'PY'
import json, sys, re
ev = json.loads(sys.argv[1])
cmd = (ev.get("tool_input") or {}).get("command", "")
if re.search(r"rm\s+-rf\s+/|dd\s+if=|mkfs", cmd):
    print(json.dumps({"decision": "block", "reason": f"refusing destructive command: {cmd}"}))
else:
    print("{}")   # continue
PY
```

## Claude Code compatibility

Hook scripts written for **Claude Code** work unchanged — their output is
auto-translated into the fields above:

| Claude Code output | Translated to |
|---|---|
| `hookSpecificOutput.permissionDecision: "deny"` (+ `permissionDecisionReason`) | `decision: block` (+ `reason`) |
| `hookSpecificOutput.additionalContext` | `context` |
| `hookSpecificOutput.updatedInput` | `tool_input` (rewrite) |
| `continue: false` (+ `stopReason`) | `decision: block` (+ `reason`) |
| `systemMessage` | `add_warning` (user-facing note) |
| `suppressOutput` | no-op (our stdout never enters the transcript) |
| exit code 2 with stderr, no stdout | `decision: block`, stderr is the reason |

Only the output **payload** is translated — event NAMES stay ours
(`pre_tool_call`, not `PreToolUse`).

## Troubleshooting "my hook never fires"

1. Is the event one of the 9 above? (a typo is a silent no-op)
2. Is the **master switch** on? `/hooks list` shows it; `/hooks on` to enable.
3. Is the hook **approved**? `✗ NOT approved` in `/hooks list` → `/hooks approve`.
4. Does the `matcher` regex actually match? Too narrow = never spawns.
5. Run `/hooks doctor` — it flags non-executable / tampered / timed-out / non-JSON.

## Deep reference

Full protocol, security model, and per-event payload detail live in the agent's
own docs: `config/context/references/agent-hooks.md` (read it for edge cases this
skill summarizes).
