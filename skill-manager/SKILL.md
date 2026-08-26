---
name: skill-manager
version: 4.3.0
description: |
  Search, install, and manage skills across official and global registries.

  Use when finding or installing skills (e.g. install a "funding rate" skill, list installed skills).

metadata:
  starchild:
    emoji: "📦"
    skillKey: skill-manager

user-invocable: true

---

# Skills

## Searching & Installing Skills

**Always use the `search_skills` tool.** Do NOT manually curl, browse GitHub, or download SKILL.md files.

`search_skills` does everything automatically:

1. **Local** — checks installed skills first
2. **Official** — searches Starchild official-skills index
3. **skills.sh** — searches the global skills ecosystem (OpenClaw, Vercel, Anthropic, etc.)
4. **Auto-install** — installs the best match via `npx skills add` (default: `auto_install=true`)

### Usage

```
search_skills(query="deploy")           # search + auto-install best match
search_skills(query="trading")          # search + auto-install
search_skills(query="k8s", auto_install=false)  # search only, don't install
search_skills()                         # list all installed skills
```

After `search_skills` installs a skill, it's immediately available. Call `skill_refresh()` only if you manually edited skill files.

### What NOT to do

- Do NOT `curl` GitHub repos to browse/download skills
- Do NOT `mkdir -p skills/<name>` and manually write SKILL.md
- Do NOT use `web_fetch` to download skill files
- Do NOT use the old gateway search/install endpoints (they no longer exist)
- Do NOT publish skills to the community-skills registry (product offline)

---

## Decision Tree

```
User wants to find/install a skill
  → Use search_skills(query) tool — it searches all sources and auto-installs
  → NEVER curl GitHub or manually download files

User wants to list installed skills
  → Use search_skills() with no query

User wants to create a new skill
  → Read the skill-creator skill first

User wants to publish a skill to community registry
  → Community Skill product is offline — do not publish
```
