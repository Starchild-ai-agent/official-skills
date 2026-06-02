#!/usr/bin/env python3
"""Image creation script — pure text-to-image generation for all creative scenarios.

Supports three models:
  - nano2    (fal-ai/gemini-3.1-flash-image-preview)     — fastest ~15s, good for drafts
  - nanopro  (fal-ai/gemini-3-pro-image-preview)   — balanced ~25s, good quality (default)
  - gpt      (openai/gpt-image-2)       — best quality, slow ~150s

Covers: logo design, poster design, illustration, meme, game assets, social media,
3D rendering, education, fashion, food, pet, wedding, holiday marketing, and more.

Flow: build prompt → submit to fal queue → poll → download.

Cost tracking: uses _cost_track.py to record per-call costs via sc-proxy
headers so the agent's per-turn cost_summary picks up this skill's cost.

Local testing: set FAL_KEY env var to call fal.ai directly (no sc-proxy).
"""

import requests
import json
import time
import os
import sys
import base64
import mimetypes
from datetime import datetime
from pathlib import Path
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Make _cost_track importable when this script is invoked from any CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from _cost_track import caller_headers, record_response  # noqa: E402

# Local testing: when FAL_KEY env var is set, call fal.ai directly
# (no sc-proxy). In production, sc-proxy injects the real key.
_FAL_KEY = os.environ.get("FAL_KEY")
_LOCAL_MODE = bool(_FAL_KEY)

PROXY_URL = 'http://sc-proxy.internal:8080'
PROXIES = {} if _LOCAL_MODE else {'http': PROXY_URL, 'https': PROXY_URL}

# ── Model configuration ──────────────────────────────────────────────
MODELS = {
    "nano2": {
        "generate": "fal-ai/gemini-3.1-flash-image-preview",
        "edit": "fal-ai/gemini-3.1-flash-image-preview/edit",
        "timeout": 90,
        "poll_interval": 2,
    },
    "nanopro": {
        "generate": "fal-ai/gemini-3-pro-image-preview",
        "edit": "fal-ai/gemini-3-pro-image-preview/edit",
        "timeout": 120,
        "poll_interval": 3,
    },
    "gpt": {
        "generate": "openai/gpt-image-2",
        "edit": "openai/gpt-image-2/edit",
        "timeout": 600,
        "poll_interval": 5,
    },
}
DEFAULT_MODEL = "nanopro"

# Supported image extensions for optional reference image
SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

# ── Category + Style prompt templates ─────────────────────────────────
# Each category contains named sub-styles with optimized prompt templates.
# The "default" key is used when no specific style is requested.
#
# Prompt templates are derived from extensive testing and reference skills:
#   - logo-design-guide (prompt structure, anti-patterns)
#   - poster-design-generation (cinematic composition, typography space)
#   - game-asset-generation (sprite sizes, tileable textures)
#   - ai-social-media-content (platform formats)
#   - book-illustrator (age-appropriate design, character consistency)
#   - pet-portrait-generation (style variety)
#   - wedding-invitation-generation (stationery formats)
#   - seasonal-campaigns (holiday calendar)

CATEGORY_STYLES = {
    # === E: Design — Logo ===
    # Key insight from logo-design-guide: AI cannot reliably render text.
    # Generate icon/symbol only; add text in a design tool.
    "logo": {
        "abstract": (
            "flat vector abstract logo mark, interlocking geometric shapes, "
            "minimal clean lines, single color, white background, "
            "negative space design, scalable at any size, "
            "professional branding quality, sharp edges"
        ),
        "pictorial": (
            "flat vector pictorial logo, recognizable icon symbol, "
            "clean silhouette, minimal geometric style, single color, "
            "white background, works without text, "
            "memorable and distinctive, scalable design"
        ),
        "mascot": (
            "friendly cartoon mascot logo, simple flat illustration, "
            "vibrant colors, clean vector style, white background, "
            "approachable character design, bold outlines, "
            "works at small sizes"
        ),
        "tech": (
            "modern minimalist tech logo, clean geometric shapes, "
            "gradient blue and purple, white background, vector style, "
            "professional branding, interconnected nodes or circuits, "
            "startup aesthetic, scalable design"
        ),
        "food": (
            "warm inviting food brand logo, hand-drawn organic style, "
            "earthy tones brown and green, white background, "
            "artisanal feel, appetizing imagery, "
            "clean vector illustration"
        ),
        "fashion": (
            "elegant fashion brand logo mark, serif-inspired geometry, "
            "gold and black, minimalist luxury feel, white background, "
            "high-end aesthetic, clean lines, "
            "works as monogram or icon"
        ),
        "gaming": (
            "bold gaming logo, dynamic angular shapes, neon accents, "
            "dark background, esports style, aggressive energy, "
            "shield or emblem shape, vibrant colors, "
            "tournament-ready design"
        ),
        "default": (
            "professional logo design, clean modern flat vector style, "
            "balanced composition, white background, "
            "scalable memorable distinctive, single or dual color, "
            "works at favicon size and billboard size"
        ),
    },

    # === E: Design — Poster ===
    "poster": {
        "movie": (
            "cinematic movie poster, dramatic lighting with strong key light, "
            "bold title text space at top, atmospheric composition, "
            "credits space at bottom, Hollywood blockbuster quality, "
            "2:3 vertical format, compelling visual narrative"
        ),
        "music_festival": (
            "music festival poster, vibrant neon colors, "
            "abstract geometric shapes with laser beams and light effects, "
            "futuristic cyberpunk aesthetic, space for artist names at top, "
            "event details at bottom, high energy rave culture vibes"
        ),
        "tech_conference": (
            "tech conference poster, futuristic design, "
            "blue and gold color scheme, bold sans-serif typography space, "
            "circuit board and data flow elements, modern layout, "
            "professional event marketing quality"
        ),
        "travel": (
            "travel destination poster, art deco style with bold shapes, "
            "warm sunset colors, dreamy wanderlust aesthetic, "
            "landmark silhouette, space for destination name at bottom, "
            "vintage travel poster inspiration"
        ),
        "product_launch": (
            "sleek product launch poster, product floating in center, "
            "dynamic light trails and particle effects, "
            "dark premium background with subtle gradient, "
            "Apple-style minimalism, space for product name and tagline"
        ),
        "minimalist": (
            "minimalist art poster, Scandinavian design style, "
            "simple geometric shapes, limited color palette, "
            "abstract composition, clean lines, modern aesthetic, "
            "suitable for home decor, gallery quality"
        ),
        "sports": (
            "dynamic sports event poster, action shot composition, "
            "explosive energy with motion blur and particle effects, "
            "dramatic stadium lighting, bold colors, high contrast, "
            "intense competitive spirit, space for event title"
        ),
        "default": (
            "professional poster design, balanced layout, "
            "clear typography space, engaging visual, "
            "high-quality print-ready design, eye-catching composition"
        ),
    },

    # === E: Design — Illustration ===
    "illustration": {
        "fantasy": (
            "fantasy world illustration, floating islands with waterfalls, "
            "crystal trees and magical creatures, dragons soaring, "
            "ethereal glow and magical particles, epic cinematic scene, "
            "detailed digital painting, rich jewel-tone color palette"
        ),
        "scifi": (
            "science fiction illustration, futuristic megacity, "
            "flying vehicles and holographic displays, neon lights, "
            "advanced technology, towering structures, "
            "cinematic atmosphere, Blade Runner meets Star Wars"
        ),
        "children": (
            "children's book illustration, cute rounded characters, "
            "bright primary colors, whimsical friendly atmosphere, "
            "soft shapes, warm and inviting, storybook quality, "
            "age-appropriate for 3-5 year olds, clear visual storytelling"
        ),
        "editorial": (
            "editorial illustration, conceptual metaphorical imagery, "
            "sophisticated style, magazine cover quality, "
            "thought-provoking composition, limited color palette, "
            "New Yorker or Atlantic style"
        ),
        "botanical": (
            "botanical illustration, detailed scientific accuracy, "
            "watercolor rendering, labeled plant anatomy, "
            "vintage natural history style, cream paper texture, "
            "museum-quality specimen illustration"
        ),
        "default": (
            "detailed illustration, rich colors, professional quality, "
            "engaging composition, polished digital art, "
            "clear visual narrative"
        ),
    },

    # === E: Design — Meme ===
    "meme": {
        "animal": (
            "funny meme image, cute animal in unexpected human situation, "
            "exaggerated expressive face, humorous composition, "
            "internet meme aesthetic, shareable viral quality, "
            "clean background for text overlay"
        ),
        "reaction": (
            "reaction meme template, exaggerated facial expression, "
            "clean solid background, meme-ready composition, "
            "bold and clear emotion, easily recognizable, "
            "space for top and bottom text"
        ),
        "surreal": (
            "surreal absurdist meme image, unexpected juxtaposition, "
            "dreamlike quality, slightly unsettling humor, "
            "deep-fried aesthetic optional, internet culture, "
            "visually striking and shareable"
        ),
        "default": (
            "humorous meme image, funny situation, expressive characters, "
            "clear visual joke, internet culture aesthetic, "
            "clean composition for text overlay"
        ),
    },

    # === K: Game Assets ===
    "game_asset": {
        "character": (
            "game character concept art, detailed fantasy RPG design, "
            "front view T-pose, clean white background, "
            "ornate armor and clothing details, "
            "professional character sheet quality, game-ready topology, "
            "consistent art direction"
        ),
        "environment": (
            "game environment concept art, atmospheric immersive scene, "
            "detailed world-building, cinematic composition, "
            "rich volumetric lighting, depth layers foreground to background, "
            "professional game art quality, painterly style"
        ),
        "weapon": (
            "game weapon design, detailed metalwork and engravings, "
            "fantasy RPG style, multiple angle views, "
            "clean white background, material detail (steel, gold, gems), "
            "professional prop design, item icon ready"
        ),
        "ui_icon": (
            "game UI icon, consistent flat style, clean sharp edges, "
            "vibrant colors on dark background, glossy finish, "
            "clear silhouette readable at 32x32 pixels, "
            "mobile game quality, item/ability icon"
        ),
        "pixel_sprite": (
            "pixel art character sprite, retro 16-bit style, "
            "clean pixel edges no anti-aliasing, limited color palette, "
            "side view facing right, transparent background, "
            "game-ready sprite, nostalgic aesthetic"
        ),
        "tileset": (
            "seamless tileable game texture, must tile perfectly "
            "with no visible seams when repeated, consistent lighting, "
            "top-down or side-view perspective, "
            "game environment surface, detailed but clean"
        ),
        "default": (
            "game asset design, professional quality, clean style, "
            "game-ready, detailed rendering, consistent art direction, "
            "suitable for indie or AAA game development"
        ),
    },

    # === M: Social Media ===
    "social_media": {
        "instagram": (
            "Instagram feed post design, aesthetic square layout, "
            "trendy colors and modern typography, lifestyle feel, "
            "visually appealing, engagement-optimized, "
            "clean composition, influencer aesthetic"
        ),
        "xiaohongshu": (
            "小红书 style post, soft pastel pink and cream colors, "
            "cute stickers and decorative elements, clean layout, "
            "lifestyle aesthetic, warm and inviting, "
            "trendy Chinese social media design, 3:4 vertical"
        ),
        "tiktok_cover": (
            "TikTok video cover thumbnail, bold text overlay space, "
            "eye-catching vibrant colors, vertical 9:16 format, "
            "dynamic composition, scroll-stopping design, "
            "trendy Gen-Z aesthetic, high contrast"
        ),
        "youtube_thumbnail": (
            "YouTube thumbnail, eye-catching 16:9 horizontal, "
            "bright saturated colors, high contrast, "
            "bold visual impact, attention-grabbing composition, "
            "professional content creator quality, "
            "text area on right third"
        ),
        "banner": (
            "social media banner header, professional design, "
            "wide 16:9 format, clean typography space, "
            "modern layout, brand-consistent aesthetic, "
            "platform-optimized, Twitter/YouTube banner quality"
        ),
        "story": (
            "Instagram story template, vertical 9:16 format, "
            "trendy design with interactive element spaces, "
            "modern aesthetic, engaging layout, "
            "swipe-up friendly, gradient background"
        ),
        "default": (
            "social media content, engaging modern design, "
            "platform-optimized, trendy aesthetic, "
            "shareable quality, clean composition"
        ),
    },

    # === N: 3D ===
    "3d": {
        "character": (
            "3D character design, Pixar-quality rendering, "
            "stylized proportions with large head, "
            "soft ambient occlusion, vibrant saturated colors, "
            "clean studio lighting, subsurface skin scattering, "
            "character select screen aesthetic, friendly expression"
        ),
        "product": (
            "3D product render, photorealistic PBR materials, "
            "studio lighting with soft reflections and caustics, "
            "clean gradient background, octane render quality, "
            "commercial product visualization, floating angle"
        ),
        "diorama": (
            "3D isometric diorama, miniature scene with tiny details, "
            "warm cozy lighting, tilt-shift depth of field, "
            "clay render aesthetic, charming miniature world, "
            "cross-section view, pastel color palette"
        ),
        "icon": (
            "3D app icon design, glossy material with soft reflections, "
            "rounded square shape, subtle shadows, glass material, "
            "iOS style, clean gradient background, "
            "professional quality, single object centered"
        ),
        "text": (
            "3D text rendering, bold chrome metallic letters, "
            "dramatic reflections and refractions, "
            "volumetric lighting with god rays, "
            "cinematic composition, floating in space, "
            "professional typography, epic atmosphere"
        ),
        "scene": (
            "3D rendered scene, low-poly stylized aesthetic, "
            "warm ambient lighting, soft shadows, "
            "miniature world feel, vibrant color palette, "
            "Blender/Cinema4D quality, clean composition"
        ),
        "default": (
            "3D render, high quality professional lighting, "
            "clean composition, detailed PBR materials, "
            "studio quality, octane render aesthetic"
        ),
    },

    # === P: Education ===
    "education": {
        "textbook": (
            "educational textbook illustration, clear informative style, "
            "labeled diagram with annotation lines, "
            "professional academic quality, clean layout, "
            "easy to understand at a glance, neutral background"
        ),
        "infographic": (
            "infographic design, data visualization with charts and icons, "
            "clean modern layout, color-coded sections, "
            "clear visual hierarchy, easy to understand, "
            "professional quality, shareable format"
        ),
        "science": (
            "scientific illustration, anatomically accurate detail, "
            "cross-section cutaway view, labeled parts with leader lines, "
            "educational quality, precise rendering, "
            "textbook-ready, medical/biology illustration style"
        ),
        "history": (
            "historical scene reconstruction, period-accurate costumes "
            "and architecture, atmospheric lighting, "
            "documentary illustration style, educational quality, "
            "immersive historical setting, museum exhibit quality"
        ),
        "diagram": (
            "technical diagram, clean vector style, "
            "step-by-step process visualization, numbered steps, "
            "arrows showing flow and connections, "
            "professional technical documentation quality"
        ),
        "default": (
            "educational illustration, clear and informative, "
            "professional quality, easy to understand, "
            "suitable for classroom or textbook use"
        ),
    },

    # === Q: Fashion ===
    "fashion": {
        "clothing": (
            "fashion design sketch, detailed garment illustration, "
            "fabric texture and draping, front and back view, "
            "fashion plate style with elongated proportions, "
            "professional fashion illustration, clean pencil lines, "
            "runway-ready design"
        ),
        "accessory": (
            "luxury accessory design rendering, detailed materials "
            "(leather, metal, gemstones), multiple angle views, "
            "product design quality, professional presentation, "
            "high-end catalog aesthetic"
        ),
        "nail_art": (
            "nail art design showcase, detailed intricate patterns, "
            "trendy seasonal style, multiple nail shapes displayed, "
            "beauty photography lighting, close-up macro detail, "
            "salon-quality design, Instagram-worthy"
        ),
        "textile": (
            "textile pattern design, seamless repeating pattern, "
            "fabric-ready, consistent motifs, "
            "fashion-forward color palette, "
            "print-ready quality, surface design"
        ),
        "default": (
            "fashion design illustration, trendy contemporary style, "
            "professional quality, detailed rendering, "
            "runway or editorial aesthetic"
        ),
    },

    # === R: Food ===
    "food": {
        "dish": (
            "food photography, beautifully plated gourmet dish, "
            "professional studio lighting with soft shadows, "
            "appetizing warm colors, shallow depth of field, "
            "restaurant quality, editorial food styling, "
            "overhead or 45-degree angle"
        ),
        "menu": (
            "restaurant menu design, elegant organized layout, "
            "food photography sections, clean serif typography, "
            "appetizing presentation, professional print quality, "
            "warm color palette, fine dining aesthetic"
        ),
        "packaging": (
            "food packaging design, shelf-ready retail quality, "
            "brand-consistent design system, appetizing product imagery, "
            "modern clean layout, consumer-friendly, "
            "mockup on store shelf context"
        ),
        "recipe_card": (
            "recipe card design, step-by-step cooking illustration, "
            "ingredient icons, clean organized layout, "
            "warm inviting colors, printable quality, "
            "home cooking aesthetic"
        ),
        "default": (
            "food styling photography, appetizing presentation, "
            "professional quality, warm inviting colors, "
            "editorial food magazine aesthetic"
        ),
    },

    # === S: Pet ===
    "pet": {
        "humanized": (
            "anthropomorphized pet portrait, animal wearing human clothes "
            "and accessories, funny and adorable, detailed illustration, "
            "charming personality shining through, "
            "whimsical storybook style, heartwarming"
        ),
        "renaissance": (
            "pet portrait in Renaissance painting style, "
            "regal royal costume with ornate details, "
            "classical oil painting technique, dramatic Rembrandt lighting, "
            "museum-quality frame aesthetic, majestic noble pose"
        ),
        "cartoon": (
            "cute cartoon pet illustration, Disney/Pixar style, "
            "big expressive eyes, playful pose, vibrant colors, "
            "clean bold outlines, fun background with toys, "
            "children's animation quality"
        ),
        "merchandise": (
            "pet-themed merchandise pattern design, cute animal motifs, "
            "seamless repeatable pattern, product-ready, "
            "consistent style, adorable aesthetic, "
            "commercial quality, works on mugs/shirts/bags"
        ),
        "memorial": (
            "pet memorial portrait, gentle warm lighting, "
            "soft ethereal atmosphere, angel wings or rainbow bridge, "
            "loving tribute artwork, emotional and beautiful, "
            "watercolor or soft pastel style"
        ),
        "default": (
            "cute pet illustration, adorable expressive style, "
            "warm colors, heartwarming atmosphere, "
            "detailed fur texture, big soulful eyes, "
            "professional pet art quality"
        ),
    },

    # === Y: Wedding ===
    "wedding": {
        "invitation": (
            "wedding invitation design, elegant floral border "
            "with roses and eucalyptus, romantic script typography space, "
            "soft blush and gold color palette, printable 5x7 quality, "
            "refined classic elegance, cream paper texture"
        ),
        "invitation_modern": (
            "modern minimalist wedding invitation, ultra clean design, "
            "lots of white space, sans-serif typography space, "
            "subtle geometric accents, black text on white, "
            "single thin gold line accent, sophisticated understated"
        ),
        "invitation_rustic": (
            "rustic bohemian wedding invitation, natural organic elements, "
            "wildflowers and greenery, kraft paper texture, "
            "hand-lettered typography space, earthy warm tones, "
            "outdoor garden wedding aesthetic"
        ),
        "venue": (
            "wedding venue decoration preview, romantic elegant setup, "
            "floral arch arrangements, fairy lights and candles, "
            "dreamy soft-focus atmosphere, warm ambient lighting, "
            "reception hall or garden ceremony"
        ),
        "save_the_date": (
            "save the date card design, playful yet elegant, "
            "photo frame space, romantic typography, "
            "soft color palette, 4x6 horizontal format, "
            "modern wedding stationery"
        ),
        "default": (
            "wedding design, romantic and elegant, "
            "soft blush and gold colors, professional quality, "
            "timeless aesthetic, printable quality"
        ),
    },

    # === I: Product Photography (from product-photography skill) ===
    "product": {
        "hero": (
            "hero product shot, premium product floating at slight angle, "
            "clean gradient background white to light grey, "
            "dramatic rim lighting with subtle reflection below, "
            "commercial photography, magazine quality, sharp details, "
            "product fills 80% of frame"
        ),
        "packshot": (
            "product packshot, product on pure white background RGB 255 255 255, "
            "soft even studio lighting, no shadows, "
            "e-commerce product photography, Amazon listing style, "
            "clean sharp focus, product fills 85% of frame, "
            "professional catalog quality"
        ),
        "lifestyle": (
            "lifestyle product photography, product in natural context, "
            "showing how it's used, warm natural lighting, "
            "shallow depth of field, editorial style, "
            "aspirational atmosphere, magazine quality"
        ),
        "flat_lay": (
            "flat lay product photography, top-down bird's eye view, "
            "carefully arranged composition, complementary props, "
            "clean background, Instagram-worthy aesthetic, "
            "balanced layout, professional styling"
        ),
        "default": (
            "professional product photography, clean studio lighting, "
            "sharp focus on product, neutral background, "
            "commercial quality, e-commerce ready"
        ),
    },

    # === Z: Holiday Marketing ===
    "holiday": {
        "christmas_card": (
            "Christmas greeting card, festive design with snowflakes "
            "and golden ornaments, warm cozy winter atmosphere, "
            "traditional red green and gold colors, "
            "printable quality, space for greeting text, "
            "fireplace and twinkling lights feel"
        ),
        "chinese_new_year": (
            "Chinese New Year celebration design, traditional red and gold, "
            "paper-cut art style, dragon or lantern motifs, "
            "auspicious symbols, festive spring festival atmosphere, "
            "春节 aesthetic, prosperity and joy"
        ),
        "new_year": (
            "New Year celebration design, midnight fireworks, "
            "gold and silver sparkle, festive typography space, "
            "party atmosphere, glamorous countdown mood, "
            "champagne and confetti elements"
        ),
        "valentines": (
            "Valentine's Day card, romantic design, "
            "hearts and roses, pink and red palette, "
            "love theme, elegant script typography space, "
            "heartfelt sentiment, soft dreamy atmosphere"
        ),
        "halloween": (
            "Halloween themed design, carved pumpkin lanterns, "
            "spider webs and bats, mysterious spooky atmosphere, "
            "dramatic purple and orange lighting, "
            "fog effects, haunted house aesthetic"
        ),
        "promotional": (
            "promotional sale banner, bold attention-grabbing typography space, "
            "eye-catching contrasting colors, urgency design elements, "
            "clear call-to-action area, "
            "marketing-optimized layout, retail quality"
        ),
        "mid_autumn": (
            "Mid-Autumn Festival design, full moon and jade rabbit, "
            "mooncake illustrations, traditional Chinese lanterns, "
            "warm golden and deep blue palette, "
            "中秋节 aesthetic, family reunion atmosphere"
        ),
        "default": (
            "holiday themed design, festive celebratory atmosphere, "
            "warm inviting mood, professional quality, "
            "space for greeting text"
        ),
    },

    # === C: Art Style (pure creation, no reference photo needed) ===
    "art_style": {
        "ghibli": (
            "Studio Ghibli anime style scene, lush natural landscape, "
            "soft watercolor sky with towering cumulus clouds, "
            "whimsical atmosphere, Hayao Miyazaki inspired, "
            "detailed hand-painted background art, "
            "warm nostalgic colors, magical realism"
        ),
        "american_comic": (
            "American comic book style illustration, bold ink outlines, "
            "dynamic action pose, halftone dot shading, "
            "vibrant primary colors, Marvel/DC aesthetic, "
            "dramatic foreshortening, speech bubble space"
        ),
        "manga": (
            "Japanese manga style illustration, detailed precise line art, "
            "screentone shading, expressive characters with large eyes, "
            "dynamic panel composition, speed lines for motion, "
            "black and white with selective color accents"
        ),
        "pixel_art": (
            "pixel art scene, retro 16-bit style, visible clean pixels, "
            "limited 32-color palette, nostalgic video game aesthetic, "
            "detailed sprite work, consistent pixel grid, "
            "NOT a pixelated photo filter"
        ),
        "pencil_sketch": (
            "detailed pencil sketch, graphite drawing on textured paper, "
            "fine hatching and cross-hatching for shading, "
            "realistic proportions, classical drawing technique, "
            "artistic study quality, visible paper grain"
        ),
        "3d_cartoon": (
            "3D cartoon style scene, Pixar/Disney quality rendering, "
            "vibrant saturated colors, soft ambient occlusion, "
            "playful exaggerated proportions, clean studio lighting, "
            "family-friendly aesthetic, subsurface scattering"
        ),
        "steampunk": (
            "steampunk style illustration, Victorian-era brass machinery, "
            "intricate gears pipes and clockwork mechanisms, "
            "steam-powered devices, industrial aesthetic, "
            "warm sepia and copper tones, retro-futuristic"
        ),
        "fantasy_magic": (
            "fantasy magic scene, glowing arcane runes and spell circles, "
            "mystical energy streams, enchanted landscape, "
            "ethereal bioluminescent lighting, magical particles, "
            "epic high fantasy art, rich jewel-tone colors"
        ),
        "wuxia": (
            "wuxia martial arts scene, Chinese ink wash painting style, "
            "misty mountains and bamboo forests, flowing silk robes, "
            "sword fighting with qi energy trails, "
            "traditional Chinese aesthetic, xianxia fantasy elements, "
            "dramatic composition with negative space"
        ),
        "scifi_space": (
            "science fiction space scene, vast cosmic landscape, "
            "colorful nebulae and dense star fields, "
            "detailed futuristic spacecraft, cinematic lighting, "
            "epic sense of scale, hard sci-fi technology, "
            "2001 Space Odyssey meets Interstellar"
        ),
        "pop_art": (
            "pop art style illustration, bold flat primary colors, "
            "Ben-Day dots pattern, thick black outlines, "
            "Andy Warhol and Roy Lichtenstein inspired, "
            "graphic design aesthetic, high contrast, "
            "screen print quality"
        ),
        "ukiyo_e": (
            "ukiyo-e Japanese woodblock print style, "
            "traditional composition with flat color areas, "
            "flowing calligraphic lines, nature and wave motifs, "
            "Hokusai Great Wave inspired, classical Japanese art, "
            "limited earth-tone palette with indigo accents"
        ),
        "impressionist": (
            "Impressionist painting style, visible brushstrokes, "
            "dappled natural light, en plein air aesthetic, "
            "Monet and Renoir inspired, soft color blending, "
            "atmospheric perspective, garden or landscape scene"
        ),
        "art_nouveau": (
            "Art Nouveau style illustration, flowing organic curves, "
            "decorative floral borders, Alphonse Mucha inspired, "
            "elegant female figure, muted jewel tones, "
            "ornamental typography space, poster quality"
        ),
        "default": (
            "artistic illustration, creative distinctive style, "
            "rich color palette, professional quality, "
            "engaging composition, gallery-worthy"
        ),
    },
}

# ── Aspect ratio recommendations per category ────────────────────────
CATEGORY_ASPECT_RATIOS = {
    "logo": "1:1",
    "poster": "3:4",
    "illustration": "4:3",
    "meme": "1:1",
    "game_asset": "1:1",
    "social_media": "1:1",
    "3d": "1:1",
    "education": "4:3",
    "fashion": "3:4",
    "food": "4:3",
    "pet": "1:1",
    "product": "1:1",
    "wedding": "3:4",
    "holiday": "4:3",
    "art_style": "4:3",
}

# Override for specific sub-styles
_STYLE_ASPECT_OVERRIDES = {
    ("social_media", "tiktok_cover"): "9:16",
    ("social_media", "story"): "9:16",
    ("social_media", "banner"): "16:9",
    ("social_media", "youtube_thumbnail"): "16:9",
    ("social_media", "xiaohongshu"): "3:4",
    ("poster", "movie"): "3:4",
    ("poster", "sports"): "3:4",
    ("fashion", "clothing"): "3:4",
    ("wedding", "save_the_date"): "4:3",
}

MAX_COUNT = 4
DEFAULT_COUNT = 1
VALID_ASPECT_RATIOS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
}
DEFAULT_ASPECT_RATIO = "1:1"
VALID_OUTPUT_FORMATS = {"jpeg", "png", "webp"}
DEFAULT_OUTPUT_FORMAT = "png"
OUTPUT_DIR = "output/images"


def _get_auth_key():
    """Return the appropriate fal API key."""
    return _FAL_KEY if _LOCAL_MODE else 'fake-falai-key-12345'


def _get_model_config(model_key):
    """Return model config dict for the given key."""
    return MODELS.get(model_key, MODELS[DEFAULT_MODEL])


def _resolve_reference_image(image_path=None, image_url=None):
    """Resolve optional reference image to a URL for the fal API.

    This skill is primarily text-to-image, but supports an optional
    reference image for design guidance.

    Returns (url_string, error_string). Both can be None (no reference).
    """
    if not image_path and not image_url:
        return None, None

    if image_path:
        p = Path(image_path)
        if not p.exists():
            return None, f"File not found: {image_path}"
        if not p.is_file():
            return None, f"Not a file: {image_path}"

        ext = p.suffix.lower()
        if ext not in SUPPORTED_IMAGE_EXTS:
            return None, (
                f"Unsupported image format: {ext}. "
                f"Supported: {', '.join(sorted(SUPPORTED_IMAGE_EXTS))}"
            )

        size = p.stat().st_size
        if size > MAX_IMAGE_BYTES:
            return None, (
                f"Image too large: {size / 1024 / 1024:.1f} MB "
                f"(max {MAX_IMAGE_BYTES / 1024 / 1024:.0f} MB)"
            )

        mime_type = mimetypes.guess_type(str(p))[0] or "image/jpeg"
        with open(p, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
        return f"data:{mime_type};base64,{b64}", None

    if not image_url.startswith(("http://", "https://")):
        return None, (
            "image_url must be a public HTTP(S) URL. "
            "For local files, use the image_path parameter instead."
        )
    return image_url, None


def _build_prompt(prompt=None, category=None, style=None):
    """Construct the generation prompt.

    Priority:
      1. prompt + category/style — user prompt enhanced with style template
      2. prompt only — used as-is
      3. category + style — lookup from CATEGORY_STYLES
      4. category only — use category's "default" style

    Returns the final prompt string.
    """
    if prompt:
        if category and category in CATEGORY_STYLES:
            style_key = style or "default"
            style_prompt = CATEGORY_STYLES[category].get(
                style_key, CATEGORY_STYLES[category].get("default", "")
            )
            if style_prompt:
                return f"{prompt}, {style_prompt}"
        return prompt

    if category and category in CATEGORY_STYLES:
        style_key = style or "default"
        style_prompt = CATEGORY_STYLES[category].get(
            style_key, CATEGORY_STYLES[category].get("default")
        )
        if style_prompt:
            return style_prompt

    # Fallback: search all categories for the style key
    if style and not category:
        for cat, styles in CATEGORY_STYLES.items():
            if style in styles:
                return styles[style]

    return prompt or "high quality image, professional photography, detailed"


def _get_recommended_aspect_ratio(category=None, style=None):
    """Return the recommended aspect ratio for a category/style combo."""
    if category and style:
        override = _STYLE_ASPECT_OVERRIDES.get((category, style))
        if override:
            return override
    if category:
        return CATEGORY_ASPECT_RATIOS.get(category, DEFAULT_ASPECT_RATIO)
    return DEFAULT_ASPECT_RATIO


def _aspect_ratio_to_size(aspect_ratio):
    """Convert aspect ratio string to fal image_size dict.

    Sizes aligned with image_generate tool capabilities
    (core/image_models.py _STD_ASPECTS / _NANO2_ASPECTS).
    """
    mapping = {
        "1:1":  {"width": 1024, "height": 1024},
        "2:3":  {"width": 680,  "height": 1024},
        "3:2":  {"width": 1024, "height": 680},
        "3:4":  {"width": 768,  "height": 1024},
        "4:3":  {"width": 1024, "height": 768},
        "4:5":  {"width": 816,  "height": 1024},
        "5:4":  {"width": 1024, "height": 816},
        "9:16": {"width": 576,  "height": 1024},
        "16:9": {"width": 1024, "height": 576},
        "21:9": {"width": 1024, "height": 440},
    }
    return mapping.get(aspect_ratio, mapping["1:1"])


def _build_request_body(prompt, aspect_ratio, reference_url=None, model_key="nanopro",
                        count=1, output_format="png"):
    """Build the request body for the fal API."""
    body = {
        "prompt": prompt,
        "num_images": count,
        "seed": int(time.time() * 1000) % (2**32),
        "output_format": output_format,
    }

    # nano2/nanopro use aspect_ratio string; gpt uses image_size object
    if model_key != "gpt":
        body["aspect_ratio"] = aspect_ratio
    else:
        body["image_size"] = _aspect_ratio_to_size(aspect_ratio)
        body["quality"] = "high"

    if reference_url:
        # Both models use image_urls array for edit mode
        body["image_urls"] = [reference_url]

    return body


def _submit_request(prompt, aspect_ratio, model_key, headers, reference_url=None,
                    count=1, output_format="png"):
    """Submit a generation request to the fal queue."""
    cfg = _get_model_config(model_key)

    if reference_url:
        model_id = cfg["edit"]
    else:
        model_id = cfg["generate"]

    submit_url = f"https://queue.fal.run/{model_id}"
    body = _build_request_body(prompt, aspect_ratio, reference_url, model_key,
                               count=count, output_format=output_format)

    resp = requests.post(
        submit_url, headers=headers, json=body,
        proxies=PROXIES, verify=False, timeout=90,
    )

    record_response(resp, request_url=submit_url, request_payload=body)

    if resp.status_code != 200:
        return None, f"Submit failed: {resp.status_code} - {resp.text[:300]}"

    data = resp.json()
    cost = float(resp.headers.get('X-Credits-Used', 0))
    data['_cost'] = cost
    return data, None


def _poll_until_done(status_url, request_id, model_key):
    """Poll the fal queue until the request completes or fails."""
    cfg = _get_model_config(model_key)
    headers = {'Authorization': f'Key {_get_auth_key()}'}
    deadline = time.time() + cfg["timeout"]
    poll_interval = cfg["poll_interval"]

    while time.time() < deadline:
        try:
            poll_resp = requests.get(
                status_url, headers=headers,
                proxies=PROXIES, verify=False, timeout=60,
            )
            status_data = poll_resp.json()
            status = status_data.get('status')

            if status == 'COMPLETED':
                return "COMPLETED", None
            elif status in ('FAILED', 'CANCELLED'):
                return status, f"Generation {status}"
        except requests.RequestException:
            pass

        time.sleep(poll_interval)

    return "TIMEOUT", f"Generation timed out after {cfg['timeout'] // 60} minutes"


def _extract_image_urls(result_json):
    """Extract image URLs from fal response across model variants."""
    if not isinstance(result_json, dict):
        return []

    urls = []

    for key in ("images", "output", "outputs", "data"):
        arr = result_json.get(key)
        if isinstance(arr, list):
            for item in arr:
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    urls.append(item["url"])
                elif isinstance(item, dict) and isinstance(item.get("b64_json"), str):
                    urls.append(f"data:image/png;base64,{item['b64_json']}")
                elif isinstance(item, str) and item.startswith("http"):
                    urls.append(item)

    if not urls:
        for key in ("image", "output_image"):
            node = result_json.get(key)
            if isinstance(node, dict) and isinstance(node.get("url"), str):
                urls.append(node["url"])
            elif isinstance(node, str) and node.startswith("http"):
                urls.append(node)

    return urls


def _download_image(url, index, label, timestamp):
    """Download a single image from fal CDN to the output directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if url.startswith("data:"):
        ext = ".png"
        filename = f"{timestamp}_{label}_{index}{ext}"
        local_path = os.path.join(OUTPUT_DIR, filename)

        b64_data = url.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_data)

        with open(local_path, 'wb') as f:
            f.write(img_bytes)
        return local_path, len(img_bytes)

    ext = ".png"
    if ".jpg" in url or ".jpeg" in url:
        ext = ".jpg"
    elif ".webp" in url:
        ext = ".webp"

    filename = f"{timestamp}_{label}_{index}{ext}"
    local_path = os.path.join(OUTPUT_DIR, filename)

    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    with open(local_path, 'wb') as f:
        f.write(resp.content)

    return local_path, len(resp.content)


def generate_image(
    prompt=None,
    category=None,
    style=None,
    model=None,
    count=None,
    aspect_ratio=None,
    image_path=None,
    image_url=None,
    output_format=None,
):
    """Generate images from text prompts with optional category/style presets.

    This is the primary function for pure text-to-image generation.
    Optionally accepts a reference image for design guidance.

    Args:
        prompt: Text description of the desired image (recommended).
        category: Preset category (logo, poster, illustration, meme,
                  game_asset, social_media, 3d, education, fashion,
                  food, pet, wedding, holiday, art_style).
        style: Sub-style within the category (e.g., "tech" for logo).
        model: Model key — "nanopro" (default, fast) or "gpt" (best quality).
        count: Number of images to generate (1-4, default 1).
            Uses fal.ai native num_images for efficient batch generation.
        aspect_ratio: Output aspect ratio (1:1, 3:4, 4:3, 9:16, 16:9).
                      If not set, uses category-recommended ratio.
        image_path: Optional local file path for reference image.
        image_url: Optional public URL for reference image.
        output_format: Output image format — "png" (default), "jpeg", or "webp".

    Returns:
        dict with success status, generated image paths, and metadata.
    """
    if not prompt and not category:
        return {
            "success": False,
            "error": "Either 'prompt' or 'category' must be provided.",
        }

    # Resolve optional reference image
    ref_url, err = _resolve_reference_image(image_path, image_url)
    if err:
        return {"success": False, "error": err}

    # Validate and normalize parameters
    model_key = model if model in MODELS else DEFAULT_MODEL
    count = min(max(int(count or DEFAULT_COUNT), 1), MAX_COUNT)
    fmt = output_format if output_format in VALID_OUTPUT_FORMATS else DEFAULT_OUTPUT_FORMAT

    # Use explicit aspect_ratio, or fall back to category recommendation
    if aspect_ratio and aspect_ratio in VALID_ASPECT_RATIOS:
        final_ar = aspect_ratio
    else:
        final_ar = _get_recommended_aspect_ratio(category, style)

    final_prompt = _build_prompt(prompt=prompt, category=category, style=style)

    # Build a label for filenames
    label = category or "image"
    if style and style != "default":
        label = f"{label}_{style}"

    headers = caller_headers({
        'Authorization': f'Key {_get_auth_key()}',
        'Content-Type': 'application/json',
    }, tool_default='image-create')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    mode = "edit" if ref_url else "generate"
    results = []
    errors = []
    total_cost = 0.0

    # Single API call with num_images=count for efficient batch generation
    submit_data, err = _submit_request(
        final_prompt, final_ar, model_key, headers, ref_url,
        count=count, output_format=fmt,
    )
    if err:
        return {"success": False, "error": err}

    request_id = submit_data.get('request_id')
    status_url = submit_data.get('status_url')
    result_url = submit_data.get('response_url') or submit_data.get('result_url')
    cost = submit_data.get('_cost', 0)
    total_cost += cost

    print(f"Submitted: {request_id} (model={model_key}, count={count}, cost=${cost:.2f})")

    # Poll for completion
    status, poll_err = _poll_until_done(status_url, request_id, model_key)
    if status != "COMPLETED":
        return {
            "success": False,
            "request_id": request_id,
            "error": poll_err,
        }

    # Fetch result
    try:
        result_resp = requests.get(
            result_url,
            headers={'Authorization': f'Key {_get_auth_key()}'},
            proxies=PROXIES, verify=False, timeout=90,
        )
        result_json = result_resp.json()
    except Exception as e:
        return {
            "success": False,
            "request_id": request_id,
            "error": f"Failed to fetch result: {e}",
        }

    # Handle fal error responses
    if result_resp.status_code != 200:
        detail = result_json.get("detail", result_resp.text[:300])
        return {
            "success": False,
            "request_id": request_id,
            "error": f"fal error ({result_resp.status_code}): {detail}",
        }

    # Extract and download images
    image_urls = _extract_image_urls(result_json)
    if not image_urls:
        detail = result_json.get("detail")
        if detail:
            err_msg = f"fal error: {detail}"
        else:
            err_msg = (
                f"No image URL found in response. "
                f"Keys: {list(result_json.keys())}"
            )
        return {
            "success": False,
            "request_id": request_id,
            "error": err_msg,
        }

    for img_url in image_urls:
        try:
            local_path, size_bytes = _download_image(
                img_url, len(results), label, timestamp,
            )
            results.append({
                "url": img_url if not img_url.startswith("data:") else "(base64)",
                "local_path": local_path,
                "size_bytes": size_bytes,
                "request_id": request_id,
            })
        except Exception as e:
            errors.append({
                "request_id": request_id,
                "error": f"Download failed: {e}",
            })

    if not results:
        return {
            "success": False,
            "error": "All download attempts failed",
            "errors": errors,
        }

    return {
        "success": True,
        "model": model_key,
        "mode": mode,
        "category": category,
        "style": style,
        "prompt": final_prompt,
        "aspect_ratio": final_ar,
        "output_format": fmt,
        "count_requested": count,
        "count_generated": len(results),
        "total_cost": round(total_cost, 4),
        "images": results,
        "errors": errors if errors else None,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_image.py <prompt> [category] [style] [count] [model]")
        print(f"\nCategories: {', '.join(sorted(CATEGORY_STYLES.keys()))}")
        print(f"\nModels: {', '.join(MODELS.keys())}")
        print("\nSet FAL_KEY env var for local testing (direct fal.ai access).")
        sys.exit(1)

    prompt_arg = sys.argv[1]
    cat_arg = sys.argv[2] if len(sys.argv) > 2 else None
    style_arg = sys.argv[3] if len(sys.argv) > 3 else None
    count_arg = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    model_arg = sys.argv[5] if len(sys.argv) > 5 else "nanopro"

    if _LOCAL_MODE:
        print("Local mode: using FAL_KEY directly (no sc-proxy)")

    result = generate_image(
        prompt=prompt_arg,
        category=cat_arg,
        style=style_arg,
        count=count_arg,
        model=model_arg,
    )
    print(json.dumps(result, indent=2))