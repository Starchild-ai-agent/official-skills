# Apify Actor Pricing & Cost Estimation Reference

> Detailed pricing data for Apify actors. The main SKILL.md covers the
> mechanism; this file has the numbers.

## Billing formula

```
credits = (actor_start_usd + result_count × per_result_usd + addon_cost_usd) × 2
```

| Component | Value | Notes |
|-----------|-------|-------|
| `actor_start_usd` | $0.00005 | One-time per run, negligible |
| `per_result_usd` | **varies by actor** (see table below) | The dominant cost factor |
| `addon_cost_usd` | $0–0.02/result | Only if actor supports add-ons (video download, cover download, etc.) |
| `× 2` | markup | Platform markup on real Apify cost |

**Quick estimate** (ignoring actor-start and add-ons):

```
credits ≈ result_count × per_result_usd × 2
```

Examples (using default $0.007/actor):
- 10 results × $0.007 × 2 = **0.14 credits**
- 100 results × $0.007 × 2 = **1.40 credits**
- 1000 results × $0.007 × 2 = **14.00 credits** ← dangerous
- 1000 results × $0.00499 × 2 = **9.98 credits** (zen-studio actors)

## Per-actor result pricing

Actors not listed here default to **$0.007/result** — the highest tier.
Always assume $0.007 for unknown actors when estimating.

### $0.003/result (cheapest)

| Actor ID | Platform |
|----------|----------|
| `apple_yang/douyin-video-audio-downloader` | 抖音 video/audio download |
| `apple_yang/douyin-transcripts-scraper` | 抖音 transcripts |

### $0.0037/result

| Actor ID | Platform |
|----------|----------|
| `clockworks/tiktok-scraper` | TikTok (paid tier) |

### $0.00499/result

| Actor ID | Platform |
|----------|----------|
| `zen-studio/douyin-search-scraper` | 抖音 search |
| `zen-studio/douyin-profile-scraper` | 抖音 profile |
| `zen-studio/rednote-search-scraper` | 小红书 search |
| `zen-studio/taobao-detail-scraper` | 淘宝 detail |
| `zen-studio/taobao-search-scraper` | 淘宝 search |
| `zen-studio/jd-com-search-scraper` | 京东 search |
| `zen-studio/1688-wholesale-scraper` | 1688 wholesale |
| `zen-studio/goofish-xianyu-search-scraper` | 闲鱼 search |

### $0.005/result

| Actor ID | Platform |
|----------|----------|
| `clockworks/free-tiktok-scraper` | TikTok (free tier) |
| `clockworks/tiktok-hashtag-scraper` | TikTok hashtag |
| `socialdatax/socialdatax-xhs-data-api` | 小红书 |
| `sian.agency/jd-com-product-scraper` | 京东 products |
| `sian.agency/taobao-tmall-product-scraper` | 淘宝/天猫 |
| `sian.agency/xiaohongshu-rednote-scraper` | 小红书 note detail |
| `sian.agency/douyin-scraper` | 抖音 |
| `sian.agency/zhihu-scraper` | 知乎 |
| `sian.agency/weibo-scraper` | 微博 |
| `sian.agency/youku-video-scraper` | 优酷 |
| `zhorex/rednote-xiaohongshu-scraper` | 小红书 |
| `zhorex/weibo-scraper` | 微博 |
| `zhorex/bilibili-scraper` | B站 |
| `zhorex/douban-scraper` | 豆瓣 |
| `zhorex/xueqiu-scraper` | 雪球 |
| `devcake/1688-com-products-scraper` | 1688 |
| `gio21/shopee-scraper` | Shopee |
| `fatihtahta/lazada-scraper` | Lazada |
| `amit123/temu-products-scraper` | Temu |
| `knagymate/trip-com-reviews-scraper` | Trip.com reviews |

### $0.007/result (most expensive — also the default for unregistered actors)

| Actor ID | Platform |
|----------|----------|
| `natanielsantos/douyin-scraper` | 抖音 |
| *(any actor not listed above)* | defaults to this price |

## `maxTotalChargeUsd` — Apify native spending cap

Apify supports a **run option** that caps the total charge for a single actor
run. When the accumulated cost reaches the limit, Apify **automatically
terminates the run** and returns whatever results were collected so far.

### How it works

1. Pass `maxTotalChargeUsd` as a **query parameter** on the run endpoint:
   `POST /v2/acts/{actorId}/run-sync-get-dataset-items?maxTotalChargeUsd=2.5`
2. Apify injects the value as `ACTOR_MAX_TOTAL_CHARGE_USD` env var inside the
   actor container.
3. The actor SDK checks this env var and stops charging/collecting when the
   budget is exhausted.
4. Only applies to **PAY_PER_EVENT** actors (all actors in our pricing table
   are this type).

### Usage in `apify_run()`

```python
from exports import apify_run

# Default: max_charge_usd=2.5 (≈ 5 credits with 2× markup)
results = apify_run("zen-studio~douyin-search-scraper",
                    {"keywords": ["MacBook"], "maxResultsPerQuery": 50})

# Tighter cap for expensive/unknown actors
results = apify_run("unknown~expensive-scraper",
                    {"query": "..."},
                    max_charge_usd=1.0)  # ≈ 2 credits max
```

### Converting credits ↔ USD

```
max_charge_usd = max_credits / 2     (because of 2× markup)
max_credits    = max_charge_usd × 2
```

| max_charge_usd | Max credits (with 2× markup) |
|----------------|----------------------------|
| $0.5 | 1.0 |
| $1.0 | 2.0 |
| $2.5 | 5.0 (default) |
| $5.0 | 10.0 |

## Cost-aware calling workflow

1. **Look up the actor's per-result price** in the table above. If not listed,
   assume $0.007 (worst case).
2. **Estimate result count** from the actor's input params (e.g.
   `maxResults`, `maxResultsPerQuery`, `maxProducts`). If the caller didn't
   specify a limit, assume a large number (100+).
3. **Calculate estimated credits**: `result_count × per_result × 2`.
4. **If estimated > 5 credits**, inform the user before proceeding.
5. **Always pass `max_charge_usd`** to `apify_run()` — it sets the Apify-side
   hard cap so a runaway actor can't drain credits.
6. **First run of an unfamiliar actor**: set `max_charge_usd=0.5` (≈ 1 credit)
   and `maxResults`-type param to 5–10. Verify the output format and quality
   before scaling up.

## Proxy-side pricing source

The authoritative pricing map lives in the proxy plugin:
`transparent-proxy/apis/apify.py` → `_ACTOR_PER_RESULT_USD` dict.

When you register a new actor's price there, also add it to this file.
