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
    # transcript resolver (generic, read-only, never downloads media)
    "get_transcript", "podcast_transcript", "resolve_podcast_episode",
    "media_info", "captions_from_media_info",
]


# ---------------------------------------------------------------------------
# Transcript resolver — generic, read-only, never downloads media.
#
# Principle (claude-video, spoken.md and every serious agent tool follow it):
# captions / subtitles / published transcripts are METADATA — fetch them
# first from every provider that has them; the media file is PAYLOAD and is
# touched only when the user explicitly agrees. Every provider (a) returns
# the same shape, (b) validates HTTP status + body, (c) proves identity
# (same channel, same episode) before claiming found.
#
# Providers, in cost order:
#   1. media_info(url) — yt-dlp extract_info(download=False): 1800+ sites,
#      title/duration/upload_date/channel_id + caption-track URLs, zero
#      media bytes. Covers YouTube/Vimeo/TED/… natively.
#   2. RSS <podcast:transcript> (Podcasting 2.0) for podcast episodes.
#   3. Cross-platform: the show's OWN YouTube channel (declared in its RSS,
#      else resolved by name) → the upload whose duration matches ±5 % and
#      date ±3 d; title similarity is a tie-break only.
#   4. Any other page → scrape_markdown (browser-rendered; survives WAF 403).
#   5. found=False → caller reports what was tried and ASKS THE USER.
# ---------------------------------------------------------------------------
import difflib as _difflib
import html as _html
import json as _json
import re as _re
from datetime import datetime as _dt, timezone as _tz


def _pget(url, timeout=30, **kw):
    from core.http_client import proxied_get
    kw.setdefault("headers", {})
    kw["headers"].setdefault("User-Agent", "Mozilla/5.0")
    return proxied_get(url, timeout=timeout, **kw)


def _ok_body(resp, min_chars=200):
    """HTTP 2xx AND a real body, not an error page (review P1-3)."""
    if resp is None or not (200 <= resp.status_code < 300):
        return False
    body = (resp.text or "").strip()
    if len(body) < min_chars:
        return False
    head = body[:400].lower()
    return not _re.search(r"\b(403 forbidden|404 not found|access denied|"
                          r"error code|captcha|request blocked)\b", head)


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


def _parse_dt(v):
    if not v:
        return None
    try:
        if isinstance(v, (int, float)):
            return _dt.fromtimestamp(v, _tz.utc)
        v = str(v)
        if _re.fullmatch(r"\d{8}", v):
            return _dt.strptime(v, "%Y%m%d").replace(tzinfo=_tz.utc)
        try:
            d = _dt.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            from email.utils import parsedate_to_datetime
            d = parsedate_to_datetime(v)
        return d if d.tzinfo else d.replace(tzinfo=_tz.utc)
    except Exception:
        return None


def _dur_secs(v):
    """'00:52:43' | '3163' | 3163 → seconds."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    try:
        parts = [int(float(x)) for x in str(v).strip().split(":")]
    except ValueError:
        return None
    secs = 0
    for x in parts:
        secs = secs * 60 + x
    return secs


def _same_episode(a_dur, b_dur, a_dt, b_dt, a_title="", b_title="",
                  dur_tol=0.05, day_tol=3):
    """Identity test for 'same episode on another platform'.
    Duration is the strong key (audio and video cuts of one recording differ
    by seconds), date the second; title is a tie-break only — shows retitle
    uploads (review P1-2: date alone matched a cooking show)."""
    if not a_dur or not b_dur:
        return False, 0.0
    rel = abs(a_dur - b_dur) / max(a_dur, b_dur)
    if rel > dur_tol:
        return False, 0.0
    score = 1.0 - rel
    if a_dt and b_dt:
        days = abs((a_dt - b_dt).total_seconds()) / 86400
        if days > day_tol:
            return False, 0.0
        score += 0.5 * (1 - days / day_tol)
    elif _sim(a_title, b_title) < 0.6:
        return False, 0.0  # no date → need title agreement
    score += 0.3 * _sim(a_title, b_title)
    return True, round(score, 3)


# ---- provider 1: yt-dlp metadata (no download) -----------------------------
def media_info(url, flat=False, playlistend=40):
    """yt-dlp extract_info(download=False): metadata + caption-track URLs for
    1800+ sites; never fetches media. {} on failure."""
    try:
        import yt_dlp
    except ImportError:
        return {}
    opts = {"skip_download": True, "quiet": True, "no_warnings": True,
            "socket_timeout": 20, "noplaylist": not flat}
    if flat:
        opts.update({"extract_flat": "in_playlist", "playlistend": playlistend})
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            return y.extract_info(url, download=False) or {}
    except Exception:
        return {}


def _caption_text_from_track(track):
    r = _pget(track["url"], timeout=40)
    if not (200 <= r.status_code < 300) or len(r.content) < 200:
        return ""
    ext = track.get("ext", "")
    if ext == "json3":
        try:
            d = r.json()
            return " ".join(seg.get("utf8", "") for ev in d.get("events", [])
                            for seg in ev.get("segs", []) if seg.get("utf8", "").strip())
        except Exception:
            return ""
    if ext in ("vtt", "srt", "srv1", "srv2", "srv3", "ttml"):
        body = _re.sub(r"<[^>]+>", " ", r.text)
        lines = [l for l in body.splitlines()
                 if l.strip() and not _re.match(r"^\d+$", l.strip())
                 and "-->" not in l
                 and not l.startswith(("WEBVTT", "NOTE", "Kind:", "Language:"))]
        return _html.unescape(" ".join(lines))
    return ""


def captions_from_media_info(info, languages=("en",)):
    """Pick a caption track (manual before auto, json3 before text formats)
    and return {text, lang, kind, ext} or None."""
    pri = {"json3": 0, "vtt": 1, "srt": 2, "srv3": 3, "ttml": 4}
    for pool_name in ("subtitles", "automatic_captions"):
        pool = info.get(pool_name) or {}
        langs = list(languages) + [l for l in pool
                                   if l.split("-")[0] in languages and l not in languages]
        for lang in langs:
            for t in sorted(pool.get(lang) or [], key=lambda t: pri.get(t.get("ext"), 9)):
                try:
                    text = _re.sub(r"\s+", " ", _caption_text_from_track(t)).strip()
                except Exception:
                    continue
                if len(text) > 200:
                    return {"text": text, "lang": lang, "kind": pool_name, "ext": t.get("ext")}
    return None


# ---- podcast episode resolution --------------------------------------------
def resolve_podcast_episode(url, caller_id=None):
    """Apple / Spotify / any podcast page → {show, episode, feed_url,
    release_date, duration}. yt-dlp's own extractor first (generic), Apple
    lookup adds the feed URL, Spotify og tags as last resort."""
    out = {"show": None, "episode": None, "feed_url": None, "release_date": None,
           "duration": None, "provider": None}
    info = media_info(url)
    if info:
        out["provider"] = info.get("extractor")
        out["episode"] = info.get("title")
        out["show"] = info.get("series") or info.get("uploader") or info.get("channel")
        out["duration"] = _dur_secs(info.get("duration"))
        out["release_date"] = info.get("upload_date") or info.get("release_date")
    m = _re.search(r"podcasts\.apple\.com/.*?/id(\d+)(?:.*?[?&]i=(\d+))?", url)
    if m:
        coll, ep = m.group(1), m.group(2)
        try:
            r = _pget("https://itunes.apple.com/lookup",
                      params={"id": coll, "entity": "podcastEpisode", "limit": 300},
                      timeout=20).json()
        except Exception:
            r = {}
        for x in r.get("results", []):
            if x.get("kind") == "podcast":
                out["show"] = x.get("collectionName") or out["show"]
                out["feed_url"] = x.get("feedUrl")
            elif ep and str(x.get("trackId")) == ep:
                out["episode"] = x.get("trackName") or out["episode"]
                out["release_date"] = x.get("releaseDate") or out["release_date"]
                out["duration"] = out["duration"] or ((x.get("trackTimeMillis") or 0) // 1000 or None)
                out["feed_url"] = out["feed_url"] or x.get("feedUrl")
    elif "open.spotify.com/episode/" in url and not out["episode"]:
        try:
            t = _pget(url, timeout=20).text
        except Exception:
            t = ""
        og = _re.search(r'property="og:title"\s+content="([^"]+)"', t)
        desc = _re.search(r'property="og:description"\s+content="([^"]+)"', t)
        if og:
            out["episode"] = _html.unescape(og.group(1))
        if desc and "·" in desc.group(1):
            out["show"] = _html.unescape(desc.group(1).split("·")[0]).strip()
    return out


def _rss_item_for(feed_url, episode_title, release_date=None, duration=None):
    """(item_xml | None, channel_xml) for the feed item matching the episode."""
    r = _pget(feed_url, timeout=40)
    if not _ok_body(r, 500):
        return None, ""
    x = r.text
    head = x.split("<item>")[0]
    rel = _parse_dt(release_date)
    best, best_s = None, 0.0
    for it in _re.findall(r"<item>(.*?)</item>", x, _re.S):
        t = _re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, _re.S)
        title = t.group(1) if t else ""
        d = _re.search(r"<itunes:duration>(.*?)</itunes:duration>", it)
        pd = _re.search(r"<pubDate>(.*?)</pubDate>", it)
        s = _sim(title, episode_title)
        ok, ident = _same_episode(duration, _dur_secs(d.group(1)) if d else None,
                                  rel, _parse_dt(pd.group(1)) if pd else None,
                                  episode_title, title)
        s = max(s, ident if ok else 0.0)
        if s > best_s:
            best, best_s = it, s
    return (best if best_s >= 0.85 else None), head


def _rss_transcript(item_xml):
    """Podcasting 2.0 <podcast:transcript> → plain text, validated."""
    cand = []
    for attrs in _re.findall(r'<podcast:transcript\s+([^>]*)/?>', item_xml or ""):
        u = _re.search(r'url="([^"]+)"', attrs)
        ty = (_re.search(r'type="([^"]+)"', attrs) or [None, ""])[1]
        if u:
            cand.append((ty, _html.unescape(u.group(1))))
    pri = ["text/plain", "application/json", "text/vtt", "application/x-subrip",
           "application/srt", "text/html"]
    cand.sort(key=lambda c: pri.index(c[0]) if c[0] in pri else 99)
    for ty, u in cand:
        try:
            r = _pget(u, timeout=40)
        except Exception:
            continue
        if not _ok_body(r, 500):          # P1-3: a 403 body is not a transcript
            continue
        body = r.text
        if "json" in ty:
            try:
                d = _json.loads(body)
                segs = d.get("segments") if isinstance(d, dict) else d
                text = " ".join(s.get("body", "") for s in segs)
            except Exception:
                continue
        else:
            body = _re.sub(r"<[^>]+>", " ", body)
            lines = [l for l in body.splitlines()
                     if l.strip() and not _re.match(r"^\d+$", l.strip())
                     and "-->" not in l and not l.startswith(("WEBVTT", "NOTE"))]
            text = " ".join(lines)
        text = _re.sub(r"\s+", " ", _html.unescape(text)).strip()
        if len(text) > 500:
            return {"text": text, "url": u, "type": ty}
    return None


def _declared_youtube_channel(item_xml, channel_xml):
    """The show's own YouTube channel as declared in its RSS (item first,
    then channel level). Identity key for the cross-platform match — not a
    fuzzy word overlap on channel names (review P1-2)."""
    pat = r"https?://(?:www\.)?youtube\.com/(?:@[\w.\-]+|channel/[\w\-]+|c/[\w.\-]+|user/[\w.\-]+)"
    for blob in (item_xml or "", channel_xml or ""):
        for u in _re.findall(pat, blob):
            return u.split("?")[0]
    return None


_STOP = {"the", "show", "podcast", "with", "a", "an", "of", "and"}


def _key(s):
    return " ".join(w for w in _norm(s).split() if w not in _STOP)


def _youtube_match(ep, channel_url=None):
    """Same episode on the show's own YouTube channel, or None.
    Channel: RSS-declared URL (listed via yt-dlp flat extraction), else a
    yt-dlp search whose channel name EQUALS the show name minus stopwords.
    Episode: _same_episode. Returns {url, title, score, channel}."""
    show_key = _key(ep.get("show") or "")
    ep_dt = _parse_dt(ep.get("release_date"))
    candidates = []
    if channel_url:
        lst = media_info(channel_url.rstrip("/") + "/videos", flat=True)
        ch = lst.get("channel") or lst.get("uploader") or lst.get("title") or ""
        candidates = [(e, ch) for e in lst.get("entries") or []]
    if not candidates and show_key:
        lst = media_info(f"ytsearch15:{ep.get('show')} {ep.get('episode')}", flat=True)
        for e in lst.get("entries") or []:
            ch = e.get("channel") or e.get("uploader") or ""
            if _key(ch) and _key(ch) == show_key:
                candidates.append((e, ch))
    best, best_s = None, 0.0
    for e, ch in candidates:
        e_dur = _dur_secs(e.get("duration"))
        e_dt = _parse_dt(e.get("upload_date") or e.get("timestamp"))
        if e_dt is None and e_dur and ep.get("duration") and ep_dt:
            # flat listings carry no date; only duration-plausible candidates
            # (usually 1-3) pay for a full metadata fetch to prove the date.
            if abs(e_dur - ep["duration"]) / max(e_dur, ep["duration"]) <= 0.05:
                full = media_info(e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}")
                e_dt = _parse_dt(full.get("upload_date") or full.get("timestamp"))
                e_dur = _dur_secs(full.get("duration")) or e_dur
        ok, score = _same_episode(ep.get("duration"), e_dur, ep_dt, e_dt,
                                  ep.get("episode") or "", e.get("title") or "")
        if ok and score > best_s:
            best, best_s = (e, ch), score
    if not best:
        return None
    e, ch = best
    u = e.get("url") or e.get("webpage_url") or f"https://www.youtube.com/watch?v={e.get('id')}"
    return {"url": u, "title": e.get("title"), "score": best_s, "channel": ch}


def _flatten_segments(tr):
    text = tr.get("transcript_only_text") or tr.get("transcript") or tr.get("text") or ""
    if isinstance(text, list):
        text = " ".join((s.get("text") or "") for s in text if isinstance(s, dict))
    return _re.sub(r"\s+", " ", str(text)).strip()


def _youtube_text(url, caller_id=None):
    """Captions for a YouTube URL: yt-dlp tracks first, ScrapeCreators as
    fallback when yt-dlp is blocked. ('', src, title) when neither has them."""
    info = media_info(url)
    cap = captions_from_media_info(info) if info else None
    if cap:
        return cap["text"], f"native_captions:{cap['kind']}", info.get("title")
    try:
        text = _flatten_segments(youtube_transcript(url, caller_id=caller_id))
    except Exception:
        text = ""
    return (text if len(text) > 200 else ""), "youtube_transcript", (info or {}).get("title")


def podcast_transcript(url, caller_id=None):
    """Transcript for a podcast episode WITHOUT touching the audio."""
    ep = resolve_podcast_episode(url, caller_id=caller_id)
    res = {"found": False, "source": None, "text": "", "url": None, "tried": [],
           "youtube_channel_url": None, "note": None, **ep}
    if not ep.get("episode"):
        res["note"] = "could not resolve episode from link"
        return res
    item, head = None, ""
    if ep.get("feed_url"):
        res["tried"].append("rss_podcast_transcript")
        try:
            item, head = _rss_item_for(ep["feed_url"], ep["episode"],
                                       ep.get("release_date"), ep.get("duration"))
            if item:
                d = _re.search(r"<itunes:duration>(.*?)</itunes:duration>", item)
                res["duration"] = res["duration"] or (_dur_secs(d.group(1)) if d else None)
                rss = _rss_transcript(item)
                if rss:
                    res.update(found=True, source="rss_podcast_transcript",
                               text=rss["text"], url=rss["url"])
                    return res
        except Exception as e:
            res["rss_error"] = str(e)[:120]
    ch = _declared_youtube_channel(item, head)
    res["youtube_channel_url"] = ch
    res["tried"].append("youtube_channel_match" if ch else "youtube_search_match")
    yt = _youtube_match(res, channel_url=ch)
    if yt:
        text, src, _ = _youtube_text(yt["url"], caller_id=caller_id)
        if text:
            res.update(found=True, source=f"youtube:{src}", text=text, url=yt["url"],
                       youtube_title=yt["title"], match_score=yt["score"],
                       youtube_channel=yt["channel"])
            return res
        res["note"] = f"matched upload {yt['url']} has no captions"
    res["note"] = res["note"] or (
        "no transcript file published: RSS has no podcast:transcript and no "
        "same-episode upload on the show's YouTube channel. "
        "Ask the user before downloading audio.")
    return res


def get_transcript(url, caller_id=None, language="en"):
    """ONE entry for any media link. Same shape every time:
    {found, kind, source, text, url, title, tried, note}.
    found=False ⇒ nothing read-only exists; ASK THE USER before any download."""
    u = (url or "").strip()
    res = {"found": False, "kind": None, "source": None, "text": "", "url": u,
           "title": None, "tried": [], "note": None}
    host = _re.sub(r"^https?://(www\.|m\.)?", "", u).split("/")[0].lower()

    if "tiktok.com" in host:
        res["kind"] = "tiktok"
        res["tried"].append("tiktok_transcript")
        try:
            text = _flatten_segments(tiktok_transcript(u, lang=language, caller_id=caller_id))
        except Exception:
            text = ""
        res.update(found=len(text) > 50, source="tiktok_transcript", text=text,
                   note=None if len(text) > 50 else "no transcript for this video")
        return res

    if "podcasts.apple.com" in host or ("spotify.com" in host and "/episode/" in u):
        res["kind"] = "podcast"
        r = podcast_transcript(u, caller_id=caller_id)
        res.update(found=r["found"], source=r["source"], text=r["text"],
                   url=r.get("url") or u, tried=r["tried"], note=r.get("note"),
                   title=" — ".join(x for x in (r.get("show"), r.get("episode")) if x) or None)
        return res

    # 1. generic: yt-dlp metadata → native caption tracks (YouTube, Vimeo, TED, …)
    info = media_info(u)
    if info and (info.get("subtitles") or info.get("automatic_captions")):
        res["tried"].append("native_captions")
        cap = captions_from_media_info(info, (language,))
        if cap:
            res.update(found=True, kind=info.get("extractor"),
                       source=f"native_captions:{cap['kind']}", text=cap["text"],
                       title=info.get("title"))
            return res
    if info and info.get("extractor") == "youtube":
        res["tried"].append("youtube_transcript")
        try:
            text = _flatten_segments(youtube_transcript(u, language=language, caller_id=caller_id))
        except Exception:
            text = ""
        if len(text) > 200:
            res.update(found=True, kind="youtube", source="youtube_transcript",
                       text=text, title=info.get("title"))
            return res
    if info and info.get("extractor") not in (None, "generic"):
        # a known media page with no captions anywhere → stop here, do not scrape
        res.update(kind=info.get("extractor"), title=info.get("title"),
                   note="media has no caption track; ask the user before downloading")
        return res

    # 2. any other page (publisher transcript page, Snipd, blog …)
    res["kind"] = "page"
    res["tried"].append("scrape_markdown")
    try:
        md = (scrape_markdown(u, caller_id=caller_id) or "").strip()
    except Exception as e:
        res["note"] = f"scrape failed: {str(e)[:120]}"
        return res
    res.update(found=len(md) > 1000, source="scrape_markdown", text=md,
               note=None if len(md) > 1000 else "page has no substantial text")
    return res
