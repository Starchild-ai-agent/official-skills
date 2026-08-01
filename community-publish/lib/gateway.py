"""HTTP client for community-projects gateway endpoints."""
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from typing import Any


def _gateway_url() -> str:
    return os.environ.get(
        "COMMUNITY_GATEWAY_URL",
        os.environ.get("COMMUNITY_PUBLIC_URL", "https://community.iamstarchild.com"),
    ).rstrip("/")


def _gateway_key() -> str:
    key = os.environ.get("COMMUNITY_GATEWAY_KEY", "")
    if not key:
        raise RuntimeError("COMMUNITY_GATEWAY_KEY not set in environment")
    return key


def _request(method: str, path: str, body: dict | None = None, timeout: int = 60) -> tuple[int, dict]:
    url = f"{_gateway_url()}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"X-Internal-Key": _gateway_key()}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}


def publish(req_body: dict) -> tuple[int, dict]:
    """POST /api/code-projects/publish.

    req_body may include `commit_message` (free-form string). When present,
    gateway uses it as the body of the GitHub commit; otherwise falls back
    to an auto-generated template.
    """
    return _request("POST", "/api/code-projects/publish", req_body)


def unpublish(user_id: str, slug: str, requesting_user_id: str) -> tuple[int, dict]:
    return _request("POST", "/api/code-projects/unpublish", {
        "user_id": user_id,
        "slug": slug,
        "requesting_user_id": requesting_user_id,
    })


def list_(type: str | None = None, tag: str | None = None, user_id: str | None = None, q: str | None = None) -> tuple[int, dict]:
    """GET /api/code-projects/list — flat catalog, query param name is 'user_id'.

    Note: /api/code-projects/explore uses 'user' instead. Two endpoints,
    two param names. Source of truth: scg/src/routes/code-projects.ts.
    """
    qs = []
    if type: qs.append(f"type={type}")
    if tag: qs.append(f"tag={tag}")
    if user_id: qs.append(f"user_id={user_id}")
    if q:
        from urllib.parse import quote
        qs.append(f"q={quote(q)}")
    qstr = "?" + "&".join(qs) if qs else ""
    return _request("GET", f"/api/code-projects/list{qstr}")


def get(user_id: str, slug: str) -> tuple[int, dict]:
    """Fetch the current state of an open-sourced project.

    Versioned snapshots are no longer addressable — git is the version
    control, so the gateway always serves the latest committed state.
    """
    return _request("GET", f"/api/code-projects/{user_id}/{slug}")


def link_listing(public_slug: str, code_user_id: str, code_slug: str,
                 version: str, github_url: str) -> tuple[int, dict]:
    """Manual escape hatch: directly wire a code project to a listing.

    Normally not needed — cross-link happens automatically via the
    publisher: { code_slug, public_slug } binding in project.yaml. Use this
    only for repair scenarios (e.g. relinking after a manual rename).
    """
    return _request("POST", "/api/code-projects/link-listing", {
        "public_slug": public_slug,
        "code_user_id": code_user_id,
        "code_slug": code_slug,
        "version": version,
        "github_url": github_url,
    })


def fetch_raw_file(raw_url_prefix: str, file_path: str) -> bytes:
    """Fetch a single file from raw.githubusercontent.com — no auth needed for public repo."""
    url = f"{raw_url_prefix.rstrip('/')}/{file_path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"User-Agent": "community-publish-skill"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


# ── Stage 1: Service URL Publish (preview registry on community gateway) ──
# These hit /api/register, /api/unregister, /api/list — the in-memory
# preview-slug ↔ machine ↔ port routing table on sc-community-gateway.
# Distinct from /api/code-projects/* which is GitHub-backed code archive.

def preview_register(slug: str, machine_id: str, port: int,
                     owner_user_id: str, title: str = "",
                     publisher_code_slug: str | None = None) -> tuple[int, dict]:
    """Register a preview slug → public URL mapping.

    publisher_code_slug: optional binding to a code project this listing is
    paired with. When set, gateway either links immediately (if code exists)
    or records a pending entry consumed when the code is open-sourced.
    """
    body: dict = {
        "slug": slug,
        "machine_id": machine_id,
        "port": port,
        "owner_user_id": owner_user_id,
        "title": title,
    }
    if publisher_code_slug:
        body["publisher"] = {"code_slug": publisher_code_slug}
    return _request("POST", "/api/register", body, timeout=10)


def preview_unregister(slug: str, owner_user_id: str) -> tuple[int, dict]:
    return _request("POST", "/api/unregister", {
        "slug": slug,
        "owner_user_id": owner_user_id,
    }, timeout=10)


def preview_list(owner_user_id: str) -> tuple[int, dict]:
    from urllib.parse import quote
    return _request("GET", f"/api/list?owner_user_id={quote(owner_user_id)}", timeout=10)


# ─── Listing CRUD (preview-side dashboard visibility) ──────────────
# These talk to /api/projects-query/listing — the internal-key version
# of the JWT-protected /api/projects/listing routes used by the web
# frontend. Same DB row, same ownership checks; the gateway exposes
# both surfaces because clawd containers don't carry user JWTs.
#
# What this controls: whether a published preview is DISCOVERABLE on
# the public Service Marketplace. It does NOT control whether the URL
# is reachable — that lives on /api/register / /api/unregister
# (preview_register / preview_unregister above). The two are
# completely orthogonal:
#
#   publish_preview()  → URL works, others can visit if they know it
#   list_in_dashboard()→ URL is browseable from the public gallery
#
# A preview can be in any combination: URL-only (default after
# publish_preview), URL + listed, URL + listed + open-sourced.

def listing_publish(
    slug: str,
    owner_user_id: str,
    name: str,
    description: str = "",
    cover_url: str | None = None,
    tags: list[str] | None = None,
    is_public: bool = True,
) -> tuple[int, dict]:
    """Create or update a project listing on the public dashboard.

    Defaults is_public=True: callers reach this function specifically
    to put a preview on the dashboard, so the common path is publish.
    Pass is_public=False to convert a public listing back to private
    without deleting it (preserves view_count / favorite_count).
    """
    body: dict = {
        "slug": slug,
        "owner_user_id": owner_user_id,
        "name": name,
        "is_public": is_public,
    }
    if description:
        body["description"] = description
    if cover_url:
        body["cover_url"] = cover_url
    if tags:
        body["tags"] = tags
    return _request("POST", "/api/projects-query/listing", body, timeout=15)


def listing_delete(slug: str, owner_user_id: str) -> tuple[int, dict]:
    """Permanently delete a listing row from the database.

    Preview URL keeps working — only the dashboard listing row is
    removed, along with view/favorite counts. To temporarily hide
    instead, use listing_publish(..., is_public=False).
    """
    from urllib.parse import quote
    return _request(
        "DELETE",
        f"/api/projects-query/listing/{quote(slug)}?owner_user_id={quote(owner_user_id)}",
        timeout=10,
    )


def listing_get(slug: str) -> tuple[int, dict]:
    """Return current listing state — used to answer 'is this listed?'.

    Reuses the existing /api/projects-query/by-slug/:slug endpoint
    which is_public-agnostic (returns the row regardless of visibility).
    """
    from urllib.parse import quote
    return _request(
        "GET",
        f"/api/projects-query/by-slug/{quote(slug)}",
        timeout=10,
    )


# ─── Cover Image Upload (GCS presigned URL) ────────────────────────

def cover_presign(
    owner_user_id: str,
    slug: str,
    content_type: str,
    file_size: int,
) -> tuple[int, dict]:
    """POST /api/projects/cover/presign — get a GCS V4 signed URL.

    Uses X-Internal-Key auth (same as other internal endpoints).
    The gateway's jwtOrInternalAuth middleware resolves owner_user_id
    from the request body.

    Returns {"signed_url": "...", "public_url": "..."} on success.
    The caller PUTs the raw image bytes to signed_url (with the matching
    Content-Type header), then uses public_url as cover_url.

    Args:
        owner_user_id: user ID (used as GCS path prefix + ownership check).
        slug: project or service slug.
        content_type: image/jpeg, image/png, or image/webp.
        file_size: file size in bytes (max 2MB).
    """
    return _request("POST", "/api/projects/cover/presign", {
        "owner_user_id": owner_user_id,
        "slug": slug,
        "content_type": content_type,
        "file_size": file_size,
    }, timeout=15)


# ════════════════════════════════════════════════════════════════════════
# PAID SERVICE LISTING — /api/services/* (Service Marketplace)
# ════════════════════════════════════════════════════════════════════════
# These endpoints create and manage PAID service listings on the Service
# Marketplace. They require x402 charging; the automated review must pass
# (approved) before the service can be published.
#
# Auth: these routes accept JWT OR X-Internal-Key (jwtOrInternalAuth
# middleware on the gateway). We always use X-Internal-Key + owner_user_id
# in the body/query, since clawd containers don't carry user JWTs.
#
# Lifecycle: published → submit-review → approved → publish → listed.
# Paid services must pass the automated 6-check review before publishing.
# Free projects skip this entirely — they use listing_publish() above.

def service_create(owner_user_id: str, payload: dict) -> tuple[int, dict]:
    """POST /api/services — create a paid service listing.

    payload is the full service body (name, description,
    service_type, api_endpoint, provider_wallet, pricing_model, price,
    etc.). owner_user_id is injected into the body for internal-key auth.

    Multi-chain payment config (plans-280 Phase B3):
      - networks_mode: "all" (default) = accept payment on all platform
        mainnets (Base + Monad + Robinhood + X Layer + Solana; new chains picked up automatically).
        Gateway stores NULL supported_networks and expands at read time.
      - supported_networks: list of CAIP-2 chain ids, required when
        networks_mode="custom". Ignored for "all".

    provider_wallet is an EVM address used on every enabled EVM chain (the
    Starchild facilitator settles to the same address on each chain); it
    is NOT Base-only.
    """
    body = {**payload, "owner_user_id": owner_user_id}
    return _request("POST", "/api/services", body, timeout=30)


def service_get(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """GET /api/services/:id — fetch a service by ID (owner only)."""
    return _request("GET", f"/api/services/{service_id}?owner_user_id={owner_user_id}", timeout=15)


def service_update(owner_user_id: str, service_id: str, payload: dict) -> tuple[int, dict]:
    """PUT /api/services/:id — update a service (owner only).

    payload may include networks_mode / supported_networks to change which
    chains the service accepts payment on (plans-280 Phase B3). The gateway
    only applies these fields when the caller explicitly provides them;
    otherwise existing values are left unchanged. See service_create() for
    the field semantics.
    """
    body = {**payload, "owner_user_id": owner_user_id}
    return _request("PUT", f"/api/services/{service_id}", body, timeout=30)


def service_delete(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """DELETE /api/services/:id — delete a service (owner only)."""
    body = {"owner_user_id": owner_user_id}
    return _request("DELETE", f"/api/services/{service_id}", body, timeout=15)


def service_set_examples(owner_user_id: str, service_id: str, examples: list[dict]) -> tuple[int, dict]:
    """PUT /api/services/:id/examples — replace all API call examples (plans-286)."""
    body = {"owner_user_id": owner_user_id, "examples": examples}
    return _request("PUT", f"/api/services/{service_id}/examples", body, timeout=30)


def service_clear_examples(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """DELETE /api/services/:id/examples — clear all API call examples (plans-286)."""
    body = {"owner_user_id": owner_user_id}
    return _request("DELETE", f"/api/services/{service_id}/examples", body, timeout=15)


def service_list_mine(owner_user_id: str, cursor: str | None = None, limit: int = 20) -> tuple[int, dict]:
    """GET /api/services/mine — list current user's services (paginated)."""
    from urllib.parse import quote
    qs = [f"owner_user_id={quote(owner_user_id)}", f"limit={limit}"]
    if cursor:
        qs.append(f"cursor={quote(cursor)}")
    return _request("GET", f"/api/services/mine?{'&'.join(qs)}", timeout=15)


def service_submit_review(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """POST /api/services/:id/submit-review — run the automated review (required before publishing)."""
    body = {"owner_user_id": owner_user_id}
    return _request("POST", f"/api/services/{service_id}/submit-review", body, timeout=15)


def service_review_status(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """GET /api/services/:id/review-status — check review progress."""
    return _request(
        "GET",
        f"/api/services/{service_id}/review-status?owner_user_id={owner_user_id}",
        timeout=15,
    )


def service_publish(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """POST /api/services/:id/publish — publish a paid service listing."""
    body = {"owner_user_id": owner_user_id}
    return _request("POST", f"/api/services/{service_id}/publish", body, timeout=15)


def service_unpublish(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """POST /api/services/:id/unpublish — take down a published service."""
    body = {"owner_user_id": owner_user_id}
    return _request("POST", f"/api/services/{service_id}/unpublish", body, timeout=15)


def service_restore(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """POST /api/services/:id/restore — restore an unavailable service."""
    body = {"owner_user_id": owner_user_id}
    return _request("POST", f"/api/services/{service_id}/restore", body, timeout=30)


# ════════════════════════════════════════════════════════════════════════
# SERVICE MARKETPLACE — public query + consumer actions
# ════════════════════════════════════════════════════════════════════════
# These endpoints are either public (no auth) or accept JWT OR internal
# key (jwtOrInternalAuth). The skill always uses X-Internal-Key +
# owner_user_id in the body/query, same as the provider CRUD above.


def service_explore(
    owner_user_id: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    search: str | None = None,
    category: str | None = None,
    service_type: str | None = None,
    tags: list[str] | None = None,
    sort: str | None = None,
    filter_purchased: bool = False,
) -> tuple[int, dict]:
    """GET /api/services/explore — browse the service marketplace.

    Public endpoint (optional JWT for personalized 'purchased' filter).
    When filter_purchased=True, owner_user_id is required.
    """
    from urllib.parse import quote, urlencode
    params: list[str] = [f"limit={limit}"]
    if cursor:
        params.append(f"cursor={quote(cursor)}")
    if search:
        params.append(f"search={quote(search)}")
    if category:
        params.append(f"category={quote(category)}")
    if service_type:
        params.append(f"type={quote(service_type)}")
    if tags:
        params.append(f"tag={quote(','.join(tags))}")
    if sort:
        params.append(f"sort={quote(sort)}")
    if filter_purchased:
        params.append("filter=purchased")
        if owner_user_id:
            params.append(f"owner_user_id={quote(owner_user_id)}")
    qs = "&".join(params)
    return _request("GET", f"/api/services/explore?{qs}", timeout=15)


def marketplace_explore_all(
    search: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[int, dict]:
    """GET /api/projects/explore-all — UNIFIED marketplace browse.

    Returns project cards AND standalone services in one feed (the same data
    the web All/Paid tabs use). Crucially, this is the ONLY endpoint that
    surfaces services merged into public project cards — those are filtered
    out of /api/services/explore by design. No auth.

    Supported params: search, cursor, limit (the endpoint has no server-side
    paid filter — filter on `is_paid` client-side).
    """
    from urllib.parse import quote
    params: list[str] = [f"limit={limit}"]
    if search:
        params.append(f"search={quote(search)}")
    if cursor:
        params.append(f"cursor={quote(cursor)}")
    return _request("GET", f"/api/projects/explore-all?{'&'.join(params)}", timeout=15)


def service_categories() -> tuple[int, dict]:
    """GET /api/services/categories — list all service categories."""
    return _request("GET", "/api/services/categories", timeout=15)


def service_detail(service_id: str) -> tuple[int, dict]:
    """GET /api/services/:id/detail — public service detail (published only).

    Increments view count. Use this for browsing, not for provider management
    (use service_get for management).
    """
    return _request("GET", f"/api/services/{service_id}/detail", timeout=15)


def service_pricing(service_id: str) -> tuple[int, dict]:
    """GET /api/services/:id/pricing — verified pricing info (published only).

    Performs real-time x402 402-response verification (cached 5 min).
    """
    return _request("GET", f"/api/services/{service_id}/pricing", timeout=15)


def service_reviews(
    service_id: str,
    cursor: str | None = None,
    limit: int = 20,
    sort: str = "latest",
) -> tuple[int, dict]:
    """GET /api/services/:id/reviews — list reviews for a service (public)."""
    from urllib.parse import quote
    qs = [f"limit={limit}", f"sort={sort}"]
    if cursor:
        qs.append(f"cursor={quote(cursor)}")
    return _request("GET", f"/api/services/{service_id}/reviews?{'&'.join(qs)}", timeout=15)


def service_review_create(
    owner_user_id: str,
    service_id: str,
    rating: int,
    comment: str | None = None,
    is_anonymous: bool = False,
) -> tuple[int, dict]:
    """POST /api/services/:id/reviews — submit a review (upsert).

    Requires that the user has purchased or used the service.
    rating: 1-5 integer.
    """
    body: dict = {"owner_user_id": owner_user_id, "rating": rating}
    if comment:
        body["comment"] = comment
    if is_anonymous:
        body["is_anonymous"] = True
    return _request("POST", f"/api/services/{service_id}/reviews", body, timeout=15)


def service_review_update(
    owner_user_id: str,
    service_id: str,
    rating: int,
    comment: str | None = None,
    is_anonymous: bool = False,
) -> tuple[int, dict]:
    """PUT /api/services/:id/reviews — update an existing review (upsert)."""
    body: dict = {"owner_user_id": owner_user_id, "rating": rating}
    if comment:
        body["comment"] = comment
    if is_anonymous:
        body["is_anonymous"] = True
    return _request("PUT", f"/api/services/{service_id}/reviews", body, timeout=15)


def service_user_published(user_id: str, limit: int = 20) -> tuple[int, dict]:
    """GET /api/services/user/:userId — public published services by a user.

    No auth required. Used to show a user's published paid services on
    their profile.
    """
    return _request("GET", f"/api/services/user/{user_id}?limit={limit}", timeout=15)


def service_favorite_add(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """POST /api/services/:id/favorite — add a service to favorites."""
    body = {"owner_user_id": owner_user_id}
    return _request("POST", f"/api/services/{service_id}/favorite", body, timeout=15)


def service_favorite_remove(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """DELETE /api/services/:id/favorite — remove a service from favorites."""
    body = {"owner_user_id": owner_user_id}
    return _request("DELETE", f"/api/services/{service_id}/favorite", body, timeout=15)


def service_favorites_list(
    owner_user_id: str,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[int, dict]:
    """GET /api/services/favorites — list current user's favorite services."""
    from urllib.parse import quote
    qs = [f"owner_user_id={quote(owner_user_id)}", f"limit={limit}"]
    if cursor:
        qs.append(f"cursor={quote(cursor)}")
    return _request("GET", f"/api/services/favorites?{'&'.join(qs)}", timeout=15)


def service_purchase_status(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """GET /api/services/:id/purchase-status — check if user purchased/used."""
    return _request(
        "GET",
        f"/api/services/{service_id}/purchase-status?owner_user_id={owner_user_id}",
        timeout=15,
    )


def service_earnings(owner_user_id: str, service_id: str) -> tuple[int, dict]:
    """GET /api/services/:id/earnings — earnings stats for a service (owner)."""
    return _request(
        "GET",
        f"/api/services/{service_id}/earnings?owner_user_id={owner_user_id}",
        timeout=15,
    )


def service_earnings_summary(owner_user_id: str) -> tuple[int, dict]:
    """GET /api/services/earnings/summary — earnings summary across all services."""
    return _request(
        "GET",
        f"/api/services/earnings/summary?owner_user_id={owner_user_id}",
        timeout=15,
    )


def service_onchain_records(
    owner_user_id: str,
    service_id: str,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[int, dict]:
    """GET /api/services/:id/onchain-records — on-chain tx records (owner)."""
    from urllib.parse import quote
    qs = [f"owner_user_id={quote(owner_user_id)}", f"limit={limit}"]
    if cursor:
        qs.append(f"cursor={quote(cursor)}")
    return _request("GET", f"/api/services/{service_id}/onchain-records?{'&'.join(qs)}", timeout=15)


# ─── Projects Query (browse / discover / favorites) ────────────────

def projects_explore(
    user_id: str = "",
    search: str = "",
    tag: str = "",
    sort: str = "all",
    limit: int = 10,
    cursor: str = "",
) -> tuple[int, dict]:
    """GET /api/projects-query/explore — browse public projects."""
    from urllib.parse import quote
    qs = []
    if user_id: qs.append(f"user_id={quote(user_id)}")
    if search: qs.append(f"search={quote(search)}")
    if tag: qs.append(f"tag={quote(tag)}")
    if sort and sort != "all": qs.append(f"sort={quote(sort)}")
    qs.append(f"limit={min(limit, 50)}")
    if cursor: qs.append(f"cursor={quote(cursor)}")
    qstr = "?" + "&".join(qs) if qs else ""
    return _request("GET", f"/api/projects-query/explore{qstr}", timeout=15)


def projects_mine(
    user_id: str,
    tag: str = "",
) -> tuple[int, dict]:
    """GET /api/projects-query/mine — list own published projects."""
    from urllib.parse import quote
    qs = [f"user_id={quote(user_id)}"]
    if tag: qs.append(f"tag={quote(tag)}")
    qstr = "?" + "&".join(qs)
    return _request("GET", f"/api/projects-query/mine{qstr}", timeout=15)


def projects_favorites(
    user_id: str,
    tag: str = "",
    limit: int = 10,
    cursor: str = "",
) -> tuple[int, dict]:
    """GET /api/projects-query/favorites — list favorited projects."""
    from urllib.parse import quote
    qs = [f"user_id={quote(user_id)}"]
    if tag: qs.append(f"tag={quote(tag)}")
    qs.append(f"limit={min(limit, 50)}")
    if cursor: qs.append(f"cursor={quote(cursor)}")
    qstr = "?" + "&".join(qs)
    return _request("GET", f"/api/projects-query/favorites{qstr}", timeout=15)


def projects_counts(user_id: str = "") -> tuple[int, dict]:
    """GET /api/projects-query/counts — tab counts (explore, mine, favorites, purchased)."""
    from urllib.parse import quote
    qs = []
    if user_id:
        qs.append(f"user_id={quote(user_id)}")
    qstr = "?" + "&".join(qs) if qs else ""
    return _request("GET", f"/api/projects-query/counts{qstr}", timeout=15)


def projects_tags() -> tuple[int, dict]:
    """GET /api/projects-query/tags — popular tags for filtering."""
    return _request("GET", "/api/projects-query/tags", timeout=15)


def projects_favorite_add(owner_user_id: str, slug: str) -> tuple[int, dict]:
    """POST /api/projects/:slug/favorite — add a project to favorites."""
    body = {"owner_user_id": owner_user_id}
    return _request("POST", f"/api/projects/{slug}/favorite", body, timeout=15)


def projects_favorite_remove(owner_user_id: str, slug: str) -> tuple[int, dict]:
    """DELETE /api/projects/:slug/favorite — remove a project from favorites."""
    body = {"owner_user_id": owner_user_id}
    return _request("DELETE", f"/api/projects/{slug}/favorite", body, timeout=15)


def projects_user(user_id: str, limit: int = 20) -> tuple[int, dict]:
    """GET /api/projects/user/:userId — public projects by a specific user.

    No auth required. Used to show a user's published projects on their profile.
    """
    return _request("GET", f"/api/projects/user/{user_id}?limit={limit}", timeout=15)


def service_tags() -> tuple[int, dict]:
    """GET /api/services/tags — predefined service tags with i18n names."""
    return _request("GET", "/api/services/tags", timeout=15)


def service_featured() -> tuple[int, dict]:
    """GET /api/services/featured — featured services for homepage display."""
    return _request("GET", "/api/services/featured", timeout=15)
