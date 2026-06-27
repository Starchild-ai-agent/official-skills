# Contributing a Skill to Starchild Official Skills

This guide walks you through building a skill that meets the Starchild official
standard — the same bar the `across-bridge`, `wallet`, and `hyperliquid` skills
are held to. Follow it end-to-end and your skill will install cleanly, show up
in search, and feel native to any agent that calls it.

---

## 1. What is a Starchild Skill?

A skill is a **self-contained directory** that teaches an agent how to use a
tool, API, or workflow. It has two halves:

- **`SKILL.md`** — the human/agent-readable contract: what it does, when to
  use it, how to call it, gotchas. This is what the agent reads to decide
  whether to use the skill and how.
- **`exports.py`** (+ supporting scripts) — the executable half: Python
  functions the agent calls at runtime via `core.skill_tools`.

A skill is NOT a prompt template, a config file, or a loose collection of
scripts. It is a **callable capability** with a documented interface.

---

## 2. Directory Structure

```
my-skill/
├── SKILL.md          ← required: frontmatter + usage doc
├── exports.py        ← required for script skills: public function surface
├── __init__.py       ← empty, makes it a package
├── logo.png          ← recommended: 128×128 or 256×256, ≤ 50KB
├── scripts/          ← optional: implementation modules
│   └── my_api.py
└── tools/            ← optional: alternative location for modules
    └── helpers.py
```

### Minimum viable skill

```
my-skill/
├── SKILL.md
└── exports.py
```

That's it. `logo.png`, `__init__.py`, `scripts/`, `tools/` are all optional.
But every official skill should have a logo — see §6.

---

## 3. SKILL.md — The Contract

### 3.1 Required frontmatter

Three fields are **mandatory** — CI will reject the build if any are missing:

```yaml
---
name: my-skill              # lowercase, hyphens only, matches dir name
version: 1.0.0              # semver
description: |
  One-line summary, then a blank line, then a "Use when…" sentence.
  This is the PRIMARY search field — be specific and keyword-rich.
---
```

### 3.2 Recommended frontmatter

```yaml
author: starchild
tags: [defi, bridge, evm, ethereum, arbitrum]
delivery: script            # "script" = callable Python functions
metadata:
  starchild:
    emoji: 🌉               # shown in skill cards / search results
    skillKey: my-skill      # matches dir name
    requires:
      bins: [python3]       # system binaries the skill needs
      env: [MY_API_KEY]     # env vars (user provides via request_env_input)
    install:
      - kind: pip
        package: requests   # pip deps auto-installed on skill load
```

### 3.3 Body structure

Use this template — agents rely on these sections to decide when and how to
call the skill:

```markdown
# 🌉 Skill Name

One-paragraph elevator pitch: what it does, why it's fast/cheap/better.

## When to Use
- Concrete trigger phrases ("bridge 50 USDC from Base to Arbitrum")
- 3–5 bullet points covering the main use cases

## Supported <Chains / Exchanges / Endpoints>
Plain list — helps the agent answer "does this support X?" without reading code.

## How to Call

Show the EXACT import + call pattern. For hyphenated skill names, use the
`_modules` dict (see §4.2):

\```bash
python3 - <<'EOF'
from core.skill_tools import _modules
my = _modules["my-skill"]
import json
print(json.dumps(my.do_thing(arg="value"), indent=2))
EOF
\```

### `function_name(args)` — one-line summary
What it returns, what side effects it has.

## Workflows
### The common case (end-to-end)
### The read-only case (quote / check / status)

## Key Facts / Gotchas
- Things that surprised you during development
- Auth model, rate limits, settlement times
- "Gas is sponsored" / "Wallet is the Agent Wallet" type facts

## Dependencies
- pip packages
- other skills (e.g. "uses core.skill_tools.wallet for signing")
```

**Do NOT** include:
- Long API reference dumps (link to the provider's docs instead)
- Internal implementation notes
- Changelogs (use git history)

---

## 4. exports.py — The Function Surface

`exports.py` is the **only** file the skill loader looks at. It defines the
public functions agents call. Everything else (`scripts/*.py`, `tools/*.py`)
is loaded as supporting infrastructure.

### 4.1 Minimal exports.py

```python
"""
my-skill exports — for use in task scripts via core.skill_tools.

Usage:
    from core.skill_tools import _modules
    my = _modules["my-skill"]
    result = my.do_thing(arg="value")
"""
import os, importlib.util

_here = os.path.dirname(__file__)
_mod_path = os.path.join(_here, "scripts", "my_api.py")
_spec = importlib.util.spec_from_file_location("_my_core", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

do_thing = _mod.do_thing
get_quote = _mod.get_quote
```

The loader auto-discovers `exports.py` and registers every public function in
it. You do **not** need `__all__` — but you **can** use it to hide helpers:

```python
__all__ = ["do_thing", "get_quote"]   # only these are exposed
```

### 4.2 Hyphenated skill names

Skill names use hyphens (`across-bridge`, `us-stock`), but Python identifiers
can't. So `from core.skill_tools import across_bridge` does **not** work. Use
the `_modules` dict instead:

```python
from core.skill_tools import _modules
across = _modules["across-bridge"]
across.bridge_execute(...)
```

This is the official pattern — document it in your SKILL.md so agents don't
waste a turn discovering it.

### 4.3 What the loader filters out automatically

The `core.skill_tools` loader wraps your exports in a namespace proxy that
hides:
- Imported modules (`os`, `requests`, `json`)
- ALL_CAPS constants (`API_URL`, `FLY_SOCKET`)
- Private names (`_helper`)
- Classes and non-callable attributes

So you can freely import at module top without polluting the public surface.
Just define your functions and they're exported.

### 4.4 Import isolation for supporting modules

If your `exports.py` does `from utils import some_function`, the loader
pre-loads every `.py` in `scripts/` and `tools/` under unique names and
injects them as bare modules during load. This means:

- `from utils import x` just works — no `sys.path` hacks
- Your `utils.py` won't permanently shadow another skill's `utils.py`
- You don't need `__all__` or careful naming

**But**: keep `exports.py` thin. Put real logic in `scripts/`. `exports.py`
should be ~30 lines: load the core module, re-export functions, done.

---

## 5. Function Design — Best Practices

### 5.1 One function = one user intent

The biggest quality signal. Don't make the agent orchestrate:

```python
# ❌ Bad — agent must call 4 functions in sequence
get_quote() → encode_calldata() → send_approval() → send_bridge() → check_status()

# ✅ Good — one function, end-to-end
bridge_execute(from_chain, to_chain, token, amount, wallet)
```

If a workflow always has the same steps, package them. The agent should be
able to say "bridge 1 USDC Base→Arbitrum" and your skill handles the rest.

### 5.2 Pair read-only + end-to-end

Expose at least two functions:

| Function | Purpose |
|----------|---------|
| `*_quote()` / `*_status()` / `*_get()` | Read-only, safe to call freely |
| `*_execute()` / `*_send()` / `*_create()` | Side effects, does the real thing |

This lets the agent "think before acting" — get a quote, show it to the user,
then execute only after confirmation.

### 5.3 Accept human-friendly args, return structured JSON

```python
# ✅ Good — agent passes "USDC", "base", 1.0
bridge_execute(from_chain="base", to_chain="arbitrum",
               token="USDC", amount=1, wallet="0x...")

# ❌ Bad — agent must know chain IDs, wei, contract addresses
bridge_execute(origin_chain_id=8453, dest_chain_id=42161,
               input_token="0x833589...", amount_wei="1000000", ...)
```

Internally resolve symbols → IDs/addresses via a registry. Return a dict with
both human and machine fields:

```python
{
  "output_amount": "995312",        # machine
  "output_amount_human": 0.995312,  # human
  "fees": {"total_pct": "0.47", ...},
  "arrival_confirmed": true,
}
```

### 5.4 Lazy-import platform dependencies

`core.skill_tools.wallet` only exists at runtime in the platform container.
If your skill needs it, import it inside the function, not at module top:

```python
def bridge_execute(...):
    from core.skill_tools import wallet as w   # lazy
    ...
```

This keeps `exports.py` loadable in any environment (CI, local dev).

### 5.5 Verify side effects before returning success

For anything that moves money or mutates external state, don't return
`status: "success"` just because the API call returned 200. Poll the
destination / re-read state until you can confirm:

```python
# bridge_execute polls destination balance until funds actually arrive
arrival_confirmed = _poll_destination_balance(timeout=180)
return {"status": "success" if arrival_confirmed else "submitted_unconfirmed", ...}
```

### 5.6 Include a CLI for debugging

Add an `if __name__ == "__main__"` block to your core script so you (and
reviewers) can test from bash without spinning up the full skill loader:

```python
# scripts/across.py
if __name__ == "__main__":
    import sys, json
    cmd = sys.argv[1]
    if cmd == "quote":
        print(json.dumps(bridge_quote(*sys.argv[2:]), indent=2))
    elif cmd == "execute":
        print(json.dumps(bridge_execute(*sys.argv[2:]), indent=2, default=str))
```

---

## 6. Logo

Every official skill should ship a logo. It shows up in skill cards, search
results, and the installed-skills panel.

### 6.1 Specs

| Property | Value |
|----------|-------|
| Format | **PNG** preferred (SVG also accepted) |
| Size | 128×128 or 256×256 px |
| File size | ≤ 50 KB |
| Filename | `logo.png` (or `logo.svg`) in the skill root |
| Background | Transparent or solid — match the brand |

### 6.2 Where to get one

- **Official brand assets page** — most projects have one (e.g.
  `docs.across.to/brand-assets`, `https://ethereum.org/brand`)
- **Favicon / OG image** — if no brand page, fetch the site's favicon:
  ```bash
  curl -sL "https://across.to/favicon.svg" -o logo.svg
  ```
- **seeklogo / cdnlogo** — community-hosted SVGs for major brands
- **Generate one** — as a last resort, use the `image-create` skill to make a
  256×256 icon that matches the skill's domain

### 6.3 Verify

```bash
ls -la my-skill/logo.png   # exists, < 50KB
file my-skill/logo.png     # "PNG image data, 256 x 256"
```

The loader picks up `logo.png` / `logo.svg` automatically — no frontmatter
field needed.

---

## 7. Publishing Checklist

Before opening a PR, verify:

- [ ] `SKILL.md` has `name`, `version`, `description` in frontmatter
- [ ] `name` matches the directory name (lowercase, hyphens only)
- [ ] `description` is specific and keyword-rich (it's the search field)
- [ ] `exports.py` loads cleanly: `python3 -c "import importlib.util, os; s=importlib.util.spec_from_file_location('m','my-skill/exports.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(dir(m))"`
- [ ] At least one read-only function + one end-to-end function
- [ ] Functions accept human-friendly args (symbols, not IDs/addresses)
- [ ] `logo.png` exists, < 50KB
- [ ] Tested with a real call (not just "it should work")
- [ ] `metadata.starchild.install` lists pip deps
- [ ] No hardcoded secrets, API keys, or wallet addresses

---

## 8. Publishing Flow

```bash
# 1. Clone
git clone https://github.com/Starchild-ai-agent/official-skills.git
cd official-skills
git checkout -b feat/my-skill

# 2. Add your skill directory
mkdir my-skill
# ... add SKILL.md, exports.py, logo.png, scripts/ ...

# 3. Commit & push
git add my-skill/
git commit -m "feat: add my-skill — one-line description"
git push origin feat/my-skill

# 4. Open PR
# GitHub Actions validates frontmatter + rebuilds skills.json automatically
```

### CI does the rest

On push to `main`, the `build-index.yml` workflow:
1. **Validates** every `SKILL.md` — fails if `name`/`version`/`description` missing
2. **Rebuilds** `skills.json` from frontmatter
3. **Commits** the updated index back to `main`

You do not need to edit `skills.json` manually — it's auto-generated.

---

## 9. Versioning

Follow semver:

| Change | Bump |
|--------|------|
| Bug fix, doc tweak | patch (`1.0.0 → 1.0.1`) |
| New function, new feature | minor (`1.0.0 → 1.1.0`) |
| Breaking API change | major (`1.0.0 → 2.0.0`) |

Users who already installed the skill get the new version on their next
`npx skills add` (npx detects the changed `computedHash`).

---

## 10. Removing a Skill

```bash
rm -rf old-skill
git add -A && git commit -m "chore: remove old-skill" && git push
```

CI removes it from `skills.json`. To also remove it from running user
containers, add the skill name to `config/skill-removals.txt` in the
[starchild-clawd](https://github.com/Starchild-ai-agent/starchild-clawd) repo.

---

## 11. Reference Skills

Read these before building your own — they embody the standard:

| Skill | Why study it |
|-------|-------------|
| `wallet` | Lazy-imports platform deps; clean read/write split |
| `hyperliquid` | `exports.py` + `client.py` + `tools.py` separation |
| `across-bridge` | One-function end-to-end + quote pair; hyphenated name pattern |
| `coingecko` | Simple read-only skill with `tools/` layout |
| `1inch` | `delivery: script` + `requires.env` for API keys |

---

## 12. Common Mistakes

| Mistake | Fix |
|---------|-----|
| `from core.skill_tools import my_skill` fails | Hyphenated name — use `_modules["my-skill"]` |
| CI rejects the build | Missing `name`/`version`/`description` in frontmatter |
| Agent calls 5 functions to do one thing | Package the workflow into one `*_execute()` |
| Skill works locally, fails in container | Hardcoded path or top-level `from core.skill_tools import wallet` — lazy-import instead |
| `description` too vague | Add a "Use when…" sentence with concrete examples |
| No logo | Fetch favicon or brand SVG; see §6 |
| Exposing `os`, `requests` as "functions" | You don't need to — the loader filters them out |
| Editing `skills.json` manually | Don't — CI overwrites it on every push |

---

Questions? Open an issue or ask in the Starchild community. Happy building.
