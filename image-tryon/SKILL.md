---
name: image-tryon
version: 1.1.0
description: |
  Deprecated alias → use the `image` skill for virtual try-on. Kept for backward compatibility; new work should call `skills/image`.
metadata:
  starchild:
    emoji: "👗"
    skillKey: image-tryon
user-invocable: true
disable-model-invocation: false
---

# image-tryon (deprecated alias)

This skill is superseded by **`image`** (`skills/image/SKILL.md`), which covers virtual try-on with the same models plus real masks, resolution control, reference-role handling, edit transactions and `inspect()`.

**Use instead:** `edit() with person as image 1, garment as image 2` — see `skills/image/SKILL.md`.

The original script in this folder still works for existing callers but receives no further updates (fixed 3-model list, prompt templates, no mask/resolution). Install `image` via `search_skills("image")` if it is missing.
