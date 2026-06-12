---
name: cloudflare-tunnel-publish
version: 1.2.1
description: |
  Publish a local service to a user-owned custom domain via Cloudflare Tunnel.

  Use when the user wants their own domain instead of community.iamstarchild.com (e.g. app.mydomain.com, fix SSL 521 on a custom domain).
keywords: cloudflare, tunnel, cloudflared, custom domain, subdomain, hostname, DNS, SSL, TLS, publish, host, bind, expose, 自定义域名, 自己的域名, 绑定域名, 子域名, 二级域名, 域名解析, 上线, 发布, 部署, ERR_SSL_VERSION_OR_CIPHER_MISMATCH, 502, 521, 530
triggers:
  - 想用我自己的域名
  - 把服务发布到我的域名
  - 把网站绑定到我的域名
  - 绑定我买的域名
  - 自定义域名
  - 自己的子域名
  - 不要 community.iamstarchild.com
  - hello.example.com 这种地址
  - cloudflare tunnel
  - publish to my own domain
  - bind a custom domain
  - host on my domain
  - subdomain pointing to localhost
  - expose localhost on a domain
  - point my domain at this service
  - ERR_SSL_VERSION_OR_CIPHER_MISMATCH
  - 530 cloudflare
  - 521 web server is down
metadata:
  starchild:
    emoji: "🌐"
    skillKey: cloudflare-tunnel-publish
    requires:
      env: [CLOUDFLARE_API_TOKEN]
      bins: [python3, curl]
user-invocable: true
disable-model-invocation: false

---

## What this skill does

Turns a service running on a local port (default: a Starchild preview, but works for any HTTP service) into something the world can reach at `app.userdomain.com`, using **Cloudflare Tunnel**. No public IP required, no inbound ports opened, free SSL.

**Two roles in the flow:**

- **User does manually** (must, can't be automated): create Cloudflare account, buy/transfer domain to Cloudflare, create API Token.
- **Agent does automatically** (this skill): verify token, pick zone, create tunnel, configure ingress, create DNS, install + start `cloudflared`, verify the public URL works.

## Audience assumption

Treat the user as a **beginner**. They may have never used Cloudflare. Walk them through one micro-step at a time, wait for confirmation, then move on. Do NOT dump the whole 10-step plan and disappear.

## Workflow

### Phase 0 — Set the stage (1 message)

Tell the user in plain language what's about to happen, in 4 phases:

1. They register a Cloudflare account + add a domain (manual, ~5 min)
2. They create an API Token and give it to you securely (manual, ~2 min)
3. You build the tunnel + DNS + start it (automatic, ~1 min)
4. You test the URL together (automatic)

Ask: **"Do you already have a domain on Cloudflare, or do we need to start from scratch?"** Branch on the answer.

### Phase 1 — Get the user a domain on Cloudflare

If they don't have one yet:

- Direct them to https://dash.cloudflare.com/sign-up to register
- Then https://dash.cloudflare.com/?to=/:account/domains to buy a domain (Cloudflare sells `.com / .net / .org / .io / .dev / .app` etc. at registry cost), OR add an existing domain and change nameservers
- Wait for them to confirm "domain is active in Cloudflare" before proceeding

Beginner hint to share: "When the domain shows status **Active** in your Cloudflare dashboard, we're good to continue."

If they already have one: skip to Phase 2.

### Phase 2 — Create the API Token

Send them this exact link (it pre-fills the right permissions when possible, and the user can also build it manually):

> https://dash.cloudflare.com/profile/api-tokens → **Create Token** → **Create Custom Token**

Required permissions (tell them to add these three):

- **Account** → **Cloudflare Tunnel** → **Edit**
- **Zone** → **DNS** → **Edit**
- **Zone** → **Zone** → **Read**

Account Resources: their account. Zone Resources: **Include All zones** (or specifically the domain). TTL: leave default.

After they click **Continue to summary** → **Create Token** → Cloudflare shows the token **once**. Tell them: **do not paste it in chat**.

### Phase 3 — Receive the token securely

Call `request_env_input` with:

```
env_vars=[{"key": "CLOUDFLARE_API_TOKEN", "label": "Cloudflare API Token", "required": true}]
reason="Used to create the tunnel and DNS record on your domain. Stored locally in workspace/.env, never echoed in chat."
```

Wait for the user to submit it via the secure popup. **Do not retry-loop** if they don't submit immediately — just wait.

### Phase 4 — Verify token + pick the zone

Run `python3 skills/cloudflare-tunnel-publish/scripts/verify.py`. It prints:
- Token validity
- The user's account_id (saves to `workspace/.cf_state.json`)
- All zones (domains) on the account

If multiple zones, ask the user which domain to use. Save `zone_id` and `zone_name` to state.

### Phase 5 — Decide what to publish

Ask the user two things:

1. **Subdomain** (e.g., `app`, `demo`, `www`) → final hostname will be `<sub>.<zone_name>`. Apex domain (`@`) is also allowed.
2. **Local port** (e.g., `8080`, `3000`). If they say "my Starchild preview", run `cat /data/previews.json 2>/dev/null` to look up an existing preview's port; otherwise ask explicitly.

Default service URL: `http://localhost:<port>`.

### Phase 6 — Build the tunnel (automated)

Run `python3 skills/cloudflare-tunnel-publish/scripts/setup.py --hostname <full_hostname> --port <port>`.

The script does, in order:
1. Create a remotely-managed tunnel (`config_src: "cloudflare"`) named `starchild-<hostname>`
2. Fetch the tunnel **run token** (a long base64 string used to start `cloudflared`)
3. PUT the ingress configuration: `<hostname>` → `http://localhost:<port>`, fallback `404`
4. Create a CNAME DNS record: `<hostname>` → `<tunnel_id>.cfargotunnel.com`, **proxied = true**
5. Save tunnel_id + run_token + hostname to `workspace/.cf_state.json`

If a tunnel with the same name exists, reuse it instead of erroring.

### Phase 7 — Start cloudflared

Run `bash skills/cloudflare-tunnel-publish/scripts/keepalive.sh` — this is the
canonical way to bring the site up. `keepalive.sh` is the single start+heal
brain (see "Keeping it alive" below): it reads `.cf_state.json`, starts the app
(if you recorded `--app-cmd`) and the tunnel, and verifies the public URL.
`run_tunnel.sh` is the lower-level tunnel-only launcher that `keepalive.sh`
calls — it downloads `cloudflared` to `workspace/bin/` if missing, reads the
run_token from `.cf_state.json`, and runs `cloudflared tunnel run`.

Tell the user the site is up. The SAME `keepalive.sh` is what you'll wire into
boot + a schedule for durability — don't hand-roll a separate starter.

### Phase 8 — Verify

⚠️ **Do not use the container's `curl https://<hostname>` directly** — the container's resolver caches stale NXDOMAIN for new domains and will lie to you. Always verify via DoH:

```bash
curl -sS "https://dns.google/resolve?name=<hostname>&type=A" | python3 -m json.tool
```

Three possible outcomes:

1. **`Status: 0` + IPs in `Answer`** → live. Now `curl -I https://<hostname>` should return 200/301/302. Show the user their URL. 🎉
2. **`Status: 3` (NXDOMAIN) + Authority = TLD registry NS** (e.g. `ns.trs-dns.com`) → **TLD registry hasn't propagated the new domain yet.** Tell the user: configuration is 100% done, wait 30–60 min (newly registered domains can take up to 24 h), then retry. Don't keep polling — let them check on their own device.
3. **Tunnel logs show errors** (check `bash_process(action='log', session_id=...)`) → real config bug. Common culprits: ingress not pointing at the right port, local service not running, wrong CNAME target.

## Decision rules

- **User says "my service is on my laptop, not in Starchild"** → exact same flow, but Phase 7 must run on their laptop, not in this container. Give them the equivalent install command for their OS:
  - macOS: `brew install cloudflared && cloudflared tunnel run --token <TOKEN>`
  - Linux/Windows: link to https://github.com/cloudflare/cloudflared/releases/latest
  Send the run_token via `request_env_input` if needed, or just print it once and tell them to copy it (it's safe to share with their own machine, but never paste back to chat).

- **User wants multiple subdomains** → reuse the same tunnel; PUT a new ingress config that lists all hostnames; create one CNAME per hostname.

- **User wants to remove it** → run `python3 skills/cloudflare-tunnel-publish/scripts/teardown.py` (deletes DNS + tunnel + kills the local cloudflared process).

## Gotchas (⚠️ all confirmed in real runs)

### Token / API
- **`Cloudflare-Tunnel:Edit` does NOT grant `/accounts` listing.** Calling `GET /accounts` returns an empty list even with a valid token. **Solution:** derive `account_id` from any zone's embedded `account.id` field — `verify.py` already does this. Do NOT add `Account:Account Settings:Read` just to fix it; the zone trick is cleaner.
- The "run token" from `GET /accounts/{id}/cfd_tunnel/{tunnel_id}/token` is what `cloudflared tunnel run --token` consumes. Do not confuse with:
  - **tunnel secret** — only relevant for legacy locally-managed tunnels (we don't use)
  - **API Token** — used to call api.cloudflare.com

### Tunnel / Ingress
- The CNAME target must be `<tunnel_id>.cfargotunnel.com`, NOT the tunnel name.
- Remotely-managed tunnel (`config_src: "cloudflare"`) routes via the API config endpoint, NOT a local `config.yml`. Do not generate one.
- Creating a tunnel via API requires a `tunnel_secret` field (32 random bytes, base64) even for `config_src=cloudflare`. `setup.py` generates one automatically.

### Universal SSL provisioning lag — the OTHER big trap
After DNS propagates, the user may still hit `ERR_SSL_VERSION_OR_CIPHER_MISMATCH` in the browser. This is NOT a bug — Cloudflare hasn't issued the **Universal SSL certificate** for the new hostname yet.

**Diagnosis (run from container — no auth needed):**
```bash
echo | timeout 10 openssl s_client -connect <hostname>:443 -servername <hostname> 2>&1 | grep -E "(handshake|peer certificate|Cipher is)"
```
- `no peer certificate available` + `handshake failure` → cert not issued yet ⏳
- Real cert returned → working ✅

**Timing:**
- Established zones with prior certs: usually < 5 min
- **Brand-new domains: 15 min ~ 24 h** (DNS validation + CA signing + edge propagation)

**What to tell the user:**
1. Open `dash.cloudflare.com → <domain> → SSL/TLS → Edge Certificates`
2. Look for a row like `*.<domain>, <domain>` and check status:
   - `Active` → done, refresh browser
   - `Pending Validation` / `Initializing` → wait
3. Confirm `SSL/TLS → Overview → Encryption mode` is **Full** (not Flexible, not Full Strict). Tunnel always carries HTTPS to the origin, so Full is the right match.

**Don't:** Tell the user to add an Advanced Certificate ($$$) or to change DNS — neither helps. Just wait.

### DNS propagation — the big trap
**Newly registered domains take 30 min ~ 2 h (sometimes up to 24 h) to propagate across the global TLD registry**, even when the Cloudflare dashboard shows "Active" instantly. Symptoms:
- `dig @1.1.1.1 yourdomain.com NS` returns NXDOMAIN (Status=3)
- The Authority section shows the TLD's registry NS (e.g., `ns.trs-dns.com` for `.fun` via Tucows), NOT Cloudflare's NS
- `cloudflared` tunnel is connected and healthy, but `https://yourdomain.com` returns DNS resolution failure

**This is NOT a bug in the skill — it's TLD registry sync lag.** Use the diagnostic snippet below to distinguish it from real issues. Tell the user: "Configuration is complete. Wait 30–60 minutes and try again. Nothing more to do on our side."

### Container DNS — false negative
When testing from inside the Starchild container, the container's local resolver may not see new domains for hours. Always cross-check with public DoH:
```bash
curl -sS "https://dns.google/resolve?name=hello.example.com&type=A" | python3 -m json.tool
```
- `Status: 0` + `Answer` array with IPs → working ✅
- `Status: 3` (NXDOMAIN) + `Authority: ns.trs-dns.com` (or similar registry NS) → TLD propagation pending ⏳
- `Status: 0` but no `Answer` → CNAME exists but Cloudflare orange-cloud not yet routing → wait 30s

## Keeping it alive — one script, two triggers

This is the part agents get wrong. "Publish" is easy; keeping a tunnel site up
for weeks is the real job. The Starchild container restarts without warning
(platform updates, OOM, migration, user reboot), and `cloudflared` *also* dies
on its own mid-life (network blip, edge reset, QUIC failure) while the container
keeps running. Either one leaves `https://yourdomain.com` returning
**502 / 521 / 530 / 1033** until something restarts the processes. DNS and the
Cloudflare-side tunnel config survive (they live on Cloudflare's servers) — only
the local processes need relaunching.

**The design: ONE idempotent recovery brain (`scripts/keepalive.sh`) called from
TWO triggers.** Do not write per-project starter/healer scripts — that's how the
two copies drift apart. `keepalive.sh` ships with this skill and is generic: it
reads `hostname`, `port`, `app_cmd`, `app_dir` from `.cf_state.json`, so the same
file works for any domain. The calling agent writes ZERO project-specific shell.

What `keepalive.sh` does each run:
1. Probe the **public** URL (reachability, not just PID — a `cloudflared` process
   can be alive but disconnected).
2. Healthy → log one line, exit **silently**.
3. Down → diagnose: local app port closed → restart app (via `app_cmd`) **and**
   tunnel; only the tunnel dead → restart just the tunnel. Then re-verify with a
   few retries (covers cold-start warm-up).
4. Report on **state transitions only** (tracked in `run/keepalive.state`):
   newly-recovered or newly-failed prints one line; steady-state (healthy, or
   already-known-down) is silent. So a scheduled task pushes signal, never spam.

### Step 1 — record how to start the app (at setup time)

Pass `--app-cmd` / `--app-dir` to `setup.py` so keepalive can restart the app,
not just the tunnel:
```
python3 setup.py --hostname app.example.com --port 8765 \
    --app-cmd "python3 server.py" --app-dir projects/myapp
```
If you omit `--app-cmd`, keepalive guards the **tunnel only** and cannot revive a
crashed app. Always record it unless the app is supervised elsewhere.

### Step 2 — start the site

```
bash skills/cloudflare-tunnel-publish/scripts/keepalive.sh
```
Idempotent: starts whatever is down, no-op when healthy.

### Step 3 — survive container restarts (boot trigger)

Add keepalive to `workspace/setup.sh` (runs on every container boot):
```bash
# Bring the tunnel site back after a restart. keepalive.sh only READS
# .cf_state.json — no Cloudflare API call, no token needed at boot.
if [ -f /data/workspace/.cf_state.json ]; then
  bash /data/workspace/skills/cloudflare-tunnel-publish/scripts/keepalive.sh &
  disown
fi
```

> 🚫 **NEVER put `setup.py` in `setup.sh`.** `setup.py` is config-time: it calls
> the Cloudflare API, may rotate the run_token, and overwrites `.cf_state.json`.
> Running it on every boot is wasteful, can hit rate limits, breaks if the API
> token was removed, and can change a working config. Boot must only *read* state
> — that's exactly what `keepalive.sh` does. The name "setup" tempts you to put
> it in "setup.sh"; resist it.

### Step 4 — survive mid-life process death (watchdog trigger)

Schedule the SAME script as a cheap `command`-mode task:
```
scheduled_task(action="schedule",
  schedule="every 2 minutes",
  command="cd /data/workspace && bash skills/cloudflare-tunnel-publish/scripts/keepalive.sh",
  title="<hostname> keepalive")
```
- Use a **relative** command with `cd /data/workspace &&`. An absolute
  `/data/workspace/...` path can be normalized by the scheduler into a
  non-existent `/data/skills/...` (the `workspace/` segment gets dropped), so
  every run fails silently. `cd` + relative path is immune. (Confirmed in a real
  run.)
- Keep `deliver` at its default so the transition-only alerts actually reach the
  user. keepalive is already silent on healthy runs, so there's no spam to
  suppress — and a real outage should ping you.
- The interval may be normalized (e.g. "every 2 minutes" → 3 min) — fine.

### Verify durability (do all of this before claiming "stable")

```bash
# 1. start + idempotency
bash skills/cloudflare-tunnel-publish/scripts/keepalive.sh   # brings up
bash skills/cloudflare-tunnel-publish/scripts/keepalive.sh   # silent no-op
tail -5 logs/keepalive.log                                   # ok https://...
# 2. boot wired
grep keepalive setup.sh
# 3. watchdog registered + command stored correctly (relative path!)
#    scheduled_task(action="list")
```
**Don't claim "long-term stable" after only editing `setup.sh`.** That covers
restarts but not mid-life death. Confirm BOTH triggers (boot + schedule) point at
keepalive.sh, and that the first run logged `ok https://...`.

**Port collision is a silent failure.** Other workspace projects may already hold
common ports (8000/8080/8765). If your app's `bind()` fails with `Address already
in use` it exits, but `curl localhost:<port>` still returns 200 — someone else's
app is answering. Use a high, project-unique port and verify the page is *your*
content (`curl https://yourdomain.com | head`), not just a 200.

**Tell the user explicitly:**
> 🔔 你的站点跑在容器里。容器可能因更新/内存/迁移**随时**重启，隧道进程偶尔也会自己掉线（域名变 502/521/530/1033）。我已经把一个自愈脚本写进了 `workspace/setup.sh`（开机自动拉起）并设了每几分钟一次的巡检（掉线自动重拉、恢复/失败才通知你）。两层都指向同一个脚本，你基本不用管。真打不开时让我看一眼 `logs/keepalive.log` 和 `logs/cloudflared.log` 就能定位。

### Plan limits
- **Free plan is enough.** No upsell needed.
- Free plan only proxies ports 80/443 publicly — irrelevant to us, since the tunnel always exposes 443 to the world; `localhost:<port>` can be anything.

## State file format

`workspace/.cf_state.json`:
```json
{
  "account_id": "...",
  "zone_id": "...",
  "zone_name": "example.com",
  "hostname": "app.example.com",
  "port": 8080,
  "tunnel_id": "...",
  "tunnel_name": "starchild-app-example-com",
  "run_token": "...",
  "app_cmd": "python3 server.py",
  "app_dir": "/data/workspace/projects/myapp"
}
```

Use this for teardown, status checks, and re-runs without re-asking the user.
