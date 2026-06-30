---
name: x-mcp-onboarding
description: Connect a user's own X (Twitter) dev app (BYOK) for the official X API MCP (reads) plus X v2 REST writes — post, reply, like, retweet, DM.

  Use when the user wants to act on X with their OWN X account/app: search, read timeline/users/news/trends/bookmarks via MCP, and post/reply/like/retweet/DM via REST. Walks through OAuth 2.0 setup in the X portal, xurl CLI registration, headless OAuth (user pastes the redirect URL back), the client-not-enrolled / Pay-per-use trap, the token-expiry auto-refresh mechanism, agent.yaml MCP wiring, and FAQ. For read-only scraping WITHOUT the user's own app, use the `twitter` skill instead.
version: 1.0.1
---

# X API Onboarding — MCP (reads) + REST (writes), BYOK

Connects the user's **own** X developer app so this agent can:
- **Read** via the official hosted **X MCP** (`https://api.x.com/mcp`) — 24 tools
- **Write** via the **X v2 REST API** (`https://api.x.com/2/...`) — post / delete / like / retweet / reply / DM

**Why BYOK (not a shared Starchild app):** X write access is per-app rate-limited
(~app-wide caps), pay-per-use billed to the app owner, and TOS liability sits with
the app owner. A shared app = single point of failure + neighbors starving each
other + concentrated billing + content-moderation liability. So every user brings
their own app + OAuth token. The token lives only on this machine (`~/.xurl`),
never proxied.

## ⚠️ Reads vs writes — two separate systems (do not confuse)

| Capability | Channel | Validated |
|---|---|---|
| search posts/users/news, timeline, mentions, trends, bookmarks | **MCP** (24 tools) | ✅ connected |
| **post / delete / reply / like / retweet / follow / DM** | **REST `/2/...`** (NOT in MCP) | ✅ post+delete tested |

The MCP `tools/list` returns ONLY the 24 read/bookmark tools. Write endpoints are a
**separate REST API** documented at docs.x.com — they are NOT discoverable through
MCP. They are listed in this skill below.

---

## STEP 1 — User creates OAuth 2.0 credentials in the X portal (manual; X has NO API for this)

X exposes no API to create/configure an app. These steps are unavoidably manual in
the web portal. Make them copy-paste exact.

1. Go to **developer.x.com** → create/open an app.
2. The default keys shown (API Key / API Secret / Bearer Token) are **OAuth 1.0a — NOT what we use.**
3. App **Settings** tab → **User authentication settings** → **Set up**. Fill EXACTLY:
   - **App permissions:** Read and write (add DM if the user wants DMs)
   - **Type of App:** Web App, Automated App or Bot → **Confidential client** (this is what produces a Client Secret; Native/Public gives none)
   - **Callback URI / Redirect URL:** `http://localhost:8080/callback` (must match xurl's listener byte-for-byte)
   - **Website URL:** `https://iamstarchild.com` (pure display metadata; not used in auth; NOT required unique — every user can use the same value, zero technical impact)
4. **Save** → X shows **Client ID + Client Secret ONCE**. Secret shown once only; copy immediately.

### What the two URLs actually control (so you can answer the user)
- **Callback URI** = where X returns the OAuth authorization code. xurl spins up a
  local listener on `localhost:8080`; the code flows browser→xurl on the user's own
  machine, never through any external server. Both sides must be identical or X
  returns `redirect_uri_mismatch`.
- **Website URL** = display-only metadata. Not part of auth, not validated for
  uniqueness. Safe for all users to set to `https://iamstarchild.com`.

## STEP 2 — Collect credentials securely

`request_env_input` (NEVER ask for keys in chat):
- `X_OAUTH_CLIENT_ID` — X App Client ID (OAuth 2.0)
- `X_OAUTH_CLIENT_SECRET` — X App Client Secret (OAuth 2.0)

Remind the user: it's the OAuth 2.0 pair (after enabling User authentication
settings + Confidential), NOT API Key/Secret (1.0a), NOT Bearer Token.

## STEP 3 — Install xurl + register the app

```bash
npm install -g @xdevplatform/xurl          # validated v1.2.2
echo 'npm install -g @xdevplatform/xurl' >> setup.sh   # survive container restarts

xurl auth apps add starchild-x \
  --client-id "$X_OAUTH_CLIENT_ID" \
  --client-secret "$X_OAUTH_CLIENT_SECRET" \
  --redirect-uri "http://localhost:8080/callback"

xurl auth status      # confirm app registered, redirect_uri shows [app config]
```

## STEP 4 — Headless OAuth (this machine has no browser → user pastes the URL back)

`xurl auth oauth2 --headless` prompts on stdin for the pasted code and BLOCKS. A
plain `bash(background=true)` hits EOF immediately and fails. **Feed stdin via a FIFO
you write to later** when the user pastes the code:

```bash
rm -f /tmp/xurl_fifo && mkfifo /tmp/xurl_fifo
sleep 1800 > /tmp/xurl_fifo &                       # holder keeps FIFO open (no premature EOF)
xurl auth oauth2 --app starchild-x --headless < /tmp/xurl_fifo   # run via bash(background=true)
```

Then `bash_process(action='log')` to grab the printed authorization URL.

**Tell the user, clearly, in the visible reply:**
1. Open the printed `https://x.com/i/oauth2/authorize?...` URL in a browser on ANY device.
2. Click **Authorize app**.
3. The browser redirects to `http://localhost:8080/callback?state=...&code=...` — **the
   page will fail to load (it's THIS remote box's localhost, the user's browser can't
   reach it). That is EXPECTED. The code is in the address bar.**
4. Copy the **full** redirected URL from the address bar and paste it back in chat.

Feed it to the waiting process:
```bash
echo '<full redirected URL with code=>' > /tmp/xurl_fifo
```

xurl exchanges it for a token in `~/.xurl`. A warning "could not resolve username via
/2/users/me" is NOT a failure — that's the enrollment trap below.

## STEP 5 — ⚠️ The `client-not-enrolled` trap (very common, happens AFTER successful OAuth)

`xurl --app starchild-x /2/users/me` returns:
```json
{"reason":"client-not-enrolled","title":"Client Forbidden",
 "detail":"...App that is attached to a Project..."}
```
OAuth succeeded but the app lacks v2 API access. Fix in the portal (manual):

- **Free tier:** in the Dashboard you can **Move to Pay-per-use** directly on the
  free app — that grants v2 access. (The app being parked under "Standalone Apps" vs a
  Project is a red herring on current portal versions; the real gate is the
  **Pay-per-use / Production** enrollment.) Pay-per-use may require a card on file.
- After enrolling, **no re-authorization needed** — token persists. Just re-run the
  test. Propagation can take a minute or two.

Verify: `xurl --app starchild-x /2/users/me` must return the user object (id, name,
username), not `client-forbidden`.

## STEP 6 — Wire MCP into agent.yaml (native MCP client; NO agent code change)

starchild-clawd has a native MCP client (`core/mcp/*`: stdio / streamable-http / sse +
static `headers`). Add under `defaults.mcp_servers:` (or the user's agent.yaml):

```yaml
defaults:
  mcp_servers:        # MAPPING keyed by server name (NOT a YAML list)
    xmcp:
      transport: streamable-http
      url: https://api.x.com/mcp
      headers:
        Authorization: "Bearer <ACCESS_TOKEN_FROM_~/.xurl>"
      timeout: 30
```

⚠️ `mcp_servers` is a **mapping** (server name → definition), not a list. A list
form (`- name: xmcp`) is silently ignored (logged `must be a mapping, got list`).

Then `/mcp` to confirm the 24 tools register as `mcp__xmcp__<tool>`.

## STEP 7 — ⚠️⚠️ Token expiry & auto-refresh (THE make-or-break step)

The OAuth2 **access token expires in ~2 hours** (`offline.access` scope grants a
refresh_token, so renewal is possible). The native MCP client reads a **STATIC**
`headers` dict — it does NOT refresh on its own. **If you only paste the current token
into agent.yaml, MCP dies in ~2 hours.** You MUST run a refresh loop.

Refresh with xurl, then rewrite the bearer in agent.yaml and reload:

```bash
# read current access token after xurl refreshes it
xurl --app starchild-x /2/users/me >/dev/null 2>&1   # xurl auto-refreshes when near expiry on use
ACCESS=$(python3 -c "import yaml,os; d=yaml.safe_load(open(os.path.expanduser('~/.xurl'))); print(d['apps']['starchild-x']['oauth2_tokens']['']['oauth2']['access_token'])")
# patch agent.yaml header to the fresh token (use a small python/yaml rewrite), then:
# trigger /mcp reload so the new header takes effect
```

### Refresh mechanics (VERIFIED)
- Confidential client refresh: `POST https://api.x.com/2/oauth2/token` with HTTP
  **Basic auth** (`base64(client_id:client_secret)`) and body
  `grant_type=refresh_token&refresh_token=<rt>`. Returns a fresh `access_token`
  (expires_in 7200) AND a **NEW rotated `refresh_token`**.
- ⚠️ **refresh_token ROTATES every refresh** — the old one is invalidated. You MUST
  persist the new refresh_token (back into `~/.xurl`) or the next refresh fails.

### Making reload zero-manual (IMPORTANT — current code reality)
`core/mcp` has an mtime-gated `maybe_hot_reload()` (cheap single stat), BUT it is
currently called ONLY from the `/mcp reload` slash command (`force=True`). Nothing
calls it automatically per turn. So **out of the box, after a token refresh the live
MCP connection does NOT pick up the new bearer until someone runs `/mcp reload`**.
A scheduled task can't fix this from outside — task run.py runs in a separate process
and can't touch the server's in-process MCP manager singleton.

Two options:
1. **(recommended) Add a per-turn auto-reload hook** to starchild-clawd: call
   `maybe_hot_reload(registry)` (no force, mtime-gated) at the start of each agent
   turn. Then refresh task rewrites agent.yaml → next user message auto-reloads →
   user NEVER types `/mcp`. This is a small core change (PR to leon-dev). The header
   signature includes sorted headers, so a bearer change correctly triggers reconnect.
2. **(no code change)** Document that the user must run `/mcp reload` after each
   ~2h token expiry. Degraded UX — connection drops every 2 hours until reloaded.

Set up the refresh as a **scheduled_task** every ~60–90 min:
refresh token (Basic auth) → write new access_token into agent.yaml header → persist
new refresh_token to `~/.xurl`. With option 1 in place this is fully automatic.

Token store path: `~/.xurl` → `apps.starchild-x.oauth2_tokens[''].oauth2.{access_token,refresh_token,expiration_time}`.

---

## REST WRITE ENDPOINTS (not in MCP — call via xurl with the same token)

All authenticated with the OAuth2 bearer. `xurl` handles auth+refresh automatically:

| Action | Method + endpoint | Body / notes | Status |
|---|---|---|---|
| **Post a tweet** | `POST /2/tweets` | `{"text":"..."}` | ✅ tested |
| **Reply** | `POST /2/tweets` | `{"text":"...","reply":{"in_reply_to_tweet_id":"<id>"}}` | documented |
| **Quote** | `POST /2/tweets` | `{"text":"...","quote_tweet_id":"<id>"}` | documented |
| **Delete tweet** | `DELETE /2/tweets/{id}` | — | ✅ tested |
| **Like** | `POST /2/users/{user_id}/likes` | `{"tweet_id":"<id>"}` | documented |
| **Unlike** | `DELETE /2/users/{user_id}/likes/{tweet_id}` | — | documented |
| **Retweet** | `POST /2/users/{user_id}/retweets` | `{"tweet_id":"<id>"}` | documented |
| **Follow** | `POST /2/users/{user_id}/following` | `{"target_user_id":"<id>"}` | documented |
| **DM** | `POST /2/dm_conversations/with/{participant_id}/messages` | `{"text":"..."}` | documented |

Example (post via xurl):
```bash
xurl --app starchild-x -X POST /2/tweets -d '{"text":"hello from my agent"}'
```
`user_id` for likes/retweets = the authed user's id from `/2/users/me`.
Endpoints marked "documented" are from docs.x.com and not yet round-trip tested here —
verify on first real use and mark tested.

## The 24 MCP READ tools (register as `mcp__xmcp__<tool>`)

Search/news: `search_posts_all`, `search_news`, `get_news`, `search_users`,
`get_trends_by_woeid`, `get_posts_counts_recent`.
Posts: `get_posts_by_id`, `get_posts_by_ids`, `get_posts_liking_users`,
`get_posts_quoted_posts`, `get_posts_reposted_by`.
Users: `get_users_me`, `get_users_by_id`, `get_users_by_username`,
`get_users_by_usernames`, `get_users_timeline`, `get_users_posts`,
`get_users_mentions`.
Bookmarks (write-ish): `get_users_bookmarks`, `get_users_bookmarks_by_folder_id`,
`get_users_bookmark_folders`, `create_users_bookmark`, `create_users_bookmark_folder`,
`delete_users_bookmark`.

Common params: `max_results`, `*.fields` (comma list), `expansions`. `search_posts_all`
takes a `query` (supports operators like `from:`, `min_faves:`, `$CASHTAG`).

---

## FAQ

- **"I only see an OAuth 1.0a app / no Client ID."** You haven't enabled *User
  authentication settings*. Until you do, Keys & tokens shows only 1.0a. See STEP 1.
- **`redirect_uri_mismatch`.** Portal Callback URI ≠ `http://localhost:8080/callback`.
  Must be identical.
- **No Client Secret offered.** Type of App was Native/Public. Switch to
  Confidential (Web App / Bot).
- **`client-not-enrolled` after OAuth succeeds.** App lacks v2 access → Move to
  Pay-per-use (STEP 5).
- **The callback page won't load.** Expected — it's the remote box's localhost. The
  code is in the address bar; paste the full URL back.
- **MCP worked, then stopped ~2h later.** Access token expired and the static header
  went stale. Set up the refresh task (STEP 7).
- **Can I post through MCP?** No. Writes go through REST `/2/...` (see table). MCP is
  reads + bookmarks only.

## Update policy (X changes → bump this skill)

Update + version-bump (then PR, never push main) when any of these change:
- **MCP tool set** (new/renamed/removed tools, schema changes) → MINOR
- **REST write endpoints** (path/body changes) → MINOR, MAJOR if a signature breaks
- **X portal enrollment flow** (UI/steps for Pay-per-use, auth settings) → PATCH/MINOR
- **xurl CLI** flags/behavior → PATCH/MINOR

## Independence (skill-only, no agent code change)

This skill needs **no changes to agent code**. It relies on the already-native MCP
client (`core/mcp/*`) plus pure config (agent.yaml `mcp_servers`) and a scheduled
refresh task — all orchestrated by the agent following this skill. The ONLY prereq is
that the running build includes the MCP client. Read-only scraping without the user's
own app → use the `twitter` skill instead.

Validated: xurl 1.2.2 · MCP server xmcp 1.0.0 (protocol 2025-06-18) · 24 tools ·
access-level read-write-directmessages · default redirect `http://localhost:8080/callback`.
