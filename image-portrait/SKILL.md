---
name: image-portrait
version: 1.0.1
description: |
  Identity-consistent portrait generation from a reference photo. Covers professional headshots, dating photos, style transfers, themed portraits, photo series, avatars, ID photos.

  Use when generating styled portraits from a reference photo (e.g. professional headshot, anime avatar, cyberpunk portrait, travel photo, dating profile photo, ID photo).
metadata:
  starchild:
    emoji: "📸"
    skillKey: image-portrait
    requires:
      env: [FAL_KEY]
user-invocable: true
disable-model-invocation: false

---

# image-portrait

Use this skill for **all identity-consistent portrait generation requests** on Starchild.

Covers: professional headshots, dating/social photos, artistic style transfers, themed/holiday portraits, photo series, digital avatars, children/family photos, ID/passport photos.

**Core principle:** call the provided script. Do not re-implement proxy/billing plumbing.

---

## 1. Quick start — single portrait (most common)

```python
exec(open('skills/image-portrait/generate_portrait.py').read())
result = generate_portrait(
    image_path="path/to/user/photo.jpg",
    style="professional",
)
# result -> {"success": True, "images": [{"local_path": "output/images/..."}], ...}
```

The script reads the local file, base64-encodes it, and sends it to fal.ai as a data URI — no manual URL publishing needed.

## 2. Quick start — public URL

```python
exec(open('skills/image-portrait/generate_portrait.py').read())
result = generate_portrait(
    face_image_url="https://example.com/photo.jpg",
    style="anime",
)
```

## 3. Quick start — text-to-image (no reference photo)

```python
exec(open('skills/image-portrait/generate_portrait.py').read())
result = generate_portrait(
    prompt="a young woman in cyberpunk armor, neon city background, rain",
    model="nanopro",
)
```

When no `image_path` or `face_image_url` is provided, the script uses the text-to-image endpoint (no `/edit` suffix).

### Delivering the result to the user — IMPORTANT

**Never hand the user the raw fal.media URL.** fal serves files with restrictive CSP headers. The only reliable delivery path is the **already-downloaded local file**:

1. Use each image's `local_path` (e.g. `output/images/xxx.png`) — the script always downloads on success.
2. Tell the user the files are saved to `output/images/` and viewable in the workspace file panel.
3. On Web channel, embed inline so the user can preview in chat:
   ```markdown
   ![photo](output/images/<filename>.png)
   ```
4. On Telegram / WeChat: send via `send_to_telegram(file_path="output/images/...", message_type="image")` or `send_to_wechat(file_path="output/images/...", message_type="image")`.

---

## 4. Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `image_path` | no | — | Local workspace file path to the user's face photo |
| `face_image_url` | no | — | Public HTTPS URL of the user's face photo |
| `style` | no | `"professional"` | Preset style key (see §5) |
| `scene` | no | `None` | Custom scene description (appended to style prompt) |
| `prompt` | no | `None` | Fully custom prompt — overrides style+scene when set |
| `model` | no | `"nanopro"` | Model: `"nano2"` (fastest ~15s), `"nanopro"` (balanced ~25s, default), or `"gpt"` (best quality ~150s) |
| `count` | no | `1` | Number of images to generate (1–8) |
| `aspect_ratio` | no | `"1:1"` | Output ratio: `1:1`, `3:4`, `4:3`, `9:16`, `16:9` |

**Image input rules:**
- Provide `image_path` OR `face_image_url` for identity-consistent generation (edit mode).
- If both are given, `image_path` takes priority.
- Omit both for pure text-to-image generation (generate mode).

**Prompt priority:** `prompt` > `style + scene` > `style` > default (`professional`).

---

## 5. Style presets

### A: Identity-consistent character styles

| Style | Key | Best for |
|-------|-----|----------|
| Professional headshot | `professional` | LinkedIn, resume, corporate |
| Artistic portrait | `artistic` | Creative portfolio, gallery |
| Anime | `anime` | Social media, fun avatar |
| Cyberpunk | `cyberpunk` | Gaming profile, sci-fi fan |
| Oil painting | `oil_painting` | Art gift, classical look |
| Watercolor | `watercolor` | Soft artistic portrait |
| Vintage | `vintage` | Retro aesthetic, nostalgia |
| Casual lifestyle | `casual` | Social media, personal blog |

### B: Personal showcase / dating / social

| Style | Key | Best for |
|-------|-----|----------|
| Dating — cafe | `dating_cafe` | Dating app, warm vibe |
| Dating — beach | `dating_beach` | Dating app, summer vibe |
| Dating — city | `dating_city` | Dating app, urban vibe |
| Dating — restaurant | `dating_restaurant` | Dating app, elegant vibe |
| Travel — Europe | `travel_europe` | Travel blog, social media |
| Travel — Japan | `travel_japan` | Travel blog, cultural |
| Travel — tropical | `travel_tropical` | Vacation, resort |
| Sports — gym | `sports_gym` | Fitness profile |
| Sports — running | `sports_running` | Athletic profile |
| Social media | `social_media` | Instagram, TikTok |
| LinkedIn | `linkedin` | Professional networking |
| Personal brand | `personal_brand` | Entrepreneur, creator |

### D: Themed / scene portraits

| Style | Key | Best for |
|-------|-----|----------|
| Christmas | `christmas` | Holiday greeting, social |
| Halloween | `halloween` | Holiday fun |
| Graduation | `graduation` | Milestone celebration |
| Wedding | `wedding` | Wedding planning, save-the-date |
| Business speech | `business_speech` | Speaker profile |
| Musician | `musician` | Music promotion |
| Chef | `chef` | Food blog, restaurant |
| Outdoor adventure | `outdoor_adventure` | Adventure blog |
| Pet together | `pet_together` | Pet lover profile |
| Reading | `reading` | Book club, literary |
| Night city | `night_city` | Urban lifestyle |
| Hanfu (Chinese traditional) | `hanfu` | Cultural, cosplay |

### O: Digital avatar

| Style | Key | Best for |
|-------|-----|----------|
| 3D cartoon | `avatar_3d` | Social avatar, Pixar style |
| Gaming avatar | `avatar_gaming` | Game profile, RPG |
| VTuber | `avatar_vtuber` | Streaming, VTuber |

### T: Children & family

| Style | Key | Best for |
|-------|-----|----------|
| Child portrait | `child_portrait` | Family keepsake |
| Family photo | `family_photo` | Family portrait |

### U: ID / passport photos

| Style | Key | Best for |
|-------|-----|----------|
| ID photo (white bg) | `id_photo_white` | Passport, driver's license |
| ID photo (blue bg) | `id_photo_blue` | Visa, work permit |

---

## 6. Model selection guide

| Model | Key | Speed | Quality | Best for |
|-------|-----|-------|---------|----------|
| Nano Banana 2 | `nano2` | ~15s | Good | Quick drafts, fast iteration, bulk generation. |
| NanoPro | `nanopro` | ~25s | Better | Default for all requests. Balanced speed and quality. |
| GPT Image 2 | `gpt` | ~150s | Best | When user explicitly asks for "highest quality" or "best quality". Complex scenes. |

**Decision rules:**
1. **Default:** always use `nanopro` unless the user explicitly requests otherwise.
2. **Use `nano2` when:** user wants fastest results, is iterating on styles, generating many images, or says "quick", "draft", "fast".
3. **Use `gpt` when:** user says "highest quality", "best quality", "premium", or the scene is very complex with many specific details.

```python
# Default (fast)
result = generate_portrait(image_path="photo.jpg", style="anime")

# High quality (user requested)
result = generate_portrait(image_path="photo.jpg", style="anime", model="gpt")
```

---

## 7. Custom scene examples

```python
# Style + custom scene
result = generate_portrait(
    image_path="uploads/my_photo.jpg",
    style="professional",
    scene="in a modern office with city skyline view",
)

# Custom scene only (defaults to professional style base)
result = generate_portrait(
    image_path="uploads/my_photo.jpg",
    scene="standing on a beach at sunset, golden hour lighting",
)

# Fully custom prompt (overrides everything)
result = generate_portrait(
    image_path="uploads/my_photo.jpg",
    prompt="portrait of a person as a medieval knight, full plate armor, castle background, dramatic lighting, oil painting style",
)

# Different aspect ratio
result = generate_portrait(
    image_path="uploads/my_photo.jpg",
    style="cyberpunk",
    aspect_ratio="9:16",
)

# Multiple images
result = generate_portrait(
    image_path="uploads/my_photo.jpg",
    style="dating_cafe",
    count=4,
)
```

---

## 8. Prompt engineering best practices

When the user's request doesn't match any preset style, or when you need to construct a custom `prompt`, follow these guidelines (derived from reference skills: ai-headshot-generation, ai-avatar-generation, style-transfer, portrait-enhancement, character-design-sheet, avatar-portrait, nano-banana-pro, pet-portrait-generation).

### Automatic likeness preservation

When a reference image is provided (edit mode), the script **automatically prepends** a likeness preservation instruction to every prompt. This ensures the generated portrait preserves the subject's facial identity. You do NOT need to add likeness instructions manually — the script handles it.

Exception: avatar styles (`avatar_3d`, `avatar_gaming`, `avatar_vtuber`) skip the likeness prefix because stylization takes priority over photographic likeness.

### The 7-element prompt structure

Every effective portrait prompt should include these elements (from nano-banana-pro skill):

```
[subject], [outfit/attire], [pose/action], [expression], [background/setting], [lighting], [style/quality modifiers]
```

### Key principles

1. **Likeness vs. style balance** (from avatar-portrait skill):
   - Too photorealistic = ignores requested style
   - Too stylized = loses resemblance to source person
   - For stylized portraits: emphasize "stylized but maintains individual features"
   - For photorealistic: emphasize "keep facial features recognizable"

2. **Lighting is critical** — always specify lighting type:
   - Studio: "soft diffused studio lighting", "Rembrandt chiaroscuro lighting"
   - Natural: "golden hour warm light", "dappled sunlight through trees"
   - Dramatic: "dramatic rim lighting", "volumetric light beams", "neon glow"
   - Flat: "even flat lighting with no shadows" (for ID photos)

3. **Background specificity** — vague backgrounds produce poor results:
   - ❌ "nice background"
   - ✅ "blurred modern office with glass windows and city view"
   - ✅ "clean neutral gray gradient studio background"
   - ✅ "background style should match the character style" (for avatars)

4. **Lens/camera hints** — help the model understand framing:
   - "85mm lens look, shallow depth of field" (portrait)
   - "head and shoulders framing" (headshot)
   - "full body, clean white background" (character design)
   - "close-up face, portrait orientation" (expression/avatar)

5. **Quality anchors** — add style quality references:
   - "professional photography quality", "magazine cover quality"
   - "National Geographic photography style" (adventure)
   - "League of Legends splash art style" (gaming)
   - "Pixar and Disney animation style" (3D avatar)
   - "Studio Ghibli inspired" (anime)
   - "fine art watercolor painting look" (watercolor)

6. **Texture and material** — for artistic styles, specify medium:
   - "visible impasto brushstrokes, canvas texture" (oil painting)
   - "loose expressive watercolor style, soft edges, beautiful color bleeds and washes" (watercolor)
   - "natural film grain, Kodak Portra emulation" (vintage)
   - "cel-shaded, clean line art, bold outlines" (anime)
   - "visible pixels but NOT a pixelated photo filter" (pixel art)

7. **Expression guidance** — be specific about mood:
   - ❌ "smiling"
   - ✅ "warm genuine smile, confident approachable expression"
   - ✅ "neutral calm expression with mouth closed" (ID photo)
   - ✅ "passionate expression, energetic" (musician)

### Example: building a custom prompt

User: "I want a photo of me as a wizard in a magical forest"

```python
result = generate_portrait(
    image_path="uploads/photo.jpg",
    prompt=(
        "fantasy wizard portrait, wearing mystical purple robes with glowing runes, "
        "ancient wooden staff with crystal orb, wise powerful expression, "
        "enchanted forest background with bioluminescent plants and floating particles, "
        "dramatic magical lighting with ethereal glow, "
        "high fantasy art style, detailed digital painting quality"
    ),
)
# Note: likeness prefix is auto-added because image_path is provided
```

### Example: pixel art avatar (from avatar-portrait skill)

User: "Make me a retro pixel art avatar"

```python
result = generate_portrait(
    image_path="uploads/photo.jpg",
    prompt=(
        "retro 16-bit pixel art portrait, visible pixels with clean lines, "
        "rich colors, consistent shading, stylized but maintains individual features, "
        "warm sunset cityscape background in matching pixel art style, "
        "head and shoulders, square format"
    ),
)
```

---

## 9. Photo series

Generate a coordinated set of themed portraits in one call. Pass a custom list of styles/scenes — the agent assembles the list based on the user's request.

```python
exec(open('skills/image-portrait/generate_portrait.py').read())
result = generate_series(
    image_path="uploads/my_photo.jpg",
    series=[
        {"style": "professional"},
        {"style": "casual", "scene": "at a rooftop bar, sunset"},
        {"style": "anime"},
        {"prompt": "portrait as a superhero, cape flowing, city skyline"},
    ],
)
# result -> {"success": True, "images": [...4 images...], "series": "custom"}
```

Each item in the list is a dict with optional keys:
- `style` — any style key from §7 (e.g. `"professional"`, `"anime"`, `"cyberpunk"`)
- `scene` — override the scene description (combined with the style template)
- `prompt` — fully custom prompt (ignores style/scene)

---

## 10. Intent recognition guide

Use this table to map user requests to the correct style/parameters:

| User says | Style | Notes |
|-----------|-------|-------|
| "professional photo", "headshot", "LinkedIn photo" | `professional` or `linkedin` | |
| "dating photo", "dating app", "Tinder photo" | `dating_cafe` / `dating_beach` / `dating_city` | Ask which vibe |
| "anime me", "anime version", "cartoon me" | `anime` | |
| "cyberpunk", "sci-fi portrait" | `cyberpunk` | |
| "oil painting", "classical portrait" | `oil_painting` | |
| "watercolor portrait" | `watercolor` | |
| "vintage photo", "retro" | `vintage` | |
| "casual photo", "lifestyle" | `casual` | |
| "travel photo in Paris/Europe" | `travel_europe` | |
| "travel photo in Japan/Tokyo/Kyoto" | `travel_japan` | |
| "beach photo", "tropical" | `travel_tropical` or `dating_beach` | |
| "gym photo", "fitness" | `sports_gym` | |
| "Christmas photo" | `christmas` | |
| "Halloween photo" | `halloween` | |
| "graduation photo" | `graduation` | |
| "wedding photo" | `wedding` | |
| "chef photo", "cooking" | `chef` | |
| "musician", "on stage" | `musician` | |
| "with my dog/pet" | `pet_together` | |
| "reading", "bookish" | `reading` | |
| "night city", "urban night" | `night_city` | |
| "hanfu", "Chinese traditional" | `hanfu` | |
| "3D avatar", "Pixar style" | `avatar_3d` | |
| "gaming avatar", "RPG character" | `avatar_gaming` | |
| "VTuber avatar" | `avatar_vtuber` | |
| "kid photo", "children's portrait" | `child_portrait` | |
| "family photo" | `family_photo` | |
| "passport photo", "ID photo" | `id_photo_white` | White bg default |
| "visa photo" | `id_photo_blue` | Blue bg |
| "photo series", "set of photos" | Use `generate_series()` | Assemble custom list from styles |
| "highest quality", "best quality" | Any style + `model="gpt"` | |
| Custom scene not in presets | Use `scene=` or `prompt=` | |

---

## 11. Provided scripts

| File | Purpose |
|------|---------|
| `generate_portrait.py` | Core script: submit → poll → download. Handles local files (base64) and URLs, all styles, custom scenes, three models (nano2/nanopro/gpt). |
| `exports.py` | Re-exports `generate_portrait`, `generate_series`, `STYLE_PROMPTS` for programmatic use by other skills. |
| `_cost_track.py` | Cost tracking helper — records per-call costs via sc-proxy headers. |

---

## 12. Local testing

Set `FAL_KEY` env var to call fal.ai directly (bypasses sc-proxy):

```bash
# Single portrait
FAL_KEY=your-fal-key python3 skills/image-portrait/generate_portrait.py photo.jpg anime 1 nanopro

# Args: <image_path_or_url> [style] [count] [model]
```

---

## 13. Troubleshooting

| Problem | Fix |
|---------|-----|
| `File not found: ...` | Check the workspace path; the file must exist |
| `Unsupported image format` | Use `.jpg`, `.jpeg`, `.png`, `.webp`, or `.bmp` |
| `Image too large` | Resize to under 10 MB before uploading |
| `face_image_url must be a public HTTP(S) URL` | Use `image_path` for local files, or provide a valid `https://` URL |
| `HTTP 402 insufficient_credits` | Top up balance; cost is pre-charged on submit |
| `HTTP 403 endpoint_not_allowed` | sc-proxy only allows approved fal endpoints; contact admin |
| Generation `FAILED` upstream | Simplify prompt, ensure face photo is clear and well-lit, retry |
| Job stuck `IN_PROGRESS` >10 min | Save `request_id`, retry later |
| Poor face consistency | Use a clear, front-facing photo with good lighting; avoid group photos |
| `gpt` model too slow | Switch to `nanopro` (default) for faster results |

---

## 14. Infrastructure (reference)

- Caller → `sc-proxy` → `queue.fal.run/{model}` → fal model providers
- All requests must include `Authorization: Key fake-falai-key-12345` (proxy injects the real `FAL_KEY`)
- Pre-charge happens at submit. Poll/result calls are free.
- Local files are base64-encoded as data URIs — no separate upload step needed.
- Final images live at `https://*.fal.media/...` — public CDN, no auth needed for download.
- Cost tracking via `_cost_track.py` — records `X-Credits-Used` from sc-proxy response headers.

### Model endpoints

| Model | Edit (with ref image) | Generate (text only) |
|-------|----------------------|---------------------|
| nano2 | `fal-ai/nano-banana-2/edit` | `fal-ai/nano-banana-2` |
| nanopro | `fal-ai/nano-banana-pro/edit` | `fal-ai/nano-banana-pro` |
| gpt | `openai/gpt-image-2/edit` | `openai/gpt-image-2` |

---
