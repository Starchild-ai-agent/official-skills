"""Instagram skill exports.

Usage from a task script:

    import sys
    sys.path.insert(0, "/data/workspace/skills/instagram")
    from exports import instagram_auth_status, instagram_publish

    print(instagram_auth_status())
    print(instagram_publish(
        media_type="image",
        image_url="https://cdn.example.com/post.jpg",
        caption="hello",
        dry_run=False,
        confirm=True,
    ))

Every function is synchronous and returns a dict. Never call a write without a
dry run first; the service defaults ``dry_run=True`` and requires
``INSTAGRAM_ALLOW_WRITES=true`` plus ``confirm=True``.
"""

from __future__ import annotations

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from ig_service import (  # noqa: E402
    instagram_auth_status,
    instagram_business_discovery,
    instagram_capabilities,
    instagram_comment_on_media,
    instagram_connect,
    instagram_delete_comment,
    instagram_disconnect,
    instagram_get_conversation,
    instagram_get_media,
    instagram_hashtag_media,
    instagram_hashtag_usage,
    instagram_hide_comment,
    instagram_insights,
    instagram_list_comment_replies,
    instagram_list_comments,
    instagram_list_conversations,
    instagram_list_followers,
    instagram_list_following,
    instagram_list_media,
    instagram_list_messages,
    instagram_mark_seen,
    instagram_private_reply,
    instagram_profile,
    instagram_publish,
    instagram_publish_status,
    instagram_publishing_limit,
    instagram_refresh_token,
    instagram_reply_comment,
    instagram_reply_mention,
    instagram_search_hashtag,
    instagram_search_locations,
    instagram_search_posts,
    instagram_search_users,
    instagram_send_dm,
)

__all__ = [
    "instagram_connect",
    "instagram_auth_status",
    "instagram_capabilities",
    "instagram_disconnect",
    "instagram_profile",
    "instagram_list_media",
    "instagram_get_media",
    "instagram_list_comments",
    "instagram_list_comment_replies",
    "instagram_insights",
    "instagram_list_followers",
    "instagram_list_following",
    "instagram_search_hashtag",
    "instagram_hashtag_media",
    "instagram_business_discovery",
    "instagram_search_users",
    "instagram_search_locations",
    "instagram_search_posts",
    "instagram_publish",
    "instagram_publish_status",
    "instagram_publishing_limit",
    "instagram_reply_comment",
    "instagram_comment_on_media",
    "instagram_private_reply",
    "instagram_reply_mention",
    "instagram_hide_comment",
    "instagram_delete_comment",
    "instagram_list_conversations",
    "instagram_get_conversation",
    "instagram_list_messages",
    "instagram_send_dm",
    "instagram_mark_seen",
    "instagram_refresh_token",
    "instagram_hashtag_usage",
]
