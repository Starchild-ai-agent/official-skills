# Reference Notes: The 5-Minute Guide to Getting the Most Out of Starchild

Source article title: **The 5-Minute Guide to Getting the Most Out of Starchild**  
Purpose of this local note: keep the key guidance inside the `user-onboarding` skill so agents can use it without fetching the web page again.

---

## Core framing

- Starchild should be presented as a practical, outcome-first agent: powerful intern + assistant, not a feature list.
- User outcome matters more than model/tool details.
- Better results come from clearer requests and faster feedback loops.

---

## 10 practical principles (condensed)

### 1) Smart Routing first
- Use `/model smart` to reduce unnecessary cost.
- Simple tasks should route to cheaper/faster models, complex tasks to stronger models.

### 2) Prompt quality is leverage
- Be specific and concrete.
- Keep each message focused on one clear ask.
- Provide key context up front to reduce back-and-forth.
- Explicitly request output format (table, bullets, etc.).

### 3) Connect delivery channels early (when needed)
- Telegram/WeChat enables mobile access + push notifications for scheduled work.
- For team usage, Telegram groups + whitelist allow controlled multi-user collaboration.

### 4) Use connectors for real workflows
- Connect external tools (e.g., Gmail, Calendar, Drive, Slack, Notion, GitHub) so the agent can execute real work in context.

### 5) Build and preview quickly
- Ask for the end result directly (dashboard/tool/page), then iterate on a live preview.
- Deploy only after the preview output meets expectations.

### 6) Turn repetition into skills
- If a task repeats, search the skill marketplace first.
- If no suitable skill exists, create one and reuse.

### 7) Keep machine health visible
- Resource limits are real (CPU/RAM/disk).
- Periodically check usage, clean stale files/processes, and avoid silent resource drift.

### 8) Wallet is a built-in capability
- Agent wallet supports EVM + Solana flows.
- Use policy controls and explicit verification for safety-sensitive operations.

### 9) Teach the agent intentionally
- Correct mistakes explicitly.
- Persist stable preferences/methods to memory.
- Convert proven workflows into skills.

### 10) If blocked, ask directly
- Encourage users to state desired outcome clearly.
- Agent should search docs/tools/skills and work backward to execution.

---

## How this maps to onboarding behavior

- Start with a quick win, not a feature tour.
- Ask discovery questions around repetitive pain points (frequency + annoyance).
- Show sample output first, then schedule automation.
- Confirm delivery channel before creating recurring pushes.
- Save user preferences and successful workflow patterns for continuity.

---

## Product feedback channel

If users report persistent missing features or broken workflows, direct them to:  
`https://t.me/starchild_beta`

---

## Maintenance note

This file is intentionally concise and operational. Update when the product guide changes materially (routing, connectors, channel flow, scheduling, wallet safety, or onboarding sequence).