---
name: ui-design
version: 1.2.0
description: |
  UI/UX quality gate and build guide for every visual output — landing pages, dashboards,
  web apps, portfolios, and tools. ui-design remains the main entry point.

  Integration model: ui-design main trunk + taste-skill overlay.
  - ui-design owns engineering quality (track selection, component-library strategy,
    accessibility, responsiveness, theming, performance, preview delivery)
  - taste-skill is invoked inside the ui-design workflow for style decisions
    (Brief Inference, Design Dials, Anti-slop hard rules)

  MUST USE together with project-builder whenever a project produces visual HTML/CSS/JS.
metadata:
  starchild:
    emoji: 🎨
    requires:
      bins: []
    install: []
---

# UI Design Skill

This skill is the **single entry point** for visual work.

Use it for any user-facing HTML/CSS/JS output: landing pages, dashboards, product UI, internal tools, and portfolio pages.

---

## Step 1 — Pick the build track

Choose deliberately before coding:

- **Track A (hand-built)**: static preview, vanilla HTML/CSS/JS, quick custom pages
- **Track B (component library)**: React/Vite/Next project using shadcn/ui, HeroUI, or coss ui

Track decision and component-library strategy are always owned by `ui-design`.

---

## Step 2 — Taste Overlay Contract (mandatory)

Inside ui-design workflow, invoke taste-skill for exactly these 3 style blocks:

1. **Brief Inference**
2. **Design Dials** (layout variance / motion intensity / visual density)
3. **Anti-slop hard rules**

### Boundary

- `ui-design` keeps ownership of engineering quality and delivery.
- `taste-skill` provides style direction and anti-template taste constraints.

This avoids overlap with ui-design’s engineering references (component libraries, a11y, preview, data dashboard implementation).

---

## Step 3 — Runtime order (use this every time)

1. Use `ui-design` to select Track A/B.
2. Run taste Brief Inference before writing UI code.
3. Apply taste Design Dials to set style direction.
4. For any interactive page, define a motion plan first (what animates, why, frequency, duration, easing, reduced-motion path).
5. Implement with ui-design engineering rules (a11y/theme/responsive/component strategy/performance).
6. Run taste Anti-slop check as final style gate before delivery.

One sentence summary:
- **taste decides style character**
- **ui-design guarantees robust implementation**

Hard rule: if the page has interactions, motion design is mandatory (at least tactile feedback + state transition feedback). Static-looking interaction states are treated as incomplete UI.

---

## Step 4 — Conflict arbitration

When rules overlap:

- **Style conflict** → taste-skill wins
- **Engineering safety/correctness conflict** → ui-design wins

Engineering safety includes: accessibility, responsive stability, interaction reliability, runtime correctness, and performance constraints.

---

## Step 5 — Where to read/download taste-skill (no local mirror)

Do **not** maintain a local mirror or version-stamp file.

Always read/update taste rules directly from GitHub:

- Repo: `https://github.com/Leonxlnx/taste-skill`
- Main skill to consult: `https://github.com/Leonxlnx/taste-skill/blob/main/skills/taste-skill/SKILL.md`
- Raw download URL: `https://raw.githubusercontent.com/Leonxlnx/taste-skill/main/skills/taste-skill/SKILL.md`
- Full skill package directory: `https://github.com/Leonxlnx/taste-skill/tree/main/skills`

When taste-skill updates, re-check the GitHub source directly and apply needed changes in the ui-design overlay contract.

---

## Engineering references

| File | Purpose |
|------|---------|
| `references/design-process.md` | Engineering quality gate (a11y/theme/responsive/interaction/runtime checklist) |
| `references/component-libraries.md` | shadcn/ui · HeroUI · coss ui selection + lookup workflow |
| `references/animations.md` | Motion implementation standards, interactive-motion requirements (integrated with emil-design-eng decision framework), and GSAP usage notes |
| `references/charts.md` | Chart.js/ECharts implementation patterns |
| `references/dashboards.md` | Data sourcing, real-time updates, dashboard structure, performance |
| taste-skill GitHub source | Read style rules directly from GitHub: `https://github.com/Leonxlnx/taste-skill/tree/main/skills` |
