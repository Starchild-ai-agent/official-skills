"""
byo-proxy — public API for other skills to consume residential proxies.

Two patterns of use:
    A. get_proxy_url(provider, country, ...)        — explicit one-off
    B. get_proxy_for_skill(skill_name)              — opt-in long-term binding

Both raise ProxyNotConfiguredError on misconfiguration. Never silent fallback:
a residential-proxy user is debugging a geo problem, and a silent passthrough
would mask exactly the symptom they care about.

Storage:
    Credentials  -> /data/workspace/.env             (shared with other skills)
    Bindings     -> /data/workspace/.byo-proxy.json  (this skill only)
"""
import json
import os
import time
import urllib.request
import urllib.error
from typing import Optional

ENV_FILE = "/data/workspace/.env"
BINDINGS_FILE = "/data/workspace/.byo-proxy.json"
SKILL_DIR = "/data/workspace/skills/byo-proxy"  # canonical runtime path used in error messages

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
}


class ProxyNotConfiguredError(RuntimeError):
    """Raised when a proxy URL is requested but cannot be built. Message
    always includes the exact remediation command for the user to run."""


# ── onboarding guidance (used by error messages and exposed publicly) ───────

def onboarding_guide(skill_name: str, provider: str = "iproyal",
                     country: str = "<cc>") -> str:
    """Return a multi-line, agent-readable guide for getting `skill_name`
    set up with `provider`. Used as the body of ProxyNotConfiguredError when
    a binding is missing, and exposed so calling skills/agents can fetch the
    same text on demand (e.g. to render their own onboarding UI).
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider {provider!r}")
    cfg = PROVIDERS[provider]
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
        f"Country reference: {SKILL_DIR}/references/{provider}.md"
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


# ── bindings IO ─────────────────────────────────────────────────────────────

def _load_bindings() -> dict:
    try:
        with open(BINDINGS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_bindings(data: dict) -> None:
    os.makedirs(os.path.dirname(BINDINGS_FILE), exist_ok=True)
    with open(BINDINGS_FILE, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


# ── provider URL builders ───────────────────────────────────────────────────

def _build_iproyal_url(country: str, sticky_minutes: Optional[int],
                       session: Optional[str]) -> str:
    """IPRoyal uses password-field params separated by `_`.
    Format (current): username:password_country-XX[_session-NAME_lifetime-Nm]@host:port
    Older format put params in the username field — that now returns 407.
    """
    user = _cred("IPROYAL_USERNAME")
    pwd = _cred("IPROYAL_PASSWORD")
    if not user or not pwd:
        raise ProxyNotConfiguredError(_creds_missing_message("iproyal"))

    parts = [f"country-{country}"]
    if session:
        parts.append(f"session-{session}")
    if sticky_minutes:
        if not 1 <= sticky_minutes <= 1440:
            raise ValueError("sticky_minutes must be between 1 and 1440 (IPRoyal limit)")
        parts.append(f"lifetime-{sticky_minutes}m")
    pwd_field = pwd + "_" + "_".join(parts)
    cfg = PROVIDERS["iproyal"]
    return f"http://{user}:{pwd_field}@{cfg['host']}:{cfg['port']}"


_BUILDERS = {"iproyal": _build_iproyal_url}


# ── public API ──────────────────────────────────────────────────────────────

def get_proxy_url(provider: str, country: str,
                  sticky_minutes: Optional[int] = None,
                  session: Optional[str] = None) -> str:
    """Build a proxy URL for the given provider + country.

    Raises ProxyNotConfiguredError if credentials are missing.
    Raises ValueError if provider or country is unsupported.
    """
    if provider not in PROVIDERS:
        raise ValueError(
            f"Unknown provider {provider!r}. Supported: {list(PROVIDERS)}"
        )
    country = country.lower()
    if country not in PROVIDERS[provider]["countries"]:
        raise ValueError(
            f"Unknown country code {country!r} for provider {provider!r}. "
            f"See references/{provider}.md for the supported list."
        )
    return _BUILDERS[provider](country, sticky_minutes, session)


def get_proxy_for_skill(skill_name: str) -> str:
    """Return the proxy URL the user has bound to the given skill.

    Caller passes its own skill name (no auto-detection — explicit is safer).
    Raises ProxyNotConfiguredError with a multi-line onboarding guide if the
    skill is unbound, or if the bound provider is missing credentials.
    """
    bindings = _load_bindings()
    entry = bindings.get(skill_name) if bindings else None
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
    out = []
    for name, cfg in PROVIDERS.items():
        configured = bool(_cred(cfg["env_user"]) and _cred(cfg["env_pass"]))
        bound = sorted(
            f"{skill}→{b['country']}"
            for skill, b in bindings.items()
            if b.get("provider") == name
        )
        out.append({
            "provider": name,
            "configured": configured,
            "endpoint": f"{cfg['host']}:{cfg['port']}",
            "supported_country_count": len(cfg["countries"]),
            "bound_skills": bound,
        })
    return out


def set_binding(skill_name: str, provider: str, country: str,
                sticky_minutes: Optional[int] = None,
                session: Optional[str] = None) -> None:
    """Persist a skill→provider/country binding. Validates inputs eagerly so
    bad bindings never end up in the file."""
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider {provider!r}")
    country = country.lower()
    if country not in PROVIDERS[provider]["countries"]:
        raise ValueError(f"Unknown country code {country!r} for {provider!r}")
    if sticky_minutes is not None and not 1 <= sticky_minutes <= 1440:
        raise ValueError("sticky_minutes must be 1..1440")

    bindings = _load_bindings()
    bindings[skill_name] = {
        "provider": provider,
        "country": country,
    }
    if sticky_minutes is not None:
        bindings[skill_name]["sticky_minutes"] = sticky_minutes
    if session is not None:
        bindings[skill_name]["session"] = session
    _save_bindings(bindings)


def unset_binding(skill_name: str) -> None:
    bindings = _load_bindings()
    if skill_name in bindings:
        del bindings[skill_name]
        _save_bindings(bindings)


def save_credentials(provider: str, **kwargs) -> None:
    """Persist provider credentials to /data/workspace/.env.

    Example: save_credentials('iproyal', username='u', password='p')
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider {provider!r}")
    cfg = PROVIDERS[provider]
    if provider == "iproyal":
        if "username" not in kwargs or "password" not in kwargs:
            raise ValueError("iproyal requires username= and password=")
        _save_env_var(cfg["env_user"], kwargs["username"])
        _save_env_var(cfg["env_pass"], kwargs["password"])
    else:  # pragma: no cover — placeholder for future providers
        raise NotImplementedError(provider)


def test_proxy(provider: str, country: str, timeout: int = 15) -> dict:
    """Issue a single request to ifconfig.co/json through the proxy and
    return {ok, exit_ip, geo_country, latency_ms}. Network errors return
    ok=false with an error field; misconfiguration still raises."""
    proxy = get_proxy_url(provider=provider, country=country)
    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
    opener = urllib.request.build_opener(handler)
    req = urllib.request.Request(
        "https://ifconfig.co/json",
        headers={"User-Agent": "byo-proxy/0.1 test"},
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
