---
name: image-edit
version: 1.1.0
description: |
  Deprecated alias → use the `image` skill for editing an existing image. Kept for backward compatibility; new work should call `skills/image`.
metadata:
  starchild:
    emoji: "✏️"
    skillKey: image-edit
user-invocable: true
disable-model-invocation: false
---

# image-edit (deprecated alias)

This skill is superseded by **`image`** (`skills/image/SKILL.md`), which covers editing an existing image with the same models plus real masks, resolution control, reference-role handling, edit transactions and `inspect()`.

**Use instead:** `edit(prompt, [base, *refs], keep=, mask_path=)` — see `skills/image/SKILL.md`.

The original script in this folder still works for existing callers but receives no further updates (fixed 3-model list, prompt templates, no mask/resolution). Install `image` via `search_skills("image")` if it is missing.
