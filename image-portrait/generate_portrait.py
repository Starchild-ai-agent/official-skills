#!/usr/bin/env python3
"""Portrait generation script — identity-consistent portrait generation.

Supports three models:
  - nano2    (fal-ai/gemini-3.1-flash-image-preview/edit)   — fastest ~15s, good for drafts
  - nanopro  (fal-ai/gemini-3-pro-image-preview/edit) — balanced ~25s, good quality (default)
  - gpt      (openai/gpt-image-2/edit)     — best quality, slow ~150s

Modes:
  - With reference image (edit): preserves facial identity from a reference photo
  - Without reference image (text-to-image): generates from prompt only

Flow: resolve image → build prompt → submit to fal queue → poll → download.

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
        "edit": "fal-ai/gemini-3.1-flash-image-preview/edit",
        "generate": "fal-ai/gemini-3.1-flash-image-preview",
        "timeout": 90,        # nano2 faster
        "poll_interval": 2,
    },
    "nanopro": {
        "edit": "fal-ai/gemini-3-pro-image-preview/edit",
        "generate": "fal-ai/gemini-3-pro-image-preview",
        "timeout": 120,       # 2 min
        "poll_interval": 3,
    },
    "gpt": {
        "edit": "openai/gpt-image-2/edit",
        "generate": "openai/gpt-image-2",
        "timeout": 600,       # 10 min
        "poll_interval": 5,
    },
}
DEFAULT_MODEL = "nanopro"

# Supported image extensions for local file validation
SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

# ── Style prompt templates ───────────────────────────────────────────
# Each produces a distinct visual aesthetic while the model preserves
# facial identity from the reference photo.
STYLE_PROMPTS = {
    # === A: Identity-consistent character styles ===
    "professional": (
        "professional headshot portrait, business attire, soft diffused studio lighting, "
        "clean neutral gray background, sharp focus on face, head and shoulders framing, "
        "confident approachable expression, slight natural smile, "
        "high quality corporate photography, 85mm lens look"
    ),
    "artistic": (
        "artistic portrait, dramatic cinematic lighting with strong key light, "
        "creative composition, shallow depth of field, fine art photography, "
        "moody atmosphere, rich contrast, gallery-quality portrait, "
        "subtle rim lighting for depth"
    ),
    "anime": (
        "anime style portrait, Studio Ghibli inspired, detailed cel-shaded illustration, "
        "vibrant saturated colors, Japanese animation aesthetic, soft shading, "
        "large expressive eyes, beautiful character design, "
        "detailed scenic background with soft bokeh, clean line art"
    ),
    "cyberpunk": (
        "cyberpunk style portrait, neon pink and blue lights, futuristic city background "
        "with holographic signs and towering buildings, sci-fi aesthetic, "
        "cybernetic implant details, rain-soaked streets reflecting neon, "
        "Blade Runner atmosphere, volumetric fog, high-tech low-life"
    ),
    "oil_painting": (
        "oil painting portrait, classical art style, rich warm colors, "
        "visible impasto brushstrokes, museum quality, Rembrandt chiaroscuro lighting, "
        "renaissance master technique, canvas texture, deep saturated tones, "
        "dramatic light and shadow interplay"
    ),
    "watercolor": (
        "watercolor painting portrait, soft pastel colors, delicate brushwork, "
        "gentle color bleeding and wet-on-wet effects, visible paper texture, "
        "impressionist style, dreamy ethereal atmosphere, "
        "transparent color layers, artistic splashes"
    ),
    "vintage": (
        "vintage photography portrait, retro style, natural film grain, warm amber tones, "
        "1970s aesthetic, analog camera look with slight lens distortion, "
        "nostalgic mood, soft vignette, faded colors, Kodak Portra film emulation"
    ),
    "casual": (
        "casual lifestyle portrait, natural golden hour lighting, outdoor park setting "
        "with soft bokeh background, relaxed natural pose, candid feel, "
        "warm and inviting atmosphere, gentle breeze in hair, "
        "authentic moment captured"
    ),

    # === B: Personal showcase / dating / social ===
    "dating_cafe": (
        "dating app profile photo, sitting in a cozy artisan cafe, "
        "holding a latte with latte art, warm genuine smile, "
        "casual but stylish outfit, cafe interior with warm Edison bulb lighting, "
        "shallow depth of field, natural and approachable vibe"
    ),
    "dating_beach": (
        "dating app profile photo, golden hour sunset beach scene, "
        "casual summer outfit, natural relaxed smile, wind in hair, "
        "ocean waves and colorful sky in background, warm tones, "
        "candid lifestyle photography feel"
    ),
    "dating_city": (
        "dating app profile photo, urban street scene with interesting architecture, "
        "fashionable outfit, confident relaxed pose, "
        "city buildings and street life in soft bokeh background, "
        "natural daylight, editorial street style photography"
    ),
    "dating_restaurant": (
        "dating app profile photo, elegant restaurant setting with ambient lighting, "
        "smart casual attire, warm charming smile, "
        "refined dining atmosphere with candle light, "
        "shallow depth of field, sophisticated and approachable"
    ),
    "travel_europe": (
        "travel photography portrait, standing in front of Eiffel Tower in Paris, "
        "casual chic travel outfit, confident natural pose, "
        "European architecture and cobblestone streets, golden hour light, "
        "wanderlust aesthetic, authentic travel moment"
    ),
    "travel_japan": (
        "travel photography portrait, walking through bamboo forest path in Arashiyama Kyoto, "
        "casual comfortable outfit, serene peaceful atmosphere, "
        "tall bamboo stalks creating natural tunnel, dappled sunlight, "
        "Japanese zen aesthetic, contemplative mood"
    ),
    "travel_tropical": (
        "travel photography portrait, tropical island paradise, "
        "stylish resort wear, relaxed confident pose, "
        "crystal clear turquoise water and pristine white sand beach, "
        "palm trees, vivid blue sky, paradise vacation aesthetic"
    ),
    "sports_gym": (
        "fitness portrait, modern athletic wear, well-equipped gym background, "
        "energetic confident pose, healthy toned physique, "
        "dramatic gym lighting with rim light, "
        "motivational fitness photography, sharp detail"
    ),
    "sports_running": (
        "outdoor running portrait, professional athletic gear, scenic park trail, "
        "dynamic mid-stride running pose, sunny weather with lens flare, "
        "motion blur on background, energetic and determined expression, "
        "sports photography style"
    ),
    "social_media": (
        "social media profile photo, front-facing warm smile, "
        "clean simple pastel gradient background, bright even lighting, "
        "high clarity and sharpness, trendy aesthetic, "
        "optimized for circular crop, approachable and authentic"
    ),
    "linkedin": (
        "LinkedIn professional headshot, well-fitted suit or business casual, "
        "confident professional expression with slight smile, "
        "clean blurred office background with soft natural light, "
        "head and shoulders framing, trustworthy and competent appearance, "
        "corporate photography quality"
    ),
    "personal_brand": (
        "personal branding photo, modern co-working space or creative office, "
        "business casual attire reflecting personal style, "
        "confident approachable pose, natural window light, "
        "clean contemporary environment, thought leader aesthetic, "
        "editorial quality photography"
    ),

    # === D: Themed / scene portraits ===
    "christmas": (
        "Christmas themed portrait, wearing cozy Christmas sweater with festive pattern, "
        "beautifully decorated Christmas tree with twinkling lights and fireplace background, "
        "warm festive atmosphere, soft warm lighting, "
        "holiday joy expression, gift boxes and ornaments, winter wonderland feel"
    ),
    "halloween": (
        "Halloween themed portrait, creative elaborate Halloween costume and makeup, "
        "carved pumpkin lanterns and spider web decorations background, "
        "mysterious spooky atmosphere, dramatic purple and orange lighting, "
        "fog effects, haunted house aesthetic"
    ),
    "graduation": (
        "graduation portrait, wearing black academic gown and mortarboard cap, "
        "holding diploma with pride, university campus with classical architecture background, "
        "sunny day with blue sky, proud accomplished expression, "
        "celebratory confetti, milestone achievement photography"
    ),
    "wedding": (
        "wedding style portrait, wearing elegant white wedding dress or formal suit, "
        "beautiful garden or chapel setting with flower arrangements, "
        "romantic soft golden hour atmosphere, dreamy bokeh background, "
        "gentle loving expression, professional wedding photography quality"
    ),
    "business_speech": (
        "business keynote presentation scene, formal professional attire, "
        "on stage at conference with dramatic stage lighting, "
        "large presentation screen and engaged audience in background, "
        "confident authoritative gesture, TED talk aesthetic, "
        "professional event photography"
    ),
    "musician": (
        "musician portrait, performing on stage under dramatic colored spotlights, "
        "cool stylish performance outfit, passionate expression, "
        "musical instruments and stage equipment visible, "
        "concert atmosphere with volumetric light beams, "
        "rock star energy, live performance photography"
    ),
    "chef": (
        "chef portrait, wearing crisp white chef uniform and toque hat, "
        "professional stainless steel kitchen environment, "
        "action shot preparing gourmet dish, fresh ingredients visible, "
        "warm kitchen lighting, culinary expertise expression, "
        "food magazine photography quality"
    ),
    "outdoor_adventure": (
        "outdoor adventure portrait, professional hiking gear and backpack, "
        "dramatic mountain peak or canyon overlook backdrop, "
        "magnificent panoramic natural scenery, golden hour lighting, "
        "windswept hair, determined adventurous expression, "
        "National Geographic photography style"
    ),
    "pet_together": (
        "heartwarming portrait with a golden retriever in a sunny park, "
        "kneeling beside or hugging the dog, genuine joyful smile, "
        "warm natural afternoon light, green grass and trees background, "
        "authentic bond between person and pet, lifestyle photography"
    ),
    "reading": (
        "literary style portrait, sitting in a charming bookstore or vintage library, "
        "holding an open book, thoughtful contemplative expression, "
        "literary casual clothing, warm ambient lighting, "
        "floor-to-ceiling bookshelves background, intellectual aesthetic, "
        "cozy reading nook atmosphere"
    ),
    "night_city": (
        "city night scene portrait, standing on rooftop or observation deck, "
        "spectacular city skyline with twinkling lights in background, "
        "fashionable dark outfit, dramatic urban night lighting, "
        "neon reflections, cinematic night photography, "
        "moody atmospheric urban portrait"
    ),
    "hanfu": (
        "Chinese traditional Hanfu portrait, wearing exquisite flowing Hanfu robes "
        "with intricate embroidery and silk fabric, "
        "classical Chinese garden with pavilion, lotus pond, and willow trees, "
        "elegant poised pose, traditional hair accessories, "
        "soft natural lighting, ancient Chinese painting aesthetic"
    ),

    # === O: Digital avatar ===
    "avatar_3d": (
        "3D cartoon avatar, Pixar and Disney animation style, "
        "rounded smooth features, bright vibrant colors, cute friendly expression, "
        "clean gradient background, subsurface skin scattering, "
        "stylized proportions, high quality 3D render, "
        "character select screen aesthetic"
    ),
    "avatar_gaming": (
        "epic gaming avatar portrait, fantasy RPG hero character style, "
        "detailed ornate armor or costume with glowing enchantments, "
        "dramatic epic background with volumetric rays, "
        "digital art quality, League of Legends splash art style, "
        "battle-ready confident pose, high detail rendering"
    ),
    "avatar_vtuber": (
        "VTuber style avatar, anime character design with expressive large eyes, "
        "colorful stylized hair with highlights, clean white background, "
        "Live2D ready design, bold clean outlines, "
        "vibrant color palette, cute kawaii aesthetic, "
        "streaming personality character art"
    ),

    # === T: Children & family ===
    "child_portrait": (
        "adorable children's portrait, bright cheerful pastel colors, "
        "playful natural pose, soft diffused natural lighting, "
        "warm family atmosphere, genuine child's smile or laughter, "
        "whimsical background, professional children's photography, "
        "safe and joyful mood"
    ),
    "family_photo": (
        "family group portrait, coordinated matching outfits, "
        "beautiful park or professional studio setting, "
        "warm loving expressions and natural interactions, "
        "professional family photography with soft even lighting, "
        "genuine connection between family members, timeless quality"
    ),

    # === U: ID / passport photos ===
    "id_photo_white": (
        "official ID photo, formal business attire with collar visible, "
        "pure white background, perfectly front-facing centered composition, "
        "neutral calm expression with mouth closed, "
        "ICAO passport photo standard compliant, even flat lighting "
        "with no shadows on face or background, sharp focus on face"
    ),
    "id_photo_blue": (
        "official ID photo, formal business attire with collar visible, "
        "solid medium blue background, perfectly front-facing centered composition, "
        "neutral calm expression with mouth closed, "
        "visa photo standard compliant, even flat lighting "
        "with no shadows on face or background, sharp focus on face"
    ),
}

DEFAULT_STYLE = "professional"
MAX_COUNT = 4  # fal.ai API supports up to 4 images per call
DEFAULT_COUNT = 1
VALID_ASPECT_RATIOS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
}
DEFAULT_ASPECT_RATIO = "1:1"
VALID_OUTPUT_FORMATS = {"jpeg", "png", "webp"}
DEFAULT_OUTPUT_FORMAT = "png"
OUTPUT_DIR = "output/images"

# Polling configuration
POLL_TIMEOUT = 600  # 10 minutes max wait per image


def _get_auth_key():
    """Return the appropriate fal API key."""
    return _FAL_KEY if _LOCAL_MODE else 'fake-falai-key-12345'


def _resolve_image_input(image_path=None, face_image_url=None):
    """Resolve image input to a URL suitable for the fal API.

    Accepts either:
      - image_path: local workspace file path → read + base64 data URI
      - face_image_url: public HTTP(S) URL → used directly

    Returns (url_string, error_string). One of them is always None.
    """
    if image_path and face_image_url:
        # Both provided — prefer image_path (local file)
        pass
    elif not image_path and not face_image_url:
        return None, None  # text-to-image mode (no reference)

    # If a local path is provided, encode it as a data URI
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

    # URL provided
    if not face_image_url.startswith(("http://", "https://")):
        return None, (
            "face_image_url must be a public HTTP(S) URL. "
            "For local files, use the image_path parameter instead."
        )
    return face_image_url, None


def _get_model_config(model_key):
    """Return model config dict for the given key."""
    return MODELS.get(model_key, MODELS[DEFAULT_MODEL])


# Likeness preservation prefix — appended when a reference image is provided.
# Learned from avatar-portrait skill: explicit likeness instructions dramatically
# improve identity consistency across all models.
_LIKENESS_PREFIX = (
    "portrait preserving the subject's exact facial features and likeness, "
    "recognizable face shape, eyes, nose, and expression, "
)

# Styles that should NOT get the likeness prefix (pure generation styles)
_NO_LIKENESS_STYLES = {"avatar_3d", "avatar_gaming", "avatar_vtuber"}


def _build_prompt(style=None, scene=None, prompt=None, has_reference=False):
    """Construct the generation prompt.

    Priority:
      1. prompt (fully custom) — used as-is (likeness prefix still added if ref)
      2. style + scene — style prompt base + scene appended
      3. scene only — scene used as full prompt with portrait quality suffix
      4. style only — style prompt used as-is
      5. neither — default to professional style

    When has_reference=True and style is not in _NO_LIKENESS_STYLES,
    a likeness preservation prefix is prepended to improve identity consistency.
    """
    if prompt:
        if has_reference:
            return f"{_LIKENESS_PREFIX}{prompt}"
        return prompt

    style_key = style or DEFAULT_STYLE
    style_prompt = STYLE_PROMPTS.get(style_key)

    if not style_prompt and style:
        # Unknown style key — treat it as a custom description
        style_prompt = style

    if not style_prompt:
        style_prompt = STYLE_PROMPTS[DEFAULT_STYLE]

    if scene:
        base = f"{style_prompt}, {scene}"
    else:
        base = style_prompt

    # Add likeness prefix for edit mode (reference image provided),
    # except for avatar styles where stylization > likeness.
    if has_reference and style_key not in _NO_LIKENESS_STYLES:
        return f"{_LIKENESS_PREFIX}{base}"
    return base


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


def _build_request_body(image_url, prompt, aspect_ratio, model_key,
                        count=1, output_format="png"):
    """Build the request body for the fal API based on model type."""
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

    if image_url:
        # Both models use image_urls array for edit mode
        body["image_urls"] = [image_url]

    return body


def _submit_request(image_url, prompt, aspect_ratio, model_key, headers,
                    count=1, output_format="png"):
    """Submit a generation request to the fal queue."""
    cfg = _get_model_config(model_key)
    has_image = image_url is not None

    # Select edit vs generate endpoint
    model_id = cfg["edit"] if has_image else cfg["generate"]
    submit_url = f"https://queue.fal.run/{model_id}"

    body = _build_request_body(image_url, prompt, aspect_ratio, model_key,
                               count=count, output_format=output_format)

    resp = requests.post(
        submit_url, headers=headers, json=body,
        proxies=PROXIES, verify=False, timeout=90,
    )

    # Record cost for the submit call
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
            pass  # transient network error — keep polling

        time.sleep(poll_interval)

    return "TIMEOUT", f"Generation timed out after {cfg['timeout'] // 60} minutes"


def _extract_image_urls(result_json):
    """Extract image URLs from fal response across model variants.

    Known shapes:
      - {"images": [{"url": "...", "width": ..., "height": ...}]}
      - {"output": [{"url": "..."}]}
      - {"data": [{"url": "..."}]}  (openai models)
    """
    if not isinstance(result_json, dict):
        return []

    urls = []

    # Primary shape: images/output/data array
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

    # Fallback: single image object
    if not urls:
        for key in ("image", "output_image"):
            node = result_json.get(key)
            if isinstance(node, dict) and isinstance(node.get("url"), str):
                urls.append(node["url"])
            elif isinstance(node, str) and node.startswith("http"):
                urls.append(node)

    return urls


def _download_image(url, index, style_key, timestamp):
    """Download a single image from fal CDN to the output directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Handle base64 data URIs (from openai models)
    if url.startswith("data:"):
        ext = ".png"
        filename = f"{timestamp}_{style_key}_{index}{ext}"
        local_path = os.path.join(OUTPUT_DIR, filename)

        # Extract base64 data after the comma
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

    filename = f"{timestamp}_{style_key}_{index}{ext}"
    local_path = os.path.join(OUTPUT_DIR, filename)

    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    with open(local_path, 'wb') as f:
        f.write(resp.content)

    return local_path, len(resp.content)


def generate_portrait(
    image_path=None,
    face_image_url=None,
    style=None,
    scene=None,
    prompt=None,
    model=None,
    count=None,
    aspect_ratio=None,
    output_format=None,
):
    """Generate identity-consistent portraits.

    Provide either image_path (local file) or face_image_url (public URL)
    for identity-consistent generation. Omit both for text-to-image mode.

    Args:
        image_path: Local workspace file path to the user's face photo.
        face_image_url: Public HTTPS URL of the user's face photo.
        style: Preset style key (professional, anime, cyberpunk, etc.).
        scene: Custom scene description (appended to style prompt).
        prompt: Fully custom prompt (overrides style+scene).
        model: Model key — "nanopro" (default, fast) or "gpt" (best quality).
        count: Number of images to generate (1-4, default 1).
            Uses fal.ai native num_images for efficient batch generation.
        aspect_ratio: Output aspect ratio (1:1, 3:4, 4:3, 9:16, 16:9).
        output_format: Output image format — "png" (default), "jpeg", or "webp".

    Returns:
        dict with success status, generated image paths, and metadata.
    """
    # Resolve image input (local path or URL)
    resolved_url, err = _resolve_image_input(image_path, face_image_url)
    if err:
        return {"success": False, "error": err}

    # Validate and normalize parameters
    model_key = model if model in MODELS else DEFAULT_MODEL
    count = min(max(int(count or DEFAULT_COUNT), 1), MAX_COUNT)
    aspect_ratio = aspect_ratio if aspect_ratio in VALID_ASPECT_RATIOS else DEFAULT_ASPECT_RATIO
    fmt = output_format if output_format in VALID_OUTPUT_FORMATS else DEFAULT_OUTPUT_FORMAT
    style_key = style or DEFAULT_STYLE

    has_ref = resolved_url is not None
    final_prompt = _build_prompt(style=style, scene=scene, prompt=prompt, has_reference=has_ref)
    headers = caller_headers({
        'Authorization': f'Key {_get_auth_key()}',
        'Content-Type': 'application/json',
    }, tool_default='image-portrait')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    mode = "edit" if resolved_url else "generate"
    results = []
    errors = []
    total_cost = 0.0

    # Single API call with num_images=count for efficient batch generation
    submit_data, err = _submit_request(
        resolved_url, final_prompt, aspect_ratio, model_key, headers,
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
                img_url, len(results), style_key, timestamp,
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
        "style": style_key,
        "prompt": final_prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": fmt,
        "count_requested": count,
        "count_generated": len(results),
        "total_cost": round(total_cost, 4),
        "images": results,
        "errors": errors if errors else None,
    }


def generate_series(
    image_path=None,
    face_image_url=None,
    series=None,
    model=None,
    aspect_ratio=None,
):
    """Generate a series of themed portraits from a custom list.

    Args:
        image_path: Local workspace file path to the user's face photo.
        face_image_url: Public HTTPS URL of the user's face photo.
        series: List of dicts with keys: style, scene, prompt.
                Example: [{"style": "professional"}, {"style": "casual", "scene": "at a cafe"}]
        model: Model key — "nano2", "nanopro" (default), or "gpt".
        aspect_ratio: Output aspect ratio (applied to all images).

    Returns:
        dict with success status, all generated images, and metadata.
    """
    if not isinstance(series, list):
        return {"success": False, "error": "series must be a list of dicts (e.g. [{\"style\": \"professional\"}, ...])"}

    series_items = series
    series_name = "custom"

    all_results = []
    all_errors = []
    total_cost = 0.0

    for idx, item in enumerate(series_items):
        s = item.get("style") if isinstance(item, dict) else None
        sc = item.get("scene") if isinstance(item, dict) else None
        p = item.get("prompt") if isinstance(item, dict) else None

        print(f"\n── Series [{idx+1}/{len(series_items)}] style={s}, scene={sc}")

        result = generate_portrait(
            image_path=image_path,
            face_image_url=face_image_url,
            style=s,
            scene=sc,
            prompt=p,
            model=model,
            count=1,
            aspect_ratio=aspect_ratio,
        )

        if result.get("success"):
            all_results.extend(result.get("images", []))
            total_cost += result.get("total_cost", 0)
        else:
            all_errors.append({
                "series_index": idx,
                "style": s,
                "error": result.get("error"),
            })

    if not all_results:
        return {
            "success": False,
            "error": "All series generation attempts failed",
            "errors": all_errors,
        }

    return {
        "success": True,
        "series": series_name,
        "count_generated": len(all_results),
        "total_cost": round(total_cost, 4),
        "images": all_results,
        "errors": all_errors if all_errors else None,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_portrait.py <image_path_or_url> [style] [count] [model]")
        print(f"\nStyles: {', '.join(sorted(STYLE_PROMPTS.keys()))}")
        print(f"\nModels: {', '.join(MODELS.keys())}")
        print("\nSet FAL_KEY env var for local testing (direct fal.ai access).")
        sys.exit(1)

    src = sys.argv[1]
    style_arg = sys.argv[2] if len(sys.argv) > 2 else "professional"
    count_arg = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    model_arg = sys.argv[4] if len(sys.argv) > 4 else "nanopro"

    if _LOCAL_MODE:
        print(f"Local mode: using FAL_KEY directly (no sc-proxy)")

    # Auto-detect: URL vs local path
    if src.startswith(("http://", "https://")):
        result = generate_portrait(
            face_image_url=src, style=style_arg,
            count=count_arg, model=model_arg,
        )
    else:
        result = generate_portrait(
            image_path=src, style=style_arg,
            count=count_arg, model=model_arg,
        )
    print(json.dumps(result, indent=2))