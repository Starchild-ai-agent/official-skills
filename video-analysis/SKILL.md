---
name: video-analysis
version: 1.1.0
description: |
  Video understanding for any model — native passthrough for small files,
  frame extraction + audio transcription fallback for large files.

  Use when the user asks to analyze, describe, or understand a video file
  (e.g. "what's in this video", "summarize this clip", "transcribe this recording").
metadata:
  starchild:
    emoji: "🎥"
    skillKey: video-analysis
delivery: script
user-invocable: true
disable-model-invocation: false
---

# Video Analysis

Analyze video files using either **native model understanding** or **frame extraction + transcription**.

## How It Works

```
analyze_video(path, question)
      │
      ├─ file_size ≤ threshold (default 20MB)
      │     → Send video to a supports_video model (default Gemini 3.1 Flash Lite)
      │     → Model sees full video natively (best quality)
      │
      └─ file_size > threshold
            → ffmpeg extracts keyframes (scene detection for long videos)
            → Whisper transcribes audio track
            → Returns frame image paths + transcript text
            → Agent feeds these to the current chat model
```

## Quick Start

⚠️ **Invocation — do NOT use dotted imports.** The directory name contains a
hyphen (`video-analysis`), so `from skills.video-analysis.exports import ...`
is a **Python syntax error** (`-` is parsed as minus). This is true for every
hyphenated skill, not just this one. Use one of the two patterns below.

**Pattern A — from workspace root (recommended for scripts):**
```bash
cd /data/workspace/skills/video-analysis && \
  python3 -c "from exports import analyze_video; \
    import json; \
    print(json.dumps(analyze_video('output/videos/clip.mp4', \
      question='What happens in this video?'), ensure_ascii=False))"
```
Note: pass the video path **workspace-relative** (analyze.py resolves it
against `WORKSPACE_DIR`), even though you cd into the skill dir.

**Pattern B — inside a starchild-clawd script:**
```python
from core.skill_tools import video_analysis
result = video_analysis.analyze_video("output/videos/clip.mp4",
                                      question="What happens in this video?")
```

❌ **Do NOT** `exec(open('skills/video-analysis/analyze.py').read())` — analyze.py
uses `__file__` at import time, which is undefined under `exec`, so it crashes.
Load it by file path with `importlib.util.spec_from_file_location` if you must
avoid both patterns above.

```python
# result keys (same for both patterns):
# Analyze a video — auto-selects native or extraction mode
# result = analyze_video("output/videos/clip.mp4", question="What happens in this video?")

# result keys:
#   success: bool
#   mode: "native" | "extraction"
#
# If mode == "native":
#   analysis: str (model's text response)
#   model: str (which model was used)
#   tokens: {input, output, video, audio}
#
# If mode == "extraction":
#   frame_paths: list[str] (workspace-relative paths to keyframe JPEGs)
#   transcript: str | None (Whisper transcription text)
#   frame_count: int
#   duration_sec: float
```

## Using the Exports

```python
from core.skill_tools import video_analysis

# Full analysis (auto-selects mode)
result = video_analysis.analyze_video("output/videos/my_video.mp4", question="Describe this video")

# Check current config
config = video_analysis.get_config()

# Get video metadata without analyzing
info = video_analysis.get_video_info("output/videos/my_video.mp4")
# → {"duration": 45.2, "size": 12345678, "width": 1920, "height": 1080, "has_audio": true}
```

## Native Mode (small videos)

For videos under the size threshold, the skill sends the full video to a model
that supports native video input. The model sees every frame and hears the audio.

**Default model:** `google/gemini-3.1-flash-lite` — best price/quality for video.

**Model benchmark** (6MB clip, vs `gemini-3.1-pro-preview` baseline):

| Model                       | Tier   | Cost     | Time  | Accuracy | Notes                          |
|-----------------------------|--------|----------|-------|----------|--------------------------------|
| google/gemini-3.1-flash-lite | budget | ~$0.0014 | 8.1s  | ~88%     | ⭐ Default — cheapest + fastest |
| google/gemini-3.5-flash     | std    | ~$0.0152 | 11.8s | ~85%     | More detail, higher cost       |
| qwen/qwen3.6-plus           | budget | ~$0.0058 | 44.2s | ~95%     | Accurate but slow              |
| qwen/qwen3.6-flash          | budget | ~$0.0027 | 16.6s | ~80%     | Misreads subjects sometimes    |
| google/gemini-3.1-pro-preview | std  | ~$0.0199 | 19.7s | 100%     | Baseline (best, most expensive)|

flash-lite identifies the full scene, action sequence, and transitions
correctly at ~14x lower cost than the Pro baseline. For maximum accuracy
(exact character names, fine detail), switch `default_model` to
`gemini-3.1-pro-preview` or `gemini-3.5-flash` in `config.yaml`.

## Extraction Mode (large videos)

For videos over the size threshold, the skill extracts keyframes and transcribes audio:

- **Short videos (≤60s):** One frame every N seconds (default: 2s)
- **Long videos (>60s):** Scene-change detection picks visually distinct frames
- **Audio:** Extracted and sent to Whisper for transcription
- **Max frames:** Capped at 30 (configurable) to control cost

The agent receives frame image paths and transcript text, then feeds them
to the current chat model as image attachments + context text.

## Configuration

Edit `skills/video-analysis/config.yaml` to customize:

```yaml
# Model for native video understanding
default_model: google/gemini-3.1-flash-lite

# Size threshold: native (≤) vs extraction (>)
# Set to 0 → always extraction. Set to 100 → always native.
native_size_limit_mb: 20

# Frame extraction settings
extraction:
  max_frames: 30                  # Max keyframes to extract
  short_video_interval_sec: 2     # Frame interval for ≤60s videos
  scene_threshold: 0.3            # Scene detection sensitivity (0.0-1.0)
  transcribe_audio: true          # Whether to Whisper-transcribe audio
```

### Available Video Models

| Model                         | Alias    | Tier     | Notes              |
|-------------------------------|----------|----------|--------------------|
| google/gemini-3.1-flash-lite  | flash31  | budget   | ⭐ Default, best price/quality |
| google/gemini-3.5-flash       | gemini35 | standard | More detail, higher cost |
| google/gemini-3.1-flash-lite  | flash31  | budget   | Cheapest option    |
| google/gemini-3.1-pro-preview | gemini   | standard | Highest quality    |
| qwen/qwen3.6-flash            | qwenf    | budget   | Good alternative   |
| qwen/qwen3.6-plus             | qwen     | budget   | —                  |
| minimax/minimax-m3             | mm3      | standard | —                  |
| meta-llama/llama-4-maverick    | maverick | standard | —                  |
| meta-llama/llama-4-scout       | scout    | budget   | —                  |
| xiaomi/mimo-v2.5               | mimo     | standard | —                  |
| z-ai/glm-5v-turbo             | glm5v    | standard | —                  |
| minimax/minimax-m2.7           | mm27     | budget   | Audio-only, no image |

## Agent Behavior

When the user provides a video file (via upload or file path) and the current
chat model does NOT support video:

1. Call `analyze_video(path, question)`.
2. If result mode is `"native"` → return `result["analysis"]` directly.
3. If result mode is `"extraction"` → use `result["frame_paths"]` as image
   references and `result["transcript"]` as context, then ask the current
   model to analyze based on the frames + transcript.

When the current model DOES support video, the backend handles it natively
via Phase 1 (base64 content block injection) — no need for this skill.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "File not found" | Check path is workspace-relative (e.g. `output/videos/x.mp4`) |
| Native mode returns error | Check `default_model` in config.yaml is valid |
| No audio transcription | Video may have no audio track; check `has_audio` in result |
| Too few frames extracted | Lower `scene_threshold` in config.yaml (e.g. 0.15) |
| Too many frames / high cost | Reduce `max_frames` or raise `scene_threshold` |
