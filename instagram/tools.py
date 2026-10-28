"""BaseTool wrappers for the Instagram skill.

The exports surface is the primary contract; these classes expose the same
functions in tool-mode. Write tools keep ``dry_run``/``confirm`` in their JSON
schema so the model can show a plan before execution.
"""

from __future__ import annotations

import asyncio
import logging

from core.tool import BaseTool, ToolContext, ToolResult

from .ig_service import (
    instagram_auth_status,
    instagram_capabilities,
    instagram_connect,
    instagram_get_conversation,
    instagram_list_comments,
    instagram_list_conversations,
    instagram_list_media,
    instagram_list_messages,
    instagram_profile,
    instagram_publish,
    instagram_reply_comment,
    instagram_search_hashtag,
    instagram_search_users,
    instagram_send_dm,
)

logger = logging.getLogger(__name__)


class _InstagramTool(BaseTool):
    func = None
    tool_name = ""
    tool_description = ""
    tool_parameters = {}

    @property
    def name(self) -> str:
        return self.tool_name

    @property
    def description(self) -> str:
        return self.tool_description

    @property
    def parameters(self) -> dict:
        return self.tool_parameters

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            result = await asyncio.to_thread(self.func, **kwargs)
            return ToolResult(success=bool(result.get("ok")), output=result, error=None if result.get("ok") else result.get("error", {}).get("message"))
        except Exception as exc:
            logger.exception("instagram tool failed: %s", exc)
            return ToolResult(success=False, error=str(exc))


class InstagramAuthStatusTool(_InstagramTool):
    func = staticmethod(instagram_auth_status)
    tool_name = "instagram_auth_status"
    tool_description = "List bound Instagram credentials, their auth kind, and supported capabilities. Call this before any other Instagram tool."
    tool_parameters = {
        "type": "object",
        "properties": {
            "account": {"type": "string", "description": "Optional account label."},
        },
    }


class InstagramCapabilitiesTool(_InstagramTool):
    func = staticmethod(instagram_capabilities)
    tool_name = "instagram_capabilities"
    tool_description = "Return the capability matrix and onboarding options for missing capabilities."
    tool_parameters = {
        "type": "object",
        "properties": {
            "account": {"type": "string", "description": "Optional account label."},
        },
    }


class InstagramConnectTool(_InstagramTool):
    func = staticmethod(instagram_connect)
    tool_name = "instagram_connect"
    tool_description = "Start the smallest auth flow that unlocks a capability. Prefers already-bound credentials; never starts a second authorization unnecessarily."
    tool_parameters = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "enum": ["auto", "composio", "graph", "private"], "default": "auto"},
            "capability": {"type": "string", "description": "Capability to unlock, e.g. search_users, search_hashtag, comment_private_reply."},
            "account": {"type": "string"},
            "confirm": {"type": "boolean", "default": False, "description": "Required for private login."},
        },
    }


class InstagramProfileTool(_InstagramTool):
    func = staticmethod(instagram_profile)
    tool_name = "instagram_profile"
    tool_description = "Read the bound account's profile, or a public professional account by username (Graph business discovery / private backend)."
    tool_parameters = {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "Omit for the bound account."},
            "account": {"type": "string"},
        },
    }


class InstagramListMediaTool(_InstagramTool):
    func = staticmethod(instagram_list_media)
    tool_name = "instagram_list_media"
    tool_description = "List recent media for the bound account or another account."
    tool_parameters = {
        "type": "object",
        "properties": {
            "username": {"type": "string"},
            "limit": {"type": "integer", "default": 25},
            "after": {"type": "string"},
            "account": {"type": "string"},
        },
    }


class InstagramListCommentsTool(_InstagramTool):
    func = staticmethod(instagram_list_comments)
    tool_name = "instagram_list_comments"
    tool_description = "List top-level comments on a media object."
    tool_parameters = {
        "type": "object",
        "properties": {
            "media": {"type": "string", "description": "Numeric media id, shortcode, or Instagram URL."},
            "limit": {"type": "integer", "default": 50},
            "after": {"type": "string"},
            "account": {"type": "string"},
        },
        "required": ["media"],
    }


class InstagramSearchHashtagTool(_InstagramTool):
    func = staticmethod(instagram_search_hashtag)
    tool_name = "instagram_search_hashtag"
    tool_description = "Resolve a hashtag to its IG hashtag id. Graph accounts have a 30-unique-hashtags-per-7-days quota."
    tool_parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Hashtag without or with #."},
            "account": {"type": "string"},
        },
        "required": ["query"],
    }


class InstagramSearchUsersTool(_InstagramTool):
    func = staticmethod(instagram_search_users)
    tool_name = "instagram_search_users"
    tool_description = "Search Instagram users by keyword. Only the private backend supports this; official API has no user search."
    tool_parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 20},
            "account": {"type": "string"},
        },
        "required": ["query"],
    }


class InstagramPublishTool(_InstagramTool):
    func = staticmethod(instagram_publish)
    tool_name = "instagram_publish"
    tool_description = "Publish an image, video, reel, story, or carousel. Defaults to dry_run=True; requires INSTAGRAM_ALLOW_WRITES=true and confirm=True to execute."
    tool_parameters = {
        "type": "object",
        "properties": {
            "media_type": {"type": "string", "enum": ["image", "video", "reel", "story", "carousel"], "default": "image"},
            "image_url": {"type": "string", "description": "Public HTTPS JPEG URL for Graph; staged/local supported by private."},
            "video_url": {"type": "string"},
            "caption": {"type": "string"},
            "carousel_items": {"type": "array", "items": {"type": "object"}},
            "alt_text": {"type": "string"},
            "is_ai_generated": {"type": "boolean", "default": False},
            "account": {"type": "string"},
            "confirm": {"type": "boolean", "default": False},
            "dry_run": {"type": "boolean", "default": True},
        },
    }


class InstagramReplyCommentTool(_InstagramTool):
    func = staticmethod(instagram_reply_comment)
    tool_name = "instagram_reply_comment"
    tool_description = "Reply publicly to an Instagram comment. Defaults to dry_run=True."
    tool_parameters = {
        "type": "object",
        "properties": {
            "comment_id": {"type": "string"},
            "text": {"type": "string"},
            "media": {"type": "string", "description": "Parent media; required by the private backend."},
            "account": {"type": "string"},
            "confirm": {"type": "boolean", "default": False},
            "dry_run": {"type": "boolean", "default": True},
        },
        "required": ["comment_id", "text"],
    }


class InstagramListConversationsTool(_InstagramTool):
    func = staticmethod(instagram_list_conversations)
    tool_name = "instagram_list_conversations"
    tool_description = "List Instagram DM conversations for the bound professional account."
    tool_parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 20},
            "after": {"type": "string"},
            "account": {"type": "string"},
        },
    }


class InstagramGetConversationTool(_InstagramTool):
    func = staticmethod(instagram_get_conversation)
    tool_name = "instagram_get_conversation"
    tool_description = "Get one DM conversation's participants and metadata."
    tool_parameters = {
        "type": "object",
        "properties": {
            "conversation_id": {"type": "string"},
            "account": {"type": "string"},
        },
        "required": ["conversation_id"],
    }


class InstagramListMessagesTool(_InstagramTool):
    func = staticmethod(instagram_list_messages)
    tool_name = "instagram_list_messages"
    tool_description = "List messages in a DM conversation."
    tool_parameters = {
        "type": "object",
        "properties": {
            "conversation_id": {"type": "string"},
            "limit": {"type": "integer", "default": 20},
            "after": {"type": "string"},
            "account": {"type": "string"},
        },
        "required": ["conversation_id"],
    }


class InstagramSendDmTool(_InstagramTool):
    func = staticmethod(instagram_send_dm)
    tool_name = "instagram_send_dm"
    tool_description = "Send a text or image DM. Official accounts can only reply inside the 24h window; private accounts can cold-DM if enabled. Defaults to dry_run=True."
    tool_parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "image_url": {"type": "string"},
            "recipient_id": {"type": "string", "description": "IGSID (official) or user pk/username (private)."},
            "conversation_id": {"type": "string"},
            "account": {"type": "string"},
            "confirm": {"type": "boolean", "default": False},
            "dry_run": {"type": "boolean", "default": True},
        },
    }
