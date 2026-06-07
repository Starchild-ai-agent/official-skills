/* ============================================================
   Dependency Update Monitor — script.js

   Layout: A20 Kanban/Column Layout
   Hover:  C6 border-width 1px → 2px (CSS)
   Entry:  D20 cascade left-top to right-bottom
   Hero:   H2 Compact Stats Bar

   APIs:
   - GitHub API (public repo info, no token required)
   - Built-in simulated dependency data

   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var CONFIG = {
    heroImageUrl: (function () {
      var raw = '{{HERO_IMAGE_URL}}';
      if (raw.indexOf('{{') === 0) return '';
      return raw;
    })(),
    githubUsername: (function () {
      var raw = '{{GITHUB_USERNAME}}';
      if (raw.indexOf('{{') === 0) return 'octocat';
      return raw;
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  var API = {
    githubUser: function (u) { return 'https://api.github.com/users/' + u; },
  };

  var ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ---------- Simulated Data ---------- */
  var SIMULATED_DEPS = [
    { name: 'express', current: '4.18.2', latest: '4.21.0', ecosystem: 'npm', status: 'outdated', severity: 'medium' },
    { name: 'react', current: '18.3.1', latest: '18.3.1', ecosystem: 'npm', status: 'uptodate', severity: 'none' },
    { name: 'next', current: '14.1.0', latest: '14.2.15', ecosystem: 'npm', status: 'outdated', severity: 'high' },
    { name: 'axios', current: '1.6.0', latest: '1.7.7', ecosystem: 'npm', status: 'outdated', severity: 'low' },
    { name: 'lodash', current: '4.17.21', latest: '4.17.21', ecosystem: 'npm', status: 'uptodate', severity: 'none' },
    { name: 'jsonwebtoken', current: '9.0.0', latest: '9.0.2', ecosystem: 'npm', status: 'vulnerable', severity: 'critical' },
    { name: 'webpack', current: '5.89.0', latest: '5.95.0', ecosystem: 'npm', status: 'outdated', severity: 'low' },
    { name: 'typescript', current: '5.3.3', latest: '5.6.3', ecosystem: 'npm', status: 'outdated', severity: 'none' },
    { name: 'fastapi', current: '0.109.0', latest: '0.115.0', ecosystem: 'pip', status: 'outdated', severity: 'medium' },
    { name: 'django', current: '4.2.7', latest: '5.1.2', ecosystem: 'pip', status: 'outdated', severity: 'high' },
    { name: 'requests', current: '2.31.0', latest: '2.32.3', ecosystem: 'pip', status: 'outdated', severity: 'low' },
    { name: 'pydantic', current: '2.5.0', latest: '2.9.2', ecosystem: 'pip', status: 'outdated', severity: 'none' },
    { name: 'flask', current: '3.0.0', latest: '3.0.3', ecosystem: 'pip', status: 'uptodate', severity: 'none' },
    { name: 'cryptography', current: '41.0.4', latest: '43.0.1', ecosystem: 'pip', status: 'vulnerable', severity: 'critical' },
    { name: 'tokio', current: '1.35.0', latest: '1.40.0', ecosystem: 'cargo', status: 'outdated', severity: 'low' },
    { name: 'serde', current: '1.0.195', latest: '1.0.210', ecosystem: 'cargo', status: 'outdated', severity: 'none' },
    { name: 'actix-web', current: '4.4.0', latest: '4.9.0', ecosystem: 'cargo', status: 'outdated', severity: 'medium' },
    { name: 'reqwest', current: '0.11.22', latest: '0.12.8', ecosystem: 'cargo', status: 'outdated', severity: 'low' },
  ];

  var SIMULATED_VULNS = [
    { cve: 'CVE-2024-34340', package: 'jsonwebtoken', severity: 'critical', title: 'JWT Algorithm Confusion Attack', desc: 'Allows attackers to bypass signature verification by switching from RS256 to HS256 algorithm.', affected: '< 9.0.1', fixed: '9.0.2', cvss: 9.1 },
    { cve: 'CVE-2024-26130', package: 'cryptography', severity: 'critical', title: 'Buffer Overflow in PKCS7 Padding', desc: 'A specially crafted PKCS7 blob can trigger a buffer overflow in the C backend.', affected: '< 42.0.0', fixed: '42.0.4', cvss: 8.8 },
    { cve: 'CVE-2024-39573', package: 'next', severity: 'high', title: 'Server-Side Request Forgery in Image Optimization', desc: 'The image optimization API can be abused to make requests to internal services.', affected: '< 14.2.10', fixed: '14.2.10', cvss: 7.5 },
    { cve: 'CVE-2024-42353', package: 'django', severity: 'high', title: 'SQL Injection in QuerySet.extra()', desc: 'Improper sanitization of user input in QuerySet.extra() allows SQL injection.', affected: '< 4.2.16', fixed: '4.2.16', cvss: 7.2 },
    { cve: 'CVE-2024-28849', package: 'express', severity: 'medium', title: 'Open Redirect via Host Header', desc: 'Express does not properly validate the Host header, allowing open redirect attacks.', affected: '< 4.19.0', fixed: '4.19.0', cvss: 5.4 },
  ];

  function generateUpdateTimeline() {
    var data = [];
    var now = Date.now();
    for (var i = 29; i >= 0; i--) {
      var date = new Date(now - i * 86400000);
      var label = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      var updates = Math.random() < 0.3 ? 0 : Math.floor(Math.random() * 4) + 1;
      data.push({ label: label, updates: updates });
    }
    return data;
  }

  /* ---------- State ---------- */
  var updateChart = null;
  var ecoChart = null;

  /* ---------- fetchWithRetry ---------- */
  async function fetchWithRetry(url, retries) {
    retries = retries || CONFIG.maxRetries;
    for (var i = 0; i <= retries; i++) {
      try {
        var res = await fetch(url);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return await res.json();
      } catch (err) {
        if (i === retries) throw err;
        await new Promise(function (r) { setTimeout(r, CONFIG.retryBaseDelay * (i + 1)); });
      }
    }
  }

  /* ---------- Theme Toggle ---------- */
  function initTheme() {
    var toggle = document.getElementById('theme-toggle');
    var saved = localStorage.getItem('dep-monitor-theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');
    toggle.addEventListener('click', function () {
      var isLight = document.documentElement.getAttribute('data-theme') === 'light';
      if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('dep-monitor-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('dep-monitor-theme', 'light');
      }
      rebuildCharts();
    });
  }

  function initHeroImage() {
    if (!CONFIG.heroImageUrl) return;
    var el = document.querySelector('.hero__bg-image');
    if (el) el.style.backgroundImage = 'url(' + CONFIG.heroImageUrl + ')';
  }

  function updateClock() {
    var el = document.getElementById('hero-time');
    if (!el) return;
    var now = new Date();
    el.textContent = now.toLocaleString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    el.setAttribute('datetime', now.toISOString());
  }

  /* ---------- Compute Health Score ---------- */
  function computeHealthScore(deps) {
    if (deps.length === 0) return 100;
    var score = 100;
    deps.forEach(function (d) {
      if (d.status === 'vulnerable') {
        if (d.severity === 'critical') score -= 15;
        else if (d.severity === 'high') score -= 10;
        else score -= 5;
      } else if (d.status === 'outdated') {
        if (d.severity === 'high') score -= 5;
        else if (d.severity === 'medium') score -= 3;
        else score -= 1;
      }
    });
    return Math.max(0, Math.round(score));
  }

  /* ---------- Update Hero Stats ---------- */
  function updateHeroStats(deps) {
    var outdated = deps.filter(function (d) { return d.status === 'outdated'; }).length;
    var vulns = deps.filter(function (d) { return d.status === 'vulnerable'; }).length;
    var uptodate = deps.filter(function (d) { return d.status === 'uptodate'; }).length;
    var healthScore = computeHealthScore(deps);

    document.getElementById('health-score').textContent = healthScore;
    document.getElementById('stat-outdated').textContent = outdated;
    document.getElementById('stat-vulns').textContent = vulns;
    document.getElementById('stat-uptodate').textContent = uptodate;

    document.querySelectorAll('.hero__stat.skeleton').forEach(function (el) { el.classList.remove('skeleton'); });
  }

  /* ---------- Render Kanban Board ---------- */
  function renderKanban(deps) {
    var outdatedCol = document.getElementById('kanban-outdated');
    var vulnCol = document.getElementById('kanban-vulnerable');
    var okCol = document.getElementById('kanban-uptodate');
    if (!outdatedCol || !vulnCol || !okCol) return;

    var outdated = deps.filter(function (d) { return d.status === 'outdated'; });
    var vulnerable = deps.filter(function (d) { return d.status === 'vulnerable'; });
    var uptodate = deps.filter(function (d) { return d.status === 'uptodate'; });

    document.getElementById('kanban-outdated-count').textContent = outdated.length;
    document.getElementById('kanban-vuln-count').textContent = vulnerable.length;
    document.getElementById('kanban-ok-count').textContent = uptodate.length;

    function renderCards(container, items) {
      container.innerHTML = items.map(function (d) {
        return '<div class="dep-card" data-animate data-col="' + d.status + '">' +
          '<div class="dep-card__name">' + d.name + '</div>' +
          '<div class="dep-card__versions">' +
            '<span>' + d.current + '</span>' +
            '<span class="dep-card__arrow">→</span>' +
            '<span>' + d.latest + '</span>' +
          '</div>' +
          '<div class="dep-card__footer">' +
            '<span class="dep-card__eco">' + d.ecosystem + '</span>' +
            '<span class="badge badge--' + d.severity + '">' + d.severity + '</span>' +
          '</div>' +
        '</div>';
      }).join('');
      if (items.length === 0) {
        container.innerHTML = '<p style="color: var(--color-text-muted); font-size: var(--text-xs); text-align: center; padding: var(--space-m);">No packages</p>';
      }
    }

    renderCards(outdatedCol, outdated);
    renderCards(vulnCol, vulnerable);
    renderCards(okCol, uptodate);
  }

  /* ---------- Render Vulnerability Cards ---------- */
  function renderVulnCards(vulns) {
    var grid = document.getElementById('vulns-grid');
    if (!grid) return;
    if (vulns.length === 0) {
      grid.innerHTML = '<p style="color: var(--color-text-secondary);">No known vulnerabilities found.</p>';
      return;
    }
    grid.innerHTML = vulns.map(function (v) {
      return '<div class="vuln-card vuln-card--' + v.severity + '" data-animate>' +
        '<div class="vuln-card__header">' +
          '<span class="vuln-card__cve">' + v.cve + '</span>' +
          '<span class="badge badge--' + v.severity + '">' + v.severity + '</span>' +
          '<span class="vuln-card__pkg">' + v.package + '</span>' +
        '</div>' +
        '<h3 class="vuln-card__title">' + v.title + '</h3>' +
        '<p class="vuln-card__desc">' + v.desc + '</p>' +
        '<div class="vuln-card__meta">' +
          '<span class="vuln-card__meta-item">Affected: ' + v.affected + '</span>' +
          '<span class="vuln-card__meta-item">Fixed: ' + v.fixed + '</span>' +
          '<span class="vuln-card__meta-item">CVSS: ' + v.cvss + '</span>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  /* ---------- Render Update Timeline Chart ---------- */
  function renderUpdateChart(timelineData) {
    var skeleton = document.getElementById('update-chart-skeleton');
    var errorEl = document.getElementById('update-chart-error');
    var ctx = document.getElementById('update-chart');
    if (!ctx) return;
    if (skeleton) skeleton.hidden = true;
    if (errorEl) errorEl.hidden = true;
    if (updateChart) updateChart.destroy();

    var styles = getComputedStyle(document.documentElement);
    var textColor = styles.getPropertyValue('--color-text-secondary').trim();
    var borderColor = styles.getPropertyValue('--color-border').trim();
    var accentColor = styles.getPropertyValue('--color-accent').trim();

    updateChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: timelineData.map(function (d) { return d.label; }),
        datasets: [{
          label: 'Updates',
          data: timelineData.map(function (d) { return d.updates; }),
          borderColor: accentColor,
          backgroundColor: accentColor + '20',
          fill: true, tension: 0.3, pointRadius: 3,
          pointBackgroundColor: accentColor, borderWidth: 2,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: { backgroundColor: 'rgba(0,0,0,0.85)', titleFont: { family: "'Victor Mono', monospace", size: 11 }, bodyFont: { family: "'Victor Mono', monospace", size: 11 }, padding: 10, cornerRadius: 6 },
        },
        scales: {
          x: { ticks: { color: textColor, font: { family: "'Victor Mono', monospace", size: 10 }, maxTicksLimit: 10 }, grid: { color: borderColor } },
          y: { beginAtZero: true, ticks: { color: textColor, font: { family: "'Victor Mono', monospace", size: 10 }, stepSize: 1 }, grid: { color: borderColor } },
        },
      },
    });
  }

  /* ---------- Render Ecosystem Doughnut ---------- */
  function renderEcoChart(deps) {
    var ctx = document.getElementById('eco-chart');
    var legendEl = document.getElementById('ecosystem-legend');
    if (!ctx) return;
    if (ecoChart) ecoChart.destroy();

    var ecosystems = {};
    deps.forEach(function (d) { ecosystems[d.ecosystem] = (ecosystems[d.ecosystem] || 0) + 1; });

    var labels = Object.keys(ecosystems);
    var data = Object.values(ecosystems);
    var styles = getComputedStyle(document.documentElement);
    var colors = [];
    for (var i = 0; i < labels.length; i++) {
      colors.push(styles.getPropertyValue('--chart-' + (i + 1)).trim() || '#f0a500');
    }

    ecoChart = new Chart(ctx, {
      type: 'doughnut',
      data: { labels: labels, datasets: [{ data: data, backgroundColor: colors.slice(0, labels.length), borderWidth: 0 }] },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '65%',
        plugins: {
          legend: { display: false },
          tooltip: { backgroundColor: 'rgba(0,0,0,0.85)', titleFont: { family: "'Victor Mono', monospace", size: 11 }, bodyFont: { family: "'Victor Mono', monospace", size: 11 }, padding: 10, cornerRadius: 6 },
        },
      },
    });

    if (legendEl) {
      legendEl.innerHTML = labels.map(function (label, i) {
        return '<div class="legend-item" data-animate>' +
          '<span class="legend-item__dot" style="background: ' + colors[i] + '"></span>' +
          '<span class="legend-item__label">' + label + '</span>' +
          '<span class="legend-item__count">' + data[i] + ' packages</span>' +
        '</div>';
      }).join('');
    }
  }

  /* ---------- Rebuild Charts ---------- */
  function rebuildCharts() {
    var timelineData = generateUpdateTimeline();
    renderUpdateChart(timelineData);
    renderEcoChart(SIMULATED_DEPS);
  }

  /* ---------- GSAP Animations: D20 Cascade ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero entrance */
    gsap.from('.hero__top', { y: -20, opacity: 0, duration: 0.6, ease: 'power3.out' });
    gsap.from('.hero__stats-bar', { y: 20, opacity: 0, duration: 0.6, ease: 'power3.out', delay: 0.2 });

    /* Kanban columns cascade: left to right */
    gsap.utils.toArray('.kanban__column').forEach(function (col, colIdx) {
      gsap.from(col, {
        scrollTrigger: { trigger: col, start: 'top 88%', toggleActions: 'play none none none' },
        opacity: 0, y: 30, duration: 0.5, delay: colIdx * 0.15, ease: 'power2.out',
      });

      /* Cards within each column: top to bottom stagger */
      var cards = col.querySelectorAll('.dep-card');
      if (cards.length > 0) {
        gsap.from(cards, {
          scrollTrigger: { trigger: col, start: 'top 85%', toggleActions: 'play none none none' },
          opacity: 0, y: 20, duration: 0.4, stagger: 0.06, delay: colIdx * 0.15 + 0.2, ease: 'power2.out',
        });
      }
    });

    /* Vuln cards cascade */
    gsap.utils.toArray('.vuln-card').forEach(function (card, i) {
      var row = Math.floor(i / 2);
      var col = i % 2;
      gsap.from(card, {
        scrollTrigger: { trigger: card, start: 'top 88%', toggleActions: 'play none none none' },
        opacity: 0, y: 25, duration: 0.5, delay: (row + col) * 0.08, ease: 'power2.out',
      });
    });

    /* Section headers */
    gsap.utils.toArray('.section__header').forEach(function (header) {
      gsap.from(header, {
        scrollTrigger: { trigger: header, start: 'top 85%', toggleActions: 'play none none none' },
        y: 25, opacity: 0, duration: 0.6, ease: 'power2.out',
      });
    });
  }

  /* ---------- Main Init ---------- */
  async function init() {
    initTheme();
    initHeroImage();
    updateClock();
    setInterval(updateClock, 30000);

    try {
      await fetchWithRetry(API.githubUser(CONFIG.githubUsername));
    } catch (err) {
      console.warn('GitHub API unavailable:', err.message);
    }

    var deps = SIMULATED_DEPS;
    updateHeroStats(deps);
    renderKanban(deps);
    renderVulnCards(SIMULATED_VULNS);

    var timelineData = generateUpdateTimeline();
    renderUpdateChart(timelineData);
    renderEcoChart(deps);

    requestAnimationFrame(function () {
      initAnimations();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
