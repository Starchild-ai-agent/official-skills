/* ============================================================
   NFT Market Trends — script.js

   APIs: Simulated NFT market data + CoinGecko (ETH price)
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
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    ethPrice: () => 'https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd&include_24hr_change=true',
  };

  /* ---------- Simulated Market Data ---------- */
  let seed = 77;
  function seededRandom() {
    seed = (seed * 16807 + 0) % 2147483647;
    return (seed - 1) / 2147483646;
  }

  const CATEGORIES = ['PFP', 'Art', 'Gaming', 'Music', 'Photography', 'Utility', 'Metaverse'];

  const COLLECTIONS = [
    { name: 'CryptoApes Elite', category: 'PFP', floor: 12.5, volume24h: 890, change24h: 15.3, owners: 5200, items: 10000 },
    { name: 'Pixel Dreamers', category: 'Art', floor: 3.2, volume24h: 340, change24h: -8.2, owners: 3100, items: 5000 },
    { name: 'MetaRealm Lands', category: 'Metaverse', floor: 1.8, volume24h: 520, change24h: 22.1, owners: 8400, items: 20000 },
    { name: 'SoundWave Genesis', category: 'Music', floor: 0.45, volume24h: 78, change24h: -3.5, owners: 1200, items: 3000 },
    { name: 'BattleCards Alpha', category: 'Gaming', floor: 0.12, volume24h: 156, change24h: 45.8, owners: 9800, items: 50000 },
    { name: 'Lens Collective', category: 'Photography', floor: 0.85, volume24h: 92, change24h: 5.2, owners: 780, items: 2000 },
    { name: 'Utility Pass Pro', category: 'Utility', floor: 0.35, volume24h: 210, change24h: -12.4, owners: 4500, items: 8000 },
    { name: 'Abstract Visions', category: 'Art', floor: 5.6, volume24h: 445, change24h: 8.9, owners: 2200, items: 4000 },
    { name: 'Cyber Samurai', category: 'PFP', floor: 2.1, volume24h: 280, change24h: -5.7, owners: 3800, items: 7777 },
    { name: 'Rhythm Drops', category: 'Music', floor: 0.22, volume24h: 45, change24h: 18.3, owners: 650, items: 1500 },
    { name: 'VoxelWorld Plots', category: 'Metaverse', floor: 0.95, volume24h: 310, change24h: 3.1, owners: 6200, items: 15000 },
    { name: 'Dungeon Loot', category: 'Gaming', floor: 0.08, volume24h: 120, change24h: -2.8, owners: 12000, items: 80000 },
  ];

  function generateTrendData() {
    const days = 30;
    const data = {};
    CATEGORIES.forEach(cat => {
      data[cat] = [];
      let base = 100 + seededRandom() * 500;
      for (let i = 0; i < days; i++) {
        base += (seededRandom() - 0.45) * 30;
        base = Math.max(20, base);
        data[cat].push(Math.round(base * 10) / 10);
      }
    });
    return data;
  }

  function generateActivityFeed() {
    const types = ['sale', 'list', 'bid'];
    const feed = [];
    for (let i = 0; i < 15; i++) {
      const col = COLLECTIONS[Math.floor(seededRandom() * COLLECTIONS.length)];
      const type = types[Math.floor(seededRandom() * types.length)];
      const price = (seededRandom() * col.floor * 2 + 0.01).toFixed(3);
      const mins = Math.floor(seededRandom() * 120);
      feed.push({
        type,
        collection: col.name,
        price: parseFloat(price),
        timeAgo: mins < 60 ? `${mins}m ago` : `${Math.floor(mins / 60)}h ago`,
      });
    }
    return feed;
  }

  /* ---------- State ---------- */
  let trendsChart = null;
  let volumeChart = null;
  let ethChart = null;
  const trendData = generateTrendData();
  const activityFeed = generateActivityFeed();

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.stats-bar__brand > *, .stats-bar__kpis', { opacity: 1 });
      return;
    }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.stats-bar__label', { opacity: 0, filter: 'blur(8px)', duration: 0.5 })
      .from('.stats-bar__title', { opacity: 0, filter: 'blur(8px)', duration: 0.6 }, '-=0.3')
      .from('.stats-bar__subtitle', { opacity: 0, filter: 'blur(8px)', duration: 0.4 }, '-=0.3')
      .from('.stats-bar__kpi', { opacity: 0, filter: 'blur(8px)', duration: 0.5, stagger: 0.08 }, '-=0.2');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('[data-animate]', { opacity: 1, filter: 'blur(0px)' });
      return;
    }
    gsap.utils.toArray('[data-animate]').forEach((el, i) => {
      gsap.to(el, {
        scrollTrigger: {
          trigger: el,
          start: 'top 88%',
          toggleActions: 'play none none none',
        },
        opacity: 1,
        filter: 'blur(0px)',
        duration: 0.6,
        delay: i * 0.06,
        ease: 'power3.out',
      });
    });
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */

  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    const stored = localStorage.getItem('nft-trends-theme');
    if (stored === 'dark') document.documentElement.setAttribute('data-theme', 'dark');

    btn.addEventListener('click', () => {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('nft-trends-theme', 'light');
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('nft-trends-theme', 'dark');
      }
      renderAllCharts();
    });
  }

  /* ============================================================
     KPI & HERO
     ============================================================ */

  function renderHeroTime() {
    const el = document.getElementById('hero-time');
    const now = new Date();
    el.textContent = now.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
    el.setAttribute('datetime', now.toISOString());
  }

  function renderKPIs() {
    const totalVolume = COLLECTIONS.reduce((s, c) => s + c.volume24h, 0);
    const totalBuyers = COLLECTIONS.reduce((s, c) => s + Math.floor(c.owners * 0.05), 0);
    const avgPrice = COLLECTIONS.reduce((s, c) => s + c.floor, 0) / COLLECTIONS.length;

    document.getElementById('kpi-volume').textContent = `${totalVolume.toLocaleString()} ETH`;
    document.getElementById('kpi-buyers').textContent = totalBuyers.toLocaleString();
    document.getElementById('kpi-avg-price').textContent = `${avgPrice.toFixed(2)} ETH`;

    // Sentiment
    const positiveCount = COLLECTIONS.filter(c => c.change24h > 0).length;
    const sentimentScore = Math.round((positiveCount / COLLECTIONS.length) * 100);
    document.getElementById('kpi-sentiment').textContent = sentimentScore > 60 ? 'Bullish' : sentimentScore > 40 ? 'Neutral' : 'Bearish';
  }

  /* ============================================================
     SENTIMENT GAUGE
     ============================================================ */

  function renderSentimentGauge() {
    const positiveCount = COLLECTIONS.filter(c => c.change24h > 0).length;
    const score = Math.round((positiveCount / COLLECTIONS.length) * 100);

    const gaugeFill = document.getElementById('gauge-fill');
    const gaugeValue = document.getElementById('gauge-value');
    const gaugeText = document.getElementById('gauge-text');

    const circumference = 251.33;
    const offset = circumference - (score / 100) * circumference;
    gaugeFill.style.strokeDashoffset = offset;

    gaugeValue.textContent = score;
    gaugeText.textContent = score > 60 ? 'Bullish' : score > 40 ? 'Neutral' : 'Bearish';

    // Sentiment factors
    const factors = document.getElementById('sentiment-factors');
    const factorData = [
      { label: 'Volume Trend', value: '+12.4%', positive: true },
      { label: 'Active Wallets', value: '+8.2%', positive: true },
      { label: 'Avg Hold Time', value: '14.2d', positive: true },
      { label: 'Listing Rate', value: '+3.1%', positive: false },
      { label: 'Wash Trade %', value: '4.8%', positive: true },
    ];

    factors.innerHTML = factorData.map(f => `
      <div class="sentiment-factor">
        <span class="sentiment-factor__label">${f.label}</span>
        <span class="sentiment-factor__value ${f.positive ? 'cell-positive' : 'cell-negative'}">${f.value}</span>
      </div>
    `).join('');
  }

  /* ============================================================
     COLLECTIONS TABLE
     ============================================================ */

  function renderCollectionsTable() {
    const tbody = document.getElementById('collections-body');
    const sorted = [...COLLECTIONS].sort((a, b) => b.volume24h - a.volume24h);

    tbody.innerHTML = sorted.map((c, i) => `
      <tr>
        <td>${i + 1}</td>
        <td><strong>${c.name}</strong></td>
        <td>${c.floor.toFixed(2)}</td>
        <td class="cell-accent">${c.volume24h.toLocaleString()}</td>
        <td class="${c.change24h >= 0 ? 'cell-positive' : 'cell-negative'}">${c.change24h >= 0 ? '+' : ''}${c.change24h.toFixed(1)}%</td>
        <td>${c.owners.toLocaleString()}</td>
        <td>${c.items.toLocaleString()}</td>
      </tr>
    `).join('');
  }

  /* ============================================================
     ACTIVITY FEED
     ============================================================ */

  function renderActivityFeed() {
    const container = document.getElementById('activity-feed');
    const icons = { sale: '💰', list: '📋', bid: '🔨' };
    const iconClasses = { sale: 'activity-item__icon--sale', list: 'activity-item__icon--list', bid: 'activity-item__icon--bid' };

    container.innerHTML = activityFeed.map(item => `
      <div class="activity-item">
        <div class="activity-item__icon ${iconClasses[item.type]}">${icons[item.type]}</div>
        <div class="activity-item__body">
          <div class="activity-item__title">${item.collection}</div>
          <div class="activity-item__meta">${item.type.charAt(0).toUpperCase() + item.type.slice(1)} · ${item.timeAgo}</div>
        </div>
        <div class="activity-item__price">${item.price} ETH</div>
      </div>
    `).join('');
  }

  /* ============================================================
     CHARTS
     ============================================================ */

  function getChartColors() {
    const style = getComputedStyle(document.documentElement);
    return {
      accent: style.getPropertyValue('--chart-1').trim(),
      c2: style.getPropertyValue('--chart-2').trim(),
      c3: style.getPropertyValue('--chart-3').trim(),
      c4: style.getPropertyValue('--chart-4').trim(),
      c5: style.getPropertyValue('--chart-5').trim(),
      c6: style.getPropertyValue('--chart-6').trim(),
      text: style.getPropertyValue('--color-text-secondary').trim(),
      border: style.getPropertyValue('--color-border').trim(),
      bg: style.getPropertyValue('--color-surface').trim(),
    };
  }

  function renderAllCharts() {
    renderTrendsChart();
    renderVolumeChart();
    renderEthChart();
  }

  function renderTrendsChart() {
    const ctx = document.getElementById('trends-chart').getContext('2d');
    const colors = getChartColors();
    const colorArr = [colors.accent, colors.c2, colors.c3, colors.c4, colors.c5, colors.c6, colors.accent + '80'];

    const labels = Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`);

    const datasets = CATEGORIES.map((cat, i) => ({
      label: cat,
      data: trendData[cat],
      borderColor: colorArr[i % colorArr.length],
      backgroundColor: 'transparent',
      tension: 0.3,
      pointRadius: 0,
      pointHoverRadius: 3,
      borderWidth: 2,
    }));

    if (trendsChart) trendsChart.destroy();

    trendsChart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: { color: colors.text, font: { family: "'JetBrains Mono', monospace", size: 10 }, boxWidth: 12 },
          },
          tooltip: {
            backgroundColor: colors.bg,
            titleColor: colors.text,
            bodyColor: colors.text,
            borderColor: colors.border,
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: { color: colors.text, font: { family: "'JetBrains Mono', monospace", size: 9 }, maxTicksLimit: 10 },
            grid: { color: colors.border },
          },
          y: {
            ticks: {
              color: colors.text,
              font: { family: "'JetBrains Mono', monospace", size: 9 },
              callback: (v) => `${v} ETH`,
            },
            grid: { color: colors.border },
          },
        },
      },
    });
  }

  function renderVolumeChart() {
    const ctx = document.getElementById('volume-chart').getContext('2d');
    const colors = getChartColors();
    const colorArr = [colors.accent, colors.c2, colors.c3, colors.c4, colors.c5, colors.c6, colors.accent + '80'];

    const catVolumes = CATEGORIES.map(cat => {
      return COLLECTIONS.filter(c => c.category === cat).reduce((s, c) => s + c.volume24h, 0);
    });

    if (volumeChart) volumeChart.destroy();

    volumeChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: CATEGORIES,
        datasets: [{
          label: '24h Volume (ETH)',
          data: catVolumes,
          backgroundColor: CATEGORIES.map((_, i) => colorArr[i % colorArr.length] + '70'),
          borderColor: CATEGORIES.map((_, i) => colorArr[i % colorArr.length]),
          borderWidth: 1,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: colors.bg,
            titleColor: colors.text,
            bodyColor: colors.text,
            borderColor: colors.border,
            borderWidth: 1,
            callbacks: {
              label: (ctx) => `${ctx.parsed.y.toLocaleString()} ETH`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: colors.text, font: { family: "'JetBrains Mono', monospace", size: 10 } },
            grid: { display: false },
          },
          y: {
            ticks: {
              color: colors.text,
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              callback: (v) => `${v} ETH`,
            },
            grid: { color: colors.border },
          },
        },
      },
    });
  }

  function renderEthChart() {
    const ctx = document.getElementById('eth-chart').getContext('2d');
    const colors = getChartColors();

    // Simulated 7-day ETH price
    const ethPrices = [];
    let price = 3400;
    for (let i = 0; i < 7; i++) {
      price += (seededRandom() - 0.48) * 100;
      ethPrices.push(Math.round(price));
    }
    const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    if (ethChart) ethChart.destroy();

    ethChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'ETH/USD',
          data: ethPrices,
          borderColor: colors.accent,
          backgroundColor: colors.accent + '15',
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointBackgroundColor: colors.accent,
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: colors.bg,
            titleColor: colors.text,
            bodyColor: colors.text,
            borderColor: colors.border,
            borderWidth: 1,
            callbacks: {
              label: (ctx) => `$${ctx.parsed.y.toLocaleString()}`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: colors.text, font: { family: "'JetBrains Mono', monospace", size: 10 } },
            grid: { display: false },
          },
          y: {
            ticks: {
              color: colors.text,
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              callback: (v) => `$${v}`,
            },
            grid: { color: colors.border },
          },
        },
      },
    });
  }

  /* ============================================================
     FETCH ETH PRICE
     ============================================================ */

  async function fetchEthPrice() {
    try {
      const res = await fetch(API.ethPrice());
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.ethereum?.usd) {
        document.getElementById('kpi-eth-price').textContent = `$${data.ethereum.usd.toLocaleString()}`;
      }
    } catch (err) {
      document.getElementById('kpi-eth-price').textContent = '$3,450';
    }
  }

  /* ============================================================
     BOOTSTRAP
     ============================================================ */

  function init() {
    initThemeToggle();
    renderHeroTime();
    renderKPIs();
    renderSentimentGauge();
    renderCollectionsTable();
    renderActivityFeed();
    renderAllCharts();
    animateHeroEntrance();
    animateCardEntrance();
    fetchEthPrice();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
