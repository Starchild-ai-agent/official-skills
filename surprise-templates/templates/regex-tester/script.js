/* ============================================================
   Regex Pattern Tester — script.js

   Pure frontend functionality — no external APIs required.
   Real-time regex matching with highlight, capture groups,
   common patterns library, and cheatsheet.

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
     COMMON REGEX PATTERNS
     ============================================================ */
  const COMMON_PATTERNS = [
    {
      name: 'Email Address',
      desc: 'Matches standard email format',
      regex: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
      flags: 'gi',
      testString: 'Contact us at hello@example.com or support@company.org',
    },
    {
      name: 'URL',
      desc: 'Matches HTTP/HTTPS URLs',
      regex: 'https?:\\/\\/[\\w\\-]+(\\.[\\w\\-]+)+[\\w\\-.,@?^=%&:/~+#]*',
      flags: 'gi',
      testString: 'Visit https://example.com or http://docs.api.io/path?q=1',
    },
    {
      name: 'IPv4 Address',
      desc: 'Matches dotted-decimal IPv4',
      regex: '\\b(?:(?:25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(?:25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\b',
      flags: 'g',
      testString: 'Server IPs: 192.168.1.1, 10.0.0.255, 256.1.2.3 (invalid)',
    },
    {
      name: 'Phone Number',
      desc: 'US phone formats',
      regex: '(?:\\+?1[-.\\s]?)?\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}',
      flags: 'g',
      testString: 'Call (555) 123-4567 or +1-800-555-0199 or 5551234567',
    },
    {
      name: 'Hex Color',
      desc: 'Matches #RGB or #RRGGBB',
      regex: '#(?:[0-9a-fA-F]{3}){1,2}\\b',
      flags: 'gi',
      testString: 'Colors: #ec4899, #fff, #1a1a1e, #F00',
    },
    {
      name: 'Date (YYYY-MM-DD)',
      desc: 'ISO date format',
      regex: '\\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\\d|3[01])',
      flags: 'g',
      testString: 'Dates: 2024-01-15, 2023-12-31, 2024-13-01 (invalid)',
    },
    {
      name: 'HTML Tag',
      desc: 'Matches opening/closing HTML tags',
      regex: '<\\/?[a-zA-Z][a-zA-Z0-9]*(?:\\s[^>]*)?\\/?>',
      flags: 'gi',
      testString: '<div class="box"><p>Hello</p><br/></div>',
    },
    {
      name: 'Strong Password',
      desc: '8+ chars, upper, lower, digit, special',
      regex: '(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&#])[A-Za-z\\d@$!%*?&#]{8,}',
      flags: 'g',
      testString: 'Weak: abc123 | Strong: MyP@ss1word! | Also: Test#9xyz',
    },
  ];

  /* ============================================================
     CHEATSHEET DATA
     ============================================================ */
  const CHEATSHEET = [
    {
      title: 'Character Classes',
      items: [
        { token: '.', desc: 'Any character (except newline)' },
        { token: '\\d', desc: 'Digit [0-9]' },
        { token: '\\w', desc: 'Word char [a-zA-Z0-9_]' },
        { token: '\\s', desc: 'Whitespace' },
        { token: '[abc]', desc: 'Any of a, b, or c' },
        { token: '[^abc]', desc: 'Not a, b, or c' },
      ],
    },
    {
      title: 'Quantifiers',
      items: [
        { token: '*', desc: '0 or more' },
        { token: '+', desc: '1 or more' },
        { token: '?', desc: '0 or 1' },
        { token: '{n}', desc: 'Exactly n' },
        { token: '{n,m}', desc: 'Between n and m' },
        { token: '*?', desc: 'Lazy (non-greedy)' },
      ],
    },
    {
      title: 'Anchors',
      items: [
        { token: '^', desc: 'Start of string/line' },
        { token: '$', desc: 'End of string/line' },
        { token: '\\b', desc: 'Word boundary' },
        { token: '\\B', desc: 'Non-word boundary' },
      ],
    },
    {
      title: 'Groups & Lookaround',
      items: [
        { token: '(abc)', desc: 'Capture group' },
        { token: '(?:abc)', desc: 'Non-capture group' },
        { token: '(?=abc)', desc: 'Positive lookahead' },
        { token: '(?!abc)', desc: 'Negative lookahead' },
        { token: '(?<=abc)', desc: 'Positive lookbehind' },
        { token: 'a|b', desc: 'Alternation (or)' },
      ],
    },
    {
      title: 'Flags',
      items: [
        { token: 'g', desc: 'Global — all matches' },
        { token: 'i', desc: 'Case insensitive' },
        { token: 'm', desc: 'Multiline (^ $ per line)' },
        { token: 's', desc: 'Dotall (. matches \\n)' },
        { token: 'u', desc: 'Unicode support' },
      ],
    },
    {
      title: 'Escapes',
      items: [
        { token: '\\\\', desc: 'Literal backslash' },
        { token: '\\n', desc: 'Newline' },
        { token: '\\t', desc: 'Tab' },
        { token: '\\0', desc: 'Null character' },
      ],
    },
  ];

  /* ============================================================
     DOM REFERENCES
     ============================================================ */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  const els = {
    themeToggle: $('#theme-toggle'),
    heroTime: $('#hero-time'),
    regexInput: $('#regex-input'),
    regexFlags: $('#regex-flags'),
    flagBtns: $$('.flag-btn'),
    matchCount: $('#match-count'),
    testString: $('#test-string'),
    highlightLayer: $('#highlight-layer'),
    regexError: $('#regex-error'),
    resultsGrid: $('#results-grid'),
    resultsEmpty: $('#results-empty'),
    patternsGrid: $('#patterns-grid'),
    cheatsheetGrid: $('#cheatsheet-grid'),
    heroBgImage: $('.hero__bg-image'),
  };

  /* ============================================================
     THEME MANAGEMENT
     ============================================================ */
  function initTheme() {
    const saved = localStorage.getItem('regex-tester-theme');
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
    localStorage.setItem('regex-tester-theme', next);
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
     REGEX ENGINE
     ============================================================ */
  function getFlags() {
    return els.flagBtns
      .filter((btn) => btn.classList.contains('active'))
      .map((btn) => btn.dataset.flag)
      .join('');
  }

  function buildRegex(pattern, flags) {
    try {
      const regex = new RegExp(pattern, flags);
      els.regexError.textContent = '';
      return regex;
    } catch (err) {
      els.regexError.textContent = `⚠ ${err.message}`;
      return null;
    }
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function performMatch() {
    const pattern = els.regexInput.value;
    const testStr = els.testString.value;

    if (!pattern || !testStr) {
      els.highlightLayer.innerHTML = '';
      els.matchCount.textContent = '0';
      showEmptyResults();
      return;
    }

    const flags = getFlags();
    const regex = buildRegex(pattern, flags);
    if (!regex) {
      els.highlightLayer.innerHTML = '';
      els.matchCount.textContent = '0';
      showEmptyResults();
      return;
    }

    // Collect all matches
    const matches = [];
    let match;

    if (flags.includes('g')) {
      while ((match = regex.exec(testStr)) !== null) {
        matches.push({
          value: match[0],
          index: match.index,
          length: match[0].length,
          groups: match.slice(1),
          namedGroups: match.groups || null,
        });
        if (match[0].length === 0) {
          regex.lastIndex++;
        }
      }
    } else {
      match = regex.exec(testStr);
      if (match) {
        matches.push({
          value: match[0],
          index: match.index,
          length: match[0].length,
          groups: match.slice(1),
          namedGroups: match.groups || null,
        });
      }
    }

    // Update match count
    els.matchCount.textContent = matches.length.toString();

    // Build highlight layer
    buildHighlightLayer(testStr, matches);

    // Build results
    buildMatchResults(matches);
  }

  function buildHighlightLayer(text, matches) {
    if (matches.length === 0) {
      els.highlightLayer.innerHTML = escapeHtml(text);
      return;
    }

    let html = '';
    let lastIndex = 0;

    for (const m of matches) {
      // Text before match
      html += escapeHtml(text.slice(lastIndex, m.index));
      // Matched text
      html += `<mark>${escapeHtml(m.value)}</mark>`;
      lastIndex = m.index + m.length;
    }
    // Remaining text
    html += escapeHtml(text.slice(lastIndex));

    els.highlightLayer.innerHTML = html;
  }

  function showEmptyResults() {
    els.resultsGrid.innerHTML = '';
    els.resultsGrid.appendChild(createEmptyState());
  }

  function createEmptyState() {
    const div = document.createElement('div');
    div.className = 'results-empty';
    div.innerHTML = `
      <div class="results-empty__icon">⌘</div>
      <p>Enter a regex pattern and test string to see results</p>
    `;
    return div;
  }

  function buildMatchResults(matches) {
    els.resultsGrid.innerHTML = '';

    if (matches.length === 0) {
      els.resultsGrid.appendChild(createEmptyState());
      return;
    }

    matches.forEach((m, i) => {
      const card = document.createElement('div');
      card.className = 'match-card';

      let groupsHtml = '';
      if (m.groups.length > 0) {
        groupsHtml = `
          <div class="match-card__groups">
            ${m.groups
              .map(
                (g, gi) => `
              <div class="match-card__group">
                <span class="match-card__group-label">Group ${gi + 1}:</span>
                <span class="match-card__group-value">${g !== undefined ? escapeHtml(g) : '<em>undefined</em>'}</span>
              </div>
            `
              )
              .join('')}
          </div>
        `;
      }

      let namedGroupsHtml = '';
      if (m.namedGroups) {
        const entries = Object.entries(m.namedGroups);
        if (entries.length > 0) {
          namedGroupsHtml = `
            <div class="match-card__groups">
              ${entries
                .map(
                  ([name, val]) => `
                <div class="match-card__group">
                  <span class="match-card__group-label">${escapeHtml(name)}:</span>
                  <span class="match-card__group-value">${val !== undefined ? escapeHtml(val) : '<em>undefined</em>'}</span>
                </div>
              `
                )
                .join('')}
            </div>
          `;
        }
      }

      card.innerHTML = `
        <div class="match-card__header">
          <span>Match ${i + 1}</span>
          <span class="match-card__index">Index ${m.index}</span>
        </div>
        <div class="match-card__value">${escapeHtml(m.value)}</div>
        <div class="match-card__meta">
          <span>Length: ${m.length}</span>
          <span>Range: [${m.index}, ${m.index + m.length})</span>
        </div>
        ${groupsHtml}
        ${namedGroupsHtml}
      `;

      els.resultsGrid.appendChild(card);
    });

    // Animate cards
    if (!prefersReducedMotion) {
      gsap.from('.match-card', {
        y: 20,
        opacity: 0,
        duration: 0.4,
        stagger: 0.06,
        ease: 'power2.out',
      });
    }
  }

  /* ============================================================
     SYNC SCROLL BETWEEN TEXTAREA AND HIGHLIGHT
     ============================================================ */
  function syncScroll() {
    els.highlightLayer.scrollTop = els.testString.scrollTop;
    els.highlightLayer.scrollLeft = els.testString.scrollLeft;
  }

  /* ============================================================
     COMMON PATTERNS RENDERING
     ============================================================ */
  function renderPatterns() {
    els.patternsGrid.innerHTML = '';

    COMMON_PATTERNS.forEach((p) => {
      const card = document.createElement('div');
      card.className = 'pattern-card';
      card.innerHTML = `
        <div class="pattern-card__name">${escapeHtml(p.name)}</div>
        <div class="pattern-card__desc">${escapeHtml(p.desc)}</div>
        <code class="pattern-card__regex">${escapeHtml(p.regex)}</code>
      `;
      card.addEventListener('click', () => {
        els.regexInput.value = p.regex;
        els.testString.value = p.testString;

        // Set flags
        els.flagBtns.forEach((btn) => {
          btn.classList.toggle('active', p.flags.includes(btn.dataset.flag));
        });

        performMatch();

        // Scroll to test section
        document.getElementById('section-test').scrollIntoView({ behavior: 'smooth' });
      });
      els.patternsGrid.appendChild(card);
    });
  }

  /* ============================================================
     CHEATSHEET RENDERING
     ============================================================ */
  function renderCheatsheet() {
    els.cheatsheetGrid.innerHTML = '';

    CHEATSHEET.forEach((section) => {
      const card = document.createElement('div');
      card.className = 'cheatsheet-card';
      card.innerHTML = `
        <div class="cheatsheet-card__title">${escapeHtml(section.title)}</div>
        <div class="cheatsheet-card__items">
          ${section.items
            .map(
              (item) => `
            <div class="cheatsheet-item">
              <span class="cheatsheet-item__token">${escapeHtml(item.token)}</span>
              <span class="cheatsheet-item__desc">${escapeHtml(item.desc)}</span>
            </div>
          `
            )
            .join('')}
        </div>
      `;
      els.cheatsheetGrid.appendChild(card);
    });
  }

  /* ============================================================
     GSAP ANIMATIONS — D5 opacity only
     ============================================================ */
  function initAnimations() {
    if (prefersReducedMotion) return;

    // Hero entrance — opacity only
    gsap.from('.hero__top-bar', { opacity: 0, duration: 0.6, ease: 'power2.out' });
    gsap.from('.tool-panel--hero', { opacity: 0, duration: 0.8, delay: 0.2, ease: 'power2.out' });

    // Section reveals — opacity only
    const sections = ['.section--test', '.section--results', '.section--patterns', '.section--cheatsheet'];
    sections.forEach((sel) => {
      gsap.from(sel, {
        scrollTrigger: {
          trigger: sel,
          start: 'top 85%',
          toggleActions: 'play none none none',
        },
        opacity: 0,
        duration: 0.7,
        ease: 'power2.out',
      });
    });

    // Pattern cards stagger — opacity only
    gsap.from('.pattern-card', {
      scrollTrigger: {
        trigger: '.section--patterns',
        start: 'top 80%',
        toggleActions: 'play none none none',
      },
      opacity: 0,
      duration: 0.5,
      stagger: 0.08,
      ease: 'power2.out',
    });

    // Cheatsheet cards stagger — opacity only
    gsap.from('.cheatsheet-card', {
      scrollTrigger: {
        trigger: '.section--cheatsheet',
        start: 'top 80%',
        toggleActions: 'play none none none',
      },
      opacity: 0,
      duration: 0.5,
      stagger: 0.08,
      ease: 'power2.out',
    });
  }

  /* ============================================================
     EVENT LISTENERS
     ============================================================ */
  function bindEvents() {
    // Theme toggle
    els.themeToggle.addEventListener('click', toggleTheme);

    // Regex input
    els.regexInput.addEventListener('input', performMatch);

    // Test string input
    els.testString.addEventListener('input', performMatch);
    els.testString.addEventListener('scroll', syncScroll);

    // Flag buttons
    els.flagBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        btn.classList.toggle('active');
        performMatch();
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
    renderPatterns();
    renderCheatsheet();
    bindEvents();

    // Delay animations to ensure DOM is ready
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
