/* ============================================================
   Color Scheme Generator — script.js

   Pure frontend functionality — no external APIs required.
   HSL-based color harmony calculations, WCAG contrast checker,
   and CSS variable export.

   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Register GSAP Plugins ---------- */
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Reduced Motion Check ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    heroImageUrl: (() => {
      const raw = '{{HERO_IMAGE_URL}}';
      if (raw.startsWith('{{')) return '';
      return raw;
    })(),
  };

  /* ============================================================
     COLOR UTILITY FUNCTIONS (HSL-based)
     ============================================================ */

  function hexToRgb(hex) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
    const num = parseInt(hex, 16);
    return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
  }

  function rgbToHex(r, g, b) {
    return '#' + [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
  }

  function rgbToHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;

    if (max === min) {
      h = s = 0;
    } else {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
        case g: h = ((b - r) / d + 2) / 6; break;
        case b: h = ((r - g) / d + 4) / 6; break;
      }
    }
    return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) };
  }

  function hslToRgb(h, s, l) {
    h /= 360; s /= 100; l /= 100;
    let r, g, b;

    if (s === 0) {
      r = g = b = l;
    } else {
      const hue2rgb = (p, q, t) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1/6) return p + (q - p) * 6 * t;
        if (t < 1/2) return q;
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
        return p;
      };
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      r = hue2rgb(p, q, h + 1/3);
      g = hue2rgb(p, q, h);
      b = hue2rgb(p, q, h - 1/3);
    }
    return { r: Math.round(r * 255), g: Math.round(g * 255), b: Math.round(b * 255) };
  }

  function hexToHsl(hex) {
    const { r, g, b } = hexToRgb(hex);
    return rgbToHsl(r, g, b);
  }

  function hslToHex(h, s, l) {
    const { r, g, b } = hslToRgb(h, s, l);
    return rgbToHex(r, g, b);
  }

  function normalizeHue(h) {
    return ((h % 360) + 360) % 360;
  }

  /* ============================================================
     COLOR SCHEME GENERATORS
     ============================================================ */

  function generateScheme(hex, type) {
    const hsl = hexToHsl(hex);
    const { h, s, l } = hsl;
    const colors = [];

    switch (type) {
      case 'complementary':
        colors.push(
          { h, s, l, label: 'Base' },
          { h: normalizeHue(h + 180), s, l, label: 'Complement' },
          { h, s: Math.min(s + 10, 100), l: Math.min(l + 15, 95), label: 'Light' },
          { h: normalizeHue(h + 180), s: Math.min(s + 10, 100), l: Math.min(l + 15, 95), label: 'Light Comp.' },
          { h, s, l: Math.max(l - 20, 5), label: 'Dark' },
          { h: normalizeHue(h + 180), s, l: Math.max(l - 20, 5), label: 'Dark Comp.' }
        );
        break;

      case 'analogous':
        colors.push(
          { h: normalizeHue(h - 30), s, l, label: 'Analogous -30°' },
          { h, s, l, label: 'Base' },
          { h: normalizeHue(h + 30), s, l, label: 'Analogous +30°' },
          { h: normalizeHue(h - 15), s, l: Math.min(l + 12, 95), label: 'Light -15°' },
          { h: normalizeHue(h + 15), s, l: Math.min(l + 12, 95), label: 'Light +15°' },
          { h, s, l: Math.max(l - 18, 5), label: 'Dark Base' }
        );
        break;

      case 'triadic':
        colors.push(
          { h, s, l, label: 'Base' },
          { h: normalizeHue(h + 120), s, l, label: 'Triad 120°' },
          { h: normalizeHue(h + 240), s, l, label: 'Triad 240°' },
          { h, s, l: Math.min(l + 15, 95), label: 'Light Base' },
          { h: normalizeHue(h + 120), s, l: Math.min(l + 15, 95), label: 'Light 120°' },
          { h: normalizeHue(h + 240), s, l: Math.min(l + 15, 95), label: 'Light 240°' }
        );
        break;

      case 'split-complementary':
        colors.push(
          { h, s, l, label: 'Base' },
          { h: normalizeHue(h + 150), s, l, label: 'Split +150°' },
          { h: normalizeHue(h + 210), s, l, label: 'Split +210°' },
          { h, s, l: Math.min(l + 15, 95), label: 'Light Base' },
          { h: normalizeHue(h + 150), s, l: Math.max(l - 15, 5), label: 'Dark +150°' },
          { h: normalizeHue(h + 210), s, l: Math.max(l - 15, 5), label: 'Dark +210°' }
        );
        break;

      case 'tetradic':
        colors.push(
          { h, s, l, label: 'Base' },
          { h: normalizeHue(h + 90), s, l, label: 'Tetrad 90°' },
          { h: normalizeHue(h + 180), s, l, label: 'Tetrad 180°' },
          { h: normalizeHue(h + 270), s, l, label: 'Tetrad 270°' },
          { h, s, l: Math.min(l + 15, 95), label: 'Light Base' },
          { h: normalizeHue(h + 180), s, l: Math.max(l - 15, 5), label: 'Dark 180°' }
        );
        break;

      case 'monochromatic':
        colors.push(
          { h, s, l: 95, label: 'Lightest' },
          { h, s, l: 80, label: 'Light' },
          { h, s, l: 65, label: 'Medium Light' },
          { h, s, l, label: 'Base' },
          { h, s, l: 35, label: 'Medium Dark' },
          { h, s, l: 15, label: 'Darkest' }
        );
        break;
    }

    return colors.map(c => ({
      ...c,
      hex: hslToHex(c.h, c.s, c.l),
      rgb: hslToRgb(c.h, c.s, c.l),
    }));
  }

  /* ============================================================
     WCAG CONTRAST RATIO
     ============================================================ */

  function relativeLuminance(r, g, b) {
    const [rs, gs, bs] = [r, g, b].map(v => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  }

  function contrastRatio(hex1, hex2) {
    const c1 = hexToRgb(hex1);
    const c2 = hexToRgb(hex2);
    const l1 = relativeLuminance(c1.r, c1.g, c1.b);
    const l2 = relativeLuminance(c2.r, c2.g, c2.b);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }

  /* ============================================================
     DOM REFERENCES
     ============================================================ */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  const els = {
    themeToggle: $('#theme-toggle'),
    heroTime: $('#hero-time'),
    colorPicker: $('#color-picker'),
    colorHex: $('#color-hex'),
    previewStrip: $('#preview-strip'),
    schemeTabs: $$('.scheme-tab'),
    colorGrid: $('#color-grid'),
    formatBtns: $$('.format-btn'),
    contrastFg: $('#contrast-fg'),
    contrastFgHex: $('#contrast-fg-hex'),
    contrastBg: $('#contrast-bg'),
    contrastBgHex: $('#contrast-bg-hex'),
    contrastPreview: $('#contrast-preview'),
    contrastScores: $('#contrast-scores'),
    exportCode: $('#export-code'),
    exportCopyBtn: $('#export-copy-btn'),
    heroBgImage: $('.hero__bg-image'),
  };

  /* ---------- State ---------- */
  let currentScheme = 'complementary';
  let currentFormat = 'hex';
  let currentColors = [];

  /* ============================================================
     THEME MANAGEMENT
     ============================================================ */
  function initTheme() {
    const saved = localStorage.getItem('color-scheme-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('color-scheme-theme', next);
  }

  /* ============================================================
     HERO CLOCK
     ============================================================ */
  function updateClock() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const dateStr = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    els.heroTime.textContent = `${dateStr} ${timeStr}`;
    els.heroTime.setAttribute('datetime', now.toISOString());
  }

  /* ============================================================
     HERO BACKGROUND IMAGE
     ============================================================ */
  function initHeroImage() {
    if (CONFIG.heroImageUrl && els.heroBgImage) {
      els.heroBgImage.style.backgroundImage = `url('${CONFIG.heroImageUrl}')`;
      els.heroBgImage.style.backgroundSize = 'cover';
      els.heroBgImage.style.backgroundPosition = 'center';
      els.heroBgImage.style.opacity = '0.12';
    }
  }

  /* ============================================================
     FORMAT COLOR VALUE
     ============================================================ */
  function formatColor(color, format) {
    switch (format) {
      case 'hex': return color.hex;
      case 'rgb': return `rgb(${color.rgb.r}, ${color.rgb.g}, ${color.rgb.b})`;
      case 'hsl': return `hsl(${color.h}, ${color.s}%, ${color.l}%)`;
      default: return color.hex;
    }
  }

  /* ============================================================
     RENDER FUNCTIONS
     ============================================================ */

  function updatePreviewStrip() {
    els.previewStrip.innerHTML = '';
    currentColors.forEach(c => {
      const swatch = document.createElement('div');
      swatch.className = 'strip-swatch';
      swatch.style.background = c.hex;
      els.previewStrip.appendChild(swatch);
    });
  }

  function renderColorGrid() {
    els.colorGrid.innerHTML = '';

    currentColors.forEach((color, i) => {
      const card = document.createElement('div');
      card.className = 'color-card';
      card.innerHTML = `
        <div class="color-card__swatch" style="background:${color.hex}">
          <div class="color-card__copied">Copied!</div>
        </div>
        <div class="color-card__info">
          <div class="color-card__label">${color.label}</div>
          <div class="color-card__value">${formatColor(color, currentFormat)}</div>
        </div>
      `;

      card.addEventListener('click', () => {
        const value = formatColor(color, currentFormat);
        navigator.clipboard.writeText(value).then(() => {
          const copied = card.querySelector('.color-card__copied');
          copied.textContent = `Copied: ${value}`;
          copied.classList.add('show');
          setTimeout(() => copied.classList.remove('show'), 1200);
        });
      });

      els.colorGrid.appendChild(card);
    });

    // Animate cards — D9 scale(0.95) with back.out
    if (!prefersReducedMotion) {
      gsap.from('.color-card', {
        scale: 0.95,
        opacity: 0,
        duration: 0.5,
        stagger: 0.06,
        ease: 'back.out(1.4)',
      });
    }
  }

  function updateContrastChecker() {
    const fg = els.contrastFgHex.value;
    const bg = els.contrastBgHex.value;

    // Update preview
    els.contrastPreview.style.background = bg;
    els.contrastPreview.style.color = fg;

    // Calculate ratio
    const ratio = contrastRatio(fg, bg);
    const ratioStr = ratio.toFixed(2);

    // WCAG levels
    const aaLarge = ratio >= 3;
    const aaNormal = ratio >= 4.5;
    const aaaLarge = ratio >= 4.5;
    const aaaNormal = ratio >= 7;

    els.contrastScores.innerHTML = `
      <div class="contrast-score">
        <span class="contrast-score__label">Ratio</span>
        <span class="contrast-score__ratio">${ratioStr}:1</span>
      </div>
      <div class="contrast-score">
        <span class="contrast-score__label">AA Normal</span>
        <span class="contrast-score__badge ${aaNormal ? 'pass' : 'fail'}">${aaNormal ? 'PASS' : 'FAIL'}</span>
      </div>
      <div class="contrast-score">
        <span class="contrast-score__label">AA Large</span>
        <span class="contrast-score__badge ${aaLarge ? 'pass' : 'fail'}">${aaLarge ? 'PASS' : 'FAIL'}</span>
      </div>
      <div class="contrast-score">
        <span class="contrast-score__label">AAA Normal</span>
        <span class="contrast-score__badge ${aaaNormal ? 'pass' : 'fail'}">${aaaNormal ? 'PASS' : 'FAIL'}</span>
      </div>
      <div class="contrast-score">
        <span class="contrast-score__label">AAA Large</span>
        <span class="contrast-score__badge ${aaaLarge ? 'pass' : 'fail'}">${aaaLarge ? 'PASS' : 'FAIL'}</span>
      </div>
    `;
  }

  function updateExport() {
    const lines = [':root {'];
    currentColors.forEach((color, i) => {
      const varName = `--color-${color.label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-+$/, '')}`;
      lines.push(`  ${varName}: ${color.hex};`);
      lines.push(`  ${varName}-rgb: ${color.rgb.r}, ${color.rgb.g}, ${color.rgb.b};`);
      lines.push(`  ${varName}-hsl: ${color.h}, ${color.s}%, ${color.l}%;`);
    });
    lines.push('}');
    els.exportCode.textContent = lines.join('\n');
  }

  function regenerate() {
    const hex = els.colorHex.value;
    currentColors = generateScheme(hex, currentScheme);
    updatePreviewStrip();
    renderColorGrid();
    updateExport();

    // Also update contrast checker bg to base color
    els.contrastBg.value = hex;
    els.contrastBgHex.value = hex;
    updateContrastChecker();
  }

  /* ============================================================
     GSAP ANIMATIONS — D9 scale(0.95) with back.out
     ============================================================ */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero entrance with scale */
    const heroTl = gsap.timeline({ defaults: { ease: 'back.out(1.4)' } });
    heroTl
      .from('.hero__title', { scale: 0.95, opacity: 0, duration: 0.7 })
      .from('.hero__subtitle', { scale: 0.95, opacity: 0, duration: 0.5 }, '-=0.4')
      .from('.hero__picker-row', { scale: 0.95, opacity: 0, duration: 0.5 }, '-=0.3');

    /* Sections with scale(0.95) + back.out */
    const sections = ['.section--schemes', '.section--colors', '.section--contrast', '.section--export'];
    sections.forEach(sel => {
      gsap.from(sel, {
        scrollTrigger: {
          trigger: sel,
          start: 'top 85%',
          toggleActions: 'play none none none',
        },
        scale: 0.95,
        opacity: 0,
        duration: 0.7,
        ease: 'back.out(1.4)',
      });
    });
  }

  /* ============================================================
     EVENT LISTENERS
     ============================================================ */
  function bindEvents() {
    // Theme toggle
    els.themeToggle.addEventListener('click', toggleTheme);

    // Color picker
    els.colorPicker.addEventListener('input', (e) => {
      els.colorHex.value = e.target.value;
      regenerate();
    });

    // Hex input
    els.colorHex.addEventListener('input', (e) => {
      let val = e.target.value;
      if (!val.startsWith('#')) val = '#' + val;
      if (/^#[0-9a-fA-F]{6}$/.test(val)) {
        els.colorPicker.value = val;
        regenerate();
      }
    });

    // Scheme tabs
    els.schemeTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        els.schemeTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentScheme = tab.dataset.scheme;
        regenerate();
      });
    });

    // Format toggle
    els.formatBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        els.formatBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFormat = btn.dataset.format;
        renderColorGrid();
      });
    });

    // Contrast checker
    els.contrastFg.addEventListener('input', (e) => {
      els.contrastFgHex.value = e.target.value;
      updateContrastChecker();
    });
    els.contrastFgHex.addEventListener('input', (e) => {
      let val = e.target.value;
      if (!val.startsWith('#')) val = '#' + val;
      if (/^#[0-9a-fA-F]{6}$/.test(val)) {
        els.contrastFg.value = val;
        updateContrastChecker();
      }
    });
    els.contrastBg.addEventListener('input', (e) => {
      els.contrastBgHex.value = e.target.value;
      updateContrastChecker();
    });
    els.contrastBgHex.addEventListener('input', (e) => {
      let val = e.target.value;
      if (!val.startsWith('#')) val = '#' + val;
      if (/^#[0-9a-fA-F]{6}$/.test(val)) {
        els.contrastBg.value = val;
        updateContrastChecker();
      }
    });

    // Export copy
    els.exportCopyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(els.exportCode.textContent).then(() => {
        els.exportCopyBtn.textContent = 'Copied!';
        els.exportCopyBtn.classList.add('copied');
        setTimeout(() => {
          els.exportCopyBtn.textContent = 'Copy CSS';
          els.exportCopyBtn.classList.remove('copied');
        }, 1500);
      });
    });
  }

  /* ============================================================
     INIT
     ============================================================ */
  function init() {
    initTheme();
    initHeroImage();
    updateClock();
    setInterval(updateClock, 1000);
    regenerate();
    updateContrastChecker();
    bindEvents();

    requestAnimationFrame(() => {
      initAnimations();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
