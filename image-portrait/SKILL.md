---
name: image-portrait
version: 1.1.0
description: |
  Deprecated alias → use the `image` skill for identity-consistent portraits. Kept for backward compatibility; new work should call `skills/image`.
metadata:
  starchild:
    emoji: "👤"
    skillKey: image-portrait
user-invocable: true
disable-model-invocation: false
---

# image-portrait (deprecated alias)

This skill is superseded by **`image`** (`skills/image/SKILL.md`), which covers identity-consistent portraits with the same models plus real masks, resolution control, reference-role handling, edit transactions and `inspect()`.

**Use instead:** `edit() with the reference face as image 1` — see `skills/image/SKILL.md`.

The original script in this folder still works for existing callers but receives no further updates (fixed 3-model list, prompt templates, no mask/resolution). Install `image` via `search_skills("image")` if it is missing.
