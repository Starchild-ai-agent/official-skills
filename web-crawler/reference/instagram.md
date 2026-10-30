# Instagram — capability map

Routes, returned fields, costs and limits for public Instagram data.
Upstream availability changes: for anything marked ⚠️ or ❌, try once and
report the actual result to the user instead of quoting this table.
No user key is needed for any route here: sc-proxy injects ScrapeCreators and
Apify credentials.

## 1. What you can get, and from where

| Data | Route | Helper | Cost | Status |
|---|---|---|---|---|
| Profile: bio, follower/following/post counts, verified, private, category, **business email / phone / address**, bio links, related profiles, highlight count | SC `/v1/instagram/profile?handle=` | `instagram_profile` | 1 SC credit | ✅ |
| Public/private flag + `has_story_archive` by user id | SC `/v1/instagram/basic-profile?userId=` | — | 1 credit | ✅ |
| All feed posts (likes, comments, caption, location, coauthors, media URLs, `taken_at`) | SC `/v2/instagram/user/posts` — 12/page, paginate `next_max_id` | `instagram_all_posts` | 1 credit/page | ✅ |
| Reels with **play counts** | SC `/v1/instagram/user/reels?user_id=` — paginate `max_id` | — | 1 credit/page | ✅ |
| One post / reel in full | SC `/v1/instagram/post?url=` | `instagram_post` | 1 credit | ✅ |
| Comments + **commenter usernames** | SC `/v2/instagram/post/comments?url=` — paginate `cursor` | — | 1 credit/page | ✅ |
| What was said in a reel | SC `/v2/instagram/media/transcript?url=` — reels >120s return **400** unless you add `allow_long_transcription=true` | — | 1 credit (≤120s); 10 credits per started minute with the flag | ✅ |
| Reels by keyword | SC `/v2/instagram/reels/search?query=` — paginate `page` | — | 1 credit | ✅ |
| Embed HTML | SC `/v1/instagram/user/embed?handle=` | — | 1 credit | ✅ |
| Highlights list → frames | SC `/v1/instagram/user/highlights` — pass `user_id` (profile `id`), not `handle` → `/user/highlight/detail?id=` | — | 1 credit when it works | ❌ unreliable: Instagram often rejects it upstream (500 "Instagram user highlights returned status 401"); Apify highlight actors fail the same way. Try once; if it fails, tell the user highlights are unavailable right now |
| **Followers / following list** with `isPrivate`, `isVerified`, name, pic | Apify `apify~instagram-followers-following-scraper` (`dataToScrape: followers|following`) or `scraping_solutions~instagram-scraper-followers-following-no-cookies` (cheaper) | `instagram_followers` | ~$0.0008–0.002/user | ✅ no login |
| **Post likers** with `isPrivate`, `isVerified` | Apify `memo23~instagram-likers-scraper` (`postUrls`, `maxLikersPerPost`) | `instagram_likers` | per liker | ✅ |
| **Active stories (<24h)**: id, `taken_at`, `expiring_at`, image/video URLs, stickers, crosspost | Apify `data-slayer~instagram-stories-scraper` (`usernames`) | `instagram_stories` | ~$0.0025/frame | ✅ public accounts only |
| Posts by **hashtag** (owner, likes, comments, caption, mentions, paid partnership) | Apify `apify~instagram-hashtag-scraper` (`hashtags`, `resultsLimit`) | `instagram_hashtag` | per post | ✅ |
| Profile extras: `relatedProfiles`, `businessAddress`, latest posts | Apify `apify~instagram-profile-scraper` | — | per profile | ✅ |
| Posts the account is **tagged** in (owner, shortCode, timestamp, type, likes, caption) | Apify `apify~instagram-tagged-scraper` (`username: [handle]`, `resultsLimit`) | `instagram_tagged` | per post | ✅ Avoid `instagram-scraper~instagram-tagged-posts-scraper` (returns no items) |

## 2. What nobody outside the account can get — say so, don't retry

- Story **views, taps, exits**; post **reach / impressions / saves / shares**.
- **Follower demographics** (age, gender, city) and the owner's Insights.
- **Expired stories** (unless pinned to a highlight), DMs, close-friends stories.
- Anything from a **private** account beyond the profile header.
- Reposts tab — no scraper exposes it (SC 404).
- SC `/user/followers`, `/user/following`, `/user/stories`, `/user/tagged`,
  `/v1/detect/age-gender` all return **404** — use the Apify routes above, never
  conclude "impossible" from an SC 404 alone.

## 3. Common recipes

**Competitor snapshot:** `instagram_profile` → `instagram_all_posts` (all pages)
→ reels play counts → engagement rate = (likes+comments)/followers per post.

**Audience quality (public vs private, verified share):** `instagram_followers`
on a sample first (`limit=100`, cents), extrapolate; full pull only after the user
confirms the cost estimate (followers × per-user price). Report aggregates, do
not store per-person lists (third-party personal data).

**Story monitoring:** stories expire in 24h and no one keeps history — run
`instagram_stories` on a schedule (e.g. every 12h) and persist rows by `id` to
build a story archive (cadence, format mix, CTAs). Views are never available.

**Engager list:** comments (SC, cheap) → likers (Apify) → optional per-user
`basic-profile` for private/public.

## 4. Gotchas

- Handles without `@`. `user/reels` wants `user_id` (from profile `id`).
- Play counts are IG-only (exclude cross-posted Facebook views).
- Story/media CDN URLs expire within hours — download immediately.
- Apify default cap is $2.5/run; for big follower pulls raise `max_charge_usd`
  only after telling the user the estimate.
