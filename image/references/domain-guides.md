# Domain guides — distilled from the 7 retired image skills

These are the non-obvious facts the old skills encoded as fixed templates. Use them as
*inputs to the prompt you write*, not as strings to paste. Everything else in those skills
(model list, queue client, cost tracking) is now `catalog.py` / `client.py`.

## Aspect ratio defaults by use (ex image-create / image-3d)

| Use | Ratio | Use | Ratio |
|---|---|---|---|
| logo, icon, meme, product, pet, game asset, 3D product/diorama/icon | 1:1 | poster, movie/sports poster, fashion, wedding, 3D character | 3:4 |
| illustration, education, food, holiday, art style, save-the-date | 4:3 | banner, YouTube thumbnail, 3D text/interior/architecture/scene | 16:9 |
| TikTok cover, story | 9:16 | Xiaohongshu | 3:4 |

Pass `aspect_ratio=` (nano2/nanopro) or `image_size=` (gpt/seedream). Ask when the target platform is unknown.

## Text-to-image categories (ex image-create, 15 categories)

logo · poster · illustration · meme · game_asset · social_media · 3d · education · fashion · food · pet · wedding · product · holiday · art_style.
What the templates actually added per category: medium ("vector", "flat illustration", "3D render"), lighting, negative space for text, and "no text/watermark" when the deliverable will be composited later. Say those explicitly in your prompt; don't rely on the model's default.

## 3D renders (ex image-3d)

Styles: character, product, diorama, icon, text, interior, architecture, scene, game_asset.
Prompt levers that mattered: render engine feel ("octane/blender-style"), material ("matte clay", "glossy plastic", "PBR"), camera ("isometric 3/4 view", "orthographic"), background ("solid pastel", "studio gradient"), and for icons/game assets "centered, single object, no scene". Isometric dioramas want 1:1; scenes/architecture 16:9.

## E-commerce product photography (ex image-ecommerce)

Shot types: hero, lifestyle, flat_lay, detail (macro), packaging, group, scale (with hand/common object), seasonal, 360_view (set of angles), comparison, infographic.
Backgrounds: white, gradient, studio, natural, lifestyle, colored, textured, transparent (→ `remove_background()` afterwards, don't ask the model for alpha).

Platform rules (encode into prompt + `aspect_ratio`):
- **Amazon / eBay / Shopify / Taobao main image**: 1:1, pure white (255,255,255), product fills ≥85%, no props/text/watermarks, ≥1600 px → use `resolution="2K"` on nanopro.
- **Instagram**: 1:1 lifestyle; **Xiaohongshu**: 3:4 flat lay/lifestyle with room for text overlay; **Etsy**: 4:3 natural/handmade feel.
- Product identity must survive: base image = the user's product photo, `keep="product shape, label text, logo, colours"`. For a *set*, loop `edit()` with the same base and vary only the scene sentence.

## Portraits (ex image-portrait)

Identity preservation is a prompt clause, not a model switch: *"portrait preserving the subject's exact facial features and likeness — face shape, eyes, nose, expression"* + `keep="face identity"`. Put the reference face as image 1.
Styles that were popular: professional/LinkedIn, ID photo (white or blue background, front-facing, neutral expression, shoulders visible), dating scenes (café/beach/city), travel (Europe/Japan/tropical), sports, holiday (Christmas/Halloween), graduation, wedding, hanfu, family/child, "with pet".
**Avatar styles (3D avatar / gaming / VTuber) intentionally drop the likeness clause** — they are stylised, exact likeness makes them look uncanny. Say so to the user.
Series (N styles of the same person): one `edit()` per style with identical base and `keep`; don't chain outputs.

## Virtual try-on (ex image-tryon)

Categories: clothing, accessory, hairstyle, makeup, glasses, hat, shoes, watch.
The one prompt that worked: *"The person in image 1 is wearing the {item} from image 2. Keep the person's face, body shape, pose, background and lighting exactly the same. Only change {the outfit / the hair / …}. Natural fit, draping, wrinkles and shadows following the body."* For hairstyle/makeup swap "wearing" for "has the hairstyle/makeup shown in image 2". Two references max are needed; nanopro is the right default. Ask for a full-body / clear-face source when the crop is bad — no prompt fixes a missing torso.

## Editing actions (ex image-edit, 20 actions)

edit · blend · extend (outpaint) · local_edit · restructure (layout change) · text_render · multi_angle · before_after · replace_bg · upscale · restore · colorize · remove_person · retouch · slim · enhance · filter · comparison · car_color · car_wrap.
How they map now:
- **local_edit** → `mask_path` on `gpt`, or a precise "only the … ; everything else pixel-identical" `keep=` on nanopro.
- **upscale** → `resolution="2K"|"4K"` (nanopro) / `quality="high"` + `image_size` (gpt). The word "upscale" alone does nothing.
- **extend/outpaint** → request a *different* `aspect_ratio` and describe what continues the scene.
- **restructure** ("3 columns → 4") → state explicitly that layout MUST change; models default to preserving composition.
- **text_render / logo** → clear region with edit, composite real text/vector with PIL, one blend pass. Diffusion models misspell.
- **before_after / comparison** → deterministic PIL side-by-side, not a generation.
- **restore/colorize/retouch/slim/enhance/filter/car_color/car_wrap** → plain `edit()` with an explicit `keep=` (identity, plate text, wheel design, background…).

## Background removal (ex image-bg-remove)

`remove_background()` → Bria RMBG, transparent PNG, no prompt, ~$0.02. Use it instead of asking a generator for "transparent background" (only gpt honours `background="transparent"`, and it re-renders the subject).
