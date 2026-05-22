---
name: byok-custom-model
version: 2.3.2
description: |
  Register a custom LLM endpoint with your own API key for chat in Starchild.

  Use when adding a personal Anthropic, OpenAI, Grok, Qwen, DeepSeek, NEAR AI, or Venice key as a chat model (e.g. add my Claude key, register DeepSeek).
author: starchild
delivery: script
protected: true
tags: [byok, custom-model, llm, openrouter, anthropic, openai, xai, grok, deepseek, qwen, kimi, mimo, gemini, venice, near-ai, tee, confidential-inference]

---

# 🔑 BYOK — Custom LLM Models

Register a custom LLM endpoint to the model selector. Bypasses the platform proxy — the user supplies their own API key, the agent hits the vendor / aggregator directly (OpenRouter, DashScope, Anthropic native, NEAR AI Cloud TEE, self-hosted, etc.).

This is a **script-mode skill** — no tools registered. Read this file, then call the exports from a `bash` block.

## See also
- `config/context/references/model-onboarding.md` — broader model selection / OAuth context
- `chatgpt-codex-onboarding` skill — for ChatGPT/Codex OAuth (different mechanism, NOT BYOK)

---

## Curated vendors (always check this first)

The skill ships with 11 pre-configured vendors. **Always match the user's intent against this list before asking for any URL, model name, or API example** — base_url / wire / thinking / capabilities are all pre-filled, so a curated match goes straight to `add_template(vendor=...)`.

| Vendor id | Use when user mentions… |
|---|---|
| `anthropic` | Claude, Anthropic |
| `openai` | GPT-4o, GPT-5, OpenAI direct |
| `xai` | Grok, xAI |
| `qwen` | Qwen, 通义千问, DashScope |
| `deepseek` | DeepSeek |
| `kimi` | Kimi, Moonshot |
| `mimo` | MiMo, 小米 |
| `gemini` | Gemini |
| `gemma` | Gemma |
| `near-ai` | **privacy, TEE, confidential inference, "don't log my data", Web3-native** |
| `venice` | Venice (only if user names it; see Privacy-first tier below) |

---

## Onboarding flow — templates first

1. **Check the curated vendors table above.** If the user's intent matches one, go straight to `add_template(vendor=...)` and skip to step 5. Do NOT ask for a URL.
2. Only if no curated vendor matches: ask the user to paste the provider's official API example from their docs (curl / requests / fetch sample). Tell them **not to include a real API key** — placeholders or fake keys are fine.
3. Run `parse_example` to auto-detect base_url, upstream_model, wire (openai vs anthropic), thinking params, and vendor-specific request fields.
4. Review the draft with the user, then call `add(...)` — the entry is written to `custom_models.yaml`.
5. **If the result contains `need_env_input`, immediately call the `request_env_input` tool** with `env_vars` and `reason` from that payload. This pops the secure-input UI; the user enters the key; it lands in `workspace/.env`. **This step is mandatory — the script cannot pop the UI itself.**

**Privacy-first tier:** `near-ai` and `venice` both target privacy-sensitive users, but NEAR AI is the cleaner integration — Venice's TEE story is itself built on top of NEAR AI + Phala, so going direct to NEAR AI yields a shorter trust chain (Intel + NVIDIA silicon + NEAR's reproducible enclave image; no product-layer proxy in between). Curated NEAR model list is **open-weight TEE-protected only** — NEAR's catalog also proxies Claude / GPT-5 / Gemini Pro under "Anonymized, not TEE-protected" mode, which we deliberately exclude since the entire privacy value-prop here is the hardware enclave.

**Whenever NEAR AI is in scope, always recommend a TEE-protected (privacy) model** — that's the entire reason a user picks NEAR over OpenAI/Anthropic direct. The curated list is already TEE-only, so `add_template(vendor='near-ai')` defaults are safe. If the user asks to register a non-TEE model on NEAR (e.g. NEAR's anonymized Claude passthrough), warn them it weakens the privacy guarantee and recommend they either stay on a curated TEE model or register the upstream vendor directly.

**NEAR AI reasoning protocol:** NEAR uses `chat_template_kwargs` nested under `extra_body` instead of the top-level `reasoning_effort`/`thinking`/`enable_thinking` that other vendors use. The provider handles this automatically via the `nearai_chat_template` thinking_capability rule. Per-model parameter names vary (GLM/Qwen3.5/Qwen3.6 use `enable_thinking`, DeepSeek-V3 uses `thinking`, gpt-oss is always-on). Full spec: [docs.near.ai/cloud/reasoning-models](https://docs.near.ai/cloud/reasoning-models). Default model `Qwen/Qwen3.6-35B-A3B-FP8` works out of the box; `Qwen3.5-122B-A10B` ships with `thinking_mode='disabled'` because its hidden-thinking pattern would otherwise cause `finish=length, content=null` on baseline calls.

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

# Enumerate the 11 curated vendor presets
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
| `templates()` | — | List the 11 curated vendor presets |
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
- The 11 curated vendors **always** use `add_template`. Only use `parse_example` + `add` for self-hosted or rare providers.

---

## xAI Grok — note on the subscription confusion

Users frequently mix up two unrelated xAI products:

- **X Premium / SuperGrok subscription** ($30/mo on x.com) — chat UI access only. **Does not include API access.**
- **console.x.ai** — independent developer account, separate billing. Generates API keys, $25 in promo credits for new accounts, then pay-per-token.

If a user wants to add Grok via BYOK, point them at **https://console.x.ai/** — not x.com / Premium / SuperGrok. The `xai` template's `homepage` field already deep-links to the right place. Hermes / Grok-CLI's OAuth-to-subscription flow relies on a first-party client_id whitelist that xAI does not extend to third-party cloud agents, so the BYOK API-key path is the only realistic integration for hosted products.
