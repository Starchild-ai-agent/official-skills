---
name: image-bg-remove
version: 1.1.0
description: |
  Deprecated alias → use the `image` skill for background removal. Kept for backward compatibility; new work should call `skills/image`.
metadata:
  starchild:
    emoji: "✂️"
    skillKey: image-bg-remove
user-invocable: true
disable-model-invocation: false
---

# image-bg-remove (deprecated alias)

This skill is superseded by **`image`** (`skills/image/SKILL.md`), which covers background removal with the same models plus real masks, resolution control, reference-role handling, edit transactions and `inspect()`.

**Use instead:** `remove_background(image_path)` — see `skills/image/SKILL.md`.

The original script in this folder still works for existing callers but receives no further updates (fixed 3-model list, prompt templates, no mask/resolution). Install `image` via `search_skills("image")` if it is missing.
