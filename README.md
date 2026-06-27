# Starchild Official Skills

Official skills maintained by the Starchild team. Installed via [`npx skills`](https://github.com/vercel-labs/skills).

> **Building a new skill?** See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide — directory structure, `SKILL.md` frontmatter, `exports.py` patterns, function design best practices, logo specs, and a publishing checklist.

## Install a Skill

```bash
npx skills add Starchild-ai-agent/official-skills --skill hyperliquid
```

Or within a Starchild agent conversation:

```
search_skills(query="hyperliquid")    # searches + auto-installs
```

## Repository Structure

```
official-skills/
├── skills.json              ← auto-generated index (do not edit manually)
├── .github/workflows/
│   └── build-index.yml      ← CI: validates + rebuilds skills.json on push
├── hyperliquid/
│   └── SKILL.md
├── birdeye/
│   ├── SKILL.md
│   ├── token.py             ← tool scripts (optional)
│   └── templates/
└── ...
```

Each skill lives in its own top-level directory. The only required file is `SKILL.md`.

## SKILL.md Format

Every `SKILL.md` must have YAML frontmatter with three required fields:

```yaml
---
name: my-skill
version: 1.0.0
description: Short summary of what this skill does
---

# My Skill

Instructions, usage examples, API references, etc.
```

### Required Fields

| Field | Rules | Example |
|-------|-------|---------|
| `name` | Lowercase, alphanumeric + hyphens | `hyperliquid` |
| `version` | Semver | `1.0.0` |
| `description` | One-line summary for search | `Trade perpetual futures on Hyperliquid DEX` |

### Optional Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `tools` | List of tool names this skill provides | `[hl_account, hl_order]` |
| `metadata` | Starchild-specific metadata (emoji, skillKey) | `starchild: { emoji: "📊" }` |
| `user-invocable` | Whether users can invoke this skill directly | `true` |
| `tags` | Search tags | `[trading, defi]` |

### Multi-File Skills

Skills can include additional files (Python scripts, templates, configs). Place them alongside `SKILL.md` in the same directory:

```
birdeye/
├── SKILL.md
├── __init__.py
├── token.py
├── wallet.py
└── tools/
```

`npx skills add` copies the entire directory recursively.

## Development Workflow

> The quick steps below cover the basics. For the full guide — including `exports.py` patterns, function design principles (one-function-per-intent, read+execute pairing), logo sourcing, and a publishing checklist — see **[CONTRIBUTING.md](CONTRIBUTING.md)**.

### Add a New Skill

1. Create a directory:

```bash
mkdir my-new-skill
```

2. Write `SKILL.md` with the required frontmatter (name, version, description).

3. Push to `main`:

```bash
git add my-new-skill/
git commit -m "feat: add my-new-skill"
git push
```

4. GitHub Actions automatically validates the frontmatter and updates `skills.json`.

### Update an Existing Skill

1. Edit the skill files.

2. **Bump the version** in the frontmatter:

```yaml
version: 1.0.0  →  version: 1.1.0
```

3. Push. CI updates `skills.json` automatically.

> Users who already installed the skill will get the new version on next `npx skills add` (npx detects the changed `computedHash`).

### Remove a Skill

1. Delete the directory:

```bash
rm -rf old-skill
git add -A && git commit -m "chore: remove old-skill" && git push
```

2. CI updates `skills.json` automatically (skill removed from index).

3. To also remove from running user containers, add the skill name to `config/skill-removals.txt` in the [starchild-clawd](https://github.com/Starchild-ai-agent/starchild-clawd) repo.

## CI Pipeline

On every push to `main` that touches `*/SKILL.md`:

1. **Validate** — scans all `SKILL.md` files, fails if any are missing `name`, `version`, or `description`
2. **Rebuild** — generates `skills.json` from frontmatter
3. **Commit** — if `skills.json` changed, auto-commits and pushes

> `skills.json` is auto-generated. Do not edit it manually — your changes will be overwritten.

## Conventions

- **Naming**: lowercase, hyphens only (e.g. `trading-strategy`, not `TradingStrategy`)
- **Versioning**: semver — bump patch for fixes, minor for new features, major for breaking changes
- **One skill per directory**: each directory = one installable unit
- **Keep skills focused**: one skill = one integration or workflow (e.g. `hyperliquid`, not `all-exchanges`)
- **Description matters**: it's the primary search field — make it specific and keyword-rich
