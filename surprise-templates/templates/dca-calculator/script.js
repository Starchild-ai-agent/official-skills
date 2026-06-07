/* ============================================================
   DCA Calculator — script.js
   D12 · Table-First · Slide-from-right entry · GSAP 3
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const html = document.documentElement;
  const themeBtn = document.getElementById('themeToggle');
  const stored = localStorage.getItem('dca-theme');
  if (stored) html.setAttribute('data-theme', stored);

  themeBtn.addEventListener('click', () => {
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('dca-theme', next);
  });

  /* ---------- Default Start Date (1 year ago) ---------- */
  const startDateInput = document.getElementById('startDate');
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
  startDateInput.value = oneYearAgo.toISOString().split('T')[0];

  /* ---------- GSAP Entry Animations ---------- */
  function initAnimations() {
    if (typeof gsap === 'undefined') return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    gsap.registerPlugin(ScrollTrigger);

    // Hero entrance
    gsap.from('.hero__heading', { x: 30, opacity: 0, duration: 0.7, ease: 'power2.out' });
    gsap.from('.hero__sub', { x: 30, opacity: 0, duration: 0.7, delay: 0.15, ease: 'power2.out' });
    gsap.from('.hero__form', { x: 30, opacity: 0, duration: 0.7, delay: 0.3, ease: 'power2.out' });
  }

  function animateResults() {
    if (typeof gsap === 'undefined') return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    const items = document.querySelectorAll('[data-anim="slide-right"]');
    items.forEach((el, i) => {
      gsap.from(el, {
        x: 30,
        opacity: 0,
        duration: 0.6,
        delay: i * 0.12,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: el,
          start: 'top 85%',
          toggleActions: 'play none none none'
        }
      });
    });
  }

  /* ---------- CoinGecko API ---------- */
  const API_BASE = 'https://pro-api.coingecko.com/api/v3';

  async function fetchMarketChart(coinId, fromTs, toTs) {
    const url = `${API_BASE}/coins/${coinId}/market_chart/range?vs_currency=usd&from=${fromTs}&to=${toTs}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = await res.json();
    return data.prices; // [[timestamp, price], ...]
  }

  /* ---------- DCA Calculation ---------- */
  function calculateDCA(prices, amount, frequency) {
    const intervalMs = {
      daily: 86400000,
      weekly: 604800000,
      monthly: 2592000000
    }[frequency];

    const purchases = [];
    let totalTokens = 0;
    let totalInvested = 0;
    let nextBuyTime = prices[0][0];

    for (let i = 0; i < prices.length; i++) {
      const [ts, price] = prices[i];
      if (ts >= nextBuyTime) {
        const tokens = amount / price;
        totalTokens += tokens;
        totalInvested += amount;
        purchases.push({
          date: new Date(ts),
          price,
          amount,
          tokens,
          totalTokens,
          totalInvested,
          currentValue: totalTokens * price
        });
        nextBuyTime = ts + intervalMs;
      }
    }

    // Update current value with latest price
    const latestPrice = prices[prices.length - 1][1];
    const currentValue = totalTokens * latestPrice;
    const avgCost = totalInvested / totalTokens;
    const returnPct = ((currentValue - totalInvested) / totalInvested) * 100;

    return { purchases, totalInvested, currentValue, avgCost, returnPct, totalTokens, latestPrice };
  }

  function calculateLumpSum(prices, totalInvested) {
    const firstPrice = prices[0][1];
    const tokens = totalInvested / firstPrice;
    return prices.map(([ts, price]) => ({
      date: new Date(ts),
      value: tokens * price
    }));
  }

  /* ---------- Chart Rendering ---------- */
  let dcaChartInstance = null;
  let compareChartInstance = null;

  function getChartColors() {
    const isDark = html.getAttribute('data-theme') === 'dark';
    return {
      grid: isDark ? 'rgba(240,235,227,.08)' : 'rgba(44,36,22,.06)',
      text: isDark ? '#8a7e6e' : '#9a8b78',
      accent: isDark ? '#22c55e' : '#16a34a',
      secondary: isDark ? '#f59e0b' : '#d97706'
    };
  }

  function renderDCAChart(dcaResult, lumpSumData) {
    const ctx = document.getElementById('dcaChart').getContext('2d');
    const colors = getChartColors();

    // Sample data points for chart (max 60 points)
    const step = Math.max(1, Math.floor(dcaResult.purchases.length / 60));
    const dcaPoints = dcaResult.purchases.filter((_, i) => i % step === 0 || i === dcaResult.purchases.length - 1);

    const lumpStep = Math.max(1, Math.floor(lumpSumData.length / 60));
    const lumpPoints = lumpSumData.filter((_, i) => i % lumpStep === 0 || i === lumpSumData.length - 1);

    if (dcaChartInstance) dcaChartInstance.destroy();

    dcaChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: dcaPoints.map(p => p.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
        datasets: [
          {
            label: 'DCA Value',
            data: dcaPoints.map(p => p.currentValue),
            borderColor: colors.accent,
            backgroundColor: colors.accent + '18',
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2
          },
          {
            label: 'Lump Sum Value',
            data: lumpPoints.slice(0, dcaPoints.length).map(p => p.value),
            borderColor: colors.secondary,
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
            borderDash: [6, 3]
          },
          {
            label: 'Total Invested',
            data: dcaPoints.map(p => p.totalInvested),
            borderColor: colors.text,
            backgroundColor: 'transparent',
            fill: false,
            tension: 0,
            pointRadius: 0,
            borderWidth: 1,
            borderDash: [3, 3]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            labels: { color: colors.text, font: { family: "'IBM Plex Mono', monospace", size: 11 } }
          },
          tooltip: {
            backgroundColor: html.getAttribute('data-theme') === 'dark' ? '#2a2720' : '#f3efe9',
            titleColor: html.getAttribute('data-theme') === 'dark' ? '#f0ebe3' : '#2c2416',
            bodyColor: html.getAttribute('data-theme') === 'dark' ? '#b8ad9c' : '#6b5d4d',
            borderColor: html.getAttribute('data-theme') === 'dark' ? '#443f34' : '#d6cdbf',
            borderWidth: 1,
            bodyFont: { family: "'IBM Plex Mono', monospace" },
            callbacks: {
              label: function (ctx) {
                return ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: colors.grid },
            ticks: { color: colors.text, font: { family: "'IBM Plex Mono', monospace", size: 10 }, maxTicksLimit: 8 }
          },
          y: {
            grid: { color: colors.grid },
            ticks: {
              color: colors.text,
              font: { family: "'IBM Plex Mono', monospace", size: 10 },
              callback: v => '$' + v.toLocaleString()
            }
          }
        }
      }
    });
  }

  /* ---------- Multi-Token Comparison ---------- */
  async function renderCompareChart(amount, frequency, fromTs, toTs) {
    const tokens = ['bitcoin', 'ethereum', 'solana'];
    const tokenColors = ['#16a34a', '#d97706', '#0ea5e9'];
    const datasets = [];

    for (let t = 0; t < tokens.length; t++) {
      try {
        const prices = await fetchMarketChart(tokens[t], fromTs, toTs);
        const result = calculateDCA(prices, amount, frequency);
        const step = Math.max(1, Math.floor(result.purchases.length / 60));
        const points = result.purchases.filter((_, i) => i % step === 0 || i === result.purchases.length - 1);

        datasets.push({
          label: tokens[t].charAt(0).toUpperCase() + tokens[t].slice(1) + ' DCA',
          data: points.map(p => ({ x: p.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), y: p.currentValue })),
          borderColor: tokenColors[t],
          backgroundColor: 'transparent',
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2
        });
      } catch (e) {
        console.warn(`Failed to fetch ${tokens[t]}:`, e);
      }
    }

    if (datasets.length === 0) return;

    const ctx = document.getElementById('compareChart').getContext('2d');
    const colors = getChartColors();

    if (compareChartInstance) compareChartInstance.destroy();

    const maxLen = Math.max(...datasets.map(d => d.data.length));
    const labels = datasets.find(d => d.data.length === maxLen)?.data.map(d => d.x) || [];

    compareChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: datasets.map(ds => ({
          ...ds,
          data: ds.data.map(d => d.y)
        }))
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            labels: { color: colors.text, font: { family: "'IBM Plex Mono', monospace", size: 11 } }
          },
          tooltip: {
            backgroundColor: html.getAttribute('data-theme') === 'dark' ? '#2a2720' : '#f3efe9',
            titleColor: html.getAttribute('data-theme') === 'dark' ? '#f0ebe3' : '#2c2416',
            bodyColor: html.getAttribute('data-theme') === 'dark' ? '#b8ad9c' : '#6b5d4d',
            borderColor: html.getAttribute('data-theme') === 'dark' ? '#443f34' : '#d6cdbf',
            borderWidth: 1,
            bodyFont: { family: "'IBM Plex Mono', monospace" },
            callbacks: {
              label: function (ctx) {
                return ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: colors.grid },
            ticks: { color: colors.text, font: { family: "'IBM Plex Mono', monospace", size: 10 }, maxTicksLimit: 8 }
          },
          y: {
            grid: { color: colors.grid },
            ticks: {
              color: colors.text,
              font: { family: "'IBM Plex Mono', monospace", size: 10 },
              callback: v => '$' + v.toLocaleString()
            }
          }
        }
      }
    });
  }

  /* ---------- Render Detail Table ---------- */
  function renderTable(purchases) {
    const tbody = document.getElementById('detailBody');
    // Show last 50 entries max
    const shown = purchases.slice(-50);
    tbody.innerHTML = shown.map(p => `
      <tr>
        <td>${p.date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</td>
        <td>$${p.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
        <td>$${p.amount.toFixed(2)}</td>
        <td>${p.tokens.toFixed(6)}</td>
        <td>$${p.currentValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
      </tr>
    `).join('');
  }

  /* ---------- Update Summary Cards ---------- */
  function updateSummary(result) {
    document.getElementById('totalInvested').textContent = '$' + result.totalInvested.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    document.getElementById('currentValue').textContent = '$' + result.currentValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    const returnEl = document.getElementById('returnPct');
    returnEl.textContent = (result.returnPct >= 0 ? '+' : '') + result.returnPct.toFixed(2) + '%';
    returnEl.className = 'summary-card__value ' + (result.returnPct >= 0 ? 'positive' : 'negative');

    document.getElementById('avgCost').textContent = '$' + result.avgCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  /* ---------- Form Submit ---------- */
  const form = document.getElementById('dcaForm');
  const submitBtn = form.querySelector('.calc-panel__btn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const token = document.getElementById('tokenSelect').value;
    const amount = parseFloat(document.getElementById('amountInput').value);
    const frequency = document.getElementById('freqSelect').value;
    const startDate = document.getElementById('startDate').value;

    if (!amount || amount <= 0 || !startDate) return;

    const fromTs = Math.floor(new Date(startDate).getTime() / 1000);
    const toTs = Math.floor(Date.now() / 1000);

    submitBtn.classList.add('loading');
    submitBtn.textContent = 'Calculating…';

    try {
      const prices = await fetchMarketChart(token, fromTs, toTs);

      if (!prices || prices.length < 2) {
        alert('Not enough price data for the selected period.');
        return;
      }

      const result = calculateDCA(prices, amount, frequency);

      if (result.purchases.length === 0) {
        alert('No purchase points found. Try a longer period or different frequency.');
        return;
      }

      // Show results
      document.getElementById('results').style.display = 'flex';

      // Update summary
      updateSummary(result);

      // Lump sum comparison
      const lumpSumData = calculateLumpSum(prices, result.totalInvested);

      // Render chart
      renderDCAChart(result, lumpSumData);

      // Render table
      renderTable(result.purchases);

      // Animate results
      setTimeout(() => {
        animateResults();
        if (typeof ScrollTrigger !== 'undefined') ScrollTrigger.refresh();
      }, 100);

      // Multi-token comparison (delayed to avoid rate limit)
      setTimeout(() => {
        renderCompareChart(amount, frequency, fromTs, toTs);
      }, 2000);

    } catch (err) {
      console.error('DCA calculation failed:', err);
      alert('Failed to fetch data. Please try again in a moment (API rate limit).');
    } finally {
      submitBtn.classList.remove('loading');
      submitBtn.textContent = 'Calculate DCA';
    }
  });

  /* ---------- Init ---------- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAnimations);
  } else {
    initAnimations();
  }
})();
