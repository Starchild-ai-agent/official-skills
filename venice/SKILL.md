---
name: venice
version: 1.0.5
description: Venice AI — privacy-first uncensored AI platform. Image generation/edit/upscale, TTS, speech-to-text, embeddings, video generation/transcription, model catalog, character personas, and the BYOK onboarding guide for Venice chat. Use when the user mentions Venice, wants uncensored / private / TEE / E2EE inference, needs Venice-specific features (venice_parameters, character_slug, web_search citations), or wants to register Venice as a chat model.
delivery: script
metadata:
  starchild:
    emoji: "🟣"
    skillKey: venice
    requires:
      env:
      - VENICE_API_KEY
user-invocable: false
disable-model-invocation: false
---

# Venice AI

Privacy-first AI platform. OpenAI-compatible API at `https://api.venice.ai/api/v1`. Four privacy tiers — anonymized, private, TEE, E2EE. Zero data retention. No content filtering on most models.

This skill covers everything **except** chat completions. For chat, the right path is BYOK via the platform's `custom_models` tool — see "Chat onboarding" below.

## Quick capability map

| Surface | Function |
|---|---|
| Catalog | `list_models`, `list_model_traits`, `list_image_styles`, `list_characters` |
| Account | `account_balance` (balance + tier + rate-limit count) |
| Image | `image_generate`, `image_edit`, `image_upscale` |
| Audio | `tts`, `transcribe` |
| Embeddings | `embeddings` (default `text-embedding-bge-m3`, dim 1024) |
| Chat probe | `chat_with_venice_parameters` (one-shot) |
| Video | `video_quote`, `video_queue`, `video_retrieve`, `video_complete`, `video_generate` (full loop), `video_transcribe_youtube` |

Endpoints intentionally NOT wrapped: standalone `/tools/search/web` (Venice removed it; use `enable_web_search` via venice_parameters in chat instead), admin-scoped `/api_keys` and `/billing/usage` (require an admin key the BYOK key can't use).

## Setup

1. User goes to <https://venice.ai/settings/api>, creates a key.
2. Add the key to the workspace via secure input — **never paste in chat**:
   - If the user wants chat: call `custom_models(action='add_template', vendor='venice')`. Auto-pops the secure input and registers Venice for chat completions in one shot.
   - If the user only wants this skill (image/audio/embeddings): call `request_env_input(env_vars=[{key='VENICE_API_KEY', label='Venice API Key', required=True}], reason='Use Venice image/audio/embeddings via the venice skill')`.
3. The skill resolves the key in this order: `VENICE_API_KEY` → any `CUSTOM_KEY_VENICE_*` from BYOK registration. Either path works; both is fine.

`account_balance()` is the cheapest probe (200 OK = key works).

## Usage

```python
import sys
sys.path.insert(0, "/data/workspace/skills/venice")
from exports import (
    list_models, image_generate, image_edit, image_upscale,
    tts, transcribe, embeddings,
    list_image_styles, list_characters, list_model_traits,
    account_balance, chat_with_venice_parameters,
)
```

### Browse models

```python
# Default returns text models only — pass type_filter to scope.
text_vision = list_models(type_filter="text", only_capabilities=["supportsVision"])
images = list_models(type_filter="image")          # 28 image models
ttss   = list_models(type_filter="tts")            # 10 voices
private_only = list_models(type_filter="text", privacy="private")
all_models   = list_models(type_filter="all")      # ~244 entries — heavy, use sparingly
```

Each entry: `id, type, name, description, privacy, context_tokens, max_completion_tokens, capabilities, pricing_input_usd, pricing_output_usd, pricing_cache_input_usd, traits`.

`list_model_traits()` returns Venice's curated picks: `default`, `most_intelligent`, `most_uncensored`, `default_reasoning`, `default_vision`, `default_code`, `function_calling_default`, `fastest`. Use this when the user says "give me Venice's smartest model" — don't guess.

### Image generation

**Don't guess model IDs.** Venice rotates image models often (e.g. `flux-dev-uncensored` no longer exists; `flux-2-pro` does). Always confirm with `list_models(type_filter="image")` before passing a non-default `model=`. Same rule for `image_edit` and `image_upscale`.

```python
g = image_generate(
    "neon cyberpunk cat in the rain",
    model="venice-sd35",       # default; see list_models(type_filter='image') for others
    width=1024, height=1024,   # any aspect-ratio Venice supports
    steps=20,
    style_preset="Cinematic",  # see list_image_styles() for the 76 presets
    save_path="cat.webp",      # → output/images/cat.webp (platform convention)
)
print(g["saved_path"])
```

Returns `{id, model, prompt, width, height, image_b64 (always), saved_path, timing}`.

### Image edit

```python
e = image_edit(
    "output/images/cat.webp",
    "make the rain heavier and add lightning",
    model="qwen-edit",         # default ($0.04/edit). Other valid IDs:
                                # firered-image-edit, grok-imagine-edit,
                                # qwen-image-2-edit, qwen-image-2-pro-edit,
                                # wan-2-7-pro-edit, flux-2-max-edit,
                                # nano-banana-pro-edit, seedream-v5-lite-edit
    save_path="cat_edited.png",
)
```

`image` accepts: bytes, Path, file path, http(s) URL, data URI, or base64 string. Anything else gets base64-encoded for transport. Endpoint returns raw bytes (NOT JSON).

### Image upscale

```python
image_upscale("output/images/cat.webp", scale=2, save_path="cat_2x.png")
```

Topaz-quality upscale. Scale 2 or 4. ~3 MB result for a 512×512 source at 2x.

### TTS

```python
tts(
    "Welcome to Venice",
    model="tts-kokoro",        # default; alts: tts-xai-v1, tts-elevenlabs-turbo-v2-5,
                                # tts-orpheus, tts-chatterbox-hd, tts-inworld-1-5-max,
                                # tts-qwen3-0-6b, tts-qwen3-1-7b
    voice="af_alloy",          # voice list per model in Venice docs
    response_format="mp3",     # mp3 | opus | aac | flac | wav | pcm
    save_path="welcome.mp3",   # → output/audio/welcome.mp3
)
```

### Transcribe (STT)

```python
result = transcribe(
    "output/audio/welcome.mp3",
    model="openai/whisper-large-v3",  # default. Alt: stt-xai-v1
                                       # The `openai/` prefix is REQUIRED —
                                       # bare `whisper-large-v3` returns 404.
)
print(result["text"])      # transcribed text
print(result["duration"])  # seconds
```

### Embeddings

```python
out = embeddings(["hello world", "second sentence"])
# → {model, count, dim: 1024 (for bge-m3), vectors: list[list[float]], usage}
```

### Characters

```python
list_characters(limit=20)  # [{slug, name, description, tags}, ...]
# Use the slug in chat via venice_parameters['character_slug']
```

## Chat onboarding (BYOK is the answer)

Don't try to wrap chat completions in this skill. The platform has a first-class BYOK flow that handles streaming, history, cost tracking, and model-switcher integration.

**Standard flow when the user says "I want to chat with Venice":**

1. `custom_models(action='templates')` — confirm Venice is in the curated list (it is, with `supports_dynamic_models: true`).
2. Optional but recommended for picky users: `custom_models(action='list_vendor_models', vendor='venice')` — returns the live catalog (~75 text models) with capabilities, pricing, and privacy tier. Filter and present the top picks.
3. `custom_models(action='add_template', vendor='venice', upstream_model='<id>')` — registers Venice with one of Venice's models as the chat target. The `upstream_model` parameter accepts ANY id from step 2's response (Venice has dynamic discovery). Auto-pops the secure-input prompt for the API key.
4. Tell the user how to switch: `/model custom/<id>` in chat, or use the model picker.

**Recommended models (use `list_model_traits()` to keep this fresh):**

| Use case | Trait | Typical pick |
|---|---|---|
| Smartest text | `most_intelligent` | `zai-org-glm-4.7` |
| Uncensored | `most_uncensored` | `venice-uncensored-1-2` |
| Reasoning | `default_reasoning` | `qwen3-235b-a22b-thinking-2507` |
| Vision | `default_vision` | `qwen3-vl-235b-a22b` |
| Code | `default_code` | `qwen3-coder-*` |
| Cheap & fast | `fastest` | `llama-3.2-3b` |
| Function calling | `function_calling_default` | `zai-org-glm-4.7` |
| Privacy: TEE/E2EE | filter `list_models(privacy='tee')` or `'e2ee'` | varies |

Pricing varies wildly: `llama-3.2-3b` is $0.15/$0.60 per 1M tokens; `zai-org-glm-5-1` is $1.75/$5.50; Grok 4.20 is even higher. Always check `list_models()` before recommending if the user is cost-sensitive.

### venice_parameters — Venice-specific chat extensions

These pass through `extra_body` in the OpenAI-compatible chat-completions call. Currently the platform's BYOK chat path doesn't have a UI for them, so users typically:

- **Test them** here via `chat_with_venice_parameters()` to see what they do.
- **Use them in production** by directly calling Venice from a script (also via this skill's `chat_with_venice_parameters`, or any OpenAI SDK pointed at Venice).

```python
chat_with_venice_parameters(
    "What's the latest Bitcoin price?",
    venice_parameters={
        "enable_web_search": "on",            # "auto" | "on" | "off"
        "include_venice_system_prompt": False, # drop Venice's default sysprompt
        "enable_web_citations": True,         # ask for inline citations
    },
)
```

| Parameter | Type | Effect |
|---|---|---|
| `enable_web_search` | "auto" \| "on" \| "off" | Real-time web search via Brave (ZDR) |
| `enable_web_scraping` | bool | Auto-fetch URLs in user messages (Firecrawl) |
| `enable_web_citations` | bool | Inline citations in the response |
| `enable_x_search` | bool | xAI native search (web + X) for Grok models |
| `character_slug` | str | Use a Venice character persona (see `list_characters`) |
| `include_venice_system_prompt` | bool | Default True. Set False to strip Venice's defaults |
| `strip_thinking_response` | bool | Drop `<think>` blocks from reasoning model output |
| `disable_thinking` | bool | Force-off thinking on reasoning-capable models |
| `enable_e2ee` | bool | Enable E2EE on E2EE-capable models |

The Venice response echoes a `venice_parameters` block in the body so you can verify the request was actually applied (look for it in `raw_response_keys`).

## Errors

`VeniceError(status, message, body)` is raised on any 4xx/5xx. Common ones:

| Status | Message hint | Fix |
|---|---|---|
| 401 | `Admin API key required` | Endpoint needs an admin-scope key the BYOK key doesn't have. Skip — no workaround. |
| 401 | `VENICE_API_KEY not set` | Run `request_env_input` for `VENICE_API_KEY`, or `custom_models(add_template, vendor='venice')`. |
| 400 | `Invalid model id` | Wrong model name. Check `list_models(type_filter='image')` for valid ids — many models in `/models` are NOT valid for `/image/edit` (only the `*-edit` family). |
| 404 | `Specified model not found: …. Did you mean: …` | Use the suggested model name. STT requires `openai/whisper-large-v3` (with prefix). |

## Costs

This skill talks **directly** to Venice — costs are billed against the user's Venice balance, not against platform credits. The platform's per-tool ledger does NOT track Venice spend. Tell the user to check `account_balance()` periodically. Image edit is $0.04/edit, TTS depends on chars, image generate depends on resolution + steps.

`account_balance()` returns both `balance_usd` and `balance_diem` — Venice supports two parallel cost models:

### Pay-as-you-go (USD top-up) — default

User funds the API key with USD at <https://venice.ai/settings/api>. Each request decrements `balance_usd`. Standard SaaS billing. **This is what 99% of users want.**

### DIEM staking — for high-volume / always-on users

DIEM is an ERC-20 on Base. Each staked DIEM unlocks **$1 of AI compute per day, every day, no expiry** (unused daily credits do NOT roll over). Burning DIEM returns the locked VVV (Venice's native token) used to mint it.

Pricing in `list_models()` shows both currencies, e.g. GLM 5.1 input is `$1.75/1M usd, 1.75/1M diem` — meaning Venice's backend auto-detects whether the wallet behind the API key has staked DIEM and routes spend to that bucket first. **No skill changes needed** to use DIEM — the API key resolves the right pool server-side.

| Path | When it makes sense |
|---|---|
| USD top-up | Casual / variable usage. Pay only what you spend. Zero idle cost. |
| Stake DIEM | Daily Venice spend ≥ $1 sustained, OR running 24h agent loops, OR want predictable cost ceiling. Capital is locked in DIEM, but unused daily credits = pure waste, so size to floor of your daily usage. |

Break-even rule of thumb: stake N DIEM only if your projected daily Venice spend is ≥ $N. At any DIEM market price, the math is simple: 1 DIEM costs (current market price) once, gives $1/day forever — break-even time = price / 1.

Setup: `https://venice.ai/token` — connect a wallet on Base, stake there. **Never send DIEM directly to the contract address — use the staking page only.** This skill does NOT automate staking (involves wallet ops + Base chain + VVV/DIEM contracts that are out of scope for an inference skill); the user does it once on the website.

## Video

Video is **async** — the API returns a queue id and you poll. Use `video_generate()` for one-shot end-to-end (quote → queue → poll → download → optional cleanup), or call the four primitives directly when you need control.

**Audio support is per-model, not universal.** Pass `audio=True` only after confirming via `list_models(type_filter="video")` that the chosen model exposes audio capability. `wan-2-7-text-to-video` and most text-to-video models do NOT support audio — passing `audio=True` returns `400: This model does not support audio configuration`. The `video_queue` / `video_generate` defaults default to `audio=False` for that reason; opt in only when you've checked the capability.

```python
from exports import video_generate, video_quote, list_models

# Browse video models — confirm capabilities before picking
videos = list_models(type_filter="video")
# Common families: seedance-2-0-text-to-video, wan-2-7-text-to-video,
# seedance-2-0-image-to-video, seedance-2-0-reference-to-video, kling-o3-r2v.
# Upscale models use upscale_factor instead of resolution.
# Audio-capable models are a subset — check `capabilities` on each entry.

# 1. Cheap path — quote first (free, no balance charge)
q = video_quote(
    model="wan-2-7-text-to-video",
    duration="5s", aspect_ratio="16:9", resolution="720p",
    # audio omitted → defaults to False (safe for wan-2-7)
)
# {"quote": 0.55}  — USD against your Venice balance

# 2. End-to-end (charges balance, polls until done)
v = video_generate(
    model="wan-2-7-text-to-video",
    prompt="A golden retriever chasing a frisbee at sunset, slow motion.",
    duration="5s", resolution="720p",
    save_path="retriever.mp4",                           # → output/videos/retriever.mp4
    on_progress=lambda r: print(r.get("status"),
                                  r.get("execution_duration", 0) // 1000, "s"),
)
# {queue_id, saved_path, bytes, quote_usd, elapsed_s, polls, ...}
```

`video_generate` accepts every queue parameter via `**queue_kwargs`:

| Field | Purpose |
|---|---|
| `negative_prompt` | What to avoid |
| `image_url` | First-frame reference (image-to-video) |
| `end_image_url` | Last-frame reference (transition) |
| `audio_url` | Background music input (WAV/MP3, ≤30s, ≤15MB) |
| `video_url` | Video-to-video / upscale input (MP4/MOV/WebM) |
| `reference_image_urls` | Up to 9 character/style references |
| `elements` | Up to 4 advanced elements (Kling O3 R2V style); reference in prompt as `@Element1` |
| `scene_image_urls` | Up to 4 scene references; reference as `@Image1` |
| `upscale_factor` | 1 / 2 / 4 — for upscale models (use instead of resolution) |
| `delete_media_on_completion` | Auto-delete from Venice storage after retrieve |

**Manual loop** when you want fine control (interactive ETA, custom storage, batched jobs):

```python
queued = video_queue(model="...", prompt="...", duration="5s",
                      resolution="720p", aspect_ratio="16:9")
# Add audio=True only when the model's `capabilities` include audio.
qid = queued["queue_id"]
download_url = queued.get("download_url")  # only for VPS-backed models

while True:
    r = video_retrieve(model="...", queue_id=qid)
    if "video_bytes" in r:
        open("out.mp4", "wb").write(r["video_bytes"]); break
    if r.get("status") == "COMPLETED":
        # VPS-backed model — fetch download_url
        import requests; v = requests.get(download_url, timeout=120)
        open("out.mp4", "wb").write(v.content); break
    if r.get("status") != "PROCESSING":
        raise RuntimeError(r)
    time.sleep(5)

video_complete(model="...", queue_id=qid)  # cleanup
```

**Video transcription (YouTube only)**:

```python
video_transcribe_youtube("https://www.youtube.com/watch?v=...")
# → {"transcript": "...", "lang": "en"}
```

For arbitrary local audio/video files, use `transcribe()` (uploads to /audio/transcriptions and accepts file paths). For non-YouTube hosted video, strip audio with ffmpeg first then call `transcribe()`.

**Video errors** beyond the table above:

| Code | Meaning |
|---|---|
| 400 | Bad params: model doesn't support that duration/resolution combo, missing `image_url` for i2v, or `prompt` empty |
| 402 | Insufficient balance — top up at venice.ai |
| 413 | Payload too big — use hosted URLs instead of base64 data URIs |
| 422 | Content policy violation (rare on Venice but possible on i2v) |
| 503 | Queue saturated — wait and retry |

Gotchas:
- `duration` is required even for `Auto` (pass it explicitly).
- `download_url` from queue is valid 24h — fetch promptly.
- Upscale models require `upscale_factor`, NOT `resolution`.
- Quote varies wildly by model and duration — wan 5s @ 720p ≈ $0.55, seedance-2-0-pro 10s @ 1080p can be $5+.

## Don't

- Don't wrap chat as a function here. Use BYOK.
- Don't fabricate a model id from training data — Venice ships new models weekly. Always `list_models()` or `list_model_traits()` first.
- Don't ask the user to paste the API key in chat. Use `request_env_input` (or `custom_models add_template`).
