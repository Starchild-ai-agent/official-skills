---
name: image-bg-remove
version: 1.0.1
description: >-
  Background removal — transparent PNG cutouts of products, portraits, pets; no prompt needed, ~3s, $0.01 (Bria RMBG 2.0).
metadata:
  starchild:
    emoji: "✂️"
    skillKey: image-bg-remove
    requires:
      env: [FAL_KEY]
user-invocable: true
disable-model-invocation: false

---

# image-bg-remove

Use this skill for **all background removal requests** on Starchild.

Covers: portrait background removal (ID photos, headshots), product cutouts (e-commerce white-background), group photo background removal, pet/animal cutouts, object isolation, and preparing transparent PNGs for compositing.

**Core principle:** call the provided script. Do not re-implement proxy/billing plumbing.

**Key difference from other image skills:** this skill uses a **dedicated background removal model** (`fal-ai/bria/background/remove` — Bria RMBG 2.0), not the general-purpose nanopro/gpt models. No prompt is needed — just provide an image.

---

## When to use

Background removal: transparent PNGs, cutouts, product photos, portraits, pets, group photos.
Uses dedicated Bria RMBG 2.0 model — no prompt needed, fast (~3s), cheap ($0.01).

Use when removing backgrounds, creating transparent PNGs, making cutouts, extracting foreground subjects, or preparing images for compositing.

## 1. Quick start — local file (most common)

```python
exec(open('skills/image-bg-remove/remove_bg.py').read())
result = remove_bg(image_path="uploads/photo.jpg")
# result -> {"success": True, "image": {"local_path": "output/images/..."}, "cost": 0.01, "duration_s": 3.2}
```

The script reads the local file, base64-encodes it, and sends it to fal.ai as a data URI — no manual URL publishing needed.

## 2. Quick start — public URL

```python
exec(open('skills/image-bg-remove/remove_bg.py').read())
result = remove_bg(image_url="https://example.com/photo.jpg")
```

## 3. Quick start — custom output path

```python
exec(open('skills/image-bg-remove/remove_bg.py').read())
result = remove_bg(
    image_path="uploads/product.jpg",
    output_path="output/images/product_transparent.png",
)
```

### Delivering the result to the user — IMPORTANT

**Never hand the user the raw fal.media URL.** fal serves files with restrictive CSP headers. The only reliable delivery path is the **already-downloaded local file**:

1. Use the image's `local_path` (e.g. `output/images/xxx.png`) — the script always downloads on success.
2. Tell the user the file is saved to `output/images/` and viewable in the workspace file panel.
3. On Web channel, embed inline so the user can preview in chat:
   ```markdown
   ![transparent](output/images/<filename>.png)
   ```
4. On Telegram / WeChat: send via `send_to_telegram(file_path="output/images/...", message_type="image")` or `send_to_wechat(file_path="output/images/...", message_type="image")`.

---

## 4. Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `image_path` | yes* | — | Local workspace file path to the source image |
| `image_url` | yes* | — | Public HTTPS URL of the source image |
| `output_path` | no | auto | Custom output file path. If not set, saves to `output/images/` with timestamp. |

*At least one of `image_path` or `image_url` must be provided. If both are given, `image_path` takes priority.

**No prompt parameter** — this is a pure tool skill. The dedicated model handles background removal automatically without any text instruction.

---

## 5. When to use this skill

Use **image-bg-remove** when the user wants to:

| User says | Use this skill |
|-----------|---------------|
| "remove the background" / "去背景" / "抠图" | ✅ Yes |
| "make it transparent" / "透明背景" | ✅ Yes |
| "create a cutout" / "cut out the person" | ✅ Yes |
| "product photo with white background" / "白底图" | ✅ Yes |
| "extract the foreground" / "isolate the subject" | ✅ Yes |
| "remove background from headshot" / "证件照去背景" | ✅ Yes |
| "transparent PNG" / "PNG cutout" | ✅ Yes |
| "remove background from pet photo" | ✅ Yes |
| "batch remove backgrounds" (multiple images) | ✅ Yes — call `remove_bg()` in a loop |

---

## 6. When NOT to use this skill — use image-edit instead

| User says | Use instead |
|-----------|-------------|
| "replace background with a beach" / "换背景" | **image-edit** (`action="replace_bg"`) |
| "blur the background" / "背景虚化" | **image-edit** (`action="edit"`) |
| "change background color to blue" | **image-edit** (`action="replace_bg"`) |
| "edit the image" / "enhance the photo" | **image-edit** |
| "generate an image from text" | **image-create** |

**Key distinction:**
- **image-bg-remove** → **removes** the background → outputs transparent PNG
- **image-edit** (`replace_bg`) → **replaces** the background with a new scene using a general-purpose model

For **background replacement workflows**, the recommended approach is:
1. First use **image-bg-remove** to get a clean transparent cutout
2. Then use **image-edit** (`action="blend"`) to composite onto a new background

This two-step approach produces better results than a single `replace_bg` call because the dedicated RMBG model produces cleaner edges.

---

## 7. Model details

| Property | Value |
|----------|-------|
| Model | `fal-ai/bria/background/remove` (Bria RMBG 2.0) |
| Speed | ~3 seconds |
| Cost | ~$0.01 per image |
| Output | Transparent PNG (RGBA) |
| Input formats | JPEG, PNG, WEBP, BMP |
| Max input size | 10 MB |

This is the **only** image skill that uses a dedicated single-purpose model. All other image skills use nanopro or gpt general-purpose models.

---

## 8. Response format

```json
{
    "success": true,
    "image": {
        "url": "https://fal.media/files/...",
        "local_path": "output/images/20250531_153000_bg_removed.png",
        "size_bytes": 245760,
        "request_id": "abc123"
    },
    "cost": 0.01,
    "duration_s": 3.2
}
```

On error:
```json
{
    "success": false,
    "error": "File not found: uploads/missing.jpg"
}
```

---

## 9. Use case examples

### Portrait background removal (ID photo / headshot)

```python
exec(open('skills/image-bg-remove/remove_bg.py').read())
result = remove_bg(image_path="uploads/headshot.jpg")
if result["success"]:
    print(f"Transparent headshot saved: {result['image']['local_path']}")
```

### Product cutout for e-commerce

```python
exec(open('skills/image-bg-remove/remove_bg.py').read())
result = remove_bg(image_path="uploads/product.jpg")
# Output: transparent PNG ready for white-background product listing
```

### Batch processing multiple images

```python
exec(open('skills/image-bg-remove/remove_bg.py').read())
import glob

images = glob.glob("uploads/products/*.jpg")
for img in images:
    result = remove_bg(image_path=img)
    if result["success"]:
        print(f"✓ {img} → {result['image']['local_path']}")
    else:
        print(f"✗ {img}: {result['error']}")
```

### Background removal + replacement (two-step workflow)

```python
# Step 1: Remove background with dedicated model (better edges)
exec(open('skills/image-bg-remove/remove_bg.py').read())
result = remove_bg(image_path="uploads/portrait.jpg")
transparent_path = result["image"]["local_path"]

# Step 2: Composite onto new background with image-edit
exec(open('skills/image-edit/edit_image.py').read())
final = edit_image(
    image_path=transparent_path,
    prompt="place this person on a tropical beach at sunset",
    action="blend",
)
```

---

## 10. Supported input formats

| Format | Extension | Notes |
|--------|-----------|-------|
| JPEG | `.jpg`, `.jpeg` | Most common input |
| PNG | `.png` | Supports existing alpha channel |
| WebP | `.webp` | Modern web format |
| BMP | `.bmp` | Legacy format |

Maximum file size: 10 MB.

---

## 11. Troubleshooting

| Issue | Solution |
|-------|----------|
| "File not found" | Check the file path is relative to workspace root |
| "Unsupported image format" | Convert to JPEG/PNG/WebP first |
| "Image too large" | Resize to under 10 MB before processing |
| "Submit failed: 401" | Check FAL_KEY env var (local) or sc-proxy config (production) |
| Timeout | Rare — the model usually completes in ~3s. Retry once. |
