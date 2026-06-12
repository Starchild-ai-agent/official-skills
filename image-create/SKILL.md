---
name: image-create
version: 1.0.1
description: >-
  Text-to-image with NO reference photo — logos, posters, illustrations, memes, game art, social content, 3D renders.
metadata:
  starchild:
    emoji: "🎨"
    skillKey: image-create
    requires:
      env: [FAL_KEY]
user-invocable: true
disable-model-invocation: false

---

# image-create

Use this skill for **all pure text-to-image generation requests** on Starchild.

Covers: logo design, poster design, illustration, meme creation, game assets, social media content, 3D rendering, educational illustrations, fashion design, food photography, pet illustrations, wedding design, holiday marketing, and artistic style creation.

**Core principle:** call the provided script. Do not re-implement proxy/billing plumbing.

**When to use image-create vs image-portrait:**
- **image-create** → user wants to CREATE something from a text description (no face/identity needed)
- **image-portrait** → user wants a portrait with their face/identity preserved from a reference photo

---

## When to use

Pure text-to-image generation for all creative scenarios: logo design, poster design, illustration, meme, game assets, social media content, 3D rendering, education, fashion, food, pet, wedding, holiday marketing, and artistic styles.

Use when generating images from text descriptions without a reference photo (e.g. design a logo, create a poster, generate game art, make a meme, 3D render).

## 1. Quick start — basic generation (most common)

```python
exec(open('skills/image-create/generate_image.py').read())
result = generate_image(
    prompt="a futuristic city skyline at sunset with flying cars",
)
# result -> {"success": True, "images": [{"local_path": "output/images/..."}], ...}
```

## 2. Quick start — with category preset

```python
exec(open('skills/image-create/generate_image.py').read())
result = generate_image(
    prompt="StarChild AI platform",
    category="logo",
    style="tech",
)
```

## 3. Quick start — category only (no custom prompt)

```python
exec(open('skills/image-create/generate_image.py').read())
result = generate_image(
    category="3d",
    style="diorama",
)
# Uses the built-in style template as the full prompt
```

### Delivering the result to the user — IMPORTANT

**Never hand the user the raw fal.media URL.** fal serves files with restrictive CSP headers. The only reliable delivery path is the **already-downloaded local file**:

1. Use each image's `local_path` (e.g. `output/images/xxx.png`) — the script always downloads on success.
2. Tell the user the files are saved to `output/images/` and viewable in the workspace file panel.
3. On Web channel, embed inline so the user can preview in chat:
   ```markdown
   ![image](output/images/<filename>.png)
   ```
4. On Telegram / WeChat: send via `send_to_telegram(file_path="output/images/...", message_type="image")` or `send_to_wechat(file_path="output/images/...", message_type="image")`.

---

## 4. Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `prompt` | yes* | — | Text description of the desired image |
| `category` | yes* | — | Preset category (see §5) |
| `style` | no | `"default"` | Sub-style within the category (see §5) |
| `model` | no | `"nanopro"` | Model: `"nano2"` (fastest ~15s), `"nanopro"` (balanced ~25s, default), or `"gpt"` (best quality ~150s) |
| `count` | no | `1` | Number of images to generate (1–4) |
| `aspect_ratio` | no | auto | Output ratio: `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`. Auto-selected by category if not set. |
| `image_path` | no | — | Optional local file path for reference/inspiration image |
| `image_url` | no | — | Optional public URL for reference/inspiration image |

*At least one of `prompt` or `category` must be provided.

**Prompt priority:** `prompt + category/style` (enhanced) > `prompt` only > `category + style` > `category` default.

**Aspect ratio auto-selection:** When not explicitly set, the script picks the best ratio for the category (e.g., `1:1` for logos, `3:4` for posters, `16:9` for banners).

---

## 5. Category and style presets

### E: Design — Logo (`category="logo"`)

> ⚠️ **AI cannot reliably render text.** Generate the icon/symbol only; add text/wordmark in a design tool (Figma, Canva, Illustrator).

| Style | Key | Best for |
|-------|-----|----------|
| Abstract geometric | `abstract` | Tech, conceptual brands (Nike swoosh style) |
| Pictorial icon | `pictorial` | Universal brands, works without text (Apple style) |
| Mascot character | `mascot` | Friendly brands, food, sports (KFC style) |
| Tech company | `tech` | SaaS, AI, fintech startups |
| Food brand | `food` | Restaurant, bakery, organic |
| Fashion brand | `fashion` | Luxury, apparel, beauty |
| Gaming | `gaming` | Esports, game studio |
| General | `default` | Any professional logo |

**Logo prompt anti-patterns (avoid):**
- ❌ `"logo with text 'Company Name'"` — text will be garbled
- ❌ `"photorealistic logo"` — logos aren't photos
- ❌ `"3D rendered logo"` — too complex, won't scale down
- ✅ `"flat vector logo of [subject], minimal geometric style, single color, white background"`

### E: Design — Poster (`category="poster"`)

| Style | Key | Best for | Recommended ratio |
|-------|-----|----------|-------------------|
| Movie poster | `movie` | Film promotion, cinematic | 3:4 |
| Music festival | `music_festival` | Concerts, festivals | 3:4 |
| Tech conference | `tech_conference` | Tech events, hackathons | 3:4 |
| Travel destination | `travel` | Tourism, wanderlust | 3:4 |
| Product launch | `product_launch` | Product announcements | 3:4 |
| Minimalist art | `minimalist` | Home decor, gallery | 3:4 |
| Sports event | `sports` | Athletic events | 3:4 |
| General | `default` | Any poster | 3:4 |

### E: Design — Illustration (`category="illustration"`)

| Style | Key | Best for |
|-------|-----|----------|
| Fantasy | `fantasy` | Fantasy worlds, magic, dragons |
| Sci-fi | `scifi` | Futuristic scenes, space |
| Children's book | `children` | Kids content, storybooks (ages 3-5) |
| Editorial | `editorial` | Magazine, article headers |
| Botanical | `botanical` | Scientific plant illustrations |
| General | `default` | Any illustration |

### E: Design — Meme (`category="meme"`)

| Style | Key | Best for |
|-------|-----|----------|
| Animal meme | `animal` | Cute/funny animal memes |
| Reaction | `reaction` | Reaction templates |
| Surreal | `surreal` | Absurdist internet humor |
| General | `default` | Any meme |

### K: Game Assets (`category="game_asset"`)

| Style | Key | Best for | Common sizes |
|-------|-----|----------|-------------|
| Character concept | `character` | RPG characters, heroes | 1024x1024 |
| Environment | `environment` | Game worlds, levels | 1920x1080 |
| Weapon/prop | `weapon` | Items, weapons, artifacts | 1024x1024 |
| UI icon | `ui_icon` | Game UI, mobile icons | 32x32 to 128x128 |
| Pixel sprite | `pixel_sprite` | Retro game characters | 32x32 to 64x64 |
| Tileset | `tileset` | Seamless environment tiles | 256x256 to 512x512 |
| General | `default` | Any game asset | 1024x1024 |

### M: Social Media (`category="social_media"`)

| Style | Key | Best for | Recommended ratio | Resolution |
|-------|-----|----------|-------------------|------------|
| Instagram post | `instagram` | IG feed posts | 1:1 | 1080x1080 |
| 小红书 | `xiaohongshu` | Xiaohongshu posts | 3:4 | 1080x1440 |
| TikTok cover | `tiktok_cover` | TikTok thumbnails | 9:16 | 1080x1920 |
| YouTube thumbnail | `youtube_thumbnail` | YT thumbnails | 16:9 | 1280x720 |
| Banner | `banner` | Twitter/YouTube banners | 16:9 | 1920x1080 |
| Story | `story` | IG/FB stories | 9:16 | 1080x1920 |
| General | `default` | Any social content | 1:1 | 1024x1024 |

### N: 3D (`category="3d"`)

| Style | Key | Best for |
|-------|-----|----------|
| 3D character | `character` | Pixar-style characters |
| Product render | `product` | Product visualization |
| Diorama | `diorama` | Miniature scenes, isometric |
| App icon | `icon` | iOS/Android app icons |
| 3D text | `text` | Chrome/metallic text |
| 3D scene | `scene` | Low-poly environments |
| General | `default` | Any 3D render |

### P: Education (`category="education"`)

| Style | Key | Best for |
|-------|-----|----------|
| Textbook | `textbook` | Textbook illustrations |
| Infographic | `infographic` | Data visualization |
| Science | `science` | Scientific diagrams, anatomy |
| History | `history` | Historical scene reconstruction |
| Diagram | `diagram` | Technical process diagrams |
| General | `default` | Any educational content |

### Q: Fashion (`category="fashion"`)

| Style | Key | Best for |
|-------|-----|----------|
| Clothing design | `clothing` | Garment sketches, fashion plates |
| Accessory | `accessory` | Jewelry, bags, shoes |
| Nail art | `nail_art` | Nail designs |
| Textile pattern | `textile` | Fabric patterns, surface design |
| General | `default` | Any fashion design |

### R: Food (`category="food"`)

| Style | Key | Best for |
|-------|-----|----------|
| Dish photo | `dish` | Food photography, editorial |
| Menu design | `menu` | Restaurant menus |
| Packaging | `packaging` | Food packaging design |
| Recipe card | `recipe_card` | Recipe illustrations |
| General | `default` | Any food content |

### S: Pet (`category="pet"`)

| Style | Key | Best for |
|-------|-----|----------|
| Humanized pet | `humanized` | Pets in human clothes |
| Renaissance | `renaissance` | Royal/regal pet portraits |
| Cartoon | `cartoon` | Disney/Pixar style pets |
| Merchandise | `merchandise` | Pet-themed product patterns |
| Memorial | `memorial` | Pet tribute artwork |
| General | `default` | Cute pet illustrations |

### I: Product Photography (`category="product"`)

> Derived from product-photography skill best practices.

| Style | Key | Best for |
|-------|-----|----------|
| Hero shot | `hero` | Primary product image, magazine ads |
| Packshot | `packshot` | E-commerce listings, Amazon (pure white bg) |
| Lifestyle | `lifestyle` | Product in context, editorial |
| Flat lay | `flat_lay` | Instagram, top-down arrangement |
| General | `default` | Any product photo |

**Product photography tips:**
- Hero shot: product fills 80% of frame, slight 15-30° angle for dimension
- Packshot (Amazon): pure white background, product fills 85%+, no props/text/watermarks
- Always specify lighting: "soft studio lighting", "dramatic rim lighting"
- For e-commerce: "sharp focus", "no shadows" or "subtle shadow only"

### Y: Wedding (`category="wedding"`)

| Style | Key | Best for | Format |
|-------|-----|----------|--------|
| Classic invitation | `invitation` | Floral elegant invitations | 5x7 inches |
| Modern invitation | `invitation_modern` | Minimalist invitations | 5x7 inches |
| Rustic invitation | `invitation_rustic` | Bohemian invitations | 5x7 inches |
| Venue preview | `venue` | Venue decoration preview | — |
| Save the date | `save_the_date` | Pre-announcement cards | 4x6 inches |
| General | `default` | Any wedding design | — |

### Z: Holiday Marketing (`category="holiday"`)

| Style | Key | Best for |
|-------|-----|----------|
| Christmas card | `christmas_card` | Christmas greetings |
| Chinese New Year | `chinese_new_year` | 春节 designs |
| New Year | `new_year` | New Year celebrations |
| Valentine's | `valentines` | Valentine's Day |
| Halloween | `halloween` | Halloween designs |
| Promotional | `promotional` | Sale banners, promos |
| Mid-Autumn | `mid_autumn` | 中秋节 designs |
| General | `default` | Any holiday content |

**Major holiday calendar for campaign planning:**

| Holiday | Timing | Best for |
|---------|--------|----------|
| Chinese New Year | Jan-Feb | Gifts, family, food |
| Valentine's Day | Feb 14 | Romance, gifts |
| Women's Day | Mar 8 | Empowerment, gifts |
| 520 (5/20) | May 20 | Romance (Chinese Valentine's) |
| 618 Shopping | June | E-commerce sales |
| Qixi (七夕) | Jul-Aug | Romance |
| Mid-Autumn | Sept | Family, mooncakes |
| National Day | Oct 1 | Travel, shopping |
| 11.11 Singles' Day | Nov 11 | Major sales |
| 12.12 Double 12 | Dec 12 | Year-end sales |
| Christmas | Dec 25 | Gifts, winter |

### C: Art Style (`category="art_style"`)

| Style | Key | Best for |
|-------|-----|----------|
| Studio Ghibli | `ghibli` | Ghibli-style scenes |
| American comic | `american_comic` | Marvel/DC style |
| Japanese manga | `manga` | Manga illustrations |
| Pixel art | `pixel_art` | Retro game style |
| Pencil sketch | `pencil_sketch` | Hand-drawn look |
| 3D cartoon | `3d_cartoon` | Pixar/Disney style |
| Steampunk | `steampunk` | Victorian sci-fi |
| Fantasy magic | `fantasy_magic` | Magical scenes |
| Wuxia/Xianxia | `wuxia` | Chinese martial arts |
| Sci-fi space | `scifi_space` | Space scenes |
| Pop art | `pop_art` | Warhol style |
| Ukiyo-e | `ukiyo_e` | Japanese woodblock |
| Impressionist | `impressionist` | Monet/Renoir style |
| Art Nouveau | `art_nouveau` | Mucha style |
| General | `default` | Any artistic style |

---

## 6. Model selection guide

| Model | Key | Speed | Quality | Best for |
|-------|-----|-------|---------|----------|
| NanoPro | `nanopro` | ~25s | Good | Default for all requests. Fast iteration. |
| GPT Image 2 | `gpt` | ~150s | Best | When user explicitly asks for "highest quality" or "best quality". Text-heavy designs. |

**Decision rules:**
1. **Default:** always use `nanopro` unless the user explicitly requests higher quality.
2. **Use `gpt` when:** user says "highest quality", "best quality", "premium", or the design requires precise text rendering (logos with specific text, posters with typography).
3. **Use `nanopro` when:** user wants fast results, is iterating on designs, or generating multiple variants.

```python
# Default (fast)
result = generate_image(prompt="cute cat logo", category="logo")

# High quality (user requested)
result = generate_image(prompt="cute cat logo", category="logo", model="gpt")
```

---

## 7. Aspect ratio guide

| Category | Default ratio | Notes |
|----------|--------------|-------|
| Logo | 1:1 | Square, scalable |
| Poster | 3:4 | Portrait orientation |
| Illustration | 4:3 | Landscape, wide scene |
| Meme | 1:1 | Square, shareable |
| Game asset | 1:1 | Square, consistent |
| Social media | 1:1 | Varies by platform |
| 3D | 1:1 | Square render |
| Education | 4:3 | Landscape, readable |
| Fashion | 3:4 | Portrait, full garment |
| Food | 4:3 | Landscape, appetizing |
| Pet | 1:1 | Square, cute |
| Product | 1:1 | Square, e-commerce |
| Wedding | 3:4 | Portrait, elegant |
| Holiday | 4:3 | Landscape, festive |
| Art style | 4:3 | Landscape, scenic |

**Platform-specific overrides (auto-applied):**
- TikTok cover → `9:16` (1080x1920)
- Instagram story → `9:16` (1080x1920)
- YouTube thumbnail → `16:9` (1280x720)
- Social media banner → `16:9` (1920x1080)
- 小红书 → `3:4` (1080x1440)

The script auto-selects the best ratio when `aspect_ratio` is not explicitly set.

---

## 8. Prompt engineering best practices

### The 5-element prompt structure

Every effective image prompt should include:

```
[subject/content], [style/aesthetic], [composition/layout], [lighting/atmosphere], [quality modifiers]
```

### Key principles

1. **Be specific about the subject:**
   - ❌ "a logo"
   - ✅ "a minimalist cat silhouette logo for a pet grooming business, clean vector style"

2. **Specify the visual style:**
   - "flat design", "3D render", "watercolor painting", "photorealistic"
   - "minimalist", "detailed", "abstract", "geometric"

3. **Include composition guidance:**
   - "centered composition", "rule of thirds", "symmetrical layout"
   - "close-up", "wide shot", "isometric view", "bird's eye view"

4. **Lighting matters:**
   - Studio: "soft diffused studio lighting", "Rembrandt chiaroscuro"
   - Natural: "golden hour warm light", "dappled sunlight through trees"
   - Dramatic: "dramatic rim lighting", "volumetric light beams", "neon glow"
   - Flat: "even flat lighting with no shadows" (for icons/diagrams)

5. **Quality anchors:**
   - "professional quality", "print-ready", "4K resolution"
   - "octane render", "Unreal Engine quality", "magazine quality"

6. **For text in images (use `gpt` model):**
   - Explicitly state the text: `text reading "SALE 50% OFF"`
   - Specify font style: "bold sans-serif typography", "elegant script font"
   - GPT model handles text rendering much better than nanopro

### Logo-specific prompt tips (from logo-design-guide)

**Keywords that work:**
```
flat vector logo, simple minimal icon, single color silhouette,
geometric logo mark, clean lines, negative space design,
line art logo, flat design icon, minimalist symbol
```

**Keywords that fail:**
```
❌ photorealistic logo (contradiction — logos aren't photos)
❌ 3D rendered logo (too complex, won't scale down)
❌ gradient logo (inconsistent results, hard to reproduce)
❌ logo with text "Company Name" (text rendering fails)
```

**Prompt structure for logos:**
```
flat vector logo of [subject], [style], [color constraint], [background], [additional detail]
```

### Children's illustration tips (from book-illustrator)

- **Ages 0-2:** Simple, bold, high-contrast, clear shapes
- **Ages 3-5:** Colorful, expressive, engaging characters with movement
- **Ages 6-8:** More detailed scenes with visual storytelling
- **Ages 9-12:** Sophisticated illustrations supporting text
- **The 3-Color Rule:** Limit each character to 3-4 primary colors for visual clarity

### Game asset tips (from game-asset-generation)

- Always specify pixel dimensions for sprites: "32x32", "64x64", "128x128"
- For seamless textures: "must tile perfectly with no visible seams when repeated"
- For sprite sheets: specify grid layout "4x2 grid (256x64 total)"
- For icons: "clear silhouette readable at 32x32 pixels"

### Example: building a custom prompt

User: "Design a logo for my coffee shop called Bean Dream"

```python
result = generate_image(
    prompt=(
        "flat vector logo of a coffee bean morphing into a crescent moon, "
        "minimalist design, warm brown and cream color palette, "
        "clean lines, white background, "
        "professional branding quality, works at any size"
    ),
    category="logo",
    model="gpt",  # GPT for better detail
)
```

### Example: game character concept

User: "Create a warrior character for my RPG game"

```python
result = generate_image(
    prompt=(
        "female warrior character, ornate golden armor with dragon motifs, "
        "flowing red cape, wielding a glowing enchanted sword, "
        "determined fierce expression, battle-ready stance, "
        "front view T-pose, clean white background"
    ),
    category="game_asset",
    style="character",
)
```

### Example: social media content

User: "Make a TikTok cover about cooking tips"

```python
result = generate_image(
    prompt=(
        "cooking tips video thumbnail, colorful kitchen scene, "
        "fresh ingredients flying in the air, chef's hands visible, "
        "fun energetic vibe, bold visual impact"
    ),
    category="social_media",
    style="tiktok_cover",
    # aspect_ratio auto-set to 9:16
)
```

---

## 9. Intent recognition guide

Use this table to map user requests to the correct category/style/parameters:

| User says | Category | Style | Notes |
|-----------|----------|-------|-------|
| "design a logo", "make a logo" | `logo` | auto-detect | Ask about industry for style |
| "create a poster", "event poster" | `poster` | auto-detect | |
| "draw an illustration", "illustrate" | `illustration` | auto-detect | |
| "make a meme", "funny image" | `meme` | auto-detect | |
| "game character", "RPG asset" | `game_asset` | `character` | |
| "game environment", "level design" | `game_asset` | `environment` | |
| "weapon design", "sword/shield" | `game_asset` | `weapon` | |
| "game icon", "UI icon" | `game_asset` | `ui_icon` | |
| "pixel art sprite" | `game_asset` | `pixel_sprite` | |
| "tileable texture", "seamless tile" | `game_asset` | `tileset` | |
| "Instagram post", "IG content" | `social_media` | `instagram` | |
| "小红书", "xiaohongshu" | `social_media` | `xiaohongshu` | |
| "TikTok cover", "抖音封面" | `social_media` | `tiktok_cover` | 9:16 |
| "YouTube thumbnail" | `social_media` | `youtube_thumbnail` | 16:9 |
| "banner", "cover image" | `social_media` | `banner` | 16:9 |
| "story template" | `social_media` | `story` | 9:16 |
| "3D character", "Pixar style" | `3d` | `character` | |
| "product render", "3D product" | `3d` | `product` | |
| "diorama", "miniature scene" | `3d` | `diorama` | |
| "app icon", "3D icon" | `3d` | `icon` | |
| "3D text", "chrome text" | `3d` | `text` | |
| "textbook illustration" | `education` | `textbook` | |
| "infographic", "data viz" | `education` | `infographic` | |
| "scientific diagram" | `education` | `science` | |
| "historical scene" | `education` | `history` | |
| "fashion sketch", "clothing design" | `fashion` | `clothing` | |
| "accessory design", "jewelry" | `fashion` | `accessory` | |
| "nail art", "nail design" | `fashion` | `nail_art` | |
| "textile pattern", "fabric design" | `fashion` | `textile` | |
| "food photo", "dish" | `food` | `dish` | |
| "menu design" | `food` | `menu` | |
| "food packaging" | `food` | `packaging` | |
| "recipe card" | `food` | `recipe_card` | |
| "product photo", "product shot" | `product` | `hero` | |
| "Amazon listing", "e-commerce photo" | `product` | `packshot` | White bg |
| "lifestyle product", "product in context" | `product` | `lifestyle` | |
| "flat lay", "top-down product" | `product` | `flat_lay` | |
| "pet in clothes", "humanized pet" | `pet` | `humanized` | |
| "royal pet", "renaissance pet" | `pet` | `renaissance` | |
| "cartoon pet", "Disney pet" | `pet` | `cartoon` | |
| "pet merchandise", "pet pattern" | `pet` | `merchandise` | |
| "pet memorial", "rainbow bridge" | `pet` | `memorial` | |
| "wedding invitation", "请柬" | `wedding` | `invitation` | |
| "modern invitation" | `wedding` | `invitation_modern` | |
| "rustic invitation" | `wedding` | `invitation_rustic` | |
| "wedding venue", "婚礼布置" | `wedding` | `venue` | |
| "save the date" | `wedding` | `save_the_date` | |
| "Christmas card", "圣诞贺卡" | `holiday` | `christmas_card` | |
| "春节", "Chinese New Year" | `holiday` | `chinese_new_year` | |
| "New Year design", "新年" | `holiday` | `new_year` | |
| "Valentine's card", "情人节" | `holiday` | `valentines` | |
| "Halloween", "万圣节" | `holiday` | `halloween` | |
| "sale banner", "promotional" | `holiday` | `promotional` | |
| "中秋节", "Mid-Autumn" | `holiday` | `mid_autumn` | |
| "Ghibli style", "吉卜力" | `art_style` | `ghibli` | |
| "comic style", "漫画风" | `art_style` | `american_comic` or `manga` | |
| "pixel art", "像素风" | `art_style` | `pixel_art` | |
| "pencil sketch", "素描" | `art_style` | `pencil_sketch` | |
| "steampunk", "蒸汽朋克" | `art_style` | `steampunk` | |
| "fantasy", "魔法" | `art_style` | `fantasy_magic` | |
| "wuxia", "武侠", "仙侠" | `art_style` | `wuxia` | |
| "space", "太空", "sci-fi" | `art_style` | `scifi_space` | |
| "pop art", "波普" | `art_style` | `pop_art` | |
| "ukiyo-e", "浮世绘" | `art_style` | `ukiyo_e` | |
| "impressionist", "印象派" | `art_style` | `impressionist` | |
| "Art Nouveau", "新艺术" | `art_style` | `art_nouveau` | |
| "highest quality", "best quality" | any | any + `model="gpt"` | |
| Custom description not in presets | — | — | Use `prompt=` directly |

---

## 10. Using with a reference image (optional)

While this skill is primarily text-to-image, you can provide a reference image for design inspiration:

```python
# Reference image for design guidance
result = generate_image(
    prompt="redesign this logo in a modern minimalist style",
    category="logo",
    image_path="uploads/old_logo.png",
)

# Reference URL
result = generate_image(
    prompt="create a similar style illustration but with a forest theme",
    image_url="https://example.com/reference.jpg",
)
```

When a reference image is provided, the script uses the `/edit` endpoint instead of the generate endpoint.

---

## 11. Multiple images

```python
# Generate 4 logo variants
result = generate_image(
    prompt="minimalist mountain logo for outdoor brand",
    category="logo",
    count=4,
)
# result["images"] -> list of 4 image dicts
```

---

## 12. Anti-patterns (avoid these)

| Avoid | Why | Instead |
|-------|-----|---------|
| `"logo with text 'My Brand'"` | AI garbles text | Generate icon only, add text in Figma/Canva |
| `"photorealistic logo"` | Logos aren't photos | Use "flat vector logo" |
| `"3D rendered logo"` | Won't scale to favicon | Use "flat minimal icon" |
| Vague prompts like "nice image" | Poor results | Be specific: subject, style, colors, lighting |
| Too many concepts in one prompt | Confused output | Focus on one clear concept |
| Requesting exact pixel dimensions | Not supported | Use `aspect_ratio` parameter |
| Using `nanopro` for text-heavy designs | Text rendering poor | Use `model="gpt"` for text |

---

## 13. Provided scripts

| File | Purpose |
|------|---------|
| `generate_image.py` | Core script: prompt building → submit → poll → download. Handles all categories, styles, two models. |
| `exports.py` | Re-exports `generate_image`, `CATEGORY_STYLES`, `MODELS` for programmatic use. |
| `_cost_track.py` | Cost tracking helper — records per-call costs via sc-proxy headers. Self-contained, no external dependencies. |

---

## 14. Local testing

Set `FAL_KEY` env var to call fal.ai directly (bypasses sc-proxy):

```bash
# Basic generation
FAL_KEY=your-fal-key python3 skills/image-create/generate_image.py "a cute robot" illustration fantasy 1 nanopro

# Args: <prompt> [category] [style] [count] [model]
```

---

## 15. Troubleshooting

| Problem | Fix |
|---------|-----|
| `Either 'prompt' or 'category' must be provided` | Provide at least a prompt or category |
| `File not found: ...` | Check the workspace path for reference image |
| `Unsupported image format` | Use `.jpg`, `.jpeg`, `.png`, `.webp`, or `.bmp` |
| `Image too large` | Resize reference image to under 10 MB |
| `HTTP 402 insufficient_credits` | Top up balance; cost is pre-charged on submit |
| `HTTP 403 endpoint_not_allowed` | sc-proxy only allows approved fal endpoints; contact admin |
| Generation `FAILED` upstream | Simplify prompt, retry |
| Job stuck `IN_PROGRESS` >10 min | Save `request_id`, retry later |
| Text not rendering well | Switch to `model="gpt"` — GPT handles text much better |
| `gpt` model too slow | Switch to `nanopro` (default) for faster results |
| Logo too complex to scale | Use "flat vector", "minimal", "single color" in prompt |
| Seamless texture has visible seams | Add "must tile perfectly with no visible seams" to prompt |

---

## 16. Infrastructure (reference)

- Caller → `sc-proxy` → `queue.fal.run/{model}` → fal model providers
- All requests must include `Authorization: Key fake-falai-key-12345` (proxy injects the real `FAL_KEY`)
- Pre-charge happens at submit. Poll/result calls are free.
- Final images live at `https://*.fal.media/...` — public CDN, no auth needed for download.
- Cost tracking via `_cost_track.py` — records `X-Credits-Used` from sc-proxy response headers.
- Each skill contains its own `_cost_track.py` copy (skills are independently deployed).

### Model endpoints

| Model | Generate (text only) | Edit (with ref image) |
|-------|---------------------|----------------------|
| nanopro | `fal-ai/nano-banana-pro` | `fal-ai/nano-banana-pro/edit` |
| gpt | `openai/gpt-image-2` | `openai/gpt-image-2/edit` |

---
