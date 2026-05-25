---
name: temp-files
version: 1.0.2
description: Workroom file relay — agents hand off files, directories, and zipped bundles to each other through the sc-agent-backup /temp-files subsystem. TTL, sliding renewal, internal short links. Distinct semantics from the backup skill.
metadata:
  starchild:
    emoji: "🔁"
    skillKey: temp-files
user-invocable: true
tags: [temp-files, workroom, handoff, share, ttl, links]
---

# Temp-Files — Workroom file relay

This skill lets one agent drop temporary files, directories, or whole-site
snapshots to another agent without polluting the long-term backup namespace
and without an external file host.

| Trigger | Flow | What it does |
|---|---|---|
| `/tf put`, "drop this file in the relay", "share this with agent B" | **A. Upload** | Write to path → returns `expires_at` |
| `/tf list`, "show me what's in the relay", "list temp files" | **B. List** | One-level `ls`: files + subdirs |
| `/tf get`, "pull X down", "download X" | **C. Download** | File straight through / dir as zip |
| `/tf rm`, "delete X from the relay" | **D. Delete** | Single file, or `--recursive` subtree |
| `/tf link`, "make a temp link for agent B" | **E. Short link** | Mint a `tf_xxxx` internal short link |

Every command hits the same service (`sc-agent-backup.internal`) and
authenticates with the container's built-in `CONTAINER_JWT`. Identity and
path are derived from the JWT:
**`user_id = JWT.userInfoID`, `agent_scope = JWT.containerId`** (defaults to
`default`). You cannot reach, see, or delete relay files belonging to another
user or another agent.

## Difference vs. the `backup` skill (must read)

| Dimension | `backup` skill | `temp-files` skill (this one) |
|---|---|---|
| Purpose | Long-term agent state | Short-term handoff, collaboration relay |
| Addressing | Server-generated `backup_id` | Caller-supplied path |
| Model | Immutable `tar.gz` bundle | Path-based filesystem, overwritable |
| Quota | 5 bundles / user, hard cap | Byte quota + per-file size limit |
| TTL | None | **Default 7 days, sliding on access/overwrite, hard cap 60 days** |
| Cross-agent | Restore the whole bundle | Per-file / per-directory + short link |

**Never mix the two.** "Restore an entire agent state" → use `backup`.
"Hand off one artifact so the other agent can carry on" → use this skill.

## Operational rules

### Rule 1 — Do not use the relay as a file host

Default file TTL is 7 days. Even with overwrite/download sliding renewal,
the hard cap is 60 days. Anything that needs to stick around goes through
`backup` or `volume-backup`.

### Rule 2 — Path whitelist

The server only accepts segments matching `[A-Za-z0-9._\- ]`. It rejects
`..`, absolute paths, empty segments, and control characters. Just pass a
relative path:

- `skills/my-skill/SKILL.md`  ✅
- `sites/staging/index.html`  ✅
- `../escape.txt`  ❌ → 400 bad_path
- `/abs/oops.md` gets its leading slash stripped — better not to send it

### Rule 3 — Short links are "agent-to-agent inside", not public sharing

The first-pass short link follows a **capability URL model**:

- Whoever holds `tf_xxxxxxxx` can fetch it (the code itself is the credential — 64 bits of entropy)
- But still requires the **6PN internal network** + a **valid `CONTAINER_JWT`** (for audit)
- A browser or bare `curl` has no token, so it gets 401 — that's expected, not a bug
- Cross-user agents *can* fetch, because that is exactly the Workroom handoff use case

Correct flow:

1. Agent A calls `/tf put` to upload
2. Agent A calls `/tf link` and receives `tf_xxxxxxxx`
3. Agent A sends the short link to agent B over Workroom
4. Agent B (inside Fly, with its own `CONTAINER_JWT`, possibly under a different
   user) calls `tf fetch tf_xxxxxxxx` to retrieve it

**Do not** hand `http://sc-agent-backup.internal:8080/t/<code>` to an end user
to open in a browser — it isn't publicly reachable. If/when public sharing
ships, wait for the phase-B public resolver.

**Cleanup rule**: once the receiver confirms they have the file, the sender
should immediately `tf unlink <code>` to revoke the short link and stop the
token from lingering. Sensitive content *must* be unlinked — don't rely on
TTL as a backstop.

### Rule 4 — Stop on failure, do not silently retry

If any `tf.py` subcommand exits non-zero, **stop immediately and return the
stderr verbatim to the user**. Do not "let me try again for you."

## Install path

The skill installs into `/data/workspace/skills/temp-files/`. Every command
runs from the agent's working directory:

```bash
python3 skills/temp-files/scripts/tf.py <subcommand> ...
```

## Command reference

Environment for every command:
- `CONTAINER_JWT` — injected by ai-agent, required
- `TEMP_STORAGE_URL` — optional, defaults to `http://sc-agent-backup.internal:8080`

Global output switches (place before the subcommand):
- `--verbose`: emit full payload / error meta (for debugging)
- `--json`: stable JSON envelope, same keys on success and failure
  - success: `{ok: true, error: "", message: "ok", detail: "", data: {...}}`
    - `data` defaults to the command's compact view (minimum useful field set)
    - with `--verbose`, `data` becomes the server's raw payload (all fields)
  - failure: `{ok: false, error: "<code>", message: "...", detail: "...", exit_code: N}`
    - `error` is the server's error code (e.g. `bad_path` / `not_found` / `quota_exceeded`) or `usage_error` / `http_error`
    - with `--verbose`, includes a `meta` sub-structure (HTTP status / server's original message+detail)
- default (no switches): compact output, the smallest useful set of fields (readable by humans and agents alike)

Note: `tf list` and `tf links` without `--json` print a human-friendly table;
with `--json` they go through the envelope and `data` carries the full
`entries`/`links` array.

### Recommended defaults (quick reference)

| Flag | Recommended | Why |
|---|---|---|
| `link --ttl-seconds` | `3600` (1 hour) | Long enough for the receiver to fetch once, short enough not to linger |
| `put --ttl-days` | `7` (default) | Covers a typical review cycle |
| `fetch --extract` | **always pass it** | Auto-unpack, one less step, zip-slip defence built in |
| `get` on a directory | must pass `--zip` | Server has no plain-directory download mode |
| `unlink` after handoff | call as soon as the receiver confirms | Short code = credential; sensitive content must be revoked |

### A. Upload / overwrite

```bash
python3 skills/temp-files/scripts/tf.py put <local-file> <remote-path> \
    [--ttl-days N]
```

Example:

```bash
python3 skills/temp-files/scripts/tf.py put ./SKILL.md skills/demo/SKILL.md
# → {"path": "...", "size_bytes": ..., "expires_at": ...}
```

Same-name uploads overwrite; the response returns a fresh `expires_at`.

### B. List

```bash
python3 skills/temp-files/scripts/tf.py list [--prefix PATH]
```

No `--prefix` lists the root; `--prefix sites/` lists one level under that.

### C. Download

```bash
# Single file
python3 skills/temp-files/scripts/tf.py get <remote-path> <local-dest>

# Whole directory as a zip
python3 skills/temp-files/scripts/tf.py get <remote-dir> <local-dest.zip> --zip
```

A successful download slides the TTL forward by 7 days.

### D. Delete

```bash
# Single file / empty directory
python3 skills/temp-files/scripts/tf.py rm <remote-path>

# Non-empty directory
python3 skills/temp-files/scripts/tf.py rm <remote-dir> --recursive
```

### E. Short links

```bash
python3 skills/temp-files/scripts/tf.py link <remote-path> \
    [--zip] [--ttl-seconds 3600]
# → {"code": "tf_xxxxxxxx", "url": "http://.../t/tf_xxxxxxxx", ...}

# List currently active short links
python3 skills/temp-files/scripts/tf.py links

# Revoke
python3 skills/temp-files/scripts/tf.py unlink <code>
```

Short link TTL defaults to 1 hour and caps at 7 days (independent of the
file's own TTL).

### F. Pull data via a short link (what the receiving agent runs)

```bash
# Download + auto-unpack (strongly recommended)
python3 skills/temp-files/scripts/tf.py fetch <code> <local-dest> --extract

# Or specify the extract directory
python3 skills/temp-files/scripts/tf.py fetch <code> ./pack.zip --extract ./out

# Without --extract: download only, no unpack
python3 skills/temp-files/scripts/tf.py fetch <code> <local-dest>
```

Any caller with a valid `CONTAINER_JWT` can fetch (cross-user is fine).

**Zip auto-detect**: when the server returns `Content-Type: application/zip`,
`fetch` and `get` automatically rename the local file to end in `.zip` and
tell you in the JSON output via `"kind": "zip"`.

**Auto-unpack (`--extract`)**:

- Uses Python's built-in `zipfile` / `tarfile`; no dependency on system `unzip`/`7z`
- Supported formats: `.zip` / `.tar` / `.tar.gz` / `.tar.bz2` / `.tar.xz` (detected by
  magic bytes, not the file suffix)
- Built-in zip-slip / tar-slip defence: `..` segments are rejected; symlink
  members are rejected
- With no value: extracts to a sibling directory (archive name minus suffix); with
  a value: extracts into the specified directory
- After a successful extract, the JSON output includes `extracted_kind` /
  `extracted_to` / `extracted_top`

Example JSON output (with `--extract`):

```json
{
  "saved": "output/tf_from_4814.zip",
  "kind": "zip",
  "bytes": 7363,
  "sha256": "...",
  "content_type": "application/zip",
  "server_filename": "temp-files-share.zip",
  "extracted_kind": "zip",
  "extracted_to": "output/tf_from_4814",
  "extracted_top": ["temp-files-share/"]
}
```

**So the receiving agent should**:

1. Call `fetch` with `--extract` by default
2. Read `extracted_to` from the stdout JSON — files live in that directory
3. If the JSON contains `extract_skipped` or `extract_error`, fall back to the
   `saved` path and handle it manually based on `kind`

## Typical scenarios

### Scenario 1: agent A hands a skill to agent B for testing

```bash
# A:
python3 skills/temp-files/scripts/tf.py put ./my-skill.zip skills/my-skill.zip
python3 skills/temp-files/scripts/tf.py link skills/my-skill.zip --ttl-seconds 3600
# Receive tf_xxxxxxxx, post it to B in Workroom

# B: (recommended: fetch + auto-unpack in one shot)
python3 skills/temp-files/scripts/tf.py fetch tf_xxxxxxxx ./inbox.zip --extract
# The fetch JSON already includes sha256 — no need to rerun sha256sum
# cd into JSON.extracted_to to test; write a report
python3 skills/temp-files/scripts/tf.py put ./test-report.md reports/test-report.md
python3 skills/temp-files/scripts/tf.py link reports/test-report.md --ttl-seconds 1800
# Send the report short link back to A

# Once A has the report:
python3 skills/temp-files/scripts/tf.py unlink tf_xxxxxxxx  # revoke the original skill short link
```

### Scenario 2: agent A hands a staging site to agent B

```bash
# A:
cd ./staging-site/
python3 skills/temp-files/scripts/tf.py put-dir . sites/foo --ttl-days 14
python3 skills/temp-files/scripts/tf.py link sites/foo --zip
# B receives a directory-zip link

# B:
python3 skills/temp-files/scripts/tf.py fetch tf_xxxxxxxx ./foo.zip --extract
cd ./foo
# Edit, then push back
python3 skills/temp-files/scripts/tf.py put-dir . sites/foo
```

## Security boundary cheatsheet

- 6PN only: the service returns 403 on the public internet
- JWT must be valid and `type ∈ {container, access}`
- Each user has an isolated namespace; each agent under that user has its own sub-scope
- Direct path access at `/temp-files/...` is user-isolated (you cannot reach others')
- Short links at `/t/<code>` are capabilities: anyone with the code can fetch (still requires 6PN + any valid JWT for audit)
- Paths reject `..` and control characters
- Per-file limit 200 MB, per-user quota 2 GiB (server-tunable)

## Common errors / troubleshooting

> Read `ERROR + DETAIL` first, then decide whether it's a parameter problem,
> a permission problem, or a missing object.
> If a command exits non-zero, follow the house rule: stop, do not silently retry.

| Scenario | Typical stderr | Root cause | Action |
|---|---|---|---|
| Illegal path (`..`/empty segment/illegal char) | `HTTP 400` + `DETAIL: error=bad_path, message=...` | `remote-path` violates the whitelist | Switch to a normal relative path, e.g. `skills/demo/SKILL.md` |
| Object does not exist | `HTTP 404` + `DETAIL: error=not_found, message=...` | Target file/dir is missing | Run `tf list --prefix ...` to confirm, then retry |
| TTL out of range | `ERROR: --ttl-days must be <= 60` or `--ttl-seconds ...` | CLI argument out of range (front-loaded check) | Use a value inside the allowed range |
| Not authorized | `HTTP 401/403` | Missing/invalid `CONTAINER_JWT`, or running outside the internal network | Run inside a Fly machine; confirm the JWT is injected |
| Downloaded a directory without `--zip` | `HTTP 400` (`DETAIL` mentions download mode) | Server requires zip mode for directories | `tf get <dir> out.zip --zip` |
| Deleted a non-empty directory without recursive | `HTTP 400/409` | Directory is non-empty but `--recursive` wasn't passed | `tf rm <dir> --recursive` |
| File too large or directory zip exceeds the limit | `HTTP 413` | Over the server's size limit | Split the directory/file and upload again |

### Minimal regression checklist (P1 gates)

After every CLI output or error-handling change, run at least these five:
1. Default output is compact (without `--verbose`), yet put/get/fetch still include `sha256` and link still includes `url`
2. `--verbose` emits the full field set (envelope's `data` = server's raw payload)
3. `--json` on success has every key: `ok, error, message, detail, data`
4. `--json` on failure has every key: `ok, error, message, detail, exit_code` (where `error` is the server error code)
5. Exit codes stay consistent: success = 0, business failure = 1, usage error = 2
6. `tf --json list` and `tf --json links` go through the envelope (don't let the subparser's `--json` override)

### Quick triage flow (share with collaborators)

1. `tf list --prefix <target-prefix>`: confirm the object actually exists.
2. Preserve the original stderr from the failing command (especially `DETAIL:`).
3. On 4xx: fix the arguments — do not retry the same command.
4. On 5xx / network error: wait briefly, then retry once.

## Notes

- File TTL defaults to 7 days; downloads/overwrites each renew by 7 days; hard cap 60 days
- Short link TTL defaults to 1 hour, capped at 7 days
- To force a shorter TTL: pass `--ttl-days 1` on upload (still bounded by the horizon)
- Directory-zip default caps: 5000 files / 500 MB; over either limit → 413
