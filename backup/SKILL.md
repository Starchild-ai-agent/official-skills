---
name: backup
version: 1.0.0
description: Manage this agent's state backups on sc-agent-backup storage — take snapshots, list prior backups, and restore the agent from any of them. Identity-bound; 5 backups per user, cap enforced on upload.
metadata:
  starchild:
    emoji: "🛡️"
    skillKey: backup
user-invocable: true
tags: [backup, snapshot, restore, agent-state, disaster-recovery]
---

# Backup — Snapshot Manager

One skill, three flows:

| Trigger | Flow | What happens |
|---|---|---|
| `/backup`, "备份…", "做个快照", "back up my agent", "バックアップ", … | **A. Create** | pack current agent state → upload to sc-agent-backup |
| `/restore`, "恢复…", "回滚到上次备份", "restore from backup", "復元", … | **B. Restore** | list → pick → download → apply each section (user-confirmed) |
| `/delete-backup`, "删除备份…", "delete a backup", "バックアップ削除", … | **C. Delete** | list → pick → **two user confirmations** → `DELETE /backups/{id}` |

All flows talk to the same storage service (`sc-agent-backup.internal`) using the container's `CONTAINER_JWT`. Identity is derived from the JWT — you can never read, write, or delete another user's namespace.

Storage has a hard cap of **5 backups per user**. Full uploads return a replace menu that **the user** picks from — never auto-pick the oldest.

## Language policy

**Every user-facing message you produce in these flows — prompts, summaries, confirmation questions, status updates, error explanations — MUST be in the user's conversation language.** Detect the language from the user's most recent messages (fall back to `user_settings.language` if ambiguous, fall back to English if that's also unclear).

The prompt examples throughout this SKILL.md are written in Chinese or English for illustration only. **Translate them.** Keep the same structure and detail level, but render the prose in whatever the user is actually speaking.

This applies to the rules file too:
- **Section headings** (`## Mode`, `## Extra excludes`, `## Extra paths`, `## Label template`, `## Notes`) stay in **English** — the parser depends on them.
- **Everything else** (intro prose, comments inside code blocks, example text, the `Notes` section, values like the label template) should match the user's language.

When you compose `backup_rules.md` after the first-time discussion (Flow A.1.0 case B.3), write the whole file in the user's language — only the five section headings stay English.

If a user's language preference isn't obvious from context and `user_settings.language` is missing, ask once: "What language should I use?" and stick with that.

---

## Operational rules (read before touching any flow)

### Rule 1 — Bash variables do NOT persist across tool calls

Every `bash` tool invocation starts a **fresh shell**. Variables set in one call (`WORK=$(mktemp -d ...)`) are empty in the next. **Passing `"$WORK/api"` to `pack.py` in a later tool call expands to `"/api"` and pack.py fails.**

Two safe patterns:

**(a) One bash call for the whole scratchpad setup:**

```bash
WORK=$(mktemp -d /tmp/backup-XXXXXX)
mkdir -p "$WORK/api"
echo "WORKDIR: $WORK"   # print the literal path so you can copy-paste it into later calls
# ... write the three API JSONs to $WORK/api/ in this SAME bash call if possible ...
```

**(b) Use a literal, deterministic path you remember verbatim:**

```bash
# In call 1:
WORK=/tmp/backup-20260427T164500Z
mkdir -p "$WORK/api"

# In call 2 (different shell — $WORK is now empty, so use the literal string):
python3 skills/backup/scripts/pack.py \
  --api-dir /tmp/backup-20260427T164500Z/api \
  --out /tmp/backup-20260427T164500Z/bundle.tar.gz \
  --label "..."
```

Pattern (b) is the robust choice when writing JSONs with your native file-write tool (which doesn't share a shell with bash at all).

If `pack.py` exits with `ERROR: --api-dir does not exist`, this is almost certainly the cause.

### Rule 2 — On any script failure, STOP the flow and surface the error

When `pack.py`, `upload.py`, `download.py`, `restore.py`, `delete.py`, `list.py`, `propose_rules.py`, `ensure_rules.py`, or any other script in these flows exits non-zero or errors unexpectedly:

1. **STOP the flow immediately.** Do not try the next step. Do not retry silently.
2. **Surface the exact stderr to the user** (at least the first 10 lines), in their conversation language. Include the script name and exit code.
3. **State explicitly that you stopped.** "备份失败了，我已经停下，没做进一步操作。下面是错误："
4. **Wait for the user to direct you.** Do not loop on "trying again" unless the user asks.

**Anti-pattern to avoid**: replying with generic acknowledgements like "了解", "ok", "understood", "明白" after a failure. If the last action failed and the user hasn't given you a fix, **you don't have new work to acknowledge** — stating the failure once and waiting is the correct behavior.

This applies even when the user's follow-up messages are unrelated. If the user asks an unrelated question after a backup failure, answer that question AND remember the backup is still in a failed state — don't pretend it's still progressing.

### Rule 3 — Install paths

The `backup` skill installs to `/data/workspace/skills/backup/`. Script paths in all examples below should be interpreted as **relative to the agent's working directory (`/data/workspace/`)**:

```bash
python3 skills/backup/scripts/pack.py ...
python3 skills/backup/scripts/upload.py ...
# etc.
```

If you want to be defensive about cwd, use full absolute paths:

```bash
python3 /data/workspace/skills/backup/scripts/pack.py ...
```

The examples in this doc use the short form. Don't prepend `sc-backup-service/` — that's the upstream project name, not part of the install path.

### Rule 4 — **HARD BAN**: do not edit skill code files

Any file under `/data/workspace/skills/backup/` is **read-only from your perspective as an agent**. You must not invoke `Edit`, `Write`, `bash`-level `sed`/`tee`/redirect-overwrite, or any other mutation tool against:

- `skills/backup/SKILL.md`
- `skills/backup/scripts/pack.py`
- `skills/backup/scripts/propose_rules.py`
- `skills/backup/scripts/upload.py` / `download.py` / `restore.py` / `list.py` / `delete.py` / `ensure_rules.py`

Even if you believe you've identified a bug or a missing exclusion, **the fix never goes in these files**. Those paths are the universal skill contract; a local edit silently diverges this agent from every other Starchild agent using the skill.

**All backup-behavior adjustments go in ONE place**: `/data/workspace/config/backup_rules.md`. This file is yours (the user's copy) to shape freely.

#### The canonical wrong-vs-right pattern

When you notice a backup is too large because some path is getting bundled:

| Wrong | Right |
|---|---|
| `Edit skills/backup/scripts/pack.py` to add `.cache` to `DEFAULT_SKIP_DATA_TOP` | `Edit /data/workspace/config/backup_rules.md` to add `.cache` under `## Extra excludes` |
| Argue "it's a universal cache so I'll fix the skill for everyone" | Add to this agent's `Extra excludes` and move on. If it's truly universal, it's a design conversation for upstream — not a one-container patch |
| Run `sed -i` or redirect-write into a `scripts/*.py` file | Never. Those files are tagged read-only by convention. |

#### Why this matters

1. **Reproducibility.** Another agent re-installing from `backup.zip` would have the old blacklist; your patch is silently invisible outside this container.
2. **Upgrade safety.** Next skill update re-extracts the zip and clobbers your local mutations. You'd lose the fix and not know why.
3. **Shared-baseline trust.** The skill docs, error messages, and behaviors all assume `pack.py`'s blacklist matches what's documented. A locally-mutated pack.py makes debugging harder.

#### What belongs where

| Layer | What belongs here | Agent's relationship |
|---|---|---|
| **skill code** (`skills/backup/**`) | Noise that is **noise for EVERY agent by convention** (`logs/`, `__pycache__/`, `.npm-cache/`, ChromaDB-derived indexes, `.backup/.restore` scratch) | Read-only. Invoke as-is. |
| **`/data/workspace/config/backup_rules.md`** | Preferences **specific to this agent** — anything that varies between containers (`.local/`, `.cache/`, `sessions/`, `workspace/output/`, …) | Read + write freely. |

If you catch yourself about to edit a skill file, **stop and redirect the same change into `backup_rules.md`'s `Extra excludes` (or `Extra paths` for additions)**.

The first-time discussion flow (A.1.0 case B) is explicitly designed to catch user-specific exclusions up front so they land in the rules file from the start. If users keep coming back reporting unexpected items in backups, that's a signal to **improve B.2's proactive flagging** (e.g. add more name heuristics in the SKILL.md instructions to the agent) — not to patch the blacklist.

---

## Bundle layout (shared by both flows)

```
backup/
  manifest.json                         # bundle-internal self-description (v1.1)
                                        #   + contents.files[{path,size,sha256}]
                                        #   + contents.api[{path,size,sha256}]
                                        #   + exclusions[] (what got skipped and why)
  files/
    workspace/...                       # mirror of /data/workspace/ (minus skipped)
    data/...                            # mirror of /data/* non-workspace (minus skipped)
  api/
    profile.json                        ← agent_profile(action="get")
    settings.json                       ← user_settings(action="get")
    scheduled_tasks.json                ← scheduled_task list, normalized for register()
```

**What's IN by default**: everything under `/data/`, including `.env` secrets plaintext and `sessions/state.db` + WAL.

**What's OUT by default** (blacklist — see pack.py for exact list):

| Kind | Why skipped |
|---|---|
| `/data/logs/`, `*.log` files | logs, regenerate |
| `/data/memory/` (ChromaDB, FTS indexes, embedding cache) | fully derivable from `workspace/memory/**` |
| `/data/.npm-cache/` | cache |
| `/data/.bash_processes/`, `.startup-tasks/`, `hibernation_state.json` | transient, resets on container restart |
| `workspace/.backup/`, `workspace/.restore/` | our own scratch (self-loop guard; skipped even in `--mode full`) |
| `workspace/.active-upload.json`, `workspace/.restore.log` | transient flow markers |
| `__pycache__/`, `*.pyc` anywhere | Python compile caches |

Note `/data/workspace/config/backup_rules.md` (user's persistent preferences, see Flow A.1.0) **IS** included by default — it lives under `workspace/config/` like any other user file. Restoring a bundle restores the user's rules too, so their backup workflow stays consistent across restores.

`--mode full` disables all those skips (except the two self-loop items). Use it when you need a bit-for-bit dump, e.g. debugging or migrating to a bigger volume.

Integrity is layered:
- Storage side: `{backup_id}.manifest.json` has the whole-bundle sha256, returned as `X-Sha256` on `GET /backups/{id}`.
- Bundle side: `manifest.json` has per-file `{path, size, sha256}` under `contents.files` + `contents.api`. Restore rehashes every one before applying.

* **`.env` contains plaintext secrets** (API keys, tokens). The bundle is
  tenant-scoped — only the user's own JWT can read it from storage. But
  treat the bundle itself as sensitive: don't copy it outside storage, don't
  share `backup_id` across accounts. AEAD encryption at the client is a
  future opt-in (see design doc §11).

The **storage-side manifest** (`<backup_id>.manifest.json`, kept by the
server) is a separate file used for listing and quota accounting. Don't
confuse the two.

---

## Step 0 (BOTH FLOWS) — `/workspace/.restore.log` check

Before either flow does anything, inspect `/workspace/.restore.log`. This file exists iff a previous restore started applying sections and never finished (agent crash, container restart, user walked away). The agent is in a **half-restored state** and the right reaction differs by flow.

```bash
if [ -f /workspace/.restore.log ]; then
  cat /workspace/.restore.log
fi
```

Each line of the log is a JSON event:
```json
{"ts": "...", "backup_id": "bk_...", "section": "memory", "status": "ok"}
```

### If the log exists…

**Flow A (Create) → refuse:**
> 检测到上次 restore 未完成（`{backup_id}`，已应用 `{N}/{M}` section）。
> 现在备份会把这个半恢复状态存下来，请先 `/restore` 继续或放弃之前的恢复。

Do not proceed to Step A.1.

**Flow B (Restore) → ask the user:**
> 检测到上次 restore 未完成：`{backup_id}` 已应用 `{N}/{M}` section（{sections}）。
>
> 1. **继续恢复** — 从下一个 section 接着跑（推荐，若进度可信）
> 2. **放弃并重新开始** — 清除 `.restore.log`，重走 Step B.1
> 3. **取消** — 保持当前半恢复状态，以后再说

**Flow C (Delete) → proceed but warn:**
Deletion is orthogonal to a half-restore (deleting a backup doesn't touch
live agent state). You MAY continue to Flow C, but the first thing you
say to the user should be:
> 注意：上次 restore 未完成（`{backup_id}`）。删除备份不会影响当前半恢复状态，
> 但建议先 `/restore` 把状态理清楚。要继续删除吗？

If they want to proceed with delete, continue with Flow C below.

Never auto-pick. Never silently clear the log.

### Log-write contract (only written during Flow B)

During Flow B §4b, **append one line per section after it succeeds**:

```bash
echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"backup_id\":\"$BID\",\"section\":\"memory\",\"status\":\"ok\"}" \
  >> /workspace/.restore.log
```

On full success (all sections done + §4c cleanup), **delete** the file:
```bash
rm -f /workspace/.restore.log
```

Missing file = "no restore in progress". File present = "something was interrupted". The whole contract is just those two states.

---

## Flow A — Create a backup

Flow A has **four phases**. You MUST NOT skip from A.1 straight to A.3. The
user has to see the plan and approve the scope before any tar.gz is built.

### A.1 Inspect — load rules, gather API state, dry-run the pack plan

This phase produces the **plan** without building a bundle yet. Three sub-steps.

**A.1.0 Load (or bootstrap) user's backup rules file**

User's persistent preferences live at `/data/workspace/config/backup_rules.md`. It records their default mode, extra exclusions, extra paths, label template, and self-notes. This file is the glue between "pack.py stock defaults" and "what this specific user wants every time".

**Two cases:**

### Case A: the rules file ALREADY exists

Parse it (see format below) and continue to A.1.1. Zero friction.

### Case B: first-ever backup — discover, discuss, author

If the file is missing, **do NOT silently drop in a generic template.** Instead, scan the live `/data/` tree, present a tailored proposal, and build the rules file from the user's decisions.

**B.1** Run the classifier:

```bash
python3 skills/backup/scripts/propose_rules.py
```

The script walks `/data/workspace/` and `/data/` top-level entries, tags each with one of four categories, and emits JSON. **With the conservative default, all four categories matter for presentation but only `skip` changes behavior** (only `skip` items get dropped; `core` + `ask` + `unknown` all get included):

| Category | Default action | How to present |
|---|---|---|
| `core` | **include** | list under "✓ will be backed up" |
| `skip` | **skip** | list under "✗ will be skipped (logs + runtime caches)" |
| `ask`  | **include** | list under "✓ will be backed up" with ⚠ marker + a one-line note (lets user opt out if they want) |
| `unknown` | **include** | list under "✓ will be backed up" with a nudge ("not on my known list — tell me if you didn't mean to back this up") |

Each item carries `{name, size_bytes, file_count, category, reason}` so the presentation in B.2 can be concrete.

**B.2** Present the **conservative default**: back up everything except logs and runtime caches. Show the user both lists (what gets included, what gets skipped) so they have full visibility. **Then proactively point at specific items to exclude** before asking the open-ended "anything else?" question. Don't make the user spot the 420MB `.local/` themselves.

**Pre-presentation processing** (do this before rendering):

1. **Sort each section by size descending.** Biggest-first is more useful than alphabetical — `.user-packages/ 420 MB` at the top gets attention.

2. **Identify "likely-skip" candidates** using size + name heuristics, and surface them as `⚠` items with an explicit "consider excluding" note. Heuristics (apply to items the stock blacklist didn't already catch):

   | Signal | Criterion | Recommendation |
   |---|---|---|
   | Size ≥ 50 MB | Any item | "⚠ this is big — do you need the history, or can we skip?" |
   | Size ≥ 20 MB AND unrecognized | `unknown` category | "⚠ unknown + big — safest to skip unless you know what it is" |
   | Name matches `.cache*`, `*_cache*`, `*.tmp*`, `.tmp`, `.thumbnails`, `.pip*`, `.pnpm*`, `.yarn*` (case-insensitive, any depth in name) | Any size | "⚠ name suggests this is a cache; probably safe to skip" |
   | Name = `.local` | Any size | "⚠ can be anything — pipx installs, app data, pip-user. If you don't know what's here, probably safe to skip (setup.sh should reinstall binaries)" |
   | Name = `sessions` | Size ≥ 10 MB | "⚠ chat history is big — if you don't need old conversations, you can skip it" |

3. **Show the recommendations as an explicit pre-filled list**, not as per-item "should I skip this?" questions. The user can then confirm the list, remove some, or add more.

Below is a **Chinese-language example** — render the same structure in the user's conversation language. Keep the `✓` / `✗` / ⚠ markers (unambiguous symbols); translate the prose.

```
这是你第一次备份。默认策略：**除了日志和运行时缓存，其他全部带走**（最保守）。
下面是扫描结果（按大小倒序），我标了几个建议排除的：

✓ 会备份（core + ask + unknown 全都包含）：
  data/.user-packages/           420 MB   ⚠ 大（pip/npm --user 包）— 建议排除，setup.sh 能装回
  data/.local/                   66 MB    ⚠ 通常是 pipx / 应用 state — 建议排除（name 看着像 cache，不确定就别带）
  data/.cache/                   25 MB    ⚠ name 就是 cache — 建议排除
  data/sessions/                 5.1 MB           对话历史 + WAL
  data/scheduled_jobs.db         4 MB             任务执行历史
  workspace/output/              240 KB, 3 reports
  workspace/memory/              3.2 KB, 10 files
  data/tasks.json                12 KB            subagent 运行记录
  workspace/tasks/               12 KB, 5 jobs
  workspace/my-custom-dir/       12 KB            ⚠ 我没见过这个，你创的吗？
  data/preview_history.json      8 entries
  workspace/config/              2.1 KB           agent.yaml 等
  workspace/prompt/              1.2 KB           SOUL.md / USER.md
  workspace/skills/              (.skill-lock.json)
  workspace/setup.sh             412 B
  workspace/.env                 245 B    ⚠ 原文 secrets
  data/scheduled_jobs.json       5 entries
  data/previews.json             2 active
  data/some-mystery-file.dat     4 B              ⚠ 我没见过的文件

✗ 会跳过（日志和运行时缓存 — pack.py 内置黑名单）：
  data/logs/                     36 MB
  data/memory/                   10 MB    ChromaDB + FTS（从 workspace/memory 重建即可）
  data/.npm-cache/               2.4 MB   npm 缓存
  data/.bash_processes, .startup-tasks/, hibernation_state.json   (运行时瞬态)
  workspace/.backup, workspace/.restore                           (skill 自己的 scratch)

---
我的建议：把下面这几项也加进跳过（都是上面带 ⚠ 的大/cache 嫌疑项）：
  - data/.user-packages/   (420 MB, pip 包)
  - data/.local/           (66 MB, 通常是 pipx)
  - data/.cache/           (25 MB, name = cache)

这样备份会从 ~700 MB 降到 ~8 MB。

回答两件事就行：
1. 上面这 3 条排除建议，你同意几条？（"全部接受" / "只排除 .cache" / "都不排除，全要" / 自定义）
2. label 模板？（默认 "自动备份 {date}"）
```

**Handling "unknown" items**: the heuristic flags them but doesn't demand per-item answer — just surface them with one-line nudges. If the user doesn't mention them, they get backed up (conservative default).

**Why proactive suggestions, not blacklist changes?** The Skill vs rules boundary (Rule 4 above) — these items being big/cache-like is **this agent's workload**, not a universal truth. Another Starchild agent might have empty `.local/` and no `.cache/`. Keep the universal defaults narrow; push per-agent decisions into `backup_rules.md`.

**Why conservative in the rendering of recommendations?** Phrase them as "my suggestion" / "建议排除", not as mandates. If user says "no, keep .local", respect it. They might know something you don't (e.g. they manually pip-installed some binary not in setup.sh).


**B.3** Once you have the user's decisions, **compose `backup_rules.md`**. The file has two purposes:

1. **Parsed configuration** — five required headings the agent reads on subsequent backups
2. **Living record** — a human-readable snapshot of what was discussed, so three months from now the user can look at the file and remember WHY they made each choice

Compose it from:

- **`## Mode`** (parsed) = always `default` (the blacklist embedded in pack.py matches "logs + runtime caches" exactly)
- **`## Extra excludes`** (parsed) = paths the user asked to drop in B.2 Q1 (relative to `/data/`; may be empty)
- **`## Extra paths`** (parsed) = empty on first run (user didn't mention anything outside `/data/`)
- **`## Label template`** (parsed) = their answer to B.2 Q2, or the localized default
- **`## Notes`** (not parsed) = the discussion date + any context the user mentioned (why they keep certain things, reminders, preferences)
- **`## File inventory`** (not parsed, extra section) = a point-in-time snapshot from the `propose_rules.py` output, rendered as a decision table: what was on disk, what gets backed up, what gets skipped, and why

The inventory section is crucial. **Do not generate a rules file without it.** It's the difference between a useful lived-in document and an empty stub.

Write it to `/data/workspace/config/backup_rules.md`. Example below is in Chinese — **translate prose, comments, labels, the inventory narrative into the user's language; keep the parsed `##` headings in English verbatim**. Also render sizes/counts naturally in the user's language (e.g. "3.2 KB / 10 文件" / "10 ファイル" / "10 files"):

```markdown
# Backup rules — 你的备份偏好

`/backup` 执行时 agent 会先读这个文件应用设置。直接编辑保存生效。
想恢复默认？删掉这个文件，下次 `/backup` 会重建。

## Mode

```
default
```

## Extra excludes

```
# 你在首次讨论时决定不备份的路径，每行一个，相对 /data/。
# 当前你选了"全都要"，所以这里是空的。
# 以后想排除什么，直接在这里加，例如：
# workspace/output
# data/.user-packages
```

## Extra paths

```
# /data/ 外想额外打包的绝对路径。首次讨论时你没提。
# 示例：
# /home/myuser/some-config
```

## Label template

```
自动备份 {date}
```

## Notes

首次备份日期：2026-04-27
讨论时选择的策略：保守默认（除了日志和运行时缓存，其他全部打包）。
- my-custom-dir/ 是我自己创的笔记目录，一定要带上
- .user-packages 虽然 420MB 挺大，但我不确定 setup.sh 装得全，先留着
- 以后想瘦身再回来改

---

## File inventory (首次备份时的 /data/ 快照，2026-04-27)

这是**首次备份时**扫描到的 /data/ 内容和每项的处理方式。不是配置项——
agent 不会读这段。纯粹是给你自己看的"当时我是怎么想的"记录。

新增或改动目录后，这个表会过时——如果你想让 rules 始终反映最新结构，
请手动更新这段（或让 agent 帮你重新扫描）。

### workspace/
| 状态 | 路径 | 大小 | 备注 |
|---|---|---|---|
| ✓ | memory/ | 3.2 KB, 10 files | agent 记忆 |
| ✓ | prompt/ | 1.2 KB, 3 files | SOUL.md / USER.md / AGENTS.md |
| ✓ | config/ | 2.1 KB, 2 files | agent.yaml + backup_rules.md（就是这个文件） |
| ✓ | tasks/ | 12 KB, 5 jobs | 定时任务脚本 |
| ✓ | skills/ | — | .skill-lock.json（装的 skill 清单） |
| ✓ | setup.sh | 412 B | 启动钩子 |
| ✓ | .env | 245 B | ⚠ 原文 secrets (API keys) |
| ✓ | output/ | 240 KB, 3 reports | agent 生成的报告；保留 |
| ✓ | scripts/ | (空) | 将来可能用得到 |
| ✓ | my-custom-dir/ | 12 KB | 我的笔记目录 — 一定要带上 |

### data/ (non-workspace)
| 状态 | 路径 | 大小 | 备注 |
|---|---|---|---|
| ✓ | sessions/ | 5.1 MB | 对话历史（state.db + WAL） |
| ✓ | scheduled_jobs.json | 5 entries | 任务注册表 |
| ✓ | scheduled_jobs.db | 4 MB | 任务执行历史 |
| ✓ | preview_history.json | 8 entries | preview 服务历史 |
| ✓ | previews.json | 2 active | 活跃 preview |
| ✓ | tasks.json | 12 KB | subagent 运行记录 |
| ✓ | .user-packages/ | 420 MB | ⚠ 大；pip/npm --user 包 |
| ✓ | .local/ | 4.6 MB | pipx / 应用 state |
| ✓ | some-mystery-file.dat | 4 B | 不认识的文件；用户确认要留 |
| ✗ | logs/ | 36 MB | 日志（pack.py 自动跳过） |
| ✗ | memory/ | 10 MB | ChromaDB（可从 workspace/memory 重建，自动跳过） |
| ✗ | .npm-cache/ | 2.4 MB | npm 缓存（自动跳过） |
| ✗ | .bash_processes, .startup-tasks/, hibernation_state.json | — | 运行时瞬态（自动跳过） |
```

Tailor the example to the actual propose_rules.py output for this user — don't copy the example paths literally. Every ✓/✗ row should come from the JSON, with the correct size, category, and a short reason in the user's language.

After writing, tell the user: "我把规则写进了 `/data/workspace/config/backup_rules.md`，里面也记录了这次讨论的完整文件清单和每项的处理方式。以后想调整偏好直接编辑这个文件；如果增加了新的目录想让它反映出来，告诉我帮你重扫描就行。" Then continue to A.1.1.

### Fallback: "just use a generic template"

If the user says "don't ask me, just use the defaults" during B.2, skip the discussion and write the stock template instead:

```bash
python3 skills/backup/scripts/ensure_rules.py
# prints CREATED /data/workspace/config/backup_rules.md
```

The template `ensure_rules.py` writes is in **English** (neutral baseline). If the user's conversation language isn't English, immediately offer: "I wrote the rules file in English as a baseline — want me to translate the prose and comments into {user's language}? (Section headings stay in English either way; the parser needs them.)" If they accept, rewrite the file in their language using your native file-write tool. If they pass, continue.

### Format spec (for Case A parsing)

The markdown has five **required** fixed headings; extract values by section:

| Heading | Value | Becomes |
|---|---|---|
| `## Mode` | single word (`default` or `full`) | `--mode` |
| `## Extra excludes` | fenced code block; one path per line; `#` comments ignored | zero or more `--extra-exclude` |
| `## Extra paths` | fenced code block; one absolute path per line; `#` comments ignored | zero or more `--extra-path` |
| `## Label template` | fenced code block; single line with optional `{date}` placeholder | default `--label` (replace `{date}` with today's UTC date `YYYY-MM-DD`) |
| `## Notes` | free-form text | **ignore** (user-private notes, not instructions) |

Additional headings like `## File inventory` (common on rules files composed via B.3) are **also ignored**. Only the five above are parsed. This lets users add sections freely without breaking the parser.

**Parsing rules**:
- Ignore markdown around the headings (intro paragraphs, HTML comments, horizontal rules).
- Trim whitespace on each extracted line.
- Skip lines starting with `#` inside fenced code blocks — those are user-commented examples.
- If a section is absent or all its lines are commented out, treat it as empty.
- If the file is unparseable (e.g. user broke the headings), report to the user `无法解析 backup_rules.md，请检查格式或删除文件让我重建。` (in user's language) and stop.

Values from this file become the **starting point** for the plan. The user can still override any of them in A.1.3's conversation.


**A.1.1 API state read** (agent tool calls) + write to a per-run workdir:

```
agent_profile(action="get")    → 4 fields: {agentName, agentVibe, agentEmoji, agentCreature}
user_settings(action="get")    → pick {language, timezone, what_to_call, agent_*}
scheduled_task(action="list")  → normalize each task to {title, schedule, description, channels}
                                 (strip runtime fields: last_run, status, error_log)
```

Allocate one workdir per backup attempt (mktemp gives process-unique path,
so concurrent `/backup` calls don't collide):

```bash
WORK=$(mktemp -d /tmp/backup-XXXXXX)
mkdir -p "$WORK/api"
# write the three JSONs to $WORK/api/:
#   $WORK/api/profile.json
#   $WORK/api/settings.json
#   $WORK/api/scheduled_tasks.json
```

Remember `$WORK` — every subsequent step uses it.

**A.1.2 Dry-run pack to preview the plan** (with rules applied):

Build the `pack.py` command from the rules you loaded in A.1.0. Example — if
the rules file has `Mode: default`, `Extra excludes: [workspace/output, sessions]`,
`Label template: 自动备份 {date}`:

```bash
python3 skills/backup/scripts/pack.py \
  --api-dir "$WORK/api" --out "$WORK/bundle.tar.gz" \
  --mode default \
  --extra-exclude workspace/output \
  --extra-exclude sessions \
  --label "自动备份 2026-04-27" \
  --dry-run
```

The script walks `/data/`, applies the mode's blacklist + your `--extra-exclude` list, and prints a JSON plan to stdout with `items[]` and their `status: ok | absent | excluded_*`. This is zero-cost: no files copied, no network I/O.

### A.1.3 STOP — show the plan, wait for user

Render the pack plan as a table to the user. Keep it compact, and **surface any defaults you pulled from `backup_rules.md`** so they know what's being carried over:

```
打包清单（mode=default，等待你确认）:

📋 从 backup_rules.md 读取的默认：
   label = "自动备份 2026-04-27"
   额外 exclude: workspace/output, sessions
   额外 include: (无)

✓ workspace/memory/           3.2 KB (MEMORY.md + daily/ + topics/)
✓ workspace/prompt/           850 B  (USER.md + SOUL.md)
✓ workspace/config/           2.1 KB (agent.yaml, backup_rules.md)
✓ workspace/tasks/            12 KB  (5 jobs, run.py + data)
✓ workspace/skills/.skill-lock.json   11 installed skills
✓ workspace/setup.sh          412 B
✓ workspace/.env              3 vars   ⚠️ 原文 secrets
✓ data/scheduled_jobs.json    5 entries
✓ data/scheduled_jobs.db      4 MB   (执行历史)
✓ data/preview_history.json   8 entries
✓ data/previews.json          2 active
✓ data/tasks.json             12 KB
✓ data/.user-packages/        420 MB ⚠️ 大

跳过（默认 blacklist + rules 新增）:
✗ data/logs/                  日志
✗ data/memory/                ChromaDB + FTS 索引（可从 workspace/memory 重建）
✗ data/.npm-cache/            npm 缓存
✗ data/.bash_processes, .startup-tasks/, hibernation_state.json  (运行时状态)
✗ workspace/output/           ← rules.md 里 extra-exclude
✗ data/sessions/              ← rules.md 里 extra-exclude
✗ workspace/.backup, workspace/.restore  (本 skill 自身 scratch，self-loop 保护)

---
请回答（按你 rules.md 里的默认做就直接说 "ok"）:
1. 标签 (label)?  (当前默认 "自动备份 2026-04-27")
2. mode?  (当前默认 default)
3. 要调整的 exclude / include?  (当前从 rules.md 读了 2 项)

```

**关于偏好和本次选择的关系**：
- `backup_rules.md` 是**持久偏好**——每次 `/backup` 的出发点。
- A.1.3 的回答是**本次一次性覆盖**——只影响当前备份，不动 rules 文件。
- 用户想永久改变规则？告诉他去编辑 `backup_rules.md`，不是在对话里每次重说。

Do not proceed to A.2 until the user confirms. "就按 rules.md 来" is a valid answer (means: use all rules-file defaults as-is).


### A.2 Pack the bundle

Once the user confirms, invoke the deterministic packer against the
same `$WORK` dir you created in A.1.1:

```bash
python3 skills/backup/scripts/pack.py \
  --label "升级前" \
  --api-dir "$WORK/api" \
  --mode default \
  --out "$WORK/bundle.tar.gz"
```

Optional flags for power-user overrides (typically empty):
- `--mode full` — bypass the blacklist, pack everything (except `workspace/.backup`/`.restore` self-loops)
- `--extra-exclude <rel>` — skip one more path, relative to `/data/` (e.g. `sessions` or `workspace/output`). Repeat for multiple.
- `--extra-path <abs>` — include one more path outside `/data/`. Repeat for multiple.

The script:
1. Walks `/data/workspace/*` and `/data/*`, applies the mode's skip rules + user overrides, copies everything else into `backup/files/workspace/**` and `backup/files/data/**`. `__pycache__` and `*.pyc` are pruned universally.
2. Reads `$WORK/api/*.json` into `backup/api/**`.
3. Computes sha256 of every bundled file and writes `backup/manifest.json` v1.1 with `{version, source, mode, created_at, label, sections, contents.files[{path,size,sha256}], contents.api[{path,size,sha256}], exclusions[], plan_summary}`.
4. `tar czf` the whole thing, prints `{bundle_path, size_bytes, manifest}` as JSON.

The `exclusions[]` array in the manifest records every path that was skipped and the reason (`excluded_self_loop`, `excluded_user_rule`, `excluded_default_rule`). Restore-time readers / auditors can use it to explain what the bundle does and doesn't contain.

### A.3 Upload

```bash
python3 skills/backup/scripts/upload.py \
  "$WORK/bundle.tar.gz" \
  --label "升级前"
```

Bundles < 10 MB go through one-shot `POST /backups`. Bundles ≥ 10 MB go
through the resumable protocol (reserve → 10 MB chunks → auto-finalize).
In both cases the script streams from disk — server and client RAM stay
flat regardless of bundle size.

If the agent container restarts mid-upload and the state file
`/workspace/.active-upload.json` is intact, the next invocation resumes at
the server's current offset automatically. Sessions expire after 1 hour
of inactivity. (Note: `$WORK` itself lives in `/tmp/` and is wiped on
container restart, so a mid-upload restart means the bundle is gone and
resume will fail gracefully — the agent should repack and retry fresh.)

### A.4 Handle the response

Exit codes (non-zero is always a real failure — branch on stdout content, not on exit code alone):

| Exit | Stdout signal | Meaning | What to do |
|------|---------------|---------|------------|
| `0`  | JSON with `"backup_id"` | Uploaded. Also has `size_bytes`, `sha256`, `remaining_slots`. | Tell the user it's done; mention remaining slots. |
| `0`  | JSON with `"error": "quota_exceeded"` + `"current": [...]` | Quota full (5/5). | **Ask the user which to replace** — never pick for them. Then re-run with `--replace <backup_id>`. |
| `1`  | `ERROR: ...` on stderr | Network / auth / size / protocol failure. | Surface it; retry is usually safe (the script already does one jittered retry on transport errors). |

Example replace:
```bash
python3 skills/backup/scripts/upload.py \
  "$WORK/bundle.tar.gz" --label "升级前" \
  --replace bk_20260320_091500_a7f3
```

### A.5 Clean up

```bash
rm -rf "$WORK"
```

One recursive delete removes `api/` scratch, `bundle.tar.gz`, and any
staging artefacts — all of this run's intermediate state lives under the
single `$WORK` dir by convention. (If the agent lost track of `$WORK`,
everything is under `/tmp/backup-*/` and container restart will wipe it
anyway.)

---

## Flow B — Restore from a backup

```
   ┌──────────────────────────────────────────────────────────────┐
   │ 0. CHECK      → /workspace/.restore.log (see Step 0 above)   │
   │ 1. LIST       → show characteristics of every backup         │
   │ 2. PICK       → user chooses one by number                   │
   │ 3. DOWNLOAD   → pull into the agent container, verify sha256 │
   │ 4. RESTORE    → apply each component to its original target  │
   └──────────────────────────────────────────────────────────────┘
```

**Invariants (non-negotiable):**
- No auto-pick (user picks the backup by number).
- No auto-apply (every section confirmed by user before tool call).
- Every API section writes a `.restore.log` line on success.

### Where each component goes

| Kind | Bundle path | Original target | How to restore |
|---|---|---|---|
| Agent memory (main) | `files/workspace/memory/MEMORY.md` | `/data/workspace/memory/MEMORY.md` | filesystem copy (via `restore.py`) |
| Daily memory | `files/workspace/memory/daily/*.md` | `/data/workspace/memory/daily/` | filesystem copy |
| Topic memory | `files/workspace/memory/topics/{slug}/` | `/data/workspace/memory/topics/` | filesystem copy |
| User profile + memory | `files/workspace/prompt/USER.md` | `/data/workspace/prompt/USER.md` | filesystem copy |
| SOUL.md | `files/workspace/prompt/SOUL.md` | `/data/workspace/prompt/SOUL.md` | filesystem copy |
| Agent-level config | `files/workspace/config/agent.yaml` | `/data/workspace/config/agent.yaml` | filesystem copy |
| Custom LLM routes | `files/workspace/config/custom_models.yaml` | `/data/workspace/config/custom_models.yaml` | filesystem copy |
| Task scripts | `files/workspace/tasks/{job_id}/*` | `/data/workspace/tasks/{job_id}/` | filesystem copy |
| Startup hook | `files/workspace/setup.sh` | `/data/workspace/setup.sh` | filesystem copy |
| Skill registry | `files/workspace/skills/.skill-lock.json` | `/data/workspace/skills/.skill-lock.json` | filesystem copy + `npx skills install` |
| Secrets | `files/workspace/.env` | `/data/workspace/.env` | filesystem copy (plaintext) |
| Scheduler registry | `files/data/scheduled_jobs.json` | `/data/scheduled_jobs.json` | filesystem copy (⚠ see B.4b) |
| Preview state | `files/data/preview*.json` | `/data/preview*.json` | filesystem copy |
| Opt-in large files | `files/data/sessions/state.db` etc. | `/data/**` | filesystem copy (user-picked at backup time) |
| Profile | `api/profile.json` | `agent_profile` API | `agent_profile(action="update", ...)` |
| User settings | `api/settings.json` | `user_settings` API | `user_settings(action="update", ...)` |
| Scheduled tasks | `api/scheduled_tasks.json` | `scheduled_task` API | `register` + **ensure** `run.py` from files/ + `activate` |

`restore.py` automates **all file rows** in one pass (both `files/workspace/**` and `files/data/**`). The three `api/*.json` rows are applied by **you** using Starchild native tools, one section at a time with user confirmation. This asymmetry is intentional — file overwrites are reversible from a diff; API state writes are not, so they deserve a heavier prompt.

### B.1 List available backups

```bash
python3 skills/backup/scripts/list.py
```

Prints a numbered menu:
```
您的备份（3 / 5，按时间倒序）：

[1] bk_20260424_143000_a7f3
    标签: 升级前
    时间: 2026-04-24 14:30 UTC  (1 天前)
    大小: 12.3 MB
    内容: memory, tasks, soul, files

[2] bk_20260418_091500_b2c1
    ...
```

Surface the menu to the user verbatim (or reformat only if you keep every field). Label / date / age / size / sections are the backup's "characteristics" and the user picks based on them.

Exit codes:
- `0` → request succeeded. stdout is either the pick menu or `"（无备份）"`.
  - If the user has zero backups, tell them to run `/backup` first — no `/restore` is possible yet.
  - Otherwise ask the user to pick a number.
- `1` → network/auth failure. Surface stderr.

### B.2 User picks one

Ask explicitly:
> "请选择要恢复的备份编号（1–N），或输入 `cancel` 取消。"

Do not pick for them. Do not default to `[1]`. If they reply `cancel` or anything ambiguous, stop and ask again. Map their number back to the `backup_id` from the list output, then continue.

### B.3 Download into the agent container

```bash
python3 skills/backup/scripts/download.py <backup_id>
```

`download.py`:
1. Streams `GET /backups/{backup_id}` from `sc-agent-backup.internal` using `CONTAINER_JWT` (client memory stays bounded).
2. Verifies **whole-bundle sha256** against the storage's `X-Sha256` header while streaming. Mismatch → exit 1, delete tmp.
3. Validates the tar (rejects absolute paths or `..` members).
4. Extracts into **`/data/workspace/.restore/{backup_id}/`** — hidden dot-dir, per-backup_id isolated so two concurrent restores of different ids don't collide, and retrying the same id just re-extracts in place.
5. Reads `manifest.json` and verifies **every listed file's sha256 + size** (pre-apply integrity, defense-in-depth vs the whole-bundle hash). Mismatch → list bad/missing/extra files and exit 1.
6. Prints a human summary grouped by section (workspace/memory, workspace/prompt, …, api).

Show the summary to the user. This is the **deep characteristics** view — once the bundle is on disk and integrity-verified, you know exactly what's inside, not just the storage-side metadata from Step B.1.

### B.4 Restore to original paths

#### B.4a File-based components (all of `files/**`) — automated

Always start with a dry-run:

```bash
python3 skills/backup/scripts/restore.py --backup-id <backup_id>
```

The script first **re-verifies the per-file manifest hashes** (second pass after download.py's check — time passed between download and apply; we catch any tampering that happened in between), then walks `files/workspace/**` → `/data/workspace/**` and `files/data/**` → `/data/**`. Plan output:

```
Pre-apply integrity check: OK (18 files verified)
Restore plan (workspace=/data/workspace, data=/data)
  new       : 12 file(s)
  unchanged : 3 file(s) (will skip)
  modified  : 2 file(s) (will overwrite with --force)

NEW:
  + [workspace] /data/workspace/tasks/btc-alert/run.py  (1834 B)
  + [workspace] /data/workspace/.env                    (245 B)
  + [data]      /data/scheduled_jobs.json               (412 B)

MODIFIED (existing content differs):
  ~ [workspace] /data/workspace/prompt/SOUL.md
    --- /data/workspace/prompt/SOUL.md
    +++ .../files/workspace/prompt/SOUL.md
    @@ -3,2 +3,3 @@
     - Be concise
    +- Be opinionated, back with data
```

If the pre-apply hash check fails (`ERROR: pre-apply integrity check FAILED`), **do not retry with `--skip-verify`**. Delete `/data/workspace/.restore/{backup_id}/`, re-run `download.py`, and try again. If fresh download also fails, the bundle on storage is corrupt — use Flow C to delete it.

Walk the user through the diff for each modified file. Only after they approve:

```bash
# new files only (safe, no overwrites)
python3 skills/backup/scripts/restore.py --backup-id <backup_id> --apply

# new files AND overwrite modified files (user must have approved each)
python3 skills/backup/scripts/restore.py --backup-id <backup_id> --apply --force
```

If the user wants to keep *some* local changes, manually copy only the subset they approve and skip `--force`.

#### B.4b API-based components — per-section, per-user-confirmation

Read each file from `/data/workspace/.restore/{backup_id}/api/` and apply via native tools. **Confirm each section with the user before calling the API.** Order matters — restore settings first because timezone/language affect formatting downstream.

**After each section succeeds**, append a line to `/workspace/.restore.log` (see Step 0).

```
.restore/{backup_id}/api/settings.json        ──▶  user_settings(action="update", settings=...)
.restore/{backup_id}/api/profile.json         ──▶  agent_profile(action="update", profile=...)
.restore/{backup_id}/api/scheduled_tasks.json ──▶  for each task:
                                                     scheduled_task(action="register", ...)
                                                     (run.py already restored via B.4a)
                                                     scheduled_task(action="activate", job_id=...)
```

- **Memory is NOT re-applied via the API.** The real source of truth is `files/workspace/memory/**` (MEMORY.md, daily/, topics/) — already copied by B.4a. Calling `memory(action="add")` for each entry would duplicate whatever's already in those files.
- **Skip existing tasks.** Call `scheduled_task(action="list")` first; skip any task with a matching title.
- **scheduled_jobs.json reconciliation.** B.4a puts the old registry on disk. When the agent calls `scheduled_task(action="register")` for tasks from `api/scheduled_tasks.json`, the scheduler deduplicates by title. If anything in the JSON doesn't match a live task, it's orphan — safe to leave alone.

#### B.4c Cleanup

```bash
rm -rf /data/workspace/.restore/{backup_id}/
rm -f /workspace/.restore.log
```

Both deletions matter. The per-backup_id extract dir is no longer needed; the restore log signals that everything applied successfully and future sessions don't need to prompt about it.

---

## Flow C — Delete a backup

Deletion is **permanent** — the storage `rm`s both `{id}.tar.gz` and `{id}.manifest.json` (see storage §4.5). There is no undo. That's why Flow C is gated behind **two distinct user confirmations** plus a script-level tripwire.

```
   ┌───────────────────────────────────────────────────────────────┐
   │ 0. CHECK      → /workspace/.restore.log (warn, then proceed)  │
   │ 1. LIST       → reuse list.py, show menu                      │
   │ 2. PICK       → user picks the one to delete                  │
   │ 3. CONFIRM #1 → show metadata, require "yes" / "delete"       │
   │ 4. CONFIRM #2 → user types the full backup_id verbatim        │
   │ 5. EXECUTE    → delete.py {id} --confirm {id}                 │
   │ 6. REPORT     → show what got deleted                         │
   └───────────────────────────────────────────────────────────────┘
```

**Invariants (non-negotiable):**
- No auto-pick (user picks by number from C.1's menu).
- **Two confirmations**, not one. Confirm #1 is a yes/no on the picked item. Confirm #2 is the user retyping the full `backup_id` — this protects against them nodding "yes" to the wrong pick.
- If Confirm #2's typed string differs from the target `backup_id` by even a single character, **abort**. Don't auto-correct.
- Never call `delete.py` before both confirms pass.

### C.1 List

```bash
python3 skills/backup/scripts/list.py
```

Same output as Flow B.1. Surface to the user verbatim. If the list is empty (stdout `"（无备份）"`), there's nothing to delete — stop and say so.

### C.2 User picks

Ask explicitly:
> "请选择要**删除**的备份编号（1–N），或输入 `cancel` 取消。"

Do not pick for them. Map their number back to `backup_id` from the list output.

### C.3 Confirm #1 — show the target, ask yes/no

Render the full metadata of the chosen backup. The example below is in Chinese — **translate the prose to the user's language**; structural labels like `backup_id`, `label`, `created`, `size`, `sections` stay verbatim:

```
即将删除：
  backup_id : bk_20260424_143000_a7f3
  label     : 升级前
  created   : 2026-04-24 14:30 UTC  (1 天前)
  size      : 12.3 MB
  sections  : memory, tasks, soul, files

⚠ 删除后**无法恢复**。服务端会同时清除 bundle 和 manifest，
  下次 list 就看不到了。

继续删除吗？ (yes / no)
```

Acceptable affirmative inputs (in any language): "yes", "y", "delete", "confirm", plus the equivalent words in the user's language (e.g., Chinese `删除` / `确认`, Japanese `はい` / `削除`, Spanish `sí`, etc.). Anything else — including "maybe", "sure?", silence, or an unrelated message — **abort** with a language-appropriate "cancelled" message.

### C.4 Confirm #2 — user types the full backup_id

Prompt the user to retype the backup_id verbatim. Translate the prose, keep the id literal:

```
最后一步确认：请把 backup_id 完整输入以确认删除

  bk_20260424_143000_a7f3

输入：
```

Wait for the user's next message. Trim surrounding whitespace only. Compare byte-for-byte:

- Exact match → proceed to C.5.
- Different by any character (typo, truncation, wrong id pasted) → **abort** with "输入的 ID 与目标不匹配，取消删除"。Do NOT attempt to guess what they meant.
- User wrote something else entirely (e.g. "yes", "confirm") → abort. Flow C requires the literal id string, not another "yes".

This second confirm exists specifically to catch: "I said yes but I actually wanted to delete a different one" and "I scroll-clicked the wrong number in C.2".

### C.5 Execute

```bash
python3 skills/backup/scripts/delete.py \
  bk_20260424_143000_a7f3 \
  --confirm bk_20260424_143000_a7f3
```

Both arguments MUST be the same string — the script's `--confirm` tripwire exits 2 on mismatch. This prevents a future agent refactor from accidentally calling `delete.py` without the user double-confirm.

### C.6 Report

The script prints a JSON object to stdout on success:

```json
{
  "deleted_backup_id": "bk_20260424_143000_a7f3",
  "user_label": "升级前",
  "created_at": 1714000000,
  "size_bytes": 12345678,
  "sections": ["memory", "tasks", "soul", "files"]
}
```

Tell the user:
> 已删除 `bk_20260424_143000_a7f3`（label: "升级前", 12.3 MB）。剩余 {N}/5 份备份。

Exit codes:

| Exit | Meaning | What to do |
|---|---|---|
| `0`  | Deleted. stdout has the metadata. | Confirm to user, mention remaining slots. |
| `1`  | Network / auth / 404 / "vanished between list and delete". | Surface stderr; re-list to see current state. |
| `2`  | `--confirm` mismatch tripwire — should never happen if you followed Flow C. | Do not retry with auto-filled --confirm. Go back to C.4. |

---

## Example walkthrough (restore)

```
User: /restore

Agent: (Step 0: /workspace/.restore.log missing → proceed)
       (runs list.py, shows the menu)
       您的备份（3 / 5）：
       [1] bk_20260424_...  标签: 升级前
       [2] bk_20260418_...  标签: 周备份
       [3] bk_20260410_...  标签: (无)
       请选择编号。

User: 1

Agent: (runs download.py bk_20260424_143000_a7f3)
       Downloaded 12.3 MB, sha256 verified.
       Bundle contents:
         agent memory : 42 entries
         user memory  : 18 entries
         identity     : name, vibe, emoji
         soul.md      : 23 lines
         user settings: name, timezone, language
         tasks        : 3 tasks
         files        : 7 files

       (runs restore.py dry-run)
       Restore plan:
         new       : 4 file(s)
         unchanged : 1 file(s)
         modified  : 2 file(s)  ← prompt/SOUL.md, ...

       以下文件将被覆盖：
         ~ prompt/SOUL.md
           [diff]
       是否覆盖？ (yes / no / only new)

User: only new

Agent: (runs restore.py --apply without --force)
       Applied: wrote=4 skipped_modified=2 errors=0
       API state to restore next: settings, profile, 42+18 memory, 3 tasks.
       是否先恢复 settings？ (yes / skip)

... (continues per-section, each appending to /workspace/.restore.log) ...

Agent: rm -rf /data/workspace/.restore/bk_20260424_143000_a7f3/  ✓
       rm -f /workspace/.restore.log    ✓
       Restore complete.
```

---

## Guarantees

- **Tenant isolation**: both flows derive `user_id` from the `CONTAINER_JWT`. Storage paths are `/data/backups/{user_id}/...` and `/data/sessions/{user_id}/...`, structurally unable to reach another user's namespace.
- **Bundle confidentiality**: bundles contain `.env` plaintext (by design, so restore can rebuild third-party integrations without making the user remember every API key). Only the JWT's own `userInfoID` can download a bundle — no cross-tenant read, no public URL. A stolen `CONTAINER_JWT`, however, would expose the secrets; treat bundle files moved outside storage as sensitive.
- **Network**: scripts only talk to `http://sc-agent-backup.internal:8080`. The storage itself rejects any non-`fdaa::/16` peer, so a misconfigured URL cannot leak to the public internet.
- **Atomicity (upload)**: `--replace` swaps via POSIX rename. A crash mid-write leaves the old backup intact and a harmless `.tmp` file the storage reaps after 1 hour.
- **Resumability (upload)**: bundles ≥ 10 MB use chunked upload; an agent restart can resume at the server's current offset via `/workspace/.active-upload.json`. Sessions expire after 1 h idle.
- **Sha256 end-to-end, two layers**: (1) server computes whole-bundle sha256 on upload; client verifies it on download via `X-Sha256`. (2) pack.py writes per-file sha256 into `manifest.contents`; download.py and restore.py both rehash every listed file, so corruption introduced anywhere along tar → disk → extract → sit-on-disk → apply gets caught before any write to live workspace/data.
- **Path safety (restore)**: `download.py` rejects tar members with absolute paths or `..`; `restore.py` only writes under `/data/workspace/` (or `WORKSPACE` env var).
- **Overwrite protection**: `restore.py` defaults to dry-run, refuses to overwrite modified files without `--force`.
- **Ask-don't-decide**: quota full → user picks which to replace; restore plan → user approves each section; half-restore on entry → user chooses continue / abandon / cancel.

---

## Don'ts

- ❌ **Don't edit any file under `skills/backup/`** — see Rule 4. Backup behavior tweaks go in `/data/workspace/config/backup_rules.md`, never in `pack.py` / `propose_rules.py` / `SKILL.md` / any script. If you catch yourself about to invoke `Edit` / `Write` / `sed` on a skill file, stop.
- ❌ Don't re-pack and re-upload in the same turn without user approval.
- ❌ Don't skip A.1.3 — the user has to see the plan and confirm before pack.
- ❌ Don't hit the public hostname. Everything goes through `.internal`.
- ❌ Don't back up a half-restored agent (Step 0 blocks this).
- ❌ Don't auto-pick which backup to replace, restore, or delete.
- ❌ Don't auto-apply API sections on restore — every one needs a user "yes".
- ❌ Don't skip either of Flow C's two confirmations. **Two separate turns**, not one combined "yes and I confirm id=X" — the whole point is to catch wrong-pick + wrong-intent separately.
- ❌ Don't auto-fill `--confirm` from the target `backup_id` without running the user through C.3 and C.4 first. The tripwire is there to catch exactly that shortcut.
- ❌ Don't `rm -f /workspace/.restore.log` without the user's explicit "abandon" / normal completion. The file is a safety marker.
- ⚠️ **The bundle includes `.env` plaintext.** Bundles are tenant-scoped in
  storage (only the user's own JWT can download), but a bundle file pulled
  out of storage is still plaintext secrets. Don't copy `backup_id` /
  bundle file to other accounts, other projects, or public channels. If
  you need zero-knowledge storage, use client-side AEAD (future work).

---

## Error handling

| Symptom | Likely cause | Fix |
|---|---|---|
| `upload.py` exit 0, stdout has `"error": "quota_exceeded"` | Quota full (5/5) | Ask user to pick one to replace; re-run with `--replace` |
| `ensure_rules.py` exit 1, "could not write" | `/data/workspace/config/` not writable | Unusual — likely permission / disk full. Don't block the backup; continue with stock defaults and tell user the rules file couldn't be created |
| `propose_rules.py` exit 1, "workspace or data dir does not exist" | Running outside a Starchild container / wrong WORKSPACE_DIR | Don't proceed to backup — the filesystem shape is wrong. Surface the error |
| `backup_rules.md` unparseable (heading renamed, broken code block) | User mangled the file | Don't guess. Surface the parse issue to the user and offer to `mv` the bad file aside and regenerate the template |
| `upload.py` exit 1, "cannot reach backup storage" | 6PN / DNS blip | Retry (script already does one backoff retry); if still failing, relaunch container |
| `upload.py` exit 1, "unauthorized" | JWT expired or wrong key | Container JWT issue — relaunch the machine |
| `upload.py` exit 1, "too large" | Bundle > 500 MB | Trim `files/` and repack |
| `upload.py`: "session expired on server mid-transfer" | Idle > 1 h during chunked upload | Just run the script again (start over) |
| `list.py` exit 0, stdout `"（无备份）"` | User has no backups yet | Tell them to run `/backup` first |
| `list.py` exit 1 | Network / auth / non-JSON reply | Surface stderr; relaunch if JWT expired |
| `download.py`: 404 | backup_id typo, or cross-tenant (storage replies same 404) | Re-list, pick again |
| `download.py`: whole-bundle sha256 mismatch | Transport corruption, or storage-side disk bit-rot | Retry download once; if still failing the server copy is bad — use Flow C to delete the corrupt backup |
| `download.py`: per-file contents verification failed | Tar corruption, or bundle was produced by a buggy packer | List the specific bad/missing/extra files. Same remediation: re-download, then delete if persistent |
| `restore.py`: pre-apply integrity check FAILED | Extract dir was modified after download (edit, cp over, etc.) | Delete `/data/workspace/.restore/{backup_id}/`, re-download, retry. Don't use `--skip-verify` outside of debugging |
| `download.py`: 403 | Not running on Fly 6PN | Restore must happen inside the Starchild Fly machine |
| `restore.py`: ERROR cannot write | Permission / disk full | Investigate; don't force |
| `restore.py`: skipped_modified > 0 | Local changes differ from backup | Expected. Show each diff and let user decide per file |
| `delete.py` exit 2 | `--confirm` didn't match `backup_id` | Agent skipped C.4 or auto-filled --confirm. Go back to C.4 and get the user to retype the id literally |
| `delete.py` exit 1, "backup not found" | Already deleted, or cross-tenant 404 | Re-list via `list.py`; the backup is already gone |
| `delete.py` exit 1, "vanished between list and delete" | Rare race — another session deleted the same id first | Re-list to confirm current state; the user's target is gone either way |
| `delete.py` exit 1, unauthorized / forbidden | JWT expired / not on 6PN | Same remediation as upload/download variants above |
