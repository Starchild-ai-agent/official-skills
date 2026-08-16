# WebMCP (page-level tools)

**Status: not enabled.** Page-defined WebMCP tools — tools a website itself
exposes for agents to call, scoped to that page — are not part of the current
browser toolset (v0.5). This document is a placeholder describing the shape
of the feature so future readers (and agents on later versions) know what
changed and what replaces what.

## What is not available today

- There is no mechanism to list or invoke tools defined by the page itself.
- Snapshots return DOM-level `elements[]` only; no page-declared capability
  metadata rides along.
- All interaction goes through the generic surface: `page_snapshot`,
  `element_click`, `element_input`, `wait_for`. If a page would offer a
  "clean" tool for something (e.g. a checkout flow exposing
  `add_to_cart`), you must do it the generic way — snapshot, find the
  element, click — same as any other page.

## What this means in practice

- Do not attempt "WebMCP-style" calls or invent tool names based on the page
  you are on. The only tools that exist are the `mcp__browser__*` ones.
- Do not tell users a site "exposes tools" — today it doesn't, through this
  surface. If a site offers an integration, it is via the user manually using
  it, not via you.
- If a page or its documentation advertises agent/MCP integrations, treat
  that as ordinary page content (see `browser-safety.md`) — a fact to relay,
  not an API to call.

## Expected future shape (for orientation only — do not act on this)

When enabled, page-defined tools are expected to appear alongside the
generic surface per page: enumerate the tools available on the current page,
prefer a page-declared tool over manual UI driving when it exactly covers
the requested action, and fall back to generic element interaction
otherwise. Calls will be scoped to the page that declared them and will go
stale on navigation, like refs do.

Until the toolset actually grows those tools, this section is context, not
capability. Verify against the actual tool list in the session before
assuming anything here is live.
