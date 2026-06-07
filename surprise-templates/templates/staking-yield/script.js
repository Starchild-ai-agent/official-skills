/* ============================================================
   Staking Yield Calculator — script.js
   Skeleton: A8 Comparison · Hover: C14 border-top
   Entrance: D8 translateX(40px) · Hero: H14 Comparison
   ============================================================ */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };

  var STAKING_DATA = {
    eth: { name: 'Ethereum', symbol: 'ETH', price: 3200, protocols: [
      { name: 'Lido', apy: 3.8, minStake: 0, lock: 'None' },
      { name: 'Rocket Pool', apy: 3.5, minStake: 0.01, lock: 'None' },
      { name: 'Coinbase', apy: 3.2, minStake: 0, lock: 'None' },
      { name: 'Native (32 ETH)', apy: 4.1, minStake: 32, lock: 'Variable' }
    ]},
    sol: { name: 'Solana', symbol: 'SOL', price: 145, protocols: [
      { name: 'Marinade', apy: 7.2, minStake: 0, lock: 'None' },
      { name: 'Jito', apy: 7.8, minStake: 0, lock: 'None' },
      { name: 'Native', apy: 6.9, minStake: 0.01, lock: '2 epochs' },
      { name: 'Blaze', apy: 7.0, minStake: 0, lock: 'None' }
    ]},
    ada: { name: 'Cardano', symbol: 'ADA', price: 0.62, protocols: [
      { name: 'Daedalus Pool', apy: 4.5, minStake: 10, lock: 'None' },
      { name: 'Yoroi Pool', apy: 4.3, minStake: 5, lock: 'None' },
      { name: 'Binance', apy: 3.8, minStake: 1, lock: '30 days' }
    ]},
    dot: { name: 'Polkadot', symbol: 'DOT', price: 7.5, protocols: [
      { name: 'Native Nominator', apy: 14.2, minStake: 250, lock: '28 days' },
      { name: 'Acala', apy: 13.5, minStake: 5, lock: 'None' },
      { name: 'Parallel', apy: 12.8, minStake: 1, lock: 'None' }
    ]},
    atom: { name: 'Cosmos', symbol: 'ATOM', price: 9.2, protocols: [
      { name: 'Keplr Validator', apy: 18.5, minStake: 0.05, lock: '21 days' },
      { name: 'Stride', apy: 16.8, minStake: 0, lock: 'None' },
      { name: 'Osmosis', apy: 15.2, minStake: 0, lock: 'None' }
    ]},
    matic: { name: 'Polygon', symbol: 'MATIC', price: 0.72, protocols: [
      { name: 'Native Validator', apy: 5.2, minStake: 1, lock: 'None' },
      { name: 'Lido (Polygon)', apy: 4.8, minStake: 0, lock: 'None' },
      { name: 'Stader', apy: 5.0, minStake: 0, lock: 'None' }
    ]}
  };

  var yieldChart = null;
  var savedTheme = localStorage.getItem('sy_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);

  $('#themeToggle').addEventListener('click', function () {
    var cur = document.documentElement.getAttribute('data-theme');
    var nxt = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nxt);
    localStorage.setItem('sy_theme', nxt);
    updateChart();
  });

  function calcYield(principal, apyPct, months, comp) {
    var apy = apyPct / 100;
    var periods;
    if (comp === 'daily') periods = 365;
    else if (comp === 'weekly') periods = 52;
    else if (comp === 'monthly') periods = 12;
    else return principal * apy * (months / 12);
    var years = months / 12;
    return principal * Math.pow(1 + apy / periods, periods * years) - principal;
  }

  function calculate() {
    var token = $('#tokenSelect').value;
    var amount = parseFloat($('#stakeAmount').value) || 0;
    var months = parseInt($('#stakePeriod').value) || 12;
    var comp = $('#compounding').value;
    var data = STAKING_DATA[token];
    renderTable(data, amount, months, comp);
    updateChart();
    renderSummary(data, amount, months, comp);
  }

  function renderTable(data, amount, months, comp) {
    var body = $('#apyBody');
    var bestIdx = 0, bestYld = 0;
    var rows = data.protocols.map(function (p, i) {
      var yld = calcYield(amount, p.apy, months, comp);
      var total = amount + yld;
      if (yld > bestYld) { bestYld = yld; bestIdx = i; }
      return { p: p, yld: yld, total: total, usd: total * data.price, i: i };
    });
    body.innerHTML = rows.map(function (r) {
      var cls = r.i === bestIdx ? ' class="best-row"' : '';
      return '<tr' + cls + '><td>' + r.p.name + '</td><td class="highlight">' + r.p.apy + '%</td><td>' + r.p.minStake + ' ' + data.symbol + '</td><td>' + r.p.lock + '</td><td class="highlight">+' + r.yld.toFixed(4) + ' ' + data.symbol + '</td><td>$' + r.usd.toFixed(2) + '</td></tr>';
    }).join('');
  }

  function updateChart() {
    if (typeof Chart === 'undefined') return;
    var token = $('#tokenSelect').value;
    var amount = parseFloat($('#stakeAmount').value) || 0;
    var months = parseInt($('#stakePeriod').value) || 12;
    var comp = $('#compounding').value;
    var data = STAKING_DATA[token];
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var txtC = isDark ? '#e4e8ec' : '#1a1d21';
    var gridC = isDark ? '#333a42' : '#dde2e8';
    var labels = [];
    for (var m = 0; m <= months; m++) labels.push('M' + m);
    var colors = ['#10b981', '#f59e0b', '#6366f1', '#ef4444', '#8b5cf6'];
    var datasets = data.protocols.map(function (p, i) {
      var pts = labels.map(function (_, mi) { return amount + calcYield(amount, p.apy, mi, comp); });
      return { label: p.name + ' (' + p.apy + '%)', data: pts, borderColor: colors[i % colors.length], backgroundColor: 'transparent', borderWidth: 2, pointRadius: 0, tension: 0.3 };
    });
    if (yieldChart) yieldChart.destroy();
    yieldChart = new Chart($('#yieldChart'), {
      type: 'line',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: { ticks: { color: txtC }, grid: { color: gridC } },
          y: { ticks: { color: txtC }, grid: { color: gridC } }
        },
        plugins: { legend: { position: 'bottom', labels: { color: txtC, font: { family: 'JetBrains Mono', size: 11 } } } }
      }
    });
  }

  function renderSummary(data, amount, months, comp) {
    var grid = $('#summaryGrid');
    var best = null, bestYld = 0;
    data.protocols.forEach(function (p) {
      var yld = calcYield(amount, p.apy, months, comp);
      if (yld > bestYld) { bestYld = yld; best = p; }
    });
    if (!best) { grid.innerHTML = ''; return; }
    var totalVal = (amount + bestYld) * data.price;
    var daily = bestYld / (months * 30);
    grid.innerHTML =
      '<div class="summary__card"><div class="summary__card-label">Best Protocol</div><div class="summary__card-value">' + best.name + '</div><div class="summary__card-sub">' + best.apy + '% APY</div></div>' +
      '<div class="summary__card"><div class="summary__card-label">Total Yield</div><div class="summary__card-value">+' + bestYld.toFixed(4) + '</div><div class="summary__card-sub">' + data.symbol + ' over ' + months + ' months</div></div>' +
      '<div class="summary__card"><div class="summary__card-label">Portfolio Value</div><div class="summary__card-value">$' + totalVal.toFixed(2) + '</div><div class="summary__card-sub">~' + daily.toFixed(6) + ' ' + data.symbol + '/day</div></div>';
  }

  $('#tokenSelect').addEventListener('change', calculate);
  $('#stakeAmount').addEventListener('input', calculate);
  $('#stakePeriod').addEventListener('input', calculate);
  $('#compounding').addEventListener('change', calculate);
  calculate();

  if (typeof gsap !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
    var mm = gsap.matchMedia();
    mm.add('(prefers-reduced-motion: no-preference)', function () {
      gsap.from('.hero__badge', { x: 40, opacity: 0, duration: 0.6, ease: 'power2.out' });
      gsap.from('.hero__title', { x: 40, opacity: 0, duration: 0.7, delay: 0.1, ease: 'power2.out' });
      gsap.from('.hero__sub', { x: 40, opacity: 0, duration: 0.7, delay: 0.2, ease: 'power2.out' });
      gsap.from('.input-panel', { x: 40, opacity: 0, duration: 0.6, delay: 0.3, ease: 'power2.out' });
      gsap.from('.comparison', { x: 40, opacity: 0, duration: 0.6, scrollTrigger: { trigger: '.comparison', start: 'top 85%' }, ease: 'power2.out' });
      gsap.from('.chart-section', { x: 40, opacity: 0, duration: 0.6, scrollTrigger: { trigger: '.chart-section', start: 'top 85%' }, ease: 'power2.out' });
      gsap.from('.summary__card', { x: 40, opacity: 0, duration: 0.5, stagger: 0.1, scrollTrigger: { trigger: '.summary', start: 'top 85%' }, ease: 'power2.out' });
    });
  }
})();
