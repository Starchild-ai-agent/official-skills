---
name: image-tryon
version: 1.0.0
description: |
  Virtual try-on: clothing, accessories, hairstyles, makeup, glasses, hats, shoes, watches.

  Use when the user wants to see how an item looks on a person — e.g. "try on this dress", "put these glasses on me", "show me with this hairstyle", "what would I look like in this outfit".
metadata:
  starchild:
    emoji: "👗"
    skillKey: image-tryon
    requires:
      env: [FAL_KEY]
user-invocable: true
disable-model-invocation: false

---

# image-tryon

Use this skill for **all virtual try-on requests** on Starchild.

Covers: clothing try-on, accessory try-on, hairstyle preview, makeup preview, glasses try-on, hat try-on, shoes try-on, watch try-on.

**Core principle:** call the provided script. Do not re-implement proxy/billing plumbing.

**Key difference from image-edit:** try-on always requires **two images** — a person photo and a garment/item photo.

---

## 1. Quick start — clothing try-on (most common)

```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/person.jpg",
    garment_path="uploads/dress.jpg",
    category="clothing",
)
# result -> {"success": True, "images": [{"local_path": "output/images/..."}], ...}
```

The script reads both local files, base64-encodes them, and sends them to fal.ai as data URIs — no manual URL publishing needed.

## 2. Quick start — URL inputs

```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_url="https://example.com/person.jpg",
    garment_url="https://example.com/jacket.jpg",
    category="clothing",
)
```

## 3. Quick start — glasses try-on

```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/face.jpg",
    garment_path="uploads/sunglasses.jpg",
    category="glasses",
)
```

### Delivering the result to the user — IMPORTANT

**Never hand the user the raw fal.media URL.** fal serves files with restrictive CSP headers. The only reliable delivery path is the **already-downloaded local file**:

1. Use each image's `local_path` (e.g. `output/images/xxx.png`) — the script always downloads on success.
2. Tell the user the files are saved to `output/images/` and viewable in the workspace file panel.
3. On Web channel, embed inline so the user can preview in chat:
   ```markdown
   ![try-on result](output/images/<filename>.png)
   ```
4. On Telegram / WeChat: send via `send_to_telegram(file_path="output/images/...", message_type="image")` or `send_to_wechat(file_path="output/images/...", message_type="image")`.

---

## 4. Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `person_path` | yes* | — | Local workspace file path to the person's photo |
| `person_url` | yes* | — | Public HTTPS URL of the person's photo |
| `garment_path` | yes* | — | Local workspace file path to the garment/item photo |
| `garment_url` | yes* | — | Public HTTPS URL of the garment/item photo |
| `category` | no | `"clothing"` | Try-on category key (see §5) |
| `prompt` | no | `None` | Custom prompt — overrides category default when set |
| `model` | no | `"nanopro"` | Model: `"nanopro"` (fast ~25s) or `"gpt"` (best quality ~150s) |
| `aspect_ratio` | no | `"3:4"` | Output ratio: `1:1`, `3:4`, `4:3`, `9:16`, `16:9` |

**Image input rules:**
- **Person image:** provide `person_path` OR `person_url` (one is required).
- **Garment/item image:** provide `garment_path` OR `garment_url` (one is required).
- If both path and URL are given for the same image, path takes priority.
- Both images are required — try-on cannot work with only one image.

**Prompt priority:** `prompt` (full override) > `category` default prompt.

---

## 5. Try-on categories

### Intent recognition — what the user says → which category to use

| User says | Category | Key |
|-----------|----------|-----|
| "try on this dress/shirt/jacket/outfit" | Clothing | `clothing` |
| "put this necklace/scarf/bag on me" | Accessory | `accessory` |
| "show me with this hairstyle/hair color" | Hairstyle | `hairstyle` |
| "apply this makeup/lipstick look" | Makeup | `makeup` |
| "try on these glasses/sunglasses" | Glasses | `glasses` |
| "put this hat/cap/beanie on me" | Hat | `hat` |
| "try on these shoes/sneakers/boots" | Shoes | `shoes` |
| "put this watch on my wrist" | Watch | `watch` |

### Category details

| Category | Key | Best for | Photo requirements |
|----------|-----|----------|-------------------|
| Clothing | `clothing` | Shirts, dresses, jackets, pants, coats, full outfits | Full body or upper body person photo |
| Accessory | `accessory` | Scarves, bags, belts, jewelry, necklaces, earrings | Relevant body area visible |
| Hairstyle | `hairstyle` | Haircuts, hair colors, styling changes | Clear face/head photo |
| Makeup | `makeup` | Lipstick, eyeshadow, foundation, blush, full looks | Clear face close-up |
| Glasses | `glasses` | Prescription glasses, sunglasses, reading glasses | Clear face photo, front-facing |
| Hat | `hat` | Caps, beanies, fedoras, sun hats, helmets | Head and shoulders visible |
| Shoes | `shoes` | Sneakers, heels, boots, sandals, loafers | Full body or lower body photo |
| Watch | `watch` | Analog, smartwatches, luxury watches | Wrist/arm visible |

---

## 6. Model selection guide

| Model | Key | Speed | Quality | Best for |
|-------|-----|-------|---------|----------|
| NanoPro | `nanopro` | ~25s | Good | Default for all requests. Fast iteration. |
| GPT Image 2 | `gpt` | ~150s | Best | When user explicitly asks for "highest quality" or "best quality". |

**Decision rules:**
1. **Default:** always use `nanopro` unless the user explicitly requests higher quality.
2. **Use `gpt` when:** user says "highest quality", "best quality", "premium", or the result needs to be photorealistic for professional use.
3. **Use `nanopro` when:** user wants fast results, is trying multiple items, or iterating on looks.

```python
# Default (fast)
result = try_on(person_path="me.jpg", garment_path="dress.jpg", category="clothing")

# High quality (user requested)
result = try_on(person_path="me.jpg", garment_path="dress.jpg", category="clothing", model="gpt")
```

---

## 7. Usage examples by category

### Clothing try-on
```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/person_fullbody.jpg",
    garment_path="uploads/summer_dress.jpg",
    category="clothing",
)
```

### Accessory try-on
```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/portrait.jpg",
    garment_path="uploads/gold_necklace.jpg",
    category="accessory",
)
```

### Hairstyle preview
```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/face.jpg",
    garment_path="uploads/bob_hairstyle.jpg",
    category="hairstyle",
)
```

### Makeup preview
```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/face_closeup.jpg",
    garment_path="uploads/evening_makeup.jpg",
    category="makeup",
)
```

### Glasses try-on
```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/face_front.jpg",
    garment_path="uploads/aviator_sunglasses.jpg",
    category="glasses",
)
```

### Hat try-on
```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/head_shoulders.jpg",
    garment_path="uploads/fedora_hat.jpg",
    category="hat",
)
```

### Shoes try-on
```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/person_fullbody.jpg",
    garment_path="uploads/white_sneakers.jpg",
    category="shoes",
)
```

### Watch try-on
```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/wrist_photo.jpg",
    garment_path="uploads/luxury_watch.jpg",
    category="watch",
)
```

### Custom prompt (override default)
```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/person.jpg",
    garment_path="uploads/vintage_jacket.jpg",
    category="clothing",
    prompt="The person is wearing the vintage leather jacket from the second image, styled with a casual street fashion look. Keep the person's face and body exactly the same. Add realistic leather texture and natural draping.",
)
```

### Different aspect ratio
```python
exec(open('skills/image-tryon/try_on.py').read())
result = try_on(
    person_path="uploads/person.jpg",
    garment_path="uploads/outfit.jpg",
    category="clothing",
    aspect_ratio="9:16",  # Full-length portrait
)
```

---

## 8. Photo requirements — best practices

### Person photo guidelines

| Category | Recommended photo type | Tips |
|----------|----------------------|------|
| Clothing | Full body, front-facing | Arms slightly away from body, neutral pose |
| Accessory | Relevant body area visible | Good lighting on the area where accessory goes |
| Hairstyle | Clear head/face, front or 3/4 view | Hair pulled back or current style clearly visible |
| Makeup | Face close-up, front-facing | Clean face, good even lighting, no heavy makeup |
| Glasses | Face front-facing, eyes visible | No existing glasses, clear eye area |
| Hat | Head and shoulders, front-facing | No existing hat, hair visible |
| Shoes | Full body or legs/feet visible | Standing pose, current shoes visible |
| Watch | Wrist/forearm visible | Bare wrist or current watch visible |

### General photo quality rules

1. **Lighting:** well-lit, even lighting works best. Avoid harsh shadows on the face/body.
2. **Resolution:** 1024×1024 or higher recommended. Low-res photos produce poor results.
3. **Angle:** front-facing photos work best for most categories.
4. **Background:** any background works, but clean backgrounds produce cleaner results.
5. **Pose:** natural, relaxed poses. Avoid extreme angles or heavy cropping.

### Garment/item photo guidelines

1. **Product shots work best:** official product images on white/neutral backgrounds.
2. **Clear visibility:** the item should be the main focus, not obscured.
3. **Multiple angles:** front view is most important for clothing.
4. **Color accuracy:** ensure the photo shows true colors (no heavy filters).
5. **High resolution:** detailed product images produce better try-on results.

---

## 9. Prompt engineering for custom try-on

When the default category prompt doesn't produce the desired result, use a custom `prompt`. Follow these guidelines:

### The 5-element try-on prompt structure

```
[person preservation] + [item description] + [fit/positioning] + [style/mood] + [quality anchors]
```

### Key principles

1. **Always preserve identity:** "Keep the person's face, body shape, and pose exactly the same."
2. **Describe the item clearly:** "wearing the red leather jacket from the second image"
3. **Specify fit and positioning:** "natural draping, proper shoulder fit, realistic wrinkles"
4. **Add style context:** "casual street style look", "formal business attire"
5. **Quality anchors:** "professional fashion photography", "editorial quality", "realistic shadows"

### Example custom prompts

**Formal outfit:**
```
The person is wearing the navy blue suit from the second image. Keep the person's face, body, and pose exactly the same. The suit should fit perfectly with proper tailoring — clean shoulder line, correct sleeve length, natural lapel lay. Professional fashion photography quality with studio lighting.
```

**Casual street style:**
```
The person is wearing the oversized hoodie from the second image in a relaxed street style. Keep the person's identity and pose the same. The hoodie should drape naturally with realistic fabric weight and casual fit. Urban photography style.
```

**Jewelry combination:**
```
The person is wearing the diamond pendant necklace from the second image. Keep everything about the person the same. The necklace should sit naturally on the collarbone with realistic sparkle and light reflections. The chain length and pendant size should be proportional to the person's frame.
```

---

## 10. Error handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Person image error: Either person_path or person_url must be provided" | Missing person photo | Ask user for their photo |
| "Garment/item image error: Either garment_path or garment_url must be provided" | Missing item photo | Ask user for the item photo |
| "File not found" | Invalid file path | Check the file path and try again |
| "Unsupported image format" | Non-image file | Use JPG, PNG, or WebP |
| "Image too large" | File > 10 MB | Resize or compress the image |
| "Unknown category" | Invalid category key | Use one of the 8 valid categories |
| Low quality result | Poor input photos | Use higher resolution, well-lit photos |
| Wrong item placement | Unclear body positioning | Use front-facing photos with target area visible |

---

## 11. When NOT to use this skill

- **Single image editing** (no garment/item reference) → use `image-edit` skill
- **Portrait generation** (styled photos from one reference) → use `image-portrait` skill
- **Text-to-image** (no reference photos at all) → use `image-create` skill
- **Fashion model generation** (creating models from scratch) → use `image-create` skill
