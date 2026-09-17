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


def wayback_snapshot_url(url, caller_id=None, timeout=30):
    """Ask the Internet Archive for the newest available Wayback snapshot of
    `url`. Returns the snapshot URL string, or None if none archived.
    Note: Wayback honors robots.txt / paywalls, so hard paywalls (NYT/WSJ)
    are often NOT captured here — try archive.today first for those.
    """
    resp = proxied_get("https://archive.org/wayback/available",
                       params={"url": url}, headers=_headers(caller_id),
                       timeout=timeout)
    resp.raise_for_status()
    snaps = (resp.json().get("archived_snapshots") or {}).get("closest") or {}
    return snaps.get("url") if snaps.get("available") else None


def archive_fallback(url, caller_id=None, timeout=120):
    """Last-resort full-text recovery for a page Firecrawl couldn't get
    (hard paywall / Cloudflare returning 403 even through Firecrawl).

    Strategy, in order:
      1. archive.today — scrape the `/newest/` snapshot via Firecrawl. This
         site captures with a real browser and historically preserves full
         text behind paywalls (NYT, WSJ, Economist). Best for paywalls.
      2. Wayback Machine — if archive.today has nothing, fall back to the
         Internet Archive's newest snapshot and scrape that.

    Returns a dict: {markdown, source, snapshot_url}. markdown == "" means
    no archived copy exists anywhere — then stop and tell the user / try a
    different source. archive_fallback CANNOT create a snapshot that nobody
    ever saved; it only retrieves existing ones.
    """
    # 1. archive.today — try its mirror domains; /newest/ resolves latest capture
    for host in ("https://archive.ph/newest/", "https://archive.today/newest/",
                 "https://archive.is/newest/"):
        try:
            md = scrape_markdown(host + url, caller_id=caller_id, timeout=timeout)
            if md and len(md) > 800:  # filter out "no snapshot" / chrome-only pages
                return {"markdown": md, "source": "archive.today",
                        "snapshot_url": host + url}
        except Exception:
            continue
    # 2. Wayback Machine fallback
    try:
        snap = wayback_snapshot_url(url, caller_id=caller_id)
        if snap:
            md = scrape_markdown(snap, caller_id=caller_id, timeout=timeout)
            if md:
                return {"markdown": md, "source": "wayback",
                        "snapshot_url": snap}
    except Exception:
        pass
    return {"markdown": "", "source": None, "snapshot_url": None}


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


# ---------------------------------------------------------------------------#
# Apify — China apps & structured e-commerce data
# ---------------------------------------------------------------------------#
APIFY_BASE = "https://api.apify.com"


def apify_run(actor_id, run_input, caller_id=None, timeout=180, max_charge_usd=2.5):
    """Run an Apify actor synchronously and return the result list.

    Use this for China apps (抖音/小红书/微博/B站/京东/淘宝/1688/闲鱼/得物 etc.)
    and Southeast Asia e-commerce (Shopee/Lazada/Temu) that Firecrawl and
    ScrapeCreators don't cover.

    No API key needed — sc-proxy injects the platform Apify token automatically.
    The `Authorization` header sent here is a fake placeholder; the proxy
    replaces it with the real token.

    Args:
        actor_id: "username~actor-name", e.g. "zen-studio~douyin-search-scraper".
                  Find reliable actors in output/apify_china_reliable.json.
        run_input: dict, the actor's input JSON (varies per actor — fetch the
                   actor's input-schema page via scrape_markdown to discover
                   required fields).
        caller_id: optional SC-CALLER-ID for billing traceability.
        timeout: seconds to wait for the run to finish (default 180).
        max_charge_usd: hard spending cap passed to Apify as
                        ``maxTotalChargeUsd``. Apify terminates the run when
                        accumulated cost reaches this USD amount and returns
                        partial results. Default $2.5 (≈ 5 credits with 2×
                        markup). Set lower (e.g. 0.5) for first-time tests of
                        unfamiliar actors. Set to None to disable the cap
                        (not recommended).

    Returns:
        list of result dicts. Empty list if the actor ran but found nothing.

    Raises:
        HTTPError on non-2xx (400 = bad input, 401 = proxy misconfigured,
        504 = timeout).

    Example:
        # Normal call (default cap ≈ 5 credits)
        results = apify_run("zen-studio~douyin-search-scraper",
                            {"keywords": ["MacBook"], "maxResultsPerQuery": 5})

        # First-time test of an unfamiliar actor (tight cap)
        results = apify_run("unknown~new-scraper",
                            {"query": "test"},
                            max_charge_usd=0.5)
    """
    url = f"{APIFY_BASE}/v2/acts/{actor_id}/run-sync-get-dataset-items"
    params = {"timeout": timeout}
    if max_charge_usd is not None:
        params["maxTotalChargeUsd"] = str(max_charge_usd)
    resp = proxied_post(
        url,
        params=params,
        headers={
            "SC-CALLER-ID": caller_id or _DEFAULT_CALLER,
            "Authorization": "Bearer fake-apify-token-12345",  # proxy injects real
            "Content-Type": "application/json",
        },
        json=run_input,
        timeout=timeout + 30,  # buffer beyond the Apify-side timeout
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    # Some actors return {"items": [...]} or {"data": [...]}
    if isinstance(data, dict):
        for key in ("items", "results", "data"):
            v = data.get(key)
            if isinstance(v, list):
                return v
    return []


__all__ = [
    "sc_get", "scrape_page", "scrape_markdown",
    "archive_fallback", "wayback_snapshot_url",
    "apify_run",
    "youtube_transcript", "youtube_video",
    "tiktok_video", "tiktok_transcript", "tiktok_profile",
    "instagram_post", "instagram_profile",
    "twitter_tweet", "reddit_post", "reddit_search",
    "google_search", "linkedin_profile",
]


# ---------------------------------------------------------------------------
# Podcast transcript — deterministic, read-only, no audio.
#
# Incident 2026-09-17: given an Apple Podcasts link, the agent hit 403 on two
# transcript hosts and downloaded the 49 MB mp3 to transcribe it. The correct
# route is a fixed chain of APIs, not model improvisation:
#   Apple/Spotify link → show + episode title (+ RSS)
#   → RSS <podcast:transcript> if the feed publishes one
#   → the show's YouTube upload of the same episode → captions file.
# Returns {"found": bool, "source": ..., "text": ..., "show": ..., "episode": ...}.
# When found is False the caller must ASK THE USER before any download.
# ---------------------------------------------------------------------------
import difflib as _difflib
import html as _html
import json as _json
import re as _re


def _pget(url, timeout=30, **kw):
    from core.http_client import proxied_get
    kw.setdefault("headers", {})
    kw["headers"].setdefault("User-Agent", "Mozilla/5.0")
    return proxied_get(url, timeout=timeout, **kw)


def _norm(s):
    s = _html.unescape(s or "").lower()
    s = _re.sub(r"[\u2018\u2019\u201c\u201d'\"`|:\-–—,.!?()\[\]]", " ", s)
    return _re.sub(r"\s+", " ", s).strip()


def _sim(a, b):
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return _difflib.SequenceMatcher(None, a, b).ratio()


def resolve_podcast_episode(url, caller_id=None):
    """Apple / Spotify episode link → {show, episode, feed_url, release_date}."""
    out = {"show": None, "episode": None, "feed_url": None, "release_date": None,
           "provider": None}
    m = _re.search(r"podcasts\.apple\.com/.*?/id(\d+)(?:.*?[?&]i=(\d+))?", url)
    if m:
        out["provider"] = "apple"
        coll, ep = m.group(1), m.group(2)
        r = _pget("https://itunes.apple.com/lookup",
                  params={"id": coll, "entity": "podcastEpisode", "limit": 300},
                  timeout=20).json()
        for x in r.get("results", []):
            if x.get("kind") == "podcast":
                out["show"] = x.get("collectionName")
                out["feed_url"] = x.get("feedUrl")
            elif ep and str(x.get("trackId")) == ep:
                out["episode"] = x.get("trackName")
                out["release_date"] = x.get("releaseDate")
                out["show"] = out["show"] or x.get("collectionName")
                out["feed_url"] = out["feed_url"] or x.get("feedUrl")
        return out
    if "open.spotify.com/episode/" in url:
        out["provider"] = "spotify"
        t = _pget(url, timeout=20).text
        og = _re.search(r'property="og:title"\s+content="([^"]+)"', t)
        desc = _re.search(r'property="og:description"\s+content="([^"]+)"', t)
        if og:
            out["episode"] = _html.unescape(og.group(1))
        # Spotify og:description is "<Show> · Episode" on episode pages
        if desc and "·" in desc.group(1):
            out["show"] = _html.unescape(desc.group(1).split("·")[0]).strip()
        return out
    return out


def _rss_transcript(feed_url, episode_title, caller_id=None):
    """Podcasting 2.0 <podcast:transcript> for the matching item, as text."""
    if not feed_url:
        return None
    x = _pget(feed_url, timeout=40).text
    best, best_s = None, 0.0
    for it in _re.findall(r"<item>(.*?)</item>", x, _re.S):
        t = _re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, _re.S)
        s = _sim(t.group(1), episode_title) if t else 0.0
        if s > best_s:
            best, best_s = it, s
    if not best or best_s < 0.85:
        return None
    tags = _re.findall(r'<podcast:transcript\s+([^>]*)/?>', best)
    if not tags:
        return None
    # prefer plain text/json/vtt/srt in that order
    cand = []
    for attrs in tags:
        u = _re.search(r'url="([^"]+)"', attrs)
        ty = (_re.search(r'type="([^"]+)"', attrs) or [None, ""])[1]
        if u:
            cand.append((ty, _html.unescape(u.group(1))))
    pri = ["text/plain", "application/json", "text/vtt", "application/x-subrip", "application/srt", "text/html"]
    cand.sort(key=lambda c: pri.index(c[0]) if c[0] in pri else 99)
    for ty, u in cand:
        try:
            body = _pget(u, timeout=40).text
        except Exception:
            continue
        if "json" in ty:
            try:
                d = _json.loads(body)
                segs = d.get("segments") or d
                return {"text": " ".join(s.get("body", "") for s in segs), "url": u, "type": ty}
            except Exception:
                continue
        # vtt/srt → strip cue headers / timestamps / indices
        lines = [l for l in body.splitlines()
                 if l.strip() and not _re.match(r"^\d+$", l.strip())
                 and "-->" not in l and not l.startswith(("WEBVTT", "NOTE"))]
        return {"text": _re.sub(r"<[^>]+>", "", " ".join(lines)), "url": u, "type": ty}
    return None


def _youtube_captions(show, episode_title, release_date=None, caller_id=None,
                      min_sim=0.6):
    """Find the show's YouTube upload of this episode and pull its captions.

    Two keys, either suffices: title similarity >= min_sim, OR same channel
    published within ±2 days of the podcast release (shows routinely retitle
    the YouTube upload — a16z feed 'The AI-Native CRM' vs YouTube 'Inside
    Lightfield's Vision for the AI-Native Business', both 2026-09-16)."""
    from datetime import datetime, timezone
    rel = None
    if release_date:
        try:
            rel = datetime.fromisoformat(release_date.replace("Z", "+00:00"))
        except Exception:
            rel = None
    q = f"{show} {episode_title}".strip()
    r = sc_get("/v1/youtube/search", query=q, caller_id=caller_id)
    vids = r.get("videos") or r.get("results") or r.get("data") or []
    show_n = _norm(show)
    best, best_s = None, 0.0
    for v in vids[:20]:
        title = v.get("title") or ""
        ch = ((v.get("channel") or {}).get("title") or v.get("channelTitle")
              or v.get("author") or "")
        # channel must look like the show's own upload (a16z Show → channel a16z)
        if not any(tok in _norm(ch) for tok in show_n.split() if len(tok) > 2):
            continue
        s = _sim(title, episode_title)
        if rel and v.get("publishedTime"):
            try:
                pub = datetime.fromisoformat(v["publishedTime"].replace("Z", "+00:00"))
                days = abs((pub - rel).total_seconds()) / 86400
                if days <= 2:
                    s = max(s, 0.9 - 0.1 * days + 0.1 * s)  # date match dominates
            except Exception:
                pass
        if s > best_s:
            best, best_s = v, s
    if not best or best_s < min_sim:
        return None
    u = best.get("url") or f"https://www.youtube.com/watch?v={best.get('id')}"
    tr = youtube_transcript(u, caller_id=caller_id)
    text = tr.get("transcript_only_text") or tr.get("transcript") or ""
    if isinstance(text, list):
        text = " ".join(seg.get("text", "") for seg in text)
    text = _re.sub(r"\s+", " ", str(text)).strip()
    if len(text) < 500:
        return None
    return {"text": text, "url": u, "title": best.get("title"), "similarity": round(best_s, 2)}


def podcast_transcript(url, caller_id=None):
    """Transcript for a podcast episode link WITHOUT touching the audio.

    Chain: resolve link → RSS <podcast:transcript> → YouTube captions of the
    show's own upload. On found=False do NOT download media — report show +
    episode and ask the user.
    """
    ep = resolve_podcast_episode(url, caller_id=caller_id)
    res = {"found": False, "source": None, "text": "", "url": None, **ep}
    if not ep.get("episode"):
        res["note"] = "could not resolve episode title from link"
        return res
    try:
        rss = _rss_transcript(ep.get("feed_url"), ep["episode"], caller_id=caller_id)
    except Exception as e:  # feed unreachable → fall through
        rss = None
        res["rss_error"] = str(e)[:120]
    if rss:
        res.update(found=True, source="rss_podcast_transcript", text=rss["text"], url=rss["url"])
        return res
    yt = _youtube_captions(ep.get("show") or "", ep["episode"],
                           release_date=ep.get("release_date"), caller_id=caller_id)
    if yt:
        res.update(found=True, source="youtube_captions", text=yt["text"], url=yt["url"],
                   youtube_title=yt["title"], similarity=yt["similarity"])
        return res
    res["note"] = ("no transcript file published (RSS has no podcast:transcript, "
                   "no matching YouTube upload). Ask the user before downloading audio.")
    return res
