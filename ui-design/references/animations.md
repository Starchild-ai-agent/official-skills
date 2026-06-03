# Animation & Motion Reference

Guidelines and timing standards for UI animation. These are constraints and principles — implement the actual CSS/JS fresh each time based on your design direction.

---

## Core Principles

1. **Animate only `transform` and `opacity`**. Never animate `width`, `height`, `top`, `left`, `margin`, `padding` — they trigger layout recalculation.
2. **No `transition: all`**. Always specify exact properties: `transition: transform 200ms, opacity 200ms`.
3. **No `linear` or default `ease-in-out`**. Use custom cubic-bezier curves that match your design's personality.
4. **Exit faster than enter**. Exit animations should be ~70% of enter duration.
5. **Motion must have purpose**. Every animation should communicate something (feedback, orientation, continuity). Decorative-only animation is noise.
6. **Respect `prefers-reduced-motion`**. Provide a reduced alternative (opacity fade or instant) for every animation.
7. **Delight scales inversely with frequency**. High-frequency interactions (button clicks, tab switches) need near-invisible transitions. Low-frequency moments (page load, first reveal) can be more expressive.

---

## Easing Philosophy

Choose easing curves that match your design's atmosphere. Define them as CSS custom properties, but use your own names and values — don't copy the same curves every time.

**Guidelines for choosing curves:**
- **Entrances and reveals**: Ease-out curves (fast start, gentle landing). The element "arrives" with confidence.
- **Slides and panels**: Slightly less aggressive ease-out. Smooth, continuous movement.
- **Dramatic reveals**: Exponential ease-out for hero animations and page-load sequences.
- **Micro-interactions**: Quick, subtle curves. The user should feel the response, not watch it.

**Never use**: `linear` (robotic), `ease-in` alone (sluggish entrances), default `ease-in-out` (generic, the browser default).

**Real-world easing references** (from major brands — use as starting points, not templates):

| Brand | Signature Curve | Feel |
|-------|----------------|------|
| Apple | `cubic-bezier(0.25, 0.1, 0.25, 1)` | Smooth, confident |
| Stripe | `cubic-bezier(0.4, 0, 0.2, 1)` | Quick start, gentle land |
| Linear | `cubic-bezier(0.16, 1, 0.3, 1)` | Snappy, precise |
| Framer | `cubic-bezier(0.76, 0, 0.24, 1)` | Dramatic, poster-like |
| Spotify | `cubic-bezier(0.3, 0, 0, 1)` | Fast, musical |
| Tesla | `cubic-bezier(0.5, 0, 0, 0.75)` | Engineered, restrained |
| Airbnb | `cubic-bezier(0.2, 0, 0, 1)` | Warm, welcoming |

**Vary your curves between projects**. If every project uses the same cubic-bezier values, the motion becomes an AI signature. Adjust the control points to match the design's energy — snappier for technical tools, softer for editorial, bouncier for playful contexts.

---

## Timing Standards

These are ranges, not fixed values. Choose within the range based on your design's density and energy.

| Element | Enter Duration | Exit Duration | Notes |
|---------|---------------|---------------|-------|
| Button hover/press | 80-150ms | 80-100ms | Should feel instant. High-frequency. |
| Card hover | 150-250ms | 120-180ms | Subtle lift or border change. |
| Tooltip/popover | 120-180ms | 80-120ms | Fast in, faster out. |
| Dropdown/select | 150-250ms | 120-180ms | Match card hover timing. |
| Modal/dialog | 200-300ms | 150-220ms | Scale + opacity. |
| Drawer/panel | 250-350ms | 200-280ms | Slide from edge. |
| Scroll reveal | 400-700ms | — | One-shot, no exit needed. |
| Page load stagger | 300-600ms | — | Stagger delay 30-80ms per item. |

**Asymmetric timing rule**: For high-frequency UI (tabs, toggles, accordions), consider making the entrance near-instant (0-50ms) and only animating the exit (100-150ms). The user's action should feel immediate.

---

## Scroll Reveal

Every page should have scroll reveal on content sections. Use IntersectionObserver to add a class when elements enter the viewport.

**Implementation approach** (not a template — write fresh each time):
1. Mark revealable elements with a data attribute or class
2. Set their initial state in CSS (hidden: reduced opacity, slight transform offset)
3. Create an IntersectionObserver that adds a "visible" class on intersection
4. The "visible" class transitions to the final state using your easing variables
5. Unobserve after revealing (one-shot, not toggle)

**Reveal styles** — choose ONE per page and use it consistently:
- Fade up: opacity 0 + slight translateY → visible
- Fade in: opacity 0 → visible (simpler, calmer)
- Scale up: opacity 0 + slight scale → visible (more dramatic)
- Slide in: opacity 0 + translateX → visible (directional, editorial)

**Stagger rules for grids/lists:**
- Delay per item: 30-80ms (vary based on energy level)
- Total stagger duration: never exceed 400ms (so max ~5-8 items staggered)
- For longer lists, only stagger the first visible batch

---

## Reduced Motion

Always include a `prefers-reduced-motion` media query that effectively disables animations and transitions. This is a hard requirement, not optional.

The implementation should:
- Set all `animation-duration` and `transition-duration` to near-zero
- Apply to all elements including pseudo-elements
- Use `!important` to override inline styles

---

## Interaction Feedback

- **Button press**: Slight scale-down on `:active` for tactile feedback
- **Card hover**: Subtle lift (translateY) OR border/shadow change. Not both.
- **Link hover**: Color change or underline animation. Keep it simple.
- **Focus**: Visible focus ring for keyboard navigation. Never remove `:focus-visible` styles.

---

## Modal & Overlay Animation

- **Overlay**: Fade in opacity with optional backdrop blur
- **Modal content**: Scale from slightly smaller + fade in. Never start from `scale(0)` — nothing appears from nothing.
- **Drawer**: Slide from edge (translateX or translateY depending on direction)
- **Exit**: Reverse the animation, but faster (70% of enter duration)
- **Overlay and content animate independently** — the overlay fades while the content transforms

---

## Skeleton Loading

- Use a horizontal shimmer effect (gradient sweep from left to right)
- Match skeleton shapes to the content they replace (text lines, avatars, cards)
- Animation: infinite loop, ~1.5s duration
- Disable shimmer animation when `prefers-reduced-motion` is active — show static placeholder instead

---

## Anti-Patterns

- ❌ `transition: all` — animates unintended properties, causes jank
- ❌ Animating layout properties (`width`, `height`, `top`, `left`, `margin`)
- ❌ `linear` easing on UI elements
- ❌ Starting from `scale(0)` — nothing appears from nothing
- ❌ Permanent `will-change` — only during active animation
- ❌ `backdrop-blur` on scrolling containers — kills mobile performance
- ❌ Symmetric enter/exit timing — exit should be faster
- ❌ Animations without `prefers-reduced-motion` fallback
- ❌ Bouncy/elastic easing on UI elements (save for marketing/playful contexts only)
- ❌ Same easing curves and timing on every project — vary to match the design's energy
- ❌ Scroll-triggered animations that replay on scroll-up (use one-shot reveals)

---

## GSAP — Advanced Motion Layer (when CSS isn't enough)

[GSAP](https://gsap.com/) (GreenSock Animation Platform) is the production-grade JS animation engine for the moments CSS transitions can't cover: scroll-driven sequences, timelines, text-into-characters reveals, SVG morph/draw, FLIP layout animations, draggable UI. As of **April 2025 it is 100% free including commercial use** (Webflow now sponsors it) — the formerly-paid plugins (ScrollTrigger, SplitText, MorphSVG, DrawSVG, Flip, Physics2D, etc.) are all free. Apache-style open availability, no license gate.

**Why it fits both tracks:** GSAP is framework-agnostic plain JavaScript. It loads via a `<script>` CDN tag with **no build step**, so it works in a single-file Track A preview *and* in a Track B React app. This is the key difference from the component libraries — you can reach for GSAP even in a throwaway preview.

### When to use GSAP vs plain CSS

| Use **CSS transitions/keyframes** (the default) | Reach for **GSAP** |
|--------------------------------------------------|--------------------|
| Hover, press, focus, tab/accordion toggles | Multi-step **timelines** (sequence/overlap several animations precisely) |
| Simple one-shot scroll reveal (IntersectionObserver) | **Scroll-driven** animation: pin sections, scrub progress to scroll, parallax (ScrollTrigger) |
| Modal/drawer enter-exit | **Text reveals** by line/word/char (SplitText) |
| Skeleton shimmer | **SVG** morphing (MorphSVG) or line drawing (DrawSVG) |
| Anything achievable in <10 lines of CSS | **FLIP** layout transitions (animate elements between DOM states), physics, draggable, complex stagger |

Rule of thumb: **don't pull GSAP for what CSS already does well** — it's ~50KB+ and overkill for a button hover. Use it when the motion is a *feature* (a landing-page scroll story, a hero text reveal), not decoration. All the timing/easing/`prefers-reduced-motion` discipline in this file still applies — GSAP makes ignoring it easier, so be disciplined.

### Load it (look up the current version — don't trust a memorized number)

GSAP iterates; **check the current version and exact CDN paths at build time** at [gsap.com/docs/v3/Installation](https://gsap.com/docs/v3/Installation/) (the install helper there generates the right tags). Pattern (Track A, CDN):

```html
<!-- core -->
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
<!-- only the plugins you actually use -->
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/ScrollTrigger.min.js"></script>
<script>
  gsap.registerPlugin(ScrollTrigger); // every plugin must be registered once
</script>
```

Track B (build step): `npm i gsap` → `import gsap from "gsap"` + `import { ScrollTrigger } from "gsap/ScrollTrigger"` → `gsap.registerPlugin(ScrollTrigger)`.

### Core API in three shapes (full reference: [gsap.com/docs/v3](https://gsap.com/docs/v3/))

```js
// 1. Tween — animate to/from. Note: GSAP durations are in SECONDS, not ms.
gsap.to(".box", { x: 200, opacity: 1, duration: 0.6, ease: "power3.out" });
gsap.from(".card", { y: 24, opacity: 0, duration: 0.5, stagger: 0.06 }); // built-in stagger

// 2. Timeline — sequence/overlap with precise control
const tl = gsap.timeline({ defaults: { ease: "power3.out", duration: 0.5 } });
tl.from(".title", { y: 30, opacity: 0 })
  .from(".subtitle", { y: 20, opacity: 0 }, "-=0.3")  // overlap previous by 0.3s
  .from(".cta", { scale: 0.9, opacity: 0 }, "<");      // start with previous

// 3. ScrollTrigger — bind animation to scroll position
gsap.from(".reveal", {
  y: 40, opacity: 0, duration: 0.7,
  scrollTrigger: { trigger: ".reveal", start: "top 80%", once: true } // one-shot
});
```

GSAP has its own named eases (`power1`–`power4`, `expo`, `back`, `elastic`, `circ`, custom via `CustomEase`) — visualize/choose at the [GSAP ease visualizer](https://gsap.com/docs/v3/Eases). Map them to the same atmosphere rules above (ease-out for entrances, restrained for UI; save `elastic`/`back` for playful contexts only).

### Plugins (all free now) — look up usage per-plugin, don't memorize

Don't write plugin code from memory; open the plugin's doc page for current API. Most useful for UI work:

| Plugin | Use for | Docs |
|--------|---------|------|
| **ScrollTrigger** | scroll-scrub, pin sections, reveal-on-scroll, parallax | `/docs/v3/Plugins/ScrollTrigger` |
| **SplitText** | split headings into lines/words/chars for staggered text reveals | `/docs/v3/Plugins/SplitText` |
| **Flip** | animate elements smoothly between two layout/DOM states | `/docs/v3/Plugins/Flip` |
| **DrawSVG** | animate SVG strokes drawing themselves | `/docs/v3/Plugins/DrawSVGPlugin` |
| **MorphSVG** | morph one SVG shape into another | `/docs/v3/Plugins/MorphSVGPlugin` |
| **Draggable** | drag/throw/snap interactions | `/docs/v3/Plugins/Draggable` |

Browse all at [gsap.com/docs/v3/Plugins](https://gsap.com/docs/v3/Plugins/).

### React: use the official hook

In a React/Next app, don't call GSAP in a raw `useEffect` — use **`useGSAP()`** from `@gsap/react`. It scopes selectors to a container ref and auto-cleans up all animations/ScrollTriggers on unmount (prevents the classic memory-leak + duplicate-trigger bugs). See [gsap.com/resources/React](https://gsap.com/resources/React/).

```js
import { useGSAP } from "@gsap/react";
const container = useRef();
useGSAP(() => {
  gsap.from(".item", { y: 20, opacity: 0, stagger: 0.05 });
}, { scope: container }); // selectors resolve inside container; cleanup automatic
```

### GSAP non-negotiables

- **Register every plugin once** (`gsap.registerPlugin(...)`) before use, or it silently no-ops.
- **Durations are seconds.** `duration: 0.3`, not `300`.
- **`prefers-reduced-motion` still applies.** Guard scroll/timeline animations: if the user prefers reduced motion, skip the animation or jump to the end state. Wrap setup in `gsap.matchMedia()` or a `matchMedia("(prefers-reduced-motion: reduce)")` check — a flashy GSAP scroll story with no reduced-motion path is a defect.
- **Clean up.** In SPAs, kill ScrollTriggers/timelines on teardown (React: `useGSAP` does this for you; vanilla: keep refs and `.kill()` / `ScrollTrigger.getAll().forEach(t => t.kill())` on route change).
- **Don't GSAP-animate what CSS does fine.** Reserve it for timelines, scroll, text, SVG, FLIP, physics, drag.
- **Still animate `transform`/`opacity`**, not layout properties — GSAP doesn't exempt you from compositor rules.
- **Look up current version + plugin APIs at build time** from gsap.com — don't ship memorized snippets for fast-moving plugins.
