"""Official Instagram Graph API backend.

Uses ``graph.facebook.com`` because hashtag search and business discovery are
only available with the Facebook Login configuration. Instagram Login tokens can
still read/publish/reply; pass ``login_type="instagram"`` to switch the host.

All methods raise ``InstagramError`` subclasses. Public service functions turn
those into structured ``{"ok": False, ...}`` replies.
"""

from __future__ import annotations

import os
import re
import time
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional

from ig_errors import (
    AuthError,
    CapabilityUnavailable,
    NotFound,
    PermissionDenied,
    ProviderError,
    RateLimitError,
    ValidationError,
)
from ig_http import request_json
from ig_models import Account
from ig_state import check_hashtag, record_hashtag, usage

DEFAULT_API_VERSION = "v26.0"

PROFILE_FIELDS = (
    "id,username,name,biography,followers_count,follows_count,media_count,"
    "profile_picture_url,website"
)
MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,media_url,permalink,thumbnail_url,"
    "timestamp,username,like_count,comments_count,children{id,media_type,media_url,permalink,thumbnail_url}"
)
COMMENT_FIELDS = (
    "id,text,timestamp,username,like_count,replies{id,text,timestamp,username,like_count}"
)
MESSAGE_FIELDS = "id,created_time,from,to,message,attachments"
CONVERSATION_FIELDS = "id,participants,updated_time,message_count"


def _chunks(values: Iterable[Any], size: int) -> Iterable[List[Any]]:
    batch: List[Any] = []
    for value in values:
        batch.append(value)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


class GraphClient:
    def __init__(self, account: Account) -> None:
        meta = account.metadata
        self.account = account
        self.access_token = str(
            meta.get("access_token") or os.environ.get("INSTAGRAM_GRAPH_TOKEN") or ""
        )
        self.page_token = str(
            meta.get("page_token") or os.environ.get("INSTAGRAM_GRAPH_PAGE_TOKEN") or ""
        )
        self.ig_user_id = str(
            meta.get("ig_user_id")
            or account.ig_user_id
            or os.environ.get("INSTAGRAM_GRAPH_USER_ID")
            or ""
        )
        self.page_id = str(
            meta.get("page_id") or account.page_id or os.environ.get("INSTAGRAM_GRAPH_PAGE_ID") or ""
        )
        self.app_id = str(meta.get("app_id") or os.environ.get("INSTAGRAM_META_APP_ID") or "")
        self.app_secret = str(
            meta.get("app_secret") or os.environ.get("INSTAGRAM_META_APP_SECRET") or ""
        )
        self.api_version = str(
            meta.get("api_version")
            or os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            or DEFAULT_API_VERSION
        )
        login_type = str(meta.get("login_type") or os.environ.get("INSTAGRAM_LOGIN_TYPE") or "facebook")
        default_host = "graph.instagram.com" if login_type == "instagram" else "graph.facebook.com"
        self.host = str(meta.get("host") or os.environ.get("INSTAGRAM_GRAPH_HOST") or default_host)
        self.username = str(meta.get("username") or "")

        if not self.access_token:
            raise AuthError(
                "No Instagram Graph access token bound to this account.",
                hint="Set INSTAGRAM_GRAPH_TOKEN or add an account with an access_token.",
            )

    # -- transport ---------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"https://{self.host}/{self.api_version}/{path.lstrip('/')}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        use_page_token: bool = False,
    ) -> Any:
        token = self.page_token if (use_page_token and self.page_token) else self.access_token
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = request_json(
                self._url(path),
                method=method,
                params=params,
                body=body,
                headers=headers,
                timeout=90,
                no_proxy=False,
            )
        except ProviderError as exc:
            # request_json already turned non-2xx into a ProviderError; parse
            # Meta's error envelope out of its details when present.
            self._raise_graph_error(exc)
            raise
        if isinstance(response, dict) and response.get("error"):
            self._raise_graph_error(response)
        return response

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(
        self,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        *,
        use_page_token: bool = False,
    ) -> Any:
        return self._request(
            "POST", path, body=body, use_page_token=use_page_token
        )

    def _delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def _raise_graph_error(self, response: Any) -> None:
        error = response
        if isinstance(response, dict) and "error" in response:
            error = response["error"]
        elif isinstance(response, ProviderError):
            details = response.details or {}
            error = details.get("body") if isinstance(details.get("body"), dict) else {}
            error = error.get("error", error) if isinstance(error, dict) else {}
        if not isinstance(error, dict):
            return

        message = str(error.get("message") or response)
        code = error.get("code")
        subcode = error.get("error_subcode")
        trace = error.get("fbtrace_id")
        details = {"code": code, "subcode": subcode, "fbtrace_id": trace}

        if subcode == 2534022:
            raise CapabilityUnavailable(
                "Instagram's 24-hour messaging window is closed for this recipient.",
                hint=(
                    "Only an inbound DM, story reply, Click-to-Direct message, or "
                    "human_agent tag opens a send window. Do not retry."
                ),
                details=details,
            )
        if code == 190:
            raise AuthError(
                "Instagram access token is invalid or expired.",
                hint="Refresh the long-lived token or reconnect the account.",
                details=details,
            )
        if code in (4, 17, 613):
            raise RateLimitError(
                "Instagram Graph API rate limit reached.",
                hint="Back off and retry later; inspect the app's call count and publishing quota.",
                details=details,
            )
        if code == 803:
            raise NotFound("Instagram object not found.", details=details)
        if code in (10, 200):
            raise PermissionDenied(
                "The bound token lacks the permission required for this operation.",
                hint="Re-authorize with the Instagram scopes/features needed for this call.",
                details=details,
            )
        if code == 100:
            raise ValidationError(
                f"Instagram rejected the request: {message}", details=details
            )
        raise ProviderError(
            f"Instagram Graph error: {message}", details=details
        )

    # -- identity ----------------------------------------------------------

    def me(self) -> Dict[str, Any]:
        return self._get("me", {"fields": "id,username"})

    def resolve_ig_user_id(self) -> str:
        if self.ig_user_id:
            return self.ig_user_id
        data = self.me()
        self.ig_user_id = str(data.get("id") or "")
        if not self.ig_user_id:
            raise AuthError("Could not resolve the Instagram professional account id.")
        return self.ig_user_id

    def resolve_page_id(self) -> str:
        if self.page_id:
            return self.page_id
        ig_user_id = self.resolve_ig_user_id()
        try:
            data = self._get(
                "me/accounts",
                {"fields": "id,name,instagram_business_account", "limit": 100},
            )
        except Exception as exc:
            raise ValidationError(
                "A Facebook Page is required for this messaging operation.",
                hint="Bind INSTAGRAM_GRAPH_PAGE_ID/INSTAGRAM_GRAPH_PAGE_TOKEN, or use Instagram Login.",
                details={"original": str(exc)},
            )
        pages = data.get("data", []) if isinstance(data, dict) else []
        for page in pages:
            linked = page.get("instagram_business_account") or {}
            if str(linked.get("id") or "") == ig_user_id:
                self.page_id = str(page.get("id"))
                return self.page_id
        if len(pages) == 1:
            self.page_id = str(pages[0].get("id"))
            return self.page_id
        raise ValidationError(
            "Could not find the Facebook Page linked to this Instagram account.",
            hint="Set INSTAGRAM_GRAPH_PAGE_ID explicitly.",
        )

    def _sender_id(self) -> str:
        return self.page_id or self.resolve_ig_user_id()

    # -- reading -----------------------------------------------------------

    def profile(self, username: Optional[str] = None) -> Dict[str, Any]:
        if username and username.lstrip("@").lower() != (self.username or "").lower():
            return self.business_discovery(username)
        return self._get(self.resolve_ig_user_id(), {"fields": PROFILE_FIELDS})

    def list_media(
        self,
        username: Optional[str] = None,
        *,
        limit: int = 25,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        limit = max(1, min(int(limit), 100))
        if username:
            if after:
                raise ValidationError("Pagination for other accounts requires business discovery fields.")
            discovery = self.business_discovery(
                username,
                fields=(
                    f"id,username,media.limit({limit})"
                    f"{{{fields or MEDIA_FIELDS}}}"
                ),
            )
            return discovery.get("media", discovery)
        return self._get(
            f"{self.resolve_ig_user_id()}/media",
            {"fields": fields or MEDIA_FIELDS, "limit": limit, "after": after},
        )

    def resolve_media_id(self, media: str) -> str:
        value = str(media).strip()
        if value.isdigit():
            return value
        if "instagram.com" in value:
            parsed = urllib.parse.urlsplit(value)
            parts = [p for p in parsed.path.split("/") if p]
            shortcode = None
            for marker in ("p", "reel", "tv"):
                if marker in parts:
                    idx = parts.index(marker)
                    if idx + 1 < len(parts):
                        shortcode = parts[idx + 1]
                        break
            if not shortcode:
                raise ValidationError(f"Could not extract a shortcode from {value!r}.")
            value = shortcode
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,}", value):
            raise ValidationError(f"Invalid media id or shortcode: {value!r}.")

        # Graph has no shortcode -> id lookup; scan the account's recent media.
        data = self._get(
            f"{self.resolve_ig_user_id()}/media",
            {"fields": "id,permalink,shortcode", "limit": 100},
        )
        for item in data.get("data", []) if isinstance(data, dict) else []:
            if item.get("shortcode") == value or value in str(item.get("permalink") or ""):
                return str(item["id"])
        raise NotFound(
            f"No recent media matched shortcode {value!r}.",
            hint="Pass the numeric IG media id, or a URL for media in the last 100 posts.",
        )

    def get_media(self, media: str, fields: Optional[str] = None) -> Dict[str, Any]:
        media_id = self.resolve_media_id(media)
        return self._get(media_id, {"fields": fields or MEDIA_FIELDS})

    def list_comments(
        self,
        media: str,
        *,
        limit: int = 50,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        media_id = self.resolve_media_id(media)
        return self._get(
            f"{media_id}/comments",
            {"fields": fields or COMMENT_FIELDS, "limit": max(1, min(int(limit), 50)), "after": after},
        )

    def list_comment_replies(
        self,
        comment_id: str,
        *,
        limit: int = 50,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._get(
            f"{comment_id}/replies",
            {"fields": fields or COMMENT_FIELDS, "limit": max(1, min(int(limit), 50)), "after": after},
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
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"metric": metric or "reach"}
        if period:
            params["period"] = period
        if metric_type:
            params["metric_type"] = metric_type
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if breakdown:
            params["breakdown"] = breakdown
        return self._get(f"{self.resolve_ig_user_id()}/insights", params)

    def hashtag_usage(self) -> Dict[str, Any]:
        return usage(self.account.label)

    def search_hashtag(self, query: str) -> Dict[str, Any]:
        tag = query.strip().lstrip("#").lower()
        if not tag or " " in tag:
            raise ValidationError("Hashtag queries must be a single token without spaces.")
        check_hashtag(self.account.label, tag)
        data = self._get(
            "ig_hashtag_search",
            {"user_id": self.resolve_ig_user_id(), "q": tag},
        )
        record_hashtag(self.account.label, tag)
        return {"query": tag, "id": data.get("id"), "quota": usage(self.account.label)}

    def hashtag_media(
        self,
        hashtag_id: str,
        *,
        mode: str = "top",
        limit: int = 25,
        after: Optional[str] = None,
        fields: Optional[str] = None,
        hashtag: Optional[str] = None,
    ) -> Dict[str, Any]:
        edge = "recent_media" if mode == "recent" else "top_media"
        if hashtag:
            check_hashtag(self.account.label, hashtag)
        data = self._get(
            f"{hashtag_id}/{edge}",
            {
                "user_id": self.resolve_ig_user_id(),
                "fields": fields or MEDIA_FIELDS,
                "limit": max(1, min(int(limit), 50)),
                "after": after,
            },
        )
        if hashtag:
            record_hashtag(self.account.label, hashtag)
        return data

    def business_discovery(
        self,
        username: str,
        *,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        handle = username.strip().lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", handle):
            raise ValidationError(f"Invalid Instagram username: {username!r}.")
        nested = fields or (
            "id,username,name,biography,followers_count,follows_count,"
            "media_count,profile_picture_url,website"
        )
        data = self._get(
            self.resolve_ig_user_id(),
            {"fields": f"business_discovery.username({handle}){{{nested}}}"},
        )
        discovery = data.get("business_discovery") if isinstance(data, dict) else None
        if not discovery:
            raise NotFound(
                f"Business discovery returned no data for @{handle}.",
                hint="Only public Instagram professional accounts are discoverable.",
            )
        return discovery

    # -- publishing --------------------------------------------------------

    def _create_container(self, params: Dict[str, Any]) -> str:
        data = self._post(f"{self.resolve_ig_user_id()}/media", params)
        container_id = str(data.get("id") or "")
        if not container_id:
            raise ProviderError("Instagram did not return a media container id.")
        return container_id

    def container_status(self, container_id: str) -> Dict[str, Any]:
        return self._get(container_id, {"fields": "status_code,status"})

    def wait_for_container(self, container_id: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        deadline = time.time() + int(
            timeout or os.environ.get("INSTAGRAM_CONTAINER_TIMEOUT", "180")
        )
        last: Dict[str, Any] = {}
        while time.time() < deadline:
            last = self._get(container_id, {"fields": "status_code,status"})
            status = str(last.get("status_code") or "")
            if status == "FINISHED":
                return last
            if status in {"ERROR", "EXPIRED"}:
                raise ProviderError(
                    f"Instagram media container failed with status {status}.",
                    details={"container_id": container_id, "response": last},
                )
            time.sleep(3)
        raise ProviderError(
            "Timed out waiting for the Instagram media container.",
            details={"container_id": container_id, "last": last},
        )

    def publish_container(self, container_id: str) -> Dict[str, Any]:
        data = self._post(
            f"{self.resolve_ig_user_id()}/media_publish",
            {"creation_id": container_id},
        )
        return data

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
        base: Dict[str, Any] = {}
        if caption:
            base["caption"] = caption
        if alt_text and media_type == "image":
            base["alt_text"] = alt_text
        if is_ai_generated:
            base["is_ai_generated"] = "true"

        if media_type == "carousel":
            if not carousel_items or not (2 <= len(carousel_items) <= 10):
                raise ValidationError("Carousels require 2-10 image/video items.")
            child_ids: List[str] = []
            for item in carousel_items:
                child = {**base, "is_carousel_item": "true"}
                child.pop("caption", None)
                child.pop("is_ai_generated", None)
                if item.get("image_url"):
                    child["image_url"] = item["image_url"]
                elif item.get("video_url"):
                    child["media_type"] = "VIDEO"
                    child["video_url"] = item["video_url"]
                else:
                    raise ValidationError("Each carousel item needs image_url or video_url.")
                if extra:
                    child.update(extra)
                child_ids.append(self._create_container(child))
            parent = {
                **base,
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
            }
            if extra:
                parent.update(extra)
            container_id = self._create_container(parent)
            self.wait_for_container(container_id)
            return self.publish_container(container_id)

        if media_type == "reel":
            if not video_url:
                raise ValidationError("Reels require video_url.")
            params = {
                **base,
                "media_type": "REELS",
                "video_url": video_url,
                "share_to_feed": "true" if share_to_feed else "false",
            }
        elif media_type == "story":
            params = {**base, "media_type": "STORIES"}
            if image_url:
                params["image_url"] = image_url
            elif video_url:
                params["video_url"] = video_url
            else:
                raise ValidationError("Stories require image_url or video_url.")
        elif media_type == "video":
            if not video_url:
                raise ValidationError("Video posts require video_url.")
            params = {**base, "media_type": "VIDEO", "video_url": video_url}
        elif media_type == "image":
            if not image_url:
                raise ValidationError("Image posts require image_url.")
            params = {**base, "image_url": image_url}
        else:
            raise ValidationError(f"Unsupported media_type: {media_type!r}.")

        if extra:
            params.update(extra)
        container_id = self._create_container(params)
        self.wait_for_container(container_id)
        result = self.publish_container(container_id)
        result["container_id"] = container_id
        return result

    def publishing_limit(self) -> Dict[str, Any]:
        return self._get(
            f"{self.resolve_ig_user_id()}/content_publishing_limit",
            {"fields": "quota_usage,config"},
        )

    # -- comments ----------------------------------------------------------

    def reply_comment(self, comment_id: str, text: str) -> Dict[str, Any]:
        return self._post(f"{comment_id}/replies", {"message": text})

    def comment_on_media(self, media: str, text: str) -> Dict[str, Any]:
        media_id = self.resolve_media_id(media)
        return self._post(f"{media_id}/comments", {"message": text})

    def reply_mention(self, media: str, text: str) -> Dict[str, Any]:
        return self.comment_on_media(media, text)

    def hide_comment(self, comment_id: str, hide: bool = True) -> Dict[str, Any]:
        return self._request(
            "POST",
            comment_id,
            params={"hide": "true" if hide else "false"},
        )

    def delete_comment(self, comment_id: str) -> Dict[str, Any]:
        return self._delete(comment_id)

    # -- messaging ---------------------------------------------------------

    def private_reply(self, comment_id: str, text: str) -> Dict[str, Any]:
        if not self.page_id:
            self.resolve_page_id()
        return self._post(
            f"{self.page_id}/messages",
            {
                "recipient": {"comment_id": comment_id},
                "message": {"text": text},
            },
            use_page_token=True,
        )

    def conversations(
        self,
        *,
        limit: int = 20,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._get(
            f"{self._sender_id()}/conversations",
            {
                "platform": "instagram",
                "fields": fields or CONVERSATION_FIELDS,
                "limit": max(1, min(int(limit), 100)),
                "after": after,
            },
        )

    def conversation(self, conversation_id: str) -> Dict[str, Any]:
        return self._get(conversation_id, {"fields": CONVERSATION_FIELDS})

    def messages(
        self,
        conversation_id: str,
        *,
        limit: int = 20,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._get(
            f"{conversation_id}/messages",
            {
                "fields": fields or MESSAGE_FIELDS,
                "limit": max(1, min(int(limit), 100)),
                "after": after,
            },
        )

    def _recipient_from_conversation(self, conversation_id: str) -> str:
        data = self.conversation(conversation_id)
        participants = data.get("participants", [])
        if isinstance(participants, dict):
            participants = participants.get("data", [])
        self_id = self.resolve_ig_user_id()
        for participant in participants:
            pid = str(participant.get("id") or "")
            if pid and pid != self_id and pid != self.page_id:
                return pid
        raise ValidationError(
            "Could not determine the other participant in this conversation.",
            details={"conversation_id": conversation_id},
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
        if not text and not image_url:
            raise ValidationError("send_dm needs text or image_url.")

        message: Dict[str, Any] = {}
        if image_url:
            message["attachment"] = {"type": "image", "payload": {"url": image_url}}
        else:
            message["text"] = text

        return self._post(
            f"{self._sender_id()}/messages",
            {"recipient": {"id": recipient_id}, "message": message},
            use_page_token=True,
        )

    def mark_seen(self, recipient_id: str) -> Dict[str, Any]:
        return self._post(
            f"{self._sender_id()}/messages",
            {"recipient": {"id": recipient_id}, "sender_action": "mark_seen"},
            use_page_token=True,
        )

    # -- auth --------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        return self.me()

    def refresh_token(self) -> Dict[str, Any]:
        if not (self.app_id and self.app_secret):
            raise ValidationError(
                "Token refresh needs INSTAGRAM_META_APP_ID and INSTAGRAM_META_APP_SECRET."
            )
        return request_json(
            f"https://{self.host}/{self.api_version}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": self.access_token,
            },
            timeout=30,
            no_proxy=False,
        )
