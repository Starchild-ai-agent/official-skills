"""
web-crawler skill exports — script-mode helpers.

Why this file exists: agents kept hand-rolling proxied_get/proxied_post calls,
which made them wonder "where's the API key?" and waste turns. There is NO key
to find — sc-proxy injects ScrapeCreators + Firecrawl credentials automatically.
Call these functions and ignore auth entirely.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/web-crawler")
    from exports import youtube_transcript, scrape_page, sc_get
    print(youtube_transcript("https://www.youtube.com/watch?v=VIDEO_ID"))
    EOF

Or via the platform loader:
    from core.skill_tools import web_crawler
    web_crawler.scrape_page("https://example.com/article")

NO API KEY NEEDED for any function here. Do not read $SCRAPECREATORS_API_KEY or
$FIRECRAWL_API_KEY, do not check .env, do not ask the user. Proxy handles it.
"""
from core.http_client import proxied_get, proxied_post

SC_BASE = "https://api.scrapecreators.com"
FC_BASE = "https://api.firecrawl.dev"
_DEFAULT_CALLER = "chat:web-crawler"


def _headers(caller_id=None):
    return {"SC-CALLER-ID": caller_id or _DEFAULT_CALLER}


def _strip(value):
    """Normalize a handle/hashtag: drop leading @ or # that the API rejects."""
    if isinstance(value, str):
        return value.lstrip("@#").strip()
    return value


# ---------------------------------------------------------------------------
# Generic backends — use these for any endpoint not wrapped below.
# ---------------------------------------------------------------------------
def sc_get(path, caller_id=None, timeout=30, **params):
    """Generic ScrapeCreators GET. `path` is the endpoint, e.g.
    '/v1/tiktok/profile'. Pass query params as kwargs:
        sc_get('/v1/tiktok/profile', handle='charlidamelio')
    Handle/hashtag values are auto-stripped of leading @/#.
    Returns parsed JSON. No api key needed — proxy injects it.
    """
    if not path.startswith("/"):
        path = "/" + path
    for k in ("handle", "hashtag"):
        if k in params:
            params[k] = _strip(params[k])
    resp = proxied_get(SC_BASE + path, params=params,
                       headers=_headers(caller_id), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def scrape_page(url, formats=None, only_main_content=True, caller_id=None,
                timeout=90, **extra):
    """Firecrawl fallback for ONE web page when ordinary fetch is blocked
    (403/429/anti-bot/JS-heavy). Returns parsed JSON; the markdown lives at
    result['data']['markdown']. No api key needed — proxy injects it.
        scrape_page('https://example.com/article')
        scrape_page(url, formats=['rawHtml'])   # retry when markdown misses fields
    """
    payload = {
        "url": url,
        "formats": formats or ["markdown", "links"],
        "onlyMainContent": only_main_content,
        "timeout": 60000,
    }
    payload.update(extra)
    resp = proxied_post(FC_BASE + "/v2/scrape", json=payload,
                        headers=_headers(caller_id), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def scrape_markdown(url, caller_id=None, **kw):
    """Convenience: scrape_page and return just the markdown string (or '')."""
    data = scrape_page(url, caller_id=caller_id, **kw)
    return (data.get("data") or {}).get("markdown", "")


# ---------------------------------------------------------------------------
# High-frequency named wrappers (thin sugar over sc_get).
# ---------------------------------------------------------------------------
def youtube_transcript(url, language="en", caller_id=None):
    return sc_get("/v1/youtube/video/transcript", url=url, language=language,
                  caller_id=caller_id)


def youtube_video(url, caller_id=None):
    return sc_get("/v1/youtube/video", url=url, caller_id=caller_id)


def tiktok_video(url, caller_id=None):
    return sc_get("/v2/tiktok/video", url=url, caller_id=caller_id)


def tiktok_transcript(url, lang="en", caller_id=None):
    return sc_get("/v1/tiktok/video/transcript", url=url, lang=lang,
                  caller_id=caller_id)


def tiktok_profile(handle, caller_id=None):
    return sc_get("/v1/tiktok/profile", handle=handle, caller_id=caller_id)


def instagram_post(url, caller_id=None):
    return sc_get("/v1/instagram/post", url=url, caller_id=caller_id)


def instagram_profile(handle, caller_id=None):
    return sc_get("/v1/instagram/profile", handle=handle, caller_id=caller_id)


def twitter_tweet(url, caller_id=None):
    return sc_get("/v1/twitter/tweet", url=url, caller_id=caller_id)


def reddit_post(url, caller_id=None):
    return sc_get("/v1/reddit/post/comments", url=url, caller_id=caller_id)


def reddit_search(query, caller_id=None, **params):
    return sc_get("/v1/reddit/search", query=query, caller_id=caller_id, **params)


def google_search(query, caller_id=None, **params):
    return sc_get("/v1/google/search", query=query, caller_id=caller_id, **params)


def linkedin_profile(url, caller_id=None):
    return sc_get("/v1/linkedin/profile", url=url, caller_id=caller_id)


__all__ = [
    "sc_get", "scrape_page", "scrape_markdown",
    "youtube_transcript", "youtube_video",
    "tiktok_video", "tiktok_transcript", "tiktok_profile",
    "instagram_post", "instagram_profile",
    "twitter_tweet", "reddit_post", "reddit_search",
    "google_search", "linkedin_profile",
]
