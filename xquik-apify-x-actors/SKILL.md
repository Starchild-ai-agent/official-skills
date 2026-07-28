---
name: xquik-apify-x-actors
version: 1.0.0
description: |
  Collect public X posts and audience relations with Xquik's Apify Actors.

  Use for bounded X research through Apify.
author: Xquik
tags: [apify, x, twitter, scraping, social-media, audience-research]
delivery: script
user-invocable: true
disable-model-invocation: false
metadata:
  starchild:
    emoji: "🔎"
    skillKey: xquik-apify-x-actors
    requires:
      bins: [python3]
      env: [APIFY_TOKEN]
---

# Xquik X Actors on Apify

Use two public Apify Actors for public X data.
Keep this workflow on Apify.
Do not route it through an external Xquik website or API.

Xquik is an independent third-party service. Not affiliated with X Corp. "Twitter" and "X" are trademarks of X Corp.

## When to Use

- Search public posts by keyword, hashtag, account, or query operator.
- Read public timelines, lists, threads, replies, or quotes.
- Export followers, following, verified followers, or list members.
- Export list followers or public community members.
- Compare overlap across public audiences.

Never bypass private profiles or access controls.
Collect only the public data needed for the task.

## Actor Directory

| Goal | Actor | REST selector | Actor ID |
| --- | --- | --- | --- |
| Posts and timelines | [X Tweet Scraper](https://apify.com/xquik/x-tweet-scraper) | `xquik~x-tweet-scraper` | `wAusCMrm284Voaw86` |
| Audiences and relations | [X Follower Scraper](https://apify.com/xquik/x-follower-scraper) | `xquik~x-follower-scraper` | `AaT0BcKU5GQh97wdt` |

Use `xquik/x-tweet-scraper` with the Apify CLI.
Use `xquik/x-follower-scraper` with the Apify CLI.

Run both Actors when the task needs both datasets.
Keep their runs and datasets separate.

## Prerequisites

- Install the current Apify CLI.
- Authenticate through `APIFY_TOKEN` or `apify login`.
- Confirm the requested result cap.
- Confirm the live Apify price before running.

Never print or store `APIFY_TOKEN`.
Never place the token inside Actor input.

## How to Call

Load the native exports through Starchild:

```python
from core.skill_tools import _modules

xquik = _modules["xquik-apify-x-actors"]
info = xquik.get_actor_info("tweet")
```

`get_actor_info(actor)` reads current Apify Actor metadata.
Pass `tweet` or `follower`.
It never starts an Actor run.

`run_tweet_scraper(input_data, confirmed, timeout, max_total_charge_usd)` runs the Tweet Actor.
`run_follower_scraper(input_data, confirmed, timeout, max_total_charge_usd)` runs the Follower Actor.

Both run functions require `confirmed=True`.
They also require a positive `maxItems` value.
Set `max_total_charge_usd` when the user requests a spending cap.

## Inspect Current Schemas

Inspect schemas before using unfamiliar fields:

```bash
apify actors info "xquik/x-tweet-scraper" --input --json
apify actors info "xquik/x-follower-scraper" --input --json
```

Treat each Actor listing and schema as authoritative.
Do not hardcode prices.
Set Apify's maximum total charge outside Actor input when needed.

## X Tweet Scraper

Supported modes include:

`legacy`, `tweet`, `tweets`, `search`, `profileTweets`, `profileReplies`,
`profileMedia`, `profileLikes`, `listTweets`, `article`, `replies`, `quotes`,
`thread`, `retweeters`, and `favoriters`.

The Actor supports `legacy`, `rich`, and `raw` output variants.
It also supports several field styles and output presets.

`maxItems` caps the complete run.
It does not create one quota per search term.

Use `maxItemsPerTarget` only with explicit multi-target modes.
Nonpositive per-target values are ignored.

### Search Public Posts

Start with a small run:

```bash
apify actors call "xquik/x-tweet-scraper" \
  --input '{"mode":"search","searchTerms":["from:apify AI"],"queryType":"Latest","outputVariant":"rich","includeSearchTerms":true,"maxItems":25}' \
  --json \
  --output-dataset
```

Use `includeSearchTerms: true` for multi-query attribution.
Use direct modes for threads, replies, quotes, or engagement routes.

## X Follower Scraper

Supported relations include:

`followers`, `following`, `verified_followers`, `list_members`,
`list_followers`, and `community_members`.

Supported output modes include `compact`, `full`, and `raw`.
Supported dedupe modes include `none`, `first`, and `merge`.

`maxItems` caps the complete run.
`maxItemsPerTarget` balances explicit multi-target runs.

Keep `includeTargetMetadata: true` for source attribution.
Use `overlapMode: true` for public audience comparisons.

### Export a Public Audience

```bash
apify actors call "xquik/x-follower-scraper" \
  --input '{"twitterHandles":["apify"],"relation":"followers","outputMode":"compact","includeTargetMetadata":true,"maxItems":25,"maxItemsPerTarget":25}' \
  --json \
  --output-dataset
```

For overlap, pass at least two public targets.
Use `dedupeMode: "merge"` or `overlapMode: true`.

## Run Safety

Before every paid run, present:

1. The Actor slug.
2. The public targets or search terms.
3. The global result cap.
4. Any per-target cap.
5. The live pricing source.

Get explicit user approval before starting the run.
Do not retry a partial paid run automatically.
Pass `confirmed=True` only after receiving that approval.

## Validate Results

Separate data rows from diagnostic rows.
Diagnostic rows can include `status` and `message`.

Exclude diagnostic rows from scraped totals.
Read diagnostics before changing input.

Both Actors write a `run-report` record.
Use it to review routes, totals, outcomes, and anomalies.

Preserve these fields when available:

- Canonical post or profile IDs
- Canonical public URLs
- Search terms
- Source targets
- Source relations
- Overlap counts

Do not infer endorsement, identity, or intent from a follow.

## Report Results

Report:

- Actor slug and route
- Inputs and result limits
- Retrieval time
- Data and diagnostic row counts
- Missing or unavailable targets
- Dataset or saved artifact location
- Analysis limits

Separate observed public data from interpretation.
