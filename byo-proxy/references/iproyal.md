# IPRoyal residential proxy reference

Loaded by `byo-proxy` only when the user is configuring or debugging IPRoyal.
Source of truth: <https://docs.iproyal.com/proxies/residential>.

## Endpoint

```
geo.iproyal.com:12321
```

Single endpoint for all countries. Region selection happens **inside the password field**.

> Historical note: IPRoyal used to put these params in the *username* field. Starting
> 2026, that format returns `407 Proxy Authentication Required` — params must now
> be appended to the password.

## Password parameter format

```
<password>_country-<cc>[_state-<st>][_city-<city>][_session-<id>][_lifetime-<N>m][_streaming-1]
```

Parameters are joined with `_` and follow the literal password.

| Param | Example | Meaning |
|---|---|---|
| `country-XX` | `country-jp` | ISO-3166-1 alpha-2, lowercase |
| `state-NAME` | `state-california` | US states only; lowercase, hyphens for spaces |
| `city-NAME` | `city-tokyo` | Lowercase, hyphens for spaces. Country must be set. |
| `session-ID` | `session-abc123` | Pin a logical session. Same id → same IP (within `lifetime`). |
| `lifetime-Nm` | `lifetime-30m` | Sticky-session lifetime, 1..1440 minutes. Requires `session-`. |
| `streaming-1` | `streaming-1` | Optimized for video/audio streaming. |

Without `session-`, IPRoyal rotates the exit IP on every request — good for scraping,
bad for sites that pin you to a session cookie.

## Auth

HTTP basic auth in the proxy URL: `http://<username>:<password>_<params>@geo.iproyal.com:12321`.

Both username and password come from your IPRoyal dashboard:
**Residential → Access**. They are *not* your account login.

## Country coverage (the 50 we expose by default)

Americas: `us ca mx br ar cl co pe`
Europe:   `gb de fr nl es it se no fi dk ch at be pl ie pt cz ro ru ua tr`
Asia:     `jp kr sg hk tw th vn id my ph in pk`
Oceania:  `au nz`
Africa:   `za eg ng ke`
Mideast:  `ae sa il`

IPRoyal advertises 195+ countries — extend `IPROYAL_COUNTRIES` in `exports.py`
if a user needs a code that isn't in this list. Verify with `test_proxy.py` after adding.

## Pricing model (informational)

Pay-as-you-go from $1.75/GB, no monthly minimum (as of 2026-Q1). Billed per byte,
not per request, so rotating vs. sticky doesn't change cost — only your traffic shape does.

## Verifying connectivity

```bash
curl -x "http://USER:PASS_country-jp@geo.iproyal.com:12321" https://ifconfig.co/json
```

Expected: `country_iso: "JP"`, `ip` is a Japanese residential IP.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `407 Proxy Authentication Required` | wrong username/password, **or** params still in username field (old format) | re-run `setup_provider.py iproyal`; if you hand-built the URL, move params to the password field |
| `502 Bad Gateway` | unsupported country code | check the table above |
| Got an IP from the wrong country | IPRoyal pool depleted; nearest country returned | retry, or use a different country |
| Connection succeeds but site still blocks you | residential IP burned for that site | rotate (drop `session-`) or pick a different country |
| Sticky session changes IP early | session expired (lifetime exceeded) or IPRoyal evicted | shorter requests, or accept rotation |
