#!/usr/bin/env python3
"""Ensure /data/workspace/config/backup_rules.md exists. Idempotent.

On first run this writes a default template; on subsequent runs it does
nothing (user's edited version is preserved). Prints one line to stdout
so the agent can confirm which branch fired:

    CREATED /data/workspace/config/backup_rules.md
    EXISTS  /data/workspace/config/backup_rules.md

Exit codes:
    0   ok (created, or already existed)
    1   filesystem error (permission, disk full, etc.)

The default template covers every field pack.py can read from rules (mode,
extra excludes, extra paths, label template, notes). All sections are
present-but-inert (comment-only) so the file's mere existence doesn't
change default behavior — user must edit to activate anything.

Language: the template body is in English as a neutral baseline. The
SKILL.md Flow A.1.0 tells the agent to offer localizing it to the user's
conversation language after CREATE. Section headings stay in English in all
cases because the rules parser keys off them.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RULES_PATH = Path(os.environ.get(
    "BACKUP_RULES_PATH",
    "/data/workspace/config/backup_rules.md",
))

TEMPLATE = """\
# Backup rules — your backup preferences

When you run `/backup`, the agent reads this file first and applies whatever
you set here to the pack step. Edit it anytime; changes take effect on the
next backup. To reset everything to defaults, delete this file — the agent
will rebuild it on the next run.

> **Language note.** The section headings (`## Mode`, `## Extra excludes`,
> `## Extra paths`, `## Label template`, `## Notes`) must stay in English —
> the agent's parser depends on them. Everything else (intro prose, comments
> inside code blocks, the label template, your notes) can be in any language
> you prefer. Ask the agent to localize this file to your language if you'd
> rather not read English.

---

## Mode

The pack mode applied every time, unless you override in-conversation.

```
default
```

Valid values:
- `default` — skip logs / caches / ChromaDB / runtime transients / skill scratch (recommended)
- `full`    — include everything except this skill's own scratch (`.backup` / `.restore`)

---

## Extra excludes

Paths to skip on top of the default blacklist. One per line, **relative to
`/data/`**. Lines starting with `#` are comments and are ignored.

```
# Examples (remove the leading # to activate):
# workspace/output
# data/.user-packages
```

---

## Extra paths

Additional absolute paths to include from **outside** `/data/`. One per line.

```
# Example:
# /home/myuser/some-config
```

---

## Label template

Default label for each backup. `{date}` is replaced with today's UTC date
(YYYY-MM-DD). A label you provide in-conversation overrides this template.

```
auto-backup {date}
```

---

## Notes

Free-form space for your own reminders. The agent reads this section but
treats it as informational only — it won't execute anything you write here.

Example uses:
- "Do a `full` mode backup every Sunday."
- "If I add a new OPENAI key, test a backup afterward to make sure it picked up."
- "Last data loss happened because I forgot `output/` — don't skip it again."
"""


def main() -> None:
    if RULES_PATH.exists():
        print(f"EXISTS  {RULES_PATH}")
        return

    try:
        RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
        RULES_PATH.write_text(TEMPLATE, encoding="utf-8")
    except OSError as e:
        print(f"ERROR: could not write {RULES_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"CREATED {RULES_PATH}")


if __name__ == "__main__":
    main()
