# Design Process — Engineering Quality Gate (Track A: hand-built UI)

This file defines **engineering implementation quality** for hand-built HTML/CSS/JS.

Style direction is provided via ui-design's Taste Overlay Contract:
- Brief Inference
- Design Dials
- Anti-slop hard rules

Implement style from taste-skill first, then validate with this engineering gate.

---

## Scope

`ui-design` owns:
- accessibility implementation
- theme mechanics (light/dark)
- responsive stability
- interaction-state reliability
- runtime correctness and delivery checklist

`taste-skill` overlay owns:
- style inference and art direction
- layout variation strategy
- visual density and motion intensity style targets
- anti-template/anti-slop style filtering

---

## Mandatory workflow (Track A)

1. Resolve style using taste-skill overlay in ui-design flow.
2. If the page is interactive, write a motion plan before implementation.
3. Build HTML/CSS/JS.
4. Validate against this engineering gate.
5. Run final taste anti-slop check.
6. Deliver only after both gates pass.

### Motion plan requirement for interactive pages

For any interactive UI (buttons, tabs, dropdowns, drawers, modals, sortable lists, drag/swipe gestures), motion is mandatory and must include:
- purpose per motion (feedback, state change, orientation, continuity)
- frequency-aware decision (high-frequency actions should be near-instant or unanimated)
- easing and duration choice (avoid default/browser-generic feel)
- reduced-motion fallback

No motion plan = incomplete implementation.

---

## Required implementation baseline

### 1) Document and structure
- Valid `<!doctype html>`, `charset`, `viewport`
- Semantic landmarks where applicable (`header`, `main`, `nav`, `section`, `footer`)
- One clear `h1`; heading order must be sequential

### 2) Theme system (mandatory)
- Support both light and dark themes
- Use CSS custom properties for color tokens
- Theme toggle persists in `localStorage`
- Initial theme respects `prefers-color-scheme` if no saved choice
- Both themes fully usable (not invert-only)

### 3) Accessibility baseline (mandatory)
- Body text contrast >= 4.5:1
- Large text / UI controls >= 3:1
- Visible keyboard focus on all interactive elements
- Icon-only buttons require `aria-label`
- Inputs require visible `<label>`
- Color is never the only status signal
- Touch targets >= 44×44 on mobile
- Meaningful images require `alt` (decorative use `alt=""`)

### 4) Responsive stability
- No horizontal overflow at 375px width
- Avoid mobile viewport jump: use `100dvh` where full-height is required
- Layout degrades gracefully desktop → mobile

### 5) Interaction reliability
- Never use `transition: all`
- Animate safe properties for common UI (`transform`, `opacity`)
- Deterministic states: default / hover / active / disabled / loading
- For interactive pages, include tactile motion feedback (e.g., press scale, state transition, enter/exit transition)
- For actions >300ms, show loading feedback (skeleton preferred)
- Keyboard-triggered high-frequency actions should be instant or near-instant (avoid decorative animation)

### 6) Motion safety
- Respect `prefers-reduced-motion: reduce`
- Reduce or disable non-essential motion when requested

### 7) Forms and feedback
- Required fields visibly marked
- Validation errors shown near related fields
- Destructive actions require confirmation
- Success/error feedback explicit after submit actions

---

## Charts / data UI (if present)

- Theme-aware chart colors (token-driven)
- Theme switch refreshes chart palette correctly
- Axes/tooltips/legends readable in both themes
- Never use fabricated production data

---

## Technical hard-fail list

- Missing dark theme or broken theme toggle
- Contrast below threshold for core text/UI
- No visible keyboard focus
- Horizontal overflow on mobile
- Broad use of `transition: all`
- Missing disabled/loading behavior on actionable controls
- Icon-only controls without labels
- Interactive page shipped with no motion feedback for interactions/state changes

---

## Pre-delivery checklist (blocking)

### Accessibility
- [ ] Contrast passes (body >=4.5:1, large/UI >=3:1)
- [ ] Keyboard focus visible and usable
- [ ] Heading hierarchy valid with one `h1`
- [ ] Inputs have visible labels
- [ ] Icon-only controls have `aria-label`
- [ ] Touch targets >=44×44 on mobile

### Theme
- [ ] Light/dark toggle works
- [ ] Theme preference persists via `localStorage`
- [ ] `prefers-color-scheme` default works
- [ ] Both themes readable and complete

### Responsive
- [ ] No horizontal scroll at 375px
- [ ] Full-height areas use `100dvh` where needed
- [ ] Core interactions usable on desktop and mobile

### Motion / interaction
- [ ] Reduced-motion path implemented
- [ ] No `transition: all`
- [ ] Hover/active/disabled/loading states are clear
- [ ] Interactive pages include tactile feedback + state-transition motion
- [ ] High-frequency keyboard actions are instant or nearly instant

### Runtime quality
- [ ] No broken asset references
- [ ] No runtime-breaking console errors in core path
- [ ] Key panels handle empty/loading/error states
