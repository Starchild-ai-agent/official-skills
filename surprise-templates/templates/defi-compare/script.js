/* ============================================================
   DeFi Protocol Comparison — script.js
   Skeleton: A8 Comparison · Hover: C22 outline
   Entrance: D17 translateY(-30px) · Hero: H14 Comparison
   ============================================================ */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };

  var PROTOCOLS = {
    aave: { name: 'Aave', tvl: 12.4, apy: 4.2, chains: 7, audits: 12, token: 'AAVE', mcap: '$1.8B', launched: 2020, type: 'Lending', governance: 'Yes', tvlHistory: [8.2, 9.1, 10.5, 11.2, 11.8, 12.4], pros: ['Multi-chain support', 'Flash loans', 'Strong audits', 'Governance'], cons: ['Complex for beginners', 'Gas fees on L1'] },
    compound: { name: 'Compound', tvl: 3.1, apy: 3.8, chains: 2, audits: 8, token: 'COMP', mcap: '$420M', launched: 2018, type: 'Lending', governance: 'Yes', tvlHistory: [5.5, 4.8, 4.2, 3.8, 3.4, 3.1], pros: ['Pioneer in DeFi lending', 'Simple interface', 'Battle-tested'], cons: ['Limited chain support', 'Declining TVL', 'Lower APY'] },
    makerdao: { name: 'MakerDAO', tvl: 8.7, apy: 5.0, chains: 1, audits: 15, token: 'MKR', mcap: '$1.2B', launched: 2017, type: 'CDP/Stablecoin', governance: 'Yes', tvlHistory: [6.8, 7.2, 7.8, 8.1, 8.4, 8.7], pros: ['DAI stablecoin issuer', 'Most audited', 'RWA integration'], cons: ['Ethereum only', 'Complex governance', 'Liquidation risk'] },
    uniswap: { name: 'Uniswap', tvl: 5.2, apy: 8.5, chains: 8, audits: 6, token: 'UNI', mcap: '$5.8B', launched: 2018, type: 'DEX', governance: 'Yes', tvlHistory: [3.8, 4.1, 4.5, 4.8, 5.0, 5.2], pros: ['Largest DEX', 'Multi-chain', 'Concentrated liquidity'], cons: ['Impermanent loss', 'MEV exposure', 'No fee switch yet'] },
    curve: { name: 'Curve', tvl: 2.8, apy: 6.2, chains: 12, audits: 9, token: 'CRV', mcap: '$580M', launched: 2020, type: 'DEX', governance: 'Yes', tvlHistory: [4.5, 4.0, 3.5, 3.2, 3.0, 2.8], pros: ['Best for stableswaps', 'veCRV model', 'Wide chain support'], cons: ['Complex UI', 'Declining TVL', 'Smart contract risk'] },
    lido: { name: 'Lido', tvl: 33.5, apy: 3.8, chains: 5, audits: 10, token: 'LDO', mcap: '$1.5B', launched: 2020, type: 'Liquid Staking', governance: 'Yes', tvlHistory: [18.0, 22.0, 26.0, 29.0, 31.0, 33.5], pros: ['Largest LST protocol', 'stETH widely used', 'No minimum stake'], cons: ['Centralization concerns', 'Slashing risk', 'Validator dependency'] }
  };

  var compareChart = null;

  var savedTheme = localStorage.getItem('dc_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  $('#themeToggle').addEventListener('click', function () {
    var cur = document.documentElement.getAttribute('data-theme');
    var nxt = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nxt);
    localStorage.setItem('dc_theme', nxt);
    updateChart();
  });

  function compare() {
    var a = PROTOCOLS[$('#protocolA').value];
    var b = PROTOCOLS[$('#protocolB').value];
    renderTable(a, b);
    updateChart();
    renderProscons(a, b);
  }

  function better(va, vb, higher) {
    if (higher) return va > vb ? 'win' : (va < vb ? 'lose' : '');
    return va < vb ? 'win' : (va > vb ? 'lose' : '');
  }

  function renderTable(a, b) {
    var rows = [
      ['TVL', '$' + a.tvl + 'B', '$' + b.tvl + 'B', better(a.tvl, b.tvl, true), better(b.tvl, a.tvl, true)],
      ['APY', a.apy + '%', b.apy + '%', better(a.apy, b.apy, true), better(b.apy, a.apy, true)],
      ['Chains', a.chains, b.chains, better(a.chains, b.chains, true), better(b.chains, a.chains, true)],
      ['Audits', a.audits, b.audits, better(a.audits, b.audits, true), better(b.audits, a.audits, true)],
      ['Token', a.token, b.token, '', ''],
      ['Market Cap', a.mcap, b.mcap, '', ''],
      ['Launched', a.launched, b.launched, '', ''],
      ['Type', a.type, b.type, '', ''],
      ['Governance', a.governance, b.governance, '', '']
    ];

    var html = '<table class="compare-table"><thead><tr><th>Metric</th><th>' + a.name + '</th><th>' + b.name + '</th></tr></thead><tbody>';
    rows.forEach(function (r) {
      html += '<tr><td>' + r[0] + '</td><td class="col-a ' + r[3] + '">' + r[1] + '</td><td class="col-b ' + r[4] + '">' + r[2] + '</td></tr>';
    });
    html += '</tbody></table>';
    $('#comparison').innerHTML = html;
  }

  function updateChart() {
    if (typeof Chart === 'undefined') return;
    var a = PROTOCOLS[$('#protocolA').value];
    var b = PROTOCOLS[$('#protocolB').value];
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var txtC = isDark ? '#e4e8f0' : '#14162a';
    var gridC = isDark ? '#282a40' : '#d0d4e4';
    var labels = ['6m ago', '5m ago', '4m ago', '3m ago', '2m ago', 'Now'];

    if (compareChart) compareChart.destroy();
    compareChart = new Chart($('#compareChart'), {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          { label: a.name, data: a.tvlHistory, backgroundColor: isDark ? 'rgba(167,139,250,0.6)' : 'rgba(124,58,237,0.6)', borderRadius: 6 },
          { label: b.name, data: b.tvlHistory, backgroundColor: isDark ? 'rgba(56,189,248,0.6)' : 'rgba(14,165,233,0.6)', borderRadius: 6 }
        ]
      },
      options: {
        responsive: true,
        scales: {
          x: { ticks: { color: txtC }, grid: { display: false } },
          y: { ticks: { color: txtC, callback: function (v) { return '$' + v + 'B'; } }, grid: { color: gridC } }
        },
        plugins: { legend: { labels: { color: txtC, font: { family: 'JetBrains Mono', size: 11 } } } }
      }
    });
  }

  function renderProscons(a, b) {
    var html = '<div class="proscons__card"><h3 class="proscons__card-title">' + a.name + '</h3><ul class="proscons__list">';
    a.pros.forEach(function (p) { html += '<li class="proscons__item proscons__item--pro">' + p + '</li>'; });
    a.cons.forEach(function (c) { html += '<li class="proscons__item proscons__item--con">' + c + '</li>'; });
    html += '</ul></div><div class="proscons__card"><h3 class="proscons__card-title">' + b.name + '</h3><ul class="proscons__list">';
    b.pros.forEach(function (p) { html += '<li class="proscons__item proscons__item--pro">' + p + '</li>'; });
    b.cons.forEach(function (c) { html += '<li class="proscons__item proscons__item--con">' + c + '</li>'; });
    html += '</ul></div>';
    $('#proscons').innerHTML = html;
  }

  $('#protocolA').addEventListener('change', compare);
  $('#protocolB').addEventListener('change', compare);
  compare();

  if (typeof gsap !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
    var mm = gsap.matchMedia();
    mm.add('(prefers-reduced-motion: no-preference)', function () {
      gsap.from('.hero__title', { y: -30, opacity: 0, duration: 0.6, ease: 'power2.out' });
      gsap.from('.hero__sub', { y: -30, opacity: 0, duration: 0.6, delay: 0.1, ease: 'power2.out' });
      gsap.from('.selectors', { y: -30, opacity: 0, duration: 0.6, delay: 0.2, ease: 'power2.out' });
      gsap.from('.comparison', { y: -30, opacity: 0, duration: 0.6, delay: 0.3, ease: 'power2.out' });
      gsap.from('.chart-section', { y: -30, opacity: 0, duration: 0.6, scrollTrigger: { trigger: '.chart-section', start: 'top 85%' }, ease: 'power2.out' });
      gsap.from('.proscons__card', { y: -30, opacity: 0, duration: 0.5, stagger: 0.1, scrollTrigger: { trigger: '.proscons', start: 'top 85%' }, ease: 'power2.out' });
    });
  }
})();
