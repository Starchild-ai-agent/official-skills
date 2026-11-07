---
name: instagram
version: 1.0.0
description: |
  Instagram connect, search, read, post, comment reply, and DM.

  Use for any Instagram task: publish a photo/reel/carousel/story, inspect
  profile/media/comments/insights, search hashtags or people, reply to a
  comment, or read/send direct messages. Hybrid auth: Composio managed OAuth,
  official Graph API, or an opt-in instagrapi private session.
author: starchild
tags: [instagram, social, social-media, posts, reels, stories, comments, dm, search]
delivery: script
metadata:
  starchild:
    emoji: "📸"
    skillKey: instagram
    requires:
      bins: [python3]
      env: []
    install: []
user-invocable: true
disable-model-invocation: false
---

# 📸 Instagram

One skill, three auth backends, one function surface. It supports the whole
requested loop — **connect, search, read, post, reply, DM** — without forcing a
second authorization for capabilities an already-bound credential can serve.

```
account.auth_kind == "graph"    → official Graph API (own Meta app)
account.auth_kind == "composio" → official Graph API via Composio managed OAuth
account.auth_kind == "private"  → instagrapi private API (opt-in, internal)
```

## When to Use

- "Post this image/reel to Instagram"
- "What did @brand post recently? Show comments and insights."
- "Search #fitness / find people in Amsterdam / find posts about X"
- "Reply to this comment" or "DM this person"
- "Read my Instagram inbox"
- "Connect my Instagram account"

## Mandatory first step

Always call `instagram_auth_status()` before acting. It lists bound accounts,
their `auth_kind`, and supported capabilities. **Never start a second
authorization just because a capability is missing** — the error from the
requested operation already contains `details.onboarding` with the smallest
path that unlocks it.

```python
import sys
sys.path.insert(0, "/data/workspace/skills/instagram")
from exports import instagram_auth_status

print(instagram_auth_status())
```

Every function returns:

```json
{"ok": true, "account": "brand", "auth_kind": "graph", "data": {...}}
{"ok": false, "error": {"code": "capability_not_available", "message": "...", "hint": "...", "details": {"onboarding": {...}}}}
```

## Credential resolution: bound credentials first

When a function is called, the router resolves in this order:

1. Explicit `account="label"`.
2. `INSTAGRAM_ACCOUNT` env label.
3. Any bound account that supports the requested capability, sorted by
   `INSTAGRAM_PREFERRED_AUTH` (default `graph,composio,private`).
4. If none supports it, return `capability_not_available` with onboarding.
   It does **not** silently authenticate another backend.

One account has exactly one `auth_kind`. The router never fans one operation out
across Graph + Composio + private for the same account.

## Capability matrix

| Capability | Composio | Graph (FB Login) | Private |
|---|---|---|---|
| connect | ✅ OAuth | ✅ OAuth | ✅ session |
| profile / media / comments / insights | ✅ own account | ✅ own + business discovery | ✅ any public account |
| publish image/video/reel/carousel/story | ✅ image/video/reel; carousel/story via helper | ✅ all | ✅ all |
| comment reply / mention reply | ✅ | ✅ | ✅ |
| comment moderate (delete/hide) | ✅ delete | ✅ delete/hide | ✅ delete |
| DM read / reply in existing thread | ✅ | ✅ (Page token) | ✅ |
| DM initiate (cold) | ❌ | ❌ | ✅ (`INSTAGRAM_ALLOW_COLD_DM=true`) |
| hashtag search | ❌ | ✅ (30 unique tags / 7 days) | ✅ |
| business discovery | ❌ | ✅ exact username, professional only | ✅ any public |
| people / location / post search | ❌ | ❌ | ✅ |
| follower / following lists | ❌ | ❌ | ✅ |
| comment private reply | ❌ | ✅ (Page token, 7 days) | ❌ |

## Connect / onboarding

### Official via Composio (fastest, no Meta app)

```python
instagram_connect(target="composio")
```

Returns `action_request` and `connect_url`:

```json
{
  "status": "action_required",
  "auth_kind": "composio",
  "connect_url": "https://...",
  "action_request": {"action_type": "composio_connect", "toolkit": "instagram"}
}
```

On Web, render the connect card with
`frontend_action(action_type="composio_connect", toolkit="instagram")`; do not
paste a raw OAuth URL. Off Web, show `connect_url` as plain text. Then call
`instagram_auth_status()` to confirm. The account must be Instagram
Business/Creator; the OAuth token is bound to the account selected in the picker.

### Official via your own Meta app

```python
instagram_connect(target="graph")
```

If `INSTAGRAM_GRAPH_TOKEN` is already set, it validates and returns
`already_connected`. Otherwise it returns an OAuth URL + required scopes. Use
**Facebook Login for Business**, not Instagram Login, if you need hashtag search
or business discovery.

Required scopes:
`instagram_basic`, `instagram_manage_comments`, `instagram_manage_insights`,
`instagram_content_publish`, `instagram_manage_messages`, `pages_show_list`,
`pages_read_engagement`. Request feature **Instagram Public Content Access** for
hashtag search. Bind a Page token for messaging/private replies.

### Private session (only when the capability requires it)

```python
instagram_connect(target="private", capability="search_users", confirm=True)
```

Requires `INSTAGRAM_ENABLE_PRIVATE=true` and one of:
`INSTAGRAM_SESSIONID`, `INSTAGRAM_SESSION_FILE`, or
`INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD` (plus optional
`INSTAGRAM_TOTP_SEED`). This writes a session file and logs in once.

> **Risk:** instagrapi drives Instagram's private API. It violates Instagram's
> ToS and can get the account challenged or banned. Use only for a single
> internal/own account, never as a multi-tenant product backend. Stop on
> `challenge_required` or `action_blocked`; do not retry.

### Capability-driven onboarding

```python
instagram_connect(capability="search_hashtag")
# → already_connected if a Graph account supports it
# → otherwise onboarding options: Graph (recommended) or private
```

The error/onboarding payload includes `options`, `recommended`, `steps`,
`requires`, `risk`, and `notes`. Show the user only the recommended path plus
the tradeoff; do not dump all three.

## Function reference

### Auth

| Function | Purpose |
|---|---|
| `instagram_auth_status(account=None)` | Bound accounts, capabilities, gateway health, write/private flags |
| `instagram_capabilities(account=None)` | Capability matrix + onboarding for gaps |
| `instagram_connect(target="auto", capability=None, account=None, confirm=False)` | Prefer bound; otherwise start the smallest auth flow |
| `instagram_disconnect(account, confirm=False)` | Remove a Composio connection or private session |

### Read

| Function | Notes |
|---|---|
| `instagram_profile(username=None, account=None)` | Own profile, or other public professional account |
| `instagram_list_media(username=None, limit=25, after=None, account=None)` | Own or other account |
| `instagram_get_media(media, account=None)` | Media id, shortcode, or URL |
| `instagram_list_comments(media, limit=50, after=None, account=None)` | Top-level comments |
| `instagram_list_comment_replies(comment_id, media=None, ...)` | `media` required by private backend |
| `instagram_insights(metric=None, period=None, ..., media=None)` | Media or account insights |
| `instagram_list_followers / instagram_list_following` | Private only |

### Search

| Function | Official path | Private path |
|---|---|---|
| `instagram_search_hashtag(query)` | Graph: hashtag id + 30/7d ledger | instagrapi |
| `instagram_hashtag_media(hashtag_id, mode="top")` | Graph top/recent media | instagrapi |
| `instagram_business_discovery(username)` | Graph exact username, professional only | — |
| `instagram_search_users(query)` | ❌ | ✅ |
| `instagram_search_locations(query)` | ❌ | ✅ |
| `instagram_search_posts(query)` | ❌ | ✅ |

### Write / reply

All writes default to `dry_run=True`; dry-run previews work even when writes are
disabled. Execution requires `INSTAGRAM_ALLOW_WRITES=true` **and**
`confirm=True` after showing the exact payload.

| Function | Notes |
|---|---|
| `instagram_publish(media_type="image", image_url=..., caption=...)` | image/video/reel/story/carousel |
| `instagram_publish_status(container_id)` | Graph container status |
| `instagram_publishing_limit()` | Graph 100 posts / 24h quota |
| `instagram_reply_comment(comment_id, text, media=None)` | Public reply |
| `instagram_comment_on_media(media, text)` | New top-level comment |
| `instagram_private_reply(comment_id, text)` | Graph Page token; one message within 7 days |
| `instagram_reply_mention(media, text)` | Reply to a mention |
| `instagram_hide_comment(comment_id, hide=True)` | Graph only |
| `instagram_delete_comment(comment_id, media=None)` | Graph/Composio/private |
| `instagram_hashtag_usage(account=None)` | Local 30/7d ledger |

### DM

| Function | Notes |
|---|---|
| `instagram_list_conversations(limit=20)` | Inbox |
| `instagram_get_conversation(conversation_id)` | Participants |
| `instagram_list_messages(conversation_id, limit=20)` | Thread |
| `instagram_send_dm(text=..., recipient_id=..., conversation_id=...)` | Official reply-only inside window; private can cold-DM |
| `instagram_mark_seen(recipient_id)` | Best-effort; Graph only |

## Typical workflows

### Publish with a preview

```python
plan = instagram_publish(
    media_type="image",
    image_url="https://cdn.example.com/post.jpg",
    caption="New drop",
)
# show plan["data"]["payload"] to the user
result = instagram_publish(
    media_type="image",
    image_url="https://cdn.example.com/post.jpg",
    caption="New drop",
    dry_run=False,
    confirm=True,
)
```

### Reply to a comment + DM the commenter

```python
instagram_reply_comment(comment_id="178...", text="Thanks!", dry_run=False, confirm=True)
instagram_private_reply(comment_id="178...", text="Just sent you a DM.", dry_run=False, confirm=True)
```

`instagram_private_reply` needs a Graph Page token and the Human Agent feature;
it can send exactly one message within 7 days. The user must reply to open the
24-hour continue-window.

### Search → read → engage

```python
tag = instagram_search_hashtag("fitness")          # Graph
media = instagram_hashtag_media(tag["data"]["id"], mode="top")
# Graph cannot comment on hashtag-discovered media.
```

For people/location search, the router returns private onboarding if no private
session is bound:

```python
instagram_search_users("amsterdam fitness")
# → {"ok": false, "error": {"code": "capability_not_available", "details": {"onboarding": ...}}}
```

## Key facts / gotchas

- **Official API is professional-only.** Personal accounts cannot use Graph or
  Composio.
- **Publishing:** 100 API posts / 24h; carousel counts as one; JPEG images only;
  Graph fetches media from a public HTTPS URL. Composio takes URL args through
  this skill; use the private backend for local files.
- **Hashtag search:** 30 unique hashtags per rolling 7 days; top/recent media
  fetches also count; cannot comment on hashtag-discovered media; Facebook Login
  + Instagram Public Content Access required.
- **Business discovery:** exact username, public professional accounts only, no
  follower/following lists.
- **DM window:** 24h for most actions, up to 7 days for Click-to-Direct, 7 days
  with `human_agent`. Error `10/2534022` means closed — do not retry.
- **Official DM IDs:** recipient must be an IGSID from a webhook/conversation;
  usernames are not resolvable to IGSID.
- **Composio slug quirk:** use `INSTAGRAM_CREATE_MEDIA_CONTAINER` +
  `INSTAGRAM_CREATE_POST`; the newer documented slugs may return "Tool not found".
  The adapter falls back automatically.
- **Composio has no search tools** and no private reply; that is why the router
  offers Graph/private onboarding for those capabilities.
- **Private backend:** session files are secrets; keep them `0600` and out of
  git. Stop on challenge/action-blocked. Delay jitter is applied automatically.
- **Media input:** Graph/Composio mostly need public URLs; private accepts local
  paths and downloads URLs to a temp file.

## Environment variables

```bash
# Routing
INSTAGRAM_ACCOUNT=brand
INSTAGRAM_PREFERRED_AUTH=graph,composio,private
INSTAGRAM_STATE_DIR=~/.starchild/instagram

# Composio (gateway auto-authenticates; no key needed)
INSTAGRAM_COMPOSIO_ENABLED=true

# Official Graph
INSTAGRAM_GRAPH_TOKEN=...
INSTAGRAM_GRAPH_USER_ID=...
INSTAGRAM_GRAPH_PAGE_ID=...
INSTAGRAM_GRAPH_PAGE_TOKEN=...
INSTAGRAM_META_APP_ID=...
INSTAGRAM_META_APP_SECRET=...
INSTAGRAM_GRAPH_API_VERSION=v26.0
INSTAGRAM_LOGIN_TYPE=facebook   # or instagram (no hashtag/business discovery)
INSTAGRAM_GRAPH_HASHTAG_SEARCH=true
INSTAGRAM_GRAPH_BUSINESS_DISCOVERY=true

# Private (opt-in)
INSTAGRAM_ENABLE_PRIVATE=false
INSTAGRAM_USERNAME=...
INSTAGRAM_PASSWORD=...
INSTAGRAM_SESSIONID=...
INSTAGRAM_SESSION_FILE=...
INSTAGRAM_TOTP_SEED=...
INSTAGRAM_PROXY=...
INSTAGRAM_ALLOW_COLD_DM=false
INSTAGRAM_DELAY_MIN=3
INSTAGRAM_DELAY_MAX=8

# Safety
INSTAGRAM_ALLOW_WRITES=false
INSTAGRAM_AUTO_CONFIRM=false
INSTAGRAM_CONTAINER_TIMEOUT=180
```

Multi-account config:

```bash
INSTAGRAM_ACCOUNTS_JSON='[
  {"label":"brand-a","auth_kind":"graph","access_token":"...","ig_user_id":"...","page_id":"...","page_token":"..."},
  {"label":"personal","auth_kind":"private","session_file":"/data/secrets/ig-session.json","cold_dm":false}
]'
```

## Verification

```bash
python3 -c "import importlib.util, os; s=importlib.util.spec_from_file_location('m','instagram/exports.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.instagram_auth_status())"
```

Offline smoke test: `python3 instagram/smoke_test.py` (no network, no live
Instagram calls).
