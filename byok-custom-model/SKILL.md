---
name: byok-custom-model
version: 1.0.0
description: "BYOK — register a custom LLM endpoint (Anthropic, OpenAI, Qwen, DeepSeek, etc.) with your own API key"
author: starchild
tags: [byok, custom-model, llm, openrouter, anthropic, deepseek, qwen, kimi, mimo, gemini, venice]
---

# 🔑 BYOK — Custom LLM Models

Add a custom LLM endpoint to the model selector. Bypasses the platform proxy — you supply your own API key, the agent hits the vendor / aggregator directly (OpenRouter, DashScope, Anthropic native, self-hosted, etc.).

The `custom_models` tool stays built-in. This SKILL.md is the reference doc + onboarding flow.

## See also
- `config/context/references/model-onboarding.md` — broader model selection / OAuth context
- `chatgpt-codex-onboarding` skill — for ChatGPT/Codex OAuth (different mechanism, NOT BYOK)

---

## Onboarding flow — API-example first

When a user wants to add a custom model, **the first move is NOT to ask for `base_url` or `upstream_model`.** Instead:

1. Ask the user to paste the provider's official API example from their docs (curl / requests sample). **Tell them not to include a real API key** — placeholders or fake keys are fine.
2. Run `custom_models(action="parse_example", api_example="<pasted>")`. It auto-detects:
   - `base_url`
   - `upstream_model`
   - `wire` (openai vs anthropic)
   - `thinking_mode`
   - vendor-specific `request_params`
   - `capabilities`
3. Review the parsed draft with the user (1 sentence summary), then call `add` with the detected fields.
4. The `add` call dispatches a **secure input popup** to collect the API key. The key goes straight to `workspace/.env`, never to chat history or tool results.
5. After success, the model appears in the selector as `custom/<short-name>`. User switches with `/model custom/<name>`.

**Only ask for `base_url` / `upstream_model` directly if the user refuses to paste an example or already supplied them.**

---

## Curated vendors — `add_template` shortcut

For these 9 vendors, skip `parse_example` entirely. Call `add_template(vendor="<id>")` — all fields auto-filled, the user only provides the API key via the secure popup.

| vendor id | notes |
|---|---|
| `anthropic` | Anthropic native API (Claude direct, not via Bedrock/Vertex) |
| `openai` | OpenAI API direct |
| `qwen` | Alibaba DashScope |
| `deepseek` | DeepSeek API |
| `kimi` | Moonshot |
| `mimo` | Xiaomi MiMo |
| `gemini` | Google AI Studio (NOT Vertex) |
| `gemma` | Google Gemma |
| `venice` | Venice AI (privacy-first) |

Optional `upstream_model` overrides the curated default — accepts any model id from `list_vendor_models` for vendors with dynamic discovery.

---

## Dynamic vendor catalogs — `list_vendor_models`

Some vendors ship new models often. Use `list_vendor_models(vendor="<id>")` to fetch the live `/models` catalog with capabilities (vision, tools, reasoning, privacy tier), pricing, and context length.

Required when:
- User wants the **latest** model not in curated defaults
- User asks for a specific capability ("which Venice model supports vision?")
- User wants pricing comparison

Only works for vendors with `supports_dynamic_models: true` in `templates`.

---

## Actions reference

| action | required | purpose |
|---|---|---|
| `templates` | — | List curated vendor presets |
| `list_vendor_models` | `vendor` | Live `/models` catalog (requires `supports_dynamic_models`) |
| `add_template` | `vendor` | One-click registration for curated vendor (recommended path for 9 known vendors) |
| `parse_example` | `api_example` | Parse docs API example into a safe draft (non-curated vendors) |
| `add` | `upstream_model`, `base_url`, `wire` | Register from custom args (use after `parse_example`) |
| `list` | — | Show all registered custom entries |
| `get` | `model_id` | Inspect one entry |
| `remove` | `model_id` | Delete an entry |

---

## After registration

- Model appears in the selector prefixed with `custom/`.
- User switches via `/model custom/<name>` (e.g. `/model custom/qwen-plus-e3f4`) or via the model picker UI.
- Subsequent calls bypass the platform proxy — the vendor's pricing applies directly to the user's BYOK quota.

---

## Critical rules

- **Never accept an API key pasted in chat.** If the user pastes one, ignore it, refuse to register, and explain that the secure popup is the only way.
- **Never re-issue the secure-input popup automatically** if the user hasn't responded — wait.
- **Don't manually edit `workspace/config/custom_models.yaml` or `workspace/.env`.** Always go through this tool.
- The 9 curated vendors **always** use `add_template`. Only use `parse_example` + `add` for self-hosted or rare providers.
