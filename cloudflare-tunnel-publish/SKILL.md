---
name: cloudflare-tunnel-publish
version: 1.1.1
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

Run `bash skills/cloudflare-tunnel-publish/scripts/run_tunnel.sh`. It:
- Downloads the `cloudflared` binary to `workspace/bin/cloudflared` if missing
- Reads run_token from `workspace/.cf_state.json`
- Launches `cloudflared tunnel run --token <TOKEN>` in background via `bash(background=true)`
- Returns the bash session_id so we can poll/log later

Save the session_id to state. Tell the user the tunnel daemon is running.

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

### ⚠️ Container restarts will kill your tunnel
**This is the #1 issue users hit after deployment.** The Starchild container can restart for several reasons:
- User-triggered restart
- Platform agent updates (auto-applied; can happen any time)
- Out-of-memory crash
- Container migration

When the container restarts, **every background process dies** — including:
- Your local service (Flask app, static server, dashboard, dev server, etc.)
- The `cloudflared` tunnel client

DNS records and the Cloudflare-side Tunnel config persist (they live on Cloudflare's servers), but the connection drops. Result: `https://yourdomain.com` will return **502 / 521 / 530** until both processes are restarted.

**The fix: register the services in `workspace/setup.sh`.** This file runs every time the container starts. Use a dedicated `scripts/start_services.sh` to keep it organized and idempotent.

**Pattern:** PID-file based, idempotent (safe to re-run), uses `setsid` so the recorded PID survives bash exit.

```bash
# scripts/start_services.sh
#!/usr/bin/env bash
set -uo pipefail
WS=/data/workspace
LOGDIR="$WS/logs"; PIDDIR="$WS/run"
mkdir -p "$LOGDIR" "$PIDDIR"

is_alive() { [ -f "$1" ] && [ -d "/proc/$(cat "$1" 2>/dev/null)" ]; }

start_service() {
  local name="$1" wd="$2" cmd="$3"
  local pidfile="$PIDDIR/$name.pid"
  is_alive "$pidfile" && return 0
  cd "$wd" || return 1
  setsid bash -c "exec $cmd" >> "$LOGDIR/$name.log" 2>&1 < /dev/null &
  echo $! > "$pidfile"
}

# 1. Local service (your app on some port)
start_service myapp "$WS/output/myapp" "exec python3 -m http.server 8765 --bind 127.0.0.1"

# 2. Cloudflare Tunnel
start_service cloudflared "$WS" "exec bash $WS/skills/cloudflare-tunnel-publish/scripts/run_tunnel.sh"
```

**Hook into `workspace/setup.sh`** (created on first container boot, runs on every boot):
```bash
# Auto-restart user-facing services. Background — never blocks setup.
bash /data/workspace/scripts/start_services.sh &
disown
```

**Critical implementation details (don't skip these — learned the hard way):**
- ✅ Use `setsid bash -c "exec ..."` — without `exec`, `$!` records the wrapper bash PID, which exits immediately and orphans the real process beyond tracking.
- ✅ Pass the command **without** a leading `exec` from the caller — the wrapper already adds one. Calling `start_service x dir "exec foo"` becomes `bash -c "exec exec foo"` which fails with `exec: exec: not found`.
- ✅ Redirect stdin from `/dev/null` so the service doesn't block on terminal input after detach.
- ✅ Background the entire `start_services.sh` call from `setup.sh` with `&` and `disown` — otherwise `cloudflared` (which runs forever) blocks `setup.sh`, blocking the agent from starting.
- ✅ The PID-file check makes the script idempotent — safe to re-run mid-session for testing without spawning duplicates.
- ❌ Don't use `nohup` from the agent toolkit — the runtime explicitly rejects it for orphan-process reasons.
- ❌ Don't rely on `pgrep` — not installed in the Starchild container. Use `[ -d /proc/$PID ]` instead.

**Port collision is a silent failure.** The Starchild workspace can have OTHER projects/sessions still listening on common ports (8000, 8080, 8765, etc.). When your service `bind()` fails with `Address already in use`, it exits immediately — but `curl localhost:<port>` still returns 200, because **someone else's app is answering on that port**. You'll think the tunnel is working, then realize the wrong content is being served. Mitigations:
- Use a high, project-unique port (e.g. `18765` instead of `8765`)
- Always `tail logs/<service>.log` after first launch to catch `OSError: [Errno 98]`
- Verify with the inode-based port-owner check (see `check_status.py` or the snippet in Phase 8) that the listening process is yours

**Verify content, not just status code.** After tunnel comes up, fetch the actual page and confirm it's YOUR content — `curl https://yourdomain.com | head` and check the title/markup. A 200 from an unrelated workspace process can mislead for hours.

**Verification after setup:**
```bash
# Right after editing setup.sh, run start_services.sh manually once to test
bash /data/workspace/scripts/start_services.sh
# Then verify both PIDs are alive
for f in /data/workspace/run/*.pid; do
  pid=$(cat "$f")
  echo "$f → pid=$pid → $([ -d /proc/$pid ] && echo ALIVE || echo DEAD)"
done
# And re-run to confirm idempotency (should say "already running")
bash /data/workspace/scripts/start_services.sh
tail -5 /data/workspace/logs/startup.log
```

**Tell the user explicitly:**
> 🔔 你的服务现在在容器里跑。Starchild 的容器可能因为更新、内存或迁移**任何时候**自动重启，重启后所有进程都会死。我已经把启动脚本写进 `workspace/setup.sh`，下次容器起来会自动拉起服务和隧道——你不用管。如果哪天访问域名变成 502/521/530，那就是服务还没拉起来或者启动失败，让我看一眼 `logs/startup.log` 和 `logs/cloudflared.log` 就能定位。

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
  "cloudflared_session_id": "bash-..."
}
```

Use this for teardown, status checks, and re-runs without re-asking the user.
