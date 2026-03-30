---
name: skillmarketplace
version: 4.0.0
description: "Search, install, and publish skills. Use search_skills tool for discovery + auto-install. Manual publish via gateway."

metadata:
  starchild:
    emoji: "📦"
    skillKey: skillmarketplace

user-invocable: true
---

# Skill Market

## Searching & Installing

**Always use `search_skills` tool.** Never curl GitHub or manually download.

```
search_skills(query="deploy")                    # search + auto-install
search_skills(query="k8s", auto_install=false)   # search only
search_skills()                                  # list installed
```

Search order: local → Starchild community → skills.sh global ecosystem.
After install, skill is immediately available. `skill_refresh()` only needed after manual edits.

**Never** curl repos, mkdir + write SKILL.md manually, or web_fetch skill files.

## Publishing (Starchild Only)

### SKILL.md Frontmatter

```yaml
---
name: my-skill        # lowercase, alphanumeric + hyphens, 2-64 chars
version: 1.0.0        # semver, immutable once published
description: What it does
author: your-name
tags: [tag1, tag2]
---
```

### Publish Steps

```bash
# 1. Get OIDC token
TOKEN=$(curl -s --unix-socket /.fly/api \
  -X POST -H "Content-Type: application/json" \
  "http://localhost/v1/tokens/oidc" \
  -d '{"aud": "skills-market-gateway"}')

# 2. Build payload + publish
SKILL_DIR="./skills/my-skill"
GATEWAY="https://skills-market-gateway.fly.dev"

PAYLOAD=$(python3 -c "
import os, json
files = {}
for root, dirs, fnames in os.walk('$SKILL_DIR'):
    for f in fnames:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, '$SKILL_DIR')
        with open(full) as fh:
            files[rel] = fh.read()
print(json.dumps({'files': files}))
")

curl -s -X POST "$GATEWAY/skills/publish" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | python3 -m json.tool
```

Each version is immutable — bump version to update.
