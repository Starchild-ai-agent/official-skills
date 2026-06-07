/* ============================================================
   Competitor Monitor — script.js
   Mock data · GSAP 3 + ScrollTrigger
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Mock Data ---------- */
  const COMPETITORS = [
    { name: 'AlphaDAO', handle: '@alphadao', followers: '245K', engagement: '4.2%', postsPerWeek: 28, topContent: 'Threads', growth: '+12.3%' },
    { name: 'BetaLabs', handle: '@betalabs', followers: '189K', engagement: '3.8%', postsPerWeek: 21, topContent: 'Infographics', growth: '+8.7%' },
    { name: 'GammaFi', handle: '@gammafi', followers: '312K', engagement: '5.1%', postsPerWeek: 35, topContent: 'Alpha Calls', growth: '+18.2%' },
    { name: 'DeltaX', handle: '@deltax_io', followers: '156K', engagement: '3.2%', postsPerWeek: 18, topContent: 'Memes', growth: '+5.4%' },
  ];

  const METRICS = [
    { name: 'Followers', values: ['245K', '189K', '312K', '156K'], best: 2 },
    { name: 'Engagement Rate', values: ['4.2%', '3.8%', '5.1%', '3.2%'], best: 2 },
    { name: 'Posts/Week', values: ['28', '21', '35', '18'], best: 2 },
    { name: 'Avg Likes', values: ['1,240', '890', '2,100', '620'], best: 2 },
    { name: 'Avg Retweets', values: ['340', '210', '580', '150'], best: 2 },
    { name: 'Reply Rate', values: ['12%', '8%', '15%', '6%'], best: 2 },
    { name: '30d Growth', values: ['+12.3%', '+8.7%', '+18.2%', '+5.4%'], best: 2 },
    { name: 'Thread Ratio', values: ['35%', '20%', '45%', '10%'], best: 2 },
  ];

  const TIMELINE = [
    { time: '1h ago', account: '@gammafi', action: 'Published a 12-tweet thread on Solana DeFi yields, gaining 2.4K likes in first hour.', tag: 'Thread' },
    { time: '3h ago', account: '@alphadao', action: 'Announced partnership with Chainlink for oracle integration. Tweet went viral with 5K+ retweets.', tag: 'Announcement' },
    { time: '5h ago', account: '@betalabs', action: 'Released weekly market analysis infographic. Engagement rate 2x their average.', tag: 'Content' },
    { time: '8h ago', account: '@deltax_io', action: 'Posted meme about ETH gas fees that reached 1M+ impressions.', tag: 'Viral' },
    { time: '12h ago', account: '@gammafi', action: 'Hosted Twitter Space with 3,200 live listeners on L2 scaling solutions.', tag: 'Space' },
    { time: '1d ago', account: '@alphadao', action: 'Changed profile bio and pinned tweet. New positioning: "DeFi Intelligence Platform".', tag: 'Branding' },
    { time: '1d ago', account: '@betalabs', action: 'Started daily "Market Pulse" series. First edition got 800+ bookmarks.', tag: 'Series' },
    { time: '2d ago', account: '@deltax_io', action: 'Collaborated with @whale_alert for a joint AMA. Gained 2K new followers.', tag: 'Collab' },
  ];

  const STRATEGIES = [
    { name: 'AlphaDAO', breakdown: [{ label: 'Threads', pct: 35 }, { label: 'News', pct: 25 }, { label: 'Alpha', pct: 20 }, { label: 'Engagement', pct: 20 }] },
    { name: 'BetaLabs', breakdown: [{ label: 'Infographics', pct: 40 }, { label: 'Analysis', pct: 30 }, { label: 'News', pct: 20 }, { label: 'Polls', pct: 10 }] },
    { name: 'GammaFi', breakdown: [{ label: 'Alpha Calls', pct: 45 }, { label: 'Threads', pct: 25 }, { label: 'Spaces', pct: 20 }, { label: 'Memes', pct: 10 }] },
    { name: 'DeltaX', breakdown: [{ label: 'Memes', pct: 50 }, { label: 'News', pct: 20 }, { label: 'Threads', pct: 15 }, { label: 'Polls', pct: 15 }] },
  ];

  /* ---------- DOM ---------- */
  const $ = (sel) => document.querySelector(sel);

  /* ---------- Theme Toggle ---------- */
  function initTheme() {
    const saved = localStorage.getItem('competitor-monitor-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }
  initTheme();
  $('#theme-toggle').addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem('competitor-monitor-theme', isDark ? 'light' : 'dark');
  });

  /* ---------- Render Hero Comparison ---------- */
  function renderHeroComparison() {
    const grid = $('#hero-comparison');
    grid.innerHTML = COMPETITORS.map(c => `
      <div class="hero-comp-card">
        <div class="hero-comp-card__name">${c.name}</div>
        <div class="hero-comp-card__handle">${c.handle}</div>
        <div class="hero-comp-card__followers">${c.followers}</div>
        <div class="hero-comp-card__label">Followers</div>
      </div>
    `).join('');
  }

  /* ---------- Render Comparison Table ---------- */
  function renderComparisonTable() {
    const table = $('#comparison-table');
    const headerRow = '<tr><th>Metric</th>' + COMPETITORS.map(c => `<th>${c.name}</th>`).join('') + '</tr>';
    const bodyRows = METRICS.map(m => {
      const cells = m.values.map((v, i) => `<td class="${i === m.best ? 'metric-best' : ''}">${v}</td>`).join('');
      return `<tr><td class="metric-name">${m.name}</td>${cells}</tr>`;
    }).join('');
    table.innerHTML = '<thead>' + headerRow + '</thead><tbody>' + bodyRows + '</tbody>';
  }

  /* ---------- Render Timeline ---------- */
  function renderTimeline() {
    const list = $('#timeline-list');
    list.innerHTML = TIMELINE.map(item => `
      <div class="timeline-item">
        <div class="timeline-item__time">${item.time}</div>
        <div class="timeline-item__account">${item.account}</div>
        <div class="timeline-item__action">${item.action}</div>
        <span class="timeline-item__tag">${item.tag}</span>
      </div>
    `).join('');
  }

  /* ---------- Render Strategy ---------- */
  function renderStrategy() {
    const grid = $('#strategy-grid');
    grid.innerHTML = STRATEGIES.map(s => `
      <div class="strategy-card">
        <div class="strategy-card__name">${s.name}</div>
        <div class="strategy-card__breakdown">
          ${s.breakdown.map(b => `
            <div class="strategy-bar">
              <span class="strategy-bar__label">${b.label}</span>
              <div class="strategy-bar__track">
                <div class="strategy-bar__fill" style="width: ${b.pct}%"></div>
              </div>
              <span class="strategy-bar__value">${b.pct}%</span>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');
  }

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero — D8 translateX(40px) */
    const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__label', { x: 40, opacity: 0, duration: 0.5 })
      .from('.hero__title', { x: 40, opacity: 0, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { x: 40, opacity: 0, duration: 0.5 }, '-=0.3')
      .from('.hero-comp-card', { x: 40, opacity: 0, duration: 0.4, stagger: 0.08 }, '-=0.2');

    /* Table rows */
    gsap.from('.comparison-table tbody tr', {
      scrollTrigger: { trigger: '#comparison', start: 'top 80%', once: true },
      x: 40, opacity: 0, duration: 0.4, stagger: 0.05, ease: 'power3.out'
    });

    /* Timeline items */
    gsap.from('.timeline-item', {
      scrollTrigger: { trigger: '#timeline', start: 'top 80%', once: true },
      x: 40, opacity: 0, duration: 0.5, stagger: 0.06, ease: 'power3.out'
    });

    /* Strategy cards */
    gsap.from('.strategy-card', {
      scrollTrigger: { trigger: '#strategy', start: 'top 80%', once: true },
      x: 40, opacity: 0, duration: 0.5, stagger: 0.08, ease: 'power3.out'
    });
  }

  /* ---------- Init ---------- */
  function init() {
    renderHeroComparison();
    renderComparisonTable();
    renderTimeline();
    renderStrategy();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
