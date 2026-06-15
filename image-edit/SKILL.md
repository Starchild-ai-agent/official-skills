---
name: image-edit
version: 1.0.1
description: |
  Image editing and enhancement of an existing image. Covers background replacement, super-resolution upscaling, old photo restoration, colorization, person removal, portrait retouching (skin smoothing, blemish removal), slimming, color grading, artistic filters, image blending, outpainting, local editing, text rendering, multi-angle generation, before/after comparison, car recoloring, car wrap preview.

  Use when editing, enhancing, or transforming an existing image (e.g. remove background, upscale photo, restore old photo, retouch portrait, change car color, apply filter, extend image).
metadata:
  starchild:
    emoji: "✏️"
    skillKey: image-edit
    requires:
      env: [FAL_KEY]
user-invocable: true
disable-model-invocation: false

---

# image-edit

Use this skill for **all image editing and enhancement requests** on Starchild.

Covers: general editing, background replacement, super-resolution, old photo restoration, colorization, person removal, portrait retouching (skin smoothing, blemish removal, teeth whitening), slimming, color grading, artistic filters, image blending, outpainting, local editing, text rendering, multi-angle generation, before/after comparison, car recoloring, car wrap preview, and fitness/medical transformation comparisons.

**Core principle:** call the provided script. Do not re-implement proxy/billing plumbing.

**When to use image-edit vs other image skills:**
- **image-edit** → user wants to EDIT, ENHANCE, or TRANSFORM an existing image
- **image-portrait** → user wants a portrait with their face/identity preserved from a reference photo
- **image-create** → user wants to CREATE something from a text description (no source image)

---

## 1. Quick start — basic edit (most common)

```python
exec(open('skills/image-edit/edit_image.py').read())
result = edit_image(
    image_path="uploads/photo.jpg",
    prompt="make the sky more dramatic with golden sunset colors",
    action="enhance",
)
# result -> {"success": True, "images": [{"local_path": "output/images/..."}], ...}
```

The script reads the local file, base64-encodes it, and sends it to fal.ai as a data URI — no manual URL publishing needed.

## 2. Quick start — public URL

```python
exec(open('skills/image-edit/edit_image.py').read())
result = edit_image(
    image_url="https://example.com/photo.jpg",
    prompt="replace the background with a tropical beach",
    action="replace_bg",
)
```

### Delivering the result to the user — IMPORTANT

**Never hand the user the raw fal.media URL.** fal serves files with restrictive CSP headers. The only reliable delivery path is the **already-downloaded local file**:

1. Use each image's `local_path` (e.g. `output/images/xxx.png`) — the script always downloads on success.
2. Tell the user the files are saved to `output/images/` and viewable in the workspace file panel.
3. On Web channel, embed inline so the user can preview in chat:
   ```markdown
   ![edited](output/images/<filename>.png)
   ```
4. On Telegram / WeChat: send via `send_to_telegram(file_path="output/images/...", message_type="image")` or `send_to_wechat(file_path="output/images/...", message_type="image")`.

---

## 3. Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `image_path` | yes* | — | Local workspace file path to the source image |
| `image_url` | yes* | — | Public HTTPS URL of the source image |
| `prompt` | no | auto | Editing instruction (what to change) |
| `action` | no | `"edit"` | Operation type (see §4) |
| `model` | no | `"nanopro"` | Model: `"nanopro"` (fast ~25s) or `"gpt"` (best quality ~150s) |
| `aspect_ratio` | no | `None` | Output ratio: `1:1`, `3:4`, `4:3`, `9:16`, `16:9`. `None` = preserve original. |

*At least one of `image_path` or `image_url` must be provided. If both are given, `image_path` takes priority.

---

## 4. Actions — operation types

### F: Multi-image / general editing

| Action | Key | Description |
|--------|-----|-------------|
| General edit | `edit` | Modify the image according to the prompt |
| Image blending | `blend` | Place a person/subject into a new background or scene |
| Outpainting | `extend` | Extend the image beyond its current boundaries |
| Local edit | `local_edit` | Modify only a specific region of the image |
| Text rendering | `text_render` | Add or modify text within the image |
| Multi-angle | `multi_angle` | Generate different viewing angles from one photo |
| Before/after | `before_after` | Generate a side-by-side comparison image |

### G: Professional editing

| Action | Key | Description |
|--------|-----|-------------|
| Background replacement | `replace_bg` | Swap the background while keeping the subject |
| Super-resolution | `upscale` | Upscale and enhance image resolution |
| Photo restoration | `restore` | Repair scratches, tears, fading in old photos |
| Colorization | `colorize` | Add realistic colors to black-and-white photos |
| Person removal | `remove_person` | Remove a specific person from the photo |

### V: Retouching / beauty

| Action | Key | Description |
|--------|-----|-------------|
| Portrait retouching | `retouch` | Skin smoothing, blemish removal, teeth whitening |
| Slimming | `slim` | Adjust facial and body proportions subtly |
| Enhancement | `enhance` | Color correction, lighting improvement, quality boost |
| Artistic filter | `filter` | Apply a specific artistic style or filter effect |

### W: Medical / fitness comparison

| Action | Key | Description |
|--------|-----|-------------|
| Transformation comparison | `comparison` | Before/after for medical, fitness, or transformation |

### X: Automotive

| Action | Key | Description |
|--------|-----|-------------|
| Car recolor | `car_color` | Change the color of a vehicle |
| Car wrap preview | `car_wrap` | Visualize a wrap or film on a vehicle |

---

## 5. Model selection guide

| Model | Key | Speed | Quality | Best for |
|-------|-----|-------|---------|----------|
| NanoPro | `nanopro` | ~25s | Good | Default for all requests. Fast iteration. |
| GPT Image 2 | `gpt` | ~150s | Best | When user explicitly asks for "highest quality" or "best quality". Complex edits. |

**Decision rules:**
1. **Default:** always use `nanopro` unless the user explicitly requests higher quality.
2. **Use `gpt` when:** user says "highest quality", "best quality", "premium", or the edit requires very precise detail preservation (e.g., complex text rendering, fine inpainting).
3. **Use `nanopro` when:** user wants fast results, is iterating on edits, or the edit is straightforward.

```python
# Default (fast)
result = edit_image(image_path="photo.jpg", prompt="remove background", action="replace_bg")

# High quality (user requested)
result = edit_image(image_path="photo.jpg", prompt="remove background", action="replace_bg", model="gpt")
```

---

## 6. Intent recognition guide

Use this table to map user requests to the correct action:

### General editing

| User says | Action | Prompt hint |
|-----------|--------|-------------|
| "edit this photo", "modify this image" | `edit` | Pass user's instruction as prompt |
| "put me on a beach", "change the scene" | `blend` | Describe the target scene |
| "extend the image", "make it wider", "outpaint" | `extend` | Describe what to add |
| "change just the shirt color", "edit only the sky" | `local_edit` | Specify the region and change |
| "add text", "write 'Hello' on the image" | `text_render` | Specify text content and placement |
| "show from the side", "different angle" | `multi_angle` | Describe the desired angle |
| "before and after", "show the difference" | `before_after` | Describe the transformation |

### Professional editing

| User says | Action | Prompt hint |
|-----------|--------|-------------|
| "remove background", "change background", "换背景" | `replace_bg` | Describe the new background |
| "upscale", "make it higher resolution", "enhance quality" | `upscale` | Optionally specify target quality |
| "restore old photo", "fix this damaged photo", "修复老照片" | `restore` | Describe specific damage to fix |
| "colorize", "add color to B&W photo", "上色" | `colorize` | Optionally describe expected colors |
| "remove this person", "P掉某人" | `remove_person` | Describe which person to remove |

### Retouching / beauty

| User says | Action | Prompt hint |
|-----------|--------|-------------|
| "retouch", "smooth skin", "remove blemishes", "磨皮美白" | `retouch` | Specify retouching level |
| "make me thinner", "slim face", "瘦脸" | `slim` | Specify areas to adjust |
| "enhance colors", "improve lighting", "调色" | `enhance` | Describe desired look |
| "apply filter", "make it look vintage", "滤镜" | `filter` | Describe the filter style |

### Medical / fitness

| User says | Action | Prompt hint |
|-----------|--------|-------------|
| "before and after surgery", "fitness transformation" | `comparison` | Describe the transformation context |

### Automotive

| User says | Action | Prompt hint |
|-----------|--------|-------------|
| "change car color", "make it red", "汽车改色" | `car_color` | Specify the target color and finish |
| "car wrap", "vinyl wrap preview", "贴膜预览" | `car_wrap` | Describe wrap material and color |

---

## 7. Prompt engineering best practices

### The prompt template system

Every action has a built-in prompt template that wraps the user's instruction for optimal results. You only need to pass the user's specific intent — the template adds the technical quality instructions automatically.

For example, if the user says "make the background a sunset beach":
```python
result = edit_image(
    image_path="photo.jpg",
    prompt="a beautiful sunset beach with palm trees and golden light",
    action="replace_bg",
)
# The script wraps this into: "Replace the background of this image: a beautiful
# sunset beach with palm trees and golden light. Keep the foreground subject
# perfectly intact with clean edges. Match the lighting direction..."
```

### Key principles (from reference skills)

1. **Be specific about the change** — vague prompts produce poor results:
   - ❌ "make it better"
   - ✅ "increase contrast, add warm golden tones, sharpen details"

2. **Describe what to preserve** — especially for local edits:
   - ❌ "change the shirt"
   - ✅ "change the shirt color to navy blue, keep the same fabric texture and wrinkles"

3. **Specify materials and finishes** — for car and product edits:
   - ❌ "make it blue"
   - ✅ "deep metallic blue with a glossy clear coat finish"

4. **Reference real-world styles** — for filters and artistic effects:
   - ❌ "make it artistic"
   - ✅ "apply a warm cinematic color grade like Wes Anderson films"

5. **Describe the era for restoration/colorization**:
   - ❌ "colorize this"
   - ✅ "colorize this 1940s family portrait with period-appropriate clothing colors"

6. **For retouching, specify the level**:
   - Light: "subtle skin smoothing, keep natural texture"
   - Medium: "professional retouching, remove blemishes, even skin tone"
   - Heavy: "full beauty retouching, smooth skin, brighten eyes, whiten teeth"

---

## 8. Usage examples by scenario

### Background replacement

```python
exec(open('skills/image-edit/edit_image.py').read())

# Simple background swap
result = edit_image(
    image_path="uploads/portrait.jpg",
    prompt="a modern office with floor-to-ceiling windows and city skyline view",
    action="replace_bg",
)

# Studio background
result = edit_image(
    image_path="uploads/product.jpg",
    prompt="clean white studio background with soft shadow",
    action="replace_bg",
)
```

### Old photo restoration

```python
# Repair damaged photo
result = edit_image(
    image_path="uploads/old_family_photo.jpg",
    prompt="repair all scratches, tears, and stains; restore faded colors; enhance clarity",
    action="restore",
)

# Colorize black-and-white photo
result = edit_image(
    image_path="uploads/grandpa_1945.jpg",
    prompt="colorize with historically accurate colors for 1940s era, natural skin tones, period-appropriate clothing",
    action="colorize",
)
```

### Portrait retouching

```python
# Professional retouching
result = edit_image(
    image_path="uploads/selfie.jpg",
    prompt="professional portrait retouching: smooth skin while keeping natural texture, remove blemishes, subtle teeth whitening, brighten eyes",
    action="retouch",
)

# Slimming
result = edit_image(
    image_path="uploads/photo.jpg",
    prompt="subtle facial slimming, slightly more defined jawline, natural proportions",
    action="slim",
)
```

### Image enhancement

```python
# Color grading
result = edit_image(
    image_path="uploads/landscape.jpg",
    prompt="cinematic color grading with warm golden tones, enhanced contrast, vibrant but natural colors",
    action="enhance",
)

# Artistic filter
result = edit_image(
    image_path="uploads/photo.jpg",
    prompt="oil painting style with visible brushstrokes, rich warm palette, impressionist feel",
    action="filter",
)
```

### Super-resolution upscaling

```python
result = edit_image(
    image_path="uploads/low_res.jpg",
    prompt="upscale to maximum quality, enhance fine details, reduce noise and compression artifacts",
    action="upscale",
)
```

### Person removal

```python
result = edit_image(
    image_path="uploads/group_photo.jpg",
    prompt="remove the person on the far right, fill with the park background seamlessly",
    action="remove_person",
)
```

### Outpainting (image extension)

```python
result = edit_image(
    image_path="uploads/cropped.jpg",
    prompt="extend the image to the left and right, continuing the mountain landscape naturally",
    action="extend",
    aspect_ratio="16:9",
)
```

### Car customization

```python
# Car recolor
result = edit_image(
    image_path="uploads/my_car.jpg",
    prompt="change to a deep cherry red metallic paint with glossy clear coat",
    action="car_color",
)

# Car wrap preview
result = edit_image(
    image_path="uploads/my_car.jpg",
    prompt="matte black vinyl wrap with carbon fiber accents on the hood and mirrors",
    action="car_wrap",
)
```

### Before/after comparison

```python
# Fitness transformation
result = edit_image(
    image_path="uploads/fitness_photo.jpg",
    prompt="create a fitness transformation comparison showing a more toned and fit version",
    action="comparison",
)
```

### Local editing

```python
# Change specific element
result = edit_image(
    image_path="uploads/outfit.jpg",
    prompt="change only the dress color from red to emerald green, keep the same fabric texture",
    action="local_edit",
)
```

### Text rendering

```python
result = edit_image(
    image_path="uploads/poster_bg.jpg",
    prompt="add the text 'SUMMER SALE' in bold white letters centered at the top, with a subtle drop shadow",
    action="text_render",
)
```

### High quality edit

```python
# Use GPT model for best quality
result = edit_image(
    image_path="uploads/important_photo.jpg",
    prompt="professional color correction and enhancement for print publication",
    action="enhance",
    model="gpt",
)
```

---

## 9. Provided scripts

| File | Purpose |
|------|---------|
| `edit_image.py` | Core script: resolve image → build prompt → submit → poll → download. Handles local files (base64) and URLs, all actions, two models. |
| `exports.py` | Re-exports `edit_image`, `ACTIONS`, `ACTION_PROMPTS`, `MODELS` for programmatic use by other skills. |
| `_cost_track.py` | Cost tracking helper — records per-call costs via sc-proxy headers. |

---

## 10. Local testing

Set `FAL_KEY` env var to call fal.ai directly (bypasses sc-proxy):

```bash
# Basic edit
FAL_KEY=your-fal-key python3 skills/image-edit/edit_image.py photo.jpg "make it brighter" enhance nanopro

# Args: <image_path_or_url> [prompt] [action] [model]
```

---

## 11. Troubleshooting

| Problem | Fix |
|---------|-----|
| `File not found: ...` | Check the workspace path; the file must exist |
| `Unsupported image format` | Use `.jpg`, `.jpeg`, `.png`, `.webp`, or `.bmp` |
| `Image too large` | Resize to under 10 MB before uploading |
| `image_url must be a public HTTP(S) URL` | Use `image_path` for local files, or provide a valid `https://` URL |
| `Unknown action` | Check valid actions in §4 |
| `HTTP 402 insufficient_credits` | Top up balance; cost is pre-charged on submit |
| `HTTP 403 endpoint_not_allowed` | sc-proxy only allows approved fal endpoints; contact admin |
| Edit `FAILED` upstream | Simplify prompt, ensure source image is clear, retry |
| Job stuck `IN_PROGRESS` >10 min | Save `request_id`, retry later |
| Poor edit quality | Try `model="gpt"` for higher quality; be more specific in prompt |
| Background not fully removed | Use `replace_bg` action with explicit background description |
| Retouching looks unnatural | Add "keep natural texture" or "subtle" to prompt |

---

## 12. Infrastructure (reference)

- Caller → `sc-proxy` → `queue.fal.run/{model}` → fal model providers
- All requests must include `Authorization: Key fake-falai-key-12345` (proxy injects the real `FAL_KEY`)
- Pre-charge happens at submit. Poll/result calls are free.
- Local files are base64-encoded as data URIs — no separate upload step needed.
- Final images live at `https://*.fal.media/...` — public CDN, no auth needed for download.
- Cost tracking via `_cost_track.py` — records `X-Credits-Used` from sc-proxy response headers.

### Model endpoints

| Model | Edit endpoint |
|-------|--------------|
| nanopro | `fal-ai/nano-banana-pro/edit` |
| gpt | `openai/gpt-image-2/edit` |

---
