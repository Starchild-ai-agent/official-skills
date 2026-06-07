/* ============================================================
   Smart Contract Reader — script.js
   Skeleton: A3 Split Screen · Hover: C15 左侧边框+背景
   Entrance: D7 translateX(-20px) · Hero: H7 Minimal
   ============================================================ */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return document.querySelectorAll(s); };

  var SAMPLE_ABI = [
    { type: 'function', name: 'transfer', stateMutability: 'nonpayable', inputs: [{ name: 'to', type: 'address' }, { name: 'amount', type: 'uint256' }], outputs: [{ name: '', type: 'bool' }] },
    { type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] },
    { type: 'function', name: 'approve', stateMutability: 'nonpayable', inputs: [{ name: 'spender', type: 'address' }, { name: 'amount', type: 'uint256' }], outputs: [{ name: '', type: 'bool' }] },
    { type: 'function', name: 'allowance', stateMutability: 'view', inputs: [{ name: 'owner', type: 'address' }, { name: 'spender', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] },
    { type: 'function', name: 'totalSupply', stateMutability: 'view', inputs: [], outputs: [{ name: '', type: 'uint256' }] },
    { type: 'function', name: 'name', stateMutability: 'view', inputs: [], outputs: [{ name: '', type: 'string' }] },
    { type: 'function', name: 'symbol', stateMutability: 'view', inputs: [], outputs: [{ name: '', type: 'string' }] },
    { type: 'function', name: 'decimals', stateMutability: 'view', inputs: [], outputs: [{ name: '', type: 'uint8' }] },
    { type: 'function', name: 'transferFrom', stateMutability: 'nonpayable', inputs: [{ name: 'from', type: 'address' }, { name: 'to', type: 'address' }, { name: 'amount', type: 'uint256' }], outputs: [{ name: '', type: 'bool' }] },
    { type: 'function', name: 'mint', stateMutability: 'nonpayable', inputs: [{ name: 'to', type: 'address' }, { name: 'amount', type: 'uint256' }], outputs: [] },
    { type: 'function', name: 'burn', stateMutability: 'nonpayable', inputs: [{ name: 'amount', type: 'uint256' }], outputs: [] },
    { type: 'event', name: 'Transfer', inputs: [{ name: 'from', type: 'address', indexed: true }, { name: 'to', type: 'address', indexed: true }, { name: 'value', type: 'uint256', indexed: false }] },
    { type: 'event', name: 'Approval', inputs: [{ name: 'owner', type: 'address', indexed: true }, { name: 'spender', type: 'address', indexed: true }, { name: 'value', type: 'uint256', indexed: false }] }
  ];

  var DESCRIPTIONS = {
    transfer: 'Transfer tokens from your account to another address',
    balanceOf: 'Get the token balance of a specific address',
    approve: 'Allow a spender to withdraw tokens from your account up to a limit',
    allowance: 'Check how many tokens a spender is allowed to withdraw',
    totalSupply: 'Get the total number of tokens in existence',
    name: 'Get the name of the token',
    symbol: 'Get the ticker symbol of the token',
    decimals: 'Get the number of decimal places the token uses',
    transferFrom: 'Transfer tokens from one address to another using allowance',
    mint: 'Create new tokens and assign them to an address',
    burn: 'Destroy tokens from your account permanently',
    Transfer: 'Emitted when tokens are transferred between addresses',
    Approval: 'Emitted when an approval is granted to a spender'
  };

  var parsedAbi = [];
  var currentFilter = 'all';

  /* ---------- Theme ---------- */
  var savedTheme = localStorage.getItem('cr_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  $('#themeToggle').addEventListener('click', function () {
    var cur = document.documentElement.getAttribute('data-theme');
    var nxt = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nxt);
    localStorage.setItem('cr_theme', nxt);
  });

  /* ---------- Parse ---------- */
  function parseAbi() {
    var raw = $('#abiJson').value.trim();
    if (!raw) return;
    try {
      parsedAbi = JSON.parse(raw);
      if (!Array.isArray(parsedAbi)) parsedAbi = [parsedAbi];
      $('#filterBar').style.display = 'flex';
      renderFunctions();
    } catch (e) {
      $('#fnList').innerHTML = '<div class="fn-list__empty" style="color:var(--accent)">Invalid JSON: ' + e.message + '</div>';
    }
  }

  function classifyFn(item) {
    if (item.type === 'event') return 'event';
    if (item.stateMutability === 'view' || item.stateMutability === 'pure') return 'read';
    return 'write';
  }

  function renderFunctions() {
    var list = $('#fnList');
    var filtered = parsedAbi.filter(function (item) {
      if (item.type !== 'function' && item.type !== 'event') return false;
      if (currentFilter === 'all') return true;
      return classifyFn(item) === currentFilter;
    });

    if (filtered.length === 0) {
      list.innerHTML = '<div class="fn-list__empty">No matching functions found</div>';
      return;
    }

    list.innerHTML = filtered.map(function (item) {
      var cat = classifyFn(item);
      var desc = DESCRIPTIONS[item.name] || 'No description available';
      var inputs = (item.inputs || []).map(function (inp) {
        return '<div class="fn-card__param"><span class="fn-card__param-name">' + (inp.name || '_') + '</span><span class="fn-card__param-type">' + inp.type + '</span></div>';
      }).join('');
      var outputs = '';
      if (item.outputs && item.outputs.length > 0) {
        outputs = '<div class="fn-card__outputs"><div class="fn-card__outputs-label">Returns</div>' +
          item.outputs.map(function (o) {
            return '<div class="fn-card__param"><span class="fn-card__param-name">' + (o.name || '_') + '</span><span class="fn-card__param-type">' + o.type + '</span></div>';
          }).join('') + '</div>';
      }
      return '<div class="fn-card">' +
        '<div class="fn-card__header"><span class="fn-card__name">' + item.name + '</span><span class="fn-card__badge fn-card__badge--' + cat + '">' + cat + '</span></div>' +
        '<div class="fn-card__desc">' + desc + '</div>' +
        (inputs ? '<div class="fn-card__params">' + inputs + '</div>' : '') +
        outputs +
        '</div>';
    }).join('');

    // GSAP entrance
    if (typeof gsap !== 'undefined') {
      var mm = gsap.matchMedia();
      mm.add('(prefers-reduced-motion: no-preference)', function () {
        gsap.from('.fn-card', { x: -20, opacity: 0, duration: 0.4, stagger: 0.05, ease: 'power2.out' });
      });
    }
  }

  /* ---------- Events ---------- */
  $('#parseBtn').addEventListener('click', parseAbi);
  $('#sampleBtn').addEventListener('click', function () {
    $('#abiJson').value = JSON.stringify(SAMPLE_ABI, null, 2);
    parseAbi();
  });
  $('#clearBtn').addEventListener('click', function () {
    $('#abiJson').value = '';
    parsedAbi = [];
    $('#fnList').innerHTML = '<div class="fn-list__empty">Paste an ABI JSON to see contract functions</div>';
    $('#filterBar').style.display = 'none';
  });

  $$('.filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      $$('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      renderFunctions();
    });
  });

  /* ---------- GSAP Init ---------- */
  if (typeof gsap !== 'undefined') {
    var mm = gsap.matchMedia();
    mm.add('(prefers-reduced-motion: no-preference)', function () {
      gsap.from('.hero__title', { x: -20, opacity: 0, duration: 0.6, ease: 'power2.out' });
      gsap.from('.hero__sub', { x: -20, opacity: 0, duration: 0.6, delay: 0.1, ease: 'power2.out' });
      gsap.from('.abi-input', { x: -20, opacity: 0, duration: 0.6, delay: 0.2, ease: 'power2.out' });
    });
  }
})();
