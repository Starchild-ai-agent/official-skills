/* ============================================================
   Market Overview Dashboard — script.js
   CoinGecko API + simulated stock/forex data
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Constants ---------- */
  const COINGECKO_BASE = 'https://pro-api.coingecko.com/api/v3';
  const FNG_API = 'https://api.alternative.me/fng/?limit=1';
  const REFRESH_INTERVAL = 60000; // 60s
  const TRACKED_COINS = ['bitcoin', 'ethereum', 'solana', 'binancecoin', 'ripple', 'cardano', 'dogecoin', 'avalanche-2'];

  /* Simulated stock indices */
  const STOCK_INDICES = [
    { name: 'S&P 500',  base: 5420, volatility: 0.008 },
    { name: 'NASDAQ',   base: 17200, volatility: 0.012 },
    { name: 'Hang Seng', base: 18500, volatility: 0.010 },
    { name: 'Nikkei 225', base: 38900, volatility: 0.009 },
    { name: 'DAX',      base: 18400, volatility: 0.007 },
  ];

  /* Simulated forex pairs */
  const FOREX_PAIRS = [
    { pair: 'EUR/USD', base: 1.0850, volatility: 0.003 },
    { pair: 'GBP/USD', base: 1.2720, volatility: 0.004 },
    { pair: 'USD/JPY', base: 157.20, volatility: 0.005 },
    { pair: 'USD/CNY', base: 7.2450, volatility: 0.002 },
    { pair: 'AUD/USD', base: 0.6650, volatility: 0.004 },
  ];

  /* ---------- DOM refs ---------- */
  const headerClock   = document.getElementById('headerClock');
  const headerDate    = document.getElementById('headerDate');
  const apiStatus     = document.getElementById('apiStatus');
  const totalMcap     = document.getElementById('totalMcap');
  const totalMcapChange = document.getElementById('totalMcapChange');
  const totalVolume   = document.getElementById('totalVolume');
  const btcDominance  = document.getElementById('btcDominance');
  const activeCryptos = document.getElementById('activeCryptos');
  const cryptoList    = document.getElementById('cryptoList');
  const fngCanvas     = document.getElementById('fngCanvas');
  const fngValue      = document.getElementById('fngValue');
  const fngLabel      = document.getElementById('fngLabel');
  const stockList     = document.getElementById('stockList');
  const trendingList  = document.getElementById('trendingList');
  const forexList     = document.getElementById('forexList');
  const themeToggle   = document.getElementById('themeToggle');

  /* ---------- Theme ---------- */
  function initTheme() {
    const saved = localStorage.getItem('mkt-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('mkt-theme', next);
  });

  initTheme();

  /* ---------- Header Clock ---------- */
  function updateHeaderClock() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    headerClock.textContent = `${h}:${m}:${s}`;

    headerDate.textContent = now.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  }

  setInterval(updateHeaderClock, 1000);
  updateHeaderClock();

  /* ---------- Utility ---------- */
  function formatUSD(n) {
    if (n >= 1e12) return '$' + (n / 1e12).toFixed(2) + 'T';
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'K';
    return '$' + n.toFixed(2);
  }

  function formatPrice(n) {
    if (n >= 1000) return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (n >= 1) return '$' + n.toFixed(2);
    return '$' + n.toFixed(4);
  }

  function changeClass(val) {
    if (val > 0) return 'change--positive';
    if (val < 0) return 'change--negative';
    return 'change--neutral';
  }

  function changeText(val) {
    const sign = val >= 0 ? '+' : '';
    return sign + val.toFixed(2) + '%';
  }

  /* ---------- Fetch: Global Market Data ---------- */
  async function fetchGlobalData() {
    try {
      const res = await fetch(`${COINGECKO_BASE}/global`);
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      const d = data.data;

      totalMcap.textContent = formatUSD(d.total_market_cap.usd);
      const mcapPct = d.market_cap_change_percentage_24h_usd;
      totalMcapChange.textContent = changeText(mcapPct);
      totalMcapChange.className = 'metric-card__change ' + changeClass(mcapPct);

      totalVolume.textContent = formatUSD(d.total_volume.usd);
      btcDominance.textContent = d.market_cap_percentage.btc.toFixed(1) + '%';
      activeCryptos.textContent = d.active_cryptocurrencies.toLocaleString();

      apiStatus.textContent = '● LIVE';
      apiStatus.classList.remove('terminal-header__status--error');
    } catch {
      apiStatus.textContent = '● OFFLINE';
      apiStatus.classList.add('terminal-header__status--error');
      // Use fallback data
      totalMcap.textContent = '$2.45T';
      totalVolume.textContent = '$89.2B';
      btcDominance.textContent = '54.3%';
      activeCryptos.textContent = '14,200';
    }
  }

  /* ---------- Fetch: Crypto Prices ---------- */
  async function fetchCryptoPrices() {
    try {
      const ids = TRACKED_COINS.join(',');
      const res = await fetch(`${COINGECKO_BASE}/coins/markets?vs_currency=usd&ids=${ids}&order=market_cap_desc&sparkline=false`);
      if (!res.ok) throw new Error('API error');
      const coins = await res.json();
      renderCryptoList(coins);
    } catch {
      // Fallback data
      const fallback = [
        { name: 'Bitcoin', symbol: 'btc', current_price: 67420, price_change_percentage_24h: 2.34, market_cap_rank: 1 },
        { name: 'Ethereum', symbol: 'eth', current_price: 3580, price_change_percentage_24h: -1.12, market_cap_rank: 2 },
        { name: 'Solana', symbol: 'sol', current_price: 172.50, price_change_percentage_24h: 5.67, market_cap_rank: 5 },
        { name: 'BNB', symbol: 'bnb', current_price: 612, price_change_percentage_24h: 0.89, market_cap_rank: 4 },
        { name: 'XRP', symbol: 'xrp', current_price: 0.5234, price_change_percentage_24h: -0.45, market_cap_rank: 6 },
        { name: 'Cardano', symbol: 'ada', current_price: 0.4521, price_change_percentage_24h: 1.23, market_cap_rank: 8 },
        { name: 'Dogecoin', symbol: 'doge', current_price: 0.1523, price_change_percentage_24h: 3.45, market_cap_rank: 9 },
        { name: 'Avalanche', symbol: 'avax', current_price: 36.80, price_change_percentage_24h: -2.10, market_cap_rank: 12 },
      ];
      renderCryptoList(fallback);
    }
  }

  function renderCryptoList(coins) {
    cryptoList.innerHTML = '';
    coins.forEach(coin => {
      const pct = coin.price_change_percentage_24h || 0;
      const row = document.createElement('div');
      row.className = 'crypto-row';
      row.innerHTML = `
        <span class="crypto-row__rank">#${coin.market_cap_rank || '—'}</span>
        <div class="crypto-row__info">
          <span class="crypto-row__name">${coin.name}</span>
          <span class="crypto-row__symbol">${coin.symbol}</span>
        </div>
        <span class="crypto-row__price">${formatPrice(coin.current_price)}</span>
        <span class="crypto-row__change ${changeClass(pct)}">${changeText(pct)}</span>
      `;
      cryptoList.appendChild(row);
    });
  }

  /* ---------- Fetch: Fear & Greed ---------- */
  async function fetchFearGreed() {
    try {
      const res = await fetch(FNG_API);
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      const fng = data.data[0];
      const value = parseInt(fng.value, 10);
      const label = fng.value_classification;
      renderFngGauge(value, label);
    } catch {
      renderFngGauge(45, 'Fear');
    }
  }

  function renderFngGauge(value, label) {
    fngValue.textContent = value;
    fngLabel.textContent = label;

    const canvas = fngCanvas;
    const dpr = window.devicePixelRatio || 1;
    const w = 200;
    const h = 120;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    canvas.width = w * dpr;
    canvas.height = h * dpr;

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const cx = w / 2;
    const cy = h - 10;
    const r = 80;
    const startAngle = Math.PI;
    const endAngle = 2 * Math.PI;

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, endAngle);
    ctx.lineWidth = 12;
    const styles = getComputedStyle(document.documentElement);
    ctx.strokeStyle = styles.getPropertyValue('--bg-tertiary').trim() || '#222';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Gradient arc
    const gradient = ctx.createLinearGradient(cx - r, cy, cx + r, cy);
    gradient.addColorStop(0, '#ef4444');
    gradient.addColorStop(0.25, '#f59e0b');
    gradient.addColorStop(0.5, '#eab308');
    gradient.addColorStop(0.75, '#84cc16');
    gradient.addColorStop(1, '#22c55e');

    const valueAngle = startAngle + (value / 100) * Math.PI;
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, valueAngle);
    ctx.lineWidth = 12;
    ctx.strokeStyle = gradient;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Needle
    const needleAngle = startAngle + (value / 100) * Math.PI;
    const needleLen = r - 20;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(
      cx + needleLen * Math.cos(needleAngle),
      cy + needleLen * Math.sin(needleAngle)
    );
    ctx.strokeStyle = styles.getPropertyValue('--accent').trim() || '#eab308';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Center dot
    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = styles.getPropertyValue('--accent').trim() || '#eab308';
    ctx.fill();
  }

  /* ---------- Simulated: Stock Indices ---------- */
  function renderStockIndices() {
    stockList.innerHTML = '';
    STOCK_INDICES.forEach(idx => {
      const change = (Math.random() - 0.48) * idx.volatility * 100;
      const price = idx.base * (1 + change / 100);

      const row = document.createElement('div');
      row.className = 'stock-row';
      row.innerHTML = `
        <span class="stock-row__name">${idx.name}</span>
        <div class="stock-row__values">
          <span class="stock-row__price">${price.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</span>
          <span class="stock-row__change ${changeClass(change)}">${changeText(change)}</span>
        </div>
      `;
      stockList.appendChild(row);
    });
  }

  /* ---------- Fetch: Trending Coins ---------- */
  async function fetchTrending() {
    try {
      const res = await fetch(`${COINGECKO_BASE}/search/trending`);
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      renderTrending(data.coins.slice(0, 8));
    } catch {
      // Fallback
      const fallback = [
        { item: { name: 'Pepe', symbol: 'PEPE', thumb: '', market_cap_rank: 25 } },
        { item: { name: 'Bonk', symbol: 'BONK', thumb: '', market_cap_rank: 60 } },
        { item: { name: 'Render', symbol: 'RNDR', thumb: '', market_cap_rank: 30 } },
        { item: { name: 'Injective', symbol: 'INJ', thumb: '', market_cap_rank: 40 } },
        { item: { name: 'Sui', symbol: 'SUI', thumb: '', market_cap_rank: 45 } },
        { item: { name: 'Celestia', symbol: 'TIA', thumb: '', market_cap_rank: 55 } },
      ];
      renderTrending(fallback);
    }
  }

  function renderTrending(coins) {
    trendingList.innerHTML = '';
    coins.forEach((coin, i) => {
      const c = coin.item;
      const card = document.createElement('div');
      card.className = 'trending-card';
      card.innerHTML = `
        <span class="trending-card__rank">${i + 1}</span>
        ${c.thumb ? `<img class="trending-card__img" src="${c.thumb}" alt="${c.name}" loading="lazy" />` : '<div class="trending-card__img"></div>'}
        <div class="trending-card__info">
          <span class="trending-card__name">${c.name}</span>
          <span class="trending-card__symbol">${c.symbol}</span>
        </div>
      `;
      trendingList.appendChild(card);
    });
  }

  /* ---------- Simulated: Forex ---------- */
  function renderForex() {
    forexList.innerHTML = '';
    FOREX_PAIRS.forEach(fx => {
      const change = (Math.random() - 0.48) * fx.volatility * 100;
      const rate = fx.base * (1 + change / 100);
      const decimals = fx.base >= 100 ? 2 : 4;

      const row = document.createElement('div');
      row.className = 'forex-row';
      row.innerHTML = `
        <span class="forex-row__pair">${fx.pair}</span>
        <span class="forex-row__rate">${rate.toFixed(decimals)}</span>
        <span class="forex-row__change ${changeClass(change)}">${changeText(change)}</span>
      `;
      forexList.appendChild(row);
    });
  }

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      document.querySelectorAll('.market-panel').forEach(p => {
        p.style.opacity = '1';
        p.style.transform = 'none';
      });
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    // Terminal header
    gsap.fromTo('.terminal-header', {
      opacity: 0, y: -10,
    }, {
      opacity: 1, y: 0,
      duration: 0.4,
      ease: 'power2.out',
    });

    // Panels: D2 stagger left-to-right
    const panels = document.querySelectorAll('.market-panel');
    panels.forEach((panel, i) => {
      gsap.fromTo(panel, {
        opacity: 0,
        x: -20,
      }, {
        opacity: 1,
        x: 0,
        duration: 0.5,
        delay: 0.08 * i,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: panel,
          start: 'top 90%',
          once: true,
        },
      });
    });
  }

  /* ---------- Fetch all data ---------- */
  async function fetchAllData() {
    await Promise.allSettled([
      fetchGlobalData(),
      fetchCryptoPrices(),
      fetchFearGreed(),
      fetchTrending(),
    ]);
    renderStockIndices();
    renderForex();
  }

  /* ---------- Init ---------- */
  async function init() {
    await fetchAllData();
    initAnimations();

  }

  init();
})();
