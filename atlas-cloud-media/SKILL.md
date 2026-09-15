---
name: atlas-cloud-media
version: 1.0.0
description: |
  Generate images, videos, and audio through Atlas Cloud's unified asynchronous API.

  Use when an agent needs model discovery or a callable media workflow with explicit billing boundaries, bounded polling, and local output downloads.
author: Atlas Cloud
tags: [media, image, video, audio, generation]
delivery: script
metadata:
  starchild:
    emoji: "☁️"
    skillKey: atlas-cloud-media
    requires:
      bins: [python3]
      env: [ATLASCLOUD_API_KEY]
user-invocable: true
disable-model-invocation: false
---

# Atlas Cloud Media

Use Atlas Cloud's unified API to discover current models and run image, video,
or audio generation. The skill uses only the Python standard library.

## When to Use

- Find current Atlas Cloud image, video, or audio models before generation.
- Generate an image from a text prompt.
- Generate a short video from text or model-specific media inputs.
- Generate speech, music, or other audio supported by the selected model.
- Check an existing prediction without creating another billable request.

## Billing Boundary

`list_models()` and `prediction_status()` are read-only. The three
`generate_*()` functions create billable jobs. Get user confirmation before
calling a generation function. A generation POST is sent exactly once; only
the prediction GET is polled with bounded transient-error handling.

## How to Call

```bash
python3 - <<'EOF'
from core.skill_tools import _modules

atlas = _modules["atlas-cloud-media"]
models = atlas.list_models(kind="Image", search="qwen-image")
print(models[:3])
EOF
```

### `list_models(kind=None, search=None, limit=100)`

Read the live model catalog. `kind` accepts `Image`, `Video`, or `Audio`.
Returned entries retain the model's schema URL; inspect that schema before
passing model-specific parameters.

```python
atlas.list_models(kind="Audio", search="text-to-speech", limit=20)
```

### `prediction_status(prediction_id)`

Read one existing prediction. This function never submits a generation job.

```python
atlas.prediction_status("prediction-id")
```

### `generate_image(prompt, model, **params)`

Submit once, poll until terminal, and download output files.

```python
atlas.generate_image(
    prompt="A paper-cut city skyline at sunrise",
    model="qwen-image-3.0/text-to-image",
    size="1024*1024",
)
```

### `generate_video(prompt, model, **params)`

```python
atlas.generate_video(
    prompt="A slow dolly shot through a miniature paper forest",
    model="bytedance/seedance-2.5/text-to-video",
    duration=4,
    resolution="480p",
    ratio="16:9",
)
```

### `generate_audio(model, text=None, **params)`

Audio schemas differ: TTS models usually require `text`; music models may use
`prompt` or other fields. Read the live schema and pass only supported fields.

```python
atlas.generate_audio(
    model="xai/tts-v1",
    text="Atlas Cloud media generation is ready.",
    language="en",
    voice_id="eve",
)
```

All generation functions also accept:

- `output_dir`: local destination, default `output/atlas-cloud`
- `timeout`: total polling deadline in seconds
- `poll_interval`: seconds between status checks
- Additional keyword arguments are forwarded to the selected model schema.

## Result Shape

```json
{
  "success": true,
  "prediction_id": "...",
  "status": "completed",
  "model": "...",
  "outputs": ["https://..."],
  "local_paths": ["/absolute/path/to/output.mp3"]
}
```

## Safety and Failure Handling

- The API key is read only from `ATLASCLOUD_API_KEY`.
- Secrets are never returned in results or forwarded to output hosts.
- Downloads require HTTPS and reject local hostnames and non-public IP literals.
- Direct downloads verify resolved addresses; proxy-routed hostnames rely on the proxy's egress policy.
- Failed, cancelled, and timed-out predictions raise an explicit error.
- Partial downloads use a temporary file and are atomically renamed.
- Model IDs and parameters are not treated as permanent constants; query the
  catalog and linked schema at runtime.

## Dependencies

- Python 3.10 or newer
- `ATLASCLOUD_API_KEY` for prediction reads and generation
- Network access to `api.atlascloud.ai` and public output hosts
