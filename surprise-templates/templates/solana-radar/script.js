/* ============================================================
   Solana Ecosystem Radar — script.js

   APIs: CoinGecko (SOL price + ecosystem tokens) + Mock data
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D6 scale(1.05) → scale(1)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Register GSAP Plugins ---------- */
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Reduced Motion Check ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    solPrice: () =>
      'https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd&include_24hr_change=true',
    solEcosystem: () =>
      'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=solana-ecosystem&order=market_cap_desc&per_page=10&sparkline=false&price_change_percentage=24h',
  };

  /* ---------- Mock Data ---------- */
  const DAPP_RANKINGS = [
    { rank: 1, name: 'Marinade', category: 'Liquid Staking', tvl: '$1.8B', users: '45K', change: '+5.2%' },
    { rank: 2, name: 'Raydium', category: 'DEX / AMM', tvl: '$890M', users: '120K', change: '+12.3%' },
    { rank: 3, name: 'Jupiter', category: 'DEX Aggregator', tvl: '$650M', users: '280K', change: '+8.7%' },
    { rank: 4, name: 'Kamino', category: 'Lending', tvl: '$1.2B', users: '35K', change: '+15.1%' },
    { rank: 5, name: 'Jito', category: 'MEV / Staking', tvl: '$2.1B', users: '28K', change: '+22.4%' },
    { rank: 6, name: 'Orca', category: 'DEX / CLMM', tvl: '$320M', users: '65K', change: '+3.8%' },
    { rank: 7, name: 'Drift', category: 'Perps DEX', tvl: '$450M', users: '42K', change: '+9.1%' },
    { rank: 8, name: 'Marginfi', category: 'Lending', tvl: '$780M', users: '55K', change: '-2.3%' },
    { rank: 9, name: 'Tensor', category: 'NFT Market', tvl: '$120M', users: '89K', change: '+18.5%' },
  ];

  const NFT_COLLECTIONS = [
    { rank: 1, name: 'Mad Lads', floor: '142 SOL', volume24h: '2,340 SOL', listed: '4.2%', holders: '5,891' },
    { rank: 2, name: 'Tensorians', floor: '28 SOL', volume24h: '1,890 SOL', listed: '6.1%', holders: '4,234' },
    { rank: 3, name: 'Claynosaurz', floor: '35 SOL', volume24h: '890 SOL', listed: '3.8%', holders: '3,567' },
    { rank: 4, name: 'Famous Fox', floor: '18 SOL', volume24h: '456 SOL', listed: '5.5%', holders: '4,891' },
    { rank: 5, name: 'Okay Bears', floor: '12 SOL', volume24h: '234 SOL', listed: '7.2%', holders: '3,234' },
    { rank: 6, name: 'SMB Gen2', floor: '45 SOL', volume24h: '678 SOL', listed: '4.8%', holders: '2,891' },
  ];

  const DEX_DATA = [
    { name: 'Jupiter', volume: '$2.8B', change: '+15.3%', changeDir: 'up', pairs: '1,200+', detail: 'Aggregator — routes across all Solana DEXs' },
    { name: 'Raydium', volume: '$1.4B', change: '+8.7%', changeDir: 'up', pairs: '3,400+', detail: 'AMM + CLMM — deepest on-chain liquidity' },
    { name: 'Orca', volume: '$680M', change: '-2.1%', changeDir: 'down', pairs: '850+', detail: 'Concentrated liquidity — Whirlpools' },
  ];

  const NETWORK_HEALTH = [
    { label: 'Current TPS', value: '3,847', status: 'good', statusText: 'Healthy' },
    { label: 'Validators', value: '1,892', status: 'good', statusText: 'Decentralized' },
    { label: 'Epoch', value: '612', status: 'good', statusText: 'Active' },
    { label: 'Stake Rate', value: '67.2%', status: 'good', statusText: 'Strong' },
    { label: 'Skip Rate', value: '0.8%', status: 'good', statusText: 'Low' },
    { label: 'Avg Block Time', value: '400ms', status: 'good', statusText: 'Fast' },
  ];

  const MOCK_TOKENS = [
    { name: 'JTO', change: 12.5 },
    { name: 'JUP', change: 8.3 },
    { name: 'PYTH', change: -3.2 },
    { name: 'BONK', change: 25.1 },
    { name: 'WIF', change: -8.7 },
    { name: 'RNDR', change: 5.4 },
    { name: 'HNT', change: 2.1 },
    { name: 'RAY', change: 11.8 },
    { name: 'ORCA', change: -1.5 },
    { name: 'MNDE', change: 7.9 },
  ];

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.hero__content > *', { opacity: 1 });
      return;
    }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__badge', { opacity: 0, y: -15, duration: 0.5 })
      .from('.hero__title', { opacity: 0, scale: 1.05, duration: 0.7 }, '-=0.2')
      .from('.hero__subtitle', { opacity: 0, y: 15, duration: 0.5 }, '-=0.3')
      .from('.hero__metric', { opacity: 0, y: 20, stagger: 0.1, duration: 0.5 }, '-=0.2')
      .from('.hero__metric-divider', { opacity: 0, scaleY: 0, stagger: 0.08, duration: 0.3 }, '-=0.4');
  }

  /** D6: scale(1.05) → scale(1) entrance */
  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.sol-panel, .chart-container, .nft-card, .dex-card, .health-card', {
        opacity: 1, scale: 1,
      });
      return;
    }

    const targets = gsap.utils.toArray('.sol-panel, .chart-container, .nft-card, .dex-card, .health-card');
    targets.forEach((el) => {
      gsap.to(el, {
        opacity: 1,
        scale: 1,
        duration: 0.6,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: el,
          start: 'top 90%',
          toggleActions: 'play none none none',
        },
      });
    });
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */
  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    const html = document.documentElement;
    const stored = localStorage.getItem('solana-radar-theme');
    if (stored) html.setAttribute('data-theme', stored);

    btn.addEventListener('click', () => {
      const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      localStorage.setItem('solana-radar-theme', next);
    });
  }

  /* ============================================================
     DATA FETCHING
     ============================================================ */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let i = 0; i <= retries; i++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (i === retries) throw err;
        await new Promise((r) => setTimeout(r, CONFIG.retryBaseDelay * (i + 1)));
      }
    }
  }

  /* ---------- SOL Price ---------- */
  async function loadSolPrice() {
    const el = document.getElementById('metric-sol-price');
    if (!el) return;
    try {
      const data = await fetchWithRetry(API.solPrice());
      const price = data.solana.usd;
      el.textContent = `$${price.toLocaleString()}`;
    } catch {
      el.textContent = '$178.50';
    }
  }

  /* ---------- Hero Metrics ---------- */
  function loadHeroMetrics() {
    document.getElementById('metric-tps').textContent = '3,847';
    document.getElementById('metric-addresses').textContent = '1.2M';
  }

  /* ---------- DApp Rankings ---------- */
  function loadDapps() {
    const container = document.getElementById('dapp-grid');
    if (!container) return;

    container.innerHTML = DAPP_RANKINGS.map((d) => `
      <div class="sol-panel">
        <div class="dapp-card__rank">#${d.rank}</div>
        <div class="dapp-card__name">${d.name}</div>
        <div class="dapp-card__category">${d.category}</div>
        <div class="dapp-card__stats">
          <div>
            <span>TVL</span>
            <span class="dapp-card__stat-value">${d.tvl}</span>
          </div>
          <div>
            <span>Users</span>
            <span class="dapp-card__stat-value">${d.users}</span>
          </div>
          <div>
            <span>24h</span>
            <span class="dapp-card__stat-value">${d.change}</span>
          </div>
        </div>
      </div>
    `).join('');
  }

  /* ---------- Ecosystem Tokens Chart ---------- */
  async function loadTokensChart() {
    const canvas = document.getElementById('tokens-chart');
    if (!canvas) return;

    let tokenData = MOCK_TOKENS;

    try {
      const coins = await fetchWithRetry(API.solEcosystem());
      if (coins && coins.length > 0) {
        tokenData = coins.slice(0, 10).map((c) => ({
          name: c.symbol.toUpperCase(),
          change: c.price_change_percentage_24h || 0,
        }));
      }
    } catch {
      // Use mock data
    }

    const style = getComputedStyle(document.documentElement);
    const accent = style.getPropertyValue('--color-accent').trim();
    const danger = style.getPropertyValue('--color-danger').trim();
    const textMuted = style.getPropertyValue('--color-text-muted').trim();
    const border = style.getPropertyValue('--color-border').trim();

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: tokenData.map((t) => t.name),
        datasets: [{
          label: '24h Change %',
          data: tokenData.map((t) => t.change),
          backgroundColor: tokenData.map((t) => t.change >= 0 ? accent : danger),
          borderRadius: 4,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#16112a',
            titleFont: { family: 'JetBrains Mono', size: 11 },
            bodyFont: { family: 'JetBrains Mono', size: 10 },
            callbacks: {
              label: (ctx) => `${ctx.raw >= 0 ? '+' : ''}${ctx.raw.toFixed(1)}%`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: textMuted, font: { family: 'JetBrains Mono', size: 10 } },
          },
          y: {
            grid: { color: border },
            ticks: {
              color: textMuted,
              font: { family: 'JetBrains Mono', size: 10 },
              callback: (v) => `${v >= 0 ? '+' : ''}${v}%`,
            },
          },
        },
      },
    });
  }

  /* ---------- NFT Market ---------- */
  function loadNfts() {
    const container = document.getElementById('nft-grid');
    if (!container) return;

    container.innerHTML = NFT_COLLECTIONS.map((n) => `
      <div class="nft-card">
        <div class="nft-card__rank">#${n.rank} on Magic Eden</div>
        <div class="nft-card__name">${n.name}</div>
        <div class="nft-card__stats">
          <div>
            <div class="nft-card__stat-label">Floor</div>
            <div class="nft-card__stat-value nft-card__stat-value--accent">${n.floor}</div>
          </div>
          <div>
            <div class="nft-card__stat-label">24h Vol</div>
            <div class="nft-card__stat-value">${n.volume24h}</div>
          </div>
          <div>
            <div class="nft-card__stat-label">Listed</div>
            <div class="nft-card__stat-value">${n.listed}</div>
          </div>
          <div>
            <div class="nft-card__stat-label">Holders</div>
            <div class="nft-card__stat-value">${n.holders}</div>
          </div>
        </div>
      </div>
    `).join('');
  }

  /* ---------- DEX Comparison ---------- */
  function loadDex() {
    const container = document.getElementById('dex-comparison');
    if (!container) return;

    container.innerHTML = DEX_DATA.map((d) => `
      <div class="dex-card">
        <div class="dex-card__name">${d.name}</div>
        <div class="dex-card__volume">${d.volume}</div>
        <div class="dex-card__change dex-card__change--${d.changeDir}">${d.change}</div>
        <div class="dex-card__detail">${d.pairs} pairs · ${d.detail}</div>
      </div>
    `).join('');
  }

  /* ---------- Network Health ---------- */
  function loadHealth() {
    const container = document.getElementById('health-grid');
    if (!container) return;

    container.innerHTML = NETWORK_HEALTH.map((h) => `
      <div class="health-card">
        <div class="health-card__label">${h.label}</div>
        <div class="health-card__value">${h.value}</div>
        <div class="health-card__status health-card__status--${h.status}">${h.statusText}</div>
      </div>
    `).join('');
  }

  /* ============================================================
     INIT
     ============================================================ */
  function init() {
    initThemeToggle();
    loadHeroMetrics();
    loadDapps();
    loadNfts();
    loadDex();
    loadHealth();
    loadSolPrice();
    loadTokensChart();

    animateHeroEntrance();
    requestAnimationFrame(() => {
      animateCardEntrance();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
