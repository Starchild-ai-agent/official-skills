---
name: image-ecommerce
version: 1.0.0
description: |
  E-commerce product photography: white-background hero shots, lifestyle scenes, flat lay, detail close-ups, packaging shots, group/collection displays, scale references, seasonal/holiday themes, 360-degree views, comparison layouts, infographics, and platform-optimized images (Amazon, Shopify, Taobao, Instagram, Xiaohongshu, Etsy, eBay).

  Use when generating professional product photos for e-commerce listings, catalogs, or marketing (e.g. product hero shot, Amazon listing image, lifestyle product photo, product on white background, product detail close-up, seasonal product campaign).
metadata:
  starchild:
    emoji: "🛍️"
    skillKey: image-ecommerce
    requires:
      env: [FAL_KEY]
user-invocable: true
disable-model-invocation: false

---

# image-ecommerce

Use this skill for **all e-commerce product photography requests** on Starchild.

Covers: white-background hero shots, lifestyle product scenes, flat lay arrangements, detail/macro close-ups, packaging/unboxing shots, group/collection displays, scale reference images, seasonal themes (spring/summer/autumn/winter), 360-degree views, comparison layouts, infographic-style feature callouts, and platform-optimized images for Amazon, Shopify, Taobao, Instagram, Xiaohongshu, Etsy, eBay.

**Core principle:** call the provided script. Do not re-implement proxy/billing plumbing.

**When to use image-ecommerce vs other image skills:**
- **image-ecommerce** → user wants PRODUCT PHOTOS for e-commerce, catalogs, or marketing
- **image-edit** → user wants to EDIT or TRANSFORM an existing image (not product-specific)
- **image-portrait** → user wants a portrait with their face/identity preserved
- **image-create** → user wants to CREATE something from text (not product photography)
- **image-tryon** → user wants to try on clothing/accessories on a person

---

## 1. Quick start — single product photo (most common)

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    product_path="uploads/product.jpg",
    style="hero",
    background="white",
)
# result -> {"success": True, "images": [{"local_path": "output/images/..."}], ...}
```

The script reads the local file, base64-encodes it, and sends it to fal.ai as a data URI — no manual URL publishing needed.

## 2. Quick start — public URL

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    product_url="https://example.com/product.jpg",
    style="lifestyle",
    background="natural",
)
```

## 3. Quick start — text-to-image (no product photo)

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    prompt="premium wireless bluetooth headphones, matte black finish, over-ear design",
    style="hero",
    background="white",
)
```

When no `product_path` or `product_url` is provided, the script uses the text-to-image endpoint (no `/edit` suffix). A `prompt` describing the product is required in this mode.

## 4. Quick start — platform-optimized

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    product_path="uploads/product.jpg",
    platform="amazon",
)
# Automatically applies: style=hero, background=white, aspect_ratio=1:1
```

## 5. Quick start — complete product image set

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo_set(
    product_path="uploads/product.jpg",
    prompt="premium leather wallet",
    platform="amazon",
)
# Generates 7 images: hero, lifestyle, detail, scale, alternate angle, packaging, flat lay
```

### Delivering the result to the user — IMPORTANT

**Never hand the user the raw fal.media URL.** fal serves files with restrictive CSP headers. The only reliable delivery path is the **already-downloaded local file**:

1. Use each image's `local_path` (e.g. `output/images/xxx.png`) — the script always downloads on success.
2. Tell the user the files are saved to `output/images/` and viewable in the workspace file panel.
3. On Web channel, embed inline so the user can preview in chat:
   ```markdown
   ![product](output/images/<filename>.png)
   ```
4. On Telegram / WeChat: send via `send_to_telegram(file_path="output/images/...", message_type="image")` or `send_to_wechat(file_path="output/images/...", message_type="image")`.

---

## 6. Parameters — `product_photo()`

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `product_path` | no | — | Local workspace file path to the product image |
| `product_url` | no | — | Public HTTPS URL of the product image |
| `prompt` | no | — | Custom prompt describing the product or desired photo |
| `style` | no | `"hero"` | Photography style preset (see §7) |
| `background` | no | `"white"` | Background type (see §8) |
| `model` | no | `"nanopro"` | Model: `"nanopro"` (fast ~25s) or `"gpt"` (best quality ~150s) |
| `count` | no | `1` | Number of images to generate (1–8) |
| `aspect_ratio` | no | `"1:1"` | Output ratio: `1:1`, `3:4`, `4:3`, `9:16`, `16:9` |
| `platform` | no | — | Platform preset: `amazon`, `shopify`, `taobao`, `instagram`, `xiaohongshu`, `etsy`, `ebay` |

**Image input rules:**
- Provide `product_path` OR `product_url` for edit mode (transform existing product photo).
- If both are given, `product_path` takes priority.
- Omit both for pure text-to-image generation (requires `prompt`).

**Prompt priority:** `prompt + style/background` (enhanced) > `style + background` templates.

**Platform preset:** When `platform` is set, it overrides default `style`, `background`, and `aspect_ratio` with platform-optimized values — unless you explicitly set them.

---

## 7. Photography styles

### Core product shots

| Style | Key | Best for |
|-------|-----|----------|
| Hero shot | `hero` | Primary listing image, magazine ads, main product display |
| Lifestyle | `lifestyle` | Product in use, editorial, social media |
| Flat lay | `flat_lay` | Instagram, top-down arrangement, catalog |
| Detail close-up | `detail` | Material quality, texture, craftsmanship |
| Packaging | `packaging` | Unboxing experience, brand packaging |
| Group/collection | `group` | Multiple products, variants, bundles |
| Scale reference | `scale` | Size comparison, product in hand |

### Marketing & informational

| Style | Key | Best for |
|-------|-----|----------|
| 360° view | `360_view` | Multi-angle showcase, turntable display |
| Comparison | `comparison` | Side-by-side, before/after, feature highlight |
| Infographic | `infographic` | Feature callouts, specs, dimensions |

### Seasonal campaigns

| Style | Key | Best for |
|-------|-----|----------|
| Spring | `seasonal_spring` | Cherry blossoms, fresh green, pastel |
| Summer | `seasonal_summer` | Beach, sunshine, tropical, vacation |
| Autumn | `seasonal_autumn` | Fall leaves, golden tones, harvest |
| Winter | `seasonal_winter` | Snow, holiday, festive, cozy |

---

## 8. Background types

| Background | Key | Best for |
|------------|-----|----------|
| Pure white | `white` | Amazon, e-commerce standard, marketplace listings |
| Gradient | `gradient` | Hero shots, premium feel, modern |
| Studio | `studio` | Professional catalog, controlled lighting |
| Natural | `natural` | Outdoor products, organic brands |
| Lifestyle | `lifestyle` | Home/office context, in-use scenarios |
| Colored | `colored` | Brand-matching, vibrant marketing |
| Textured | `textured` | Luxury products, marble/wood surface |
| Transparent | `transparent` | Product cutout, PNG for design use |

---

## 9. Platform presets

| Platform | Aspect Ratio | Background | Style | Key Requirements |
|----------|-------------|------------|-------|------------------|
| Amazon | 1:1 | white | hero | Pure white bg (RGB 255,255,255), product fills 85%+, no props/text/watermarks, min 1000px (1600px+ for zoom) |
| Shopify | 1:1 | white | hero | Square format, consistent catalog style, 2048x2048 recommended |
| Taobao | 1:1 | white | hero | 800x800 minimum, white bg for main image |
| Instagram | 1:1 | lifestyle | lifestyle | 1080x1080 feed, lifestyle context, visually appealing |
| Xiaohongshu | 3:4 | lifestyle | flat_lay | 1080x1440 vertical, aesthetic flat lay, text overlay space |
| Etsy | 4:3 | natural | lifestyle | Handmade/artisan feel, natural backgrounds |
| eBay | 1:1 | white | hero | White background, clear product view, 1600px min for zoom |

---

## 10. Model selection guide

| Model | Key | Speed | Quality | Best for |
|-------|-----|-------|---------|----------|
| NanoPro | `nanopro` | ~25s | Good | Default for all requests. Fast iteration. |
| GPT Image 2 | `gpt` | ~150s | Best | When user explicitly asks for "highest quality" or "best quality". Complex scenes. |

**Decision rules:**
1. **Default:** always use `nanopro` unless the user explicitly requests higher quality.
2. **Use `gpt` when:** user says "highest quality", "best quality", "premium", or the scene is very complex with many specific details.
3. **Use `nanopro` when:** user wants fast results, is iterating on styles, or generating multiple images.

```python
# Default (fast)
result = product_photo(product_path="product.jpg", style="hero")

# High quality (user requested)
result = product_photo(product_path="product.jpg", style="hero", model="gpt")
```

---

## 11. Intent recognition guide

Use this table to map user requests to the correct style + background:

### Product listing images

| User says | Style | Background | Notes |
|-----------|-------|------------|-------|
| "product photo", "listing image", "主图" | `hero` | `white` | Default e-commerce |
| "Amazon listing", "亚马逊主图" | `hero` | `white` | Use `platform="amazon"` |
| "Shopify product", "独立站产品图" | `hero` | `white` | Use `platform="shopify"` |
| "淘宝主图", "天猫主图" | `hero` | `white` | Use `platform="taobao"` |
| "white background", "白底图" | `hero` | `white` | Standard packshot |
| "product on white", "纯白背景" | `hero` | `white` | Amazon-style |

### Lifestyle & context

| User says | Style | Background | Notes |
|-----------|-------|------------|-------|
| "lifestyle photo", "场景图" | `lifestyle` | `lifestyle` | Product in context |
| "product in use", "使用场景" | `lifestyle` | `lifestyle` | Show product being used |
| "flat lay", "俯拍", "平铺" | `flat_lay` | `textured` | Top-down arrangement |
| "Instagram product", "小红书产品" | `flat_lay` | `lifestyle` | Social media optimized |

### Detail & technical

| User says | Style | Background | Notes |
|-----------|-------|------------|-------|
| "close-up", "detail shot", "细节图" | `detail` | `studio` | Macro/texture |
| "packaging", "包装图", "开箱" | `packaging` | `studio` | Box + product |
| "size comparison", "尺寸对比" | `scale` | `studio` | With reference object |
| "multiple products", "组合图" | `group` | `white` | Collection display |
| "360 view", "多角度" | `360_view` | `white` | Turntable style |
| "comparison", "对比图" | `comparison` | `white` | Side by side |
| "infographic", "功能标注" | `infographic` | `white` | Feature callouts |

### Seasonal & campaign

| User says | Style | Background | Notes |
|-----------|-------|------------|-------|
| "spring campaign", "春季" | `seasonal_spring` | auto | Cherry blossoms, pastel |
| "summer sale", "夏季" | `seasonal_summer` | auto | Beach, tropical |
| "autumn/fall", "秋季" | `seasonal_autumn` | auto | Golden leaves, warm |
| "winter/holiday", "冬季", "圣诞" | `seasonal_winter` | auto | Snow, festive |

### Complete product set

| User says | Function | Notes |
|-----------|----------|-------|
| "complete set", "全套产品图", "listing images" | `product_photo_set()` | 7 images covering all angles |
| "Amazon listing set", "亚马逊全套" | `product_photo_set(platform="amazon")` | Platform-optimized set |

---

## 12. Usage examples by scenario

### Amazon listing — white background hero shot

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    product_path="uploads/headphones.jpg",
    platform="amazon",
)
```

### Lifestyle product photo

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    product_path="uploads/coffee_mug.jpg",
    style="lifestyle",
    background="lifestyle",
    prompt="premium coffee mug on rustic wooden table beside an open book, morning sunlight",
)
```

### Product detail close-up

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    product_path="uploads/leather_bag.jpg",
    style="detail",
    background="studio",
    prompt="extreme close-up of leather stitching and grain texture",
)
```

### Seasonal campaign — winter holiday

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    product_path="uploads/candle.jpg",
    style="seasonal_winter",
    prompt="luxury scented candle in cozy holiday setting with pine branches and warm glow",
)
```

### Text-to-image — generate product from description

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    prompt="sleek minimalist smartwatch with black silicone band and OLED display showing time",
    style="hero",
    background="gradient",
    model="gpt",
)
```

### Flat lay for Instagram / Xiaohongshu

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    product_path="uploads/skincare_set.jpg",
    style="flat_lay",
    background="textured",
    platform="xiaohongshu",
)
```

### Multiple images — batch generation

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo(
    product_path="uploads/sneakers.jpg",
    style="hero",
    background="white",
    count=4,
)
# Generates 4 variations of the hero shot
```

### Complete product image set

```python
exec(open('skills/image-ecommerce/product_photo.py').read())
result = product_photo_set(
    product_path="uploads/wallet.jpg",
    prompt="premium leather bifold wallet",
    platform="amazon",
)
# result -> {"success": True, "sets": [...], "total_images": 7, ...}
# Generates: hero, lifestyle, detail, scale, alternate angle, packaging, flat lay
```

---

## 13. Prompt engineering best practices

### The product photography prompt structure

Every effective product photo prompt should include these elements:

```
[product description], [photography style], [lighting], [background/surface], [composition], [quality modifiers]
```

### Key principles (derived from product-photography, eachlabs-product-visuals, image-create skills)

1. **Product preservation is critical** — when editing an existing product image:
   - Always emphasize "keep the product exactly as it is"
   - Preserve shape, color, branding, and details
   - Only change the background/context/lighting

2. **Lighting specificity** — always specify lighting type:
   - Studio: "soft diffused studio lighting", "even lighting with no shadows"
   - Dramatic: "dramatic rim lighting", "edge light for premium feel"
   - Natural: "natural window light", "golden hour warm light"
   - Flat: "flat even lighting" (for e-commerce white background)

3. **Background precision** — vague backgrounds produce poor results:
   - ❌ "nice background"
   - ✅ "pure white background #FFFFFF, no shadows"
   - ✅ "rustic wooden table with morning sunlight"
   - ✅ "soft gradient from white to light grey"

4. **Composition rules** (from product-photography skill):
   - Hero shot: product fills 80% of frame, slight 15-30° angle
   - Packshot (Amazon): product dead center, fills 85%+
   - Flat lay: bird's eye view, organized arrangement
   - Group: odd numbers (3 or 5), triangle composition

5. **Shadow types matter**:
   - No shadow: Amazon/e-commerce requirements
   - Contact shadow: grounded but clean
   - Drop shadow: adds depth, professional
   - Reflection: tech, luxury, premium feel

6. **Material and texture** — for detail shots, specify:
   - "visible leather grain and stitching"
   - "brushed metal finish with subtle reflections"
   - "soft fabric texture, thread detail visible"

7. **Platform compliance** — when targeting a specific platform:
   - Amazon: pure white (RGB 255,255,255), no props/text/watermarks
   - Instagram: lifestyle context, visually appealing
   - Xiaohongshu: vertical format, aesthetic, text overlay space

### Example: building a custom prompt

User request: "I need a hero shot of my leather wallet for Amazon"

```python
result = product_photo(
    product_path="uploads/wallet.jpg",
    platform="amazon",
    prompt="premium leather bifold wallet, rich brown color, slight angle showing card slots",
)
```

The script automatically builds:
```
Transform this product image into a professional e-commerce photo.
Keep the product exactly as it is — preserve its shape, color, details, and branding.
premium leather bifold wallet, rich brown color, slight angle showing card slots.
Photography style: professional product hero shot, clean composition, studio lighting...
Background: pure white background #FFFFFF, clean, e-commerce standard, no shadows.
```

---

## 14. E-commerce image set guide

A complete product listing needs 7-9 images. Use `product_photo_set()` for automatic generation, or create individual shots:

| Position | Image Type | Style | Background | Purpose |
|----------|-----------|-------|------------|---------|
| 1 | Hero / packshot | `hero` | `white` | Primary listing image |
| 2 | Lifestyle | `lifestyle` | `lifestyle` | Product in use/context |
| 3 | Detail close-up | `detail` | `studio` | Material quality, craftsmanship |
| 4 | Scale reference | `scale` | `studio` | Size in hand or next to known object |
| 5 | Alternate angle | `hero` | `white` | Back or side view |
| 6 | Packaging | `packaging` | `studio` | Unboxing experience |
| 7 | Flat lay | `flat_lay` | `textured` | Arranged composition |
| 8 | Infographic | `infographic` | `white` | Dimensions, specs, features |
| 9 | Seasonal | `seasonal_*` | auto | Campaign-specific |

---

## 15. Error handling

The script returns structured results. Always check `success`:

```python
result = product_photo(product_path="uploads/product.jpg")
if result["success"]:
    for img in result["images"]:
        print(f"Saved: {img['local_path']}")
else:
    print(f"Error: {result.get('error')}")
```

Common errors:
- `"File not found"` — check the product_path
- `"Unsupported image format"` — use JPG, PNG, or WebP
- `"Image too large"` — max 10 MB
- `"Either a product image or a prompt is required"` — provide product_path/product_url or prompt
- `"Unknown style/background"` — check available presets in §7/§8
