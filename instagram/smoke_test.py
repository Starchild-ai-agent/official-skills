#!/usr/bin/env python3
"""Offline smoke test. No network, no live Instagram, no real credentials."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

TMP = tempfile.mkdtemp(prefix="instagram-smoke-")
os.environ.update(
    {
        "INSTAGRAM_COMPOSIO_ENABLED": "false",
        "INSTAGRAM_STATE_DIR": TMP,
        "INSTAGRAM_ALLOW_WRITES": "false",
        "INSTAGRAM_AUTO_CONFIRM": "false",
        "INSTAGRAM_PREFERRED_AUTH": "graph,composio,private",
        "INSTAGRAM_ACCOUNTS_JSON": json.dumps(
            [
                {
                    "label": "brand",
                    "auth_kind": "graph",
                    "access_token": "test-graph-token",
                    "ig_user_id": "123",
                    "page_id": "456",
                    "page_token": "test-page-token",
                },
                {
                    "label": "personal",
                    "auth_kind": "private",
                    "session_file": str(Path(TMP) / "session.json"),
                    "cold_dm": True,
                },
            ]
        ),
    }
)

import ig_gateway  # noqa: E402
from ig_composio import ComposioBackend  # noqa: E402
from ig_errors import CapabilityUnavailable, QuotaExceeded, ToolNotFound  # noqa: E402
from ig_graph import GraphClient  # noqa: E402
from ig_models import AUTH_GRAPH, AUTH_PRIVATE, Account, graph_capabilities  # noqa: E402
from ig_router import Router  # noqa: E402
from ig_service import (  # noqa: E402
    ROUTER,
    instagram_auth_status,
    instagram_capabilities,
    instagram_hashtag_media,
    instagram_publish,
)
from ig_state import check_hashtag, record_hashtag, usage  # noqa: E402

# Never touch the network.
ig_gateway.GatewayClient.health = lambda self: {"ok": False, "error": "offline smoke"}
ig_gateway.GatewayClient.connections = lambda self, toolkit="instagram": []


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"ok  {label}")


router = Router()
router.refresh()
accounts = {a.label: a for a in router.accounts(include_composio=False)}
check("two bound accounts", set(accounts) == {"brand", "personal"})
check("graph capabilities include hashtag search", "search_hashtag" in accounts["brand"].capabilities)
check("private capabilities include people search", "search_users" in accounts["personal"].capabilities)

check("search_hashtag routes to graph", router.resolve("search_hashtag").label == "brand")
check("search_users routes to private", router.resolve("search_users").label == "personal")
check("post_publish routes to graph", router.resolve("post_publish").label == "brand")
check("dm_reply routes to graph page", router.resolve("dm_reply").label == "brand")
check("dm_initiate routes to private", router.resolve("dm_initiate").label == "personal")
check("explicit account wins", router.resolve("profile_read", account="personal").label == "personal")

onboarding = router.onboarding("search_users")
check("search_users onboarding recommends private", onboarding["recommended"] == AUTH_PRIVATE)
check("onboarding has steps", bool(onboarding["options"][0]["steps"]))

try:
    router.resolve("search_users", account="brand")
except CapabilityUnavailable as exc:
    check("graph account rejects people search", "onboarding" in exc.details)
else:
    raise AssertionError("graph account should reject search_users")

from ig_service import instagram_connect  # noqa: E402

already_graph = instagram_connect(target="graph")
check("graph connect prefers bound token", already_graph["ok"] and already_graph["data"]["status"] == "already_connected")
already_private = instagram_connect(target="private")
check("private connect prefers bound session", already_private["ok"] and already_private["data"]["status"] == "already_connected")
already_cap = instagram_connect(capability="search_hashtag")
check("capability connect prefers bound graph", already_cap["ok"] and already_cap["data"]["status"] == "already_connected")
already_people = instagram_connect(capability="search_users")
check("capability connect prefers bound private", already_people["ok"] and already_people["data"]["status"] == "already_connected")

wrong_target = instagram_connect(target="composio", capability="search_users", account="brand")
check("composio cannot be asked for people search", wrong_target["ok"] and wrong_target["data"]["status"] == "capability_not_available")
wrong_graph = instagram_connect(target="graph", capability="search_users", account="brand")
check("graph cannot be asked for people search", wrong_graph["ok"] and wrong_graph["data"]["status"] == "capability_not_available")

status = instagram_auth_status()
check("auth status ok", status["ok"] is True)
check("auth status lists two accounts", len(status["data"]["accounts"]) == 2)

caps = instagram_capabilities()
check("capability matrix ok", caps["ok"] is True)
check("missing everywhere includes dm_initiate? no, private has it", "dm_initiate" not in caps["data"]["missing_everywhere"])

# Dry-run is allowed even when writes are disabled.
preview_disabled = instagram_publish(
    media_type="image",
    image_url="https://cdn.example.com/a.jpg",
    caption="test",
)
check("dry run works without write permission", preview_disabled["ok"] is True and preview_disabled["data"]["dry_run"] is True)

# Write guard: disabled.
blocked = instagram_publish(
    media_type="image",
    image_url="https://cdn.example.com/a.jpg",
    caption="test",
    dry_run=False,
    confirm=True,
)
check("writes disabled", blocked["ok"] is False and blocked["error"]["code"] == "write_blocked")

os.environ["INSTAGRAM_ALLOW_WRITES"] = "true"
preview = instagram_publish(
    media_type="image",
    image_url="https://cdn.example.com/a.jpg",
    caption="test",
)
check("publish dry run", preview["ok"] is True and preview["data"]["dry_run"] is True)
unconfirmed = instagram_publish(
    media_type="image",
    image_url="https://cdn.example.com/a.jpg",
    caption="test",
    dry_run=False,
    confirm=False,
)
check("publish needs confirmation", unconfirmed["ok"] is False and unconfirmed["error"]["code"] == "confirmation_required")

# Hybrid fallback: Graph business discovery misses a personal account, private succeeds.
from ig_errors import NotFound  # noqa: E402
from ig_service import instagram_profile  # noqa: E402


class FakeGraph:
    def profile(self, username=None):
        raise NotFound("not a professional account")


class FakePrivate:
    def profile(self, username=None):
        return {"username": username, "source": "private"}


original_backend = router.backend
router.backend = lambda account: FakeGraph() if account.auth_kind == "graph" else FakePrivate()
import ig_service  # noqa: E402

ig_service.ROUTER = router
fallback = instagram_profile("someone")
check("profile falls back to private on not-found", fallback["ok"] and fallback["auth_kind"] == "private")
router.backend = original_backend
ig_service.ROUTER = ROUTER

# Graph publish orchestration without HTTP.
graph_account = Account(
    label="brand",
    auth_kind=AUTH_GRAPH,
    capabilities=graph_capabilities(has_page_token=True),
    ig_user_id="123",
    page_id="456",
    metadata={"access_token": "x", "page_token": "y", "ig_user_id": "123", "page_id": "456"},
)
graph = GraphClient(graph_account)
graph._create_container = lambda params: "container-1"
graph.wait_for_container = lambda container_id: {"status_code": "FINISHED"}
graph.publish_container = lambda container_id: {"id": "media-1"}
published = graph.publish(media_type="image", image_url="https://cdn.example.com/a.jpg", caption="hi")
check("graph publish uses container then media", published["id"] == "media-1" and published["container_id"] == "container-1")

# Graph request shapes (no HTTP).
import ig_graph  # noqa: E402

http_calls = []
original_request_json = ig_graph.request_json


def fake_http(url, **kwargs):
    http_calls.append((url, kwargs))
    if "ig_hashtag_search" in url:
        return {"id": "hashtag-1"}
    if url.endswith("/media") and kwargs.get("method") == "POST":
        return {"id": "container-http"}
    if "container-http" in url:
        return {"status_code": "FINISHED"}
    if "media_publish" in url:
        return {"id": "media-http"}
    if "/messages" in url and kwargs.get("method") == "POST":
        return {"message_id": "msg-1"}
    if "/media" in url:
        return {"data": [{"id": "m1"}]}
    return {"data": []}


ig_graph.request_json = fake_http
http_account = Account(
    label="http-test",
    auth_kind=AUTH_GRAPH,
    capabilities=graph_capabilities(has_page_token=True),
    ig_user_id="123",
    page_id="456",
    metadata={"access_token": "x", "page_token": "y", "ig_user_id": "123", "page_id": "456"},
)
http_graph = GraphClient(http_account)
tag_result = http_graph.search_hashtag("fitness")
check("graph hashtag search endpoint", tag_result["id"] == "hashtag-1" and "ig_hashtag_search" in http_calls[-1][0])
http_calls.clear()
hashtag_media = instagram_hashtag_media("fitness", account="brand")
check("service resolves tag to hashtag id", hashtag_media["ok"] and "hashtag-1/top_media" in http_calls[-1][0])
http_calls.clear()
http_graph.publish(media_type="image", image_url="https://cdn.example.com/a.jpg", caption="hi")
check("graph create container body", http_calls[0][1]["body"]["image_url"].endswith("a.jpg"))
check("graph publish body", http_calls[-1][1]["body"]["creation_id"] == "container-http")
http_calls.clear()
http_graph.send_dm(text="hello", recipient_id="igsid-1")
check("graph DM uses page messages", http_calls[-1][0].endswith("/456/messages"))
check("graph DM recipient", http_calls[-1][1]["body"]["recipient"]["id"] == "igsid-1")

http_calls.clear()
published = instagram_publish(
    media_type="image",
    image_url="https://cdn.example.com/a.jpg",
    caption="hi",
    dry_run=False,
    confirm=True,
)
check("service publish executes", published["ok"] and published["data"]["id"] == "media-http")
ig_graph.request_json = original_request_json

# Hashtag ledger: 30 unique tags per 7 days.
ledger_path = Path(TMP) / "hashtag_usage.json"
if ledger_path.exists():
    ledger_path.unlink()
for index in range(30):
    check_hashtag("brand", f"tag{index}")
    record_hashtag("brand", f"tag{index}")
try:
    check_hashtag("brand", "tag30")
except QuotaExceeded:
    check("hashtag quota enforced", True)
else:
    raise AssertionError("hashtag quota should be exhausted")
check("hashtag usage reports 30", usage("brand")["used"] == 30)

# Composio schema arg mapping.
gateway = ig_gateway.GatewayClient()
gateway._schema_cache["TEST_TOOL"] = {
    "input_parameters": {
        "properties": {
            "ig_media_id": {"type": "string"},
            "message": {"type": "string"},
        }
    }
}
captured = {}
gateway.execute = lambda tool, arguments: captured.update({"tool": tool, "arguments": arguments}) or {"ok": 1}
gateway.call("TEST_TOOL", {"ig_media_id": "1", "text": "hello"})
check("composio maps text -> message", captured["arguments"] == {"ig_media_id": "1", "message": "hello"})

# Composio publish fallback to the working legacy slugs.
composio_account = Account(
    label="composio",
    auth_kind="composio",
    capabilities=frozenset({"post_publish"}),
    ig_user_id="999",
)
backend = ComposioBackend(composio_account)
calls = []


def fake_call(tool, arguments, extra=None):
    calls.append((tool, arguments))
    if tool == "INSTAGRAM_CREATE_MEDIA_CONTAINER":
        raise ToolNotFound("not found")
    if tool == "INSTAGRAM_POST_IG_USER_MEDIA":
        return {"id": "container-2"}
    if tool == "INSTAGRAM_CREATE_POST":
        return {"id": "media-2"}
    if tool == "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH":
        return {"id": "media-2"}
    raise AssertionError(tool)


backend.gateway.call = fake_call
result = backend.publish(media_type="image", image_url="https://cdn.example.com/a.jpg", caption="hi")
check("composio falls back to legacy slugs", result["id"] == "media-2")
check(
    "composio used container then publish",
    [c[0] for c in calls]
    == [
        "INSTAGRAM_CREATE_MEDIA_CONTAINER",
        "INSTAGRAM_POST_IG_USER_MEDIA",
        "INSTAGRAM_CREATE_POST",
    ],
)

# Exports surface loads.
import exports  # noqa: E402

check("exports surface", callable(exports.instagram_auth_status) and callable(exports.instagram_send_dm))

print("\nAll offline smoke tests passed.")
