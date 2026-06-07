/* ============================================================
   NFT Collection Gallery — script.js
   Layout: A12 Masonry/Gallery Grid
   Entrance: D14 fade + scale(0.9)
   API: CoinGecko (ETH price)
   Charts: Chart.js (doughnut, line)
   Animation: GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const CONFIG = {
    maxRetries: 2, retryBaseDelay: 1500, refreshInterval: 120_000,
  };

  const API = {
    ethPrice: 'https://pro-api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd',
  };

  let ethPriceUsd = 3450;

  const NFT_COLLECTIONS = [
    { id: 'bayc', name: 'Bored Ape Yacht Club', symbol: 'BAYC', floorEth: 28.5, emoji: '🐵' },
    { id: 'azuki', name: 'Azuki', symbol: 'AZUKI', floorEth: 9.2, emoji: '⛩️' },
    { id: 'pudgy', name: 'Pudgy Penguins', symbol: 'PUDGY', floorEth: 12.8, emoji: '🐧' },
    { id: 'doodles', name: 'Doodles', symbol: 'DOODLE', floorEth: 3.1, emoji: '🎨' },
    { id: 'moonbirds', name: 'Moonbirds', symbol: 'MOON', floorEth: 1.8, emoji: '🦉' },
    { id: 'clonex', name: 'CloneX', symbol: 'CLONEX', floorEth: 2.4, emoji: '🤖' },
  ];

  const RARITY_TIERS = ['Legendary', 'Epic', 'Rare', 'Uncommon', 'Common'];
  const TRAIT_TYPES = ['Background', 'Skin', 'Eyes', 'Mouth', 'Clothing', 'Headwear', 'Accessory'];

  function generateNFTItems() {
    const items = [];
    NFT_COLLECTIONS.forEach((col) => {
      const count = 2 + Math.floor(Math.random() * 4);
      for (let i = 0; i < count; i++) {
        const tokenId = Math.floor(Math.random() * 10000);
        const rarityIdx = Math.floor(Math.random() * 5);
        const rarityMultiplier = [5, 3, 2, 1.3, 1][rarityIdx];
        const estimatedEth = col.floorEth * rarityMultiplier * (0.9 + Math.random() * 0.3);
        items.push({
          collection: col,
          tokenId,
          rarity: RARITY_TIERS[rarityIdx],
          rarityScore: Math.round(100 - rarityIdx * 20 + Math.random() * 15),
          estimatedEth: Math.round(estimatedEth * 100) / 100,
          traits: TRAIT_TYPES.slice(0, 4 + Math.floor(Math.random() * 3)).map((t) => ({
            type: t,
            value: `Trait #${Math.floor(Math.random() * 50)}`,
            rarity: Math.round(Math.random() * 100) / 10,
          })),
        });
      }
    });
    return items.sort((a, b) => b.estimatedEth - a.estimatedEth);
  }

  function generateFloorHistory() {
    const days = 30;
    const labels = [];
    const datasets = {};
    const now = Date.now();
    NFT_COLLECTIONS.slice(0, 4).forEach((col) => {
      datasets[col.symbol] = [];
    });
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(now - i * 86400_000);
      labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
      Object.keys(datasets).forEach((sym) => {
        const col = NFT_COLLECTIONS.find((c) => c.symbol === sym);
        const base = col ? col.floorEth : 5;
        const drift = (Math.random() - 0.48) * base * 0.08;
        const prev = datasets[sym].length ? datasets[sym][datasets[sym].length - 1] : base;
        datasets[sym].push(Math.round((prev + drift) * 100) / 100);
      });
    }
    return { labels, datasets };
  }

  /* ---- Utilities ---- */
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

  function fmtEth(n) { return n.toFixed(2) + ' ETH'; }
  function fmtUsd(n) {
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'K';
    return '$' + n.toFixed(0);
  }

  /* ---- Theme ---- */
  (function initTheme() {
    const saved = localStorage.getItem('nft-gallery-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    if (theme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    document.getElementById('theme-toggle').addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      if (next === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
      else document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('nft-gallery-theme', next);
    });
  })();

  /* ---- Hero background image ---- */
  (function initHeroImage() {
    const raw = '{{HERO_IMAGE_URL}}';
    if (!raw.startsWith('{{') && raw.trim()) {
      const el = document.getElementById('hero-bg');
      if (el) { el.style.backgroundImage = `url("${raw}")`; el.style.background = ''; }
    }
  })();

  /* ---- Charts ---- */
  let distributionChart = null;
  let priceChart = null;

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

  function renderDistributionChart(items) {
    const ctx = document.getElementById('distribution-chart');
    if (!ctx) return;
    const c = getChartColors();
    const colors = [c.c1, c.c2, c.c3, c.c4, c.c5, c.c6];

    const collectionMap = {};
    items.forEach((item) => {
      const key = item.collection.symbol;
      if (!collectionMap[key]) collectionMap[key] = { count: 0, totalEth: 0, name: item.collection.name };
      collectionMap[key].count++;
      collectionMap[key].totalEth += item.estimatedEth;
    });
    const labels = Object.keys(collectionMap);
    const data = labels.map((k) => Math.round(collectionMap[k].totalEth * 100) / 100);

    if (distributionChart) distributionChart.destroy();
    distributionChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels.map((k) => collectionMap[k].name),
        datasets: [{ data, backgroundColor: colors.slice(0, labels.length), borderWidth: 0, hoverOffset: 8 }],
      },
      options: {
        maintainAspectRatio: false,
        responsive: true,
        cutout: '65%',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: c.surface,
            titleColor: c.text,
            bodyColor: c.text,
            borderColor: c.c1,
            borderWidth: 1,
            callbacks: { label: (ctx2) => ` ${ctx2.parsed} ETH (${fmtUsd(ctx2.parsed * ethPriceUsd)})` },
          },
        },
      },
    });

    const legendEl = document.getElementById('distribution-legend');
    if (legendEl) {
      legendEl.innerHTML = labels.map((k, i) => `<div class="legend-item">
        <span class="legend-item__dot" style="background:${colors[i]}"></span>
        <span class="legend-item__label">${collectionMap[k].name}</span>
        <span class="legend-item__value">${collectionMap[k].count} NFTs</span>
      </div>`).join('');
    }
  }

  function renderPriceChart(history) {
    const ctx = document.getElementById('price-chart');
    if (!ctx) return;
    const c = getChartColors();
    const colors = [c.c1, c.c2, c.c3, c.c4];
    const datasets = Object.keys(history.datasets).map((sym, i) => ({
      label: sym,
      data: history.datasets[sym],
      borderColor: colors[i],
      backgroundColor: colors[i] + '18',
      fill: true,
      tension: 0.35,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
    }));

    if (priceChart) priceChart.destroy();
    priceChart = new Chart(ctx, {
      type: 'line',
      data: { labels: history.labels, datasets },
      options: {
        maintainAspectRatio: false,
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { labels: { color: c.text, font: { family: "'Figtree',sans-serif", size: 11 } } },
          tooltip: { backgroundColor: c.surface, titleColor: c.text, bodyColor: c.text, borderColor: c.c1, borderWidth: 1 },
        },
        scales: {
          x: { grid: { color: c.border + '40' }, ticks: { color: c.muted, font: { family: "'Space Mono',monospace", size: 10 }, maxTicksLimit: 8 } },
          y: { grid: { color: c.border + '40' }, ticks: { color: c.muted, font: { family: "'Space Mono',monospace", size: 10 }, callback: (v) => v + ' Ξ' } },
        },
      },
    });
  }

  /* ---- Gallery (Masonry) ---- */
  function renderGallery(items) {
    const grid = document.getElementById('gallery-grid');
    if (!grid) return;
    grid.innerHTML = items.slice(0, 12).map((item) => {
      const rarityClass = item.rarity.toLowerCase();
      return `<div class="gallery-item" style="position:relative">
        <div class="gallery-item__image">${item.collection.emoji}</div>
        <span class="gallery-item__rarity gallery-item__rarity--${rarityClass}">${item.rarity}</span>
        <div class="gallery-item__body">
          <div class="gallery-item__collection">${item.collection.symbol}</div>
          <div class="gallery-item__name">${item.collection.name} #${item.tokenId}</div>
          <div class="gallery-item__price">${fmtEth(item.estimatedEth)} · ${fmtUsd(item.estimatedEth * ethPriceUsd)}</div>
        </div>
      </div>`;
    }).join('');
  }

  /* ---- Rarity cards ---- */
  function renderRarityCards(items) {
    const container = document.getElementById('rarity-cards');
    if (!container) return;
    const top3 = items.filter((i) => i.rarity === 'Legendary' || i.rarity === 'Epic').slice(0, 3);
    if (!top3.length) {
      container.innerHTML = '<p style="color:var(--color-text-muted)">No rare items found in collection</p>';
      return;
    }
    container.innerHTML = top3.map((item) => `<div class="rarity-card">
      <div class="rarity-card__header">
        <div class="rarity-card__icon">${item.collection.emoji}</div>
        <div>
          <div class="rarity-card__title">${item.collection.name} #${item.tokenId}</div>
          <div class="rarity-card__subtitle">${item.rarity} · ${fmtEth(item.estimatedEth)}</div>
        </div>
      </div>
      <div class="rarity-card__traits">
        ${item.traits.map((t) => `<div class="trait-row">
          <span class="trait-row__name">${t.type}</span>
          <div class="trait-row__bar"><div class="trait-row__bar-fill" style="width:${Math.min(t.rarity * 10, 100)}%"></div></div>
          <span class="trait-row__value">${t.rarity}%</span>
        </div>`).join('')}
      </div>
      <div class="rarity-card__score">
        <span class="rarity-card__score-label">Rarity Score</span>
        <span class="rarity-card__score-value">${item.rarityScore}</span>
      </div>
    </div>`).join('');
  }

  /* ---- Hero metrics ---- */
  function updateHero(items) {
    const totalValue = document.getElementById('hero-total-value');
    const nftCount = document.getElementById('hero-nft-count');
    const mostValuable = document.getElementById('hero-most-valuable');

    const totalEth = items.reduce((s, i) => s + i.estimatedEth, 0);
    if (totalValue) totalValue.textContent = fmtUsd(totalEth * ethPriceUsd);
    if (nftCount) nftCount.textContent = items.length;
    if (mostValuable && items.length) {
      mostValuable.textContent = fmtEth(items[0].estimatedEth);
    }
  }

  /* ---- Remove chart skeletons ---- */
  function removeChartSkeletons() {
    ['distribution-chart-skeleton', 'price-chart-skeleton'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.remove();
    });
  }

  /* ---- GSAP Animations ---- */
  function initAnimations() {
    if (prefersReducedMotion) {
      gsap.set('.gallery-item, .rarity-card, .gallery-item--chart', { opacity: 1, scale: 1 });
      return;
    }

    /* Hero */
    gsap.from('.fullwidth-hero__badge', { y: 20, opacity: 0, duration: 0.6, ease: 'power3.out' });
    gsap.from('.fullwidth-hero__title', { y: 40, opacity: 0, duration: 1, delay: 0.1, ease: 'power3.out' });
    gsap.from('.fullwidth-hero__subtitle', { y: 30, opacity: 0, duration: 0.8, delay: 0.25, ease: 'power3.out' });
    gsap.from('.fullwidth-hero__kpi', { y: 20, opacity: 0, duration: 0.6, stagger: 0.1, delay: 0.4, ease: 'power3.out' });

    /* D14: gallery items fade + scale(0.9) */
    gsap.utils.toArray('.gallery-item:not(.gallery-item--chart)').forEach((item, i) => {
      gsap.to(item, {
        opacity: 1, scale: 1, duration: 0.6,
        delay: i * 0.06,
        ease: 'power3.out',
        scrollTrigger: { trigger: item, start: 'top 90%', once: true }
      });
    });

    /* Chart panels — use gsap.from since they default to visible */
    gsap.utils.toArray('.gallery-item--chart').forEach((item, i) => {
      gsap.from(item, {
        opacity: 0, scale: 0.95, duration: 0.7,
        delay: i * 0.1,
        ease: 'power3.out',
        scrollTrigger: { trigger: item, start: 'top 88%', once: true }
      });
    });

    /* Rarity cards */
    gsap.utils.toArray('.rarity-card').forEach((card, i) => {
      gsap.to(card, {
        opacity: 1, scale: 1, duration: 0.6,
        delay: i * 0.08,
        ease: 'power3.out',
        scrollTrigger: { trigger: card, start: 'top 88%', once: true }
      });
    });
  }

  /* ---- Main ---- */
  async function init() {
    try {
      const priceData = await fetchWithRetry(API.ethPrice);
      if (priceData?.ethereum?.usd) ethPriceUsd = priceData.ethereum.usd;
    } catch (e) { /* Use default */ }

    const items = generateNFTItems();
    const floorHistory = generateFloorHistory();

    updateHero(items);
    renderGallery(items);
    renderDistributionChart(items);
    renderPriceChart(floorHistory);
    renderRarityCards(items);
    removeChartSkeletons();
    initAnimations();
  }

  init();
})();
