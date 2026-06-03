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
