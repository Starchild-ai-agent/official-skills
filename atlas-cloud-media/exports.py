"""Public function surface for the Atlas Cloud media skill."""

from __future__ import annotations

import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_MODULE_PATH = os.path.join(_HERE, "atlas_cloud.py")
_SPEC = importlib.util.spec_from_file_location("_atlas_cloud_media", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"cannot load Atlas Cloud media module: {_MODULE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

list_models = _MODULE.list_models
prediction_status = _MODULE.prediction_status
generate_image = _MODULE.generate_image
generate_video = _MODULE.generate_video
generate_audio = _MODULE.generate_audio

__all__ = [
    "list_models",
    "prediction_status",
    "generate_image",
    "generate_video",
    "generate_audio",
]
