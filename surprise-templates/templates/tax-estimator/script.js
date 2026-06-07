/* ============================================================
   Crypto Tax Estimator — script.js
   Skeleton: A7 Table-First · Hover: C19 背景渐变
   Entrance: D9 scale(0.95) · Hero: H5 KPI Bar
   ============================================================ */

(function () {
  'use strict';

  var $ = function (s) { return document.querySelector(s); };

  var TAX_RATES = {
    us: { short: 15, long: 20, label: 'US' },
    uk: { short: 20, long: 10, label: 'UK' },
    de: { short: 45, long: 0, label: 'Germany' },
    jp: { short: 55, long: 20, label: 'Japan' },
    au: { short: 45, long: 22.5, label: 'Australia' },
    sg: { short: 0, long: 0, label: 'Singapore' },
    custom: { short: 20, long: 20, label: 'Custom' }
  };

  var transactions = JSON.parse(localStorage.getItem('te_txs') || '[]');
  var taxChart = null;

  var themeToggle = $('#themeToggle');
  var countrySelect = $('#country');
  var taxRateInput = $('#taxRate');
  var addTxBtn = $('#addTx');
  var txBody = $('#txBody');

  /* ---------- Theme ---------- */
  var savedTheme = localStorage.getItem('te_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);

  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme');
    var next = current === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('te_theme', next);
    updateChart();
  });

  /* ---------- Country ---------- */
  countrySelect.addEventListener('change', function () {
    var c = countrySelect.value;
    if (c !== 'custom') {
      taxRateInput.value = TAX_RATES[c].short;
    }
    recalculate();
  });
  taxRateInput.addEventListener('input', recalculate);

  /* ---------- Add Transaction ---------- */
  addTxBtn.addEventListener('click', function () {
    var asset = $('#txAsset').value.trim().toUpperCase();
    var buyPrice = parseFloat($('#txBuyPrice').value);
    var sellPrice = parseFloat($('#txSellPrice').value);
    var amount = parseFloat($('#txAmount').value);
    var date = $('#txDate').value;

    if (!asset || isNaN(buyPrice) || isNaN(sellPrice) || isNaN(amount)) return;

    transactions.push({
      id: Date.now(),
      asset: asset,
      buyPrice: buyPrice,
      sellPrice: sellPrice,
      amount: amount,
      date: date || new Date().toISOString().split('T')[0],
      gainLoss: (sellPrice - buyPrice) * amount
    });

    saveTxs();
    renderTable();
    recalculate();

    $('#txAsset').value = '';
    $('#txBuyPrice').value = '';
    $('#txSellPrice').value = '';
    $('#txAmount').value = '';
  });

  function saveTxs() {
    localStorage.setItem('te_txs', JSON.stringify(transactions));
  }

  /* ---------- Render Table ---------- */
  function renderTable() {
    if (transactions.length === 0) {
      txBody.innerHTML = '<tr class="table__empty"><td colspan="7">No transactions added</td></tr>';
      return;
    }
    txBody.innerHTML = transactions.map(function (tx) {
      var cls = tx.gainLoss >= 0 ? 'gain' : 'loss';
      var sign = tx.gainLoss >= 0 ? '+' : '';
      return '<tr>' +
        '<td>' + tx.asset + '</td>' +
        '<td>' + tx.amount + '</td>' +
        '<td>$' + tx.buyPrice.toLocaleString() + '</td>' +
        '<td>$' + tx.sellPrice.toLocaleString() + '</td>' +
        '<td class="' + cls + '">' + sign + '$' + tx.gainLoss.toFixed(2) + '</td>' +
        '<td>' + tx.date + '</td>' +
        '<td><button class="del-btn" data-id="' + tx.id + '">&#215;</button></td>' +
        '</tr>';
    }).join('');

    txBody.querySelectorAll('.del-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.dataset.id);
        transactions = transactions.filter(function (t) { return t.id !== id; });
        saveTxs();
        renderTable();
        recalculate();
      });
    });
  }

  /* ---------- Recalculate ---------- */
  function recalculate() {
    var totalGains = 0;
    var totalLosses = 0;

    transactions.forEach(function (tx) {
      if (tx.gainLoss >= 0) totalGains += tx.gainLoss;
      else totalLosses += Math.abs(tx.gainLoss);
    });

    var net = totalGains - totalLosses;
    var rate = parseFloat(taxRateInput.value) / 100;
    var tax = Math.max(0, net * rate);

    $('#kpiGains').textContent = '$' + totalGains.toFixed(2);
    $('#kpiLosses').textContent = '-$' + totalLosses.toFixed(2);
    $('#kpiNet').textContent = (net >= 0 ? '$' : '-$') + Math.abs(net).toFixed(2);
    $('#kpiTax').textContent = '$' + tax.toFixed(2);

    updateReport(totalGains, totalLosses, net, tax);
    updateChart();
  }

  /* ---------- Report ---------- */
  function updateReport(gains, losses, net, tax) {
    var grid = $('#reportGrid');
    if (transactions.length === 0) {
      grid.innerHTML = '<p class="report__empty">Add transactions to generate report</p>';
      return;
    }

    var keepAfterTax = Math.max(0, net - tax);
    var effectiveRate = net > 0 ? ((tax / net) * 100).toFixed(1) : '0.0';
    var assets = {};
    transactions.forEach(function (tx) {
      if (!assets[tx.asset]) assets[tx.asset] = 0;
      assets[tx.asset] += tx.gainLoss;
    });
    var topAsset = Object.keys(assets).sort(function (a, b) { return assets[b] - assets[a]; })[0] || '-';

    grid.innerHTML =
      '<div class="report__item"><span class="report__item-label">Total Transactions</span><span class="report__item-value">' + transactions.length + '</span></div>' +
      '<div class="report__item"><span class="report__item-label">Total Gains</span><span class="report__item-value" style="color:var(--gain)">$' + gains.toFixed(2) + '</span></div>' +
      '<div class="report__item"><span class="report__item-label">Total Losses</span><span class="report__item-value" style="color:var(--loss)">$' + losses.toFixed(2) + '</span></div>' +
      '<div class="report__item"><span class="report__item-label">Net Taxable</span><span class="report__item-value">$' + net.toFixed(2) + '</span></div>' +
      '<div class="report__item"><span class="report__item-label">Estimated Tax</span><span class="report__item-value" style="color:var(--accent)">$' + tax.toFixed(2) + '</span></div>' +
      '<div class="report__item"><span class="report__item-label">Effective Rate</span><span class="report__item-value">' + effectiveRate + '%</span></div>' +
      '<div class="report__item"><span class="report__item-label">Keep After Tax</span><span class="report__item-value">$' + keepAfterTax.toFixed(2) + '</span></div>' +
      '<div class="report__item"><span class="report__item-label">Top Asset</span><span class="report__item-value">' + topAsset + '</span></div>';
  }

  /* ---------- Chart ---------- */
  function updateChart() {
    if (typeof Chart === 'undefined') return;

    var totalGains = 0;
    var totalLosses = 0;
    transactions.forEach(function (tx) {
      if (tx.gainLoss >= 0) totalGains += tx.gainLoss;
      else totalLosses += Math.abs(tx.gainLoss);
    });

    var net = totalGains - totalLosses;
    var rate = parseFloat(taxRateInput.value) / 100;
    var tax = Math.max(0, net * rate);
    var keep = Math.max(0, net - tax);

    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var textColor = isDark ? '#ede6dc' : '#2c2418';

    if (taxChart) taxChart.destroy();

    taxChart = new Chart($('#taxChart'), {
      type: 'doughnut',
      data: {
        labels: ['Keep', 'Tax', 'Losses'],
        datasets: [{
          data: [keep, tax, totalLosses],
          backgroundColor: [
            isDark ? '#4ade80' : '#15803d',
            isDark ? '#ef4444' : '#b91c1c',
            isDark ? '#7a6e5e' : '#9a8d7f'
          ],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: textColor, font: { family: 'IBM Plex Mono', size: 11 } }
          }
        }
      }
    });
  }

  /* ---------- Init ---------- */
  renderTable();
  recalculate();

  /* ---------- GSAP ---------- */
  if (typeof gsap !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
    var mm = gsap.matchMedia();
    mm.add('(prefers-reduced-motion: no-preference)', function () {
      gsap.from('.hero__title', { scale: 0.95, opacity: 0, duration: 0.6, ease: 'power2.out' });
      gsap.from('.hero__subtitle', { scale: 0.95, opacity: 0, duration: 0.6, delay: 0.1, ease: 'power2.out' });
      gsap.from('.kpi', { scale: 0.95, opacity: 0, duration: 0.5, stagger: 0.08, delay: 0.2, ease: 'power2.out' });
      gsap.from('.settings', { scale: 0.95, opacity: 0, duration: 0.6, delay: 0.4, ease: 'power2.out' });
      gsap.from('.tx-form', {
        scale: 0.95, opacity: 0, duration: 0.6, ease: 'power2.out',
        scrollTrigger: { trigger: '.tx-form', start: 'top 85%' }
      });
      gsap.from('.tx-table', {
        scale: 0.95, opacity: 0, duration: 0.6, ease: 'power2.out',
        scrollTrigger: { trigger: '.tx-table', start: 'top 85%' }
      });
      gsap.from('.chart-section', {
        scale: 0.95, opacity: 0, duration: 0.6, ease: 'power2.out',
        scrollTrigger: { trigger: '.chart-section', start: 'top 85%' }
      });
      gsap.from('.report', {
        scale: 0.95, opacity: 0, duration: 0.6, ease: 'power2.out',
        scrollTrigger: { trigger: '.report', start: 'top 85%' }
      });
    });
  }
})();
