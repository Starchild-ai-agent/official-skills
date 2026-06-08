/* ============================================
 * Alpha Signal Board — E2
 * APIs: CoinGecko + simulated alpha signals
 * ============================================ */

(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const themeToggle = document.getElementById('themeToggle');
  const root = document.documentElement;

  function setTheme(t) {
    root.setAttribute('data-theme', t);
    localStorage.setItem('alpha-theme', t);
  }

  themeToggle.addEventListener('click', () => {
    setTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });

  const saved = localStorage.getItem('alpha-theme');
  if (saved) setTheme(saved);

  /* ---------- Simulated Signal Data ---------- */
  const signalTypes = ['kol', 'onchain', 'price', 'new'];
  const typeLabels = { kol: 'KOL Mention', onchain: 'On-chain', price: 'Price Break', new: 'New Listing' };

  const mockSignals = [
    { token: '$PEPE', type: 'kol', score: 92, desc: 'Mentioned by @CryptoKaleo, @Hsaka, and 3 other KOLs in the last 2 hours. Volume spike 340%.', source: '@CryptoKaleo', time: '12 min ago' },
    { token: '$ARB', type: 'onchain', score: 88, desc: 'Smart money wallet 0x7a3...f2c accumulated 2.4M ARB in 3 transactions. Total inflow $4.2M.', source: 'On-chain Monitor', time: '28 min ago' },
    { token: '$WLD', type: 'price', score: 85, desc: 'Broke above 200-day MA with 5x average volume. RSI at 68, approaching overbought.', source: 'Price Scanner', time: '45 min ago' },
    { token: '$ONDO', type: 'kol', score: 82, desc: 'Featured in @Pentoshi thread about RWA narrative. 12 quote tweets from top accounts.', source: '@Pentoshi', time: '1h ago' },
    { token: '$STRK', type: 'new', score: 79, desc: 'New listing on Binance Futures. Initial funding rate -0.03%. Open interest surging.', source: 'Exchange Monitor', time: '1.5h ago' },
    { token: '$TIA', type: 'onchain', score: 76, desc: 'Unusual staking activity: 8M TIA unstaked from validators in 24h. Potential sell pressure.', source: 'Staking Tracker', time: '2h ago' },
    { token: '$JUP', type: 'price', score: 74, desc: 'Golden cross on 4H chart. MACD histogram turning positive. Support at $1.12 holding.', source: 'TA Scanner', time: '2.5h ago' },
    { token: '$PYTH', type: 'kol', score: 71, desc: 'Mentioned by @cobie in spaces discussion about oracle infrastructure plays.', source: '@cobie', time: '3h ago' },
    { token: '$MANTA', type: 'onchain', score: 68, desc: 'DEX volume on Manta Pacific up 280% in 24h. New TVL record at $420M.', source: 'DeFi Tracker', time: '3.5h ago' },
    { token: '$PIXEL', type: 'new', score: 65, desc: 'Token generation event completed. Initial DEX offering at $0.52. Currently trading at $0.78.', source: 'Launch Monitor', time: '4h ago' },
    { token: '$SEI', type: 'price', score: 63, desc: 'Breakout from descending wedge pattern. Target $0.95 based on measured move.', source: 'Pattern Scanner', time: '4.5h ago' },
    { token: '$DYMENSION', type: 'kol', score: 60, desc: 'Multiple CT accounts discussing modular blockchain thesis. Sentiment score 8.2/10.', source: 'Sentiment AI', time: '5h ago' }
  ];

  const credibilitySources = [
    { name: '@CryptoKaleo', type: 'KOL / Twitter', score: 94 },
    { name: 'On-chain Monitor', type: 'Blockchain Analytics', score: 91 },
    { name: '@Pentoshi', type: 'KOL / Twitter', score: 88 },
    { name: 'Price Scanner', type: 'Technical Analysis', score: 85 },
    { name: '@cobie', type: 'KOL / Twitter', score: 83 },
    { name: 'DeFi Tracker', type: 'Protocol Analytics', score: 80 },
    { name: 'Exchange Monitor', type: 'CEX Data', score: 77 },
    { name: 'Sentiment AI', type: 'NLP Analysis', score: 74 }
  ];

  /* ---------- Render Signals ---------- */
  const signalFeed = document.getElementById('signalFeed');
  let currentFilter = 'all';

  function renderSignals(filter) {
    signalFeed.innerHTML = '';
    const filtered = filter === 'all' ? mockSignals : mockSignals.filter(s => s.type === filter);

    filtered.forEach(signal => {
      const el = document.createElement('div');
      el.className = 'signal-item';
      el.setAttribute('data-type', signal.type);
      el.innerHTML = `
        <div class="signal-meta">
          <span class="signal-score">${signal.score}</span>
          <span class="signal-score-label">Score</span>
        </div>
        <div class="signal-body">
          <div class="signal-header">
            <span class="signal-token">${signal.token}</span>
            <span class="signal-type-tag" data-type="${signal.type}">${typeLabels[signal.type]}</span>
          </div>
          <p class="signal-desc">${signal.desc}</p>
          <div class="signal-time">${signal.time} · <span class="signal-source">${signal.source}</span></div>
        </div>
      `;
      signalFeed.appendChild(el);
    });

    // Animate new items
    if (window.gsap) {
      const mm = gsap.matchMedia();
      mm.add('(prefers-reduced-motion: no-preference)', () => {
        gsap.fromTo('.signal-item',
          { x: -50, opacity: 0 },
          {
            x: 0,
            opacity: 1,
            duration: 0.4,
            stagger: 0.06,
            ease: 'power2.out',
            clearProps: 'transform'
          }
        );
      });
    }
  }

  /* ---------- Filter Buttons ---------- */
  const filterBtns = document.querySelectorAll('.filter-btn');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      renderSignals(currentFilter);
    });
  });

  /* ---------- Banner ---------- */
  function updateBanner() {
    const top = mockSignals[0];
    document.getElementById('bannerToken').textContent = top.token;
    document.getElementById('bannerReason').textContent = top.desc.slice(0, 80) + '...';
    document.getElementById('bannerCount').textContent = mockSignals.length;

    const avgScore = Math.round(mockSignals.reduce((a, s) => a + s.score, 0) / mockSignals.length);
    document.getElementById('bannerStrength').textContent = avgScore;
  }

  /* ---------- Token Chart (Bar) ---------- */
  function renderTokenChart() {
    const tokenCounts = {};
    mockSignals.forEach(s => {
      tokenCounts[s.token] = (tokenCounts[s.token] || 0) + 1;
    });

    // Also weight by score
    const tokenScores = {};
    mockSignals.forEach(s => {
      tokenScores[s.token] = (tokenScores[s.token] || 0) + s.score;
    });

    const labels = Object.keys(tokenScores).sort((a, b) => tokenScores[b] - tokenScores[a]).slice(0, 8);
    const values = labels.map(l => tokenScores[l]);

    const ctx = document.getElementById('tokenChart');
    if (!ctx) return;

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Signal Score',
          data: values,
          backgroundColor: 'rgba(234,179,8,.3)',
          borderColor: '#eab308',
          borderWidth: 1,
          borderRadius: 4,
          barPercentage: 0.6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        indexAxis: 'y',
        scales: {
          x: {
            grid: { color: 'rgba(138,122,116,.1)' },
            ticks: {
              color: getComputedStyle(document.body).getPropertyValue('--text-muted').trim() || '#8a7a74',
              font: { family: "'Victor Mono', monospace", size: 10 }
            }
          },
          y: {
            grid: { display: false },
            ticks: {
              color: getComputedStyle(document.body).getPropertyValue('--text-primary').trim() || '#faf5f0',
              font: { family: "'Victor Mono', monospace", size: 11, weight: 600 }
            }
          }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
  }

  /* ---------- Credibility List ---------- */
  function renderCredibility() {
    const list = document.getElementById('credibilityList');
    credibilitySources.forEach((src, i) => {
      const el = document.createElement('div');
      el.className = 'cred-item';
      el.innerHTML = `
        <span class="cred-rank">#${i + 1}</span>
        <div class="cred-info">
          <div class="cred-name">${src.name}</div>
          <div class="cred-type">${src.type}</div>
        </div>
        <div class="cred-score-bar">
          <div class="cred-score-fill" style="width: ${src.score}%"></div>
        </div>
        <span class="cred-score-value">${src.score}</span>
      `;
      list.appendChild(el);
    });
  }

  /* ---------- CoinGecko Price Validation ---------- */
  async function validatePrices() {
    try {
      const tokens = ['pepe', 'arbitrum', 'worldcoin', 'ondo-finance', 'starknet'];
      const res = await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${tokens.join(',')}&vs_currencies=usd&include_24hr_change=true`);
      if (!res.ok) return;
      const data = await res.json();

      // Update signal descriptions with real prices where available
      const priceMap = {
        pepe: data['pepe'],
        arbitrum: data['arbitrum'],
        worldcoin: data['worldcoin'],
        'ondo-finance': data['ondo-finance'],
        starknet: data['starknet']
      };

      // Could enhance signals with real price data here
      console.info('Price validation data loaded');
    } catch (e) {
      console.warn('CoinGecko validation skipped:', e.message);
    }
  }

  /* ---------- GSAP Animations ---------- */
  gsap.registerPlugin(ScrollTrigger);

  const mm = gsap.matchMedia();
  mm.add('(prefers-reduced-motion: no-preference)', () => {
    // D10: translateX(-50px) for feed items
    gsap.fromTo('.alert-banner',
      { x: -50, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.6, ease: 'power2.out', clearProps: 'transform' }
    );

    gsap.fromTo('.filter-btn',
      { x: -30, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.3, stagger: 0.05, ease: 'power2.out', delay: 0.3, clearProps: 'transform' }
    );

    gsap.fromTo('.analysis-section',
      { x: -50, opacity: 0 },
      {
        x: 0, opacity: 1, duration: 0.6, ease: 'power2.out', clearProps: 'transform',
        scrollTrigger: { trigger: '.analysis-section', start: 'top 85%' }
      }
    );

    gsap.fromTo('.cred-item',
      { x: -40, opacity: 0 },
      {
        x: 0, opacity: 1, duration: 0.4, stagger: 0.06, ease: 'power2.out', clearProps: 'transform',
        scrollTrigger: { trigger: '.credibility-section', start: 'top 85%' }
      }
    );
  });

  /* ---------- Init ---------- */
  updateBanner();
  renderSignals('all');
  renderTokenChart();
  renderCredibility();
  validatePrices();

})();
