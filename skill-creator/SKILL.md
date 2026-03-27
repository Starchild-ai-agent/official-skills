---
name: skill-creator
version: 1.0.0
description: "Create and scaffold new skills with proper frontmatter, directory structure, and validation. Use when the user asks to build a new capability, integrate a new API, or extend the system with a repeatable workflow."

metadata:
  starchild:
    emoji: "🛠️"
    skillKey: skill-creator

user-invocable: true
---

# Skill Creator

Create new skills to permanently extend agent capabilities.

## Core Principles

**Concise is key.** Context window is shared — every SKILL.md line competes with system prompt, history, and reasoning. Only add what the agent doesn't already know. Don't document tool params visible in system prompt.

**Progressive disclosure:**
1. **Always in context** — name + description in `<available_skills>` (trigger for activation)
2. **On activation** — full SKILL.md body loaded via `read_file`
3. **On demand** — `scripts/`, `references/`, `assets/` loaded only when needed

Keep SKILL.md body < 500 lines. Put detailed API docs in `references/`, automation in `scripts/`.

**Freedom levels:**
- **High** (text guidance) — multiple valid approaches, explain WHAT and WHY
- **Medium** (pseudocode + params) — preferred pattern exists, describe approach with key params
- **Low** (scripts/) — fragile operations, exact syntax, executed not loaded

## Skill Structure

```
my-skill/
├── SKILL.md          # Required: frontmatter + instructions
├── scripts/          # Optional: executable code (run via bash)
├── references/       # Optional: docs loaded on demand
└── assets/           # Optional: templates, images, data files
```

## Creating a Skill

### 1. Understand the Request
- What capability? (API integration, workflow, knowledge domain)
- What triggers it? → becomes the description
- What freedom level? → determines scripts vs text guidance
- What dependencies? → env vars, binaries, packages

### 2. Scaffold

```bash
python skills/skill-creator/scripts/init_skill.py my-skill --path ./workspace/skills
# With resources:
python skills/skill-creator/scripts/init_skill.py my-skill --path ./workspace/skills --resources scripts,references
# With examples:
python skills/skill-creator/scripts/init_skill.py my-skill --path ./workspace/skills --resources scripts --examples
```

### 3. Write SKILL.md

Body design patterns:
- **Workflow-based** — step-by-step process (fetch → configure → render → serve)
- **Task-based** — organized by user asks ("analyze a coin" / "compare strategies")
- **Reference/guidelines** — rules, frameworks, decision trees
- **Capabilities-based** — organized by what the skill can do

### 4. Validate & Refresh

```bash
python skills/skill-creator/scripts/validate_skill.py ./workspace/skills/my-skill
```
Then call `skill_refresh()` to make it available.

## Frontmatter Format

```yaml
---
name: skill-name
description: "What this does. Use when [trigger scenarios]."
metadata:
  starchild:
    emoji: "🔧"
    skillKey: skill-name
    requires:
      env: [API_KEY_NAME]
      bins: [python]
    install:
      - kind: pip
        package: pandas
user-invocable: true
disable-model-invocation: false
---
```

Key fields: `name` (required), `description` (required, trigger text), `requires.env` (env vars), `requires.bins` (ALL must exist), `requires.anyBins` (ANY one), `install` (pip/apt/npm deps).

## On-Chain Skills — Wallet Policy

If the skill involves on-chain operations (transactions, approvals, swaps), add a Prerequisites section near the top:

> Before executing, load **wallet-policy** skill and propose standard wildcard policy (deny key export + allow `*`).

## What NOT to Include

- README.md (SKILL.md IS the readme)
- Tool descriptions already in system prompt
- Step-by-step for simple tasks the agent can figure out
- Generic programming advice ("use error handling")

## Best Practices

1. **Description is the trigger** — include "Use when..." with specific scenarios
2. **Write for the agent** — direct language: "You generate charts" not "This skill can be used to..."
3. **Scripts execute without loading** — keeps context clean
4. **Don't duplicate system prompt** — focus on domain knowledge, gotchas, decision trees
5. **Request credentials last** — design skill first, then ask for API keys
6. **Always validate** before refreshing
