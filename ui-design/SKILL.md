---
name: ui-design
version: 1.0.3
description: |
  The UI/UX quality gate and build guide for every visual output — landing pages, dashboards,
  web apps, portfolios, tools, any HTML the user will see. Merges visual-design methodology
  (palette, typography, layout, anti-AI-slop) with concrete build guidance, including when and
  how to use open-source component libraries (shadcn/ui, HeroUI, coss ui) to reduce work and
  raise quality.

  MUST USE together with project-builder whenever a project produces visual HTML/CSS/JS.
  project-builder owns the engineering workflow; this skill owns how the result looks and feels.
metadata:
  starchild:
    emoji: 🎨
    requires:
      bins: []
    install: []
---

# UI Design Skill

Make every visual output look like a professional designed it — never generic AI slop — while doing the least hand-work necessary. This skill is the single entry point for all UI/UX decisions; it replaces the older `project-design` and `dashboard` skills.

## When to use

Any time you generate HTML/CSS/JS the user will see: landing page, dashboard, web app, portfolio, internal tool, settings page, a single chart panel — anything visual. If it renders, this skill applies.

---

## Step 1 — Pick the track

Two ways to build a UI. Choose deliberately; they are not interchangeable.

| | **Track A — Hand-built** | **Track B — Component library** |
|---|--------------------------|----------------------------------|
| What | You write the markup + Tailwind/CSS yourself | You pull accessible React components from shadcn/ui, HeroUI, or coss ui |
| Best for | Single-file previews, quick dashboards, emails, anything with **no build step** | Real React/Next/Vite apps with forms, modals, tables, date pickers the user will keep |
| Build step | None — static `preview` | Bundler required (Vite/Next) + `preview` with `command`+`port` |
| Read | `references/design-process.md` (+ aesthetics/components/animations/charts) | `references/component-libraries.md` |

Decision shortcut:
```
No build step / throwaway preview / static files only          → Track A
Real app, lots of interactive components, user will extend it  → Track B
User named "shadcn" / "HeroUI" / "Cal.com look" / "Origin UI"  → Track B (that library)
Just a dashboard?                                              → either track + references/dashboards.md
```

**Taste is required on both tracks.** A component library gives correct, accessible parts — it does NOT give a point of view. The palette / typography / layout-rhythm / anti-slop / copy rules from `design-process.md` apply on top of the library, or every app looks identically generic.

---

## Step 2 — Always-on design discipline (both tracks)

These are the non-negotiables. Full methodology, banned-value lists, and the pre-delivery checklist are in `references/design-process.md` — read it before writing markup on Track A, and for the taste layer on Track B.

1. **Design Read first.** One line: page type · audience · atmosphere · aesthetic family · light/dark/tinted. Every later choice serves it.
2. **Spin the Design Dials** (Track A) to avoid converging on the same dark-blue-card layout every time: Surface · Accent · Typography · Aesthetic Family, derived from the current UTC time. User-stated preferences always override the dials.
3. **Anchor dark surfaces with a Scene Sentence** — never default to `#0a-#0f` blue-black.
4. **Banned by default:** Inter/Roboto/Arial fonts; generic blue (`#3b82f6`) and AI purple (`#8b5cf6`/`#6366f1`); cream/beige backgrounds; blue-black dark; em-dashes in copy; marketing buzzwords; centered-hero-plus-three-cards; `border-radius > 16px` on cards; gradient text; `transition: all`; `100vh` (use `100dvh`).
5. **Copy reads human, not LLM.** No buzzwords, no aphoristic "Simple. Fast. Powerful.", no fake-precise numbers, no scroll cues, zero em-dashes.
6. **Accessibility is mandatory:** ≥4.5:1 body contrast, visible focus rings, alt text, sequential headings, `aria-label` on icon buttons, color never the sole signal, 44×44px touch targets, `prefers-reduced-motion`.
7. **Light/dark theme** with a toggle, CSS custom properties, system-preference default, `localStorage` persistence — both themes fully designed, not just inverted.
8. **Refinement pass + checklist before delivery.** The instinct to add more is usually wrong; fix spacing, contrast, and typography instead. Run the pre-delivery checklist in `design-process.md`.

---

## Step 3 — Reduce work with open-source component libraries (Track B)

When there's a build step, don't hand-roll dropdowns, dialogs, and date pickers — that's where hand-written code fails on a11y and keyboard handling. Pull them from a library instead.

| Library | Model | Reach for it when |
|---------|-------|-------------------|
| **shadcn/ui** | Copy-paste via CLI + registry + **MCP** (Radix/Base UI + Tailwind) | Largest ecosystem, you want to own/edit every component; lowest-effort for an agent via MCP/CLI |
| **HeroUI v3** (was NextUI) | **npm package**, auto-updating (React Aria + Tailwind v4) | Polished defaults with zero maintenance; just update the package |
| **coss ui** (was Origin UI) | Copy-paste (Base UI + Tailwind), Cal.com's system | Dense, production-grade Cal.com-style UI; OK with beta churn |

> **Never paste component code into work from memory.** These libraries ship fast and APIs drift. **Look up the current component + props at build time** — via the library's MCP server, its `llms.txt`, its CLI registry, or its docs page. The library's own source is the truth, every time. Exact lookup URLs, CLI/MCP setup, the copy-paste-vs-package tradeoff, and the build-step reality are in `references/component-libraries.md`.

Default when unspecified and a build is justified: **shadcn/ui** (MCP + CLI make it the lowest-effort), unless "zero maintenance" → HeroUI, or "Cal.com look" → coss ui.

### Advanced motion: GSAP (works on BOTH tracks)

Component libraries give you correct components; they don't give you cinematic motion. For scroll-driven storytelling, multi-step timelines, text-into-characters reveals, SVG morph/draw, or FLIP layout transitions, reach for **[GSAP](https://gsap.com/)** — now 100% free (incl. all former-paid plugins: ScrollTrigger, SplitText, MorphSVG, Flip…). Unlike the component libraries, GSAP is plain JS that loads via a CDN `<script>` tag with **no build step**, so it works in a single-file Track A preview *and* a Track B app.

Decision: plain CSS for hovers/toggles/simple reveals (the default — don't pull 50KB for a button); GSAP only when the motion is a *feature* (landing-page scroll story, hero text reveal, animated SVG). Full guidance — when-to-use table, CDN loading, core/timeline/ScrollTrigger API, plugin list, the React `useGSAP` hook, and the reduced-motion/cleanup rules — is in `references/animations.md` (GSAP section). Look up the current version and plugin APIs at gsap.com at build time; don't ship memorized snippets.

---

## AI-generated visual assets (optional quality boost)

When the user wants a premium, polished look — or when the project would benefit from custom imagery (hero backgrounds, logos, decorative illustrations, themed graphics) — load the **image-create** skill and use it to generate visuals with AI.

**When to use:**
- Landing pages, portfolios, or dashboards where a custom hero image would elevate the design
- Projects where the user explicitly wants "better looking" / "more polished" / "premium" output
- Any time a stock photo or generic gradient feels insufficient

**How to use:**
1. Load the `image-create` skill (read its SKILL.md) and follow its instructions to generate an image with a prompt that matches the project's Design Read (atmosphere, aesthetic family, color palette)
2. The generated image is saved to `output/images/`. **You MUST copy it into the project's preview/serve directory** before referencing it in HTML:
   ```
   bash("cp output/images/GENERATED_FILE.png output/projects/{slug}/src/hero.png")
   ```
3. Reference the image with a **relative path** in HTML: `url('./hero.png')` — NOT `url('../images/...')`. Preview can only serve files within its own directory.
4. If image generation fails, fall back to CSS gradients or abstract SVG patterns — never leave a broken `<img>` or `background-image` reference.

---

## Dashboards

For multi-panel monitoring views (portfolio, prices, system health), read `references/dashboards.md` after picking a track: it covers finding real data (Starchild proxied APIs + rate-limit math), real-time updates (polling/SSE/WebSocket), dashboard layout, loading/error/empty states, and performance. Charts setup is in `references/charts.md`. Never put fabricated numbers on a dashboard.

---

## Reference map

| File | Read when |
|------|-----------|
| `references/design-process.md` | The full quality gate — Design Read, Dials, Scene Sentence, all design rules, copy rules, anti-slop tests, theme support, pre-delivery checklist |
| `references/aesthetics.md` | Building a palette / choosing type — methodology + real-brand values + dark-surface tint guide |
| `references/components.md` | Hand-building nav, cards, tables, buttons, forms, hero, CTAs |
| `references/animations.md` | Motion — scroll reveals, hover, modals, entrance strategies, timing, **+ GSAP advanced-motion layer** (timelines, ScrollTrigger, SplitText, SVG, FLIP, useGSAP) |
| `references/charts.md` | Charts — Chart.js/ECharts setup, chart-type selection, mock data |
| `references/component-libraries.md` | shadcn/ui · HeroUI · coss ui — when to use which + how to look up components dynamically |
| `references/dashboards.md` | Data sourcing, real-time, dashboard layout, performance |
