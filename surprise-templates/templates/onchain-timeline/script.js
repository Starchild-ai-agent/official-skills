/* ============================================================
   On-Chain Activity Timeline — script.js
   Layout: A14 Vertical Timeline (center axis + alternating)
   Entrance: D12 alternating odd:translateX(-30px) even:translateX(30px)
   API: CoinGecko (ETH price)
   Charts: Chart.js (doughnut), Canvas (heatmap)
   Animation: GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const CONFIG = { maxRetries: 2, retryBaseDelay: 1500 };
  const API = { ethPrice: 'https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd' };

  let ethPriceUsd = 3450;

  const ACTIVITY_TYPES = [
    { type: 'transfer', label: 'Token Transfer', icon: '↗️', cssClass: 'transfer' },
    { type: 'contract', label: 'Contract Call', icon: '📜', cssClass: 'contract' },
    { type: 'defi', label: 'DeFi Interaction', icon: '🔄', cssClass: 'defi' },
    { type: 'nft', label: 'NFT Activity', icon: '🖼️', cssClass: 'nft' },
  ];

  const DEFI_PROTOCOLS = ['Uniswap V3', 'Aave V3', 'Lido', 'Curve', 'Compound', 'MakerDAO'];
  const NFT_ACTIONS = ['Minted', 'Purchased', 'Listed', 'Transferred'];
  const TOKENS = ['ETH', 'USDC', 'USDT', 'WBTC', 'DAI', 'LINK', 'UNI', 'AAVE'];

  function generateTimeline(count = 20) {
    const events = [];
    const now = Date.now();
    const walletAge = 365 + Math.floor(Math.random() * 730);
    const startDate = now - walletAge * 86400_000;

    for (let i = 0; i < count; i++) {
      const actType = ACTIVITY_TYPES[Math.floor(Math.random() * ACTIVITY_TYPES.length)];
      const timestamp = startDate + Math.random() * (now - startDate);
      let title, detail, value;

      switch (actType.type) {
        case 'transfer': {
          const token = TOKENS[Math.floor(Math.random() * TOKENS.length)];
          const amount = token === 'ETH' ? (0.1 + Math.random() * 10).toFixed(4) : Math.floor(100 + Math.random() * 50000);
          const direction = Math.random() > 0.5 ? 'Sent' : 'Received';
          title = `${direction} ${amount} ${token}`;
          detail = `${direction === 'Sent' ? 'To' : 'From'} 0x${Math.random().toString(16).slice(2, 10)}...`;
          value = token === 'ETH' ? `$${(parseFloat(amount) * ethPriceUsd).toFixed(0)}` : `$${amount}`;
          break;
        }
        case 'contract': {
          const protocol = DEFI_PROTOCOLS[Math.floor(Math.random() * DEFI_PROTOCOLS.length)];
          const methods = ['approve', 'execute', 'multicall', 'swap', 'deposit'];
          const method = methods[Math.floor(Math.random() * methods.length)];
          title = `${protocol} — ${method}()`;
          detail = `Contract: 0x${Math.random().toString(16).slice(2, 10)}...`;
          value = `Gas: ${(0.002 + Math.random() * 0.02).toFixed(4)} ETH`;
          break;
        }
        case 'defi': {
          const protocol = DEFI_PROTOCOLS[Math.floor(Math.random() * DEFI_PROTOCOLS.length)];
          const actions = ['Swapped', 'Supplied', 'Borrowed', 'Staked', 'Withdrew'];
          const action = actions[Math.floor(Math.random() * actions.length)];
          const amount = (0.5 + Math.random() * 20).toFixed(2);
          title = `${action} on ${protocol}`;
          detail = `${amount} ETH equivalent`;
          value = `$${(parseFloat(amount) * ethPriceUsd).toFixed(0)}`;
          break;
        }
        case 'nft': {
          const action = NFT_ACTIONS[Math.floor(Math.random() * NFT_ACTIONS.length)];
          const collections = ['CryptoPunks', 'BAYC', 'Azuki', 'Doodles', 'Pudgy Penguins'];
          const col = collections[Math.floor(Math.random() * collections.length)];
          const tokenId = Math.floor(Math.random() * 10000);
          title = `${action} ${col} #${tokenId}`;
          detail = action === 'Minted' ? 'Mint price' : 'Floor price';
          value = `${(0.5 + Math.random() * 30).toFixed(2)} ETH`;
          break;
        }
      }
      events.push({ ...actType, title, detail, value, timestamp });
    }
    return events.sort((a, b) => b.timestamp - a.timestamp);
  }

  function generateActivityDistribution(events) {
    const counts = {};
    ACTIVITY_TYPES.forEach((t) => { counts[t.type] = 0; });
    events.forEach((e) => { counts[e.type]++; });
    return ACTIVITY_TYPES.map((t) => ({ ...t, count: counts[t.type] }));
  }

  function generateHeatmapData() {
    const data = [];
    const now = new Date();
    const startDate = new Date(now);
    startDate.setDate(startDate.getDate() - 364);
    startDate.setDate(startDate.getDate() - startDate.getDay());
    for (let w = 0; w < 52; w++) {
      for (let d = 0; d < 7; d++) {
        const date = new Date(startDate);
        date.setDate(date.getDate() + w * 7 + d);
        if (date > now) continue;
        const val = Math.random() < 0.3 ? 0 : Math.floor(Math.random() * 8);
        data.push({ week: w, day: d, value: val, date: date.toISOString().slice(0, 10) });
      }
    }
    return data;
  }

  function generateMilestones() {
    const now = Date.now();
    const walletAge = 365 + Math.floor(Math.random() * 730);
    const startDate = now - walletAge * 86400_000;
    return [
      { icon: '🎉', title: 'First Transaction', desc: 'Your very first on-chain transaction', date: new Date(startDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) },
      { icon: '💰', title: 'Largest Transaction', desc: `Transferred ${(5 + Math.random() * 50).toFixed(2)} ETH in a single transaction`, date: new Date(startDate + Math.random() * (now - startDate)).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) },
      { icon: '🔄', title: 'First DeFi Interaction', desc: `First swap on ${DEFI_PROTOCOLS[Math.floor(Math.random() * DEFI_PROTOCOLS.length)]}`, date: new Date(startDate + Math.random() * (now - startDate) * 0.5).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) },
      { icon: '🖼️', title: 'First NFT Mint', desc: 'Minted your first NFT on-chain', date: new Date(startDate + Math.random() * (now - startDate) * 0.7).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) },
      { icon: '🏆', title: '100th Transaction', desc: 'Reached 100 total on-chain transactions', date: new Date(startDate + Math.random() * (now - startDate) * 0.6).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) },
      { icon: '📅', title: '1 Year On-Chain', desc: 'Your wallet has been active for over a year', date: new Date(startDate + 365 * 86400_000).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) },
    ];
  }

  /* ---- Utilities ---- */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let i = 0; i <= retries; i++) {
      try { const res = await fetch(url); if (!res.ok) throw new Error(`HTTP ${res.status}`); return await res.json(); }
      catch (err) { if (i === retries) throw err; await new Promise((r) => setTimeout(r, CONFIG.retryBaseDelay * (i + 1))); }
    }
  }

  function formatDate(ts) {
    return new Date(ts).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  /* ---- Theme ---- */
  (function initTheme() {
    const saved = localStorage.getItem('onchain-timeline-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    if (theme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    document.getElementById('theme-toggle').addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      if (next === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
      else document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('onchain-timeline-theme', next);
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
  let distributionChart = null;

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
    };
  }

  function renderDistributionChart(distData) {
    const ctx = document.getElementById('distribution-chart');
    if (!ctx) return;
    const c = getChartColors();
    const colors = [c.c2, c.c3, c.c4, c.c5];
    if (distributionChart) distributionChart.destroy();
    distributionChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: distData.map((d) => d.label),
        datasets: [{ data: distData.map((d) => d.count), backgroundColor: colors, borderWidth: 0, hoverOffset: 8 }],
      },
      options: {
        maintainAspectRatio: false, responsive: true, cutout: '65%',
        plugins: { legend: { display: false }, tooltip: { backgroundColor: c.surface, titleColor: c.text, bodyColor: c.text, borderColor: c.c1, borderWidth: 1 } },
      },
    });
  }

  /* ---- Heatmap ---- */
  function renderHeatmap(data) {
    const canvas = document.getElementById('heatmap-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.scale(dpr, dpr);

    const w = rect.width, h = rect.height;
    const marginLeft = 30, marginTop = 20, marginBottom = 20;
    const cellSize = Math.min((w - marginLeft - 10) / 52, (h - marginTop - marginBottom) / 7) - 2;
    const gap = 2;
    const maxVal = Math.max(...data.map((d) => d.value), 1);
    const days = ['', 'Mon', '', 'Wed', '', 'Fri', ''];

    ctx.clearRect(0, 0, w, h);
    const labelColor = getComputedStyle(document.documentElement).getPropertyValue('--color-text-muted').trim();
    ctx.fillStyle = labelColor;
    ctx.font = `10px 'IBM Plex Mono',monospace`;
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    days.forEach((day, i) => { if (day) ctx.fillText(day, marginLeft - 6, marginTop + i * (cellSize + gap) + cellSize / 2); });

    const accentRaw = getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim();
    data.forEach((d) => {
      const x = marginLeft + d.week * (cellSize + gap);
      const y = marginTop + d.day * (cellSize + gap);
      if (d.value === 0) {
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim();
        ctx.globalAlpha = 0.4;
      } else {
        ctx.fillStyle = accentRaw;
        ctx.globalAlpha = 0.2 + (d.value / maxVal) * 0.8;
      }
      ctx.beginPath(); ctx.roundRect(x, y, cellSize, cellSize, 2); ctx.fill();
      ctx.globalAlpha = 1;
    });

    ctx.fillStyle = labelColor; ctx.textAlign = 'left'; ctx.textBaseline = 'top';
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let lastMonth = -1;
    data.filter((d) => d.day === 0).forEach((d) => {
      const date = new Date(d.date);
      const month = date.getMonth();
      if (month !== lastMonth) { lastMonth = month; ctx.fillText(months[month], marginLeft + d.week * (cellSize + gap), marginTop + 7 * (cellSize + gap) + 4); }
    });
  }

  /* ---- Timeline (Vertical, alternating) ---- */
  function renderTimeline(events) {
    const container = document.getElementById('timeline');
    if (!container) return;
    const axisHtml = '<div class="vertical-timeline__axis" aria-hidden="true"></div>';
    const cardsHtml = events.slice(0, 15).map((ev) => `<div class="event-card">
      <span class="event-card__type event-card__type--${ev.cssClass}">${ev.icon} ${ev.label}</span>
      <div class="event-card__event-title">${ev.title}</div>
      <div class="event-card__detail">${ev.detail}</div>
      <div class="event-card__value">${ev.value}</div>
      <div class="event-card__time">${formatDate(ev.timestamp)}</div>
    </div>`).join('');
    container.innerHTML = axisHtml + cardsHtml;
  }

  /* ---- Stats ---- */
  function renderStats(events, distData) {
    const sidebar = document.getElementById('stats-sidebar');
    if (!sidebar) return;
    const totalGas = events.length * (0.002 + Math.random() * 0.01);
    sidebar.innerHTML = distData.map((d) => `<div class="stat-card">
      <div class="stat-card__label">${d.icon} ${d.label}</div>
      <div class="stat-card__value">${d.count}</div>
      <div class="stat-card__sub">${((d.count / events.length) * 100).toFixed(1)}% of all</div>
    </div>`).join('') + `<div class="stat-card">
      <div class="stat-card__label">⛽ Gas Spent</div>
      <div class="stat-card__value">${totalGas.toFixed(3)} ETH</div>
      <div class="stat-card__sub">≈ $${(totalGas * ethPriceUsd).toFixed(0)}</div>
    </div>`;
  }

  /* ---- Milestones ---- */
  function renderMilestones(milestones) {
    const grid = document.getElementById('milestones-grid');
    if (!grid) return;
    grid.innerHTML = milestones.map((m) => `<div class="milestone-card">
      <div class="milestone-card__icon">${m.icon}</div>
      <div class="milestone-card__title">${m.title}</div>
      <div class="milestone-card__desc">${m.desc}</div>
      <div class="milestone-card__date">${m.date}</div>
    </div>`).join('');
  }

  /* ---- Hero ---- */
  function updateHero(events) {
    const walletAge = document.getElementById('hero-wallet-age');
    const totalTxns = document.getElementById('hero-total-txns');
    const activeDays = document.getElementById('hero-active-days');
    if (walletAge) walletAge.textContent = (1 + Math.random() * 2).toFixed(1) + ' yrs';
    if (totalTxns) totalTxns.textContent = (events.length * 15 + Math.floor(Math.random() * 200)).toLocaleString();
    if (activeDays) activeDays.textContent = Math.floor(100 + Math.random() * 500);
  }

  /* ---- GSAP ---- */
  function initAnimations() {
    if (prefersReducedMotion) {
      gsap.set('.event-card, .event-card--chart', { opacity: 1, x: 0 });
      return;
    }

    gsap.from('.minimal-hero__text', { opacity: 0, y: 16, duration: 0.5, ease: 'power3.out' });
    gsap.from('.minimal-hero__stat', { opacity: 0, y: 12, stagger: 0.08, duration: 0.4, delay: 0.2, ease: 'power3.out' });

    /* D12: alternating directions */
    gsap.utils.toArray('.vertical-timeline .event-card').forEach((card, i) => {
      gsap.to(card, {
        opacity: 1, x: 0, duration: 0.6,
        delay: i * 0.08,
        ease: 'power3.out',
        scrollTrigger: { trigger: card, start: 'top 88%', once: true }
      });
    });

    /* Chart panels */
    gsap.utils.toArray('.event-card--chart').forEach((card, i) => {
      gsap.to(card, {
        opacity: 1, x: 0, duration: 0.7,
        delay: i * 0.1,
        ease: 'power3.out',
        scrollTrigger: { trigger: card, start: 'top 88%', once: true }
      });
    });

    gsap.from('.milestone-card', {
      scrollTrigger: { trigger: '.milestones-grid', start: 'top 80%', once: true },
      y: 30, opacity: 0, duration: 0.5, stagger: 0.1, ease: 'power3.out',
    });
  }

  /* ---- Main ---- */
  async function init() {
    try {
      const priceData = await fetchWithRetry(API.ethPrice);
      if (priceData?.ethereum?.usd) ethPriceUsd = priceData.ethereum.usd;
    } catch (e) { /* default */ }

    const events = generateTimeline(20);
    const distData = generateActivityDistribution(events);
    const heatmapData = generateHeatmapData();
    const milestones = generateMilestones();

    updateHero(events);
    renderTimeline(events);
    renderDistributionChart(distData);
    renderStats(events, distData);
    renderHeatmap(heatmapData);
    renderMilestones(milestones);
    initAnimations();
  }

  init();

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => renderHeatmap(generateHeatmapData()), 250);
  });
})();
