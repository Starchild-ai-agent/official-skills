"""Composio Instagram adapter.

The shipped ``composio`` skill documents two important environment quirks:

1. The documented ``INSTAGRAM_POST_IG_USER_MEDIA`` slugs may return
   "Tool ... not found"; the working pair is
   ``INSTAGRAM_CREATE_MEDIA_CONTAINER`` + ``INSTAGRAM_CREATE_POST``.
2. Execute takes ``arguments`` (not ``params``).

Every call goes through ``GatewayClient.call`` so provider schemas can rename a
canonical argument without breaking the skill.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ig_errors import CapabilityUnavailable, ProviderError, ValidationError
from ig_gateway import GatewayClient
from ig_models import Account

MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,media_url,permalink,thumbnail_url,"
    "timestamp,username,like_count,comments_count,children{id,media_type,media_url,permalink,thumbnail_url}"
)
COMMENT_FIELDS = "id,text,timestamp,username,like_count,replies{id,text,timestamp,username,like_count}"
MESSAGE_FIELDS = "id,created_time,from,to,message,attachments"
CONVERSATION_FIELDS = "id,participants,updated_time,message_count"


def _id_of(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        for key in ("id", "creation_id", "container_id"):
            if value.get(key):
                return str(value[key])
        if isinstance(value.get("data"), dict):
            return _id_of(value["data"])
    return None


class ComposioBackend:
    def __init__(self, account: Account) -> None:
        self.account = account
        self.gateway = GatewayClient()
        self.ig_user_id = str(
            account.ig_user_id
            or account.metadata.get("ig_user_id")
            or os.environ.get("INSTAGRAM_IG_USER_ID")
            or ""
        )

    # -- helpers -----------------------------------------------------------

    def _ensure_ig_user_id(self) -> str:
        if self.ig_user_id:
            return self.ig_user_id
        data = self.gateway.call(
            "INSTAGRAM_GET_USER_INFO",
            {"ig_user_id": "me"},
        )
        resolved = _id_of(data)
        if not resolved:
            raise ProviderError(
                "Composio did not return an Instagram user id.",
                hint="Connect a Business/Creator account in Composio.",
            )
        self.ig_user_id = resolved
        return resolved

    def _media_id(self, media: str) -> str:
        value = str(media).strip()
        if value.isdigit():
            return value
        raise ValidationError(
            "Composio tools address media by numeric IG media id.",
            hint="Pass the numeric id, or use the Graph/private backend for shortcodes and URLs.",
        )

    def _recipient_from_conversation(self, conversation_id: str) -> str:
        data = self.conversation(conversation_id)
        participants = data.get("participants", [])
        if isinstance(participants, dict):
            participants = participants.get("data", []) if isinstance(data, dict) else []
        self_id = self._ensure_ig_user_id()
        for participant in participants:
            pid = str(participant.get("id") or "")
            if pid and pid != self_id:
                return pid
        raise ValidationError(
            "Could not determine the other participant in this conversation.",
            details={"conversation_id": conversation_id},
        )

    # -- reading -----------------------------------------------------------

    def profile(self, username: Optional[str] = None) -> Dict[str, Any]:
        if username:
            raise CapabilityUnavailable(
                "Composio's Instagram toolkit has no business-discovery/search tool.",
                hint="Bind a Graph account with business discovery, or use the private backend.",
            )
        return self.gateway.call(
            "INSTAGRAM_GET_USER_INFO",
            {"ig_user_id": self._ensure_ig_user_id()},
        )

    def list_media(
        self,
        username: Optional[str] = None,
        *,
        limit: int = 25,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        if username:
            raise CapabilityUnavailable("Composio cannot list another account's media.")
        return self.gateway.call(
            "INSTAGRAM_GET_IG_USER_MEDIA",
            {
                "ig_user_id": self._ensure_ig_user_id(),
                "fields": fields or MEDIA_FIELDS,
                "limit": int(limit),
                "after": after,
            },
        )

    def get_media(self, media: str, fields: Optional[str] = None) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_GET_IG_MEDIA",
            {"ig_media_id": self._media_id(media), "fields": fields or MEDIA_FIELDS},
        )

    def list_comments(
        self,
        media: str,
        *,
        limit: int = 50,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_GET_IG_MEDIA_COMMENTS",
            {
                "ig_media_id": self._media_id(media),
                "limit": int(limit),
                "after": after,
                "fields": fields or COMMENT_FIELDS,
            },
        )

    def list_comment_replies(
        self,
        comment_id: str,
        *,
        limit: int = 50,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_GET_IG_COMMENT_REPLIES",
            {
                "ig_comment_id": comment_id,
                "limit": int(limit),
                "after": after,
                "fields": fields or COMMENT_FIELDS,
            },
        )

    def insights(
        self,
        *,
        metric: Optional[str] = None,
        period: Optional[str] = None,
        metric_type: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        breakdown: Optional[str] = None,
        media: Optional[str] = None,
    ) -> Dict[str, Any]:
        if media:
            return self.gateway.call(
                "INSTAGRAM_GET_IG_MEDIA_INSIGHTS",
                {"ig_media_id": self._media_id(media), "metric": metric},
            )
        return self.gateway.call(
            "INSTAGRAM_GET_USER_INSIGHTS",
            {
                "ig_user_id": self._ensure_ig_user_id(),
                "metric": metric,
                "period": period,
                "metric_type": metric_type,
                "since": since,
                "until": until,
                "breakdown": breakdown,
            },
        )

    def list_followers(
        self, username: Optional[str] = None, *, limit: int = 50, after: Optional[str] = None
    ) -> Dict[str, Any]:
        raise CapabilityUnavailable("Composio's Instagram toolkit does not expose follower lists.")

    def list_following(
        self, username: Optional[str] = None, *, limit: int = 50, after: Optional[str] = None
    ) -> Dict[str, Any]:
        raise CapabilityUnavailable("Composio's Instagram toolkit does not expose following lists.")

    # -- publishing --------------------------------------------------------

    def _create_container(self, arguments: Dict[str, Any]) -> str:
        try:
            data = self.gateway.call("INSTAGRAM_CREATE_MEDIA_CONTAINER", arguments)
            container_id = _id_of(data)
            if container_id:
                return container_id
            raise ProviderError("Composio returned no container id.", details={"response": data})
        except Exception as first_error:
            # Fallback to the newer documented slugs when the gateway does not
            # expose the legacy pair.
            try:
                data = self.gateway.call("INSTAGRAM_POST_IG_USER_MEDIA", arguments)
                container_id = _id_of(data)
                if container_id:
                    return container_id
                raise ProviderError("Composio returned no container id.", details={"response": data})
            except Exception:
                raise first_error

    def _publish_container(self, container_id: str) -> Dict[str, Any]:
        arguments = {
            "ig_user_id": self._ensure_ig_user_id(),
            "creation_id": container_id,
        }
        try:
            return self.gateway.call("INSTAGRAM_CREATE_POST", arguments)
        except Exception as first_error:
            try:
                return self.gateway.call("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", arguments)
            except Exception:
                raise first_error

    def publish(
        self,
        *,
        media_type: str = "image",
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
        caption: str = "",
        carousel_items: Optional[List[Dict[str, str]]] = None,
        alt_text: Optional[str] = None,
        is_ai_generated: bool = False,
        share_to_feed: bool = True,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        media_type = media_type.lower()
        if media_type == "carousel":
            raise CapabilityUnavailable(
                "Composio carousel args vary by gateway version; use Graph or private for carousels.",
                hint="Instagram carousels need 2-10 child containers.",
            )
        if media_type not in {"image", "video", "reel", "story"}:
            raise ValidationError(f"Unsupported media_type: {media_type!r}")

        arguments: Dict[str, Any] = {
            "ig_user_id": self._ensure_ig_user_id(),
            "caption": caption,
        }
        if image_url:
            arguments["image_url"] = image_url
        if video_url:
            arguments["video_url"] = video_url
        if media_type == "image":
            arguments["content_type"] = "photo"
        elif media_type in {"video", "reel"}:
            arguments["content_type"] = media_type
        elif media_type == "story":
            arguments["content_type"] = "story"
            arguments["media_type"] = "STORIES"
        if alt_text and media_type == "image":
            arguments["alt_text"] = alt_text
        if is_ai_generated:
            arguments["is_ai_generated"] = True
        if extra:
            arguments.update(extra)

        container_id = self._create_container(arguments)
        result = self._publish_container(container_id)
        if isinstance(result, dict):
            result.setdefault("container_id", container_id)
        return result

    def publishing_limit(self) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_GET_IG_USER_CONTENT_PUBLISHING_LIMIT",
            {"ig_user_id": self._ensure_ig_user_id()},
        )

    # -- comments ----------------------------------------------------------

    def reply_comment(self, comment_id: str, text: str) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_POST_IG_COMMENT_REPLIES",
            {"ig_comment_id": comment_id, "message": text},
        )

    def comment_on_media(self, media: str, text: str) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_POST_IG_MEDIA_COMMENTS",
            {"ig_media_id": self._media_id(media), "message": text},
        )

    def reply_mention(self, media: str, text: str) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_POST_IG_USER_MENTIONS",
            {"ig_media_id": self._media_id(media), "message": text},
        )

    def hide_comment(self, comment_id: str, hide: bool = True) -> Dict[str, Any]:
        raise CapabilityUnavailable(
            "Composio exposes delete and comment-disable, but not hide/unhide for one comment."
        )

    def delete_comment(self, comment_id: str) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_DELETE_COMMENT",
            {"ig_comment_id": comment_id},
        )

    # -- messaging ---------------------------------------------------------

    def conversations(
        self,
        *,
        limit: int = 20,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_LIST_ALL_CONVERSATIONS",
            {
                "ig_user_id": self._ensure_ig_user_id(),
                "limit": int(limit),
                "after": after,
                "fields": fields or CONVERSATION_FIELDS,
            },
        )

    def conversation(self, conversation_id: str) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_GET_CONVERSATION",
            {"conversation_id": conversation_id, "fields": CONVERSATION_FIELDS},
        )

    def messages(
        self,
        conversation_id: str,
        *,
        limit: int = 20,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_LIST_ALL_MESSAGES",
            {
                "conversation_id": conversation_id,
                "limit": int(limit),
                "after": after,
                "fields": fields or MESSAGE_FIELDS,
            },
        )

    def send_dm(
        self,
        *,
        text: Optional[str] = None,
        image_url: Optional[str] = None,
        recipient_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not recipient_id and conversation_id:
            recipient_id = self._recipient_from_conversation(conversation_id)
        if not recipient_id:
            raise ValidationError("send_dm needs recipient_id or conversation_id.")
        if image_url:
            return self.gateway.call(
                "INSTAGRAM_SEND_IMAGE",
                {"recipient_id": recipient_id, "image_url": image_url},
            )
        if not text:
            raise ValidationError("send_dm needs text or image_url.")
        return self.gateway.call(
            "INSTAGRAM_SEND_TEXT_MESSAGE",
            {"recipient_id": recipient_id, "message": text},
        )

    def mark_seen(self, recipient_id: str) -> Dict[str, Any]:
        return self.gateway.call(
            "INSTAGRAM_MARK_SEEN",
            {"recipient_id": recipient_id},
        )

    def private_reply(self, comment_id: str, text: str) -> Dict[str, Any]:
        raise CapabilityUnavailable(
            "Composio has no public private-reply tool.",
            hint="Use a Graph account with a Page token, or reply in an existing DM thread.",
        )

    def validate(self) -> Dict[str, Any]:
        return self.profile()

    def refresh_token(self) -> Dict[str, Any]:
        raise CapabilityUnavailable("Composio manages token refresh.")
