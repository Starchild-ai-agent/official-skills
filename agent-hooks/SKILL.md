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
| Dry-run the script via `bash` | `/hooks doctor` (verify) |
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
    command: ./extensions/shell_hooks/examples/block_secrets.py
    timeout: 10                          # seconds, default 20, max 120
```

## Two hook transports

A hook is either a local **command** (default) or an **HTTP endpoint** — same
payload in, same decision JSON out, only the transport differs.

```yaml
hooks:
  - event: pre_tool_call
    type: http                          # omit type -> "command" (default)
    url: https://my-guard.example.com/hook
    timeout: 10
```

HTTP specifics:
- **SSRF guard** — the URL must be http(s) and must NOT resolve to a loopback /
  private / link-local (incl. cloud metadata `169.254.169.254`) / reserved
  address (blocked at parse AND call time). Set
  `STARCHILD_SHELL_HOOKS_HTTP_ALLOW_LOCAL=1` only to intentionally hit a local
  service.
- **Approval keys on the URL**: `/hooks approve <event> <url>`; `/hooks list`
  shows it as `POST <url>` and skips the executable/mtime checks.

## Adding an LLM judgement (call the proxy, NOT /chat)

When a hook needs real reasoning ("does this leak a secret?", "is this
completion actually done?"), call an LLM **directly through the proxy** from your
script — never the agent's own `/chat`.

```python
from core.http_client import proxied_post
import json, sys

event = json.load(sys.stdin)
r = proxied_post(
    "https://openrouter.ai/api/v1/chat/completions",
    json={
        "model": "minimax/minimax-m3",   # cheap default (~$0.0002/call)
        "messages": [
            {"role": "system", "content":
                'You are a guard. Output ONLY JSON {"decision":"block|allow","reason":"..."}.'},
            {"role": "user", "content": json.dumps(event)},
        ],
        "temperature": 0, "max_tokens": 200,
    },
    headers={"SC-CALLER-ID": "chat:hook"},   # required for billing
    timeout=40,
)
try:
    print(json.dumps(json.loads(r.json()["choices"][0]["message"]["content"])))
except Exception:
    print("{}")   # fail-open on any parse error
```

Why proxy-direct: OpenRouter is an external stateless API, so it does **not**
re-enter the agent loop or fire `pre_llm_call` -> **no recursion**, one cheap
completion instead of a full agent turn, your own prompt + pure-JSON response.
Calling `/chat` from a hook re-emits the same event (the bridge guards against
the loop, but it's needless overhead) — and an LLM hook that calls `/chat` must
**never** sit on `pre_llm_call`. See the host docs `sc-proxy.md` section
"Calling an LLM through the proxy".

## Standard workflow (the agent's checklist)

1. **Clarify** the rule and pick the event from the table above.
2. **Write the script** — read JSON on stdin, print a decision on stdout.
   Exit non-zero / non-JSON = continue. Make it executable (`chmod +x`).
3. **Add a config entry** in `workspace/config/shell_hooks.yaml` (add a `matcher`
   regex when possible so the script only spawns when relevant).
4. **Dry-run it yourself with `bash`** — pipe a sample JSON payload into the
   script and confirm it prints valid JSON. (The agent CANNOT run `/hooks` —
   that is a user-typed command. Ask the user to run `/hooks doctor` to verify
   after approval.)
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
| `block_secrets.py` | multi | private-key / seed-phrase guard (inbound warn + outbound/tool hard-block) |
| `check_publish.sh` | `on_completion_claim` | block "claimed published but no publish tool ran / cited a fake URL" |
| `inject_website_reminder.sh` | `pre_llm_call` | inject a context note when a published site exists |

For any other rule (block dangerous bash, audit tool calls, redact outbound
PII, warn on prod writes, ...), write a fresh script — the minimal block
example below is the template, and the output protocol above covers every
capability.

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
