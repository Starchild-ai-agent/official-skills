---
name: cli-bridge
version: 0.1.5
description: |
  Manage short-code bundles that authorize the local starchild CLI to talk to this agent.

  Use when connecting or disconnecting the starchild CLI (e.g. mint a CLI bridge code, list my CLI bundles, revoke an old CLI session).
delivery: script
metadata:
  starchild:
    emoji: "🔗"
    skillKey: cli-bridge
    requires:
      bins: [python3]
user-invocable: false
author: starchild
tags: [cli, akm, bridge, sc-chatroom, short-code]

---

# cli-bridge — issue CLI bundles for the user's own `starchild` binary

This skill mints a fresh AKM key (`scope=chat:bridge:cli`) on the local
clawd, then registers it with sc-chatroom in exchange for a short opaque
code (``sc_xxxxxxxx``). The bundle handed to the user contains only that
short code — never the AKM secret, never the Fly machine id.

```
+----------------+   POST /agent/chat/stream   +-----------------+
| starchild CLI  |   Bearer sc_xxxxxxxx        | sc-chatroom     |
| (user laptop)  | --------------------------> | (gateway)       |
+----------------+                             +--------+--------+
                                                        |
                            resolves sc_… → AKM + container_id
                                                        |
                                                        v
                                          POST /chat/stream (Bearer sk_…
                                          + fly-force-instance-id)
                                          +----------------------+
                                          | user's own clawd     |
                                          | (Fly internal)       |
                                          +----------------------+
```

## Why a short code instead of the raw AKM?

Earlier versions baked the AKM secret + Fly machine id into the bundle
directly. That worked but had two downsides — the bundle leaked routing
metadata when decoded, and any party that ever held the bundle held a
permanent AKM secret. The short-code form fixes both:

- Bundle base64 decodes to ``{d, c:"", k:"sc_…", s, exp, l}`` — no
  secret, no Fly machine id.
- ``cli-revoke <sc_…>`` kills just the short code; the underlying AKM
  stays alive (use ``cli-revoke --akm <prefix>`` to nuke that too).
- sc-chatroom now holds the AKM secret in its DB. That's a deliberate
  trust shift — the AKM stays inside Fly's internal network instead of
  riding around on user laptops.

## Scope boundary — read this first

`cli-bridge` covers **exactly one path**: the user's local CLI talking 1:1
to that user's own clawd. It is **not** a chatroom membership credential.

| Use case | Right credential | Wrong |
|---|---|---|
| Personal CLI ↔ own clawd (this skill) | `chat:bridge:cli` AKM, fronted by `sc_…` code | — |
| Join an sc-chatroom room | `chat:thread:chatroom-{room_id}` AKM via `chatroom join` | `chat:bridge:cli` AKM |
| Browse a public room as a guest | no credential needed | any AKM |

## Prerequisites

Same as `chatroom`:

- AKM is installed in this clawd (`POST /api/keys` works on loopback)
- AKM accepts `scope="chat:bridge:cli"` and the `/chat/stream` middleware
  allows arbitrary `thread_id` for that scope (already shipped in clawd
  branch `aladdin/feat/akm-chatroom`)
- sc-chatroom is on a build that includes `POST /cli-keys` (migration 007+)
- `FLY_MACHINE_ID` (or `CONTAINER_ID`) env is set
- `CHATROOM_PUBLIC_URL` env points at the sc-chatroom gateway (defaults
  to `https://workroom.iamstarchild.com`)
- `CHATROOM_SERVER_URL` env points at the Fly-internal sc-chatroom
  (defaults to `http://sc-chatroom.internal:8080`)

## Commands

### `cli-login` — mint a new bundle

```bash
python3 skills/cli-bridge/scripts/cli_login.py --label "my laptop"
python3 skills/cli-bridge/scripts/cli_login.py --label "codex-vm" --ttl-days 14
```

Default TTL is 30 days; max is 90 days. Output is a one-liner the user
copies into `starchild login`. The bundle is opaque — sc-chatroom
resolves it on each call.

### `cli-list` — show active bundles

```bash
python3 skills/cli-bridge/scripts/cli_list.py
python3 skills/cli-bridge/scripts/cli_list.py --include-revoked
```

Lists every CLI short code minted by this user on sc-chatroom. Columns:
code, issued, expires, uses, label.

### `cli-revoke` — kill a bundle

```bash
python3 skills/cli-bridge/scripts/cli_revoke.py sc_xxxxxxxx
python3 skills/cli-bridge/scripts/cli_revoke.py --akm sk_yyyyyy
```

Default: kills the short code in sc-chatroom; underlying AKM stays alive.
With `--akm`: also revokes the AKM on local clawd, taking out every
bundle backed by it.

## End-to-end smoke test

```bash
# 1. Inside agent chat:
@agent give me a cli key for my laptop
# → outputs `starchild login starchild_<base64>` (bundle has sc_… code)

# 2. On laptop:
starchild login starchild_xxx
starchild whoami
starchild "hello, who are you?"
# → starchild sends Bearer sc_… to sc-chatroom; sc-chatroom resolves
# → it to AKM + container_id and forwards to user's clawd

# 3. Revoke the short code from chat:
@agent revoke cli code sc_xxxxxxxx

# 4. Next CLI call should fail at the gateway:
starchild "hello?"
# → "gateway rejected (401) — code may be revoked; ask your agent for a fresh CLI bundle"
```

## Pipe / shell composition (CLI ≥ v0.1.0)

Once paired, `starchild` is pipe-friendly. It reads stdin when no
positional prompt is given, writes the assistant reply to stdout, and
sends diagnostics to stderr — so it composes with any Unix tool.

```bash
# stdin → reply
echo "explain monads in 3 lines" | starchild

# reply → downstream
starchild "what is the OWASP top 10?" | pbcopy

# full three-stage pipe with streaming output
( echo "summarize this README:"; cat README.md ) | starchild --stream | tee summary.md

# code review pattern — concatenate context + question upstream
( echo "review this diff, flag risky changes:"; git diff ) | starchild
```

**Gotcha:** when you pass a positional prompt, stdin is **ignored**.
To send both context and an instruction, concatenate them upstream
with `( echo "<question>"; cat <file> )` rather than relying on
`cat <file> | starchild "<question>"` (which would silently drop the
file contents).

## SOUL.md hint (recommended)

Add to your agent's SOUL.md so the LLM picks the right tool when the
user asks for a CLI key:

```markdown
## Issuing CLI bundles for the user's own bots/scripts

When the user asks "give me a cli key" / "create a starchild bundle" /
"let me talk to you from my terminal", run:

  python3 skills/cli-bridge/scripts/cli_login.py --label "<inferred>"

Default the label to something like "untitled-YYYY-MM-DD" if the user
doesn't suggest one. Show them the resulting bundle and tell them how
to revoke: `cli-list` to find the code, then `cli-revoke sc_…`.

After pairing, mention they can also pipe into the CLI from their
shell — e.g. `echo "..." | starchild`, `starchild "..." | pbcopy`,
or `( echo "review:"; git diff ) | starchild`. Stdout is the reply
(pipe-safe), stderr is diagnostics. Note the gotcha: passing a
positional prompt makes stdin get ignored, so context + question
should be concatenated upstream.
```
