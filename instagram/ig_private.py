"""Optional instagrapi backend.

This is the only backend that can search people/locations/posts and initiate a
new DM. It authenticates with an Instagram session, not OAuth, so it is opt-in
and intended for single-tenant/internal use. Instagram ToS and account-ban risk
apply; the router never selects it for a capability an official account can
already satisfy unless the caller explicitly asks for it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import os
import struct
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ig_errors import (
    AuthError,
    CapabilityUnavailable,
    NotFound,
    ProviderError,
    RateLimitError,
    ValidationError,
)
from ig_models import Account


def _totp(secret: str, *, digits: int = 6, period: int = 30) -> str:
    raw = secret.strip().replace(" ", "").upper()
    padding = "=" * ((8 - len(raw) % 8) % 8)
    key = base64.b32decode(raw + padding)
    counter = int(time.time() // period)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def _media_pk_from_any(client: Any, media: str) -> int:
    value = str(media).strip()
    if value.isdigit():
        return int(value)
    if "instagram.com" in value:
        return int(client.media_pk_from_url(value))
    try:
        return int(client.media_pk_from_code(value))
    except Exception as exc:
        raise ValidationError(
            f"Could not resolve Instagram media {media!r}.",
            hint="Pass a numeric pk, shortcode, or instagram.com URL.",
            details={"original": str(exc)},
        )


def _user_pk(client: Any, user: str) -> int:
    value = str(user).strip().lstrip("@")
    if value.isdigit():
        return int(value)
    try:
        return int(client.user_id_from_username(value))
    except Exception as exc:
        raise NotFound(f"Instagram user @{value} was not found.", details={"original": str(exc)})


def _map_private_error(exc: Exception) -> Exception:
    name = type(exc).__name__
    message = str(exc)
    lowered = message.lower()
    details = {"type": name, "original": message[:500]}
    if name in {"ChallengeRequired", "ChallengeError", "LoginRequired", "ReloginAttemptExceeded"}:
        return AuthError(
            "Instagram requires a fresh login or a challenge check.",
            hint="Open Instagram, finish the challenge, then create a new session file.",
            details=details,
        )
    if name in {"PleaseWaitFewMinutes", "RateLimitError", "ClientThrottledError"} or "wait a few minutes" in lowered:
        return RateLimitError(
            "Instagram asked this account to slow down.",
            hint="Stop the run, raise the delay, and retry later. Do not loop.",
            details=details,
        )
    if name in {"ActionBlocked", "FeedbackRequired"} or "action blocked" in lowered:
        return RateLimitError(
            "Instagram blocked this action for the account.",
            hint="Stop automation for this account; it is at risk.",
            details=details,
        )
    if name in {"UserNotFound", "MediaNotFound", "CommentNotFound"}:
        return NotFound(message, details=details)
    return ProviderError(f"instagrapi error: {message}", details=details)


class PrivateClient:
    def __init__(self, account: Account) -> None:
        if importlib.util.find_spec("instagrapi") is None:
            raise AuthError(
                "The private backend requires instagrapi.",
                hint="pip install instagrapi, or use the Composio/Graph backend.",
            )
        self.account = account
        meta = account.metadata
        self.username = str(meta.get("username") or os.environ.get("INSTAGRAM_USERNAME") or "")
        self.password = str(meta.get("password") or os.environ.get("INSTAGRAM_PASSWORD") or "")
        self.sessionid = str(meta.get("sessionid") or os.environ.get("INSTAGRAM_SESSIONID") or "")
        self.verification_code = str(
            meta.get("verification_code") or os.environ.get("INSTAGRAM_VERIFICATION_CODE") or ""
        )
        self.totp_seed = str(
            meta.get("totp_seed") or os.environ.get("INSTAGRAM_TOTP_SEED") or ""
        )
        self.proxy = str(meta.get("proxy") or os.environ.get("INSTAGRAM_PROXY") or "")
        self.session_file = str(
            meta.get("session_file")
            or account.session_file
            or os.environ.get("INSTAGRAM_SESSION_FILE")
            or (Path.home() / ".starchild" / "instagram" / "session.json")
        )
        self._client: Any = None

    # -- login -------------------------------------------------------------

    def _load(self) -> Any:
        if self._client is not None:
            return self._client
        from instagrapi import Client  # lazy: optional dependency

        client = Client()
        if self.proxy:
            try:
                client.set_proxy(self.proxy)
            except Exception:
                pass
        delay_min = float(os.environ.get("INSTAGRAM_DELAY_MIN", "3"))
        delay_max = float(os.environ.get("INSTAGRAM_DELAY_MAX", "8"))
        if hasattr(client, "delay_range"):
            client.delay_range = [delay_min, max(delay_min, delay_max)]

        session_path = Path(self.session_file).expanduser()
        if session_path.exists():
            try:
                client.load_settings(str(session_path))
            except Exception:
                pass

        try:
            if self.sessionid:
                client.login_by_sessionid(self.sessionid)
            elif self.username and self.password:
                code = self.verification_code
                if not code and self.totp_seed:
                    code = _totp(self.totp_seed)
                client.login(self.username, self.password, verification_code=code or "")
            elif session_path.exists():
                # A dumped session is enough for read-only calls in many cases.
                pass
            else:
                raise AuthError(
                    "No Instagram private credentials are bound.",
                    hint=(
                        "Set INSTAGRAM_USERNAME + INSTAGRAM_PASSWORD, "
                        "INSTAGRAM_SESSIONID, or INSTAGRAM_SESSION_FILE."
                    ),
                )
        except AuthError:
            raise
        except Exception as exc:
            raise _map_private_error(exc)

        try:
            session_path.parent.mkdir(parents=True, exist_ok=True)
            client.dump_settings(str(session_path))
            session_path.chmod(0o600)
        except Exception:
            pass

        self._client = client
        return client

    # -- reading -----------------------------------------------------------

    def _safe(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            raise _map_private_error(exc)

    def profile(self, username: Optional[str] = None) -> Dict[str, Any]:
        client = self._load()
        if not username:
            info = self._safe(client.account_info)
        else:
            info = self._safe(client.user_info_by_username, username.lstrip("@"))
        return info.dict() if hasattr(info, "dict") else info

    def list_media(
        self,
        username: Optional[str] = None,
        *,
        limit: int = 25,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        if after:
            raise ValidationError("The private backend does not use Graph cursors.")
        client = self._load()
        user_id = _user_pk(client, username) if username else int(client.user_id)
        medias = self._safe(client.user_medias, user_id, amount=int(limit))
        return {"data": [m.dict() if hasattr(m, "dict") else m for m in medias]}

    def get_media(self, media: str, fields: Optional[str] = None) -> Dict[str, Any]:
        client = self._load()
        info = self._safe(client.media_info, _media_pk_from_any(client, media))
        return info.dict() if hasattr(info, "dict") else info

    def list_comments(
        self,
        media: str,
        *,
        limit: int = 50,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        if after:
            raise ValidationError("The private backend does not use Graph cursors.")
        client = self._load()
        pk = _media_pk_from_any(client, media)
        comments = self._safe(client.media_comments, pk, amount=int(limit))
        return {"data": [c.dict() if hasattr(c, "dict") else c for c in comments]}

    def list_comment_replies(
        self,
        comment_id: str,
        *,
        media: Optional[str] = None,
        limit: int = 50,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not media:
            raise ValidationError(
                "The private backend needs the parent media id to list replies.",
                hint="Pass media=<post pk/shortcode/url> alongside comment_id.",
            )
        client = self._load()
        pk = _media_pk_from_any(client, media)
        replies = self._safe(client.media_comment_replies, pk, comment_id, amount=int(limit))
        return {"data": [c.dict() if hasattr(c, "dict") else c for c in replies]}

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
        client = self._load()
        if media:
            pk = _media_pk_from_any(client, media)
            return self._safe(client.insights_media, pk)
        if hasattr(client, "insights_account"):
            return self._safe(client.insights_account)
        raise CapabilityUnavailable("This instagrapi version exposes no account insights.")

    def list_followers(
        self, username: Optional[str] = None, *, limit: int = 50, after: Optional[str] = None
    ) -> Dict[str, Any]:
        client = self._load()
        user_id = _user_pk(client, username) if username else int(client.user_id)
        users = self._safe(client.user_followers, user_id, amount=int(limit))
        data = users.values() if isinstance(users, dict) else users
        return {"data": [u.dict() if hasattr(u, "dict") else u for u in data]}

    def list_following(
        self, username: Optional[str] = None, *, limit: int = 50, after: Optional[str] = None
    ) -> Dict[str, Any]:
        client = self._load()
        user_id = _user_pk(client, username) if username else int(client.user_id)
        users = self._safe(client.user_following, user_id, amount=int(limit))
        data = users.values() if isinstance(users, dict) else users
        return {"data": [u.dict() if hasattr(u, "dict") else u for u in data]}

    # -- search ------------------------------------------------------------

    def search_users(self, query: str, *, limit: int = 20) -> Dict[str, Any]:
        client = self._load()
        users = self._safe(client.search_users, query)
        data = [u.dict() if hasattr(u, "dict") else u for u in list(users)[: int(limit)]]
        return {"data": data}

    def search_hashtags(self, query: str) -> Dict[str, Any]:
        client = self._load()
        tags = self._safe(client.search_hashtags, query)
        return {"data": [t.dict() if hasattr(t, "dict") else t for t in tags]}

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
        client = self._load()
        tag = hashtag or hashtag_id
        method = client.hashtag_medias_recent if mode == "recent" else client.hashtag_medias_top
        medias = self._safe(method, tag, amount=int(limit))
        return {"data": [m.dict() if hasattr(m, "dict") else m for m in medias]}

    def search_locations(self, query: str, *, limit: int = 20) -> Dict[str, Any]:
        client = self._load()
        places = self._safe(client.location_search_name, query)
        return {"data": [p.dict() if hasattr(p, "dict") else p for p in list(places)[: int(limit)]]}

    def search_posts(self, query: str, *, limit: int = 20) -> Dict[str, Any]:
        client = self._load()
        if hasattr(client, "media_search"):
            medias = self._safe(client.media_search, query, amount=int(limit))
            return {"data": [m.dict() if hasattr(m, "dict") else m for m in medias]}
        if hasattr(client, "fbsearch_topsearch_v2"):
            return self._safe(client.fbsearch_topsearch_v2, query)
        raise CapabilityUnavailable("This instagrapi version exposes no post search.")

    # -- publishing --------------------------------------------------------

    def _ensure_local(self, value: str, kind: str = "media") -> Tuple[str, bool]:
        if not value:
            raise ValidationError(f"{kind} path/url is required.")
        if not str(value).startswith(("http://", "https://")):
            if not Path(value).exists():
                raise ValidationError(f"Local {kind} file does not exist: {value}")
            return str(value), False
        suffix = Path(urllib.parse.urlsplit(value).path).suffix or (".mp4" if kind == "video" else ".jpg")
        handle = tempfile.NamedTemporaryFile(prefix="instagram-", suffix=suffix, delete=False)
        try:
            with urllib.request.urlopen(value, timeout=120) as response:
                handle.write(response.read())
        finally:
            handle.close()
        return handle.name, True

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
        client = self._load()
        media_type = media_type.lower()
        temporary: List[str] = []
        try:
            if media_type == "carousel":
                if not carousel_items or not (2 <= len(carousel_items) <= 10):
                    raise ValidationError("Carousels require 2-10 image/video items.")
                paths: List[str] = []
                for item in carousel_items:
                    raw = item.get("image_url") or item.get("video_url") or ""
                    path, temp = self._ensure_local(raw, "media")
                    paths.append(path)
                    if temp:
                        temporary.append(path)
                result = self._safe(client.album_upload, paths, caption)
            elif media_type == "story":
                raw = image_url or video_url
                path, temp = self._ensure_local(raw, "media")
                if temp:
                    temporary.append(path)
                if video_url:
                    result = self._safe(client.video_upload_to_story, path, caption)
                else:
                    result = self._safe(client.photo_upload_to_story, path, caption)
            else:
                raw = video_url if media_type in {"video", "reel"} else image_url
                path, temp = self._ensure_local(raw, "video" if media_type in {"video", "reel"} else "image")
                if temp:
                    temporary.append(path)
                if media_type == "reel":
                    result = self._safe(client.clip_upload, path, caption)
                elif media_type == "video":
                    result = self._safe(client.video_upload, path, caption)
                else:
                    result = self._safe(client.photo_upload, path, caption)
            return result.dict() if hasattr(result, "dict") else result
        finally:
            for path in temporary:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    # -- comments ----------------------------------------------------------

    def reply_comment(
        self, comment_id: str, text: str, *, media: Optional[str] = None
    ) -> Dict[str, Any]:
        if not media:
            raise ValidationError(
                "The private backend needs the parent media id to reply to a comment.",
                hint="Pass media=<post pk/shortcode/url>.",
            )
        client = self._load()
        pk = _media_pk_from_any(client, media)
        result = self._safe(
            client.media_comment,
            pk,
            text,
            replied_to_comment_id=int(comment_id),
        )
        return result.dict() if hasattr(result, "dict") else result

    def comment_on_media(self, media: str, text: str) -> Dict[str, Any]:
        client = self._load()
        result = self._safe(client.media_comment, _media_pk_from_any(client, media), text)
        return result.dict() if hasattr(result, "dict") else result

    def reply_mention(self, media: str, text: str) -> Dict[str, Any]:
        return self.comment_on_media(media, text)

    def hide_comment(self, comment_id: str, hide: bool = True) -> Dict[str, Any]:
        raise CapabilityUnavailable(
            "The private backend does not expose hide/unhide; use Graph or the app.",
        )

    def delete_comment(
        self, comment_id: str, *, media: Optional[str] = None
    ) -> Dict[str, Any]:
        if not media:
            raise ValidationError(
                "The private backend needs the parent media id to delete a comment.",
                hint="Pass media=<post pk/shortcode/url>.",
            )
        client = self._load()
        pk = _media_pk_from_any(client, media)
        result = self._safe(client.comment_bulk_delete, pk, [int(comment_id)])
        return {"deleted": bool(result)}

    # -- messaging ---------------------------------------------------------

    def conversations(self, *, limit: int = 20, after: Optional[str] = None) -> Dict[str, Any]:
        client = self._load()
        threads = self._safe(client.direct_threads, amount=int(limit))
        return {"data": [t.dict() if hasattr(t, "dict") else t for t in threads]}

    def conversation(self, conversation_id: str) -> Dict[str, Any]:
        client = self._load()
        thread = self._safe(client.direct_thread, int(conversation_id))
        return thread.dict() if hasattr(thread, "dict") else thread

    def messages(
        self,
        conversation_id: str,
        *,
        limit: int = 20,
        after: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = self._load()
        messages = self._safe(client.direct_messages, int(conversation_id), amount=int(limit))
        return {"data": [m.dict() if hasattr(m, "dict") else m for m in messages]}

    def send_dm(
        self,
        *,
        text: Optional[str] = None,
        image_url: Optional[str] = None,
        recipient_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not text and not image_url:
            raise ValidationError("send_dm needs text or image_url.")
        client = self._load()
        thread_ids = [int(conversation_id)] if conversation_id else []
        user_ids = [_user_pk(client, recipient_id)] if recipient_id else []
        if not thread_ids and not user_ids:
            raise ValidationError("send_dm needs recipient_id or conversation_id.")
        recipient_kwargs = (
            {"thread_ids": thread_ids} if thread_ids else {"user_ids": user_ids}
        )
        if image_url:
            path, temp = self._ensure_local(image_url, "image")
            try:
                result = self._safe(
                    client.direct_send_photo,
                    path,
                    **recipient_kwargs,
                )
            finally:
                if temp:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
        elif conversation_id:
            result = self._safe(client.direct_answer, int(conversation_id), text)
        else:
            result = self._safe(client.direct_send, text, user_ids=user_ids)
        return result.dict() if hasattr(result, "dict") else result

    def mark_seen(self, recipient_id: str) -> Dict[str, Any]:
        raise CapabilityUnavailable(
            "instagrapi exposes no stable mark-seen primitive; the read receipt stays unchanged.",
        )
