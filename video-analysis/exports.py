"""Video analysis skill exports."""

import os
import sys

# Ensure skill dir is importable
_skill_dir = os.path.dirname(os.path.abspath(__file__))
if _skill_dir not in sys.path:
    sys.path.insert(0, _skill_dir)

from analyze import analyze_video, _load_config, _get_video_info, _resolve_path

__all__ = ["analyze_video", "get_config", "get_video_info"]


def get_config() -> dict:
    """Return current video-analysis config."""
    return _load_config()


def get_video_info(path: str) -> dict:
    """Get video metadata (duration, size, dimensions, has_audio)."""
    abs_path = _resolve_path(path)
    return _get_video_info(abs_path)
