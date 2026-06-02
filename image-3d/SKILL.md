---
name: image-3d
version: 1.0.0
description: |
  3D-style image generation: 3D characters, product renders, isometric dioramas, 3D icons, 3D text, interior design renders, architectural visualization, 3D scenes, game assets.

  Use when generating 3D-style 2D images from text descriptions or reference photos (e.g. 3D character design, isometric diorama, 3D product render, interior design visualization, architectural render, 3D app icon, 3D text effect, game asset render).
metadata:
  starchild:
    emoji: "🧊"
    skillKey: image-3d
    requires:
      env: [FAL_KEY]
user-invocable: true
disable-model-invocation: false

---

# image-3d

Use this skill for **all 3D-style image generation requests** on Starchild.

Covers: 3D character design (chibi, realistic, cartoon, fantasy), 3D product renders (floating, exploded, turntable), isometric dioramas & miniature scenes, 3D app icons (iOS, Material, game), 3D text effects (chrome, neon, wood, candy), interior design visualization (modern, luxury, cozy, industrial), architectural rendering (modern, traditional, futuristic, aerial, night), 3D scenes (fantasy, sci-fi, nature, urban), and game asset renders (weapons, environments, props, vehicles).

**Core principle:** call the provided script. Do not re-implement proxy/billing plumbing.

**⚠️ Important distinction — 3D-style images vs 3D model files:**
- **This skill** generates **3D-style 2D images** (PNG/JPG) — rendered pictures that *look* 3D
- This skill does **NOT** produce 3D model files (.glb, .obj, .fbx, .usdz)
- For actual 3D model files, users need dedicated 3D modeling services (Meshy, etc.)

**When to use image-3d vs other image skills:**
- **image-3d** → user wants a 3D-rendered look: 3D characters, isometric scenes, 3D icons, architectural renders, interior design renders, 3D text effects
- **image-create** → user wants general creative images (logos, posters, illustrations, memes) — image-create has a basic `3d` category, but image-3d offers far more granular control
- **image-ecommerce** → user wants product photos for e-commerce listings (white background, lifestyle shots)
- **image-edit** → user wants to edit/transform an existing image
- **image-portrait** → user wants a portrait with face/identity preserved

---

## 1. Quick start — text-to-3D image (most common)

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    prompt="a cute robot assistant with big eyes and antenna",
    category="character",
    style="chibi",
)
# result -> {"success": True, "images": [{"local_path": "output/images/..."}], ...}
```

## 2. Quick start — category + style only (no custom prompt)

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    category="diorama",
    style="isometric",
)
# Uses the built-in style template as the full prompt
```

## 3. Quick start — reference image → 3D style

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    prompt="transform into a 3D rendered character",
    reference_path="uploads/sketch.jpg",
    category="character",
    style="cartoon",
)
```

### Delivering the result to the user — IMPORTANT

**Never hand the user the raw fal.media URL.** fal serves files with restrictive CSP headers. The only reliable delivery path is the **already-downloaded local file**:

1. Use each image's `local_path` (e.g. `output/images/xxx.png`) — the script always downloads on success.
2. Tell the user the files are saved to `output/images/` and viewable in the workspace file panel.
3. On Web channel, embed inline so the user can preview in chat:
   ```markdown
   ![3d-render](output/images/<filename>.png)
   ```
4. On Telegram / WeChat: send via `send_to_telegram(file_path="output/images/...", message_type="image")` or `send_to_wechat(file_path="output/images/...", message_type="image")`.

---

## 4. Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `prompt` | yes* | — | Text description of the desired 3D image |
| `reference_path` | no | — | Local file path to a reference image (for 3D stylization) |
| `reference_url` | no | — | Public HTTPS URL of a reference image |
| `category` | no | `"character"` | 3D category preset (see §5) |
| `style` | no | `"default"` | Sub-style within the category (see §5) |
| `model` | no | `"nanopro"` | Model: `"nanopro"` (fast ~25s) or `"gpt"` (best quality ~150s) |
| `count` | no | `1` | Number of images to generate (1–4) |
| `aspect_ratio` | no | auto | Output ratio: `1:1`, `3:4`, `4:3`, `9:16`, `16:9`. Auto-selected by category if not set. |

*A `prompt` is required for text-to-image mode unless a non-default `style` is specified (which provides a built-in template).

**Prompt priority:** `prompt + category/style` (enhanced) > `prompt` only > `category + style` template > `category` default.

**Aspect ratio auto-selection:** When not explicitly set, the script picks the best ratio for the category:
- `3:4` for characters (portrait orientation)
- `1:1` for products, dioramas, icons, game assets (square showcase)
- `16:9` for text, interiors, architecture, scenes (wide cinematic)

---

## 5. Categories and style presets

### N: 3D Character (`category="character"`)

| Style | Key | Best for |
|-------|-----|----------|
| Chibi / Pixar | `chibi` | Cute stylized characters, mascots, avatars |
| Realistic | `realistic` | Game-ready characters, detailed anatomy |
| Cartoon | `cartoon` | Disney/Pixar style, family-friendly |
| Fantasy | `fantasy` | RPG characters, warriors, mages |
| General | `default` | Any 3D character |

**Character prompt tips:**
- Describe pose, outfit, expression, and accessories
- Specify "white background" or "clean background" for character sheets
- For game characters, mention "T-pose" or "action pose"
- Example: `"a female elf ranger with green cloak, holding a bow, forest background"`

### N: 3D Product Render (`category="product"`)

| Style | Key | Best for |
|-------|-----|----------|
| Floating 3/4 angle | `floating` | Hero product shots, marketing |
| Exploded view | `exploded` | Technical illustration, internal structure |
| Turntable / 360° | `turntable` | Multi-angle showcase |
| General | `default` | Any product render |

**Product prompt tips:**
- Describe material (matte, glossy, metallic, wood, glass)
- Specify lighting (studio, dramatic, soft, rim light)
- Mention the product type and key features
- Example: `"wireless earbuds in charging case, matte white, floating angle"`

### N: 3D Diorama / Isometric (`category="diorama"`)

| Style | Key | Best for |
|-------|-----|----------|
| Isometric | `isometric` | Miniature worlds, city blocks, game maps |
| Low-poly | `lowpoly` | Stylized scenes, indie game aesthetic |
| Realistic | `realistic` | Architectural models, detailed miniatures |
| General | `default` | Any diorama scene |

**Diorama prompt tips:**
- Describe the scene contents (buildings, trees, characters, vehicles)
- Mention scale ("miniature", "tiny", "dollhouse")
- Specify mood (warm, cozy, dramatic, whimsical)
- Example: `"a cozy Japanese ramen shop at night, tiny customers inside, warm glow"`

### N: 3D Icon (`category="icon"`)

| Style | Key | Best for |
|-------|-----|----------|
| iOS style | `ios` | Apple App Store icons, glossy glass |
| Material Design | `material` | Google Play icons, flat with depth |
| Game icon | `game` | RPG items, fantasy game UI |
| General | `default` | Any 3D icon |

**Icon prompt tips:**
- Describe the icon subject simply (one main element)
- Specify the shape context ("rounded square", "circular")
- Keep it simple — icons should be recognizable at small sizes
- Example: `"a camera icon with rainbow lens flare"`

### N: 3D Text (`category="text"`)

| Style | Key | Best for |
|-------|-----|----------|
| Chrome / Metallic | `chrome` | Bold titles, movie-style text |
| Neon glow | `neon` | Cyberpunk, nightlife, signs |
| Wood | `wood` | Rustic, craft, natural brands |
| Candy | `candy` | Playful, kids, sweet themes |
| General | `default` | Any 3D text effect |

**Text prompt tips:**
- ⚠️ AI text rendering is unreliable — keep text SHORT (1-3 words max)
- Describe the text content in quotes: `"the word 'HELLO'"`
- Specify material and environment
- Example: `"the word 'GAME OVER' in chrome metallic letters, dark background"`

### L: Interior Design (`category="interior"`)

| Style | Key | Best for |
|-------|-----|----------|
| Modern minimalist | `modern` | Scandinavian, clean lines, natural light |
| Luxury | `luxury` | High-end, marble, gold accents |
| Cozy / Hygge | `cozy` | Warm, comfortable, inviting |
| Industrial | `industrial` | Loft, exposed brick, urban chic |
| General | `default` | Any interior render |

**Interior prompt tips:**
- Describe the room type (living room, bedroom, kitchen, bathroom, office)
- Mention key furniture and materials
- Specify lighting (natural daylight, warm evening, dramatic)
- Specify color palette if important
- Example: `"modern Scandinavian living room with large windows, light wood floors, gray sofa, indoor plants"`

### L: Architecture (`category="architecture"`)

| Style | Key | Best for |
|-------|-----|----------|
| Modern | `modern` | Contemporary buildings, glass & steel |
| Traditional | `traditional` | Classical, heritage, stone & wood |
| Futuristic | `futuristic` | Sci-fi, organic forms, green tech |
| Aerial view | `aerial` | Bird's eye, masterplan, site context |
| Night scene | `night` | Dramatic lighting, facade uplighting |
| General | `default` | Any architectural render |

**Architecture prompt tips:**
- Describe building type (house, office, tower, museum, school)
- Mention materials (concrete, glass, steel, wood, stone, brick)
- Specify environment (urban, suburban, hillside, waterfront)
- Mention time of day for lighting (golden hour, midday, dusk, night)
- Example: `"modern three-story house with flat roof, large glass windows, surrounded by garden, golden hour"`

### N: 3D Scene (`category="scene"`)

| Style | Key | Best for |
|-------|-----|----------|
| Fantasy | `fantasy` | Magical worlds, floating islands |
| Sci-fi | `scifi` | Space stations, futuristic tech |
| Nature | `nature` | Forests, landscapes, natural beauty |
| Urban | `urban` | City streets, cyberpunk, neon |
| General | `default` | Any 3D scene |

### N: Game Asset (`category="game_asset"`)

| Style | Key | Best for |
|-------|-----|----------|
| Weapon | `weapon` | Swords, guns, magical weapons |
| Environment | `environment` | Game levels, world design |
| Prop | `prop` | Items, objects, collectibles |
| Vehicle | `vehicle` | Cars, ships, aircraft |
| General | `default` | Any game asset |

---

## 6. 3D Rendering keyword guide

When crafting custom prompts, use these keywords to control the 3D look:

### Materials
| Keyword | Effect |
|---------|--------|
| `PBR materials` | Physically-based rendering, realistic surfaces |
| `subsurface scattering` | Translucent skin, wax, marble |
| `metallic / chrome` | Reflective metal surfaces |
| `glossy / matte` | Surface finish control |
| `glass / transparent` | See-through materials |
| `clay render` | Matte gray, no textures, shape focus |

### Lighting
| Keyword | Effect |
|---------|--------|
| `studio lighting` | Clean, professional, controlled |
| `HDRI lighting` | Environment-based, natural reflections |
| `rim light` | Edge highlight, subject separation |
| `volumetric lighting` | God rays, atmospheric depth |
| `ambient occlusion` | Soft contact shadows, depth |
| `global illumination` | Realistic light bouncing |

### Camera / Composition
| Keyword | Effect |
|---------|--------|
| `isometric view` | 45° top-down, no perspective distortion |
| `3/4 angle` | Classic product/character showcase angle |
| `eye level` | Natural human perspective |
| `bird's eye view` | Top-down aerial perspective |
| `tilt-shift` | Miniature/diorama effect |
| `depth of field` | Background blur, subject focus |

### Render Engine Style
| Keyword | Effect |
|---------|--------|
| `octane render` | High-quality, photorealistic |
| `Blender Cycles` | Realistic path tracing |
| `Unreal Engine 5` | Game-quality, real-time look |
| `V-Ray` | Architectural visualization quality |
| `Cinema 4D` | Clean, stylized 3D |
| `KeyShot` | Product visualization quality |

---

## 7. Model selection guide

| Model | Key | Speed | Quality | Best for |
|-------|-----|-------|---------|----------|
| Nano Banana Pro | `nanopro` | ~25s | Good | Quick iterations, drafts, most 3D styles |
| GPT Image 2 | `gpt` | ~150s | Best | Final renders, complex scenes, fine details |

**Recommendations by category:**
- **Characters** → `nanopro` for drafts, `gpt` for final character sheets
- **Products** → `gpt` for photorealistic renders, `nanopro` for quick concepts
- **Dioramas** → `nanopro` handles isometric well; `gpt` for detailed miniatures
- **Icons** → `nanopro` is sufficient for most icons
- **Text** → `gpt` for better text rendering (still imperfect)
- **Interior/Architecture** → `gpt` for photorealistic archviz, `nanopro` for concepts
- **Scenes** → `gpt` for cinematic quality, `nanopro` for quick mood boards

---

## 8. Aspect ratio guide

| Category | Default | Recommended alternatives |
|----------|---------|--------------------------|
| character | `3:4` | `1:1` for avatar, `9:16` for full-body |
| product | `1:1` | `4:3` for landscape showcase |
| diorama | `1:1` | `16:9` for panoramic diorama |
| icon | `1:1` | Always `1:1` |
| text | `16:9` | `1:1` for square banners |
| interior | `16:9` | `4:3` for room views, `3:4` for vertical |
| architecture | `16:9` | `3:4` for tall buildings, `1:1` for aerial |
| scene | `16:9` | `9:16` for vertical scenes |
| game_asset | `1:1` | `3:4` for character assets |

---

## 9. Intent recognition guide

Map user requests to the right category + style:

| User says... | Category | Style | Notes |
|-------------|----------|-------|-------|
| "3D character", "Pixar style character" | `character` | `chibi` or `cartoon` | |
| "game character", "RPG hero" | `character` | `fantasy` | |
| "realistic 3D person" | `character` | `realistic` | |
| "3D product render", "product visualization" | `product` | `floating` | |
| "exploded view", "internal structure" | `product` | `exploded` | |
| "isometric", "miniature scene", "tiny world" | `diorama` | `isometric` | |
| "low poly scene", "stylized environment" | `diorama` | `lowpoly` | |
| "app icon", "iOS icon" | `icon` | `ios` | |
| "game icon", "RPG item icon" | `icon` | `game` | |
| "3D text", "chrome text", "metallic letters" | `text` | `chrome` | |
| "neon sign", "glowing text" | `text` | `neon` | |
| "interior design", "room design", "装修效果图" | `interior` | `modern` | |
| "luxury interior", "penthouse" | `interior` | `luxury` | |
| "cozy room", "warm interior" | `interior` | `cozy` | |
| "building render", "architecture visualization" | `architecture` | `modern` | |
| "night render", "building at night" | `architecture` | `night` | |
| "aerial view", "masterplan" | `architecture` | `aerial` | |
| "fantasy world", "magical scene" | `scene` | `fantasy` | |
| "sci-fi scene", "space station" | `scene` | `scifi` | |
| "game weapon", "sword render" | `game_asset` | `weapon` | |
| "game environment", "level design" | `game_asset` | `environment` | |

---

## 10. Error handling

| Error | Cause | Fix |
|-------|-------|-----|
| `"Unknown model"` | Invalid model key | Use `"nanopro"` or `"gpt"` |
| `"Unknown category"` | Invalid category | Check §5 for valid categories |
| `"Unknown style"` | Style not in category | Check the style table for that category |
| `"File not found"` | reference_path doesn't exist | Verify the file path |
| `"Image too large"` | Reference image > 10 MB | Resize or compress the image |
| `"Submit failed"` | API error | Check FAL_KEY, retry |
| `"Generation timed out"` | Model took too long | Retry, or switch to `nanopro` |

---

## 11. Advanced examples

### 3D character sheet (multiple angles)

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    prompt="a steampunk inventor character with goggles, leather apron, and mechanical arm, character sheet showing front and side views",
    category="character",
    style="realistic",
    model="gpt",
    aspect_ratio="16:9",
)
```

### Isometric city block

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    prompt="a bustling Tokyo street corner with ramen shop, vending machines, and cherry blossom trees, tiny people walking",
    category="diorama",
    style="isometric",
)
```

### Architectural night render

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    prompt="a modern art museum with curved glass facade, reflecting pool in front, dramatic uplighting",
    category="architecture",
    style="night",
    model="gpt",
)
```

### Interior design — modern living room

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    prompt="spacious living room with floor-to-ceiling windows overlooking city skyline, minimalist furniture, warm wood accents, indoor plants",
    category="interior",
    style="modern",
    model="gpt",
)
```

### Reference image → 3D style

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    prompt="transform into a 3D Pixar-style character with exaggerated features",
    reference_path="uploads/photo.jpg",
    category="character",
    style="cartoon",
)
```

### 3D game weapon

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    prompt="legendary fire sword with glowing runes, ember particles, dark background",
    category="game_asset",
    style="weapon",
)
```

### 3D neon text

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    prompt="the word 'CYBER' in neon pink and blue letters, wet street reflection",
    category="text",
    style="neon",
)
```

### Multiple images for comparison

```python
exec(open('skills/image-3d/generate_3d.py').read())
result = generate_3d(
    prompt="a cozy coffee shop interior with exposed brick and warm lighting",
    category="interior",
    style="cozy",
    count=3,
    model="nanopro",
)
# Generates 3 variations for the user to choose from
```
