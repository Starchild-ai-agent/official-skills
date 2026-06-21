---
name: agent-hooks
version: 1.4.0
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
- "Don't let the agent claim it published when it didn't" → `on_completion_claim` (in `/goal`) or `on_stop` (in normal chat)
- "If the answer fails my quality check, make the agent redo it" → `on_stop` block

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

## Events (12) and what each can do

| Event | Fires | Capability | stdin gives the script |
|---|---|---|---|
| `on_user_message` | a user message arrives, before the model sees it | **block** / rewrite text | `message`, `channel` |
| `pre_tool_call` | before a tool runs | **block / rewrite input** | `tool_name`, `tool_input` |
| `post_tool_call` | after a tool runs | observe (log/metrics) | `tool_name`, `tool_result` |
| `transform_tool_result` | result before agent sees it | **append a note** | `tool_name`, `tool_result` |
| `pre_llm_call` | before a model call | **inject context** | `system`, `last_user_message`, `model` |
| `post_llm_call` | after a model reply | observe / swap | `model` |
| `on_response_end` | final reply assembled, once per turn | **rewrite reply** | `response`, `model`, `tokens`, `tool_names` |
| `on_stop` | turn boundary, after `on_response_end` | **block → force a redo** | `response`, `tool_names`, `stop_hook_active` |
| `on_outbound_message` | before a TG/WeChat push | **block / rewrite outbound** | `notification`, `type` |
| `on_completion_claim` | agent claims a `/goal` done | **block → force a redo** | `goal`, `summary`, `response`, `tool_names` |
| `on_session_start` | session begins | observe | `status` |
| `on_session_end` | session ends | observe / cleanup | `status` |

Every payload also includes `event`, `session_id`, `agent_id`, `cwd`.

### The three "make the agent fix it" levers (don't mix them up)

These three fire near the end of a turn but have **very different power** — pick
by *what you need to happen* when something's wrong:

| Event | Power | Use when |
|---|---|---|
| `on_response_end` | **rewrite only** — edit the stored/forwarded reply (footer, redaction, mask). Cannot make the agent redo. Zero loop risk. | You only need to *change the text* (mask a leaked key, add a cost footer). |
| `on_stop` | **block → redo, in normal chat** — steers your `reason` back as the next instruction and the agent keeps working. Kernel-capped (≤3 redos/turn) + `stop_hook_active` flag, so it can't trap a turn. | You need the agent to *actually fix/verify its own output* in ordinary conversation (quality gate, citation/publish check). Claude Code "Stop" hook parity. |
| `on_completion_claim` | **block → redo, in `/goal` only** — refuses a fabricated "done" and keeps the goal loop running. | Same redo power, but it only fires inside a running `/goal` supervisor loop. |

Rule of thumb: **mask → `on_response_end`; redo in chat → `on_stop`; redo in a
goal → `on_completion_claim`.** Note `on_response_end` can only rewrite the
*stored* copy — tokens already streamed to a live web client can't be unsent, so
prefer `on_stop` when you need the user to actually see a corrected answer.

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

### Writing a readable `reason`

The `reason` is shown to the **user** (on the blocked-action card) and to the
**model**. Write a plain sentence a person can read — say *what* you blocked and
*why*, not just a raw command. The UI splits one reason string into two parts
for you, so you don't parse anything client-side:

- **Explanation + command box** — put the human sentence first, then `: `, then
  the offending command/payload. Everything after the first `": "` is rendered
  in a separate monospace box. The split only triggers when that tail looks like
  a payload (has a space or is longer than ~12 chars), so an ordinary sentence
  that happens to contain a colon is left intact.
- **Sentence only** — a reason with no `": "` shows as a single sentence and no
  command box. That's the right shape when there's nothing to quote (e.g. a
  pasted seed phrase).
- **`[tag]` is stripped** — a leading tag like `[security]` is removed before
  display and the sentence is auto-capitalised, so you can keep a tag for your
  own `grep` without it leaking into the UI.

```jsonc
// Good — readable sentence + a clean command box:
{"decision": "block",
 "reason": "[security] This command is irreversible and would erase the disk: mkfs.ext4 /dev/sda1"}
//  ->  "This command is irreversible and would erase the disk"   +   [ mkfs.ext4 /dev/sda1 ]

// Avoid — a bare command or lone tag as the whole reason:
{"decision": "block", "reason": "mkfs /dev/sda1"}   // user sees no WHY
```

A hook that doesn't follow this still works — a plain string just renders as one
sentence. The convention only unlocks the nicer "explanation + command" layout.

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

## Ready-made scripts (each has ONE clear job)

Two **production-grade, multi-event guards** ship in this skill under
`templates/` (copy + approve as-is). Four **single-purpose examples** ship with
the host under `extensions/shell_hooks/examples/` (copy + adapt). No two overlap
— pick by the job, not by trial.

### Production templates (in this skill, `templates/`)

| Template | Events | Its one job |
|---|---|---|
| `security_guard.py` | `on_user_message`, `pre_tool_call`, `transform_tool_result`, `on_response_end`, `on_outbound_message` | **Secrets + destructive bash.** Block pasted/exfiltrated secrets (API keys incl. Bearer, PEM/EVM private keys, BIP-39 seeds, Solana byte-array & base58 WIF), mask leaked keys in replies/pushes, block irreversible-data-loss bash. See below. |
| `verify_publish_claims.py` | `on_stop` (chat redo) / `on_completion_claim` (`/goal` redo) / `on_response_end` (rewrite fallback) | **Anti-hallucination.** Catch fabricated "published / posted to AgentX / scheduled" claims by checking the reply against ground truth (previews registry, AgentX ledger, scheduler registry). |

### Single-purpose examples (host repo, `extensions/shell_hooks/examples/`)

| Script | Event | Its one job |
|---|---|---|
| `pii_redactor.py` | `transform_tool_result`, `on_response_end` | Mask emails / phones (PII — distinct from secrets). |
| `tool_audit_log.py` | `post_tool_call` | Observe-only: append every tool call to a JSONL audit trail. |
| `budget_alert.py` | `on_response_end` | Append a soft warning when a turn's cost crosses a threshold. |
| `inject_website_reminder.sh` | `pre_llm_call` | Preventive nudge: remind the model to actually publish before claiming done (pairs with `verify_publish_claims.py`). |

### Superseded by the templates (don't ship a second, conflicting guard)

The host repo also ships some **minimal single-event examples** under
`extensions/shell_hooks/examples/` that overlap the two templates above. They're
fine as learning references, but for real use prefer the template — running both
just creates two guards with possibly different policies.

| Minimal example | Use this instead | Why |
|---|---|---|
| `block_secrets.py` | `security_guard.py` | the guard's secret detection is a strict superset (adds Bearer, Solana byte-array, base58 WIF, destructive-bash, masking) |
| `check_publish.sh` | `verify_publish_claims.py` | the template also covers AgentX posts + scheduled tasks and checks the same registry |

**Removed outright** (orphan duplicates, fully folded into `security_guard.py`):
`secret_guard.py` (vendor-key block/mask, incl. Bearer) and
`dangerous_bash_guard.py` (destructive-bash block). Want to *also* block
installers / force-push? Tune the guard's `DESTRUCTIVE` table rather than running
a second bash guard with a conflicting policy.

For any rule none of the above covers, write a fresh script — the minimal block
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
    print(json.dumps({"decision": "block", "reason": f"This command is irreversible and would erase data, so I've blocked it: {cmd}"}))
else:
    print("{}")   # continue
PY
```

## All-in-one security guard (`templates/security_guard.py`)

A ready-to-use, self-contained script that wires **one file to five events** and
covers the common "don't leak secrets / don't nuke the box" baseline. Copy it to
your workspace and approve it once:

```
/hooks approve /data/workspace/skills/agent-hooks/templates/security_guard.py
/hooks on
```

Wire all five events to the same command in `config/shell_hooks.yaml` (one block
per event, `command:` = the script path). `/hooks approve <script>` then approves
every event that script is configured for in one shot.

| Event | What it does |
|---|---|
| `on_user_message` | **block** a pasted API key (incl. Bearer token), private key (PEM / EVM hex), seed phrase, Solana byte-array secret, or base58 WIF before the model sees it |
| `pre_tool_call` (bash) | **block** only irreversible data loss (`rm -rf /`, `dd` to a block device, `mkfs`, fork bomb, `chmod -R 777`, `git reset --hard origin/*``) and credential exfiltration (`cat .env | curl`, `scp id_rsa`, `printenv | curl`) |
| `pre_tool_call` (message tools) | guard `send_to_telegram` / `send_to_wechat` args — **mask** a leaked key, **block** a seed phrase (these tools bypass the push pipeline, so this is the real outbound gate for them) |
| `transform_tool_result` | **warn** when a tool's OUTPUT contains a secret (backend can only flag, not rewrite, result text) |
| `on_response_end` | **mask** any secret that leaked into the final reply |
| `on_outbound_message` | **mask / block** secrets before they're pushed to TG / WeChat |

**Design policy:** block only what is *both* very dangerous *and* not part of
normal work. Common dev actions like `curl | bash` (installers) and
`git push --force` (rebasing your own feature branch) are intentionally
**allowed** — over-blocking trains users to disable the guard.

Tune the `SECRET_PATTERNS`, `DESTRUCTIVE`, and `MSG_TOOLS` tables at the top of
the file for your own rules. `templates/security_guard_selftest.py` is the
self-test (run it after any edit; dangerous strings live there as data only, so
the host bash guard can't trip on them).

## Anti-hallucination guard (`templates/verify_publish_claims.py`)

Catches a fabricated success: the agent writes "Published! community.iamstarchild.com/…",
"Posted to AgentX /post/…", or "Reminder scheduled" when it never ran the tool.
The script checks the reply against **ground truth** — the previews registry
(`/data/previews.json`), the AgentX post ledger, and the scheduler registry —
and either rewrites the reply or forces a redo. It is deliberately
low-false-positive: a *real* published URL or an "offer to publish" (future
tense) passes untouched; only a past-tense success claim with no backing trips it.

```
/hooks approve /data/workspace/skills/agent-hooks/templates/verify_publish_claims.py
/hooks on
```

| Event | What it does |
|---|---|
| `on_stop` | **(preferred)** in ordinary chat, **block** a fabricated success and force the agent to actually publish/redo (loop-capped) |
| `on_completion_claim` | in a `/goal` loop, **block** a fabricated "done" and force a real publish (loop-capped) |
| `on_response_end` | rewrite-only fallback when `on_stop` isn't wired: append an honest "unverified" note (cannot make the agent redo) |

> **Wire it on `on_stop`** for normal chat — that's the only event that makes the
> agent *actually redo* a turn instead of just editing the text. The host honors
> only a `decision: block` on `on_stop` / `on_completion_claim` (a rewrite is
> ignored on those events), so the hook blocks on both and only rewrites on
> `on_response_end`. `templates/verify_publish_claims_selftest.py` is the self-test
> (covers the `on_stop` block path + the loop cap).

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
(`pre_tool_call`, not `PreToolUse`). Claude Code's **`Stop`** hook maps to our
`on_stop` (block → force a redo); its **`UserPromptSubmit`** maps to
`on_user_message`. A Stop script that returns `{"decision":"block","reason":…}`
or exits 2 works unchanged once wired to `on_stop`.

## Troubleshooting "my hook never fires"

1. Is the event one of the 12 above? (a typo is a silent no-op)
2. Is the **master switch** on? `/hooks list` shows it; `/hooks on` to enable.
3. Is the hook **approved**? `✗ NOT approved` in `/hooks list` → `/hooks approve`.
4. Does the `matcher` regex actually match? Too narrow = never spawns.
5. Run `/hooks doctor` — it flags non-executable / tampered / timed-out / non-JSON.

## Deep reference

Full protocol, security model, and per-event payload detail live in the agent's
own docs: `config/context/references/agent-hooks.md` (read it for edge cases this
skill summarizes).
