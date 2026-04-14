# Art Direction Reference

Detailed visual style vocabulary for building HTML slides.

---

## Style Taxonomy

### 1. Dark Tech Minimal
**Mood:** Bold, modern, premium  
**Industries:** SaaS, AI, developer tools, startups  
**Search keywords:** `"dark UI presentation" "dark minimal slide deck" site:dribbble.com`

```
Background:   #000 / #0a0a0a / #0d0d0d
Surface:      rgba(255,255,255,0.04) borders rgba(255,255,255,0.08)
Accent:       #3b82f6 (blue) / #10b981 (green) / #f59e0b (amber)
Text:         #fff / #e5e7eb / #9ca3af
Font:         Inter, Space Grotesk, JetBrains Mono (mono accents)
Radius:       6–12px
Glow:         radial-gradient(ellipse at top, rgba(accent,0.15) 0%, transparent 60%)
```

---

### 2. Light Clean Corporate
**Mood:** Trustworthy, professional, readable  
**Industries:** Finance, consulting, enterprise, legal  
**Search keywords:** `"clean white presentation" "corporate slide design" site:behance.net`

```
Background:   #fff / #f8fafc
Surface:      #f1f5f9 border #e2e8f0
Accent:       #1e40af (navy) / #0f766e (teal) / #7c3aed (violet)
Text:         #0f172a / #374151 / #6b7280
Font:         Inter, DM Sans, Plus Jakarta Sans
Radius:       4–8px
Shadow:       0 1px 3px rgba(0,0,0,0.08)
```

---

### 3. Bold Gradient
**Mood:** Creative, energetic, expressive  
**Industries:** Agencies, design studios, product launches, events  
**Search keywords:** `"gradient slide deck" "colorful presentation design" site:dribbble.com`

```
Background:   linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #0f172a 100%)
Surface:      rgba(255,255,255,0.08) borders rgba(255,255,255,0.12)
Accent:       #a855f7 / #ec4899 / #06b6d4 (vivid, high contrast)
Text:         #fff / rgba(255,255,255,0.7)
Font:         Outfit, Nunito, Sora
Radius:       12–20px
Effect:       blurred blobs (filter: blur(80px)) as background deco
```

---

### 4. Playful Illustration
**Mood:** Friendly, casual, approachable  
**Industries:** Education, consumer apps, HR/culture, NGO  
**Search keywords:** `"playful presentation design" "illustration slide deck" pastel`

```
Background:   #fffbf0 / #f0fdf4 / #fdf4ff (soft warm/cool pastels)
Surface:      #fff border #e9d5ff / #bbf7d0
Accent:       #f97316 (orange) / #8b5cf6 (violet) / #10b981 (green)
Text:         #1f2937 / #4b5563
Font:         Nunito, Poppins, Quicksand
Radius:       16–24px
Decoration:   wavy SVG dividers, rounded blobs, dashed borders
```

---

### 5. Newspaper / Editorial
**Mood:** Authoritative, journalistic, high-information  
**Industries:** Media, research, reports, policy  
**Search keywords:** `"editorial layout presentation" "newspaper style slide" typography`

```
Background:   #fafaf9 / #1c1917 (dark variant)
Surface:      ruled lines (border-bottom: 1px solid #e7e5e4), column grids
Accent:       #dc2626 (red) / #ca8a04 (amber) — used sparingly
Text:         #1c1917 / #57534e (body)
Font:         Playfair Display (headings), Source Serif 4 (body), mono for data
Radius:       0px (sharp, no rounding)
Layout:       multi-column grid, large pull quotes
```

---

### 6. Glassmorphism
**Mood:** Modern, layered, premium light  
**Industries:** Tech, fintech, luxury, mobile apps  
**Search keywords:** `"glassmorphism slide" "frosted glass UI presentation"`

```
Background:   linear-gradient(135deg, #667eea 0%, #764ba2 100%) or photo
Surface:      background: rgba(255,255,255,0.12); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.2)
Accent:       #fff (primary) / #f0f9ff (secondary)
Text:         #fff / rgba(255,255,255,0.8)
Font:         Inter, Figtree, Geist
Radius:       16–24px
Effect:       Multiple glass layers, subtle shadows
```

---

### 7. Monochrome Technical
**Mood:** Precise, systematic, data-first  
**Industries:** Engineering, research, academic, cybersecurity  
**Search keywords:** `"monochrome technical presentation" "data report slide design"`

```
Background:   #111827 / #030712
Surface:      #1f2937 border #374151
Accent:       #34d399 (terminal green) / #60a5fa (signal blue) — exactly one accent
Text:         #f9fafb / #9ca3af
Font:         JetBrains Mono, IBM Plex Mono (code/data), Inter (prose)
Radius:       2–4px
Layout:       dense, grid-aligned, data heavy
```

---

### 8. Warm Startup
**Mood:** Human, optimistic, narrative  
**Industries:** Consumer brands, D2C, social impact, storytelling  
**Search keywords:** `"warm brand presentation" "human centered slide deck" startup pitch`

```
Background:   #fff7ed / #fef3c7 / #1c1917 (dark variant)
Surface:      #fff border #fed7aa
Accent:       #ea580c (orange) / #16a34a (green) / #b45309 (amber)
Text:         #1c1917 / #78350f
Font:         Plus Jakarta Sans, Lora (serif headings), DM Sans
Radius:       8–16px
Photo style:  warm-toned, human subjects
```

---

## Industry → Style Quick Map

| Industry | Recommended style |
|----------|------------------|
| SaaS / Dev tools | Dark Tech Minimal or Monochrome Technical |
| Finance / Legal | Light Clean Corporate or Newspaper Editorial |
| Creative agency | Bold Gradient or Glassmorphism |
| Education / EdTech | Playful Illustration or Warm Startup |
| AI / Research | Monochrome Technical or Dark Tech Minimal |
| Consumer brand | Warm Startup or Playful Illustration |
| Healthcare | Light Clean Corporate |
| Crypto / Web3 | Dark Tech Minimal or Glassmorphism |
| Government / Policy | Newspaper Editorial or Light Clean Corporate |

---

## CSS Token Templates

Each style above maps directly to a CSS variables block. When building, open the
template for the chosen style and customize accent/font to match user's brand.

### Token structure (use in `<style>` or `styles.css`)

```css
:root {
  --bg-primary:   /* main slide bg */
  --bg-surface:   /* card/panel bg */
  --border-color: /* subtle dividers */
  --accent:       /* primary action color */
  --accent-muted: /* 15% opacity version */
  --text-primary: /* headings */
  --text-muted:   /* body/secondary */
  --radius:       /* border-radius */
  --font-head:    /* heading font */
  --font-body:    /* body font */
}
```

---

## Art Direction Conversation Guide

### 3 key questions to ask the user

1. **Audience & setting** — "这个 deck 是给谁看的？投资人、团队内部、还是公开演讲？"
2. **Mood keyword** — "你希望看完之后观众有什么感觉？（专业权威 / 创意活力 / 亲切友好 / 极客酷炫）"
3. **Brand constraint** — "有没有品牌色、指定字体、或者 logo 需要融入？"

### Search strategy

Use `web_search` with these patterns to find visual references:
- Style-specific: `"dark minimal presentation 2024" site:dribbble.com`
- Industry-specific: `"[industry] pitch deck design" OR "slide design inspiration"`
- Color-specific: `"[color palette name] UI deck slides"`

### Presenting options to user

Present exactly **3 style options**, each with:
- Style name + 1-line mood description
- 3 color hex swatches (bg / surface / accent)
- Font pairing
- Why it fits their content

### style-brief.md output template

```markdown
# Style Brief: [Project Name]

## Chosen Style: [Style Name]

### Color Palette
- Background: [hex]
- Surface: [hex]
- Accent: [hex]
- Text primary: [hex]
- Text muted: [hex]

### Typography
- Heading font: [name + Google Fonts URL]
- Body font: [name + Google Fonts URL]

### Visual Character
- Border radius: [px]
- Surface treatment: [description]
- Special effects: [glow / blur / grain / none]
- Layout density: [minimal / balanced / dense]

### Mood Reference
[1-2 sentence description of the visual feel]

### Search references found
- [URL or description 1]
- [URL or description 2]
```
