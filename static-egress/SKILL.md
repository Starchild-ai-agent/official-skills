---
name: static-egress
version: 0.1.0
description: |
  Give this agent a fixed egress IP for TCP services that use IP allowlists (RDS/Postgres, MySQL, Redis, Kafka).

  Use when a database or API firewall keeps failing because the agent's outbound IP changes (e.g. "RDS whitelist broke again", "our IP isn't in the security group"), or when you need the agent to appear from one stable address for raw TCP traffic.
delivery: script
metadata:
  starchild:
    emoji: "🎯"
    skillKey: static-egress
    requires:
      bins: [python3]
user-invocable: true
author: starchild
tags: [proxy, static-ip, egress, firewall, allowlist, rds, tcp, postgres]
---

# static-egress — a fixed outbound IP for this agent

The platform's relay app holds a **static egress IP**; your TCP traffic goes out
through it. The target's firewall then allowlists **one address, permanently** —
it never has to track this agent's drifting egress again.

```
agent container ──6PN private──▶ sc-static-egress relay ──static egress IP──▶ your DB
```

## When to Use

- A DB/API firewall is keyed on **source IP** and the agent's IP keeps changing.
- You need a **stable source address for raw TCP** (Postgres 5432, MySQL 3306, Redis 6379…).
- Someone must allowlist *your* traffic and you want to hand them one IP.

## When NOT to Use

| Situation | Use instead |
|---|---|
| HTTP(S) API calls | `byo-proxy` (per-request, bring your own account) or the platform's `sc-proxy` |
| Geo-blocked HTTP request | `sc-vpn` |
| The DB supports **IAM database authentication** | IAM auth — but note it removes *passwords*, **not** IP requirements; the firewall still applies |
| The DB is **not reachable from the public internet** (VPC-private endpoint) | This relay cannot reach it either. Ask the platform team for an AWS-side relay/tunnel. |
| The target is inside the platform's own private network (a `.internal` service, `localhost`, or a private/link-local address) | **Refused by policy** — the relay only dials external destinations. Reach those directly. |
| You want a **different IP per request** | Not possible here — this is a container-level egress, not per-request routing |

## How to Call

```bash
# 1. Open an allocation for the target(s) you need to reach
python3 skills/static-egress/scripts/enable.py --target db-prod.xxx.rds.amazonaws.com:5432

# 2. Prove it works (NEVER skip: it checks the exit IP *and* a real TCP handshake)
python3 skills/static-egress/scripts/verify.py --target db-prod.xxx.rds.amazonaws.com:5432

# 3. Show the current allocation (never prints the credential)
python3 skills/static-egress/scripts/status.py

# 4. Stop paying for it / revoke the credential
python3 skills/static-egress/scripts/disable.py
```

Or call it in-process (another skill wiring the egress without shelling out):

```python
from core.skill_tools import _modules
egress = _modules["static-egress"]
egress.enable_egress(["db-prod.abc123.us-east-1.rds.amazonaws.com:5432"])  # -> allowlist + rule
egress.verify_egress("db-prod.abc123.us-east-1.rds.amazonaws.com:5432")    # read-only proof
egress.egress_status()                                                     # read-only
egress.disable_egress()                                                    # revoke
```

`enable.py` is **idempotent**: re-running keeps the same egress IPs, so an
allowlist entry you already installed stays valid. It mints a fresh credential
each time and revokes the previous one, so it also doubles as "renew".

## Workflows — the typical case: an RDS Postgres behind a security group

This is the case the service exists for: the agent's own egress IP drifts, RDS's
security group allowlists IPs, so the allowlist keeps breaking. Put the static IP
on the relay and point the DB client at the relay.

**No database yet?** Prove the mechanism first — it needs no DB and no
allocation of your own (it saves and restores whatever you already have):

```bash
python3 skills/static-egress/scripts/selftest.py
```

It must print two `PASS` lines:

- `tcp + source address` — the relay reaches a real target and **the far end sees
  the allowlisted address**. A `MISMATCH` here is exactly the condition that
  breaks an RDS allowlist.
- `tls verify-full via relay` — a TLS handshake with hostname verification
  succeeds while the socket goes to loopback, i.e. the `host` + `hostaddr`
  semantics the recipe below relies on.

It cannot prove that *your* firewall allows the address or that your endpoint is
reachable — only a real target can, which is what step 3 is for.

**1. Open an allocation for the DB endpoint**

```bash
python3 skills/static-egress/scripts/enable.py \
    --target db-prod.abc123.us-east-1.rds.amazonaws.com:5432
```

Read the two addresses it prints — those are the only thing the firewall needs,
and they never change (re-running `enable.py` returns the same ones).

**2. Allow the relay in the RDS security group (once, ever)**

Use the `sg_rule` from step 1, with the group attached to the RDS instance and
the DB port. Both an IPv4 and an IPv6 entry are printed; RDS endpoints normally
resolve to IPv4, so **the IPv4 entry is the one that matters** — `verify.py`
tells you which family the DB will actually see. `sc-static-egress` needs the
endpoint to be publicly reachable: a VPC-private RDS has no route from here.

**3. Prove it before touching the application**

```bash
python3 skills/static-egress/scripts/verify.py \
    --target db-prod.abc123.us-east-1.rds.amazonaws.com:5432
```

Expect `egress matches: yes` and `tcp handshake: ok`. If the handshake fails,
the security-group entry is missing or the endpoint is private — fix that now,
not after changing the app.

**4. Start the forwarder and point the client at it**

Database drivers do not speak SOCKS5, so run the bundled forwarder:

```bash
# once per container — put this line in the workspace startup script so it
# survives agent recreation
python3 skills/static-egress/scripts/tunnel.py \
    --target db-prod.abc123.us-east-1.rds.amazonaws.com:5432 \
    --listen 127.0.0.1:5432 &
```

Then connect with **both** names, so `sslmode=verify-full` still passes:

| setting | value | why |
|---|---|---|
| `host` | the real RDS endpoint | SNI + certificate hostname check |
| `hostaddr` | `127.0.0.1` | the actual socket — the local forwarder |
| `port` | `5432` | |
| `sslmode` | `verify-full` | end-to-end TLS; the relay only carries ciphertext |

```bash
# psql
psql "host=db-prod.abc123.us-east-1.rds.amazonaws.com hostaddr=127.0.0.1 \
      port=5432 dbname=app user=app sslmode=verify-full" \
     -c 'select inet_client_addr();'
```

`inet_client_addr()` is the DB-side confirmation: it must print the allowlisted
address. That is the same fact `verify.py` proves from the agent side.

```python
# psycopg 3 — identical settings
import psycopg
conn = psycopg.connect(
    host="db-prod.abc123.us-east-1.rds.amazonaws.com",
    hostaddr="127.0.0.1", port=5432, dbname="app", user="app",
    sslmode="verify-full",
)
```

- `asyncpg` has no `hostaddr`, so it cannot both dial `127.0.0.1` and verify the
  real name. Use `sslmode="require"` (encrypted, name unchecked) or put the
  tunnel behind a name the certificate actually covers.
- The forwarder is **transparent**: keep the real hostname in the protocol — TLS
  SNI, HTTP `Host`. Requesting `http://127.0.0.1:18080/` sends
  `Host: 127.0.0.1:18080`, and a CDN in front of the real host answers 403
  (Cloudflare 1003) for the unknown name.
- `tunnel.py` refreshes its credential itself; nothing is written to disk.

**5. Checklist**

- [ ] `enable.py` printed an allowlist
- [ ] those addresses are in the RDS security group, and the endpoint is
      publicly reachable
- [ ] `verify.py`: `egress matches: yes`, `tcp handshake: ok`
- [ ] `tunnel.py` is running (and wired into the startup script)
- [ ] the app connects with `host` + `hostaddr`
- [ ] `select inet_client_addr();` returns the allowlisted address

**Related:** if the DB supports IAM database authentication, that replaces the
*password* — it does **not** replace the security group, so this recipe still
applies. For a VPC-private endpoint, ask the platform team for an AWS-side
relay/tunnel instead.

## The one-time firewall change

`enable.py` prints an `sg_rule` ready to paste:

```
aws ec2 authorize-security-group-ingress --group-id <sg-id> \
  --ip-permissions IpProtocol=tcp,FromPort=0,ToPort=65535,IpRanges=[{CidrIp=<v4>/32}] \
                   IpProtocol=tcp,FromPort=0,ToPort=65535,Ipv6Ranges=[{CidrIpv6=<v6>/128}]
```

Add the IPv4 address; add the IPv6 one too if the target actually serves AAAA
records (a client that prefers IPv6 fails if only the IPv4 is allowlisted).
`verify.py` reports which family the target sees, so you can tell whether the
IPv6 entry is doing anything.

## What `verify.py` proves

| Field | Meaning |
|---|---|
| `egress_ip_seen` | the address the internet actually sees coming from the relay |
| `egress_ip_allocated` | the addresses you should have allowlisted |
| `egress_matches_allowlist` | the two agree — if this is `no`, do not tell the user it works |
| `target_reachable` | a real TCP handshake to the target from the relay |

## Key facts, rules and boundaries

- **The credential is the lock.** A relay port carries no identity; every
  connection is authenticated with a short-lived token bound to **you**, your
  **container**, and the **exact target list**. Tokens are refused if expired,
  revoked, replayed with another username, or pointed at a target outside the
  ACL.
- **Never** put the token or the allocation's addresses in logs, prompts, or
  shared files.
- This is **container-level**: everything you send through the tunnel uses the
  fixed IP; it is not a per-request switch.
- **Targets must be external.** Loopback, link-local, private ranges and
  `.internal` names are refused when you enable (and re-checked by the relay
  before it dials), so this is not a way into the platform's private network.
  Pass `--region` only with a region the deployment allows; omitting it uses the
  default.
- Do not set a global `HTTP_PROXY`/`HTTPS_PROXY` — it breaks the platform's
  paid-API routing (`sc-proxy`).

## Dependencies

None. Everything is Python 3 standard library; the only external requirement is
the platform's `CONTAINER_JWT`, which the container injects. `exports.py` imports
nothing beyond stdlib either.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `unreachable` | service not reachable (outside the platform network) | run inside the Starchild container |
| `no_identity` | `CONTAINER_JWT` not set | only usable in the platform container |
| `egress_matches_allowlist: no` | firewall entry missing, or the target address is not the one allowlisted | add the `allowlist` addresses, then `verify.py` again |
| `tcp handshake: FAILED` | firewall not updated, wrong port, or the target is VPC-private | confirm the allowlist; if the endpoint is private, an AWS-side relay is required |
| certificate hostname mismatch | client connects to `127.0.0.1` with `verify-full` | use `host=<real host>` **and** `hostaddr=127.0.0.1` |
| `no active allocation` | not enabled, or already disabled | `enable.py` |
| `target_refused` | the target is loopback / private / link-local / `.internal` | point at the real external endpoint; the relay is not a route into the private network |
| `region 'xx' is not allowed` | that region is not enabled for this deployment | omit `--region` to use the default |
| `payload_too_large` | request body over the cap (64 KB) | the API takes a handful of targets — this is not a bulk interface |
| relay rejects credentials | credential expired/revoked | `enable.py` (renews) or restart `tunnel.py` |

## Files

```
static-egress/
├── SKILL.md
├── exports.py      # in-process surface (read-only + end-to-end)
├── logo.png
└── scripts/
    ├── api.py      # the functions exports.py re-exports
    ├── enable.py     # open/renew the allocation, print the allowlist + sg rule
    ├── status.py     # show allocation (credential redacted)
    ├── verify.py     # prove exit IP + TCP reachability
    ├── selftest.py   # prove the mechanism without a database
    ├── disable.py    # revoke credential (release the IP only in per-user-app mode)
    └── tunnel.py     # local TCP -> SOCKS5 forwarder for non-SOCKS clients
```