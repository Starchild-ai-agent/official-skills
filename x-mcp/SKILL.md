---
name: x-mcp
description: >-
  Connect a user's own X (Twitter) dev app (BYOK) for the official X API MCP
  (reads) plus X v2 REST writes — post, reply, like, retweet, DM.

  Use when the user wants to act on X with their OWN X account or app — search,
  read timeline/users/news/trends/bookmarks via MCP, and post/reply/like/retweet/DM
  via REST. Walks through OAuth 2.0 setup in the X portal, xurl CLI registration,
  headless OAuth (user pastes the redirect URL back), the client-not-enrolled /
  Pay-per-use trap, the token-expiry auto-refresh mechanism, agent.yaml MCP wiring,
  and FAQ. For read-only scraping WITHOUT the user's own app, use the twitter skill.
version: 1.5.2
author: starchild
tags: [x, twitter, mcp, oauth, byok, post, tweet, dm, x-api, xurl]
---

# X API — MCP (reads) + REST (writes), BYOK

Connects the user's **own** X developer app so this agent can:
- **Read** via the official hosted **X MCP** (`https://api.x.com/mcp`) — 24 tools
- **Write** via the **X v2 REST API** (`https://api.x.com/2/...`) — post / delete / like / retweet / reply / DM

**Why BYOK (not a shared Starchild app):** X write access is per-app rate-limited
(~app-wide caps), pay-per-use billed to the app owner, and TOS liability sits with
the app owner. A shared app = single point of failure + neighbors starving each
other + concentrated billing + content-moderation liability. So every user brings
their own app + OAuth token. The token lives only on this machine (`~/.xurl`,
symlinked to the persistent workspace — see STEP 3),
never proxied.

## When to use this skill

Use when the user wants to act on X with their OWN account/app:
- "Connect my X / Twitter account so you can post for me"
- "Set up the X API with my dev app", "use my X developer keys"
- "Search recent tweets / read my timeline / read mentions" (with their own app)
- "Post / reply / like / retweet / DM on X as me"
- "Bookmark this tweet"

Do NOT use — pick the right alternative instead:
- "Summarize this tweet" / "what's @user posting" / cashtag scan, **no account needed**
  → use the `twitter` skill (read-only scraping via twitterapi.io, no OAuth)
- "Add the X / Grok *model*" → that's `xai-grok-onboarding` (chat model), unrelated
- The user has no X developer app and doesn't want one → `twitter` skill, or explain
  that writes require their own app

Disambiguator: `twitter` = read-only, no setup, anyone's public tweets. `x-mcp` =
the user's OWN authenticated account, can WRITE, needs one-time OAuth setup.

## See also
- `twitter` skill — read-only X scraping (no account, no OAuth) for any public tweet
- `config/context/references/model-onboarding.md` — if the user actually meant a chat
  model (Grok), not the X data API

## Preflight — build compatibility (check before you start)

This skill drives two platform capabilities. Confirm both before setup:

1. **Native MCP client (required for reads).** starchild-clawd must include
   `core/mcp/*` and read `defaults.mcp_servers` from agent.yaml. Quick check: run
   `/mcp` — if it returns a status block, the client exists. If `/mcp` is unknown or
   errors, the running build predates MCP support → reads via MCP won't work. The REST
   write path (xurl) still works regardless; or update the platform image.
2. **Per-turn hot-reload (required for automatic token refresh).** Needed so the
   ~2h token rotation reconnects automatically (STEP 7). Builds without it still work
   but need a manual `/mcp reload` after each refresh — documented as the fallback in
   STEP 7. There is no clean runtime probe; assume current builds have it, treat
   "MCP silently dies ~2h after a refresh and only `/mcp reload` revives it" as the
   signal that the build lacks the per-turn hook.

If neither MCP capability is present and the user only needs to read public tweets,
stop here and use the `twitter` skill instead — it needs no build support.

## Reads vs writes — two separate systems

| Capability | Channel | Validated |
|---|---|---|
| search posts/users/news, timeline, mentions, trends, bookmarks | **MCP** (24 tools) | connected |
| **post / delete / reply / like / retweet / follow / DM** | **REST `/2/...`** (NOT in MCP) | post+delete tested |

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

## STEP 3 — Install xurl + persist the credential store + register the app

⚠️ **Persistence is REQUIRED, not optional.** xurl keeps BOTH the app registration
AND the OAuth token in `~/.xurl` (i.e. `/root/.xurl`). `/root` is **ephemeral** — it is
wiped on every container restart, so without this step the user loses the connection
(and even the app registration) on the next restart and has to re-OAuth from scratch.
Keep the real file in the persistent workspace and symlink it back each boot. xurl
writes through symlinks (verified), so every xurl call transparently uses the
persistent file — no per-command `HOME` prefix needed.

```bash
npm install -g @xdevplatform/xurl          # validated v1.2.2

# Persist install + credential store across container restarts (idempotent).
# Append ONCE to workspace/setup.sh (which re-runs at every boot):
cat >> setup.sh <<'SH'
npm install -g @xdevplatform/xurl
# X (xurl) credential store: /root is ephemeral, keep ~/.xurl in the workspace
XURL_STORE=/data/workspace/.config/x-mcp/xurl_store
mkdir -p "$(dirname "$XURL_STORE")"; chmod 700 "$(dirname "$XURL_STORE")" 2>/dev/null || true
if [ -f /root/.xurl ] && [ ! -L /root/.xurl ]; then mv /root/.xurl "$XURL_STORE"; fi
ln -sf "$XURL_STORE" /root/.xurl
SH

# Run it now so the store is live for this session BEFORE registering the app:
XURL_STORE=/data/workspace/.config/x-mcp/xurl_store
mkdir -p "$(dirname "$XURL_STORE")"; chmod 700 "$(dirname "$XURL_STORE")" 2>/dev/null || true
if [ -f /root/.xurl ] && [ ! -L /root/.xurl ]; then mv /root/.xurl "$XURL_STORE"; fi
ln -sf "$XURL_STORE" /root/.xurl

xurl auth apps add starchild-x \
  --client-id "$X_OAUTH_CLIENT_ID" \
  --client-secret "$X_OAUTH_CLIENT_SECRET" \
  --redirect-uri "http://localhost:8080/callback"

xurl auth status      # confirm app registered, redirect_uri shows [app config]
ls -la /data/workspace/.config/x-mcp/xurl_store   # confirm store lives in workspace
```

The OAuth token from STEP 4 lands in this same persistent file, so once connected the
connection survives restarts. (`agent.yaml`'s MCP bearer is separate and already lives
in the workspace; the refresh task in STEP 7 keeps both in sync.)

## STEP 4 — Headless OAuth (this machine has no browser → user pastes the URL back)

`xurl auth oauth2 --headless` prints an authorize URL, then BLOCKS on stdin waiting
for the pasted code. The code is bound to a **PKCE code_verifier that lives only in
that process's memory** — if the process dies before the user pastes back, the code
can never be exchanged. So the whole flow must keep ONE xurl process alive from
"print URL" all the way through "exchange code".

### Persistent driver pattern
Run a single Python driver that holds xurl's stdin open via `subprocess.PIPE`,
writes the authorize URL to a file, waits up to ~10 min for a code file, then feeds
the code and captures the result. Key shape:

```python
proc = subprocess.Popen(["xurl","auth","oauth2","--app","starchild-x","--headless"],  # no USERNAME (see token-key note)
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
# 1) read stdout until the oauth2/authorize line → write it to /tmp/xurl_auth_url.txt
# 2) poll /tmp/xurl_code_input.txt (up to 600s) for the pasted callback URL/code
# 3) proc.stdin.write(code+"\n"); flush  → 4) read result → write /tmp/xurl_oauth_done.json
```
**Use the driver SHIPPED WITH THIS SKILL** — do NOT re-author it from memory (that's
how the hardcoded-username and wrong-timeout bugs creep back). It lives at
`skills/x-mcp/scripts/oauth_driver.py`. Launch it so it SURVIVES the 180s foreground
limit — stdout redirected to a file, detached, and DON'T block the foreground bash
on it:

```bash
# clean any stale driver/xurl FIRST (see IRON RULE #1), then:
python3 skills/x-mcp/scripts/oauth_driver.py >/tmp/oauth_driver_console.log 2>&1 &
sleep 8
cat /tmp/xurl_auth_url.txt        # the URL THIS live driver just wrote — give the user THIS one
pgrep -f oauth_driver.py >/dev/null && echo "driver alive, waiting for code"
```

The driver runs `xurl auth oauth2 --app starchild-x --headless` (no USERNAME arg),
captures the authorize URL to `/tmp/xurl_auth_url.txt`, waits up to 600s (~10 min) for
`/tmp/xurl_code_input.txt`, feeds the code, and writes the outcome to
`/tmp/xurl_oauth_done.json`.

> **⚠️ Token-key note (this WILL KeyError if you get it wrong).** Regardless of
> whether you pass a USERNAME, xurl resolves the account via `/2/users/me` and stores
> the token under that **resolved X handle** (e.g. `oauth2_tokens['ud_noel']`), NOT
> under an empty-string key. So **never hardcode the key** — discover it dynamically
> (one token per app):
> ```python
> import yaml, os
> d = yaml.safe_load(open(os.path.expanduser('~/.xurl')))
> toks = d['apps']['starchild-x']['oauth2_tokens']   # {'<handle>': {...}}
> key = next(iter(toks))                              # the resolved handle
> oauth = toks[key]['oauth2']                         # access_token / refresh_token / expiration_time
> ```

### OAuth driver rules
1. **Exactly ONE driver alive at a time.** Before starting, kill any stale
   `xurl auth oauth2` / `oauth_driver` PIDs **by exact PID, excluding your own shell**
   (NEVER `pkill -f oauth_driver.py` — that pattern matches your own bash command line
   and kills the shell running the cleanup). Safe snippet:
   ```bash
   SELF=$$
   for pat in "xurl auth oauth2" "oauth_driver.py"; do
     for pid in $(pgrep -f "$pat"); do [ "$pid" != "$SELF" ] && kill "$pid" 2>/dev/null; done
   done
   rm -f /tmp/xurl_auth_url.txt /tmp/xurl_code_input.txt /tmp/xurl_oauth_done.json /tmp/xurl_oauth.pid
   ```
2. **Give the user ONLY the URL the LIVE driver just wrote** — read it from
   `/tmp/xurl_auth_url.txt` AFTER this driver started. Never paste a URL from an
   earlier attempt or from chat history.
3. **If you ever restart, the previous authorize URL is DEAD.** Tell the user to
   discard it and use only the newest one.
4. **Verify the `state` matches** if exchange fails: the `state=` in the user's
   pasted callback must equal the `state=` in the URL the live driver generated. A
   mismatch means the callback came from an older authorize URL.

**Tell the user, clearly, in the visible reply:**
1. Open the `https://x.com/i/oauth2/authorize?...` URL (the one the live driver wrote)
   in a browser on ANY device.
2. Click **Authorize app**.
3. The browser redirects to `http://localhost:8080/callback?state=...&code=...` — **the
   page will fail to load (it's THIS remote box's localhost, the user's browser can't
   reach it). That is EXPECTED. The code is in the address bar.**
4. Copy the **full** redirected URL from the address bar and paste it back in chat.

Feed it to the waiting driver:
```bash
echo '<full redirected URL with code=>' > /tmp/xurl_code_input.txt
```

The driver exchanges it for a token in `~/.xurl` and writes `/tmp/xurl_oauth_done.json`.
A warning "could not resolve username via /2/users/me" is NOT a failure — that's the
enrollment trap below.

## STEP 5 — The `client-not-enrolled` enrollment gate

`xurl --app starchild-x /2/users/me` returns:
```json
{"reason":"client-not-enrolled","title":"Client Forbidden",
 "detail":"...App that is attached to a Project..."}
```
OAuth succeeded but the app lacks v2 API access. Fix in the portal (manual):

- **Free tier:** in the Dashboard you can **Move to Pay-per-use** directly on the
  free app — that grants v2 access. The required gate is **Pay-per-use /
  Production** enrollment. Pay-per-use may require a card on file.
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

`mcp_servers` is a **mapping** (server name → definition), not a list. A list
form (`- name: xmcp`) is silently ignored (logged `must be a mapping, got list`).

Then `/mcp` to confirm the 24 tools register as `mcp__xmcp__<tool>`.

## STEP 7 — Token expiry & auto-refresh

The OAuth2 **access token expires in ~2 hours** (`offline.access` scope grants a
refresh_token, so renewal is possible). The bearer in agent.yaml `headers` is static —
nothing refreshes the TOKEN VALUE on its own. **If you only paste the current token
into agent.yaml and never refresh, MCP dies in ~2 hours.** You MUST run a refresh loop
that rewrites the bearer. (Reconnecting with the new bearer IS automatic on current
clawd — see "Automatic reload on current clawd" below — but the token itself still has to be
refreshed and written.)

Refresh with xurl, then rewrite the bearer in agent.yaml (reconnect is automatic):

```bash
# read current access token after xurl refreshes it
xurl --app starchild-x /2/users/me >/dev/null 2>&1   # xurl auto-refreshes when near expiry on use
# token key = the resolved X handle, NOT '' — discover it dynamically (see token-key note in STEP 4)
ACCESS=$(python3 -c "import yaml,os; d=yaml.safe_load(open(os.path.expanduser('~/.xurl'))); t=d['apps']['starchild-x']['oauth2_tokens']; k=next(iter(t)); print(t[k]['oauth2']['access_token'])")
# patch agent.yaml header to the fresh token (a small python/yaml rewrite).
# On current clawd that's all — the next chat turn auto-reconnects (see below).
```

### Refresh mechanics
- Confidential client refresh: `POST https://api.x.com/2/oauth2/token` with HTTP
  **Basic auth** (`base64(client_id:client_secret)`) and body
  `grant_type=refresh_token&refresh_token=<rt>`. Returns a fresh `access_token`
  (expires_in 7200) AND a **NEW rotated `refresh_token`**.
- **refresh_token ROTATES every refresh** — the old one is invalidated. You MUST
  persist the new refresh_token (back into `~/.xurl`) or the next refresh fails.
- ✅ **Prefer xurl's own on-use refresh** (`xurl --app starchild-x /2/users/me`): xurl
  refreshes when near expiry and writes the rotated token back to `~/.xurl` itself,
  **through the symlink** (verified) — persistence stays intact, you don't touch the file.
- 🚫 **If you DO write `~/.xurl` yourself, NEVER use an atomic-rename write**
  (`tempfile` + `os.replace`/`os.rename`). Since `~/.xurl` is a **symlink** to the
  persistent workspace store (STEP 3), a rename **replaces the symlink with a regular
  file in ephemeral `/root`** — persistence silently breaks and the token vanishes on
  the next restart. (This is the standard "safe" pattern the ChatGPT/Grok `store.py`
  use — correct for real files, fatal for a symlink.) Verified: `os.replace` clobbers
  the symlink; in-place `open(path,"w")` and xurl both write **through** it. So write
  in place only:
  ```python
  # safe: follows the symlink, lands in the persistent workspace store
  with open(os.path.expanduser("~/.xurl"), "w") as f:
      yaml.safe_dump(data, f)
  ```

### Automatic reload on current clawd
Current starchild-clawd calls `maybe_hot_reload()` at the START of every `/chat`
and `/chat/stream` turn (mtime-gated, cheap single stat). So after the refresh task
rewrites the bearer in agent.yaml, **the very next chat turn auto-reconnects with the
new token — the user NEVER runs `/mcp reload`.** The MCP server config signature
includes sorted headers, so a bearer change is correctly classified as a reconnect.

So the refresh task only needs to do TWO things:
1. refresh the token (Basic auth) and **persist the rotated refresh_token** to `~/.xurl`
   (in-place write or via xurl only — NOT atomic-rename, see the symlink warning above),
2. **write the new access_token into the agent.yaml `headers.Authorization`** bearer
   (agent.yaml is already in the workspace, so atomic write is fine there).

No `/mcp reload`, no manual step. (A scheduled task can't reload the connection
itself — task run.py is a separate process and can't touch the in-process MCP
manager singleton — but it doesn't need to: the per-turn hook handles reconnection.)

**Older clawd builds without per-turn hot-reload**: if running a build that predates
the per-turn `maybe_hot_reload()` call, the live connection won't pick up the new
bearer until someone runs `/mcp reload` — in that case have the refresh task additionally
trigger a reload, or instruct the user to run `/mcp reload` after each ~2h refresh.

Set up the refresh as a **scheduled_task** every ~60–90 min (token lives ~2h):
refresh token (Basic auth) → persist rotated refresh_token to `~/.xurl` → write new
access_token into the agent.yaml bearer. On current clawd that is fully automatic.

Token store path: `~/.xurl` → `apps.starchild-x.oauth2_tokens['<resolved-handle>'].oauth2.{access_token,refresh_token,expiration_time}`.
The key is the X handle xurl resolves from `/2/users/me` (e.g. `'ud_noel'`), **not** an
empty string — read it dynamically with `next(iter(oauth2_tokens))` (one token per app).
`~/.xurl` is a symlink to the persistent `/data/workspace/.config/x-mcp/xurl_store`
(set up in STEP 3) — read/write `~/.xurl` as normal; persistence is transparent.

---

## REST WRITE ENDPOINTS (not in MCP — call via xurl with the same token)

All authenticated with the OAuth2 bearer. `xurl` handles auth+refresh automatically:

| Action | Method + endpoint | Body / notes | Status |
|---|---|---|---|
| **Post a tweet** | `POST /2/tweets` | `{"text":"..."}` | tested |
| **Reply** | `POST /2/tweets` | `{"text":"...","reply":{"in_reply_to_tweet_id":"<id>"}}` | documented |
| **Quote** | `POST /2/tweets` | `{"text":"...","quote_tweet_id":"<id>"}` | documented |
| **Delete tweet** | `DELETE /2/tweets/{id}` | — | tested |
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
- **MCP worked, then stopped ~2h later.** Access token expired and the bearer in
  agent.yaml went stale. Set up the refresh task that rewrites the bearer (STEP 7) —
  on current clawd the next chat turn then reconnects automatically, no `/mcp reload`.
- **Can I post through MCP?** No. Writes go through REST `/2/...` (see table). MCP is
  reads + bookmarks only.

## Critical rules

- **Never echo the access_token or refresh_token to chat.** They are persistent
  credentials in `~/.xurl`. When showing config, mask the bearer
  (`Bearer S0tHdk…`). The token never goes through the proxy or into chat history.
- **Never ask for the Client ID / Secret in chat.** Always collect via
  `request_env_input` (STEP 2).
- **Don't auto-poll / rush the OAuth step.** After printing the authorize URL, WAIT
  for the user to say they approved and paste the redirected URL back. Writing the
  code file (`/tmp/xurl_code_input.txt`) before they've pasted just makes the driver
  wait on empty input.
- **On `client-not-enrolled`, don't retry blindly.** It's a portal enrollment gate
  (STEP 5), not a transient error — retrying the same call keeps failing. Guide the
  user to Move to Pay-per-use, then re-test once.
- **Writes are REST, not MCP.** Don't look for a `create_post` MCP tool — it doesn't
  exist. Use the REST table.
- **Token rotates on every refresh.** Always persist the NEW refresh_token or the
  next refresh dies (STEP 7).

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
