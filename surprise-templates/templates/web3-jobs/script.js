/* ============================================================
   Web3 Job Board — script.js

   Skeleton: A7 Table-First
   Hover: C19 背景渐变
   Entrance: D9 scale(0.95)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Mock Data ---------- */
  var JOBS = [
    { role: 'Senior Solidity Engineer', company: 'Uniswap Labs', salary: '$180k-$250k', stack: ['Solidity', 'TypeScript', 'Hardhat'], chain: 'ethereum', type: 'remote', match: 92 },
    { role: 'Rust Protocol Developer', company: 'Solana Foundation', salary: '$160k-$220k', stack: ['Rust', 'Anchor', 'TypeScript'], chain: 'solana', type: 'remote', match: 85 },
    { role: 'Smart Contract Auditor', company: 'OpenZeppelin', salary: '$200k-$300k', stack: ['Solidity', 'Vyper', 'Foundry'], chain: 'ethereum', type: 'remote', match: 78 },
    { role: 'Full Stack Web3 Dev', company: 'Aave', salary: '$150k-$200k', stack: ['React', 'Solidity', 'The Graph'], chain: 'ethereum', type: 'hybrid', match: 88 },
    { role: 'ZK Engineer', company: 'Polygon Labs', salary: '$190k-$280k', stack: ['Rust', 'Circom', 'Halo2'], chain: 'polygon', type: 'remote', match: 65 },
    { role: 'DeFi Product Manager', company: 'Compound', salary: '$140k-$190k', stack: ['DeFi', 'Analytics', 'SQL'], chain: 'ethereum', type: 'remote', match: 72 },
    { role: 'Bridge Engineer', company: 'LayerZero', salary: '$170k-$240k', stack: ['Solidity', 'Go', 'Rust'], chain: 'ethereum', type: 'remote', match: 80 },
    { role: 'Frontend Engineer', company: 'Drift Protocol', salary: '$130k-$180k', stack: ['React', 'TypeScript', 'Anchor'], chain: 'solana', type: 'remote', match: 90 },
    { role: 'Security Researcher', company: 'Immunefi', salary: '$160k-$250k', stack: ['Solidity', 'EVM', 'Fuzzing'], chain: 'ethereum', type: 'remote', match: 75 },
    { role: 'L2 Infrastructure Dev', company: 'Arbitrum', salary: '$175k-$260k', stack: ['Go', 'Solidity', 'Docker'], chain: 'arbitrum', type: 'hybrid', match: 68 },
    { role: 'DevRel Engineer', company: 'Alchemy', salary: '$120k-$170k', stack: ['JavaScript', 'Solidity', 'Docs'], chain: 'ethereum', type: 'remote', match: 82 },
    { role: 'MEV Researcher', company: 'Flashbots', salary: '$200k-$350k', stack: ['Go', 'Rust', 'EVM'], chain: 'ethereum', type: 'remote', match: 55 },
  ];

  /* ---------- Theme ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('w3j-theme', theme);
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'dark';
    setTheme(current === 'dark' ? 'light' : 'dark');
  });
  var savedTheme = localStorage.getItem('w3j-theme') ||
    (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  setTheme(savedTheme);

  /* ---------- Filters ---------- */
  var filterChain = document.getElementById('filter-chain');
  var filterType = document.getElementById('filter-type');
  var filterRole = document.getElementById('filter-role');

  filterChain.addEventListener('change', renderJobs);
  filterType.addEventListener('change', renderJobs);
  filterRole.addEventListener('change', renderJobs);

  function getFilteredJobs() {
    var chain = filterChain.value;
    var type = filterType.value;
    var role = filterRole.value;

    return JOBS.filter(function (j) {
      if (chain !== 'all' && j.chain !== chain) return false;
      if (type !== 'all' && j.type !== type) return false;
      if (role !== 'all') {
        if (role === 'engineer' && j.role.toLowerCase().indexOf('engineer') === -1 && j.role.toLowerCase().indexOf('developer') === -1 && j.role.toLowerCase().indexOf('dev') === -1) return false;
        if (role === 'security' && j.role.toLowerCase().indexOf('security') === -1 && j.role.toLowerCase().indexOf('auditor') === -1 && j.role.toLowerCase().indexOf('researcher') === -1) return false;
        if (role === 'product' && j.role.toLowerCase().indexOf('product') === -1 && j.role.toLowerCase().indexOf('devrel') === -1) return false;
      }
      return true;
    });
  }

  /* ---------- Render Jobs ---------- */
  function renderJobs() {
    var tbody = document.getElementById('job-tbody');
    var jobs = getFilteredJobs();

    if (jobs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--color-text-muted);padding:var(--space-xl)">No jobs match your filters</td></tr>';
      return;
    }

    var html = '';
    jobs.forEach(function (j) {
      var typeClass = 'job__type--' + j.type;
      var matchClass = j.match >= 80 ? 'job__match--high' : j.match >= 60 ? 'job__match--medium' : 'job__match--low';
      var stackHtml = j.stack.map(function (s) {
        return '<span class="job__stack-tag">' + s + '</span>';
      }).join('');

      html += '<tr>' +
        '<td class="job__role">' + j.role + '</td>' +
        '<td class="job__company">' + j.company + '</td>' +
        '<td class="job__salary">' + j.salary + '</td>' +
        '<td><div class="job__stack">' + stackHtml + '</div></td>' +
        '<td class="job__type ' + typeClass + '">' + j.type.charAt(0).toUpperCase() + j.type.slice(1) + '</td>' +
        '<td class="job__match ' + matchClass + '">' + j.match + '%</td>' +
        '<td><a class="job__apply" href="#" onclick="return false">Apply</a></td>' +
        '</tr>';
    });
    tbody.innerHTML = html;

    if (!prefersReducedMotion) {
      gsap.utils.toArray('#job-tbody tr').forEach(function (el, i) {
        gsap.from(el, {
          opacity: 0, scale: 0.95, duration: 0.4, delay: i * 0.04, ease: 'power2.out',
        });
      });
    }
  }

  /* ---------- GSAP Animations (D9 scale(0.95)) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__title', { opacity: 0, scale: 0.95, duration: 0.6, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { opacity: 0, scale: 0.95, duration: 0.5, delay: 0.1, ease: 'power3.out' });
    gsap.from('.hero__kpi-bar', { opacity: 0, scale: 0.95, duration: 0.6, delay: 0.2, ease: 'power2.out' });
    gsap.from('.filters', { opacity: 0, scale: 0.95, duration: 0.5, delay: 0.3, ease: 'power2.out' });

    gsap.from('.table-wrapper', {
      scrollTrigger: { trigger: '.table-wrapper', start: 'top 85%' },
      opacity: 0, scale: 0.95, duration: 0.7, ease: 'power2.out',
    });
  }

  /* ---------- Init ---------- */
  renderJobs();
  initAnimations();

})();
