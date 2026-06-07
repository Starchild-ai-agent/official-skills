/* ============================================================
   Gas Optimization Cheatsheet — script.js

   Skeleton: A15 Checklist
   Hover: C29 background rgba
   Entrance: D10 translateX(-50px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Data ---------- */
  var CHECKLIST = [
    { title: 'Use calldata instead of memory for read-only args', hint: 'Function parameters that are not modified should use calldata', gas: '-200 per call', category: 'memory' },
    { title: 'Pack storage variables', hint: 'Group uint128, uint64, bool together to share a single 32-byte slot', gas: '-20,000 SSTORE', category: 'storage' },
    { title: 'Use uint256 instead of smaller uints in storage', hint: 'EVM operates on 32 bytes; smaller types require extra masking operations', gas: '-3 per operation', category: 'types' },
    { title: 'Cache storage variables in memory', hint: 'Read storage once into a local variable instead of multiple SLOADs', gas: '-100 per SLOAD saved', category: 'storage' },
    { title: 'Use unchecked for safe arithmetic', hint: 'Skip overflow checks when you know values cannot overflow (e.g., loop counters)', gas: '-30-80 per operation', category: 'loops' },
    { title: 'Use ++i instead of i++', hint: 'Pre-increment avoids a temporary copy in older Solidity versions', gas: '-5 per iteration', category: 'loops' },
    { title: 'Short-circuit conditions', hint: 'Put cheaper checks first in require/if statements with &&', gas: '-200+ on failure', category: 'memory' },
    { title: 'Use immutable for constructor-set values', hint: 'Immutable variables are embedded in bytecode, no SLOAD needed', gas: '-2,100 per read', category: 'storage' },
    { title: 'Use custom errors instead of revert strings', hint: 'Custom errors are cheaper than string-based revert messages', gas: '-50+ per revert', category: 'types' },
    { title: 'Avoid redundant zero-initialization', hint: 'uint256 x = 0 wastes gas; default is already zero', gas: '-3 per variable', category: 'types' },
    { title: 'Use mapping instead of array for lookups', hint: 'Mapping provides O(1) access vs O(n) array iteration', gas: '-5,000+ for large sets', category: 'storage' },
    { title: 'Batch operations in a single transaction', hint: 'Reduce base transaction cost (21,000 gas) by batching multiple operations', gas: '-21,000 per batch', category: 'loops' },
  ];

  var CODE_DIFFS = [
    {
      title: 'Storage Packing',
      savings: 'Saves ~20,000 gas',
      old: '// Unoptimized: 3 storage slots\ncontract Bad {\n  uint256 a;  // slot 0\n  bool b;     // slot 1\n  uint256 c;  // slot 2\n}',
      new: '// Optimized: 2 storage slots\ncontract Good {\n  uint256 a;  // slot 0\n  uint256 c;  // slot 1\n  bool b;     // packed in slot 1\n}',
    },
    {
      title: 'Unchecked Loop Counter',
      savings: 'Saves ~30 gas/iteration',
      old: '// Unoptimized\nfor (uint i = 0; i < len; i++) {\n  // overflow check on every\n  // increment is unnecessary\n  // when i < len is guaranteed\n  sum += arr[i];\n}',
      new: '// Optimized\nfor (uint i = 0; i < len;) {\n  sum += arr[i];\n  unchecked { ++i; }\n  // Safe: i < len prevents\n  // overflow, pre-increment\n  // is cheaper\n}',
    },
    {
      title: 'Custom Errors',
      savings: 'Saves ~50 gas per revert',
      old: '// Unoptimized: string storage\nrequire(\n  msg.sender == owner,\n  "Only owner can call"\n);\nrequire(\n  amount > 0,\n  "Amount must be positive"\n);',
      new: '// Optimized: custom errors\nerror NotOwner();\nerror ZeroAmount();\n\nif (msg.sender != owner)\n  revert NotOwner();\nif (amount == 0)\n  revert ZeroAmount();',
    },
    {
      title: 'Calldata vs Memory',
      savings: 'Saves ~200 gas per call',
      old: '// Unoptimized: copies to memory\nfunction process(\n  uint[] memory data\n) external {\n  // data is copied from\n  // calldata to memory\n  for (uint i; i < data.length;)\n    total += data[i];\n}',
      new: '// Optimized: reads from calldata\nfunction process(\n  uint[] calldata data\n) external {\n  // data stays in calldata\n  // no copy needed\n  for (uint i; i < data.length;)\n    total += data[i];\n}',
    },
  ];

  var VERSIONS = [
    { version: '0.8.24+', title: 'Transient Storage (EIP-1153)', desc: 'TSTORE/TLOAD opcodes for cheap temporary storage that resets after each transaction. Great for reentrancy locks.' },
    { version: '0.8.20+', title: 'Shanghai/Push0 Opcode', desc: 'PUSH0 opcode replaces PUSH1 0x00, saving 3 gas per zero-push. Compiler uses it automatically.' },
    { version: '0.8.19+', title: 'Improved Custom Error ABI', desc: 'Custom errors with parameters are now more gas-efficient in encoding.' },
    { version: '0.8.13+', title: 'Optimized Yul IR Pipeline', desc: 'New IR-based code generation produces more optimized bytecode for complex contracts.' },
    { version: '0.8.8+', title: 'Override Without Listing', desc: 'No need to list all parent contracts in override keyword, reducing bytecode size.' },
  ];

  var currentCat = 'all';

  /* ---------- Theme ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('go-theme', theme);
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'dark';
    setTheme(current === 'dark' ? 'light' : 'dark');
  });
  var savedTheme = localStorage.getItem('go-theme') ||
    (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  setTheme(savedTheme);

  /* ---------- Estimator ---------- */
  function updateEstimator() {
    var calls = parseInt(document.getElementById('est-calls').value) || 0;
    var gasSaved = parseInt(document.getElementById('est-gas-saved').value) || 0;
    var gasPrice = parseFloat(document.getElementById('est-gas-price').value) || 0;

    var dailyGas = calls * gasSaved;
    var dailyEth = (dailyGas * gasPrice) / 1e9;
    var monthlyEth = dailyEth * 30;

    document.getElementById('est-daily').textContent = dailyEth.toFixed(4) + ' ETH';
    document.getElementById('est-monthly').textContent = monthlyEth.toFixed(3) + ' ETH';
  }

  document.getElementById('est-calls').addEventListener('input', updateEstimator);
  document.getElementById('est-gas-saved').addEventListener('input', updateEstimator);
  document.getElementById('est-gas-price').addEventListener('input', updateEstimator);
  updateEstimator();

  /* ---------- Checklist Categories ---------- */
  document.querySelectorAll('.check-cat').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.check-cat').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentCat = btn.getAttribute('data-cat');
      renderChecklist();
    });
  });

  /* ---------- Render Checklist ---------- */
  function renderChecklist() {
    var list = document.getElementById('checklist-list');
    var items = currentCat === 'all' ? CHECKLIST : CHECKLIST.filter(function (c) { return c.category === currentCat; });

    var html = '';
    items.forEach(function (item, i) {
      html += '<div class="check-item" data-index="' + i + '">' +
        '<div class="check-item__box">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' +
        '</div>' +
        '<div class="check-item__content">' +
        '<div class="check-item__title">' + item.title + '</div>' +
        '<div class="check-item__hint">' + item.hint + '</div>' +
        '</div>' +
        '<div class="check-item__gas">' + item.gas + '</div>' +
        '</div>';
    });
    list.innerHTML = html;

    list.querySelectorAll('.check-item').forEach(function (el) {
      el.addEventListener('click', function () {
        el.classList.toggle('checked');
      });
    });

    if (!prefersReducedMotion) {
      gsap.utils.toArray('.check-item').forEach(function (el, i) {
        gsap.from(el, {
          scrollTrigger: { trigger: el, start: 'top 92%', toggleActions: 'play none none none' },
          opacity: 0, x: -50, duration: 0.4, delay: i * 0.04, ease: 'power2.out',
        });
      });
    }
  }

  /* ---------- Render Code Diffs ---------- */
  function renderCodeDiffs() {
    var container = document.getElementById('code-diffs');
    var html = '';
    CODE_DIFFS.forEach(function (diff) {
      html += '<div class="code-diff">' +
        '<div class="code-diff__header">' +
        '<span>' + diff.title + '</span>' +
        '<span class="code-diff__savings">' + diff.savings + '</span>' +
        '</div>' +
        '<div class="code-diff__panels">' +
        '<div class="code-diff__panel code-diff__panel--old">' +
        '<div class="code-diff__panel-label">Before</div>' +
        '<code>' + escapeHtml(diff.old) + '</code></div>' +
        '<div class="code-diff__panel code-diff__panel--new">' +
        '<div class="code-diff__panel-label">After</div>' +
        '<code>' + escapeHtml(diff.new) + '</code></div>' +
        '</div></div>';
    });
    container.innerHTML = html;
  }

  /* ---------- Render Versions ---------- */
  function renderVersions() {
    var list = document.getElementById('version-list');
    var html = '';
    VERSIONS.forEach(function (v) {
      html += '<div class="version-item">' +
        '<div class="version-item__version">Solidity ' + v.version + '</div>' +
        '<div class="version-item__title">' + v.title + '</div>' +
        '<div class="version-item__desc">' + v.desc + '</div>' +
        '</div>';
    });
    list.innerHTML = html;
  }

  /* ---------- Utility ---------- */
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------- GSAP Animations (D10 translateX(-50px)) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.terminal-hero', { opacity: 0, x: -50, duration: 0.7, ease: 'power3.out' });

    gsap.from('.estimator-card', {
      scrollTrigger: { trigger: '.estimator-card', start: 'top 85%' },
      opacity: 0, x: -50, duration: 0.7, ease: 'power2.out',
    });

    gsap.utils.toArray('.code-diff').forEach(function (el, i) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 85%' },
        opacity: 0, x: -50, duration: 0.6, delay: i * 0.1, ease: 'power2.out',
      });
    });

    gsap.utils.toArray('.version-item').forEach(function (el, i) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 90%' },
        opacity: 0, x: -50, duration: 0.5, delay: i * 0.06, ease: 'power2.out',
      });
    });

    gsap.utils.toArray('.section__title').forEach(function (el) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%' },
        opacity: 0, x: -30, duration: 0.6, ease: 'power3.out',
      });
    });
  }

  /* ---------- Init ---------- */
  renderChecklist();
  renderCodeDiffs();
  renderVersions();
  initAnimations();

})();
