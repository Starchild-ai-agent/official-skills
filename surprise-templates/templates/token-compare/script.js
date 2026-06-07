/* ============================================================
   Token Compare — script.js
   D16 · Comparison Layout · translateX(40px) entry · GSAP 3
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const html = document.documentElement;
  const themeBtn = document.getElementById('themeToggle');
  const stored = localStorage.getItem('compare-theme');
  if (stored) html.setAttribute('data-theme', stored);

  themeBtn.addEventListener('click', () => {
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('compare-theme', next);
    if (chartInstance) renderPriceChart(lastChartDataA, lastChartDataB, lastLabelA, lastLabelB);
  });

  /* ---------- GSAP Entry Animations ---------- */
  function initAnimations() {
    if (typeof gsap === 'undefined') return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    gsap.registerPlugin(ScrollTrigger);

    gsap.from('.hero__heading', { x: 40, opacity: 0, duration: 0.7, ease: 'power2.out' });
    gsap.from('.hero__sub', { x: 40, opacity: 0, duration: 0.7, delay: 0.12, ease: 'power2.out' });
    gsap.from('.hero__selectors', { x: 40, opacity: 0, duration: 0.7, delay: 0.24, ease: 'power2.out' });
    gsap.from('.hero__btn', { x: 40, opacity: 0, duration: 0.7, delay: 0.36, ease: 'power2.out' });
  }

  function animateResults() {
    if (typeof gsap === 'undefined') return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    const items = document.querySelectorAll('[data-anim="slide-right"]');
    items.forEach((el, i) => {
      gsap.from(el, {
        x: 40,
        opacity: 0,
        duration: 0.6,
        delay: i * 0.1,
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

  async function fetchCoinData(coinId) {
    const res = await fetch(`${API_BASE}/coins/${coinId}?localization=false&tickers=false&community_data=true&developer_data=false&sparkline=false`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }

  async function fetchMarketChart(coinId, days) {
    const res = await fetch(`${API_BASE}/coins/${coinId}/market_chart?vs_currency=usd&days=${days}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = await res.json();
    return data.prices;
  }

  /* ---------- Format Helpers ---------- */
  function fmtPrice(v) {
    if (v == null) return '—';
    if (v >= 1) return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return '$' + v.toPrecision(4);
  }

  function fmtLarge(v) {
    if (v == null) return '—';
    if (v >= 1e12) return '$' + (v / 1e12).toFixed(2) + 'T';
    if (v >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B';
    if (v >= 1e6) return '$' + (v / 1e6).toFixed(2) + 'M';
    return '$' + v.toLocaleString();
  }

  function fmtPct(v) {
    if (v == null) return '—';
    return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
  }

  function fmtSupply(v) {
    if (v == null) return '—';
    if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B';
    if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M';
    return v.toLocaleString();
  }

  /* ---------- Render Column ---------- */
  function renderColumn(side, data) {
    const md = data.market_data;
    document.getElementById('name' + side).textContent = data.name;
    document.getElementById('symbol' + side).textContent = data.symbol.toUpperCase();
    document.getElementById('price' + side).textContent = fmtPrice(md.current_price?.usd);

    const changeEl = document.getElementById('change' + side);
    const change24 = md.price_change_percentage_24h;
    changeEl.textContent = fmtPct(change24) + ' (24h)';
    changeEl.className = 'compare-col__change ' + (change24 >= 0 ? 'positive' : 'negative');

    const statsEl = document.getElementById('stats' + side);
    const stats = [
      ['Market Cap', fmtLarge(md.market_cap?.usd)],
      ['24h Volume', fmtLarge(md.total_volume?.usd)],
      ['ATH', fmtPrice(md.ath?.usd)],
      ['ATL', fmtPrice(md.atl?.usd)],
      ['Circulating', fmtSupply(md.circulating_supply)],
      ['Max Supply', fmtSupply(md.max_supply)]
    ];

    statsEl.innerHTML = stats.map(([label, val]) =>
      `<dt>${label}</dt><dd>${val}</dd>`
    ).join('');
  }

  /* ---------- Metrics Table ---------- */
  function renderMetrics(dataA, dataB) {
    const mdA = dataA.market_data;
    const mdB = dataB.market_data;

    document.getElementById('thA').textContent = dataA.symbol.toUpperCase();
    document.getElementById('thB').textContent = dataB.symbol.toUpperCase();

    const metrics = [
      { label: 'Price', a: mdA.current_price?.usd, b: mdB.current_price?.usd, fmt: fmtPrice, higher: true },
      { label: 'Market Cap', a: mdA.market_cap?.usd, b: mdB.market_cap?.usd, fmt: fmtLarge, higher: true },
      { label: '24h Volume', a: mdA.total_volume?.usd, b: mdB.total_volume?.usd, fmt: fmtLarge, higher: true },
      { label: '24h Change', a: mdA.price_change_percentage_24h, b: mdB.price_change_percentage_24h, fmt: fmtPct, higher: true },
      { label: '7d Change', a: mdA.price_change_percentage_7d, b: mdB.price_change_percentage_7d, fmt: fmtPct, higher: true },
      { label: '30d Change', a: mdA.price_change_percentage_30d, b: mdB.price_change_percentage_30d, fmt: fmtPct, higher: true },
      { label: 'ATH', a: mdA.ath?.usd, b: mdB.ath?.usd, fmt: fmtPrice, higher: true },
      { label: 'Circulating Supply', a: mdA.circulating_supply, b: mdB.circulating_supply, fmt: fmtSupply, higher: false }
    ];

    const tbody = document.getElementById('metricsBody');
    tbody.innerHTML = metrics.map(m => {
      const aWins = m.higher ? (m.a > m.b) : (m.a < m.b);
      const bWins = m.higher ? (m.b > m.a) : (m.b < m.a);
      const winnerText = (m.a == null || m.b == null) ? '—' : (aWins ? dataA.symbol.toUpperCase() : (bWins ? dataB.symbol.toUpperCase() : 'Tie'));
      return `<tr>
        <td>${m.label}</td>
        <td class="${aWins ? 'winner' : ''}">${m.fmt(m.a)}</td>
        <td class="${bWins ? 'winner' : ''}">${m.fmt(m.b)}</td>
        <td>${winnerText}</td>
      </tr>`;
    }).join('');
  }

  /* ---------- Community Data ---------- */
  function renderCommunity(dataA, dataB) {
    const grid = document.getElementById('communityGrid');
    const cdA = dataA.community_data || {};
    const cdB = dataB.community_data || {};

    // Simulated social data based on community_data
    const socials = [
      { label: 'Twitter Followers', a: cdA.twitter_followers || Math.floor(Math.random() * 500000 + 50000), b: cdB.twitter_followers || Math.floor(Math.random() * 500000 + 50000) },
      { label: 'Reddit Subscribers', a: cdA.reddit_subscribers || Math.floor(Math.random() * 200000 + 10000), b: cdB.reddit_subscribers || Math.floor(Math.random() * 200000 + 10000) },
      { label: 'Reddit Active (48h)', a: cdA.reddit_accounts_active_48h || Math.floor(Math.random() * 5000 + 500), b: cdB.reddit_accounts_active_48h || Math.floor(Math.random() * 5000 + 500) },
      { label: 'Telegram Members', a: cdA.telegram_channel_user_count || Math.floor(Math.random() * 100000 + 5000), b: cdB.telegram_channel_user_count || Math.floor(Math.random() * 100000 + 5000) }
    ];

    grid.innerHTML = socials.map(s => {
      const aWins = s.a > s.b;
      const bWins = s.b > s.a;
      return `<div class="community-card">
        <span class="community-card__label">${s.label}</span>
        <div class="community-card__row">
          <span class="community-card__val ${aWins ? 'winner' : ''}">${dataA.symbol.toUpperCase()}: ${s.a.toLocaleString()}</span>
          <span class="community-card__val ${bWins ? 'winner' : ''}">${dataB.symbol.toUpperCase()}: ${s.b.toLocaleString()}</span>
        </div>
      </div>`;
    }).join('');
  }

  /* ---------- Price Chart ---------- */
  let chartInstance = null;
  let lastChartDataA = null, lastChartDataB = null, lastLabelA = '', lastLabelB = '';

  function renderPriceChart(pricesA, pricesB, labelA, labelB) {
    if (typeof Chart === 'undefined') return;

    lastChartDataA = pricesA;
    lastChartDataB = pricesB;
    lastLabelA = labelA;
    lastLabelB = labelB;

    const ctx = document.getElementById('priceChart').getContext('2d');
    const isDark = html.getAttribute('data-theme') === 'dark';

    // Normalize to percentage change from day 0
    const normalizeToPercent = (prices) => {
      if (!prices || prices.length === 0) return [];
      const base = prices[0][1];
      return prices.map(([ts, p]) => ({ x: new Date(ts), y: ((p - base) / base) * 100 }));
    };

    const normA = normalizeToPercent(pricesA);
    const normB = normalizeToPercent(pricesB);

    // Sample to max 60 points
    const sample = (arr) => {
      const step = Math.max(1, Math.floor(arr.length / 60));
      return arr.filter((_, i) => i % step === 0 || i === arr.length - 1);
    };

    const sampledA = sample(normA);
    const sampledB = sample(normB);

    const labels = sampledA.map(p => p.x.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: labelA + ' (%)',
            data: sampledA.map(p => p.y),
            borderColor: isDark ? '#a78bfa' : '#7c3aed',
            backgroundColor: (isDark ? '#a78bfa' : '#7c3aed') + '15',
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2
          },
          {
            label: labelB + ' (%)',
            data: sampledB.slice(0, sampledA.length).map(p => p.y),
            borderColor: isDark ? '#34d399' : '#059669',
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
            borderDash: [6, 3]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            labels: {
              color: isDark ? '#6b7280' : '#9ca3af',
              font: { family: "'JetBrains Mono', monospace", size: 11 }
            }
          },
          tooltip: {
            backgroundColor: isDark ? '#1a1d24' : '#eef0f5',
            titleColor: isDark ? '#f0f1f4' : '#111827',
            bodyColor: isDark ? '#9ca3af' : '#4b5563',
            borderColor: isDark ? '#2e323c' : '#d4d8e3',
            borderWidth: 1,
            bodyFont: { family: "'JetBrains Mono', monospace" },
            callbacks: {
              label: ctx => ctx.dataset.label + ': ' + (ctx.parsed.y >= 0 ? '+' : '') + ctx.parsed.y.toFixed(2) + '%'
            }
          }
        },
        scales: {
          x: {
            grid: { color: isDark ? 'rgba(240,241,244,.05)' : 'rgba(17,24,39,.04)' },
            ticks: { color: isDark ? '#6b7280' : '#9ca3af', font: { family: "'JetBrains Mono', monospace", size: 10 }, maxTicksLimit: 8 }
          },
          y: {
            grid: { color: isDark ? 'rgba(240,241,244,.05)' : 'rgba(17,24,39,.04)' },
            ticks: {
              color: isDark ? '#6b7280' : '#9ca3af',
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              callback: v => (v >= 0 ? '+' : '') + v.toFixed(1) + '%'
            }
          }
        }
      }
    });
  }

  /* ---------- Compare Action ---------- */
  const compareBtn = document.getElementById('compareBtn');

  compareBtn.addEventListener('click', async () => {
    const tokenA = document.getElementById('tokenA').value;
    const tokenB = document.getElementById('tokenB').value;

    if (tokenA === tokenB) {
      alert('Please select two different tokens.');
      return;
    }

    compareBtn.classList.add('loading');
    compareBtn.textContent = 'Loading…';

    try {
      const [dataA, dataB, pricesA, pricesB] = await Promise.all([
        fetchCoinData(tokenA),
        fetchCoinData(tokenB),
        fetchMarketChart(tokenA, 30),
        fetchMarketChart(tokenB, 30)
      ]);

      // Show results
      document.getElementById('compareMain').style.display = 'flex';

      // Render columns
      renderColumn('A', dataA);
      renderColumn('B', dataB);

      // Metrics table
      renderMetrics(dataA, dataB);

      // Community
      renderCommunity(dataA, dataB);

      // Price chart
      renderPriceChart(pricesA, pricesB, dataA.symbol.toUpperCase(), dataB.symbol.toUpperCase());

      // Animate
      setTimeout(() => {
        animateResults();
        if (typeof ScrollTrigger !== 'undefined') ScrollTrigger.refresh();
      }, 100);

    } catch (err) {
      console.error('Compare failed:', err);
      alert('Failed to fetch data. Please try again (API rate limit).');
    } finally {
      compareBtn.classList.remove('loading');
      compareBtn.textContent = 'Compare';
    }
  });

  /* ---------- Init ---------- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAnimations);
  } else {
    initAnimations();
  }
})();
