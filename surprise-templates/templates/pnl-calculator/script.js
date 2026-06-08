/* ============================================================
   P&L Calculator — script.js
   D13 · Centered Single Column · Opacity-only entry · GSAP 3
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const html = document.documentElement;
  const themeBtn = document.getElementById('themeToggle');
  const stored = localStorage.getItem('pnl-theme');
  if (stored) html.setAttribute('data-theme', stored);

  themeBtn.addEventListener('click', () => {
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('pnl-theme', next);
    if (chartInstance) renderChart();
  });

  /* ---------- Trade Storage ---------- */
  const STORAGE_KEY = 'pnl-trades';

  function loadTrades() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch { return []; }
  }

  function saveTrades(trades) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trades));
  }

  let trades = loadTrades();

  /* ---------- GSAP Entry Animations ---------- */
  function initAnimations() {
    if (typeof gsap === 'undefined') return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    gsap.registerPlugin(ScrollTrigger);

    // Opacity-only fade in (D5)
    gsap.from('.hero__heading', { opacity: 0, duration: 0.8, ease: 'power2.out' });
    gsap.from('.hero__sub', { opacity: 0, duration: 0.8, delay: 0.15, ease: 'power2.out' });
    gsap.from('.trade-form', { opacity: 0, duration: 0.8, delay: 0.3, ease: 'power2.out' });

    gsap.utils.toArray('.summary-card').forEach((el, i) => {
      gsap.from(el, {
        opacity: 0,
        duration: 0.6,
        delay: 0.4 + i * 0.1,
        ease: 'power2.out',
        scrollTrigger: { trigger: el, start: 'top 90%' }
      });
    });
  }

  function animateNewRow(el) {
    if (typeof gsap === 'undefined') return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;
    gsap.from(el, { opacity: 0, duration: 0.5, ease: 'power2.out' });
  }

  /* ---------- CoinGecko API ---------- */
  const API_BASE = 'https://api.coingecko.com/api/v3';
  const priceCache = {};

  async function fetchCurrentPrice(coinId) {
    if (priceCache[coinId] && Date.now() - priceCache[coinId].ts < 60000) {
      return priceCache[coinId].price;
    }
    try {
      const res = await fetch(`${API_BASE}/simple/price?ids=${coinId}&vs_currencies=usd`);
      const data = await res.json();
      const price = data[coinId]?.usd || 0;
      priceCache[coinId] = { price, ts: Date.now() };
      return price;
    } catch {
      return 0;
    }
  }

  /* ---------- P&L Calculation ---------- */
  function calcTradePnl(trade) {
    const buyTotal = trade.buyPrice * trade.quantity;
    const sellTotal = trade.sellPrice * trade.quantity;
    const buyFee = buyTotal * (trade.feeRate / 100);
    const sellFee = sellTotal * (trade.feeRate / 100);
    const pnl = sellTotal - buyTotal - buyFee - sellFee;
    const pnlPct = buyTotal > 0 ? (pnl / buyTotal) * 100 : 0;
    return { pnl, pnlPct, buyFee, sellFee };
  }

  /* ---------- Render Trade List ---------- */
  const tradesList = document.getElementById('tradesList');
  const tradesEmpty = document.getElementById('tradesEmpty');

  function renderTrades() {
    if (trades.length === 0) {
      tradesList.innerHTML = '';
      tradesList.appendChild(tradesEmpty);
      tradesEmpty.style.display = 'block';
      document.getElementById('chartSection').style.display = 'none';
      updateSummary();
      return;
    }

    tradesEmpty.style.display = 'none';
    tradesList.innerHTML = '';

    trades.forEach((trade, idx) => {
      const { pnl, pnlPct } = calcTradePnl(trade);
      const row = document.createElement('div');
      row.className = 'trade-row';
      row.innerHTML = `
        <span class="trade-row__token">${trade.token.toUpperCase()}</span>
        <span class="trade-row__prices">
          Buy: $${trade.buyPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}<br>
          Sell: $${trade.sellPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}${trade.isOpen ? ' (live)' : ''}
        </span>
        <span class="trade-row__qty">Qty: ${trade.quantity}</span>
        <span class="trade-row__pnl ${pnl >= 0 ? 'positive' : 'negative'}">
          ${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          <br><small>${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%</small>
        </span>
        <button class="trade-row__delete" data-idx="${idx}" aria-label="Delete trade">✕</button>
      `;
      tradesList.appendChild(row);
      animateNewRow(row);
    });

    // Delete handlers
    tradesList.querySelectorAll('.trade-row__delete').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.dataset.idx, 10);
        trades.splice(idx, 1);
        saveTrades(trades);
        renderTrades();
      });
    });

    updateSummary();
    renderChart();
    document.getElementById('chartSection').style.display = 'block';
  }

  /* ---------- Update Summary ---------- */
  function updateSummary() {
    const totalTradesEl = document.getElementById('totalTrades');
    const totalPnlEl = document.getElementById('totalPnl');
    const winRateEl = document.getElementById('winRate');
    const bestTradeEl = document.getElementById('bestTrade');

    totalTradesEl.textContent = trades.length;

    if (trades.length === 0) {
      totalPnlEl.textContent = '$0.00';
      totalPnlEl.className = 'summary-card__value';
      winRateEl.textContent = '—';
      bestTradeEl.textContent = '—';
      return;
    }

    let totalPnl = 0;
    let wins = 0;
    let bestPnl = -Infinity;

    trades.forEach(trade => {
      const { pnl } = calcTradePnl(trade);
      totalPnl += pnl;
      if (pnl > 0) wins++;
      if (pnl > bestPnl) bestPnl = pnl;
    });

    totalPnlEl.textContent = (totalPnl >= 0 ? '+' : '') + '$' + totalPnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    totalPnlEl.className = 'summary-card__value ' + (totalPnl >= 0 ? 'positive' : 'negative');

    winRateEl.textContent = ((wins / trades.length) * 100).toFixed(1) + '%';
    winRateEl.className = 'summary-card__value ' + (wins / trades.length >= 0.5 ? 'positive' : 'negative');

    bestTradeEl.textContent = '+$' + bestPnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    bestTradeEl.className = 'summary-card__value positive';
  }

  /* ---------- Chart ---------- */
  let chartInstance = null;

  function renderChart() {
    if (typeof Chart === 'undefined' || trades.length === 0) return;

    const ctx = document.getElementById('pnlChart').getContext('2d');
    const isDark = html.getAttribute('data-theme') === 'dark';

    const pnlValues = trades.map(t => calcTradePnl(t).pnl);
    const labels = trades.map((t, i) => `#${i + 1} ${t.token.toUpperCase()}`);
    const colors = pnlValues.map(v => v >= 0
      ? (isDark ? '#22c55e' : '#16a34a')
      : (isDark ? '#ef4444' : '#dc2626')
    );

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'P&L ($)',
          data: pnlValues,
          backgroundColor: colors,
          borderRadius: 4,
          borderSkipped: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark ? '#242320' : '#eae7e2',
            titleColor: isDark ? '#e8e4dc' : '#1a1917',
            bodyColor: isDark ? '#a39e93' : '#5c5850',
            borderColor: isDark ? '#3a3833' : '#cfc9c0',
            borderWidth: 1,
            bodyFont: { family: "'Azeret Mono', monospace" },
            callbacks: {
              label: ctx => {
                const v = ctx.parsed.y;
                return (v >= 0 ? '+' : '') + '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: isDark ? 'rgba(232,228,220,.06)' : 'rgba(26,25,23,.04)' },
            ticks: {
              color: isDark ? '#706b60' : '#8a857b',
              font: { family: "'Azeret Mono', monospace", size: 10 }
            }
          },
          y: {
            grid: { color: isDark ? 'rgba(232,228,220,.06)' : 'rgba(26,25,23,.04)' },
            ticks: {
              color: isDark ? '#706b60' : '#8a857b',
              font: { family: "'Azeret Mono', monospace", size: 10 },
              callback: v => '$' + v.toLocaleString()
            }
          }
        }
      }
    });
  }

  /* ---------- Form Submit ---------- */
  const form = document.getElementById('tradeForm');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const tokenSelect = document.getElementById('tokenSelect');
    const token = tokenSelect.value;
    const buyPrice = parseFloat(document.getElementById('buyPrice').value);
    const quantity = parseFloat(document.getElementById('quantity').value);
    const feeRate = parseFloat(document.getElementById('feeRate').value) || 0;
    const isOpen = document.getElementById('openTrade').checked;

    if (!buyPrice || buyPrice <= 0 || !quantity || quantity <= 0) return;

    let sellPrice;
    if (isOpen && token !== 'custom') {
      sellPrice = await fetchCurrentPrice(token);
      if (!sellPrice) {
        alert('Could not fetch live price. Enter sell price manually.');
        return;
      }
    } else {
      sellPrice = parseFloat(document.getElementById('sellPrice').value);
      if (!sellPrice || sellPrice <= 0) {
        alert('Please enter a sell price.');
        return;
      }
    }

    const trade = {
      id: Date.now(),
      token: token === 'custom' ? 'CUSTOM' : token,
      buyPrice,
      sellPrice,
      quantity,
      feeRate,
      isOpen,
      timestamp: new Date().toISOString()
    };

    trades.push(trade);
    saveTrades(trades);
    renderTrades();

    // Reset form partially
    document.getElementById('buyPrice').value = '';
    document.getElementById('sellPrice').value = '';
    document.getElementById('quantity').value = '';
    document.getElementById('openTrade').checked = false;
  });

  /* ---------- Open Trade Checkbox Toggle ---------- */
  document.getElementById('openTrade').addEventListener('change', (e) => {
    const sellInput = document.getElementById('sellPrice');
    if (e.target.checked) {
      sellInput.disabled = true;
      sellInput.placeholder = 'Live price';
      sellInput.value = '';
    } else {
      sellInput.disabled = false;
      sellInput.placeholder = '0.00';
    }
  });

  /* ---------- Update Open Trades Periodically ---------- */
  async function updateOpenTrades() {
    let changed = false;
    for (const trade of trades) {
      if (trade.isOpen && trade.token !== 'CUSTOM') {
        const price = await fetchCurrentPrice(trade.token);
        if (price && price !== trade.sellPrice) {
          trade.sellPrice = price;
          changed = true;
        }
      }
    }
    if (changed) {
      saveTrades(trades);
      renderTrades();
    }
  }

  /* ---------- Init ---------- */
  function init() {
    initAnimations();
    renderTrades();
    if (trades.some(t => t.isOpen)) updateOpenTrades();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
