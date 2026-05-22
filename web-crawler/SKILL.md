---
name: web-crawler
version: 2.2.1
description: |
  Web scraping plus social data: YouTube, TikTok, Instagram, LinkedIn, Reddit, Threads.

  Use when extracting public posts, transcripts, or pages JS-heavy enough to block plain fetch (e.g. download YouTube transcript, scrape TikTok comments).
metadata:
  starchild:
    emoji: "🕷️"
    skillKey: web-crawler
    requires:
      bins: [python]
    tags:
      - scraping
      - social-media
      - web-crawler
      - tiktok
      - instagram
      - youtube
      - linkedin
      - facebook
      - twitter
      - reddit
      - threads
      - bluesky
      - pinterest
      - snapchat
      - twitch
      - truth-social
      - tiktok-shop
      - google
      - ad-library
      - creator-data
      - transcripts
      - trending
user-invocable: true
disable-model-invocation: false

---

# Web crawler

All-in-one scraping skill. Routes requests to the best backend automatically — the user does not need to know which API is used.

Use this when:
- Normal `web_fetch` fails, returns boilerplate, or a site blocks basic fetching
- The user asks for YouTube video content/transcript
- The user wants to scrape, fetch, or extract data from any social media platform
- The user mentions social media profiles, posts, comments, transcripts, ads, trending content, or engagement metrics

Prefer native `web_fetch` first for simple pages; paid fallback calls should be deliberate and scoped.

## What each service is for

### ScrapeCreators — Social media data extraction (27+ platforms)

Use for any request involving social media profiles, posts, videos, comments, transcripts, search, ads, trending content, or engagement metrics. Covers TikTok, Instagram, YouTube, LinkedIn, Facebook, Twitter/X, Reddit, Threads, Bluesky, Pinterest, Snapchat, Twitch, Kick, Truth Social, TikTok Shop, Google search, and link-in-bio services (Linktree, Komi, Pillar, Linkbio, Linkme, Amazon Shop).

**Base URL:** `https://api.scrapecreators.com`
**Auth:** No user-supplied key needed. sc-proxy injects platform credentials automatically — just send the request. The `x-api-key` header can be any value or omitted entirely. Do NOT bail out or ask the user for a key if `$SCRAPECREATORS_API_KEY` looks unset; that env var is intentionally not required.
**Method:** All endpoints use GET requests with query params. Responses are JSON.

### Firecrawl — Fallback web page scraper

Only a fallback crawler for one web page when ordinary fetching fails. Use `POST /v2/scrape` with a single `url` and focused formats like `markdown`, `html`, `rawHtml`, `links`, `summary`, or constrained `json`/`question`/`highlights` extraction.

Do not use Firecrawl crawl/map/search/agent/browser endpoints. Do not request screenshots, audio, branding, images, or browser actions unless the proxy policy is expanded later.

---

## ScrapeCreators — Intent routing

Map user intent to the right endpoint. Endpoint paths use the pattern `/v1/platform/action`.

**Important:** After selecting an endpoint from the tables below, fetch its OpenAPI spec at `https://docs.scrapecreators.com/{path}/openapi.json` for full parameter details, types, and example response before making the actual API call. For example: `https://docs.scrapecreators.com/v1/tiktok/profile/openapi.json`

### Profiles / User Info
| Platform | Endpoint | Primary Param | Example |
|----------|----------|---------------|---------|
| TikTok | `/v1/tiktok/profile` | handle | `stoolpresidente` |
| Instagram | `/v1/instagram/profile` | handle | `jane` |
| YouTube | `/v1/youtube/channel` | handle, channelId, or url | `ThePatMcAfeeShow` |
| LinkedIn (person) | `/v1/linkedin/profile` | url | `https://www.linkedin.com/in/parrsam/` |
| LinkedIn (company) | `/v1/linkedin/company` | url | `https://linkedin.com/company/shopify` |
| Facebook | `/v1/facebook/profile` | url | `https://www.facebook.com/mantraindianfolsom` |
| Twitter/X | `/v1/twitter/profile` | handle | `elonmusk` |
| Reddit | `/v1/reddit/subreddit/details` | subreddit or url | `AskReddit` |
| Threads | `/v1/threads/profile` | handle | `zuck` |
| Bluesky | `/v1/bluesky/profile` | handle | `jay.bsky.team` |
| Pinterest | `/v1/pinterest/user/boards` | handle | `pinterest` |
| Truth Social | `/v1/truthsocial/profile` | handle | `realDonaldTrump` |
| Twitch | `/v1/twitch/profile` | handle | `ninja` |
| Snapchat | `/v1/snapchat/profile` | handle | `djkhaled` |

### Posts / Content Feeds
| Platform | Endpoint | Primary Param | Example |
|----------|----------|---------------|---------|
| TikTok videos | `/v3/tiktok/profile/videos` | handle | `stoolpresidente` |
| Instagram posts | `/v2/instagram/user/posts` | handle | `jane` |
| Instagram reels | `/v1/instagram/user/reels` | handle or user_id | `jane` or `2700692569` |
| Instagram highlights | `/v1/instagram/user/highlights` | handle or user_id | `jane` or `2700692569` |
| YouTube videos | `/v1/youtube/channel/videos` | handle or channelId | `ThePatMcAfeeShow` |
| YouTube shorts | `/v1/youtube/channel/shorts` | handle or channelId | `starterstory` |
| YouTube playlist | `/v1/youtube/playlist` | playlist_id | `PLP32wGpgzmIlInfgKVFfCwVsxgGqZNIiS` |
| LinkedIn posts | `/v1/linkedin/company/posts` | url | `https://linkedin.com/company/shopify` |
| Facebook posts | `/v1/facebook/profile/posts` | url or pageId | `https://www.facebook.com/pacemorby` |
| Facebook reels | `/v1/facebook/profile/reels` | url | `https://www.facebook.com/Spurs` |
| Facebook photos | `/v1/facebook/profile/photos` | url | `https://www.facebook.com/Spurs` |
| Facebook group posts | `/v1/facebook/group/posts` | url or group_id | `742354120555345` |
| Twitter tweets | `/v1/twitter/user/tweets` | handle | `elonmusk` |
| Reddit posts | `/v1/reddit/subreddit` | subreddit | `AskReddit` |
| Threads posts | `/v1/threads/user/posts` | handle | `zuck` |
| Bluesky posts | `/v1/bluesky/user/posts` | handle or user_id | `jay.bsky.team` |
| Truth Social posts | `/v1/truthsocial/user/posts` | handle or user_id | `realDonaldTrump` |
| Pinterest board | `/v1/pinterest/board` | url | `https://www.pinterest.com/...` |

### Single Post / Video Details
| Platform | Endpoint | Primary Param | Example |
|----------|----------|---------------|---------|
| TikTok | `/v2/tiktok/video` | url | `https://www.tiktok.com/@randomspamvideos25/video/7251387037834595630` |
| Instagram | `/v1/instagram/post` | url | `https://www.instagram.com/reel/DOq6eV6iIgD` |
| Instagram highlight | `/v1/instagram/user/highlight/detail` | id | `18067016518767507` |
| YouTube | `/v1/youtube/video` | url | `https://www.youtube.com/watch?v=Y2Ah_DFr8cw` |
| YouTube community post | `/v1/youtube/community-post` | url | `https://www.youtube.com/post/Ugkxvj2KoApYAXoqLWnKVr6zZe5JjeHrQeP8` |
| LinkedIn | `/v1/linkedin/post` | url | `https://www.linkedin.com/pulse/being-father-has-made-me-better-leader...` |
| Facebook | `/v1/facebook/post` | url | `https://www.facebook.com/reel/1535656380759655` |
| Twitter/X | `/v1/twitter/tweet` | url | `https://twitter.com/elonmusk/status/...` |
| Twitter/X community | `/v1/twitter/community` | url | `https://twitter.com/i/communities/...` |
| Twitter/X community tweets | `/v1/twitter/community/tweets` | url | `https://twitter.com/i/communities/...` |
| Reddit | `/v1/reddit/post/comments` | url | `https://www.reddit.com/r/AskReddit/comments/...` |
| Threads | `/v1/threads/post` | url | `https://www.threads.net/@zuck/post/...` |
| Bluesky | `/v1/bluesky/post` | url | `https://bsky.app/profile/.../post/...` |
| Truth Social | `/v1/truthsocial/post` | url | `https://truthsocial.com/@realDonaldTrump/posts/...` |
| Pinterest | `/v1/pinterest/pin` | url | `https://www.pinterest.com/pin/...` |
| Twitch clip | `/v1/twitch/clip` | url | `https://clips.twitch.tv/...` |
| Kick clip | `/v1/kick/clip` | url | `https://kick.com/...` |

### Comments
| Platform | Endpoint | Primary Param | Example |
|----------|----------|---------------|---------|
| TikTok | `/v1/tiktok/video/comments` | url | `https://www.tiktok.com/@stoolpresidente/video/7499229683859426602` |
| Instagram | `/v2/instagram/post/comments` | url | `https://www.instagram.com/reel/DOq6eV6iIgD` |
| YouTube | `/v1/youtube/video/comments` | url | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| Facebook | `/v1/facebook/post/comments` | url or feedback_id | `https://www.facebook.com/reel/753347914167361` |
| Reddit | `/v1/reddit/post/comments` | url | `https://www.reddit.com/r/AskReddit/comments/...` |

### Transcripts
| Platform | Endpoint | Example | Note |
|----------|----------|---------|------|
| TikTok | `/v1/tiktok/video/transcript` | `url=https://www.tiktok.com/...&lang=en` | also via `/v2/tiktok/video` with get_transcript=true |
| Instagram | `/v2/instagram/media/transcript` | `url=https://www.instagram.com/reel/...` | AI-powered, 10-30s, under 2min |
| YouTube | `/v1/youtube/video/transcript` | `url=https://www.youtube.com/watch?v=bjVIDXPP7Uk` | also included in `/v1/youtube/video` response |
| Facebook | `/v1/facebook/post/transcript` | `url=https://www.facebook.com/reel/...` | under 2min only |
| Twitter/X | `/v1/twitter/tweet/transcript` | `url=https://twitter.com/...` | AI-powered, slow |

### Search
| Platform | Endpoint | Primary Param | Example |
|----------|----------|---------------|---------|
| TikTok users | `/v1/tiktok/search/users` | query | `funny` |
| TikTok videos (keyword) | `/v1/tiktok/search/keyword` | query | `funny` |
| TikTok videos (hashtag) | `/v1/tiktok/search/hashtag` | hashtag | `fyp` |
| TikTok top (photos+videos) | `/v1/tiktok/search/top` | query | `funny` |
| Instagram reels | `/v2/instagram/reels/search` | query | `dogs` |
| YouTube | `/v1/youtube/search` | query | `funny` |
| YouTube hashtag | `/v1/youtube/search/hashtag` | hashtag | `funny` |
| Reddit (all) | `/v1/reddit/search` | query | `best programming languages` |
| Reddit (in subreddit) | `/v1/reddit/subreddit/search` | subreddit + query | `AskReddit` + `funny` |
| Threads posts | `/v1/threads/search` | query | `AI` |
| Threads users | `/v1/threads/search/users` | query | `zuck` |
| Pinterest | `/v1/pinterest/search` | query | `home decor` |
| Google | `/v1/google/search` | query | `best restaurants in NYC` |

### Ad Libraries
| Platform | Endpoint | Primary Param | Example |
|----------|----------|---------------|---------|
| Facebook ads search | `/v1/facebook/adLibrary/search/ads` | query | `running` |
| Facebook company ads | `/v1/facebook/adLibrary/company/ads` | pageId or companyName | `Lululemon` |
| Facebook ad detail | `/v1/facebook/adLibrary/ad` | id or url | `702369045530963` |
| Facebook find companies | `/v1/facebook/adLibrary/search/companies` | query | `Nike` |
| Google company ads | `/v1/google/company/ads` | domain or advertiser_id | `nike.com` |
| Google ad detail | `/v1/google/ad` | url | `https://adstransparency.google.com/...` |
| Google find advertisers | `/v1/google/adLibrary/advertisers/search` | query | `Nike` |
| LinkedIn ads search | `/v1/linkedin/ads/search` | company or keyword | `Shopify` |
| LinkedIn ad detail | `/v1/linkedin/ad` | url | `https://www.linkedin.com/ad/...` |
| Reddit ads search | `/v1/reddit/ads/search` | query | `gaming` |
| Reddit ad detail | `/v1/reddit/ad` | id | `t3_abc123` |

### Trending / Popular
| Content | Endpoint | Param | Example |
|---------|----------|-------|---------|
| Trending feed | `/v1/tiktok/get-trending-feed` | region (required) | `US` |
| Popular videos | `/v1/tiktok/videos/popular` | | |
| Popular creators | `/v1/tiktok/creators/popular` | | |
| Popular hashtags | `/v1/tiktok/hashtags/popular` | | |
| Popular songs | `/v1/tiktok/songs/popular` | | |
| Song details | `/v1/tiktok/song` | clipId | `7439295283975702544` |
| Videos using song | `/v1/tiktok/song/videos` | clipId | `7439295283975702544` |
| Trending shorts (YT) | `/v1/youtube/shorts/trending` | | |

### Followers / Following / Live (TikTok only)
| Type | Endpoint | Example |
|------|----------|---------|
| Following | `/v1/tiktok/user/following` | `handle=stoolpresidente` |
| Followers | `/v1/tiktok/user/followers` | `handle=stoolpresidente` |
| Audience demographics | `/v1/tiktok/user/audience` (26 credits!) | `handle=shakira` |
| Live stream | `/v1/tiktok/user/live` | `handle=thejustalex` |

### TikTok Shop
| Type | Endpoint | Primary Param | Example |
|------|----------|---------------|---------|
| Search products | `/v1/tiktok/shop/search` | query | `shoes` |
| Store products | `/v1/tiktok/shop/products` | url | `https://www.tiktok.com/shop/store/goli-nutrition/7495794203056835079` |
| Product detail | `/v1/tiktok/product` | url | `https://www.tiktok.com/shop/pdp/goli-ashwagandha-gummies.../1729587769570529799` |
| Product reviews | `/v1/tiktok/shop/product/reviews` | url or product_id | `1731578642912612516` |
| User showcase | `/v1/tiktok/user/showcase` | handle | `mrtiktokreviews` |

### Link-in-Bio / Other
| Service | Endpoint | Param | Example |
|---------|----------|-------|---------|
| Linktree | `/v1/linktree` | url | `https://linktr.ee/...` |
| Komi | `/v1/komi` | url | `https://komi.io/...` |
| Pillar | `/v1/pillar` | url | `https://pillar.io/...` |
| Linkbio | `/v1/linkbio` | url | `https://linkbio.co/...` |
| Linkme | `/v1/linkme` | url | `https://linkme.bio/...` |
| Amazon Shop | `/v1/amazon/shop` | url | `https://www.amazon.com/shop/...` |
| Instagram basic profile | `/v1/instagram/basic/profile` | userId | `314216` |
| Instagram embed HTML | `/v1/instagram/user/embed` | handle | `jane` |
| Age/Gender detect | `/v1/detect/age-gender` | url (social profile) | `https://www.tiktok.com/@charlidamelio` |
| Credit balance | `/v1/credit/balance` | (none) | |

### ScrapeCreators pagination

Paginated endpoints return a cursor/token in the response. Pass it back as a query param to get the next page.

| Cursor Field | Used By |
|-------------|---------|
| `cursor` | TikTok comments/search/song videos, Instagram comments, Reddit subreddit search, Pinterest, Bluesky, Facebook reels/photos/posts/comments, TikTok Shop products/user showcase |
| `max_cursor` | TikTok profile videos |
| `min_time` | TikTok following/followers |
| `continuationToken` | YouTube (all paginated endpoints) |
| `after` | Reddit posts, Reddit search |
| `next_max_id` | Instagram posts, Truth Social posts |
| `max_id` | Instagram reels |
| `page` | TikTok popular/shop, Instagram reels search, LinkedIn company posts, TikTok Shop reviews |
| `paginationToken` | LinkedIn ads |

### ScrapeCreators known limitations

- **Handles**: pass without the `@` symbol. Use `charlidamelio` not `@charlidamelio`. Applies to TikTok, Instagram, Twitter, Threads, Bluesky, Snapchat, Twitch, Pinterest, Truth Social
- **YouTube handles**: pass without the `@` symbol. Use `ThePatMcAfeeShow` not `@ThePatMcAfeeShow`. You can also pass a channelId or full URL instead
- **Hashtags**: pass without the `#` symbol. Use `fyp` not `#fyp`. Applies to TikTok and YouTube hashtag search endpoints
- **Twitter**: returns ~100 most popular tweets, not chronological/latest
- **Threads**: only last 20-30 posts visible publicly
- **Facebook posts**: only 3 posts per page (API limitation)
- **Facebook group posts**: only 3 posts per page (same limitation)
- **LinkedIn company posts**: max 7 pages
- **Instagram play counts**: IG-only views (excludes cross-posted FB views)
- **Truth Social**: only prominent users (Trump, Vance, etc.) work publicly
- **Transcripts**: all transcript endpoints require video under 2 minutes
- **Reddit subreddit names**: case-sensitive! Use "AskReddit" not "askreddit"

---

## Access patterns

### ScrapeCreators (social media)

Use Python with `core.http_client.proxied_get` so sc-proxy injects credentials and bills correctly. Include a typed `SC-CALLER-ID` header (`chat:`, `job:`, `preview:`, etc.) for cost tracking. **Do not read `$SCRAPECREATORS_API_KEY` from env and do not ask the user for a key — the proxy handles it.**

```python
from core.http_client import proxied_get

headers = {"SC-CALLER-ID": "chat:youtube-transcript"}

transcript = proxied_get(
    "https://api.scrapecreators.com/v1/youtube/video/transcript",
    params={"url": "https://www.youtube.com/watch?v=VIDEO_ID", "language": "en"},
    headers=headers,
    timeout=20,
).json()
```

Bash/curl works too (proxy is transparent), but Python is preferred for cost tracking:

```bash
curl -s "https://api.scrapecreators.com/v1/tiktok/profile?handle=charlidamelio" \
  -H "x-api-key: any"
```

Each endpoint has its own OpenAPI spec at `https://docs.scrapecreators.com/{path}/openapi.json`. **Always fetch the per-endpoint spec first** to get full parameter details before making the actual API call. The full spec is at `https://docs.scrapecreators.com/openapi.json` (large file — prefer per-endpoint specs).

Common optional params:
- **`trim`** (boolean): reduces response payload size. Use when you only need key metrics.
- **`region`** (string): 2-letter country code for proxy location. Does NOT filter by region — just routes through that country's proxy.

### Firecrawl (web page fallback via transparent proxy)

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

Route every request to the right backend. The user should never need to specify which API to use.

### Social media request (profile, posts, comments, search, ads, trending, transcripts)
Use **ScrapeCreators**. Match the user's intent to an endpoint from the routing tables above. Strip `@` from handles and `#` from hashtags before calling. Fetch the per-endpoint OpenAPI spec first for full param details.

### YouTube URL or YouTube content request
Use **ScrapeCreators** for YouTube (channel info, videos, shorts, playlists, comments, transcripts, search, trending shorts). Match the user's intent to the appropriate YouTube endpoint from the routing tables above.

For a YouTube URL, use `/v1/youtube/video` to get video details and transcript. If the user's goal is content analysis, summarization, quote extraction, or topic mining, the transcript is included in the video response.

For a YouTube topic query, use `/v1/youtube/search` to find relevant videos, then call `/v1/youtube/video` only for the videos needed. Avoid fetching many videos by default.

### Blocked or JS-heavy web page
Use **Firecrawl** once with `formats:["markdown","links"]` and `onlyMainContent:true`. Treat the returned Markdown as the extraction substrate, not as final truth: parse the title, price/value fields, specs, body description, image URLs, outbound links, and obvious contact/location hints from the page structure.

General web-page extraction lessons:
- Many listing/detail pages render important content with JavaScript, image galleries, hidden sections, or repeated UI labels. `web_fetch` may return boilerplate while Firecrawl can still recover the real main content.
- Do not hard-code site-specific labels. Convert page text into a generic structured summary: what it is, where it is, key numbers, evidence snippets, media/links, and caveats.
- Preserve source URLs for images and links when they help verify the page, but do not download or batch-process every media asset unless the user asks.
- If Markdown misses important layout or structured fields, retry once with `rawHtml`; use `json`, `question`, or `highlights` only when the user asked for narrow extraction and the schema/prompt is specific.

## Cost discipline

**ScrapeCreators** — most endpoints cost 1 credit per request. Exceptions: `/v1/tiktok/user/audience` costs 26 credits; `/v1/tiktok/video/transcript` with `use_ai_as_fallback=true` costs +10 credits; `/v1/google/company/ads` with `get_ad_details=true` costs 25 credits. Warn users before calling expensive endpoints.

**Firecrawl** — billed per page plus expensive modifiers.

Keep calls tight: one page, one video, or a small shortlist. Never batch-crawl whole websites or bulk-scrape entire feeds with this skill.

If the proxy returns 403, the request is outside the allowed use case. Change the approach instead of retrying.

If the proxy returns 429, back off; do not parallelize around the limit.

If the upstream returns a failure, report the exact failure and avoid repeated paid retries unless one parameter change is clearly justified.
