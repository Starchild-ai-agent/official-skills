---
name: video
version: 3.3.1
description: |
  AI video generation: text-to-video, image-to-video, video-to-video, model selection.

  Use when generating a short video clip from a prompt or reference (e.g. 5s clip of a cat in rain, animate this photo, restyle this video).
metadata:
  starchild:
    emoji: "🎬"
    skillKey: video
    requires:
      env: [FAL_KEY]
user-invocable: true
disable-model-invocation: false

---

# video

Use this skill for **all video-generation requests** on Starchild.

**Core principle:** call the provided scripts. Do not re-implement proxy/billing/upload plumbing.

---

## 1. Text-to-video (most common)

```python
exec(open('skills/video/generate_video.py').read())
result = generate_video(
    prompt="A cinematic drone shot over snowy mountains at sunrise",
    model="balanced",   # "budget" | "balanced" | "premium"
    duration=5,
)
# result -> {"success": True, "cost": 0.70, "video_url": "...", "local_path": "output/videos/..."}
```

`generate_video` automatically: submits → polls → fetches result → downloads mp4 to `output/videos/`.

### Delivering the result to the user — IMPORTANT

**Never hand the user the raw `video_url` (e.g. `https://*.fal.media/.../*.mp4`).** fal serves these files with `Content-Security-Policy: sandbox; default-src 'none'`, which means:

- Opening the link in a browser shows a **blank page** (no inline player triggered).
- Embedding via `<video>` / `<iframe>` is blocked by CSP.
- There is no `Content-Disposition: attachment` header, so the browser does not auto-download either.
- URL-side tweaks (query params, `?download=1`, etc.) **cannot fix this** — only a server-side header change would, and we don't control fal's CDN.

The only reliable user-facing delivery path is the **already-downloaded local file**:

1. Use `result["local_path"]` (e.g. `output/videos/xxx.mp4`) — `generate_video` always downloads on success.
2. Tell the user the file is saved to `output/videos/<filename>` and is viewable in the workspace file panel / file browser.
3. On Web channel, also embed it inline so the user can preview it in chat:
   ```markdown
   ![video](output/videos/<filename>.mp4)
   ```
   (or link as `[video](output/videos/<filename>.mp4)` — the workspace serves these directly with the right headers).
4. On Telegram / WeChat: send the file via `send_to_telegram(file_path="output/videos/...", message_type="video")` or `send_to_wechat(file_path="output/videos/...", message_type="video")`.

If the download somehow failed (`local_path` missing) — re-fetch with:
```bash
curl -L -o output/videos/<filename>.mp4 "<video_url>"
```
Then deliver the local path. Still **do not** give the user the raw fal URL as the primary deliverable.

---

## 2. Image-to-video / video-to-video (reference assets)

fal.ai needs the reference asset as a **public https URL**. fal storage upload requires a Serverless permission your key currently does not have. The reliable path is to expose the asset via **a published Starchild preview**.

### Standard procedure

1. **Drop or copy the asset** into `output/fal_assets/` using `publish_asset.py`.
2. **Make sure a preview named `fal-assets` is running and published** (one-time setup, see §3).
3. **Build the public URL** as `<preview_base>/<filename>`.
4. **Call `generate_video(... image_url=public_url)`**.

```python
# Step 1: publish a local image into the asset folder
exec(open('skills/video/publish_asset.py').read())
asset = publish_local('/path/to/your/photo.jpg')
# or: publish_from_url('https://example.com/photo.jpg')

filename = asset['filename']

# Step 2: combine with the preview's public base URL (see §3)
public_url = f"https://community.iamstarchild.com/<user_slug>-fal-assets/{filename}"

# Step 3: image-to-video
exec(open('skills/video/generate_video.py').read())
result = generate_video(
    prompt="gentle cinematic camera push-in",
    model="balanced",
    duration=5,
    image_url=public_url,
)
```

`generate_video` auto-rewrites the model path from `*/text-to-video` to `*/image-to-video` whenever `image_url` is provided. The same approach works for video-to-video models — pass an mp4 URL instead.

### Asset constraints (enforced by `publish_asset.py`)

- Image: `.jpg .jpeg .png .webp .gif .bmp`, max **10 MB**
- Video: `.mp4 .mov .webm .mkv .m4v`, max **100 MB**
- Anything outside these is rejected before publish

---

## 3. One-time `fal-assets` public preview setup

Run this once per workspace. The preview keeps running across sessions.

```python
# 3.1 ensure the asset folder exists with a placeholder index
import os, pathlib
pathlib.Path('output/fal_assets').mkdir(parents=True, exist_ok=True)
if not os.path.exists('output/fal_assets/index.html'):
    open('output/fal_assets/index.html', 'w').write(
        '<!doctype html><html><body><h1>fal asset host</h1></body></html>'
    )

# 3.2 start the preview
preview(action='serve', dir='output/fal_assets', title='fal-assets')

# 3.3 publish to a public URL
preview(action='publish', preview_id='<id from step 3.2>', slug='fal-assets', title='fal-assets')
# → public base: https://community.iamstarchild.com/<user_slug>-fal-assets/
```

After publish, the public base URL is reusable for every future image-to-video / video-to-video task. Files dropped into `output/fal_assets/` become reachable as `<base>/<filename>` immediately — no re-publish needed.

Verify with:
```bash
curl -sI https://community.iamstarchild.com/<user_slug>-fal-assets/<filename>
# expect: HTTP/2 200, content-type: image/* or video/*
```

If `preview(action='serve')` returns `No available ports in pool`, ask the user which existing preview can be stopped to free a port — never silently kill one.

---

## 4. Model selection

| Tier | Model | Cost / 5s | Notes |
|------|-------|-----------|-------|
| **budget** | `fal-ai/wan/v2.5/text-to-video` | $0.25 | Fastest, cheapest; good for prompt iteration |
| **balanced** | `alibaba/happy-horse/text-to-video` | $0.70 | Default; best lip-sync, most use cases |
| **premium** | `bytedance/seedance-2.0/fast/text-to-video` | $1.20 | Best motion + camera direction |
| **mini** | `bytedance/seedance-2.0/mini/text-to-video` | $0.36 (480p) / $0.77 (720p) | Cheapest Seedance; resolution-tiered, no 1080p. **Duration must be a string** (`"5"`, not `5` or `"5s"`) — see gotcha below |

Override by passing the full model id to `generate_video(model=...)`. Image-to-video variants are auto-derived by replacing `text-to-video` with `image-to-video`.

Pricing details and model registry live in `generate_video.py::estimate_cost`.

---

## 5. Polling an existing request

```python
exec(open('skills/video/poll_status.py').read())
result = poll_video("019ded6c-d871-7290-bbf1-ddc6993f8958")
```

Use this when an earlier `generate_video` call timed out or you only have a `request_id`.

---

## 6. Provided scripts

- `generate_video.py` — submit → poll → download. Handles text-to-video and image-to-video.
- `publish_asset.py` — copy local files (or download remote URLs) into `output/fal_assets/` so they can be served by the `fal-assets` preview.
- `poll_status.py` — resume polling by `request_id`, downloads the result on completion.

---

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| `image_url must be a public HTTP(S) URL` | Use `publish_asset.py` + `fal-assets` preview, then pass the public URL |
| `No available ports in pool` (preview serve) | Ask the user which preview to stop; do not auto-kill |
| `downstream_service_error` after `COMPLETED` | Reference asset host failed mid-render — re-encode/resize to 16:9, re-publish, retry |
| `HTTP 402 insufficient_credits` | Top up balance; cost is pre-charged on submit |
| `HTTP 403 endpoint_not_allowed` | sc-proxy only allows approved fal video endpoints; pick one from the model table |
| Generation `FAILED` upstream | Shorten prompt, drop unusual tokens, retry once before changing model |
| `HTTP 422 literal_error` on `duration` (Seedance Mini) | Mini requires `duration` as a **string** (`"5"`, `"10"`, `"auto"`), not an int and not `"5s"`. `generate_video()` encodes this automatically when `model` contains `seedance-2.0/mini` — only hit this if you hand-build the request body. Other Seedance variants accept int/`"5s"` as before. |
| Job stuck `IN_PROGRESS` >15 min | Save `request_id`, resume later with `poll_status.py` |
| User reports the fal.media link "shows nothing" / "blank page" | Expected — fal serves with `CSP: sandbox; default-src 'none'`. Deliver the local file at `result["local_path"]` instead of the raw URL (see §1). |

---

## 8. Infrastructure (reference)

- Caller → `sc-proxy` → `queue.fal.run` (and `api.fal.ai`) → fal model providers
- All requests must include `Authorization: Key fake-falai-key-12345` (proxy injects the real `FAL_KEY`)
- Pre-charge happens at submit. Poll/result calls are free.
- Allowed endpoints: video text-to-video / image-to-video / video-to-video / edit-video for the registered models. Anything else returns `403 endpoint_not_allowed`.
- Final mp4 lives at `https://*.fal.media/...` — public CDN, no auth needed for download.

---

## 9. Maintenance

- Adding a new model → register price in `generate_video.py::estimate_cost` and in `transparent-proxy/apis/falai.py::_VIDEO_PRICING`.
- Asset hosting via fal storage upload is intentionally **not** used in this skill: the production `FAL_KEY` lacks Serverless permission. Keep using the preview-based approach until that changes.
