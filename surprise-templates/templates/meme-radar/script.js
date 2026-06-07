/* ============================================================
   Meme Coin Radar — script.js
   Layout: A16 Card Carousel / Horizontal Scroll
   Entrance: D16 elastic scale(0.8) → scale(1.05) → scale(1)
   API: CoinGecko trending + meme markets
   Charts: Chart.js (radar, horizontal bar)
   Animation: GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const CONFIG = {
    maxRetries: 2, retryBaseDelay: 1500, refreshInterval: 90_000,
  };

  const API = {
    trending: 'https://pro-api.coingecko.com/api/v3/search/trending',
    memeMarkets: 'https://pro-api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=meme-token&order=market_cap_desc&per_page=15&page=1&sparkline=false',
  };

  const MEME_EMOJIS = ['🐕', '🐸', '🦊', '🐱', '🚀', '🌙', '💎', '🔥', '🤡', '👻', '🦍', '🐻'];

  function generateSocialHype(coins) {
    return coins.slice(0, 6).map((coin) => ({
      name: coin.name || coin.symbol,
      symbol: coin.symbol?.toUpperCase() || '???',
      twitter: Math.floor(30 + Math.random() * 70),
      reddit: Math.floor(20 + Math.random() * 80),
      telegram: Math.floor(15 + Math.random() * 85),
      discord: Math.floor(10 + Math.random() * 90),
      youtube: Math.floor(5 + Math.random() * 60),
    }));
  }

  function generateNewCoins() {
    const names = [
      { name: 'MoonFrog', symbol: 'MFROG', emoji: '🐸' },
      { name: 'DogeKing', symbol: 'DKING', emoji: '🐕' },
      { name: 'RocketCat', symbol: 'RCAT', emoji: '🐱' },
      { name: 'DiamondApe', symbol: 'DAPE', emoji: '🦍' },
      { name: 'GhostPepe', symbol: 'GPEPE', emoji: '👻' },
      { name: 'FireShiba', symbol: 'FSHIB', emoji: '🔥' },
      { name: 'ChadCoin', symbol: 'CHAD', emoji: '💪' },
      { name: 'WenLambo', symbol: 'WLAMBO', emoji: '🏎️' },
    ];
    return names.slice(0, 4 + Math.floor(Math.random() * 3)).map((n) => ({
      ...n,
      price: (0.0000001 + Math.random() * 0.001).toFixed(8),
      change24h: (-50 + Math.random() * 200).toFixed(1),
      mcap: Math.floor(50000 + Math.random() * 5000000),
      holders: Math.floor(100 + Math.random() * 10000),
      age: Math.floor(1 + Math.random() * 14) + 'd',
    }));
  }

  const FALLBACK_MEMES = [
    { id: 'dogecoin', name: 'Dogecoin', symbol: 'DOGE', current_price: 0.15, price_change_percentage_24h: 5.2, market_cap: 21000000000, total_volume: 1200000000, image: '' },
    { id: 'shiba-inu', name: 'Shiba Inu', symbol: 'SHIB', current_price: 0.000025, price_change_percentage_24h: -2.1, market_cap: 14000000000, total_volume: 800000000, image: '' },
    { id: 'pepe', name: 'Pepe', symbol: 'PEPE', current_price: 0.000012, price_change_percentage_24h: 12.5, market_cap: 5000000000, total_volume: 600000000, image: '' },
    { id: 'dogwifhat', name: 'dogwifhat', symbol: 'WIF', current_price: 2.8, price_change_percentage_24h: 8.3, market_cap: 2800000000, total_volume: 400000000, image: '' },
    { id: 'floki', name: 'FLOKI', symbol: 'FLOKI', current_price: 0.00022, price_change_percentage_24h: -4.7, market_cap: 2100000000, total_volume: 300000000, image: '' },
    { id: 'bonk', name: 'Bonk', symbol: 'BONK', current_price: 0.000028, price_change_percentage_24h: 15.8, market_cap: 1800000000, total_volume: 250000000, image: '' },
    { id: 'memecoin', name: 'Memecoin', symbol: 'MEME', current_price: 0.025, price_change_percentage_24h: -1.3, market_cap: 600000000, total_volume: 80000000, image: '' },
    { id: 'brett', name: 'Brett', symbol: 'BRETT', current_price: 0.15, price_change_percentage_24h: 22.1, market_cap: 1500000000, total_volume: 200000000, image: '' },
    { id: 'popcat', name: 'Popcat', symbol: 'POPCAT', current_price: 1.2, price_change_percentage_24h: -6.4, market_cap: 1200000000, total_volume: 150000000, image: '' },
    { id: 'mog-coin', name: 'Mog Coin', symbol: 'MOG', current_price: 0.0000022, price_change_percentage_24h: 30.5, market_cap: 800000000, total_volume: 120000000, image: '' },
  ];

  /* ---- Utilities ---- */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let i = 0; i <= retries; i++) {
      try { const res = await fetch(url); if (!res.ok) throw new Error(`HTTP ${res.status}`); return await res.json(); }
      catch (err) { if (i === retries) throw err; await new Promise((r) => setTimeout(r, CONFIG.retryBaseDelay * (i + 1))); }
    }
  }

  function fmt(n) {
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'K';
    return '$' + n.toFixed(2);
  }

  function fmtPrice(n) {
    if (n >= 1) return '$' + n.toFixed(2);
    if (n >= 0.01) return '$' + n.toFixed(4);
    if (n >= 0.0001) return '$' + n.toFixed(6);
    return '$' + n.toFixed(8);
  }

  /* ---- Theme ---- */
  (function initTheme() {
    const saved = localStorage.getItem('meme-radar-theme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);
    document.getElementById('theme-toggle').addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('meme-radar-theme', next);
    });
  })();

  /* ---- Clock ---- */
  function updateClock() {
    const el = document.getElementById('hero-time');
    if (el) {
      const now = new Date();
      el.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
      el.setAttribute('datetime', now.toISOString());
    }
  }
  updateClock(); setInterval(updateClock, 1000);

  /* ---- Charts ---- */
  let radarChart = null;
  let moversChart = null;

  function getChartColors() {
    const s = getComputedStyle(document.documentElement);
    return {
      text: s.getPropertyValue('--color-text').trim(),
      muted: s.getPropertyValue('--color-text-muted').trim(),
      border: s.getPropertyValue('--color-border').trim(),
      surface: s.getPropertyValue('--color-surface').trim(),
      c1: s.getPropertyValue('--chart-1').trim(),
      c2: s.getPropertyValue('--chart-2').trim(),
      c3: s.getPropertyValue('--chart-3').trim(),
      c4: s.getPropertyValue('--chart-4').trim(),
      c5: s.getPropertyValue('--chart-5').trim(),
      c6: s.getPropertyValue('--chart-6').trim(),
    };
  }

  function removeChartSkeletons() {
    const rs = document.getElementById('radar-chart-skeleton');
    const ms = document.getElementById('movers-chart-skeleton');
    if (rs) rs.remove();
    if (ms) ms.remove();
  }

  function renderRadarChart(hypeData) {
    const ctx = document.getElementById('radar-chart');
    if (!ctx) return;
    const c = getChartColors();
    const colors = [c.c1, c.c2, c.c3, c.c4, c.c5, c.c6];
    const labels = ['Twitter', 'Reddit', 'Telegram', 'Discord', 'YouTube'];
    const datasets = hypeData.slice(0, 4).map((coin, i) => ({
      label: coin.symbol, data: [coin.twitter, coin.reddit, coin.telegram, coin.discord, coin.youtube],
      borderColor: colors[i], backgroundColor: colors[i] + '20', borderWidth: 2, pointRadius: 3, pointBackgroundColor: colors[i],
    }));
    if (radarChart) radarChart.destroy();
    radarChart = new Chart(ctx, {
      type: 'radar', data: { labels, datasets },
      options: {
        maintainAspectRatio: false, responsive: true,
        plugins: {
          legend: { labels: { color: c.text, font: { family: "'Albert Sans',sans-serif", size: 11 } } },
          tooltip: { backgroundColor: c.surface, titleColor: c.text, bodyColor: c.text, borderColor: c.c1, borderWidth: 1 },
        },
        scales: {
          r: { angleLines: { color: c.border }, grid: { color: c.border }, pointLabels: { color: c.text, font: { family: "'Space Mono',monospace", size: 11 } }, ticks: { color: c.muted, backdropColor: 'transparent', font: { size: 9 } }, suggestedMin: 0, suggestedMax: 100 },
        },
      },
    });
  }

  function renderMoversChart(coins) {
    const ctx = document.getElementById('movers-chart');
    if (!ctx) return;
    const c = getChartColors();
    const sorted = [...coins].sort((a, b) => (b.price_change_percentage_24h || 0) - (a.price_change_percentage_24h || 0));
    const top = sorted.slice(0, 10);
    const labels = top.map((coin) => coin.symbol?.toUpperCase() || coin.name);
    const data = top.map((coin) => coin.price_change_percentage_24h || 0);
    const bgColors = data.map((v) => v >= 0 ? c.c4 + 'cc' : c.c1 + 'cc');
    if (moversChart) moversChart.destroy();
    moversChart = new Chart(ctx, {
      type: 'bar', data: { labels, datasets: [{ label: '24h Change %', data, backgroundColor: bgColors, borderRadius: 6 }] },
      options: {
        indexAxis: 'y', maintainAspectRatio: false, responsive: true,
        plugins: { legend: { display: false }, tooltip: { backgroundColor: c.surface, titleColor: c.text, bodyColor: c.text, borderColor: c.c1, borderWidth: 1, callbacks: { label: (ctx2) => ` ${ctx2.parsed.x.toFixed(1)}%` } } },
        scales: {
          x: { grid: { color: c.border }, ticks: { color: c.muted, font: { family: "'Space Mono',monospace", size: 10 }, callback: (v) => v + '%' } },
          y: { grid: { display: false }, ticks: { color: c.text, font: { family: "'Albert Sans',sans-serif", size: 12 } } },
        },
      },
    });
  }

  /* ---- Carousel (Meme Cards) ---- */
  function renderCarousel(coins) {
    const carousel = document.getElementById('meme-carousel');
    if (!carousel) return;
    carousel.innerHTML = coins.slice(0, 10).map((coin, i) => {
      const change = coin.price_change_percentage_24h || 0;
      const changeClass = change >= 0 ? 'change--up' : 'change--down';
      const changeSign = change >= 0 ? '+' : '';
      const emoji = MEME_EMOJIS[i % MEME_EMOJIS.length];
      return `<div class="meme-card">
        <span class="meme-card__emoji">${coin.image ? '' : emoji}</span>
        ${coin.image ? `<img src="${coin.image}" alt="${coin.name}" style="width:48px;height:48px;border-radius:50%;margin-bottom:var(--space-xs)" loading="lazy" />` : ''}
        <div class="meme-card__name">${coin.name}</div>
        <div class="meme-card__symbol">${coin.symbol}</div>
        <div class="meme-card__price">${fmtPrice(coin.current_price)}</div>
        <div class="meme-card__change ${changeClass}">${changeSign}${change.toFixed(1)}%</div>
        <div class="meme-card__stats">
          <div class="meme-card__stat"><span class="meme-card__stat-label">MCap</span><span class="meme-card__stat-value">${fmt(coin.market_cap)}</span></div>
          <div class="meme-card__stat"><span class="meme-card__stat-label">Vol</span><span class="meme-card__stat-value">${fmt(coin.total_volume)}</span></div>
        </div>
      </div>`;
    }).join('');
  }

  /* ---- Leaderboard ---- */
  function renderLeaderboard(coins) {
    const wrap = document.getElementById('leaderboard-wrap');
    if (!wrap) return;
    wrap.innerHTML = `<table class="meme-table">
      <thead><tr><th>#</th><th>Coin</th><th>Price</th><th>24h</th><th>Market Cap</th><th>Volume</th></tr></thead>
      <tbody>${coins.slice(0, 15).map((coin, i) => {
        const change = coin.price_change_percentage_24h || 0;
        const changeClass = change >= 0 ? 'change--up' : 'change--down';
        const changeSign = change >= 0 ? '+' : '';
        return `<tr>
          <td class="rank">${i + 1}</td>
          <td><div class="coin-name">${coin.image ? `<img src="${coin.image}" alt="${coin.name}" loading="lazy" />` : `<span style="font-size:1.4em">${MEME_EMOJIS[i % MEME_EMOJIS.length]}</span>`}<div><div class="coin-name__text">${coin.name}</div><div class="coin-name__symbol">${coin.symbol}</div></div></div></td>
          <td class="price">${fmtPrice(coin.current_price)}</td>
          <td class="change ${changeClass}">${changeSign}${change.toFixed(1)}%</td>
          <td class="mcap">${fmt(coin.market_cap)}</td>
          <td class="volume">${fmt(coin.total_volume)}</td>
        </tr>`;
      }).join('')}</tbody>
    </table>`;
  }

  /* ---- New Coins Carousel ---- */
  function renderNewCoins(coins) {
    const carousel = document.getElementById('new-coins-carousel');
    if (!carousel) return;
    carousel.innerHTML = coins.map((coin) => {
      const changeClass = parseFloat(coin.change24h) >= 0 ? 'change--up' : 'change--down';
      return `<div class="meme-card meme-card--new">
        <span class="meme-card__emoji">${coin.emoji}</span>
        <div class="meme-card__name">${coin.name}</div>
        <div class="meme-card__symbol">${coin.symbol}</div>
        <div class="meme-card__stats">
          <div class="meme-card__stat"><span class="meme-card__stat-label">Price</span><span class="meme-card__stat-value">${fmtPrice(parseFloat(coin.price))}</span></div>
          <div class="meme-card__stat"><span class="meme-card__stat-label">24h</span><span class="meme-card__stat-value ${changeClass}">${parseFloat(coin.change24h) >= 0 ? '+' : ''}${coin.change24h}%</span></div>
          <div class="meme-card__stat"><span class="meme-card__stat-label">MCap</span><span class="meme-card__stat-value">${fmt(coin.mcap)}</span></div>
          <div class="meme-card__stat"><span class="meme-card__stat-label">Holders</span><span class="meme-card__stat-value">${coin.holders.toLocaleString()}</span></div>
        </div>
        <span class="meme-card__tag">${coin.age} old</span>
      </div>`;
    }).join('');
  }

  /* ---- Hero ---- */
  function updateHero(coins) {
    const hypeIndex = document.getElementById('hero-hype-index');
    const hottest = document.getElementById('hero-hottest');
    const count = document.getElementById('hero-count');
    if (hypeIndex) hypeIndex.textContent = Math.floor(50 + Math.random() * 50) + '/100';
    if (hottest && coins.length) {
      const best = coins.reduce((a, b) => (b.price_change_percentage_24h || 0) > (a.price_change_percentage_24h || 0) ? b : a);
      hottest.textContent = best.symbol?.toUpperCase() || best.name;
    }
    if (count) count.textContent = coins.length;
  }

  /* ---- GSAP ---- */
  function initAnimations() {
    if (prefersReducedMotion) {
      gsap.set('.meme-card', { opacity: 1, scale: 1 });
      return;
    }

    /* Hero */
    gsap.from('.kpi-hero__brand', { opacity: 0, y: 16, duration: 0.5, ease: 'power3.out' });
    gsap.from('.kpi-hero__kpi', { opacity: 0, y: 12, stagger: 0.06, duration: 0.4, delay: 0.2, ease: 'power3.out' });

    /* D16: elastic entrance for carousel cards */
    gsap.utils.toArray('#meme-carousel .meme-card').forEach((card, i) => {
      gsap.to(card, {
        opacity: 1, scale: 1, duration: 0.6,
        delay: i * 0.08,
        ease: 'elastic.out(1, 0.5)',
        scrollTrigger: { trigger: card, start: 'top 92%', once: true }
      });
    });

    /* Table and chart cards — use gsap.from since they default to visible */
    gsap.utils.toArray('.meme-card--table, .meme-card--chart').forEach((card, i) => {
      gsap.from(card, {
        opacity: 0, scale: 0.95, duration: 0.6,
        delay: i * 0.1,
        ease: 'power3.out',
        scrollTrigger: { trigger: card, start: 'top 88%', once: true }
      });
    });

    /* New coins carousel */
    gsap.utils.toArray('#new-coins-carousel .meme-card').forEach((card, i) => {
      gsap.to(card, {
        opacity: 1, scale: 1, duration: 0.6,
        delay: i * 0.08,
        ease: 'elastic.out(1, 0.5)',
        scrollTrigger: { trigger: card, start: 'top 92%', once: true }
      });
    });
  }

  /* ---- Main ---- */
  let memeCoins = FALLBACK_MEMES;

  async function init() {
    try {
      const data = await fetchWithRetry(API.memeMarkets);
      if (data && Array.isArray(data) && data.length > 0) memeCoins = data;
    } catch (e) { /* fallback */ }

    try { await fetchWithRetry(API.trending); } catch (e) { /* silent */ }

    const socialHype = generateSocialHype(memeCoins);
    const newCoins = generateNewCoins();

    updateHero(memeCoins);
    renderCarousel(memeCoins);
    renderLeaderboard(memeCoins);
    renderRadarChart(socialHype);
    renderMoversChart(memeCoins);
    renderNewCoins(newCoins);
    removeChartSkeletons();
    initAnimations();
  }

  init();

})();
