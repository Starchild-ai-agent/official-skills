"""Credential-aware hybrid router.

Resolution order, in one sentence: if the requested capability is already
supported by a bound credential, use that credential; otherwise return an
onboarding payload for the smallest auth path that unlocks it.

An account has exactly one ``auth_kind``. The router never fans one operation
out across two authorizations, and it never asks for a private session when an
official path can do the job.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, FrozenSet, List, Optional

from ig_composio import ComposioBackend
from ig_errors import AccountNotFound, CapabilityUnavailable, CredentialRequired
from ig_gateway import GatewayClient
from ig_graph import GraphClient
from ig_models import (
    AUTH_COMPOSIO,
    AUTH_GRAPH,
    AUTH_KINDS,
    AUTH_PRIVATE,
    COMPOSIO_CAPABILITIES,
    GRAPH_BASE_CAPABILITIES,
    GRAPH_MESSAGING_CAPABILITIES,
    PRIVATE_CAPABILITIES,
    Account,
    composio_capabilities,
    graph_capabilities,
    private_capabilities,
)
from ig_private import PrivateClient

CACHE_TTL_SECONDS = 30


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _auth_preference() -> List[str]:
    raw = os.environ.get("INSTAGRAM_PREFERRED_AUTH", "graph,composio,private")
    order = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return [item for item in order if item in AUTH_KINDS] or list(AUTH_KINDS)


def _capabilities_for_entry(entry: Dict[str, Any]) -> FrozenSet[str]:
    auth_kind = str(entry.get("auth_kind") or "").lower()
    if auth_kind == AUTH_GRAPH:
        return graph_capabilities(
            has_page_token=bool(entry.get("page_token")),
            hashtag_search=_env_bool(
                "INSTAGRAM_GRAPH_HASHTAG_SEARCH",
                bool(entry.get("hashtag_search", True)),
            ),
            business_discovery=_env_bool(
                "INSTAGRAM_GRAPH_BUSINESS_DISCOVERY",
                bool(entry.get("business_discovery", True)),
            ),
        )
    if auth_kind == AUTH_COMPOSIO:
        return composio_capabilities()
    if auth_kind == AUTH_PRIVATE:
        return private_capabilities(
            cold_dm=_env_bool(
                "INSTAGRAM_ALLOW_COLD_DM",
                bool(entry.get("cold_dm", False)),
            ),
            private_enabled=bool(entry.get("enabled", True)),
        )
    return frozenset()


def _entry_to_account(entry: Dict[str, Any], index: int) -> Optional[Account]:
    if not isinstance(entry, dict):
        return None
    auth_kind = str(entry.get("auth_kind") or "").lower()
    if auth_kind not in AUTH_KINDS:
        if entry.get("access_token"):
            auth_kind = AUTH_GRAPH
        elif entry.get("session_file") or entry.get("sessionid") or entry.get("username"):
            auth_kind = AUTH_PRIVATE
        else:
            return None

    label = str(entry.get("label") or entry.get("name") or f"{auth_kind}-{index + 1}")
    metadata = {
        key: value
        for key, value in entry.items()
        if key
        not in {
            "label",
            "name",
            "auth_kind",
            "ig_user_id",
            "page_id",
            "session_file",
            "enabled",
        }
    }
    enabled = bool(entry.get("enabled", True))
    if not enabled:
        return Account(
            label=label,
            auth_kind=auth_kind,
            capabilities=frozenset(),
            ig_user_id=entry.get("ig_user_id"),
            page_id=entry.get("page_id"),
            session_file=entry.get("session_file"),
            source="config",
            disabled=True,
            metadata={**metadata, "note": "disabled in account config"},
        )

    return Account(
        label=label,
        auth_kind=auth_kind,
        capabilities=_capabilities_for_entry(entry),
        ig_user_id=str(entry.get("ig_user_id") or "") or None,
        page_id=str(entry.get("page_id") or "") or None,
        session_file=entry.get("session_file"),
        source="config",
        metadata=metadata,
    )


def _env_accounts() -> List[Account]:
    entries: List[Dict[str, Any]] = []
    raw = os.environ.get("INSTAGRAM_ACCOUNTS_JSON")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and isinstance(parsed.get("accounts"), list):
                parsed = parsed["accounts"]
            if isinstance(parsed, dict):
                parsed = [parsed]
            if isinstance(parsed, list):
                entries = [e for e in parsed if isinstance(e, dict)]
        except json.JSONDecodeError:
            entries = []

    if not entries:
        graph_token = os.environ.get("INSTAGRAM_GRAPH_TOKEN") or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        if graph_token:
            entries.append(
                {
                    "label": os.environ.get("INSTAGRAM_ACCOUNT") or "default",
                    "auth_kind": AUTH_GRAPH,
                    "access_token": graph_token,
                    "page_token": os.environ.get("INSTAGRAM_GRAPH_PAGE_TOKEN"),
                    "ig_user_id": os.environ.get("INSTAGRAM_GRAPH_USER_ID"),
                    "page_id": os.environ.get("INSTAGRAM_GRAPH_PAGE_ID"),
                    "app_id": os.environ.get("INSTAGRAM_META_APP_ID"),
                    "app_secret": os.environ.get("INSTAGRAM_META_APP_SECRET"),
                    "login_type": os.environ.get("INSTAGRAM_LOGIN_TYPE", "facebook"),
                }
            )

        session_file = os.environ.get("INSTAGRAM_SESSION_FILE")
        sessionid = os.environ.get("INSTAGRAM_SESSIONID")
        username = os.environ.get("INSTAGRAM_USERNAME")
        password = os.environ.get("INSTAGRAM_PASSWORD")
        has_session = bool(session_file or sessionid)
        has_password = bool(username and password)
        private_default = has_session or has_password
        private_enabled = _env_bool("INSTAGRAM_ENABLE_PRIVATE", private_default)
        if private_enabled and (has_session or has_password):
            entries.append(
                {
                    "label": "private" if entries else (os.environ.get("INSTAGRAM_ACCOUNT") or "default"),
                    "auth_kind": AUTH_PRIVATE,
                    "username": username,
                    "password": password,
                    "sessionid": sessionid,
                    "session_file": session_file,
                    "totp_seed": os.environ.get("INSTAGRAM_TOTP_SEED"),
                    "proxy": os.environ.get("INSTAGRAM_PROXY"),
                    "cold_dm": _env_bool("INSTAGRAM_ALLOW_COLD_DM", False),
                }
            )

    accounts: List[Account] = []
    for index, entry in enumerate(entries):
        account = _entry_to_account(entry, index)
        if account:
            accounts.append(account)
    return accounts


def _composio_account() -> Optional[Account]:
    if not _env_bool("INSTAGRAM_COMPOSIO_ENABLED", True):
        return None
    try:
        gateway = GatewayClient()
        connection = gateway.active_connection("instagram")
    except Exception:
        return None
    if not connection:
        return None
    label = gateway.connected_account_label(connection)
    meta = connection.get("meta") if isinstance(connection.get("meta"), dict) else {}
    ig_user_id = (
        connection.get("ig_user_id")
        or meta.get("ig_user_id")
        or meta.get("instagram_user_id")
    )
    return Account(
        label=label,
        auth_kind=AUTH_COMPOSIO,
        capabilities=composio_capabilities(),
        ig_user_id=str(ig_user_id) if ig_user_id else None,
        source="composio",
        metadata={
            "connection_id": connection.get("id") or connection.get("connection_id"),
            "status": connection.get("status") or connection.get("state"),
            "username": meta.get("username") or connection.get("username"),
        },
    )


class Router:
    def __init__(self) -> None:
        self._accounts: List[Account] = []
        self._loaded_at = 0.0
        self._backends: Dict[str, Any] = {}

    def refresh(self) -> None:
        self._loaded_at = 0.0
        self._backends.clear()

    def accounts(self, *, include_composio: bool = True, refresh: bool = False) -> List[Account]:
        now = time.time()
        if refresh or not self._accounts or now - self._loaded_at > CACHE_TTL_SECONDS:
            accounts = _env_accounts()
            if include_composio:
                composio = _composio_account()
                if composio:
                    labels = {a.label for a in accounts}
                    if composio.label in labels:
                        composio.label = f"{composio.label}-composio"
                    accounts.append(composio)
            self._accounts = accounts
            self._loaded_at = now
        return self._accounts

    def get(self, account: Optional[str], *, include_composio: bool = True) -> Account:
        accounts = self.accounts(include_composio=include_composio)
        if not account:
            if not accounts:
                raise CredentialRequired(
                    "No Instagram credentials are bound.",
                    hint="Call instagram_connect() to start OAuth or bind a session.",
                )
            return accounts[0]
        for candidate in accounts:
            if candidate.label == account:
                return candidate
        for candidate in accounts:
            if candidate.label.lower() == str(account).lower():
                return candidate
        raise AccountNotFound(
            f"No bound Instagram account labelled {account!r}.",
            hint="Call instagram_auth_status() to list labels.",
            details={"available": [a.label for a in accounts]},
        )

    def resolve(
        self,
        capability: str,
        *,
        account: Optional[str] = None,
        auth_kind: Optional[str] = None,
        include_composio: bool = True,
    ) -> Account:
        accounts = self.accounts(include_composio=include_composio)

        if account:
            selected = self.get(account, include_composio=include_composio)
            if not selected.supports(capability):
                raise CapabilityUnavailable(
                    f"Account {selected.label!r} ({selected.auth_kind}) cannot {capability}.",
                    hint="See details.onboarding for the auth path that adds this capability.",
                    details={
                        "capability": capability,
                        "account": selected.to_public(),
                        "onboarding": self.onboarding(capability),
                    },
                )
            return selected

        candidates = [
            candidate
            for candidate in accounts
            if candidate.supports(capability)
            and (not auth_kind or candidate.auth_kind == auth_kind)
        ]
        if not candidates:
            raise CapabilityUnavailable(
                f"No bound Instagram credential can {capability}.",
                hint="See details.onboarding; bind the smallest path that unlocks it.",
                details={
                    "capability": capability,
                    "bound": [a.to_public() for a in accounts],
                    "onboarding": self.onboarding(capability),
                },
            )

        preference = _auth_preference()
        rank = {kind: index for index, kind in enumerate(preference)}
        preferred_label = os.environ.get("INSTAGRAM_ACCOUNT")

        def sort_key(candidate: Account):
            return (
                0 if preferred_label and candidate.label == preferred_label else 1,
                rank.get(candidate.auth_kind, len(rank)),
                candidate.label,
            )

        return sorted(candidates, key=sort_key)[0]

    def backend(self, account: Account) -> Any:
        cached = self._backends.get(account.label)
        if cached is not None:
            return cached
        if account.auth_kind == AUTH_GRAPH:
            backend = GraphClient(account)
        elif account.auth_kind == AUTH_COMPOSIO:
            backend = ComposioBackend(account)
        elif account.auth_kind == AUTH_PRIVATE:
            backend = PrivateClient(account)
        else:
            raise CredentialRequired(f"Unknown auth kind {account.auth_kind!r}.")
        self._backends[account.label] = backend
        return backend

    # -- onboarding --------------------------------------------------------

    def onboarding(self, capability: str) -> Dict[str, Any]:
        official_composio = capability in COMPOSIO_CAPABILITIES
        official_graph = capability in (
            GRAPH_BASE_CAPABILITIES | GRAPH_MESSAGING_CAPABILITIES
        )
        private = capability in PRIVATE_CAPABILITIES

        options: List[Dict[str, Any]] = []
        if official_composio:
            options.append(
                {
                    "auth_kind": AUTH_COMPOSIO,
                    "rank": 1,
                    "label": "Composio managed OAuth (fastest)",
                    "unlocks": sorted(COMPOSIO_CAPABILITIES),
                    "requires": "Instagram Business/Creator account; no Meta app required.",
                    "steps": [
                        "Call instagram_connect(target='composio') or use the Composio connect card.",
                        "Select the Instagram professional account in the OAuth picker.",
                        "Call instagram_auth_status() to confirm.",
                    ],
                    "risk": "low",
                    "note": "No hashtag/user search; DMs are reply-only inside 24h.",
                }
            )
        if official_graph:
            scopes = [
                "instagram_basic",
                "instagram_manage_comments",
                "instagram_manage_insights",
                "instagram_content_publish",
                "instagram_manage_messages",
                "pages_show_list",
                "pages_read_engagement",
            ]
            options.append(
                {
                    "auth_kind": AUTH_GRAPH,
                    "rank": 0 if capability in {c for c in GRAPH_BASE_CAPABILITIES if c.startswith("search_")} else 2,
                    "label": "Own Meta app + Facebook Login for Business",
                    "unlocks": sorted(
                        GRAPH_BASE_CAPABILITIES | GRAPH_MESSAGING_CAPABILITIES
                    ),
                    "requires": (
                        "Meta app with Facebook Login for Business; long-lived token; "
                        "Page token for messaging/private replies; App Review for "
                        "Instagram Public Content Access (hashtag search) and multi-user."
                    ),
                    "steps": [
                        "Create/choose a Meta app and add the Instagram product (Facebook Login setup).",
                        f"Request scopes: {', '.join(scopes)}.",
                        "Request feature Instagram Public Content Access for hashtag search.",
                        "Set INSTAGRAM_GRAPH_TOKEN, INSTAGRAM_GRAPH_USER_ID, and page token env vars.",
                        "Call instagram_auth_status() / instagram_capabilities().",
                    ],
                    "risk": "low",
                    "note": (
                        "Only public professional accounts are discoverable; no user keyword "
                        "search, follower lists, or cold DMs."
                    ),
                }
            )
        if private:
            options.append(
                {
                    "auth_kind": AUTH_PRIVATE,
                    "rank": 0
                    if capability
                    in {
                        "search_users",
                        "search_locations",
                        "search_posts",
                        "dm_initiate",
                        "followers_read",
                    }
                    else 3,
                    "label": "instagrapi private session (full surface)",
                    "unlocks": sorted(PRIVATE_CAPABILITIES),
                    "requires": (
                        "Username/password or sessionid; instagrapi installed; "
                        "single-tenant/internal use only."
                    ),
                    "steps": [
                        "Set INSTAGRAM_ENABLE_PRIVATE=true.",
                        "Set INSTAGRAM_USERNAME + INSTAGRAM_PASSWORD, or INSTAGRAM_SESSIONID, "
                        "or INSTAGRAM_SESSION_FILE.",
                        "For cold DMs set INSTAGRAM_ALLOW_COLD_DM=true as well.",
                        "Call instagram_connect(target='private', confirm=True) to login and persist the session.",
                    ],
                    "risk": "high",
                    "note": (
                        "Violates Instagram ToS; account-ban and challenge risk. Never use "
                        "for a multi-tenant product or bulk scraping."
                    ),
                }
            )

        options.sort(key=lambda item: (item["rank"], item["auth_kind"]))
        return {
            "capability": capability,
            "options": options,
            "recommended": options[0]["auth_kind"] if options else None,
            "notes": self._capability_notes(capability),
        }

    @staticmethod
    def _capability_notes(capability: str) -> List[str]:
        notes = {
            "search_hashtag": [
                "Official: Facebook Login + Instagram Public Content Access, 30 unique hashtags per rolling 7 days.",
                "Fetching top/recent media also counts as a query; replies cannot be posted on hashtag-discovered media.",
            ],
            "search_business": [
                "Official: exact username only, public professional accounts only.",
                "No keyword user search and no follower/following lists.",
            ],
            "search_users": ["Official API has no user keyword search; only the private backend can do it."],
            "search_locations": ["Official API has no location search; only the private backend can do it."],
            "search_posts": ["Official API has no arbitrary post search; only the private backend can do it."],
            "dm_reply": [
                "Meta allows sending only after the user opens a window: 24h for most actions, up to 7 days for Click-to-Direct, 7 days with human_agent.",
                "Error 10/2534022 means the window is closed; do not retry.",
            ],
            "dm_initiate": ["Official API cannot initiate a cold DM; only the private backend can."],
            "comment_private_reply": [
                "Official: Page token + instagram_manage_comments + pages_messaging + Human Agent.",
                "One message within 7 days of the comment; the user must reply to continue.",
            ],
            "post_publish": [
                "Official: 100 API-published posts per 24h; carousel counts as one; JPEG images only.",
                "Graph fetches media from a public HTTPS URL; Composio can stage some files.",
            ],
            "followers_read": ["Official API exposes counts only, not follower/following lists."],
        }
        return notes.get(capability, [])
