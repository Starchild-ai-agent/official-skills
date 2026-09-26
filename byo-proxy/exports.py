"""
byo-proxy — public API for other skills to consume residential / static proxies.

Two patterns of use:
    A. get_proxy_url(provider, country=..., proxy_id=..., ...)   — explicit one-off
    B. get_proxy_for_skill(skill_name)                           — opt-in long-term binding

Two provider kinds:
    "gateway" (iproyal)      one host:port; country/session/lifetime live in the
                             password field. Rotating by default, sticky per session.
    "isp"     (iproyal-isp)  one *dedicated* static IP per purchased proxy; each
                             has its own host:port + username:password. IP never
                             rotates. Registered per proxy via add_isp_proxy().

Both patterns raise ProxyNotConfiguredError on misconfiguration. Never silent
fallback: a proxy user is debugging a geo/identity problem, and a silent
passthrough would mask exactly the symptom they care about.

Storage:
    Account credentials (gateway providers) -> /data/workspace/.env
    Bindings + ISP proxy inventory          -> /data/workspace/.byo-proxy.json
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

ENV_FILE = "/data/workspace/.env"
BINDINGS_FILE = "/data/workspace/.byo-proxy.json"
SKILL_DIR = "/data/workspace/skills/byo-proxy"  # canonical runtime path used in error messages

# Sticky-session lifetime bounds. IPRoyal's residential pool accepts 1 minute up
# to 7 days (source: https://docs.iproyal.com/proxies/residential/proxy/rotation).
MIN_STICKY_MINUTES = 1
MAX_STICKY_MINUTES = 7 * 24 * 60  # 10080

# IPRoyal supported ISO-3166-1 alpha-2 country codes (lowercase).
# Source: https://dashboard.iproyal.com/ — residential pool covers 195+ countries;
# this is the curated subset we expose. Add more codes here as users request them.
IPROYAL_COUNTRIES = {
    "us", "ca", "mx", "br", "ar", "cl", "co", "pe",
    "gb", "de", "fr", "nl", "es", "it", "se", "no", "fi", "dk", "ch", "at", "be", "pl", "ie", "pt", "cz", "ro",
    "ru", "ua", "tr",
    "jp", "kr", "sg", "hk", "tw", "th", "vn", "id", "my", "ph", "in", "pk",
    "au", "nz",
    "za", "eg", "ng", "ke",
    "ae", "sa", "il",
}

PROVIDERS = {
    "iproyal": {
        "kind": "gateway",
        "host": "geo.iproyal.com",
        "port": 12321,
        "env_user": "IPROYAL_USERNAME",
        "env_pass": "IPROYAL_PASSWORD",
        "countries": IPROYAL_COUNTRIES,
        "signup_url": "https://iproyal.com/residential-proxies/",
        "dashboard_url": "https://dashboard.iproyal.com/",
        "credential_hint": "IPRoyal dashboard → Residential → Access  (NOT your account login)",
        "pricing_note": "Pay-as-you-go from $1.75/GB, no monthly minimum",
    },
    "iproyal-isp": {
        "kind": "isp",
        "signup_url": "https://iproyal.com/isp-proxies/",
        "dashboard_url": "https://dashboard.iproyal.com/",
        "credential_hint": (
            "IPRoyal dashboard → ISP → your purchased proxies "
            "(each IP has its own host:port and username:password)"
        ),
        "pricing_note": (
            "Dedicated static IPs from $2.00/IP "
            "(24h $1.80, 30d $2.70, 60d $2.55, 90d $2.40), unlimited traffic"
        ),
        "docs_url": "https://docs.iproyal.com/proxies/isp",
    },
}

_PROXY_ID_RE = re.compile(r"[A-Za-z0-9._-]+")


class ProxyNotConfiguredError(RuntimeError):
    """Raised when a proxy URL is requested but cannot be built. Message
    always includes the exact remediation command for the user to run."""


def _provider(provider: str) -> dict:
    cfg = PROVIDERS.get(provider)
    if cfg is None:
        raise ValueError(
            f"Unknown provider {provider!r}. Supported: {list(PROVIDERS)}"
        )
    return cfg


# ── onboarding guidance (used by error messages and exposed publicly) ───────

def onboarding_guide(skill_name: str, provider: str = "iproyal",
                     country: str = "<cc>", proxy_id: str = None) -> str:
    """Return a multi-line, agent-readable guide for getting `skill_name`
    set up with `provider`. Used as the body of ProxyNotConfiguredError when
    a binding is missing, and exposed so calling skills/agents can fetch the
    same text on demand (e.g. to render their own onboarding UI).
    """
    cfg = _provider(provider)

    if cfg["kind"] == "isp":
        pid = proxy_id or "<proxy-id>"
        return (
            f"Skill {skill_name!r} has no proxy binding for provider {provider!r}.\n"
            f"\n"
            f"{provider!r} rents dedicated static IPs, one at a time, so setup is two steps:\n"
            f"  1. Buy an ISP proxy at {cfg['signup_url']}\n"
            f"     ({cfg['pricing_note']})\n"
            f"     Copy its host:port and username:password from: {cfg['credential_hint']}\n"
            f"  2. Register it, then bind {skill_name!r} to that IP:\n"
            f"     python3 {SKILL_DIR}/scripts/add_isp_proxy.py {pid} \\\n"
            f"         --host <host> --port <port> --username <user> --password <pass>\n"
            f"     python3 {SKILL_DIR}/scripts/bind_skill.py {skill_name} "
            f"--provider {provider} --proxy-id {pid}\n"
            f"\n"
            f"One-shot alternative (prompts for the proxy details):\n"
            f"  python3 {SKILL_DIR}/scripts/onboard.py {skill_name} --provider {provider}\n"
            f"Docs: {cfg['docs_url']}"
        )

    placeholder = country == "<cc>"
    tail = (
        f"\nReplace {country!r} with an ISO-3166-1 alpha-2 code (e.g. us, jp, de, gb)."
        if placeholder else ""
    )
    return (
        f"Skill {skill_name!r} has no proxy binding for provider {provider!r}.\n"
        f"\n"
        f"One-step onboarding:\n"
        f"  python3 {SKILL_DIR}/scripts/onboard.py {skill_name} --provider {provider} --country {country}\n"
        f"\n"
        f"What it will walk you through:\n"
        f"  1. Sign up at {cfg['signup_url']}  ({cfg['pricing_note']})\n"
        f"  2. Copy proxy username + password from {cfg['credential_hint']}\n"
        f"  3. Save them to {ENV_FILE}\n"
        f"  4. Bind {skill_name!r} to {provider}/{country}\n"
        f"  5. Verify the exit IP via ifconfig.co"
        f"{tail}\n"
        f"Country reference: {SKILL_DIR}/references/{provider}.md\n"
        f"\n"
        f"Need a permanent, dedicated IP instead? Buy an IPRoyal ISP proxy\n"
        f"({PROVIDERS['iproyal-isp']['pricing_note']}) and bind it:\n"
        f"  python3 {SKILL_DIR}/scripts/onboard.py {skill_name} --provider iproyal-isp"
    )


def _creds_missing_message(provider: str, skill_name: str = None) -> str:
    cfg = PROVIDERS[provider]
    who = f"Skill {skill_name!r} is bound to {provider!r} but " if skill_name else ""
    article = "an" if provider[0] in "aeiou" else "a"
    return (
        f"{who}{cfg['env_user']} / {cfg['env_pass']} not found in {ENV_FILE}.\n"
        f"\n"
        f"Finish the {provider} setup:\n"
        f"  python3 {SKILL_DIR}/scripts/setup_provider.py {provider}\n"
        f"\n"
        f"Don't have {article} {provider} account yet? Sign up first: {cfg['signup_url']}\n"
        f"  ({cfg['pricing_note']})\n"
        f"  Get proxy credentials from: {cfg['credential_hint']}"
    )


def _isp_proxy_missing_message(proxy_id: str, skill_name: str = None) -> str:
    who = f"Skill {skill_name!r} is bound to ISP proxy " if skill_name else "ISP proxy "
    return (
        f"{who}{proxy_id!r}, but it is not registered in {BINDINGS_FILE}.\n"
        f"\n"
        f"Register the proxy (host/port/username/password from your IPRoyal ISP order):\n"
        f"  python3 {SKILL_DIR}/scripts/add_isp_proxy.py {proxy_id} \\\n"
        f"      --host <host> --port <port> --username <user> --password <pass>\n"
        f"\n"
        f"List registered proxies: python3 {SKILL_DIR}/scripts/add_isp_proxy.py --list\n"
        f"Don't have an ISP proxy yet? Buy one: {PROVIDERS['iproyal-isp']['signup_url']}"
    )


# ── env file IO (polymarket-compatible: same file, same format) ─────────────

def _load_env() -> dict:
    env = {}
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env


def _save_env_var(key: str, value: str) -> None:
    lines = []
    try:
        with open(ENV_FILE) as f:
            lines = f.readlines()
    except FileNotFoundError:
        pass
    new_lines, found = [], False
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}\n")
    os.makedirs(os.path.dirname(ENV_FILE), exist_ok=True)
    with open(ENV_FILE, "w") as f:
        f.writelines(new_lines)
    os.environ[key] = value


def _cred(key: str) -> str:
    return os.environ.get(key) or _load_env().get(key, "")


# ── store IO (bindings + ISP inventory) ─────────────────────────────────────

def _load_store() -> dict:
    """Return {"bindings": {...}, "isp_proxies": {...}}.

    Transparently migrates the legacy shape, where the file *was* the bindings
    map (skill name at the top level). Old files are read as bindings-only and
    rewritten in the new shape on the next save.
    """
    raw = {}
    try:
        with open(BINDINGS_FILE) as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    if "bindings" in raw or "isp_proxies" in raw:
        return {
            "bindings": raw.get("bindings") or {},
            "isp_proxies": raw.get("isp_proxies") or {},
        }
    return {"bindings": raw, "isp_proxies": {}}


def _save_store(store: dict) -> None:
    os.makedirs(os.path.dirname(BINDINGS_FILE), exist_ok=True)
    with open(BINDINGS_FILE, "w") as f:
        json.dump(store, f, indent=2, sort_keys=True)
        f.write("\n")


def _load_bindings() -> dict:
    return _load_store()["bindings"]


def _load_isp_proxies() -> dict:
    return _load_store()["isp_proxies"]


# ── provider URL builders ───────────────────────────────────────────────────

def _validate_sticky(sticky_minutes: int) -> None:
    if not isinstance(sticky_minutes, int) or isinstance(sticky_minutes, bool):
        raise ValueError("sticky_minutes must be an integer")
    if not MIN_STICKY_MINUTES <= sticky_minutes <= MAX_STICKY_MINUTES:
        raise ValueError(
            f"sticky_minutes must be between {MIN_STICKY_MINUTES} and "
            f"{MAX_STICKY_MINUTES} (7 days, IPRoyal's ceiling)"
        )


def _build_gateway_url(provider: str, country: str, sticky_minutes: Optional[int],
                       session: Optional[str]) -> str:
    """IPRoyal residential gateway: params live in the *password* field,
    separated by `_`.

    Format: username:password_country-XX[_session-NAME][_lifetime-Nm]@host:port

    Notes:
      * Older format put params in the username field — that now returns 407.
      * `lifetime-` is only meaningful alongside `session-` (IPRoyal ties a
        lifetime to a named session), so requesting sticky without a session
        is rejected rather than silently emitting a URL the provider refuses.
    """
    cfg = PROVIDERS[provider]
    user = _cred(cfg["env_user"])
    pwd = _cred(cfg["env_pass"])
    if not user or not pwd:
        raise ProxyNotConfiguredError(_creds_missing_message(provider))

    if sticky_minutes is not None and not session:
        raise ValueError(
            "sticky_minutes requires a session id: IPRoyal's lifetime- parameter "
            "only applies to a session- (e.g. session='myid', sticky_minutes=60)."
        )

    parts = [f"country-{country}"]
    if session:
        parts.append(f"session-{session}")
    if sticky_minutes is not None:
        _validate_sticky(sticky_minutes)
        parts.append(f"lifetime-{sticky_minutes}m")
    pwd_field = pwd + "_" + "_".join(parts)
    return f"http://{user}:{pwd_field}@{cfg['host']}:{cfg['port']}"


def _build_isp_url(proxy_id: str) -> str:
    """Static ISP proxy: dedicated host:port with its own username:password.
    No country/session params — the purchased IP *is* the selection."""
    proxies = _load_isp_proxies()
    entry = proxies.get(proxy_id)
    if entry is None:
        raise ProxyNotConfiguredError(_isp_proxy_missing_message(proxy_id))
    user = urllib.parse.quote(entry["username"], safe="")
    pwd = urllib.parse.quote(entry["password"], safe="")
    return f"http://{user}:{pwd}@{entry['host']}:{entry['port']}"


# ── public API ──────────────────────────────────────────────────────────────

def get_proxy_url(provider: str, country: str = None,
                  sticky_minutes: Optional[int] = None,
                  session: Optional[str] = None,
                  proxy_id: str = None) -> str:
    """Build a proxy URL for the given provider.

    Gateway providers (iproyal) need `country`; optional `session` +
    `sticky_minutes` pin a session (sticky requires session).
    ISP providers (iproyal-isp) need `proxy_id` — the registered static IP.

    Raises ProxyNotConfiguredError if credentials/proxy are missing.
    Raises ValueError if provider/country is unsupported or a parameter is
    invalid.
    """
    cfg = _provider(provider)

    if cfg["kind"] == "isp":
        if not proxy_id:
            raise ValueError(f"provider {provider!r} requires proxy_id=...")
        return _build_isp_url(proxy_id)

    if not country:
        raise ValueError(f"provider {provider!r} requires country=...")
    country = country.lower()
    if country not in cfg["countries"]:
        raise ValueError(
            f"Unknown country code {country!r} for provider {provider!r}. "
            f"See references/{provider}.md for the supported list."
        )
    return _build_gateway_url(provider, country, sticky_minutes, session)


def get_proxy_for_skill(skill_name: str) -> str:
    """Return the proxy URL the user has bound to the given skill.

    Caller passes its own skill name (no auto-detection — explicit is safer).
    Raises ProxyNotConfiguredError with a multi-line onboarding guide if the
    skill is unbound, the bound provider is gone, or the underlying credentials
    or ISP proxy are missing.
    """
    entry = _load_bindings().get(skill_name)
    if not entry:
        # No binding: emit the full onboarding flow.
        raise ProxyNotConfiguredError(onboarding_guide(skill_name, provider="iproyal"))

    provider = entry["provider"]
    cfg = PROVIDERS.get(provider)
    if cfg is None:
        # Binding references a provider we no longer support.
        raise ProxyNotConfiguredError(
            f"Skill {skill_name!r} is bound to unknown provider {provider!r}.\n"
            f"Rebind: python3 {SKILL_DIR}/scripts/bind_skill.py {skill_name} "
            f"--provider iproyal --country <cc>\n"
            f"Or unbind: python3 {SKILL_DIR}/scripts/bind_skill.py {skill_name} --unset"
        )

    if cfg["kind"] == "isp":
        proxy_id = entry.get("proxy_id")
        if not proxy_id:
            raise ProxyNotConfiguredError(
                f"Skill {skill_name!r} is bound to {provider!r} without a proxy_id.\n"
                f"Rebind: python3 {SKILL_DIR}/scripts/bind_skill.py {skill_name} "
                f"--provider {provider} --proxy-id <id>"
            )
        if proxy_id not in _load_isp_proxies():
            raise ProxyNotConfiguredError(
                _isp_proxy_missing_message(proxy_id, skill_name=skill_name)
            )
        return _build_isp_url(proxy_id)

    if not (_cred(cfg["env_user"]) and _cred(cfg["env_pass"])):
        # Binding exists but credentials were never saved (or were removed).
        raise ProxyNotConfiguredError(_creds_missing_message(provider, skill_name=skill_name))

    return get_proxy_url(
        provider=provider,
        country=entry["country"],
        sticky_minutes=entry.get("sticky_minutes"),
        session=entry.get("session"),
    )


def list_providers() -> list:
    """Snapshot of every known provider, whether it's configured, and which
    skills are bound to it. Safe to call without any setup."""
    bindings = _load_bindings()
    proxies = _load_isp_proxies()
    out = []
    for name, cfg in PROVIDERS.items():
        if cfg["kind"] == "isp":
            bound = sorted(
                f"{skill}→{b.get('proxy_id')}"
                for skill, b in bindings.items()
                if b.get("provider") == name
            )
            out.append({
                "provider": name,
                "kind": "isp",
                "configured": bool(proxies),
                "proxy_count": len(proxies),
                "bound_skills": bound,
            })
        else:
            configured = bool(_cred(cfg["env_user"]) and _cred(cfg["env_pass"]))
            bound = sorted(
                f"{skill}→{b.get('country')}"
                for skill, b in bindings.items()
                if b.get("provider") == name
            )
            out.append({
                "provider": name,
                "kind": "gateway",
                "configured": configured,
                "endpoint": f"{cfg['host']}:{cfg['port']}",
                "supported_country_count": len(cfg["countries"]),
                "bound_skills": bound,
            })
    return out


def set_binding(skill_name: str, provider: str, country: str = None,
                sticky_minutes: Optional[int] = None,
                session: Optional[str] = None,
                proxy_id: str = None) -> None:
    """Persist a skill→provider binding. Validates inputs eagerly so bad
    bindings never end up in the file.

    Gateway providers take country (+ optional session/sticky_minutes).
    ISP providers take proxy_id (session/sticky_minutes do not apply).
    """
    cfg = _provider(provider)

    entry = {"provider": provider}

    if cfg["kind"] == "isp":
        if not proxy_id:
            raise ValueError(f"provider {provider!r} requires proxy_id=...")
        if sticky_minutes is not None or session is not None:
            raise ValueError(
                f"provider {provider!r} serves one dedicated IP per proxy; "
                f"session/sticky_minutes do not apply"
            )
        if proxy_id not in _load_isp_proxies():
            raise ValueError(
                f"ISP proxy {proxy_id!r} is not registered. "
                f"Run: python3 {SKILL_DIR}/scripts/add_isp_proxy.py {proxy_id}"
            )
        entry["proxy_id"] = proxy_id
    else:
        if not country:
            raise ValueError(f"provider {provider!r} requires country=...")
        country = country.lower()
        if country not in cfg["countries"]:
            raise ValueError(f"Unknown country code {country!r} for {provider!r}")
        if sticky_minutes is not None:
            _validate_sticky(sticky_minutes)
            if not session:
                raise ValueError(
                    "sticky_minutes requires session: IPRoyal's lifetime- only "
                    "applies to a named session-"
                )
        entry["country"] = country
        if sticky_minutes is not None:
            entry["sticky_minutes"] = sticky_minutes
        if session is not None:
            entry["session"] = session

    store = _load_store()
    store["bindings"][skill_name] = entry
    _save_store(store)


def unset_binding(skill_name: str) -> None:
    store = _load_store()
    if skill_name in store["bindings"]:
        del store["bindings"][skill_name]
        _save_store(store)


def add_isp_proxy(proxy_id: str, host: str, port: int, username: str,
                  password: str, socks_port: Optional[int] = None,
                  label: str = None) -> None:
    """Register a dedicated IPRoyal ISP proxy so it can be bound to a skill.

    Example:
        add_isp_proxy("jp-1", host="191.116.125.248", port=12323,
                      username="aea1bcf5cb3", password="e8c6a622fe",
                      socks_port=12324, label="Tokyo ISP")
    """
    _validate_proxy_id(proxy_id)
    if not host or not str(host).strip():
        raise ValueError("host is required")
    port = _validate_port(port, "port")
    if socks_port is not None:
        socks_port = _validate_port(socks_port, "socks_port")
    if not username or not password:
        raise ValueError("username and password are required")

    record = {
        "host": str(host).strip(),
        "port": port,
        "username": username,
        "password": password,
    }
    if socks_port is not None:
        record["socks_port"] = socks_port
    if label:
        record["label"] = label

    store = _load_store()
    store["isp_proxies"][proxy_id] = record
    _save_store(store)


def remove_isp_proxy(proxy_id: str, force: bool = False) -> list:
    """Remove a registered ISP proxy. Refuses if skills are still bound to it
    unless `force=True`; returns the list of skills that were bound."""
    store = _load_store()
    if proxy_id not in store["isp_proxies"]:
        return []
    bound = sorted(
        skill for skill, b in store["bindings"].items()
        if b.get("provider") == "iproyal-isp" and b.get("proxy_id") == proxy_id
    )
    if bound and not force:
        raise ValueError(
            f"ISP proxy {proxy_id!r} is still bound to: {', '.join(bound)}. "
            f"Unbind them first, or pass force=True to remove anyway."
        )
    del store["isp_proxies"][proxy_id]
    _save_store(store)
    return bound


def list_isp_proxies() -> list:
    """Registered ISP proxies (credentials redacted) plus which skills use them."""
    bindings = _load_bindings()
    out = []
    for proxy_id, p in sorted(_load_isp_proxies().items()):
        bound = sorted(
            skill for skill, b in bindings.items()
            if b.get("provider") == "iproyal-isp" and b.get("proxy_id") == proxy_id
        )
        out.append({
            "proxy_id": proxy_id,
            "endpoint": f"{p['host']}:{p['port']}",
            "socks_endpoint": f"{p['host']}:{p['socks_port']}" if p.get("socks_port") else None,
            "label": p.get("label"),
            "bound_skills": bound,
        })
    return out


def _validate_proxy_id(proxy_id: str) -> None:
    if not proxy_id or not _PROXY_ID_RE.fullmatch(proxy_id):
        raise ValueError(
            "proxy_id must be a short non-empty identifier using letters, digits, "
            "dot, underscore or dash (e.g. jp-1)"
        )


def _validate_port(port, name: str) -> int:
    if isinstance(port, bool) or not isinstance(port, int):
        try:
            port = int(port)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be an integer port")
    if not 1 <= port <= 65535:
        raise ValueError(f"{name} must be between 1 and 65535")
    return port


def save_credentials(provider: str, **kwargs) -> None:
    """Persist gateway-provider credentials to /data/workspace/.env.

    Example: save_credentials('iproyal', username='u', password='p')

    ISP providers have per-IP credentials; use add_isp_proxy() instead.
    """
    cfg = _provider(provider)
    if cfg["kind"] == "isp":
        raise ValueError(
            f"provider {provider!r} has per-proxy credentials; "
            f"use add_isp_proxy(proxy_id, host, port, username, password) instead"
        )
    if "username" not in kwargs or "password" not in kwargs:
        raise ValueError(f"{provider} requires username= and password=")
    _save_env_var(cfg["env_user"], kwargs["username"])
    _save_env_var(cfg["env_pass"], kwargs["password"])


def test_proxy(provider: str, country: str = None, proxy_id: str = None,
               timeout: int = 15) -> dict:
    """Issue a single request to ifconfig.co/json through the proxy and
    return {ok, exit_ip, geo_country, latency_ms}. Network errors return
    ok=false with an error field; misconfiguration still raises."""
    proxy = get_proxy_url(provider=provider, country=country, proxy_id=proxy_id)
    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
    opener = urllib.request.build_opener(handler)
    req = urllib.request.Request(
        "https://ifconfig.co/json",
        headers={"User-Agent": "byo-proxy/0.2 test"},
    )
    started = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
        return {
            "ok": True,
            "exit_ip": payload.get("ip"),
            "geo_country": (payload.get("country_iso") or "").lower(),
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        return {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "latency_ms": int((time.monotonic() - started) * 1000),
        }