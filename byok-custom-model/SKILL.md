---
name: byok-custom-model
version: 2.0.3
description: "BYOK — register a custom LLM endpoint (Anthropic, OpenAI, Qwen, DeepSeek, Venice, etc.) with your own API key"
author: starchild
delivery: script
protected: true
tags: [byok, custom-model, llm, openrouter, anthropic, deepseek, qwen, kimi, mimo, gemini, venice]
---

# 🔑 BYOK — Custom LLM Models

Register a custom LLM endpoint to the model selector. Bypasses the platform proxy — the user supplies their own API key, the agent hits the vendor / aggregator directly (OpenRouter, DashScope, Anthropic native, self-hosted, etc.).

This is a **script-mode skill** — no tools registered. Read this file, then call the exports from a `bash` block.

## See also
- `config/context/references/model-onboarding.md` — broader model selection / OAuth context
- `chatgpt-codex-onboarding` skill — for ChatGPT/Codex OAuth (different mechanism, NOT BYOK)

---

## Onboarding flow — API-example first

When a user wants to add a custom model, **the first move is NOT to ask for `base_url` or `upstream_model`.** Instead:

1. Ask the user to paste the provider's official API example from their docs (curl / requests / fetch sample). **Tell them not to include a real API key** — placeholders or fake keys are fine.
2. Run `parse_example` to auto-detect base_url, upstream_model, wire (openai vs anthropic), thinking params, and vendor-specific request fields.
3. Review the draft with the user.
4. Call `add(...)` (or `add_template(vendor=...)` for a curated vendor) — the entry is written to `custom_models.yaml`.
5. **If the result contains `need_env_input`, immediately call the `request_env_input` tool** with `env_vars` and `reason` from that payload. This pops the secure-input UI; the user enters the key; it lands in `workspace/.env`. **This step is mandatory — the script cannot pop the UI itself.**

For the 9 curated vendors below, skip steps 1-3 and go straight to `add_template(vendor=...)` — base_url / wire / thinking / capabilities are all pre-filled. Step 5 still applies.

Curated vendors: `anthropic`, `openai`, `qwen`, `deepseek`, `kimi`, `mimo`, `gemini`, `gemma`, `venice`.

---

## Script usage

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/byok-custom-model")
from exports import (
    templates, list_models, get, parse_example,
    list_vendor_models, add, add_template, remove,
)

# Enumerate the 9 curated vendor presets
print(json.dumps(templates(), indent=2))

# One-click registration for a curated vendor
result = add_template(vendor="qwen")
print(json.dumps(result, indent=2))
EOF
```

---

## Functions

| Function | Required args | Purpose |
|---|---|---|
| `templates()` | — | List the 9 curated vendor presets |
| `list_vendor_models(vendor)` | `vendor` | Live `/models` catalog (only if the template has `model_discovery`) |
| `add_template(vendor, *, upstream_model=None, name=None)` | `vendor` | One-click registration for a curated vendor (recommended path) |
| `parse_example(api_example)` | `api_example` | Parse docs API example into a safe draft (non-curated vendors) |
| `add(upstream_model, base_url, ...)` | `upstream_model`, `base_url` | Register from custom args (use after `parse_example`) |
| `list_models()` | — | Show all registered custom entries |
| `get(model_id)` | `model_id` | Inspect one entry |
| `remove(model_id)` | `model_id` | Delete an entry |

All functions return a dict with `ok: True` on success or `ok: False, error: "..."` on failure.

### Handling `need_env_input` (mandatory two-step pattern)

`add()` and `add_template()` may include a `need_env_input` field in their result when the API key env var is not yet set. The script CANNOT pop the secure-input UI itself — it has no access to the user's open SSE stream. The calling agent must do it:

```python
# After add_template / add returns:
if result.get("need_env_input"):
    nei = result["need_env_input"]
    # Call the in-process tool — pseudocode, actual signature is tool-side:
    request_env_input(env_vars=nei["env_vars"], reason=nei["reason"])
```

The popup, the .env write, and the channel-specific UX (web popup / TG card / WeChat text prompt) are all handled by `request_env_input`. Do NOT prompt the user to paste the key in chat as a fallback — just call the tool.

---

## After registration

- The model appears in the selector prefixed with `custom/`.
- User switches via `/model custom/<name>` (e.g. `/model custom/qwen-plus-e3f4`) or the model picker UI.
- Subsequent calls bypass the platform proxy — vendor pricing applies directly to the user's BYOK quota.

---

## Critical rules

- **Never accept an API key pasted in chat.** If the user pastes one, ignore it, refuse to register, and tell them the secure popup is the only safe channel.
- **Never re-issue the secure-input popup automatically** if the user hasn't responded — wait.
- **If `need_env_input` is returned, always call `request_env_input`.** Do not skip, do not ask the user to paste the key, do not retry `add_template` hoping it will pop the UI — it won't.
- **Never write to `workspace/config/custom_models.yaml` or `workspace/.env` by hand.** Always go through the exports above.
- The 9 curated vendors **always** use `add_template`. Only use `parse_example` + `add` for self-hosted or rare providers.
