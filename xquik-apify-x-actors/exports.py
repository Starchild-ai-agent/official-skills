"""Callable exports for Xquik's Apify X Actors."""

import importlib.util
import os

_HERE = os.path.dirname(__file__)
_MODULE_PATH = os.path.join(_HERE, "scripts", "xquik_actors.py")
_SPEC = importlib.util.spec_from_file_location("_xquik_actors", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Xquik Actor module unavailable. Reinstall the Skill.")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

get_actor_info = _MODULE.get_actor_info
run_tweet_scraper = _MODULE.run_tweet_scraper
run_follower_scraper = _MODULE.run_follower_scraper

__all__ = [
    "get_actor_info",
    "run_tweet_scraper",
    "run_follower_scraper",
]
