/* ============================================================
   Smart Contract Security Scanner — script.js

   Pure frontend with built-in simulated vulnerability data.
   Renders vulnerability list, security checklist, distribution
   doughnut chart, and common pattern reference cards.

   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var CONFIG = {
    heroImageUrl: (function () {
      var raw = '{{HERO_IMAGE_URL}}';
      if (raw.startsWith('{{')) return '';
      return raw;
    })(),
    contractAddress: (function () {
      var raw = '{{CONTRACT_ADDRESS}}';
      if (raw.startsWith('{{')) return '0x1234...abcd';
      return raw;
    })(),
  };

  /* ---------- Simulated Vulnerability Data ---------- */
  var VULNERABILITIES = [
    {
      severity: 'critical',
      type: 'Reentrancy',
      location: 'withdraw() — Line 42',
      title: 'Reentrancy Attack Vector',
      desc: 'The withdraw function sends ETH before updating the user balance, allowing an attacker to recursively call withdraw and drain the contract.',
      fix: 'Move the balance update before the external call, or use ReentrancyGuard from OpenZeppelin.',
    },
    {
      severity: 'critical',
      type: 'Access Control',
      location: 'setAdmin() — Line 18',
      title: 'Missing Access Control on Admin Setter',
      desc: 'The setAdmin function has no access modifier, allowing any address to grant themselves admin privileges.',
      fix: 'Add onlyOwner modifier or use AccessControl from OpenZeppelin.',
    },
    {
      severity: 'high',
      type: 'Integer Overflow',
      location: 'transfer() — Line 67',
      title: 'Unchecked Arithmetic in Token Transfer',
      desc: 'The transfer function performs arithmetic without overflow checks. In Solidity <0.8.0, this can lead to integer overflow/underflow.',
      fix: 'Use Solidity >=0.8.0 (built-in overflow checks) or SafeMath library.',
    },
    {
      severity: 'high',
      type: 'Front-Running',
      location: 'swap() — Line 103',
      title: 'Front-Running Vulnerability in Swap',
      desc: 'The swap function has no slippage protection, allowing MEV bots to sandwich attack user transactions.',
      fix: 'Add a minAmountOut parameter and deadline check to prevent sandwich attacks.',
    },
    {
      severity: 'medium',
      type: 'Timestamp Dependence',
      location: 'claimReward() — Line 89',
      title: 'Block Timestamp Manipulation',
      desc: 'The reward claim uses block.timestamp for time-based logic. Miners can manipulate timestamps within ~15 seconds.',
      fix: 'Use block.number instead of block.timestamp for time-sensitive operations, or accept the ~15s variance.',
    },
    {
      severity: 'medium',
      type: 'Denial of Service',
      location: 'distributeRewards() — Line 134',
      title: 'Unbounded Loop in Reward Distribution',
      desc: 'The function iterates over all stakers in a single transaction. If the array grows too large, the function will exceed the gas limit.',
      fix: 'Implement a pull-based reward pattern instead of push-based distribution.',
    },
    {
      severity: 'medium',
      type: 'Centralization Risk',
      location: 'pause() — Line 12',
      title: 'Single Admin Can Pause All Operations',
      desc: 'A single admin address can pause the entire contract, creating a centralization risk and single point of failure.',
      fix: 'Implement a multi-sig requirement or timelock for critical admin functions.',
    },
    {
      severity: 'low',
      type: 'Gas Optimization',
      location: 'Multiple locations',
      title: 'Inefficient Storage Reads',
      desc: 'Multiple functions read the same storage variable multiple times within a single call, wasting gas.',
      fix: 'Cache storage variables in memory at the start of functions.',
    },
    {
      severity: 'low',
      type: 'Code Quality',
      location: 'Global',
      title: 'Missing Event Emissions',
      desc: 'Several state-changing functions do not emit events, making it difficult to track contract activity off-chain.',
      fix: 'Add event definitions and emit them in all state-changing functions.',
    },
    {
      severity: 'low',
      type: 'Documentation',
      location: 'Global',
      title: 'Insufficient NatSpec Documentation',
      desc: 'Most functions lack NatSpec comments, making the contract harder to audit and understand.',
      fix: 'Add @notice, @param, and @return NatSpec comments to all public/external functions.',
    },
  ];

  /* ---------- Security Checklist ---------- */
  var CHECKLIST = [
    { name: 'Reentrancy Protection', pass: false },
    { name: 'Access Control on Admin Functions', pass: false },
    { name: 'Integer Overflow/Underflow Protection', pass: false },
    { name: 'Front-Running Mitigation', pass: false },
    { name: 'Input Validation', pass: true },
    { name: 'Event Emission on State Changes', pass: false },
    { name: 'Proper Use of msg.sender', pass: true },
    { name: 'No tx.origin Authentication', pass: true },
    { name: 'Fallback/Receive Function Safety', pass: true },
    { name: 'ERC-20 Return Value Checks', pass: true },
    { name: 'Upgradability Pattern Safety', pass: true },
    { name: 'Oracle Manipulation Protection', pass: true },
    { name: 'Flash Loan Attack Resistance', pass: false },
    { name: 'Proper Initialization (no uninitialized proxies)', pass: true },
    { name: 'Gas Limit DoS Prevention', pass: false },
    { name: 'Compiler Version Pinned', pass: true },
    { name: 'License Identifier Present', pass: true },
  ];

  /* ---------- Common Vulnerability Patterns ---------- */
  var PATTERNS = [
    {
      name: 'Reentrancy',
      severity: 'critical',
      desc: 'Occurs when a contract makes an external call before updating its state, allowing the called contract to re-enter and exploit the stale state.',
      badCode: '// VULNERABLE\nfunction withdraw() external {\n  uint amount = balances[msg.sender];\n  (bool ok, ) = msg.sender.call{value: amount}("");\n  require(ok);\n  balances[msg.sender] = 0; // Too late!\n}',
      goodCode: '// FIXED\nfunction withdraw() external nonReentrant {\n  uint amount = balances[msg.sender];\n  balances[msg.sender] = 0; // Update first\n  (bool ok, ) = msg.sender.call{value: amount}("");\n  require(ok);\n}',
    },
    {
      name: 'Access Control',
      severity: 'critical',
      desc: 'Missing or incorrect access control allows unauthorized users to call privileged functions like minting tokens or changing ownership.',
      badCode: '// VULNERABLE\nfunction mint(address to, uint amount) external {\n  _mint(to, amount); // Anyone can mint!\n}',
      goodCode: '// FIXED\nfunction mint(address to, uint amount) external onlyRole(MINTER_ROLE) {\n  _mint(to, amount);\n}',
    },
    {
      name: 'Integer Overflow',
      severity: 'high',
      desc: 'In Solidity <0.8.0, arithmetic operations can silently overflow or underflow, leading to unexpected behavior and potential fund loss.',
      badCode: '// VULNERABLE (Solidity <0.8)\nuint8 balance = 255;\nbalance += 1; // Wraps to 0!',
      goodCode: '// FIXED — Use Solidity >=0.8.0\npragma solidity ^0.8.0;\n// Built-in overflow checks\nuint8 balance = 255;\nbalance += 1; // Reverts!',
    },
    {
      name: 'Front-Running / MEV',
      severity: 'high',
      desc: 'Transactions in the mempool are visible to everyone. Attackers can insert transactions before or after yours to extract value (sandwich attacks).',
      badCode: '// VULNERABLE\nfunction swap(uint amountIn) external {\n  uint amountOut = getPrice(amountIn);\n  token.transfer(msg.sender, amountOut);\n  // No slippage protection!\n}',
      goodCode: '// FIXED\nfunction swap(\n  uint amountIn,\n  uint minAmountOut,\n  uint deadline\n) external {\n  require(block.timestamp <= deadline);\n  uint amountOut = getPrice(amountIn);\n  require(amountOut >= minAmountOut);\n  token.transfer(msg.sender, amountOut);\n}',
    },
    {
      name: 'Denial of Service',
      severity: 'medium',
      desc: 'Unbounded loops or external calls in loops can cause transactions to exceed the gas limit, permanently blocking contract functionality.',
      badCode: '// VULNERABLE\nfunction distributeRewards() external {\n  for (uint i = 0; i < stakers.length; i++) {\n    payable(stakers[i]).transfer(rewards[i]);\n    // Fails if array is too large\n  }\n}',
      goodCode: '// FIXED — Pull pattern\nmapping(address => uint) public pendingRewards;\n\nfunction claimReward() external {\n  uint reward = pendingRewards[msg.sender];\n  pendingRewards[msg.sender] = 0;\n  payable(msg.sender).transfer(reward);\n}',
    },
    {
      name: 'Unchecked Return Values',
      severity: 'medium',
      desc: 'Some ERC-20 tokens do not revert on failure but return false. Not checking the return value can lead to silent failures.',
      badCode: '// VULNERABLE\ntoken.transfer(to, amount);\n// Ignores return value!',
      goodCode: '// FIXED — Use SafeERC20\nimport "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";\nusing SafeERC20 for IERC20;\n\ntoken.safeTransfer(to, amount);',
    },
  ];

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return Array.from(document.querySelectorAll(sel)); };

  var els = {
    themeToggle: $('#theme-toggle'),
    heroTime: $('#hero-time'),
    heroBgImage: $('.hero__bg-image'),
    heroAddress: $('#hero-address'),
    statScore: $('#stat-score'),
    statCritical: $('#stat-critical'),
    statHigh: $('#stat-high'),
    statMedium: $('#stat-medium'),
    statLow: $('#stat-low'),
    vulnsList: $('#vulns-list'),
    checklist: $('#checklist'),
    distChartContainer: $('#dist-chart-container'),
    distSkeleton: $('#dist-skeleton'),
    distChart: $('#dist-chart'),
    distLegend: $('#dist-legend'),
    patternsGrid: $('#patterns-grid'),
    footerTime: $('#footer-time'),
  };

  /* ---------- Theme ---------- */
  function initTheme() {
    var saved = localStorage.getItem('smart-contract-scanner-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    }
    els.themeToggle.addEventListener('click', function () {
      var current = document.documentElement.getAttribute('data-theme');
      var next = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('smart-contract-scanner-theme', next);
    });
  }

  /* ---------- Clock ---------- */
  function updateClock() {
    var now = new Date();
    var str = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    els.heroTime.textContent = str;
    els.heroTime.setAttribute('datetime', now.toISOString());
    els.footerTime.textContent = now.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  /* ---------- Hero Image ---------- */
  function initHeroImage() {
    if (CONFIG.heroImageUrl) {
      els.heroBgImage.style.backgroundImage = 'url(' + CONFIG.heroImageUrl + ')';
    }
  }

  /* ---------- Compute Stats ---------- */
  function computeStats() {
    var counts = { critical: 0, high: 0, medium: 0, low: 0 };
    VULNERABILITIES.forEach(function (v) { counts[v.severity]++; });

    // Security score: start at 100, deduct per severity
    var score = 100 - (counts.critical * 25) - (counts.high * 15) - (counts.medium * 5) - (counts.low * 2);
    score = Math.max(0, Math.min(100, score));

    return { score: score, counts: counts };
  }

  /* ---------- Render Hero Stats + Score Ring ---------- */
  function renderHeroStats(stats) {
    els.statScore.textContent = stats.score + '/100';

    /* Animate score ring (H15) */
    var ringFill = document.getElementById('score-ring-fill');
    if (ringFill) {
      var circumference = 2 * Math.PI * 52; /* r=52 */
      var offset = circumference - (stats.score / 100) * circumference;
      /* Set color based on score */
      if (stats.score >= 80) {
        ringFill.style.stroke = 'var(--color-pass)';
      } else if (stats.score >= 50) {
        ringFill.style.stroke = 'var(--color-medium)';
      } else {
        ringFill.style.stroke = 'var(--color-accent)';
      }
      requestAnimationFrame(function () {
        ringFill.style.strokeDashoffset = offset;
      });
    }
    els.statCritical.textContent = stats.counts.critical;
    els.statHigh.textContent = stats.counts.high;
    els.statMedium.textContent = stats.counts.medium;
    els.statLow.textContent = stats.counts.low;
  }

  /* ---------- Render Vulnerabilities ---------- */
  function renderVulns() {
    var sorted = VULNERABILITIES.slice().sort(function (a, b) {
      var order = { critical: 0, high: 1, medium: 2, low: 3 };
      return order[a.severity] - order[b.severity];
    });

    els.vulnsList.innerHTML = sorted.map(function (v) {
      return '<article class="vuln-item vuln-item--' + v.severity + '">' +
        '<div class="vuln-item__header">' +
          '<span class="vuln-item__severity vuln-item__severity--' + v.severity + '">' + v.severity + '</span>' +
          '<span class="vuln-item__type">' + v.type + '</span>' +
          '<span class="vuln-item__location">' + v.location + '</span>' +
        '</div>' +
        '<h3 class="vuln-item__title">' + v.title + '</h3>' +
        '<p class="vuln-item__desc">' + v.desc + '</p>' +
        '<div class="vuln-item__fix">' +
          '<div class="vuln-item__fix-label">Recommendation</div>' +
          '<div class="vuln-item__fix-text">' + v.fix + '</div>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  /* ---------- Render Checklist ---------- */
  function renderChecklist() {
    els.checklist.innerHTML = CHECKLIST.map(function (c) {
      var icon = c.pass ? '&#10003;' : '&#10007;';
      var iconClass = c.pass ? 'check-item__icon--pass' : 'check-item__icon--fail';
      var statusClass = c.pass ? 'check-item__status--pass' : 'check-item__status--fail';
      var statusText = c.pass ? 'PASS' : 'FAIL';
      return '<div class="check-item">' +
        '<span class="check-item__icon ' + iconClass + '">' + icon + '</span>' +
        '<span class="check-item__name">' + c.name + '</span>' +
        '<span class="check-item__status ' + statusClass + '">' + statusText + '</span>' +
      '</div>';
    }).join('');
  }

  /* ---------- Distribution Chart ---------- */
  function renderDistChart() {
    els.distSkeleton.remove();

    // Count by type
    var typeMap = {};
    VULNERABILITIES.forEach(function (v) {
      typeMap[v.type] = (typeMap[v.type] || 0) + 1;
    });
    var entries = Object.entries(typeMap).sort(function (a, b) { return b[1] - a[1]; });

    var labels = entries.map(function (e) { return e[0]; });
    var data = entries.map(function (e) { return e[1]; });
    var colors = [
      '#ef4444', '#f97316', '#eab308', '#38bdf8',
      '#a855f7', '#ec4899', '#14b8a6', '#6366f1',
      '#84cc16', '#f43f5e',
    ];

    new Chart(els.distChart, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors.slice(0, labels.length),
          borderColor: 'transparent',
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            titleFont: { family: "'Azeret Mono', monospace", size: 12 },
            bodyFont: { family: "'Lexend', sans-serif", size: 13 },
            padding: 10,
            cornerRadius: 6,
          },
        },
      },
    });

    // Legend
    els.distLegend.innerHTML = entries.map(function (e, i) {
      return '<div class="dist-legend__item">' +
        '<span class="dist-legend__dot" style="background:' + colors[i] + '"></span>' +
        '<span class="dist-legend__name">' + e[0] + '</span>' +
        '<span class="dist-legend__count">' + e[1] + '</span>' +
      '</div>';
    }).join('');
  }

  /* ---------- Render Patterns ---------- */
  function renderPatterns() {
    els.patternsGrid.innerHTML = PATTERNS.map(function (p) {
      var sevColor = {
        critical: 'background:rgba(239,68,68,0.15);color:var(--color-critical)',
        high: 'background:rgba(249,115,22,0.15);color:var(--color-high)',
        medium: 'background:rgba(234,179,8,0.15);color:var(--color-medium)',
      };
      return '<article class="pattern-card">' +
        '<div class="pattern-card__header">' +
          '<span class="pattern-card__severity" style="' + (sevColor[p.severity] || '') + '">' + p.severity + '</span>' +
          '<span class="pattern-card__name">' + p.name + '</span>' +
        '</div>' +
        '<p class="pattern-card__desc">' + p.desc + '</p>' +
        '<div class="pattern-card__code">' +
          '<div class="pattern-card__code-label pattern-card__code-label--bad">Vulnerable</div>' +
          '<pre>' + escapeHtml(p.badCode) + '</pre>' +
        '</div>' +
        '<div class="pattern-card__code">' +
          '<div class="pattern-card__code-label pattern-card__code-label--good">Fixed</div>' +
          '<pre>' + escapeHtml(p.goodCode) + '</pre>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ---------- GSAP Animations — D10: translateX(-50px) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero entrance from left */
    gsap.from('.hero__content', {
      x: -50, opacity: 0, duration: 1, ease: 'power3.out',
    });
    gsap.from('.hero__score-row', {
      x: -50, opacity: 0, duration: 0.8, delay: 0.3, ease: 'power3.out',
    });

    /* D10: Sections slide from left */
    $$('.section').forEach(function (section) {
      var title = section.querySelector('.section__title');
      if (title) {
        gsap.from(title, {
          scrollTrigger: { trigger: section, start: 'top 80%', once: true },
          x: -50, opacity: 0, duration: 0.8, ease: 'power3.out',
        });
      }
      var desc = section.querySelector('.section__desc');
      if (desc) {
        gsap.from(desc, {
          scrollTrigger: { trigger: section, start: 'top 80%', once: true },
          x: -50, opacity: 0, duration: 0.8, delay: 0.1, ease: 'power3.out',
        });
      }
    });

    setTimeout(function () {
      /* D10: Checklist items from left */
      $$('.check-item').forEach(function (item, i) {
        gsap.from(item, {
          scrollTrigger: { trigger: item, start: 'top 90%', once: true },
          x: -50, opacity: 0, duration: 0.4, delay: i * 0.03, ease: 'power2.out',
        });
      });

      /* D10: Vuln items from left */
      $$('.vuln-item').forEach(function (card, i) {
        gsap.from(card, {
          scrollTrigger: { trigger: card, start: 'top 85%', once: true },
          x: -50, opacity: 0, duration: 0.6, delay: i * 0.06, ease: 'power3.out',
        });
      });

      /* D10: Pattern cards from left */
      $$('.pattern-card').forEach(function (card, i) {
        gsap.from(card, {
          scrollTrigger: { trigger: card, start: 'top 85%', once: true },
          x: -50, opacity: 0, duration: 0.6, delay: i * 0.08, ease: 'power3.out',
        });
      });
    }, 200);
  }

  /* ---------- Init ---------- */
  function init() {
    initTheme();
    initHeroImage();
    updateClock();
    setInterval(updateClock, 1000);

    var stats = computeStats();
    renderHeroStats(stats);
    renderVulns();
    renderChecklist();
    renderDistChart();
    renderPatterns();

    initAnimations();
    setTimeout(function () { ScrollTrigger.refresh(); }, 300);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
