"""Public Instagram functions.

Every function returns a JSON-serialisable dict:

    {"ok": True,  "account": "...", "auth_kind": "...", "data": ...}
    {"ok": False, "error": {"code": ..., "message": ..., "hint": ...}}

The agent should call ``instagram_auth_status()`` first. If a requested
capability is not bound, the error already contains ``details.onboarding`` with
the smallest auth path that unlocks it.
"""

from __future__ import annotations

import inspect
import os
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional

from ig_errors import (
    CapabilityUnavailable,
    ConfirmationRequired,
    InstagramError,
    NotFound,
    ProviderError,
    ValidationError,
    WriteBlocked,
)
from ig_gateway import GatewayClient
from ig_graph import GraphClient
from ig_models import (
    ALL_CAPABILITIES,
    AUTH_COMPOSIO,
    AUTH_GRAPH,
    AUTH_PRIVATE,
    Account,
    COMPOSIO_CAPABILITIES,
    GRAPH_BASE_CAPABILITIES,
    GRAPH_MESSAGING_CAPABILITIES,
    PRIVATE_CAPABILITIES,
    graph_capabilities,
    private_capabilities,
)
from ig_private import PrivateClient
from ig_router import Router, _env_bool

ROUTER = Router()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _ok(data: Any, account: Optional[Account] = None, **extra: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {"ok": True}
    if account:
        result["account"] = account.label
        result["auth_kind"] = account.auth_kind
    result["data"] = data
    result.update(extra)
    return result


def _error(exc: Exception) -> Dict[str, Any]:
    if isinstance(exc, InstagramError):
        return exc.to_dict()
    return ProviderError(str(exc)).to_dict()


def _invoke(backend: Any, method: str, **kwargs: Any) -> Any:
    """Call a backend method, dropping kwargs it does not accept."""
    fn = getattr(backend, method, None)
    if fn is None:
        raise CapabilityUnavailable(f"{type(backend).__name__} cannot {method}.")
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return fn(**kwargs)
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()):
        return fn(**kwargs)
    allowed = {key: value for key, value in kwargs.items() if key in signature.parameters}
    return fn(**allowed)


def _call_any(
    capabilities: Iterable[str],
    method: str,
    *,
    account: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Try capability candidates in order; fall back only on capability/not-found."""
    errors: List[tuple[str, InstagramError]] = []
    for capability in capabilities:
        try:
            selected = ROUTER.resolve(capability, account=account)
        except InstagramError as exc:
            errors.append((capability, exc))
            continue
        try:
            backend = ROUTER.backend(selected)
            return _ok(_invoke(backend, method, **kwargs), selected)
        except (CapabilityUnavailable, NotFound) as exc:
            errors.append((capability, exc))
            continue
        except InstagramError as exc:
            return _error(exc)
    if not errors:
        return _error(CapabilityUnavailable("No capability candidate was supplied."))
    first = errors[0][1]
    if isinstance(first, CapabilityUnavailable):
        onboarding: Dict[str, Any] = {}
        for capability, exc in errors:
            options = (exc.details or {}).get("onboarding")
            if options:
                onboarding[capability] = options
        return _error(
            CapabilityUnavailable(
                "No bound credential can read this profile/account.",
                hint="Use Graph business discovery for professional accounts, or bind a private session.",
                details={
                    "candidates": [capability for capability, _ in errors],
                    "onboarding": onboarding,
                },
            )
        )
    return _error(first)


def _call(
    capability: str,
    method: str,
    *,
    account: Optional[str] = None,
    auth_kind: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    try:
        selected = ROUTER.resolve(
            capability,
            account=account,
            auth_kind=auth_kind,
        )
        backend = ROUTER.backend(selected)
        data = _invoke(backend, method, **kwargs)
        return _ok(data, selected)
    except Exception as exc:
        return _error(exc)


def _guard(
    operation: str,
    *,
    account: Optional[Account],
    confirm: bool,
    dry_run: bool,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if dry_run:
        return _ok(
            {
                "dry_run": True,
                "operation": operation,
                "payload": payload,
                "writes_enabled": _env_bool("INSTAGRAM_ALLOW_WRITES", False),
                "next": "Call again with dry_run=False, confirm=True to execute.",
            },
            account,
        )
    if not _env_bool("INSTAGRAM_ALLOW_WRITES", False):
        raise WriteBlocked(
            "Instagram writes are disabled for this agent.",
            hint="Set INSTAGRAM_ALLOW_WRITES=true after reviewing the account and target.",
            details={"operation": operation},
        )
    if not confirm and not _env_bool("INSTAGRAM_AUTO_CONFIRM", False):
        raise ConfirmationRequired(
            f"{operation} requires explicit confirmation.",
            hint="Show the exact text/media to the user, then call again with confirm=True.",
            details={"operation": operation, "payload": payload},
        )
    return None


def _call_with_guard(
    capability: str,
    method: str,
    *,
    account: Optional[str],
    confirm: bool,
    dry_run: bool,
    payload: Dict[str, Any],
    **kwargs: Any,
) -> Dict[str, Any]:
    try:
        selected = ROUTER.resolve(capability, account=account)
        preview = _guard(
            f"{capability}:{method}",
            account=selected,
            confirm=confirm,
            dry_run=dry_run,
            payload=payload,
        )
        if preview is not None:
            return preview
        backend = ROUTER.backend(selected)
        data = _invoke(backend, method, **kwargs)
        return _ok(data, selected)
    except Exception as exc:
        return _error(exc)


def _capability_view(account: Account) -> Dict[str, Any]:
    supported = sorted(account.capabilities)
    missing = sorted(set(ALL_CAPABILITIES) - set(supported))
    return {
        "account": account.to_public(),
        "supported": supported,
        "missing": missing,
    }


# ---------------------------------------------------------------------------
# auth / connection
# ---------------------------------------------------------------------------


def instagram_connect(
    target: str = "auto",
    capability: Optional[str] = None,
    account: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Start or complete the smallest auth flow for a capability.

    ``target``: ``auto`` | ``composio`` | ``graph`` | ``private``.

    If a bound credential already supports ``capability``, this returns
    ``already_connected`` and does not start a second authorization.
    """
    try:
        if capability:
            try:
                selected = ROUTER.resolve(capability, account=account)
                return _ok(
                    {"status": "already_connected", "capability": capability},
                    selected,
                )
            except CapabilityUnavailable:
                pass

        target = (target or "auto").lower()
        if target == "auto":
            if capability in {
                "search_users",
                "search_locations",
                "search_posts",
                "dm_initiate",
                "followers_read",
            }:
                target = AUTH_PRIVATE
            elif capability in {"search_hashtag", "search_business", "comment_private_reply"}:
                target = AUTH_GRAPH
            elif ROUTER.accounts(include_composio=True) and not capability:
                return _ok(
                    {
                        "status": "already_bound",
                        "accounts": [a.to_public() for a in ROUTER.accounts()],
                        "next": "Call instagram_auth_status() or specify target/capability.",
                    }
                )
            else:
                target = AUTH_COMPOSIO

        static_caps = {
            AUTH_COMPOSIO: COMPOSIO_CAPABILITIES,
            AUTH_GRAPH: GRAPH_BASE_CAPABILITIES | GRAPH_MESSAGING_CAPABILITIES,
            AUTH_PRIVATE: PRIVATE_CAPABILITIES,
        }
        if capability and target in static_caps and capability not in static_caps[target]:
            return _ok(
                {
                    "status": "capability_not_available",
                    "capability": capability,
                    "auth_kind": target,
                    "onboarding": ROUTER.onboarding(capability),
                }
            )

        if target == AUTH_COMPOSIO:
            if not _env_bool("INSTAGRAM_COMPOSIO_ENABLED", True):
                return _ok(
                    {
                        "status": "disabled",
                        "auth_kind": AUTH_COMPOSIO,
                        "instructions": "Set INSTAGRAM_COMPOSIO_ENABLED=true to use managed OAuth.",
                    }
                )
            try:
                existing = ROUTER.resolve("connect", auth_kind=AUTH_COMPOSIO, account=account)
                return _ok(
                    {"status": "already_connected", "capability": capability},
                    existing,
                )
            except CapabilityUnavailable:
                pass
            gateway = GatewayClient()
            response = gateway.connect("instagram")
            connect_url = None
            for key in ("connect_url", "redirect_url", "url"):
                if isinstance(response, dict) and response.get(key):
                    connect_url = response[key]
                    break
            return _ok(
                {
                    "status": "action_required",
                    "auth_kind": AUTH_COMPOSIO,
                    "connect_url": connect_url,
                    "response": response,
                    "action_request": {
                        "action_type": "composio_connect",
                        "toolkit": "instagram",
                        "display_name": "Instagram",
                        "connect_url": connect_url,
                    },
                    "instructions": (
                        "On Web, render the Composio connect card via "
                        "frontend_action(action_type='composio_connect', toolkit='instagram'). "
                        "Else show connect_url as plain text. Then call "
                        "instagram_auth_status() to confirm."
                    ),
                }
            )

        if target == AUTH_GRAPH:
            try:
                existing = ROUTER.resolve("connect", auth_kind=AUTH_GRAPH, account=account)
                return _ok(
                    {"status": "already_connected", "capability": capability},
                    existing,
                )
            except CapabilityUnavailable:
                pass
            token = os.environ.get("INSTAGRAM_GRAPH_TOKEN") or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
            if token:
                temp = Account(
                    label=os.environ.get("INSTAGRAM_ACCOUNT") or "graph",
                    auth_kind=AUTH_GRAPH,
                    capabilities=graph_capabilities(
                        has_page_token=bool(
                            os.environ.get("INSTAGRAM_GRAPH_PAGE_TOKEN")
                            or os.environ.get("INSTAGRAM_GRAPH_PAGE_ID")
                        ),
                    ),
                    ig_user_id=os.environ.get("INSTAGRAM_GRAPH_USER_ID"),
                    page_id=os.environ.get("INSTAGRAM_GRAPH_PAGE_ID"),
                    metadata={
                        "access_token": token,
                        "page_token": os.environ.get("INSTAGRAM_GRAPH_PAGE_TOKEN"),
                        "ig_user_id": os.environ.get("INSTAGRAM_GRAPH_USER_ID"),
                        "page_id": os.environ.get("INSTAGRAM_GRAPH_PAGE_ID"),
                        "app_id": os.environ.get("INSTAGRAM_META_APP_ID"),
                        "app_secret": os.environ.get("INSTAGRAM_META_APP_SECRET"),
                        "login_type": os.environ.get("INSTAGRAM_LOGIN_TYPE", "facebook"),
                    },
                )
                me = GraphClient(temp).validate()
                ROUTER.refresh()
                return _ok({"status": "connected", "me": me}, temp)

            app_id = os.environ.get("INSTAGRAM_META_APP_ID")
            redirect_uri = os.environ.get("INSTAGRAM_OAUTH_REDIRECT_URI")
            provider = os.environ.get("INSTAGRAM_OAUTH_PROVIDER", "facebook").lower()
            scopes = [
                "instagram_basic",
                "instagram_manage_comments",
                "instagram_manage_insights",
                "instagram_content_publish",
                "instagram_manage_messages",
                "pages_show_list",
                "pages_read_engagement",
            ]
            oauth_url = None
            if app_id and redirect_uri:
                state = os.environ.get("INSTAGRAM_OAUTH_STATE", "instagram")
                if provider == "instagram":
                    oauth_url = (
                        "https://www.instagram.com/oauth/authorize?"
                        + urllib.parse.urlencode(
                            {
                                "client_id": app_id,
                                "redirect_uri": redirect_uri,
                                "response_type": "code",
                                "scope": ",".join(scopes),
                                "state": state,
                            }
                        )
                    )
                else:
                    oauth_url = (
                        f"https://www.facebook.com/{os.environ.get('INSTAGRAM_GRAPH_API_VERSION', 'v26.0')}/dialog/oauth?"
                        + urllib.parse.urlencode(
                            {
                                "client_id": app_id,
                                "redirect_uri": redirect_uri,
                                "response_type": "code",
                                "scope": ",".join(scopes),
                                "state": state,
                            }
                        )
                    )
            return _ok(
                {
                    "status": "action_required",
                    "auth_kind": AUTH_GRAPH,
                    "oauth_url": oauth_url,
                    "scopes": scopes,
                    "instructions": [
                        "Create a Meta app and use Facebook Login for Business (not Instagram Login) "
                        "if you need hashtag search or business discovery.",
                        "Request Instagram Public Content Access for hashtag search.",
                        "Add a Page token for messaging and private replies.",
                        "Exchange the authorization code server-side, then set "
                        "INSTAGRAM_GRAPH_TOKEN / INSTAGRAM_GRAPH_USER_ID (and page vars).",
                    ],
                    "onboarding": ROUTER.onboarding(capability or "search_hashtag"),
                }
            )

        if target == AUTH_PRIVATE:
            try:
                existing = ROUTER.resolve("connect", auth_kind=AUTH_PRIVATE, account=account)
                return _ok(
                    {"status": "already_connected", "capability": capability},
                    existing,
                )
            except CapabilityUnavailable:
                pass
            if capability == "dm_initiate" and not _env_bool("INSTAGRAM_ALLOW_COLD_DM", False):
                return _ok(
                    {
                        "status": "disabled",
                        "auth_kind": AUTH_PRIVATE,
                        "instructions": "Set INSTAGRAM_ALLOW_COLD_DM=true to enable cold DMs.",
                        "risk": "high: unsolicited DMs can trigger account restrictions.",
                    }
                )
            has_creds = bool(
                os.environ.get("INSTAGRAM_SESSION_FILE")
                or os.environ.get("INSTAGRAM_SESSIONID")
                or (os.environ.get("INSTAGRAM_USERNAME") and os.environ.get("INSTAGRAM_PASSWORD"))
            )
            if not has_creds:
                return _ok(
                    {
                        "status": "action_required",
                        "auth_kind": AUTH_PRIVATE,
                        "instructions": [
                            "Private mode is the only path for personal accounts, people/location search, "
                            "follower lists, and cold DMs.",
                            "Set INSTAGRAM_ENABLE_PRIVATE=true plus one of: INSTAGRAM_SESSIONID, "
                            "INSTAGRAM_SESSION_FILE, or INSTAGRAM_USERNAME + INSTAGRAM_PASSWORD.",
                            "Then call instagram_connect(target='private', confirm=True).",
                        ],
                        "risk": "high: Instagram ToS and account-ban risk; single-tenant/internal only.",
                    }
                )
            if not confirm:
                raise ConfirmationRequired(
                    "Private login will create/refresh an Instagram session file.",
                    hint="Call again with confirm=True. Use a secondary account if experimenting.",
                    details={"auth_kind": AUTH_PRIVATE, "risk": "high"},
                )
            temp = Account(
                label=os.environ.get("INSTAGRAM_ACCOUNT") or "private",
                auth_kind=AUTH_PRIVATE,
                capabilities=private_capabilities(
                    cold_dm=_env_bool("INSTAGRAM_ALLOW_COLD_DM", False),
                    private_enabled=True,
                ),
                session_file=os.environ.get("INSTAGRAM_SESSION_FILE"),
                metadata={
                    "username": os.environ.get("INSTAGRAM_USERNAME"),
                    "password": os.environ.get("INSTAGRAM_PASSWORD"),
                    "sessionid": os.environ.get("INSTAGRAM_SESSIONID"),
                    "totp_seed": os.environ.get("INSTAGRAM_TOTP_SEED"),
                    "proxy": os.environ.get("INSTAGRAM_PROXY"),
                    "session_file": os.environ.get("INSTAGRAM_SESSION_FILE"),
                },
            )
            info = PrivateClient(temp).profile()
            ROUTER.refresh()
            return _ok(
                {
                    "status": "connected",
                    "session_file": temp.session_file,
                    "profile": info,
                    "risk": "high: private API; stop on challenge/action_blocked.",
                },
                temp,
            )

        raise ValidationError(
            f"Unknown target {target!r}.",
            hint="Use auto, composio, graph, or private.",
        )
    except Exception as exc:
        return _error(exc)


def _gateway_health() -> Dict[str, Any]:
    if not _env_bool("INSTAGRAM_COMPOSIO_ENABLED", True):
        return {"ok": False, "error": "composio disabled"}
    return GatewayClient().health()


def instagram_auth_status(account: Optional[str] = None) -> Dict[str, Any]:
    """List bound credentials and their capabilities. Never starts auth."""
    try:
        accounts = ROUTER.accounts(include_composio=True, refresh=True)
        if account:
            selected = ROUTER.get(account)
            return _ok(
                {
                    "gateway": _gateway_health(),
                    "account": _capability_view(selected),
                    "writes_enabled": _env_bool("INSTAGRAM_ALLOW_WRITES", False),
                    "private_enabled": _env_bool("INSTAGRAM_ENABLE_PRIVATE", False),
                }
            )
        union = sorted({cap for item in accounts for cap in item.capabilities})
        return _ok(
            {
                "gateway": _gateway_health(),
                "accounts": [_capability_view(item) for item in accounts],
                "capabilities": union,
                "writes_enabled": _env_bool("INSTAGRAM_ALLOW_WRITES", False),
                "private_enabled": _env_bool("INSTAGRAM_ENABLE_PRIVATE", False),
                "preference": os.environ.get("INSTAGRAM_PREFERRED_AUTH", "graph,composio,private"),
                "next": (
                    "No credentials bound. Call instagram_connect() "
                    "or instagram_connect(target='composio')."
                    if not accounts
                    else "Requested capability missing? Read error.details.onboarding."
                ),
            }
        )
    except Exception as exc:
        return _error(exc)


def instagram_capabilities(account: Optional[str] = None) -> Dict[str, Any]:
    """Capability matrix for one account or all bound accounts."""
    try:
        if account:
            selected = ROUTER.get(account)
            view = _capability_view(selected)
            view["onboarding"] = {
                cap: ROUTER.onboarding(cap)
                for cap in (
                    "search_hashtag",
                    "search_business",
                    "search_users",
                    "search_locations",
                    "search_posts",
                    "dm_initiate",
                    "comment_private_reply",
                )
                if cap not in selected.capabilities
            }
            return _ok(view)
        accounts = ROUTER.accounts(include_composio=True, refresh=True)
        union = sorted({cap for item in accounts for cap in item.capabilities})
        missing = sorted(set(ALL_CAPABILITIES) - set(union))
        return _ok(
            {
                "accounts": [_capability_view(item) for item in accounts],
                "union": union,
                "missing_everywhere": missing,
                "onboarding": {
                    cap: ROUTER.onboarding(cap)
                    for cap in (
                        "search_hashtag",
                        "search_business",
                        "search_users",
                        "search_locations",
                        "search_posts",
                        "dm_initiate",
                        "comment_private_reply",
                    )
                    if cap in missing
                },
            }
        )
    except Exception as exc:
        return _error(exc)


def instagram_disconnect(account: str, confirm: bool = False) -> Dict[str, Any]:
    """Remove one bound credential. Never touches another account."""
    try:
        selected = ROUTER.get(account)
        if not confirm:
            raise ConfirmationRequired(
                f"Disconnecting {account!r} removes its local binding.",
                hint="Call again with confirm=True.",
                details={"account": selected.to_public()},
            )
        if selected.auth_kind == AUTH_COMPOSIO:
            connection_id = selected.metadata.get("connection_id")
            if not connection_id:
                raise ValidationError("No Composio connection id is bound.")
            result = GatewayClient().disconnect(str(connection_id))
            ROUTER.refresh()
            return _ok({"status": "disconnected", "composio": result}, selected)
        if selected.auth_kind == AUTH_PRIVATE:
            path = selected.session_file or os.environ.get("INSTAGRAM_SESSION_FILE")
            if path and os.path.exists(path):
                os.remove(path)
            ROUTER.refresh()
            return _ok(
                {
                    "status": "session_removed",
                    "session_file": path,
                    "note": "Credentials in env/config remain until you unset them.",
                },
                selected,
            )
        return _ok(
            {
                "status": "manual",
                "note": "Graph tokens are bound via env/config; unset INSTAGRAM_GRAPH_TOKEN to disconnect.",
            },
            selected,
        )
    except Exception as exc:
        return _error(exc)


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------


def instagram_profile(username: Optional[str] = None, account: Optional[str] = None) -> Dict[str, Any]:
    if username:
        return _call_any(
            ["search_business", "search_users"],
            "profile",
            account=account,
            username=username,
        )
    return _call("profile_read", "profile", account=account, username=None)


def instagram_list_media(
    username: Optional[str] = None,
    limit: int = 25,
    after: Optional[str] = None,
    account: Optional[str] = None,
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    if username:
        return _call_any(
            ["search_business", "search_users"],
            "list_media",
            account=account,
            username=username,
            limit=limit,
            after=after,
            fields=fields,
        )
    return _call(
        "media_read",
        "list_media",
        account=account,
        username=None,
        limit=limit,
        after=after,
        fields=fields,
    )


def instagram_get_media(
    media: str,
    account: Optional[str] = None,
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    return _call("media_read", "get_media", account=account, media=media, fields=fields)


def instagram_list_comments(
    media: str,
    limit: int = 50,
    after: Optional[str] = None,
    account: Optional[str] = None,
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    return _call(
        "comments_read",
        "list_comments",
        account=account,
        media=media,
        limit=limit,
        after=after,
        fields=fields,
    )


def instagram_list_comment_replies(
    comment_id: str,
    media: Optional[str] = None,
    limit: int = 50,
    after: Optional[str] = None,
    account: Optional[str] = None,
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    return _call(
        "comments_read",
        "list_comment_replies",
        account=account,
        comment_id=comment_id,
        media=media,
        limit=limit,
        after=after,
        fields=fields,
    )


def instagram_insights(
    metric: Optional[str] = None,
    period: Optional[str] = None,
    metric_type: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    breakdown: Optional[str] = None,
    media: Optional[str] = None,
    account: Optional[str] = None,
) -> Dict[str, Any]:
    return _call(
        "insights_read",
        "insights",
        account=account,
        metric=metric,
        period=period,
        metric_type=metric_type,
        since=since,
        until=until,
        breakdown=breakdown,
        media=media,
    )


def instagram_list_followers(
    username: Optional[str] = None,
    limit: int = 50,
    account: Optional[str] = None,
) -> Dict[str, Any]:
    return _call(
        "followers_read",
        "list_followers",
        account=account,
        username=username,
        limit=limit,
    )


def instagram_list_following(
    username: Optional[str] = None,
    limit: int = 50,
    account: Optional[str] = None,
) -> Dict[str, Any]:
    return _call(
        "followers_read",
        "list_following",
        account=account,
        username=username,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def instagram_search_hashtag(query: str, account: Optional[str] = None) -> Dict[str, Any]:
    return _call("search_hashtag", "search_hashtag", account=account, query=query)


def instagram_hashtag_media(
    hashtag_id: str,
    mode: str = "top",
    limit: int = 25,
    after: Optional[str] = None,
    hashtag: Optional[str] = None,
    account: Optional[str] = None,
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        selected = ROUTER.resolve("search_hashtag", account=account)
        backend = ROUTER.backend(selected)
        value = str(hashtag_id).strip().lstrip("#")
        if isinstance(backend, GraphClient):
            if not value.isdigit():
                resolved = backend.search_hashtag(value)
                value = str(resolved["id"])
                hashtag = resolved.get("query", value)
        elif isinstance(backend, PrivateClient):
            hashtag = (hashtag or value).strip().lstrip("#")
            if hashtag.isdigit():
                raise ValidationError("Private hashtag media needs a tag name, not an id.")
            value = hashtag
        data = _invoke(
            backend,
            "hashtag_media",
            hashtag_id=value,
            mode=mode,
            limit=limit,
            after=after,
            hashtag=hashtag,
            fields=fields,
        )
        return _ok(data, selected)
    except Exception as exc:
        return _error(exc)


def instagram_business_discovery(
    username: str,
    fields: Optional[str] = None,
    account: Optional[str] = None,
) -> Dict[str, Any]:
    return _call(
        "search_business",
        "business_discovery",
        account=account,
        username=username,
        fields=fields,
    )


def instagram_search_users(
    query: str, limit: int = 20, account: Optional[str] = None
) -> Dict[str, Any]:
    return _call("search_users", "search_users", account=account, query=query, limit=limit)


def instagram_search_locations(
    query: str, limit: int = 20, account: Optional[str] = None
) -> Dict[str, Any]:
    return _call(
        "search_locations",
        "search_locations",
        account=account,
        query=query,
        limit=limit,
    )


def instagram_search_posts(
    query: str, limit: int = 20, account: Optional[str] = None
) -> Dict[str, Any]:
    return _call("search_posts", "search_posts", account=account, query=query, limit=limit)


# ---------------------------------------------------------------------------
# publishing
# ---------------------------------------------------------------------------


def instagram_publish(
    media_type: str = "image",
    image_url: Optional[str] = None,
    video_url: Optional[str] = None,
    caption: str = "",
    carousel_items: Optional[List[Dict[str, str]]] = None,
    alt_text: Optional[str] = None,
    is_ai_generated: bool = False,
    share_to_feed: bool = True,
    extra: Optional[Dict[str, Any]] = None,
    account: Optional[str] = None,
    confirm: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    capability = "story_publish" if media_type.lower() == "story" else "post_publish"
    return _call_with_guard(
        capability,
        "publish",
        account=account,
        confirm=confirm,
        dry_run=dry_run,
        payload={
            "media_type": media_type,
            "image_url": image_url,
            "video_url": video_url,
            "caption": caption,
            "carousel_items": carousel_items,
            "alt_text": alt_text,
            "is_ai_generated": is_ai_generated,
        },
        media_type=media_type,
        image_url=image_url,
        video_url=video_url,
        caption=caption,
        carousel_items=carousel_items,
        alt_text=alt_text,
        is_ai_generated=is_ai_generated,
        share_to_feed=share_to_feed,
        extra=extra,
    )


def instagram_publish_status(container_id: str, account: Optional[str] = None) -> Dict[str, Any]:
    try:
        selected = ROUTER.resolve("post_publish", account=account)
        backend = ROUTER.backend(selected)
        if hasattr(backend, "container_status"):
            return _ok(backend.container_status(container_id), selected)
        if hasattr(backend, "wait_for_container"):
            return _ok(backend.wait_for_container(container_id), selected)
        raise CapabilityUnavailable(
            "This backend cannot poll a media container.",
            hint="Use Graph, or read the published media id returned by publish.",
        )
    except Exception as exc:
        return _error(exc)


def instagram_publishing_limit(account: Optional[str] = None) -> Dict[str, Any]:
    return _call("publish_limit", "publishing_limit", account=account)


# ---------------------------------------------------------------------------
# replies / comments
# ---------------------------------------------------------------------------


def instagram_reply_comment(
    comment_id: str,
    text: str,
    media: Optional[str] = None,
    account: Optional[str] = None,
    confirm: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    return _call_with_guard(
        "comment_reply",
        "reply_comment",
        account=account,
        confirm=confirm,
        dry_run=dry_run,
        payload={"comment_id": comment_id, "text": text, "media": media},
        comment_id=comment_id,
        text=text,
        media=media,
    )


def instagram_comment_on_media(
    media: str,
    text: str,
    account: Optional[str] = None,
    confirm: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    return _call_with_guard(
        "comment_reply",
        "comment_on_media",
        account=account,
        confirm=confirm,
        dry_run=dry_run,
        payload={"media": media, "text": text},
        media=media,
        text=text,
    )


def instagram_private_reply(
    comment_id: str,
    text: str,
    account: Optional[str] = None,
    confirm: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    return _call_with_guard(
        "comment_private_reply",
        "private_reply",
        account=account,
        confirm=confirm,
        dry_run=dry_run,
        payload={"comment_id": comment_id, "text": text},
        comment_id=comment_id,
        text=text,
    )


def instagram_reply_mention(
    media: str,
    text: str,
    account: Optional[str] = None,
    confirm: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    return _call_with_guard(
        "mention_reply",
        "reply_mention",
        account=account,
        confirm=confirm,
        dry_run=dry_run,
        payload={"media": media, "text": text},
        media=media,
        text=text,
    )


def instagram_hide_comment(
    comment_id: str,
    hide: bool = True,
    account: Optional[str] = None,
    confirm: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    return _call_with_guard(
        "comment_moderate",
        "hide_comment",
        account=account,
        confirm=confirm,
        dry_run=dry_run,
        payload={"comment_id": comment_id, "hide": hide},
        comment_id=comment_id,
        hide=hide,
    )


def instagram_delete_comment(
    comment_id: str,
    media: Optional[str] = None,
    account: Optional[str] = None,
    confirm: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    return _call_with_guard(
        "comment_moderate",
        "delete_comment",
        account=account,
        confirm=confirm,
        dry_run=dry_run,
        payload={"comment_id": comment_id, "media": media},
        comment_id=comment_id,
        media=media,
    )


# ---------------------------------------------------------------------------
# direct messages
# ---------------------------------------------------------------------------


def instagram_list_conversations(
    limit: int = 20,
    after: Optional[str] = None,
    account: Optional[str] = None,
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    return _call(
        "dm_read",
        "conversations",
        account=account,
        limit=limit,
        after=after,
        fields=fields,
    )


def instagram_get_conversation(
    conversation_id: str, account: Optional[str] = None
) -> Dict[str, Any]:
    return _call(
        "dm_read",
        "conversation",
        account=account,
        conversation_id=conversation_id,
    )


def instagram_list_messages(
    conversation_id: str,
    limit: int = 20,
    after: Optional[str] = None,
    account: Optional[str] = None,
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    return _call(
        "dm_read",
        "messages",
        account=account,
        conversation_id=conversation_id,
        limit=limit,
        after=after,
        fields=fields,
    )


def instagram_send_dm(
    text: Optional[str] = None,
    image_url: Optional[str] = None,
    recipient_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    account: Optional[str] = None,
    confirm: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    chosen = "dm_reply"
    try:
        selected = ROUTER.resolve(chosen, account=account)
    except CapabilityUnavailable as first_error:
        if conversation_id:
            return _error(first_error)
        try:
            chosen = "dm_initiate"
            selected = ROUTER.resolve(chosen, account=account)
        except CapabilityUnavailable:
            return _error(first_error)

    return _call_with_guard(
        chosen,
        "send_dm",
        account=selected.label,
        confirm=confirm,
        dry_run=dry_run,
        payload={
            "text": text,
            "image_url": image_url,
            "recipient_id": recipient_id,
            "conversation_id": conversation_id,
        },
        text=text,
        image_url=image_url,
        recipient_id=recipient_id,
        conversation_id=conversation_id,
    )


def instagram_mark_seen(
    recipient_id: str,
    account: Optional[str] = None,
    confirm: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    return _call_with_guard(
        "dm_reply",
        "mark_seen",
        account=account,
        confirm=confirm,
        dry_run=dry_run,
        payload={"recipient_id": recipient_id},
        recipient_id=recipient_id,
    )


# ---------------------------------------------------------------------------
# auth utilities
# ---------------------------------------------------------------------------


def instagram_refresh_token(
    account: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    try:
        selected = ROUTER.resolve("connect", account=account, auth_kind=AUTH_GRAPH)
        if not confirm:
            raise ConfirmationRequired(
                "Refreshing a Graph token returns a new long-lived token.",
                hint="Persist it in the credential store, then call again with confirm=True.",
            )
        backend = ROUTER.backend(selected)
        if not hasattr(backend, "refresh_token"):
            raise CapabilityUnavailable("This backend does not expose token refresh.")
        return _ok(backend.refresh_token(), selected)
    except Exception as exc:
        return _error(exc)


def instagram_hashtag_usage(account: Optional[str] = None) -> Dict[str, Any]:
    try:
        selected = ROUTER.resolve("search_hashtag", account=account, auth_kind=AUTH_GRAPH)
        backend = ROUTER.backend(selected)
        if not hasattr(backend, "hashtag_usage"):
            raise CapabilityUnavailable("Hashtag quota is tracked for Graph accounts only.")
        return _ok(backend.hashtag_usage(), selected)
    except Exception as exc:
        return _error(exc)
