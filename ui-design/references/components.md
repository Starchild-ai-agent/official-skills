# Component Design Reference

Rules for building UI components. These are constraints and quality standards — not templates to copy. Implement each component fresh based on your design direction.

---

## Navigation

### Sidebar Navigation
- Width: 240-280px, fixed position, full viewport height
- Items: icon (20px) + label, 10-12px vertical padding per item
- Active state: must be visually obvious — background highlight, accent color, or bold text. Pick one approach and commit.
- Mobile: hide sidebar off-screen, reveal with hamburger toggle. Use `transform: translateX` for the slide animation.
- Dividers between nav groups, not between every item

### Top Navigation
- Height: 64-72px (the most common range across 73 major brands; max 80px). Never let the nav eat >10% of the viewport.
- Must render on a single line at desktop (1024px). If items don't fit, condense labels or use hamburger.
- Sticky with `backdrop-filter: blur` on scroll
- Logo left, nav links center or left, actions right
- Active link: distinct from hover state (different treatment)
- Mobile: collapse nav links into hamburger menu

### General Nav Rules
- Never mix sidebar + bottom nav + top nav at the same hierarchy level
- Active state must be visible without relying on color alone
- Navigation placement stays the same across all pages

### Navigation Anti-Example
A top nav with a blurred sticky bar, centered logo, and hamburger on the right looks polished — but when every AI-generated page uses the exact same pattern, it becomes a tell. Vary: logo position, nav link placement (left-aligned vs centered vs right), sticky behavior (always sticky vs sticky-after-scroll vs static), and mobile treatment (hamburger vs bottom tab bar vs slide-out drawer).

---

## Hero Sections

The hero is the first thing users see. It sets the tone for the entire page.

### Structure Discipline
- **Maximum 4 text elements** in the hero stack. Common combinations:
  - Heading + subheading + CTA (3 elements)
  - Eyebrow + heading + subheading + CTA (4 elements — the maximum)
  - Heading + CTA (2 elements — bold and minimal)
- More than 4 text elements creates visual noise and decision paralysis.

### Viewport Fit
- The hero should fill the viewport on load. The primary CTA must be visible without scrolling at 768px viewport height.
- Top padding should not exceed 20vh. Excessive padding pushes content below the fold.

### Layout Variety
- **Not every hero needs to be centered**. Consider:
  - Left-aligned text with right-side visual
  - Split-screen (text left, image/visual right)
  - Asymmetric layout with off-center text
  - Full-bleed image with overlaid text
  - Editorial style with large typography and minimal imagery
- Choose based on the Design Read, not habit. If you always default to centered or always default to split-screen, you're creating a pattern.

### Hero Anti-Patterns
- ❌ Centered heading + 3 equal feature cards below (the #1 AI layout)
- ❌ Hero with more than 4 text elements
- ❌ CTA below the fold at 768px height
- ❌ Div-based fake screenshots as hero images
- ❌ Generic stock photo backgrounds

### Hero Anti-Example
A split-screen hero (text left, gradient orb right) with a geometric sans heading and a single CTA button looks premium — until you realize it's the go-to "anti-centered-hero" that most AI agents converge on. If you find yourself building this exact layout, ask: could this hero be editorial (large serif, minimal imagery)? Could it be full-bleed image with overlaid text? Could it be asymmetric with off-center positioning?

---

## Cards

### Design Rules
- `border-radius`: 8-16px maximum (12px is the most common across 73 major brands). Never 24px+ on cards — that's the AI tell.
- Choose ONE card treatment and use it consistently: border only, shadow only, or background contrast. Never combine thick border + heavy shadow. **Real brand trend**: 60% of major brands prefer hairline borders (1px) over drop shadows for card elevation. Shadows are used sparingly, mainly on hover or for floating elements.
- Shadows should be subtle: max blur 16px, low opacity. Heavy shadows look dated.
- Hover: subtle lift (`translateY(-2px)`) or border color change. Not both.
- Padding: 20-28px. Consistent within the same card type.
- Cards are not the answer to everything. Consider: tables for tabular data, inline lists for simple items, sections with dividers for sequential content.

### Card Anti-Example
Three equal-width cards in a row with an icon on top, a heading, and a short description is the single most common AI card layout. It looks "clean" but is instantly recognizable as generated. Vary: card sizes (span 2 columns for the featured item), mix cards with non-card elements (inline stats, pull quotes), or replace the card grid entirely with a different pattern (accordion, timeline, comparison table).

### Stat/KPI Cards
- Structure: label (small, muted) → value (large, bold, tabular-nums) → change indicator (badge with color)
- Value should be the visually dominant element
- Change badges: green for positive, red for negative. Include direction arrow or +/- sign — don't rely on color alone.
- Optional: sparkline or mini chart below the value

### Content Cards
- Structure: optional icon/image → title → description → optional action
- Don't make every card the same size. Vary grid spans for visual interest.
- If you have 3+ cards in a row that look identical, reconsider the layout.

---

## Buttons & CTAs

### Button Design
- Primary: filled background with accent color. One primary button per view. **Real brand trend**: ~25% of major brands (Nike, Uber, Figma, Shopify, Expo, Intercom) use pure black as their primary CTA color — a confident, editorial choice. ~40% use pill-shaped buttons (border-radius: 9999px), ~30% use sharp corners (0-8px). Commit to one shape system, don't mix.
- Secondary: outlined or ghost (transparent bg + border). For secondary actions.
- Hover: brightness shift or color darken. Not a completely different color.
- Active/press: `scale(0.97-0.98)` for tactile feedback
- Disabled: reduced opacity (0.4-0.5) + `cursor: not-allowed`
- Loading: disable button + show inline spinner. Never let users double-submit.
- Labels: verb + object ("Save changes", "Export data"). Not just "Submit" or "OK".
- Icon buttons: minimum 36×36px touch target. Include `aria-label`.

### CTA Discipline
- **No duplicate intent**: Two CTAs on the same page must not say the same thing. "Get Started" in the hero and "Get Started" in the footer = duplicate intent. Differentiate: "Start free trial" vs "See pricing".
- **Button text wrapping**: CTA text must never wrap to two lines. If it wraps, shorten the text or increase the button's min-width.
- **Contrast check**: Primary CTA must have ≥ 4.5:1 contrast between text and button background. Test this explicitly.
- **One primary per viewport**: At any scroll position, only one primary-styled button should be visible. Multiple competing primaries dilute the call to action.

### CTA Anti-Example
A rounded pill button with a gradient background and a right-arrow icon (→) has become the AI-default "premium CTA". If you catch yourself building this, consider: a sharp-cornered button with no icon, a text-link CTA with an underline animation, a ghost button with a bold border, or a button that uses the page's accent color as a flat fill without gradients.

---

## Tables

- Use `font-variant-numeric: tabular-nums` for number columns — prevents layout shift
- Header row: smaller font, uppercase or muted color, sticky if table is long
- Row hover: subtle background change
- Align numbers and currency to the right
- Wrap table in a container with `overflow-x: auto` for mobile
- Zebra striping is optional — if used, keep the contrast very subtle
- Don't truncate important data. If columns don't fit, prioritize which columns to show on mobile.

---

## Badges & Status

- Shape: pill (`border-radius: 999px`) or rounded rect
- Size: small (font-size 11-12px, padding 2px 8px)
- Semantic colors: green=success, amber=warning, red=error, gray=neutral
- Always pair color with text label or icon — never color alone (accessibility)
- Don't overuse badges. If everything has a badge, nothing stands out.

---

## Forms

- Every input must have a visible `<label>`. Never use placeholder as the only label.
- Input height: 40-44px for comfortable touch targets
- Focus state: accent-colored border + subtle ring shadow. Must be visible.
- Error messages: below the field, in red/error color, with specific guidance ("Email must include @")
- Group related fields visually (fieldset or spacing)
- Required fields: mark with asterisk or "(required)" text
- Submit button: disabled until form is valid, with loading state during submission

### Form Anti-Example
Rounded input fields with a light gray background, no visible border, and a floating label that animates up on focus — this pattern is clean but has become the default AI form style. Vary: use bordered inputs with a visible 1px border, use underline-only inputs for minimal aesthetics, or use a traditional label-above-input layout. The "right" choice depends on the Design Read, not on what looks most modern.

---

## Loading States

- Use skeleton placeholders that match the shape of the content they replace
- Skeleton animation: horizontal shimmer (gradient sweep), not pulsing opacity
- Show skeletons immediately — don't show a blank screen then suddenly populate
- For actions (button clicks, form submits): inline spinner or progress indicator
- If loading takes >3 seconds: show a message explaining what's happening

---

## Empty States

- Never show a blank area. Always show:
  1. An icon or illustration (subtle, not dominant)
  2. A clear title ("No projects yet")
  3. A helpful description ("Create your first project to get started")
  4. A primary action button
- Empty states are an opportunity to guide the user, not just fill space

---

## Tooltips & Popovers

- Appear on hover (desktop) or tap (mobile)
- Position: above the trigger by default, flip if near viewport edge
- Animation: fade + slight translateY, quick timing
- Dismiss: on mouse leave or click outside
- Keep text short (1-2 lines max)
- Use `aria-describedby` for accessibility

---

## Modals & Drawers

- Overlay: semi-transparent dark backdrop with optional `backdrop-filter: blur`
- Modal: centered, scale from slightly smaller + fade in
- Drawer: slides from edge
- Always provide a close button AND clicking the overlay to dismiss
- Trap focus inside the modal while open
- Exit animation should be faster than enter

---

## Icons

- Use ONE icon library per project. Don't mix Lucide with Heroicons with Phosphor.
- Consistent stroke width across all icons
- Sizes: 16px (inline text), 20px (buttons), 24px (navigation)
- Never use emoji as structural icons (navigation, status, actions)
- Emoji is acceptable only in user-generated content or deliberately playful contexts

---

## Data Display

- Numbers: always use `font-variant-numeric: tabular-nums` in data contexts
- Currency: include symbol, use locale-appropriate formatting
- Percentages: include % sign, color-code positive/negative
- Dates: use relative time for recent ("2 hours ago"), absolute for older ("Jan 15, 2026")
- Large numbers: abbreviate with K/M/B suffix (e.g., "12.4K" not "12,400")
- Trend indicators: up/down arrow + color. Green=up is not always correct — for costs, up=red.
