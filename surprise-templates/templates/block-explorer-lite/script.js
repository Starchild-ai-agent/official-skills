/* ============================================================
   Block Explorer Lite — script.js
   Skeleton: A6 Sidebar+Content · Hover: C7 边框发光
   Entrance: D4 stagger · Hero: H9 Tool Hero
   ============================================================ */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return document.querySelectorAll(s); };

  function rHex(len) {
    var r = '';
    for (var i = 0; i < len; i++) r += '0123456789abcdef'[Math.floor(Math.random() * 16)];
    return r;
  }
  function rAddr() { return '0x' + rHex(40); }
  function rHash() { return '0x' + rHex(64); }
  function rVal() { return (Math.random() * 10).toFixed(4); }
  function rBlock() { return Math.floor(18000000 + Math.random() * 500000); }
  function rTime() {
    var d = new Date(Date.now() - Math.floor(Math.random() * 3600000));
    return d.toLocaleTimeString();
  }

  /* ---------- Mock Data ---------- */
  var mockTxs = [];
  for (var i = 0; i < 20; i++) {
    mockTxs.push({
      hash: rHash(),
      from: rAddr(),
      to: rAddr(),
      value: rVal() + ' ETH',
      block: rBlock(),
      time: rTime(),
      gas: Math.floor(21000 + Math.random() * 100000),
      gasPrice: (Math.random() * 50 + 10).toFixed(2) + ' Gwei',
      status: Math.random() > 0.1 ? 'Success' : 'Failed',
      nonce: Math.floor(Math.random() * 1000)
    });
  }

  var mockAddresses = {};
  mockTxs.forEach(function (tx) {
    if (!mockAddresses[tx.from]) mockAddresses[tx.from] = { balance: (Math.random() * 100).toFixed(4) + ' ETH', txCount: 0 };
    if (!mockAddresses[tx.to]) mockAddresses[tx.to] = { balance: (Math.random() * 100).toFixed(4) + ' ETH', txCount: 0 };
    mockAddresses[tx.from].txCount++;
    mockAddresses[tx.to].txCount++;
  });

  /* ---------- Theme ---------- */
  var savedTheme = localStorage.getItem('be_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  $('#themeToggle').addEventListener('click', function () {
    var cur = document.documentElement.getAttribute('data-theme');
    var nxt = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nxt);
    localStorage.setItem('be_theme', nxt);
  });

  /* ---------- Sidebar Nav ---------- */
  $$('.sidebar__link').forEach(function (btn) {
    btn.addEventListener('click', function () {
      $$('.sidebar__link').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
    });
  });

  /* ---------- Render Tx List ---------- */
  function renderTxList() {
    var list = $('#txList');
    list.innerHTML = mockTxs.map(function (tx, i) {
      return '<div class="tx-item" data-idx="' + i + '">' +
        '<span class="tx-item__hash">' + tx.hash.slice(0, 18) + '...' + '</span>' +
        '<span class="tx-item__info">' + tx.from.slice(0, 10) + '... → ' + tx.to.slice(0, 10) + '...</span>' +
        '<span class="tx-item__value">' + tx.value + '</span>' +
        '</div>';
    }).join('');

    list.querySelectorAll('.tx-item').forEach(function (item) {
      item.addEventListener('click', function () {
        showDetail(mockTxs[parseInt(item.dataset.idx)]);
      });
    });
  }

  /* ---------- Search ---------- */
  function doSearch() {
    var q = $('#searchInput').value.trim().toLowerCase();
    if (!q) return;

    var results = $('#results');
    var card = $('#resultCard');

    // Check if it's an address
    if (q.length === 42 && q.startsWith('0x')) {
      var addr = mockAddresses[q] || { balance: (Math.random() * 50).toFixed(4) + ' ETH', txCount: Math.floor(Math.random() * 100) };
      card.innerHTML =
        '<div class="result-card__title">Address</div>' +
        '<div class="result-card__row"><span class="result-card__label">Address</span><span class="result-card__value">' + q + '</span></div>' +
        '<div class="result-card__row"><span class="result-card__label">Balance</span><span class="result-card__value result-card__value--accent">' + addr.balance + '</span></div>' +
        '<div class="result-card__row"><span class="result-card__label">Transactions</span><span class="result-card__value">' + addr.txCount + '</span></div>';
      results.style.display = 'block';
      return;
    }

    // Check if it's a tx hash
    if (q.length === 66 && q.startsWith('0x')) {
      var tx = mockTxs.find(function (t) { return t.hash.toLowerCase() === q; });
      if (!tx) tx = mockTxs[0]; // fallback to first
      showTxResult(card, tx);
      results.style.display = 'block';
      return;
    }

    // Fuzzy: show first matching tx
    var match = mockTxs.find(function (t) { return t.hash.includes(q) || t.from.includes(q) || t.to.includes(q); });
    if (match) {
      showTxResult(card, match);
      results.style.display = 'block';
    }
  }

  function showTxResult(card, tx) {
    card.innerHTML =
      '<div class="result-card__title">Transaction</div>' +
      '<div class="result-card__row"><span class="result-card__label">Hash</span><span class="result-card__value">' + tx.hash + '</span></div>' +
      '<div class="result-card__row"><span class="result-card__label">From</span><span class="result-card__value">' + tx.from + '</span></div>' +
      '<div class="result-card__row"><span class="result-card__label">To</span><span class="result-card__value">' + tx.to + '</span></div>' +
      '<div class="result-card__row"><span class="result-card__label">Value</span><span class="result-card__value result-card__value--accent">' + tx.value + '</span></div>' +
      '<div class="result-card__row"><span class="result-card__label">Status</span><span class="result-card__value">' + tx.status + '</span></div>';
  }

  $('#searchBtn').addEventListener('click', doSearch);
  $('#searchInput').addEventListener('keydown', function (e) { if (e.key === 'Enter') doSearch(); });

  /* ---------- Detail Panel ---------- */
  function showDetail(tx) {
    var panel = $('#detailPanel');
    var body = $('#detailBody');
    body.innerHTML =
      '<div class="detail-panel__row"><span class="detail-panel__label">Hash</span><span class="detail-panel__val">' + tx.hash + '</span></div>' +
      '<div class="detail-panel__row"><span class="detail-panel__label">Status</span><span class="detail-panel__val">' + tx.status + '</span></div>' +
      '<div class="detail-panel__row"><span class="detail-panel__label">Block</span><span class="detail-panel__val">' + tx.block + '</span></div>' +
      '<div class="detail-panel__row"><span class="detail-panel__label">Time</span><span class="detail-panel__val">' + tx.time + '</span></div>' +
      '<div class="detail-panel__row"><span class="detail-panel__label">From</span><span class="detail-panel__val">' + tx.from + '</span></div>' +
      '<div class="detail-panel__row"><span class="detail-panel__label">To</span><span class="detail-panel__val">' + tx.to + '</span></div>' +
      '<div class="detail-panel__row"><span class="detail-panel__label">Value</span><span class="detail-panel__val" style="color:var(--accent)">' + tx.value + '</span></div>' +
      '<div class="detail-panel__row"><span class="detail-panel__label">Gas Used</span><span class="detail-panel__val">' + tx.gas + '</span></div>' +
      '<div class="detail-panel__row"><span class="detail-panel__label">Gas Price</span><span class="detail-panel__val">' + tx.gasPrice + '</span></div>' +
      '<div class="detail-panel__row"><span class="detail-panel__label">Nonce</span><span class="detail-panel__val">' + tx.nonce + '</span></div>';
    panel.style.display = 'block';
  }

  $('#closeDetail').addEventListener('click', function () {
    $('#detailPanel').style.display = 'none';
  });

  /* ---------- Init ---------- */
  renderTxList();

  /* ---------- GSAP ---------- */
  if (typeof gsap !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
    var mm = gsap.matchMedia();
    mm.add('(prefers-reduced-motion: no-preference)', function () {
      gsap.from('.hero__title', { y: 30, opacity: 0, duration: 0.6, ease: 'power2.out' });
      gsap.from('.hero__sub', { y: 30, opacity: 0, duration: 0.6, delay: 0.1, ease: 'power2.out' });
      gsap.from('.search-bar', { y: 30, opacity: 0, duration: 0.6, delay: 0.2, ease: 'power2.out' });
      gsap.from('.tx-item', { y: 20, opacity: 0, duration: 0.4, stagger: 0.05, delay: 0.3, ease: 'power2.out' });
    });
  }
})();