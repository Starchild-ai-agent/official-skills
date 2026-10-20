"""Accounts, auth kinds and capability sets.

The hybrid rule lives here: an account has exactly one ``auth_kind`` and a
static capability set for that kind. Credentials only add/remove capabilities
that are genuinely token-dependent (Graph messaging and hashtag search).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional

AUTH_GRAPH = "graph"
AUTH_COMPOSIO = "composio"
AUTH_PRIVATE = "private"

AUTH_KINDS = (AUTH_GRAPH, AUTH_COMPOSIO, AUTH_PRIVATE)

# Capability names are stable API surface. Keep them short and verb-like.
CAP_CONNECT = "connect"
CAP_PROFILE_READ = "profile_read"
CAP_MEDIA_READ = "media_read"
CAP_COMMENTS_READ = "comments_read"
CAP_INSIGHTS_READ = "insights_read"
CAP_FOLLOWERS_READ = "followers_read"
CAP_DM_READ = "dm_read"
CAP_POST_PUBLISH = "post_publish"
CAP_STORY_PUBLISH = "story_publish"
CAP_COMMENT_REPLY = "comment_reply"
CAP_COMMENT_MODERATE = "comment_moderate"
CAP_MENTION_REPLY = "mention_reply"
CAP_DM_REPLY = "dm_reply"
CAP_DM_INITIATE = "dm_initiate"
CAP_COMMENT_PRIVATE_REPLY = "comment_private_reply"
CAP_PUBLISH_LIMIT = "publish_limit"
CAP_SEARCH_HASHTAG = "search_hashtag"
CAP_SEARCH_BUSINESS = "search_business"
CAP_SEARCH_USERS = "search_users"
CAP_SEARCH_LOCATIONS = "search_locations"
CAP_SEARCH_POSTS = "search_posts"

ALL_CAPABILITIES = (
    CAP_CONNECT,
    CAP_PROFILE_READ,
    CAP_MEDIA_READ,
    CAP_COMMENTS_READ,
    CAP_INSIGHTS_READ,
    CAP_FOLLOWERS_READ,
    CAP_DM_READ,
    CAP_POST_PUBLISH,
    CAP_STORY_PUBLISH,
    CAP_COMMENT_REPLY,
    CAP_COMMENT_MODERATE,
    CAP_MENTION_REPLY,
    CAP_DM_REPLY,
    CAP_DM_INITIATE,
    CAP_COMMENT_PRIVATE_REPLY,
    CAP_PUBLISH_LIMIT,
    CAP_SEARCH_HASHTAG,
    CAP_SEARCH_BUSINESS,
    CAP_SEARCH_USERS,
    CAP_SEARCH_LOCATIONS,
    CAP_SEARCH_POSTS,
)

# Composio's Instagram toolkit: official Graph API behind managed OAuth.
# No search tools are exposed, and DMs are reply-only inside an existing thread.
COMPOSIO_CAPABILITIES: FrozenSet[str] = frozenset(
    {
        CAP_CONNECT,
        CAP_PROFILE_READ,
        CAP_MEDIA_READ,
        CAP_COMMENTS_READ,
        CAP_INSIGHTS_READ,
        CAP_DM_READ,
        CAP_POST_PUBLISH,
        CAP_COMMENT_REPLY,
        CAP_COMMENT_MODERATE,
        CAP_MENTION_REPLY,
        CAP_DM_REPLY,
        CAP_PUBLISH_LIMIT,
    }
)

# Official Graph API with our own Meta app + Facebook Login for Business.
# Hashtag search and business discovery are the reason to own the app.
GRAPH_BASE_CAPABILITIES: FrozenSet[str] = frozenset(
    {
        CAP_CONNECT,
        CAP_PROFILE_READ,
        CAP_MEDIA_READ,
        CAP_COMMENTS_READ,
        CAP_INSIGHTS_READ,
        CAP_POST_PUBLISH,
        CAP_STORY_PUBLISH,
        CAP_COMMENT_REPLY,
        CAP_COMMENT_MODERATE,
        CAP_MENTION_REPLY,
        CAP_PUBLISH_LIMIT,
        CAP_SEARCH_HASHTAG,
        CAP_SEARCH_BUSINESS,
    }
)
GRAPH_MESSAGING_CAPABILITIES: FrozenSet[str] = frozenset(
    {
        CAP_DM_READ,
        CAP_DM_REPLY,
        CAP_COMMENT_PRIVATE_REPLY,
    }
)

# instagrapi private API. Full surface, including cold DMs and people search.
PRIVATE_CAPABILITIES: FrozenSet[str] = frozenset(
    {
        CAP_CONNECT,
        CAP_PROFILE_READ,
        CAP_MEDIA_READ,
        CAP_COMMENTS_READ,
        CAP_INSIGHTS_READ,
        CAP_FOLLOWERS_READ,
        CAP_DM_READ,
        CAP_POST_PUBLISH,
        CAP_STORY_PUBLISH,
        CAP_COMMENT_REPLY,
        CAP_COMMENT_MODERATE,
        CAP_MENTION_REPLY,
        CAP_DM_REPLY,
        CAP_DM_INITIATE,
        CAP_SEARCH_HASHTAG,
        CAP_SEARCH_USERS,
        CAP_SEARCH_LOCATIONS,
        CAP_SEARCH_POSTS,
    }
)


@dataclass
class Account:
    """One bound Instagram identity.

    ``label`` is what the user passes as ``account=``. Secrets never appear in
    ``to_public()``.
    """

    label: str
    auth_kind: str
    capabilities: FrozenSet[str]
    ig_user_id: Optional[str] = None
    page_id: Optional[str] = None
    session_file: Optional[str] = None
    source: str = "env"
    disabled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def supports(self, capability: str) -> bool:
        return not self.disabled and capability in self.capabilities

    def to_public(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "auth_kind": self.auth_kind,
            "ig_user_id": self.ig_user_id,
            "page_id": self.page_id,
            "source": self.source,
            "disabled": self.disabled,
            "capabilities": sorted(self.capabilities),
            "metadata": {
                k: v
                for k, v in self.metadata.items()
                if k
                in {
                    "connection_id",
                    "status",
                    "username",
                    "requires_feature",
                    "risk",
                    "note",
                }
            },
        }


def graph_capabilities(
    *,
    has_page_token: bool,
    hashtag_search: bool = True,
    business_discovery: bool = True,
) -> FrozenSet[str]:
    caps = set(GRAPH_BASE_CAPABILITIES)
    if has_page_token:
        caps |= GRAPH_MESSAGING_CAPABILITIES
    if not hashtag_search:
        caps.discard(CAP_SEARCH_HASHTAG)
    if not business_discovery:
        caps.discard(CAP_SEARCH_BUSINESS)
    return frozenset(caps)


def composio_capabilities() -> FrozenSet[str]:
    return COMPOSIO_CAPABILITIES


def private_capabilities(*, cold_dm: bool, private_enabled: bool) -> FrozenSet[str]:
    if not private_enabled:
        return frozenset()
    caps = set(PRIVATE_CAPABILITIES)
    if not cold_dm:
        caps.discard(CAP_DM_INITIATE)
    return frozenset(caps)
