---
name: image-3d
version: 1.1.0
description: |
  Deprecated alias → use the `image` skill for 3D-style renders. Kept for backward compatibility; new work should call `skills/image`.
metadata:
  starchild:
    emoji: "🧊"
    skillKey: image-3d
user-invocable: true
disable-model-invocation: false
---

# image-3d (deprecated alias)

This skill is superseded by **`image`** (`skills/image/SKILL.md`), which covers 3D-style renders with the same models plus real masks, resolution control, reference-role handling, edit transactions and `inspect()`.

**Use instead:** `generate()/edit() with a 3D-render prompt` — see `skills/image/SKILL.md`.

The original script in this folder still works for existing callers but receives no further updates (fixed 3-model list, prompt templates, no mask/resolution). Install `image` via `search_skills("image")` if it is missing.
