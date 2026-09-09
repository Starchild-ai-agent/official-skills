---
name: image-ecommerce
version: 1.0.4
description: |
  Deprecated alias → use the `image` skill for product photography. Kept for backward compatibility; new work should call `skills/image`.
metadata:
  starchild:
    emoji: "🛍️"
    skillKey: image-ecommerce
user-invocable: true
disable-model-invocation: false
---

# image-ecommerce (deprecated alias)

This skill is superseded by **`image`** (`skills/image/SKILL.md`), which covers product photography with the same models plus real masks, resolution control, reference-role handling, edit transactions and `inspect()`.

**Use instead:** `edit() with the product photo as base` — see `skills/image/SKILL.md`.

The original script in this folder still works for existing callers but receives no further updates (fixed 3-model list, prompt templates, no mask/resolution). Install `image` via `search_skills("image")` if it is missing.
