---
name: web-crawler
version: 1.0.1
description: "Use when normal web_fetch cannot read a page, when a site blocks basic fetching, or when the user needs YouTube content in AI-ready form. Guides fallback use of Firecrawl for single-page web scraping and SerpApi for YouTube search/video metadata/transcripts only."
metadata:
  starchild:
    emoji: "🕷️"
    skillKey: web-crawler
    requires:
      bins: [python]
user-invocable: true
disable-model-invocation: false
---

# Web crawler

Use this only after the normal `web_fetch` path fails, returns unusable boilerplate, or the user specifically asks for YouTube video content/transcript. Prefer native tools first; paid fallback calls should be deliberate and scoped.

## What each service is for

**SerpApi** is only for YouTube-related retrieval:
- `engine=youtube` to search YouTube and discover candidate videos.
- `engine=youtube_video` to fetch video metadata, description, chapters, related videos, and the transcript discovery link.
- `engine=youtube_video_transcript` to fetch timestamped transcript segments for AI analysis.

Do not use SerpApi for Google/Bing/general SERP scraping, shopping, maps, news, or any non-YouTube engine. The transparent proxy blocks those engines.

**Firecrawl** is only a fallback crawler for one web page when ordinary fetching fails. Use `POST /v2/scrape` with a single `url` and focused formats like `markdown`, `html`, `rawHtml`, `links`, `summary`, or constrained `json`/`question`/`highlights` extraction.

Do not use Firecrawl crawl/map/search/agent/browser endpoints for this fallback skill. Do not request screenshots, audio, branding, images, or browser actions unless the proxy policy is expanded later.

## Access pattern through transparent proxy

Use Python scripts with `core.http_client.proxied_get` / `proxied_post`; include a typed `SC-CALLER-ID` header for cost tracking.

SerpApi examples:

```python
from core.http_client import proxied_get

headers = {"SC-CALLER-ID": "chat:youtube-transcript"}

search = proxied_get(
    "https://serpapi.com/search.json",
    params={"engine": "youtube", "search_query": "topic keywords"},
    headers=headers,
).json()

video = proxied_get(
    "https://serpapi.com/search.json",
    params={"engine": "youtube_video", "v": "VIDEO_ID"},
    headers=headers,
).json()

transcript = proxied_get(
    "https://serpapi.com/search.json",
    params={"engine": "youtube_video_transcript", "v": "VIDEO_ID", "language_code": "en"},
    headers=headers,
).json()
```

Firecrawl example:

```python
from core.http_client import proxied_post

headers = {"SC-CALLER-ID": "chat:web-crawl-fallback"}

page = proxied_post(
    "https://api.firecrawl.dev/v2/scrape",
    json={
        "url": "https://example.com/article",
        "formats": ["markdown", "links"],
        "onlyMainContent": True,
        "timeout": 60000,
    },
    headers=headers,
).json()
```

## Decision rules

For a YouTube URL, extract the 11-character video id and call `youtube_video_transcript` first if the user's goal is content analysis, summarization, quote extraction, or topic mining. This is usually more useful than fetching the public watch page because it returns timestamped transcript segments directly.

If the transcript call returns empty, unavailable, or the wrong language, call `youtube_video` next to inspect title, description, channel, publication date, and any advertised transcript metadata. Try one obvious `language_code` change only when the desired language is clear (for example `en` after a non-English request gives no transcript). If no transcript exists, summarize from metadata only and say the transcript was not available.

For a YouTube topic query, call `engine=youtube`, choose relevant `video_results`, then call metadata/transcript only for the videos needed. Avoid fetching many transcripts by default.

For a blocked or JS-heavy web page, call Firecrawl once with `formats:["markdown","links"]` and `onlyMainContent:true`. Treat the returned Markdown as the extraction substrate, not as final truth: parse the title, price/value fields, specs, body description, image URLs, outbound links, and obvious contact/location hints from the page structure.

General web-page extraction lessons:
- Many listing/detail pages render important content with JavaScript, image galleries, hidden sections, or repeated UI labels. `web_fetch` may return boilerplate while Firecrawl can still recover the real main content.
- Do not hard-code site-specific labels. Convert page text into a generic structured summary: what it is, where it is, key numbers, evidence snippets, media/links, and caveats.
- Preserve source URLs for images and links when they help verify the page, but do not download or batch-process every media asset unless the user asks.
- If Markdown misses important layout or structured fields, retry once with `rawHtml`; use `json`, `question`, or `highlights` only when the user asked for narrow extraction and the schema/prompt is specific.

## Cost discipline

SerpApi is billed per successful search-like call, regardless of result count. Firecrawl is billed per page plus expensive modifiers. Keep calls tight: one page, one video, or a small shortlist. Never batch-crawl whole websites with this skill.

If the proxy returns 403, the request is outside the allowed use case. Change the approach instead of retrying.

If the proxy returns 429, back off; do not parallelize around the limit.

If the upstream returns a failure, report the exact failure and avoid repeated paid retries unless one parameter change is clearly justified.
