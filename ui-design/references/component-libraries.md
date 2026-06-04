# Component Libraries — shadcn/ui · HeroUI · coss ui (Track B)

Open-source component libraries do the boring, error-prone work for you: accessible primitives, keyboard handling, focus management, consistent spacing, dark mode, and battle-tested component APIs. Reaching for one **reduces the amount of markup/CSS you hand-write and raises the floor on quality** — you spend your effort on layout, data, and taste instead of re-deriving a date picker.

> **Core rule of this file: never paste component source into this skill, and never rely on memorized component APIs.** These libraries ship fast and their APIs drift. Always *look up the current component and its props at build time* from the sources listed below (docs page, `llms.txt`, MCP server, or CLI registry). Memorized snippets are how you ship broken props. Treat the library's own docs/registry as the source of truth, every time.

---

## When a component library is the right tool

| Situation | Use a component library? |
|-----------|--------------------------|
| Static HTML preview, quick dashboard, no build step | **No** — hand-build with Track A (`design-process.md`) + CDN Tailwind/Chart.js. React libraries need a bundler. |
| Real React / Next.js / Vite app the user will keep and extend | **Yes** — pull components, don't hand-roll. |
| App with forms, modals, dropdowns, tables, date pickers, command palettes | **Yes** — these are exactly what the libraries get right and what hand-rolled code gets wrong (a11y, focus traps, keyboard). |
| User explicitly wants "shadcn", "HeroUI", "Cal.com style", "Origin UI" | **Yes** — use the named one. |
| Tiny widget, email HTML, or anything without a build step | **No** — Track A. |

**The build-step reality (Starchild `preview`):** shadcn/ui, HeroUI, and coss ui are all **React + Tailwind**. They require a bundler (Vite or Next.js) and a `preview` started with a `command` + `port`, not the static file server. If the task is a throwaway preview with no build, stay on Track A. If you're scaffolding a real app, set up Vite + Tailwind first, then add the library. (HeroUI's raw CSS can be applied to plain HTML via Tailwind, but its component *behavior* is React — don't fake it.)

---

## The three libraries at a glance

| | shadcn/ui | HeroUI v3 | coss ui |
|---|-----------|-----------|---------|
| Former name | — | NextUI | Origin UI |
| Primitives | Radix UI (and Base UI option) | React Aria Components | Base UI |
| Styling | Tailwind | Tailwind v4 | Tailwind |
| Distribution | **Copy-paste** via CLI/registry — you own the source | **npm package** — a living, auto-updating library | **Copy-paste** — you own the source |
| You maintain the code? | Yes (it's in your repo) | No (you update the package) | Yes (it's in your repo) |
| License | MIT | Apache 2.0 | open source (COSS) |
| Maturity | Very mature, huge ecosystem | Stable, production-ready | Early access / beta (Base UI also beta) |
| Best when | You want full control + the biggest registry ecosystem | You want polish out-of-the-box with zero maintenance | You want dense, production-grade Cal.com-style UI and you're OK with churn |

**Copy-paste vs package, in one line:** copy-paste (shadcn, coss ui) = maximum control, you edit files directly, you own upgrades. Package (HeroUI) = minimum maintenance, you `npm update` and bug fixes/new features arrive for free, but customization is via props/CSS vars/slots rather than editing source.

---

## How each one helps the agent (and how to look things up)

### shadcn/ui — the registry + CLI + MCP model

What it gives you: a CLI that copies a component's *source* into your project, plus a registry system so the same workflow pulls from the official registry, third-party registries, or a private one. This is the single biggest lever for "reduce agent work" because the agent never writes the component — it requests it by name and gets correct, accessible source.

**Where to look things up (in priority order):**
1. **MCP server** (best for AI): add to the project's MCP config and drive it with natural language.
   ```jsonc
   // .mcp.json  (Claude Code / Codex / Cursor / VS Code all supported)
   { "mcpServers": { "shadcn": { "command": "npx", "args": ["shadcn@latest", "mcp"] } } }
   ```
   Then prompt: "list components in the shadcn registry", "add button, dialog, card", "build a login form from shadcn". The MCP bridges your assistant ↔ registry ↔ CLI.
2. **CLI** (works without MCP): `npx shadcn@latest init` once, then `npx shadcn@latest add <component>` (e.g. `add button card dialog`). For namespaced/third-party registries: `npx shadcn add @<registry>/<component>`.
3. **Docs site** for the current component API and examples: `https://ui.shadcn.com/docs/components/<name>` — read this for props/anatomy before wiring, do not guess.
4. **Registry directory** (browse what's installable, incl. third-party): `https://ui.shadcn.com/docs/directory`.
5. **Registries config** lives in `components.json` under `"registries"` — multiple sources, private ones via `"headers": { "Authorization": "Bearer ${TOKEN}" }`.

Workflow: `init` → discover via MCP/directory → `add` the components you need → read the docs page for each component's props → compose. Never hand-write a shadcn component.

### HeroUI v3 — the package + llms.txt + MCP model

What it gives you: a maintained npm package of polished, accessible React components (React Aria under the hood). Because it's a package, you don't carry or maintain component source — you import and update. "Beautiful by default" means less time spent styling.

**Where to look things up:**
1. **Quick start / install:** `https://heroui.com/docs/react/getting-started` (and `quick-start`). Install `@heroui/react` (or per-component packages to shrink the CSS bundle). Needs Tailwind CSS v4 + React 19.
2. **`llms.txt`** — HeroUI publishes an AI-readable index of the library. Fetch it to get an accurate, current map of components and APIs instead of relying on memory. (Linked from the docs; check `heroui.com` for the current `llms.txt` path.)
3. **MCP server** — HeroUI ships an MCP for code generation; configure it the same way as shadcn's and ask for components by name.
4. **Per-component docs:** `https://heroui.com/docs/components/<name>` — read for props, slots, and the `isDisabled`/`onPress` React-Aria-style API conventions before using.
5. **Plain HTML escape hatch:** the CSS can be applied to plain HTML (see HeroUI's Tailwind Play example) — useful if you want HeroUI's *look* in a non-React page, but you lose the component behavior.

Workflow: install package → fetch `llms.txt` (or use MCP) to confirm the component exists and its current props → import + use. Customize via Tailwind utilities, CSS variables, BEM-style modifiers, or by composing the component's parts/slots.

### coss ui (Origin UI) — copy-paste, Base UI, layered model

What it gives you: copy-paste components built on **Base UI** (not Radix), styled with Tailwind — the design system Cal.com is adopting. Explicitly written to be "clear, readable, predictable" so LLMs can reason about and modify them. Good when you want dense, production-grade UI and are comfortable with beta churn.

Its layered model (pick the abstraction you need):
- **Primitives** — unstyled, accessible Base UI building blocks (the foundation).
- **Particles** — pre-assembled patterns (auth forms, tables, date pickers) — `https://coss.com/ui/particles`.
- **Atoms** — API-enhanced particles that wire UI to real data/services (e.g. Cal.com scheduling) — `https://cal.com/atoms`.

**Where to look things up:**
1. **Docs / intro:** `https://coss.com/ui/docs`.
2. **Component search:** `https://coss.com/ui` (and the search page) to find a component, then copy its current source.
3. **Migration guide** if coming from shadcn/Radix: `https://coss.com/ui/docs/radix-shadcn-migration`.
4. **Base UI docs** for the underlying primitive behavior/props: `https://base-ui.com/`.

Workflow: search the component on coss.com → copy the current source into your repo → adjust. Because it's early access + Base UI is beta, re-check the docs each time rather than trusting an earlier copy.

---

## Decision shortcut

```
Need a React app with components?
├─ Want zero maintenance, polished defaults, just update a package   → HeroUI
├─ Want to own/edit every component + the largest registry ecosystem → shadcn/ui
└─ Want Cal.com-style dense production UI on Base UI (OK with beta)  → coss ui
Single-file preview / no build step                                 → Track A (hand-built, design-process.md)
```

When the user names a library, use it. When they don't and a build step is justified, default to **shadcn/ui** (largest ecosystem, MCP + CLI make it the lowest-effort for an agent) unless "zero maintenance" or "Cal.com look" points elsewhere.

---

## Non-negotiables when using any library

- **Look up before you wire.** Open the component's current docs page (or MCP/`llms.txt`) and confirm props/anatomy. Do not write component code from memory.
- **One library per project.** Don't mix shadcn + HeroUI component sets; you'll get clashing tokens and duplicated primitives.
- **Taste still comes from you.** The library gives correct, accessible components; it does NOT give a point of view. Apply the palette, typography, layout rhythm, anti-slop and copy rules from `design-process.md` on top — otherwise every library app looks identically generic.
- **Theme via the library's tokens**, not ad-hoc hex. shadcn → CSS variables in `globals.css`; HeroUI → its theme/CSS vars + Tailwind; coss ui → its token layer. Keep the Track-A color discipline (no AI-default blue/purple, scene-anchored dark) but express it through the library's theming system.
- **Verify it renders.** After scaffolding, actually start the dev server / build and check the preview. A component that imports but throws at runtime is not done.
