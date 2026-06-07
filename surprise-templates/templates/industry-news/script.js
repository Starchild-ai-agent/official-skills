/* ============================================================
   Industry News Radar — script.js
   Mock data · GSAP 3 + ScrollTrigger
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Mock Data ---------- */
  const CATEGORIES = ['All', 'Crypto', 'AI', 'Tech', 'Finance'];

  const NEWS_ITEMS = [
    { time: '2m ago', headline: 'Bitcoin Surges Past $95K as Institutional Demand Hits Record', summary: 'Major asset managers report unprecedented inflows into Bitcoin ETFs, with BlackRock leading the charge.', category: 'Crypto', source: 'CoinDesk', credibility: 'high' },
    { time: '8m ago', headline: 'OpenAI Announces GPT-5 with Real-Time Reasoning', summary: 'The new model demonstrates chain-of-thought reasoning at 10x speed, with built-in tool use capabilities.', category: 'AI', source: 'The Verge', credibility: 'high' },
    { time: '15m ago', headline: 'Apple Unveils M5 Chip with Neural Engine Breakthrough', summary: 'New chip architecture delivers 3x ML performance, targeting on-device AI workloads.', category: 'Tech', source: 'TechCrunch', credibility: 'high' },
    { time: '22m ago', headline: 'Fed Signals Rate Cut in September Meeting', summary: 'Federal Reserve minutes reveal growing consensus for 25bps rate reduction amid cooling inflation.', category: 'Finance', source: 'Bloomberg', credibility: 'high' },
    { time: '35m ago', headline: 'Ethereum Layer 2 TVL Exceeds $50B Milestone', summary: 'Arbitrum and Base lead the growth as DeFi activity migrates to cheaper execution layers.', category: 'Crypto', source: 'DeFi Llama', credibility: 'high' },
    { time: '42m ago', headline: 'Anthropic Raises $5B Series E at $60B Valuation', summary: 'Amazon leads the round as Claude models gain enterprise traction across Fortune 500 companies.', category: 'AI', source: 'Reuters', credibility: 'high' },
    { time: '1h ago', headline: 'Stripe Launches Crypto Payment Rails for Merchants', summary: 'USDC and USDT payments now available for all Stripe merchants with instant settlement.', category: 'Tech', source: 'Stripe Blog', credibility: 'medium' },
    { time: '1h ago', headline: 'Goldman Sachs Launches Tokenized Treasury Fund', summary: 'The $500M fund offers institutional investors on-chain access to US Treasury yields.', category: 'Finance', source: 'Financial Times', credibility: 'high' },
    { time: '2h ago', headline: 'Solana Processes 100K TPS in Mainnet Stress Test', summary: 'Network stability maintained during peak load, validators report zero downtime.', category: 'Crypto', source: 'Solana Foundation', credibility: 'medium' },
    { time: '2h ago', headline: 'Google DeepMind Achieves AGI Benchmark Score of 92%', summary: 'New Gemini variant passes comprehensive reasoning tests, sparking debate on AGI definitions.', category: 'AI', source: 'Wired', credibility: 'medium' },
    { time: '3h ago', headline: 'NVIDIA Stock Hits $200 on Data Center Revenue Surge', summary: 'Q3 earnings beat estimates by 40%, driven by H200 GPU demand from hyperscalers.', category: 'Tech', source: 'CNBC', credibility: 'high' },
    { time: '3h ago', headline: 'SEC Approves Spot Ethereum ETF Options Trading', summary: 'Options on ETH ETFs to begin trading next month, expanding institutional hedging tools.', category: 'Finance', source: 'SEC Filing', credibility: 'high' },
    { time: '4h ago', headline: 'Uniswap V4 Launches with Custom Hook Architecture', summary: 'New modular design allows developers to build custom AMM logic as composable hooks.', category: 'Crypto', source: 'Uniswap Blog', credibility: 'medium' },
    { time: '5h ago', headline: 'Meta Open-Sources Llama 4 with 1T Parameters', summary: 'Largest open-source model to date, competitive with GPT-4 on major benchmarks.', category: 'AI', source: 'Meta AI Blog', credibility: 'medium' },
    { time: '6h ago', headline: 'Cloudflare Acquires AI Startup for $2.1B', summary: 'Deal strengthens edge AI inference capabilities across global CDN network.', category: 'Tech', source: 'TechCrunch', credibility: 'high' },
    { time: '7h ago', headline: 'Bank of Japan Raises Interest Rates to 0.75%', summary: 'Unexpected hawkish move sends yen surging, global carry trade unwinds accelerate.', category: 'Finance', source: 'Nikkei', credibility: 'high' },
  ];

  const SOURCES = [
    { name: 'Bloomberg', type: 'Financial Media', score: 95 },
    { name: 'CoinDesk', type: 'Crypto Media', score: 88 },
    { name: 'TechCrunch', type: 'Tech Media', score: 90 },
    { name: 'The Verge', type: 'Tech Media', score: 87 },
    { name: 'Reuters', type: 'Wire Service', score: 96 },
    { name: 'CNBC', type: 'Financial Media', score: 82 },
    { name: 'Wired', type: 'Tech Media', score: 80 },
    { name: 'Financial Times', type: 'Financial Media', score: 94 },
  ];

  let activeCategory = 'All';
  let sortBy = 'time';

  /* ---------- DOM ---------- */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  /* ---------- Theme Toggle ---------- */
  const themeToggle = $('#theme-toggle');
  function initTheme() {
    const saved = localStorage.getItem('industry-news-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }
  initTheme();
  themeToggle.addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem('industry-news-theme', isDark ? 'light' : 'dark');
  });

  /* ---------- Render Filters ---------- */
  function renderFilters() {
    const tabs = $('#filter-tabs');
    tabs.innerHTML = CATEGORIES.map(cat => `
      <button class="filter-tab ${cat === activeCategory ? 'active' : ''}" data-category="${cat}">${cat}</button>
    `).join('');

    tabs.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        activeCategory = tab.dataset.category;
        renderFilters();
        renderFeed();
      });
    });
  }

  /* ---------- Render Feed ---------- */
  function renderFeed() {
    let items = activeCategory === 'All' ? [...NEWS_ITEMS] : NEWS_ITEMS.filter(n => n.category === activeCategory);

    if (sortBy === 'credibility') {
      const order = { high: 0, medium: 1, low: 2 };
      items.sort((a, b) => order[a.credibility] - order[b.credibility]);
    } else if (sortBy === 'category') {
      items.sort((a, b) => a.category.localeCompare(b.category));
    }

    const list = $('#feed-list');
    list.innerHTML = items.map(item => `
      <div class="feed-item">
        <div class="feed-item__time">${item.time}</div>
        <div class="feed-item__body">
          <div class="feed-item__headline">${item.headline}</div>
          <div class="feed-item__summary">${item.summary}</div>
          <div class="feed-item__meta">
            <span class="feed-item__tag">${item.category}</span>
            <span class="feed-item__source">${item.source}</span>
            <span class="feed-item__credibility feed-item__credibility--${item.credibility}">${item.credibility.toUpperCase()}</span>
          </div>
        </div>
      </div>
    `).join('');

    $('#alert-count').textContent = items.length + ' stories';

    if (!prefersReducedMotion) {
      gsap.from('.feed-item', {
        x: -50,
        opacity: 0,
        duration: 0.5,
        stagger: 0.04,
        ease: 'power3.out',
        clearProps: 'transform,opacity'
      });
    }
  }

  /* ---------- Render Sources ---------- */
  function renderSources() {
    const grid = $('#source-grid');
    grid.innerHTML = SOURCES.map(s => `
      <div class="source-card">
        <div class="source-card__name">${s.name}</div>
        <div class="source-card__type">${s.type}</div>
        <div class="source-card__score" style="color: ${s.score >= 90 ? 'var(--color-success)' : s.score >= 80 ? 'var(--color-warning)' : 'var(--color-accent)'}">${s.score}/100</div>
        <div class="source-card__bar">
          <div class="source-card__bar-fill" style="width: ${s.score}%"></div>
        </div>
      </div>
    `).join('');
  }

  /* ---------- Sort Handler ---------- */
  function initSort() {
    $('#sort-select').addEventListener('change', (e) => {
      sortBy = e.target.value;
      renderFeed();
    });
  }

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero entrance — D10 translateX(-50px) */
    const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__alert-bar', { x: -50, opacity: 0, duration: 0.6 })
      .from('.hero__title', { x: -50, opacity: 0, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { x: -50, opacity: 0, duration: 0.5 }, '-=0.3');

    /* Source cards */
    gsap.from('.source-card', {
      scrollTrigger: { trigger: '#sources', start: 'top 80%', once: true },
      x: -50, opacity: 0, duration: 0.5, stagger: 0.06, ease: 'power3.out'
    });
  }

  /* ---------- Init ---------- */
  function init() {
    renderFilters();
    renderFeed();
    renderSources();
    initSort();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
