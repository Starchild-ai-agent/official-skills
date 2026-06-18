---
name: ui-templates
version: 1.5.0
description: |
  Human-designed UI template library with 380 templates from 9 professional sources.
  Use for any web page creation: landing pages, portfolios, business sites, dashboards, crypto/web3, etc.
  All templates are real human-designed HTML/CSS/JS — no AI-generated slop.
tags: [templates, ui, web, landing-page, portfolio, business, crypto, web3, surprise-me]
tools: [read_file, write_file, bash, preview_serve]
triggers:
  - "[SURPRISE_ME]"
  - "create a website"
  - "build a landing page"
  - "make a web page"
  - "build me a site"
---

# UI Templates — Human-Designed Template Library

> 380 pre-built HTML/CSS/JS templates from 9 professional template libraries.
> All templates are human-designed with real design quality — NOT AI-generated.
> The agent MUST use an existing template as the starting point. Never write HTML/CSS/JS from scratch.

---

## 1. How to Find Templates

### Step 1 — Determine the Category

Match the user's request to one or more categories from §4 Category Reference.
Be **precise** — match the user's actual stated need, not a generalized assumption.

- "I want a restaurant website" → `restaurant`
- "Build me a portfolio" → `portfolio`
- "I need a blog" → `blog`
- "Make a landing page for my app" → `app` or `landing`
- Unclear or general request → read 2-3 candidate category catalogs and compare

### Step 2 — Read the Category Catalog

Each category has a JSON catalog file: `catalogs/{category}.json` (relative to this skill directory).

```
read_file("skills/ui-templates/catalogs/{category}.json")
```

If no specific category matches, use `catalogs/multipurpose.json`.
For broad requests, read multiple catalogs (e.g., both `personal` and `portfolio`).

### Step 3 — Match Templates Using Catalog Metadata

Each catalog entry contains rich metadata for intelligent selection:

| Field | Type | How to Use |
|-------|------|------------|
| `matchSignals` | string[] | **Primary matching** — keyword array. Match against user's request keywords. |
| `description` | string | 150-700 char detailed visual/structural description. Use to evaluate fit and to present to user. |
| `colorScheme` | `"dark"` / `"light"` / `"mixed"` | Match user's style preference. |
| `visualStyle` | string | One-line visual atmosphere summary. Use to present to user. |
| `layout` | string | `"single-page"` / `"multi-page"` / `"sidebar"` / `"fullscreen"` / `"grid"` / `"dashboard"` |
| `features` | string[] | Functional capabilities (e.g., `"responsive"`, `"search"`, `"accordion"`). |
| `sections` | string[] | Page section types (e.g., `"hero"`, `"pricing"`, `"contact"`). |
| `colorPalette` | object | Full color system with named roles. Use during customization. |
| `typography` | object | Font family, weights, sizes, spacing, style. Use during customization. |
| `source` | string | Template source — indicates quality tier (see §3). |

**Matching priority:**
1. `matchSignals` keyword overlap with user request
2. `features` and `sections` matching user's functional needs
3. `colorScheme` + `visualStyle` matching user's aesthetic preference
4. `source` quality tier (prefer higher tiers)

### Step 4 — Download and Use the Template

Templates are hosted on GCS. Each catalog entry has a `downloadUrl` field pointing to a `.zip` file.

```bash
# Download and extract the template
curl -sL "{downloadUrl}" -o /tmp/template.zip
mkdir -p output/website
unzip -o /tmp/template.zip -d output/website/
rm /tmp/template.zip
```

After extraction, use the `indexPath` field from the catalog entry to locate the `index.html` within the extracted directory.

---

## 2. Customization Guide

When customizing a template, focus on content replacement while preserving the human-designed structure:

1. **Page title & headings** — Update `<title>` and main headings
2. **Navigation** — Adjust nav links to match actual sections
3. **Body text** — Replace lorem ipsum with real content
4. **Images** — Keep template originals unless user provides their own
5. **Colors** — Use `colorPalette` to understand which CSS properties to modify for brand colors
6. **Fonts** — Keep the template's fonts (already well-chosen by human designers)
7. **Sections** — Add/remove/reorder sections to match user needs
8. **Responsive** — Most templates are already responsive. Check `breakpoints` field.

---

## 3. Template Sources & Quality Tiers

**Source quality preference**: `web3` > `html5up` > `styleshout` > `startbootstrap` > `tooplate` > `themefisher` > `templatemo`

### Tier 1 — Premium (prefer these)
- **Web3** (14 templates): Crypto/DeFi/NFT dashboards and tools. Dark themes, real-time data, Chart.js. Best for blockchain projects.
- **HTML5 UP** (29 templates): Clean, modern, responsive. Best overall design quality. Pure HTML/CSS/JS.
- **StyleShout** (36 templates): Professional, polished. Great for portfolios and personal sites.
- **Start Bootstrap** (12 templates): Bootstrap-based, well-structured. Good for business sites.

### Tier 2 — Good
- **Tooplate** (88 templates): Large variety, decent quality. Good for specific niches.
- **ThemeFisher** (42 templates): Bootstrap-based, professional.
- **AdminMart** (1 template): Dashboard template.
- **GitHub** (2 templates): Community-contributed templates.

### Tier 3 — Supplementary
- **TemplateMo** (156 templates): Largest collection, variable quality. Good for niche categories.

---

## 4. Category Reference (36 categories)

| Category       | Description                          | Count | Example Use Case                    |
|----------------|--------------------------------------|-------|-------------------------------------|
| `multipurpose` | General-purpose templates            | 83    | Generic websites, quick prototypes  |
| `business`     | Business / Corporate / Consulting    | 56    | Company sites, consulting firms     |
| `personal`     | Personal pages / Resume / CV         | 24    | Personal resume, self-introduction  |
| `blog`         | Blog / Magazine / News               | 20    | Personal blog, news site            |
| `agency`       | Creative agency / Studio             | 21    | Design firms, digital marketing     |
| `restaurant`   | Restaurant / Cafe / Bakery           | 15    | Restaurants, coffee shops, bakeries |
| `crypto`       | Crypto / DeFi / NFT / Web3           | 14    | Trading platforms, wallets, DeFi    |
| `ecommerce`    | E-commerce / Shop / Fashion          | 11    | Online stores, fashion brands       |
| `portfolio`    | Portfolio / Showcase                 | 11    | Designer portfolios, project showcase |
| `app`          | App landing page                     | 11    | Mobile app promotion pages          |
| `dashboard`    | Dashboard / Admin panel              | 11    | Backend admin, data panels          |
| `travel`       | Travel / Hotel / Vacation            | 10    | Travel agencies, hotel booking      |
| `landing`      | Landing page                         | 8     | Product landing pages, sign-up pages |
| `photography`  | Photography / Image showcase         | 7     | Photographer portfolios, galleries  |
| `coming_soon`  | Coming soon / Countdown              | 7     | Product teasers, launch countdowns  |
| `saas`         | SaaS / Hosting services              | 7     | SaaS product pages, cloud services  |
| `event`        | Event / Conference                   | 5     | Conferences, event registration     |
| `fitness`      | Fitness / Sports                     | 5     | Gyms, sports brands                 |
| `automotive`   | Automotive / Taxi / Rental           | 5     | Car dealers, rental services        |
| `other`        | Other / Miscellaneous                | 5     | Uncategorized templates             |
| `gallery`      | Image gallery                        | 4     | Photo galleries, art exhibitions    |
| `nature`       | Nature / Eco / Organic               | 4     | Environmental orgs, organic brands  |
| `beauty`       | Beauty / Salon / SPA                 | 4     | Beauty salons, barber shops         |
| `food`         | Food / Recipes                       | 3     | Food blogs, recipe sharing          |
| `medical`      | Medical / Healthcare                 | 4     | Clinics, medical services           |
| `real_estate`  | Real estate / Interior design        | 4     | Real estate agencies, interior design |
| `technology`   | Technology / Innovation              | 4     | Tech companies, innovation products |
| `component`    | UI components                        | 4     | Forms, admin panel components       |
| `music`        | Music / Band                         | 3     | Bands, musicians                    |
| `education`    | Education / Training                 | 3     | Schools, online courses             |
| `charity`      | Charity / Nonprofit                  | 2     | Charity organizations               |
| `wedding`      | Wedding                              | 1     | Wedding invitations                 |
| `construction` | Construction / Building              | 1     | Construction companies              |
| `coworking`    | Coworking space                      | 1     | Coworking spaces                    |
| `job`          | Job / Career                         | 1     | Job portals                         |
| `wellness`     | Wellness / Meditation                | 1     | Meditation, mental health           |

---

## 5. Catalog Entry Format

Full example of an enriched catalog entry:

```json
{
  "id": "html5up-editorial",
  "source": "html5up",
  "dir": "html5up/editorial",
  "name": "Editorial",
  "title": "Editorial by HTML5 UP",
  "category": "blog",
  "hasIndex": true,
  "hasCss": true,
  "hasJs": true,
  "hasImages": true,
  "sizeKB": 3531,
  "indexPath": "html5up/editorial/index.html",
  "description": "Sidebar-layout blog/magazine template with a persistent left sidebar...",
  "colorScheme": "light",
  "primaryColor": "#f56a6a",
  "colorPalette": {
    "background": "#ffffff",
    "sidebarBg": "#f5f6f7",
    "text": "#7f888f",
    "heading": "#3d4449",
    "accent": "#f56a6a (coral-red)",
    "accentHover": "#f67878",
    "accentActive": "#f45c5c",
    "border": "#eff1f2",
    "muted": "#9fa3a6"
  },
  "typography": {
    "fontFamily": "Open Sans (body) + Roboto Slab (headings)",
    "headingWeight": "700",
    "bodyWeight": "400",
    "bodySize": "13pt",
    "letterSpacing": "wide (0.075em)",
    "style": "Serif+sans-serif dual font pairing. Editorial sophistication."
  },
  "layout": "sidebar",
  "layoutDetails": "Two-column: fixed left sidebar + scrollable main. Sidebar collapses to hamburger on mobile.",
  "visualStyle": "Editorial, magazine-like. Coral-red accent. Serif+sans-serif font pairing.",
  "features": ["responsive", "search", "hamburger-menu", "social-links", "accordion"],
  "sections": ["header", "navigation", "hero", "features", "blog", "contact", "footer"],
  "techStack": ["jquery", "font-awesome", "google-fonts"],
  "breakpoints": [360, 480, 736, 980, 1280, 1680],
  "matchSignals": ["blog", "magazine", "editorial", "sidebar", "search", "articles", "coral", "serif"]
}
```

---

## 6. Important Notes

- **All 380 templates are usable** — every template has an `index.html` file. Use `indexPath` to find it under `ui-templates/`.
- **Category catalogs** — read `catalogs/{category}.json` for enriched metadata.
- **Keep the human design** — these templates look good because humans designed them. Don't over-modify the CSS structure.
- **Use colorPalette for customization** — when the user has brand colors, use `colorPalette` to understand which CSS colors to replace.
- **Responsive** — most templates are already responsive. Check `breakpoints` for responsive behavior.
