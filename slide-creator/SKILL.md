---
name: slide-creator
version: 2.0.0
description: "Create presentation slide decks as HTML and auto-export to 16:9 PDF. Use when the user asks to make a PPT, slide deck, presentation, or pitch deck. Final output is a PDF file — not PowerPoint format."

metadata:
  starchild:
    emoji: "🎞️"
    skillKey: slide-creator
    install:
      - kind: pip
        package: playwright
      - kind: pip
        package: PyMuPDF

user-invocable: true
---

# Slide Creator — HTML → PDF Presentations

Build slide decks as HTML, export to pixel-perfect 16:9 PDF via headless Chromium.

**Output format: PDF** — not Microsoft PowerPoint (.pptx). The PDF preserves exact layout, fonts, and colors across all devices.

## Why HTML → PDF

- CSS layout (Grid/Flexbox) is far more flexible than any PPT editor
- Full web typography, gradients, SVG, animations (print degrades gracefully)
- Git-friendly, reproducible, scriptable
- One command → PDF with exact 16:9 page dimensions

## Workflow

### 1. Plan the Deck

Define slide count and content per slide. Each slide = one `<section class="slide">`.

### 1.5 Art Direction (run this before building)

> Run this step whenever the user hasn't provided a specific visual style.
> Read `skills/slide-creator/references/art-direction.md` for the full style taxonomy,
> CSS token templates, and style-brief output format.

**Step A — Ask 3 questions:**
1. 受众与场景：给谁看、什么场合（投资人/内部/公开演讲）？
2. 情绪关键词：希望观众感受到什么（专业权威 / 创意活力 / 亲切友好 / 极客酷炫）？
3. 品牌约束：有没有指定的品牌色、logo、字体？

**Step B — Search for references:**
Use `web_search` with patterns from art-direction.md to find 2–3 real examples.
Search target: Dribbble, Behance, or design blogs with relevant style + industry keywords.

**Step C — Present 3 style options:**
Each option includes: style name, mood description, color swatches (bg/surface/accent), font pair, and why it fits their content.
Show the search results as supporting references.

**Step D — Generate style-brief.md:**
Once user selects a style, write a `style-brief.md` (template in art-direction.md) in the project directory.
All subsequent HTML/CSS work must follow this brief.

### 2. Choose a Theme

If Art Direction was completed, the `style-brief.md` is the theme spec — skip this table.
Otherwise, use as a quick fallback:

| Style | Background | Accent | Font | Mood |
|-------|-----------|--------|------|------|
| Dark tech | `#000` / `#0a0a0a` | bright orange/blue/green | Inter, Space Grotesk | Bold, modern |
| Light clean | `#fff` / `#f8f8f8` | navy, teal, coral | Inter, DM Sans | Professional, minimal |
| Gradient | dark gradient | vibrant accent | Any sans-serif | Creative, energetic |
| Corporate | `#1a1a2e` / white | brand color | system fonts | Trustworthy, formal |
| Playful | soft pastels | warm pop colors | Nunito, Poppins | Friendly, casual |

### 3. Build HTML + CSS

Create a project directory with `index.html` + `styles.css`.

**Start from `assets/base.css`** — structural skeleton (slide dimensions, print rules, layout helpers) with NO colors or fonts. Layer your theme on top:

```css
/* Example theme layer — customize freely */
body {
  font-family: 'Inter', sans-serif;
  color: #fff;
  background: #000;
}
.slide { background: #0a0a0a; }
.slide-tag { background: rgba(0,120,255,0.15); color: #0078ff; }
.card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); }
```

**Mandatory structural rules** (in base.css — don't remove):

```css
.slide { width: 1280px; height: 720px; page-break-after: always; overflow: hidden; }
@page { size: 1280px 720px; margin: 0; }
```

**Key rules:**
- Use `px` units — never `vh/vw/rem/%` for slide dimensions
- Google Fonts: use `<link>` in `<head>`, export script waits for network idle
- Viewport meta: `<meta name="viewport" content="width=1280">`
- Content must fit within 720px height — overflow is clipped

### 4. Preview (Optional)

Use `preview_serve` to preview in browser before exporting.

### 5. Export to PDF

```bash
python3 skills/slide-creator/scripts/export_pdf.py --dir <project-dir> --output output/<name>.pdf
```

Options:
- `--dir` — directory containing `index.html` (required)
- `--output` / `-o` — output PDF path (default: `<dir>/deck.pdf`)
- `--width` — slide width in px (default: 1280)
- `--height` — slide height in px (default: 720)

### 6. Verify

The script prints slide count and confirms output path. Extra check:

```python
import fitz
doc = fitz.open("output/deck.pdf")
print(f"Pages: {doc.page_count}")
for p in doc:
    r = p.rect
    print(f"  {r.width*96/72:.0f}x{r.height*96/72:.0f}px")
```

## Style Guidelines

- **No default brand** — every deck gets a theme tailored to its content
- Prefer Art Direction-first workflow (questions → references → user pick → `style-brief.md`)
- Ask the user for preference: dark/light, accent color, font, mood
- Each slide should have clear visual hierarchy: tag → title → content
- Keep text concise — slides are visual, not documents
- Use `.bg-glow` with theme-colored radial gradients for depth
- When user asks for "美术建议/风格建议", always provide at least 3 concrete style routes with examples before coding
- Build HTML strictly against chosen style brief, then export PDF (do not skip brief unless user explicitly opts out)

## Gotchas

- **Chromium deps**: first run needs `python3 -m playwright install chromium && python3 -m playwright install-deps chromium`
- **Fonts**: Google Fonts need HTTP — the export script starts a local server automatically
- **Emoji rendering**: headless Chromium may lack emoji fonts — use SVG icons instead
- **Large images**: embed as base64 or use relative paths (local server serves the project dir)
- **Slide overflow**: content exceeding 720px height is clipped — design within bounds
