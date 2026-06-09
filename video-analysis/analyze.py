"""
Video analysis core — native model passthrough + frame extraction fallback.

Two modes:
  1. Native: send video to a supports_video model via OpenRouter (high quality)
  2. Extraction: ffmpeg keyframes + Whisper audio transcription (any model)
"""

import base64
import json
import os
import subprocess
import tempfile
import time
import yaml

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.environ.get("WORKSPACE_DIR", "/data/workspace")

# Factory defaults ship inside the skill folder. They are OVERWRITTEN on every
# skill auto-update, so users must NOT edit this file — it is a template only.
SKILL_DEFAULT_CONFIG = os.path.join(SKILL_DIR, "config.yaml")

# User config lives in the workspace and PERSISTS across skill updates. It only
# needs the keys the user wants to override; everything else falls back to the
# shipped defaults. This is the file users should edit.
USER_CONFIG_PATH = os.path.join(WORKSPACE, "config", "video-analysis.yaml")

# ── helpers ──────────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively overlay `override` onto `base` (override wins)."""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_config() -> dict:
    """Load shipped defaults, then overlay the user's workspace config.

    Hot-reloads on every call. The user file (workspace/config/video-analysis.yaml)
    survives skill updates; the skill's own config.yaml is the factory default
    and gets overwritten on update, so it is treated as a template only.
    """
    try:
        with open(SKILL_DEFAULT_CONFIG) as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        cfg = {}
    try:
        if os.path.isfile(USER_CONFIG_PATH):
            with open(USER_CONFIG_PATH) as f:
                user = yaml.safe_load(f) or {}
            cfg = _deep_merge(cfg, user)
    except Exception:
        pass
    return cfg


def _seed_user_config() -> None:
    """Create a commented user-config template on first use (best-effort).

    Writes workspace/config/video-analysis.yaml with every override key present
    but commented out, so the active config still comes from shipped defaults
    until the user uncomments a line. No-op if the file already exists.
    """
    try:
        if os.path.isfile(USER_CONFIG_PATH):
            return
        os.makedirs(os.path.dirname(USER_CONFIG_PATH), exist_ok=True)
        template = (
            "# Video Analysis — user overrides (persists across skill updates).\n"
            "# Uncomment and edit only the keys you want to change. Anything left\n"
            "# commented falls back to the skill's shipped defaults.\n"
            "\n"
            "# Model for native video understanding (must support video input).\n"
            "# default_model: google/gemini-3.1-flash-lite\n"
            "\n"
            "# Videos <= this size (MB) use native mode; larger ones use frame\n"
            "# extraction + audio transcription.\n"
            "# native_size_limit_mb: 20\n"
            "\n"
            "# extraction:\n"
            "#   max_frames: 30\n"
            "#   short_video_interval_sec: 2\n"
            "#   scene_threshold: 0.3\n"
            "#   transcribe_audio: true\n"
        )
        with open(USER_CONFIG_PATH, "w") as f:
            f.write(template)
    except Exception:
        pass


def _resolve_path(path: str) -> str:
    """Resolve a workspace-relative or absolute path to an absolute path."""
    if os.path.isabs(path):
        return path
    return os.path.join(WORKSPACE, path)


def _ffmpeg_bin() -> str:
    """Get the ffmpeg binary path."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def _get_video_info(path: str) -> dict:
    """Get video duration, dimensions, and audio presence via ffmpeg -i."""
    import re
    ffmpeg = _ffmpeg_bin()
    size = os.path.getsize(path) if os.path.exists(path) else 0
    duration, width, height, has_audio = 0.0, 0, 0, False
    try:
        r = subprocess.run(
            [ffmpeg, "-i", path, "-hide_banner"],
            capture_output=True, text=True, timeout=30
        )
        info_text = r.stderr  # ffmpeg prints info to stderr

        # Parse duration: "Duration: HH:MM:SS.cs"
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", info_text)
        if dur_match:
            h, m, s, cs = dur_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100

        # Parse video stream resolution
        vid_match = re.search(r"Stream.*Video:.*?(\d{2,5})x(\d{2,5})", info_text)
        if vid_match:
            width, height = int(vid_match.group(1)), int(vid_match.group(2))

        # Check for audio stream
        has_audio = bool(re.search(r"Stream.*Audio:", info_text))
    except Exception:
        pass
    return {
        "duration": duration,
        "size": size,
        "width": width,
        "height": height,
        "has_audio": has_audio,
    }


# ── native mode ──────────────────────────────────────────────────────

def _analyze_native(path: str, question: str, config: dict, caller_id: str = "") -> dict:
    """Send video to a supports_video model via OpenRouter."""
    from core.http_client import proxied_post

    model = config.get("default_model", "google/gemini-3.1-flash-lite")
    file_size = os.path.getsize(path)

    # Determine mime type
    ext = os.path.splitext(path)[1].lower()
    mime_map = {
        ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
        ".avi": "video/x-msvideo", ".mkv": "video/x-matroska", ".mpeg": "video/mpeg",
    }
    mime_type = mime_map.get(ext, "video/mp4")

    # Read and encode
    with open(path, "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode("ascii")

    # Build request
    messages = [{
        "role": "user",
        "content": [
            {
                "type": "video_url",
                "video_url": {
                    "url": f"data:{mime_type};base64,{video_b64}",
                }
            },
            {
                "type": "text",
                "text": question or "Describe what happens in this video in detail.",
            }
        ]
    }]

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer fake-openrouter-key",
        "HTTP-Referer": "https://iamstarchild.com",
    }
    if caller_id:
        headers["SC-CALLER-ID"] = caller_id

    t0 = time.time()
    resp = proxied_post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={"model": model, "messages": messages, "max_tokens": 4096},
        headers=headers,
        timeout=120,
    )
    elapsed = time.time() - t0

    if resp.status_code != 200:
        return {
            "success": False,
            "mode": "native",
            "model": model,
            "error": f"OpenRouter returned {resp.status_code}: {resp.text[:500]}",
        }

    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})

    return {
        "success": True,
        "mode": "native",
        "model": model,
        "analysis": content,
        "tokens": {
            "input": usage.get("prompt_tokens", 0),
            "output": usage.get("completion_tokens", 0),
            "video": usage.get("prompt_tokens_details", {}).get("video_tokens", 0),
            "audio": usage.get("prompt_tokens_details", {}).get("audio_tokens", 0),
        },
        "elapsed_sec": round(elapsed, 1),
        "file_size_mb": round(file_size / 1024 / 1024, 1),
    }


# ── extraction mode ──────────────────────────────────────────────────

def _extract_frames(path: str, info: dict, config: dict) -> list:
    """Extract keyframes from video using ffmpeg."""
    ffmpeg = _ffmpeg_bin()
    ext_config = config.get("extraction", {})
    max_frames = ext_config.get("max_frames", 30)
    duration = info.get("duration", 0)

    tmpdir = tempfile.mkdtemp(prefix="vidframes_")

    if duration <= 60:
        # Short video: fixed interval
        interval = ext_config.get("short_video_interval_sec", 2)
        vf = f"fps=1/{interval}"
    else:
        # Long video: scene change detection
        threshold = ext_config.get("scene_threshold", 0.3)
        vf = f"select='gt(scene,{threshold})',showinfo"

    cmd = [
        ffmpeg, "-i", path,
        "-vf", vf,
        "-vsync", "vfr",
        "-frames:v", str(max_frames),
        "-q:v", "3",
        os.path.join(tmpdir, "frame_%04d.jpg"),
        "-y", "-loglevel", "warning"
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        pass

    frames = sorted([
        os.path.join(tmpdir, f)
        for f in os.listdir(tmpdir)
        if f.endswith(".jpg")
    ])

    # If scene detection gave too few frames, fall back to interval
    if len(frames) < 3 and duration > 5:
        interval = max(1, int(duration / max_frames))
        cmd2 = [
            ffmpeg, "-i", path,
            "-vf", f"fps=1/{interval}",
            "-vsync", "vfr",
            "-frames:v", str(max_frames),
            "-q:v", "3",
            os.path.join(tmpdir, "fallback_%04d.jpg"),
            "-y", "-loglevel", "warning"
        ]
        try:
            subprocess.run(cmd2, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            pass
        frames = sorted([
            os.path.join(tmpdir, f)
            for f in os.listdir(tmpdir)
            if f.endswith(".jpg")
        ])

    return frames[:max_frames]


def _transcribe_audio(path: str, config: dict, caller_id: str = "") -> str:
    """Extract audio and transcribe via a video-capable model (Gemini)."""
    from core.http_client import proxied_post

    ffmpeg = _ffmpeg_bin()
    tmpdir = tempfile.mkdtemp(prefix="vidaudio_")
    audio_path = os.path.join(tmpdir, "audio.mp3")

    # Extract audio track
    cmd = [
        ffmpeg, "-i", path,
        "-vn", "-acodec", "libmp3lame", "-ab", "64k", "-ar", "16000",
        "-ac", "1", audio_path,
        "-y", "-loglevel", "warning"
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        if r.returncode != 0 or not os.path.exists(audio_path):
            return ""
    except (subprocess.TimeoutExpired, Exception):
        return ""

    audio_size = os.path.getsize(audio_path)
    if audio_size < 1000:  # < 1KB = likely silence or no audio
        return ""

    # Send audio to a model that understands audio (reuse video model)
    model = config.get("default_model", "google/gemini-3.1-flash-lite")
    try:
        with open(audio_path, "rb") as af:
            audio_b64 = base64.b64encode(af.read()).decode("ascii")

        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_b64,
                        "format": "mp3",
                    }
                },
                {
                    "type": "text",
                    "text": (
                        "Transcribe the audio above verbatim. "
                        "Output ONLY the transcription text, nothing else. "
                        "If there is no speech, output '[no speech]'."
                    ),
                }
            ]
        }]

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer fake-openrouter-key",
            "HTTP-Referer": "https://iamstarchild.com",
        }
        if caller_id:
            headers["SC-CALLER-ID"] = caller_id

        resp = proxied_post(
            "https://openrouter.ai/api/v1/chat/completions",
            json={"model": model, "messages": messages, "max_tokens": 2048},
            headers=headers,
            timeout=60,
        )
        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip()
        else:
            return f"[Transcription failed: {resp.status_code}]"
    except Exception as e:
        return f"[Transcription error: {e}]"
    finally:
        try:
            os.remove(audio_path)
            os.rmdir(tmpdir)
        except OSError:
            pass


def _analyze_extraction(path: str, question: str, info: dict, config: dict,
                         caller_id: str = "") -> dict:
    """Analyze video via frame extraction + audio transcription."""
    t0 = time.time()
    ext_config = config.get("extraction", {})

    # 1. Extract frames
    frames = _extract_frames(path, info, config)

    # 2. Transcribe audio (if enabled and audio track exists)
    transcript = ""
    if ext_config.get("transcribe_audio", True) and info.get("has_audio", False):
        transcript = _transcribe_audio(path, config, caller_id)

    # 3. Build frame data
    frame_images = []
    for fp in frames:
        try:
            with open(fp, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            frame_images.append(b64)
        except Exception:
            continue

    elapsed = round(time.time() - t0, 1)
    duration = info.get("duration", 0)

    # Build summary for the agent
    result = {
        "success": True,
        "mode": "extraction",
        "frame_count": len(frame_images),
        "duration_sec": round(duration, 1),
        "file_size_mb": round(info.get("size", 0) / 1024 / 1024, 1),
        "has_audio": info.get("has_audio", False),
        "transcript": transcript if transcript else None,
        "elapsed_sec": elapsed,
    }

    # Save frames to output dir for agent to reference
    output_dir = os.path.join(WORKSPACE, "output", "video-frames")
    os.makedirs(output_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    frame_paths = []
    for i, b64 in enumerate(frame_images):
        frame_file = os.path.join(output_dir, f"{ts}_frame_{i:03d}.jpg")
        with open(frame_file, "wb") as f:
            f.write(base64.b64decode(b64))
        frame_paths.append(os.path.relpath(frame_file, WORKSPACE))

    result["frame_paths"] = frame_paths

    # Cleanup temp frames
    for fp in frames:
        try:
            os.remove(fp)
            parent = os.path.dirname(fp)
            if not os.listdir(parent):
                os.rmdir(parent)
        except OSError:
            pass

    return result


# ── main entry ───────────────────────────────────────────────────────

def analyze_video(path: str, question: str = "", caller_id: str = "") -> dict:
    """Analyze a video file.

    Args:
        path: Video file path (workspace-relative or absolute).
        question: What to analyze (default: general description).
        caller_id: SC-CALLER-ID for billing tracking.

    Returns:
        dict with keys:
          success, mode ("native"|"extraction"), analysis (if native),
          frame_paths + transcript (if extraction), tokens, elapsed_sec, etc.
    """
    _seed_user_config()
    config = _load_config()
    abs_path = _resolve_path(path)

    # Validate file exists
    if not os.path.isfile(abs_path):
        return {"success": False, "error": f"File not found: {path}"}

    # Get video info
    info = _get_video_info(abs_path)
    file_size_mb = info["size"] / 1024 / 1024
    threshold_mb = config.get("native_size_limit_mb", 20)

    # Decide mode
    if file_size_mb <= threshold_mb:
        # Native: send to video-capable model
        return _analyze_native(abs_path, question, config, caller_id)
    else:
        # Extraction: keyframes + transcription
        return _analyze_extraction(abs_path, question, info, config, caller_id)
