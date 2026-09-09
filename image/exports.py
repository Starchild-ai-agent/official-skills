"""Unified `image` skill exports — script-mode skill.

    python3 - <<'EOF'
    import sys; sys.path.insert(0, "skills/image")
    from exports import edit, generate, inspect, list_models
    r = edit("replace the first W with the logo in image 2", ["uploads/sign.png", "uploads/logo.png"],
             model="nanopro", keep="all other letters, sign color, background", resolution="2K")
    print(r["images"][0]["local_path"] if r["success"] else r["error"])
    EOF
"""
import os, sys
_D = os.path.dirname(os.path.abspath(__file__))
if _D not in sys.path:
    sys.path.insert(0, _D)
from image_skill import (  # noqa: E402
    generate, edit, remove_background, inspect, recover, list_models,
    start_transaction, approve, reject, transaction,
)
__all__ = ["generate", "edit", "remove_background", "inspect", "recover", "list_models",
           "start_transaction", "approve", "reject", "transaction"]
