/* ============================================================
   Morning Intelligence Briefing — script.js
   APIs: CoinGecko (free) + HackerNews (free) + Quotable (free)
   Default theme: light. Dark via [data-theme="dark"].
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Configuration ---------- */
  const CONFIG = {
    userName: (() => {
      const raw = '{{USER_NAME}}';
      return raw.startsWith('{{') ? 'Explorer' : raw;
    })(),
    interests: (() => {
      try {
        const raw = '{{INTERESTS}}';
        if (raw.startsWith('{{')) return ['crypto', 'tech', 'finance'];
        return JSON.parse(raw);
      } catch {
        return ['crypto', 'tech', 'finance'];
      }
    })(),
    city: (() => {
      const raw = '{{CITY}}';
      return raw.startsWith('{{') ? '' : raw;
    })(),
    heroImageUrl: (() => {
      const raw = '{{HERO_IMAGE_URL}}';
      return raw.startsWith('{{') ? '' : raw;
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    prices: () =>
      'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin,ethereum&order=market_cap_desc&sparkline=false&price_change_percentage=24h',
    global: () =>
      'https://api.coingecko.com/api/v3/global',
    fearGreed: () =>
      'https://api.alternative.me/fng/?limit=1',
    hnTopStories: () =>
      'https://hacker-news.firebaseio.com/v0/topstories.json',
    hnItem: (id) =>
      `https://hacker-news.firebaseio.com/v0/item/${id}.json`,
    quote: () =>
      'https://api.quotable.io/random',
  };

  /* Lucide SVG icons (inline, stroke-width 1.5) */
  const ICONS = {
    alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
    globe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>',
    clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    arrowUp: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m18 15-6-6-6 6"/></svg>',
    star: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    inbox: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>',
    externalLink: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>',
    trendingUp: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
    newspaper: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/></svg>',
    quote: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V21z"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3z"/></svg>',
    checkSquare: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
    link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
    sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>',
    cloud: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>',
    moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>',
  };

  /* ---------- Utility: Fetch with Retry ---------- */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (attempt === retries) throw err;
        const delay = CONFIG.retryBaseDelay * (attempt + 1);
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }

  /* ---------- Utility: Time-based Greeting ---------- */
  function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    return 'Good Evening';
  }

  /* ---------- Utility: Relative Time ---------- */
  function timeAgo(unixSeconds) {
    const diff = Math.floor(Date.now() / 1000) - unixSeconds;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
  }

  /* ---------- Utility: Format USD ---------- */
  function formatUSD(value, compact) {
    if (value == null) return '--';
    if (compact) {
      if (value >= 1e12) return '$' + (value / 1e12).toFixed(2) + 'T';
      if (value >= 1e9) return '$' + (value / 1e9).toFixed(2) + 'B';
      if (value >= 1e6) return '$' + (value / 1e6).toFixed(2) + 'M';
    }
    if (value >= 1) return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return '$' + value.toFixed(4);
  }

  function formatPercent(value) {
    if (value == null) return '--';
    const sign = value >= 0 ? '+' : '';
    return sign + value.toFixed(2) + '%';
  }

  /* ---------- Utility: Extract domain from URL ---------- */
  function extractDomain(url) {
    if (!url) return 'news';
    try {
      return new URL(url).hostname.replace('www.', '');
    } catch {
      return 'news';
    }
  }

  /* ---------- Render: Skeleton ---------- */
  function renderSkeleton(container, type, count = 1) {
    let html = '';
    for (let i = 0; i < count; i++) {
      html += `<div class="skeleton skeleton--${type}" aria-hidden="true"></div>`;
    }
    container.innerHTML = html;
  }

  /* ---------- Render: Error State ---------- */
  function renderError(container, message, retryFn) {
    container.innerHTML = `
      <div class="error-state">
        <div class="error-state__icon">${ICONS.alert}</div>
        <p class="error-state__message">${message}</p>
        <button class="error-state__retry" type="button">Retry</button>
      </div>`;
    const btn = container.querySelector('.error-state__retry');
    if (btn && retryFn) {
      btn.addEventListener('click', retryFn);
    }
  }

  /* ---------- Render: Empty State ---------- */
  function renderEmpty(container, message) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">${ICONS.inbox}</div>
        <p>${message}</p>
      </div>`;
  }

  /* ============================================================
     SECTION 1: Hero — Greeting + Date
     ============================================================ */
  function initHero() {
    const greetingEl = document.getElementById('hero-greeting');
    const dateEl = document.getElementById('hero-date');
    const heroImg = document.querySelector('.hero__bg-image');

    if (greetingEl) {
      greetingEl.innerHTML = `${getGreeting()}, <span class="accent">${CONFIG.userName}</span>`;
    }

    if (dateEl) {
      const now = new Date();
      dateEl.textContent = now.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    }

    if (heroImg && CONFIG.heroImageUrl) {
      heroImg.style.backgroundImage = `url('${CONFIG.heroImageUrl}')`;
    }
  }

  /* ============================================================
     SECTION 2: Market Snapshot — BTC, ETH, Market Cap, Fear/Greed
     ============================================================ */
  async function loadMarketSnapshot() {
    const container = document.getElementById('market-strip');
    if (!container) return;

    renderSkeleton(container, 'kpi', 4);

    try {
      const [pricesData, globalData, fngData] = await Promise.allSettled([
        fetchWithRetry(API.prices()),
        fetchWithRetry(API.global()),
        fetchWithRetry(API.fearGreed()),
      ]);

      let html = '';

      /* BTC & ETH prices */
      if (pricesData.status === 'fulfilled' && pricesData.value) {
        pricesData.value.forEach((coin) => {
          const change = coin.price_change_percentage_24h;
          const changeClass = change >= 0 ? 'kpi-card__change--up' : 'kpi-card__change--down';
          const changeSign = change >= 0 ? '+' : '';
          html += `
            <div class="kpi-card">
              <div class="kpi-card__label">${coin.symbol.toUpperCase()}</div>
              <div class="kpi-card__value">${formatUSD(coin.current_price)}</div>
              <div class="kpi-card__change ${changeClass}">${changeSign}${change?.toFixed(2) ?? '--'}%</div>
            </div>`;
        });
      } else {
        html += buildFallbackKpi('BTC', '--', '--');
        html += buildFallbackKpi('ETH', '--', '--');
      }

      /* Total Market Cap */
      if (globalData.status === 'fulfilled' && globalData.value?.data) {
        const mcap = globalData.value.data.total_market_cap?.usd;
        const mcapChange = globalData.value.data.market_cap_change_percentage_24h_usd;
        const changeClass = mcapChange >= 0 ? 'kpi-card__change--up' : 'kpi-card__change--down';
        html += `
          <div class="kpi-card">
            <div class="kpi-card__label">Total Market Cap</div>
            <div class="kpi-card__value">${formatUSD(mcap, true)}</div>
            <div class="kpi-card__change ${changeClass}">${formatPercent(mcapChange)}</div>
          </div>`;
      } else {
        html += buildFallbackKpi('Market Cap', '--', '--');
      }

      /* Fear & Greed */
      if (fngData.status === 'fulfilled' && fngData.value?.data?.[0]) {
        const fng = fngData.value.data[0];
        html += `
          <div class="kpi-card">
            <div class="kpi-card__label">Fear &amp; Greed</div>
            <div class="kpi-card__value">${fng.value}/100</div>
            <div class="kpi-card__change" style="color: var(--accent-3);">${fng.value_classification}</div>
          </div>`;
      } else {
        html += buildFallbackKpi('Fear & Greed', '--', '--');
      }

      container.innerHTML = html;
    } catch {
      renderError(container, 'Failed to load market data', loadMarketSnapshot);
    }
  }

  function buildFallbackKpi(label, value, change) {
    return `
      <div class="kpi-card">
        <div class="kpi-card__label">${label}</div>
        <div class="kpi-card__value">${value}</div>
        <div class="kpi-card__change">${change}</div>
      </div>`;
  }

  /* ============================================================
     SECTION 3: Top News — HackerNews Top Stories
     ============================================================ */
  async function loadNews() {
    const container = document.getElementById('news-list');
    if (!container) return;

    renderSkeleton(container, 'news', 5);

    try {
      const storyIds = await fetchWithRetry(API.hnTopStories());
      if (!storyIds || storyIds.length === 0) {
        renderEmpty(container, 'No stories available right now.');
        return;
      }

      const top5Ids = storyIds.slice(0, 5);
      const stories = await Promise.all(
        top5Ids.map((id) => fetchWithRetry(API.hnItem(id)))
      );

      const validStories = stories.filter(Boolean);
      if (validStories.length === 0) {
        renderEmpty(container, 'No stories available right now.');
        return;
      }

      container.innerHTML = validStories
        .map((story, i) => {
          const domain = extractDomain(story.url);
          const ago = story.time ? timeAgo(story.time) : '';
          const href = story.url || `https://news.ycombinator.com/item?id=${story.id}`;
          return `
            <a class="news-item" href="${href}" target="_blank" rel="noopener noreferrer">
              <span class="news-item__rank">${i + 1}</span>
              <div class="news-item__body">
                <h3 class="news-item__title">${escapeHtml(story.title)}</h3>
                <div class="news-item__meta">
                  <span class="news-item__source">
                    <span class="news-item__source-icon">${ICONS.globe}</span>
                    ${domain}
                  </span>
                  <span class="news-item__time">
                    <span class="news-item__time-icon">${ICONS.clock}</span>
                    ${ago}
                  </span>
                  ${story.score ? `
                  <span class="news-item__score">
                    <span class="news-item__score-icon">${ICONS.arrowUp}</span>
                    ${story.score}
                  </span>` : ''}
                </div>
              </div>
            </a>`;
        })
        .join('');
    } catch {
      renderError(container, 'Failed to load news', loadNews);
    }
  }

  /* ---------- Utility: Escape HTML ---------- */
  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ============================================================
     SECTION 4: Daily Quote — Quotable API
     ============================================================ */
  async function loadQuote() {
    const textEl = document.getElementById('quote-text');
    const authorEl = document.getElementById('quote-author');
    if (!textEl || !authorEl) return;

    textEl.textContent = '';
    authorEl.textContent = '';
    textEl.closest('.quote-section').classList.add('loading');

    try {
      const data = await fetchWithRetry(API.quote());
      if (data && data.content) {
        textEl.textContent = data.content;
        authorEl.textContent = data.author || 'Unknown';
      } else {
        /* Fallback quote */
        textEl.textContent = 'The only way to do great work is to love what you do.';
        authorEl.textContent = 'Steve Jobs';
      }
    } catch {
      /* Fallback on error */
      textEl.textContent = 'Stay hungry, stay foolish.';
      authorEl.textContent = 'Steve Jobs';
    } finally {
      textEl.closest('.quote-section')?.classList.remove('loading');
    }
  }

  /* ============================================================
     SECTION 5: Today's Tasks — Placeholder (agent fills)
     ============================================================ */
  function initTodos() {
    const container = document.getElementById('todo-list');
    if (!container) return;

    /* Default placeholder tasks — agent replaces these */
    const defaultTodos = [
      { text: 'Review morning briefing', done: false, time: '09:00' },
      { text: 'Check portfolio performance', done: false, time: '09:30' },
      { text: 'Read top news articles', done: false, time: '10:00' },
      { text: 'Plan the day ahead', done: false, time: '10:30' },
    ];

    container.innerHTML = defaultTodos
      .map(
        (todo) => `
        <li class="todo-item">
          <span class="todo-item__check ${todo.done ? 'todo-item__check--done' : ''}"></span>
          <span class="todo-item__text ${todo.done ? 'todo-item__text--done' : ''}">${escapeHtml(todo.text)}</span>
          <span class="todo-item__time">${todo.time}</span>
        </li>`
      )
      .join('');
  }

  /* ============================================================
     SECTION 6: Quick Links — Based on INTERESTS
     ============================================================ */
  function initQuickLinks() {
    const container = document.getElementById('links-grid');
    if (!container) return;

    const linkMap = {
      crypto: [
        { label: 'CoinGecko', url: 'https://www.coingecko.com', icon: ICONS.trendingUp },
        { label: 'CoinDesk', url: 'https://www.coindesk.com', icon: ICONS.newspaper },
      ],
      tech: [
        { label: 'Hacker News', url: 'https://news.ycombinator.com', icon: ICONS.newspaper },
        { label: 'TechCrunch', url: 'https://techcrunch.com', icon: ICONS.globe },
      ],
      finance: [
        { label: 'Bloomberg', url: 'https://www.bloomberg.com', icon: ICONS.trendingUp },
        { label: 'Reuters', url: 'https://www.reuters.com', icon: ICONS.newspaper },
      ],
      ai: [
        { label: 'Hugging Face', url: 'https://huggingface.co', icon: ICONS.star },
        { label: 'ArXiv AI', url: 'https://arxiv.org/list/cs.AI/recent', icon: ICONS.globe },
      ],
      design: [
        { label: 'Dribbble', url: 'https://dribbble.com', icon: ICONS.star },
        { label: 'Awwwards', url: 'https://www.awwwards.com', icon: ICONS.globe },
      ],
      gaming: [
        { label: 'IGN', url: 'https://www.ign.com', icon: ICONS.star },
        { label: 'Kotaku', url: 'https://kotaku.com', icon: ICONS.newspaper },
      ],
    };

    /* Default links for unmatched interests */
    const defaultLinks = [
      { label: 'Google News', url: 'https://news.google.com', icon: ICONS.newspaper },
      { label: 'Wikipedia', url: 'https://www.wikipedia.org', icon: ICONS.globe },
    ];

    const links = [];
    const seen = new Set();

    CONFIG.interests.forEach((interest) => {
      const key = interest.toLowerCase().trim();
      const matches = linkMap[key] || [];
      matches.forEach((link) => {
        if (!seen.has(link.url)) {
          seen.add(link.url);
          links.push(link);
        }
      });
    });

    /* Add defaults if we have fewer than 4 links */
    if (links.length < 4) {
      defaultLinks.forEach((link) => {
        if (!seen.has(link.url)) {
          seen.add(link.url);
          links.push(link);
        }
      });
    }

    if (links.length === 0) {
      renderEmpty(container, 'No quick links configured.');
      return;
    }

    container.innerHTML = links
      .map(
        (link) => `
        <a class="link-card" href="${link.url}" target="_blank" rel="noopener noreferrer">
          <span class="link-card__icon">${link.icon}</span>
          ${escapeHtml(link.label)}
        </a>`
      )
      .join('');
  }

  /* ============================================================
     Theme Toggle (light default, dark via data-theme="dark")
     ============================================================ */
  function initTheme() {
    const stored = localStorage.getItem('morning-briefing-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');

    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    }

    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    toggle.addEventListener('click', () => {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('morning-briefing-theme', 'light');
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('morning-briefing-theme', 'dark');
      }
    });
  }

  /* ============================================================
     Scroll Reveal — IntersectionObserver
     ============================================================ */
  function initScrollReveal() {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -10% 0px' }
    );

    document.querySelectorAll('.scroll-reveal').forEach((el) => observer.observe(el));
  }

  /* ============================================================
     Init
     ============================================================ */
  function init() {
    initTheme();
    initHero();
    initScrollReveal();

    /* Load async data */
    loadMarketSnapshot();
    loadNews();
    loadQuote();

    /* Static sections */
    initTodos();
    initQuickLinks();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
