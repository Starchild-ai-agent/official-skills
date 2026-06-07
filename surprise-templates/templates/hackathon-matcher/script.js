/* ============================================================
   Hackathon Matcher — script.js

   Pure frontend with built-in simulated hackathon data.
   Renders hackathon cards, skill radar chart, calendar view,
   and past winner showcase.

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
    techStack: (function () {
      var raw = '{{TECH_STACK}}';
      if (raw.startsWith('{{')) return 'JavaScript, React, Node.js';
      return raw;
    })(),
  };

  var userSkills = CONFIG.techStack.split(',').map(function (s) { return s.trim().toLowerCase(); });

  /* ---------- Simulated Hackathon Data ---------- */
  var now = new Date();
  var HACKATHONS = [
    {
      name: 'ETHGlobal Brussels',
      platform: 'ETHGlobal',
      mode: 'in-person',
      startDate: addDays(now, 12),
      endDate: addDays(now, 14),
      prize: '$250,000',
      prizeNum: 250000,
      tags: ['solidity', 'ethereum', 'defi', 'web3', 'react'],
      desc: 'Build the future of Ethereum at the heart of Europe.',
    },
    {
      name: 'AI Agents Hackathon',
      platform: 'Devpost',
      mode: 'online',
      startDate: addDays(now, 5),
      endDate: addDays(now, 19),
      prize: '$100,000',
      prizeNum: 100000,
      tags: ['python', 'ai', 'machine-learning', 'langchain', 'typescript'],
      desc: 'Create autonomous AI agents that solve real-world problems.',
    },
    {
      name: 'MLH Global Hack Week',
      platform: 'MLH',
      mode: 'online',
      startDate: addDays(now, 22),
      endDate: addDays(now, 29),
      prize: '$50,000',
      prizeNum: 50000,
      tags: ['javascript', 'python', 'react', 'node.js', 'open-source'],
      desc: 'A week-long celebration of hacking with workshops and prizes.',
    },
    {
      name: 'Solana Grizzlython',
      platform: 'Solana Foundation',
      mode: 'online',
      startDate: addDays(now, 30),
      endDate: addDays(now, 51),
      prize: '$500,000',
      prizeNum: 500000,
      tags: ['rust', 'solana', 'web3', 'typescript', 'defi'],
      desc: 'Build on Solana for massive prizes across multiple tracks.',
    },
    {
      name: 'HackMIT',
      platform: 'HackMIT',
      mode: 'in-person',
      startDate: addDays(now, 45),
      endDate: addDays(now, 47),
      prize: '$75,000',
      prizeNum: 75000,
      tags: ['python', 'javascript', 'react', 'machine-learning', 'mobile'],
      desc: 'MIT\'s premier hackathon bringing together top student hackers.',
    },
    {
      name: 'Chainlink Constellation',
      platform: 'Devpost',
      mode: 'hybrid',
      startDate: addDays(now, 18),
      endDate: addDays(now, 39),
      prize: '$350,000',
      prizeNum: 350000,
      tags: ['solidity', 'chainlink', 'web3', 'node.js', 'typescript'],
      desc: 'Build smart contracts powered by Chainlink oracles and CCIP.',
    },
    {
      name: 'React Summit Hackathon',
      platform: 'GitNation',
      mode: 'hybrid',
      startDate: addDays(now, 60),
      endDate: addDays(now, 62),
      prize: '$30,000',
      prizeNum: 30000,
      tags: ['react', 'next.js', 'typescript', 'javascript', 'css'],
      desc: 'Show off your React skills at the biggest React conference.',
    },
    {
      name: 'Google Cloud AI Jam',
      platform: 'Google',
      mode: 'online',
      startDate: addDays(now, 8),
      endDate: addDays(now, 22),
      prize: '$150,000',
      prizeNum: 150000,
      tags: ['python', 'google-cloud', 'ai', 'tensorflow', 'typescript'],
      desc: 'Leverage Google Cloud AI to build innovative applications.',
    },
  ];

  var PAST_WINNERS = [
    { name: 'ZK-Proof Wallet', hackathon: 'ETHGlobal Paris 2025', prize: '1st Place — $15,000', tech: ['Solidity', 'React', 'Circom'], desc: 'A privacy-preserving wallet using zero-knowledge proofs for anonymous transactions.' },
    { name: 'CodeMentor AI', hackathon: 'AI Agents Hack 2025', prize: '1st Place — $25,000', tech: ['Python', 'LangChain', 'Next.js'], desc: 'An AI pair programmer that understands your codebase context and suggests improvements.' },
    { name: 'DeFi Dashboard Pro', hackathon: 'Solana Hyperdrive', prize: 'DeFi Track — $20,000', tech: ['Rust', 'TypeScript', 'React'], desc: 'Real-time portfolio tracking across all Solana DeFi protocols with yield optimization.' },
    { name: 'EcoTrack', hackathon: 'HackMIT 2025', prize: 'Best Social Impact — $10,000', tech: ['Python', 'React Native', 'TensorFlow'], desc: 'Carbon footprint tracker using ML to analyze purchase receipts and suggest alternatives.' },
    { name: 'ChainVote', hackathon: 'Chainlink Fall 2025', prize: 'Grand Prize — $30,000', tech: ['Solidity', 'Chainlink', 'Vue.js'], desc: 'Decentralized voting platform with Chainlink VRF for verifiable random ballot ordering.' },
    { name: 'PixelForge', hackathon: 'MLH Global Hack 2025', prize: 'Best Design — $5,000', tech: ['JavaScript', 'Canvas API', 'Node.js'], desc: 'Collaborative pixel art editor with real-time multiplayer and NFT minting.' },
  ];

  /* ---------- Skill Categories for Radar ---------- */
  var SKILL_CATEGORIES = [
    { label: 'Frontend', keywords: ['react', 'vue', 'vue.js', 'svelte', 'next.js', 'angular', 'css', 'html', 'javascript', 'typescript'] },
    { label: 'Backend', keywords: ['node.js', 'python', 'go', 'rust', 'java', 'ruby', 'php', 'express', 'fastapi', 'django'] },
    { label: 'Blockchain', keywords: ['solidity', 'web3', 'ethereum', 'solana', 'defi', 'chainlink', 'rust'] },
    { label: 'AI / ML', keywords: ['python', 'ai', 'machine-learning', 'tensorflow', 'pytorch', 'langchain', 'llm'] },
    { label: 'Mobile', keywords: ['react-native', 'flutter', 'swift', 'kotlin', 'mobile', 'ios', 'android'] },
    { label: 'DevOps', keywords: ['docker', 'kubernetes', 'aws', 'google-cloud', 'ci/cd', 'terraform', 'linux'] },
  ];

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return Array.from(document.querySelectorAll(sel)); };

  var els = {
    themeToggle: $('#theme-toggle'),
    heroTime: $('#hero-time'),
    heroBgImage: $('.hero__bg-image'),
    statMatched: $('#stat-matched'),
    statCountdown: $('#stat-countdown'),
    statTotalPrize: $('#stat-total-prize'),
    filterBar: $('#filter-bar'),
    hackathonGrid: $('#hackathon-grid'),
    radarChartContainer: $('#radar-chart-container'),
    radarSkeleton: $('#radar-skeleton'),
    radarChart: $('#radar-chart'),
    calMonth: $('#cal-month'),
    calPrev: $('#cal-prev'),
    calNext: $('#cal-next'),
    calGrid: $('#cal-grid'),
    winnersGrid: $('#winners-grid'),
    footerTime: $('#footer-time'),
  };

  /* ---------- Helpers ---------- */
  function addDays(date, days) {
    var d = new Date(date);
    d.setDate(d.getDate() + days);
    return d;
  }

  function formatDate(d) {
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function calcMatchScore(hackTags) {
    var matched = 0;
    hackTags.forEach(function (t) {
      if (userSkills.indexOf(t.toLowerCase()) !== -1) matched++;
    });
    return Math.round((matched / Math.max(hackTags.length, 1)) * 100);
  }

  function getCountdown(targetDate) {
    var diff = targetDate.getTime() - Date.now();
    if (diff <= 0) return 'Started!';
    var days = Math.floor(diff / 86400000);
    var hours = Math.floor((diff % 86400000) / 3600000);
    if (days > 0) return days + 'd ' + hours + 'h';
    var mins = Math.floor((diff % 3600000) / 60000);
    return hours + 'h ' + mins + 'm';
  }

  /* ---------- Theme ---------- */
  function initTheme() {
    var saved = localStorage.getItem('hackathon-matcher-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    }
    els.themeToggle.addEventListener('click', function () {
      var current = document.documentElement.getAttribute('data-theme');
      var next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('hackathon-matcher-theme', next);
      updateChartColors();
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

  /* ---------- Hero Stats ---------- */
  function updateHeroStats() {
    var matched = HACKATHONS.filter(function (h) { return calcMatchScore(h.tags) > 0; }).length;
    els.statMatched.textContent = matched;

    // Find next upcoming
    var sorted = HACKATHONS.slice().sort(function (a, b) { return a.startDate - b.startDate; });
    var next = sorted.find(function (h) { return h.startDate > new Date(); });
    els.statCountdown.textContent = next ? getCountdown(next.startDate) : 'N/A';

    var totalPrize = HACKATHONS.reduce(function (s, h) { return s + h.prizeNum; }, 0);
    els.statTotalPrize.textContent = '$' + (totalPrize / 1000) + 'k';
  }

  /* ---------- Hackathon Cards ---------- */
  function renderHackathons(filter) {
    var filtered = filter === 'all' ? HACKATHONS : HACKATHONS.filter(function (h) { return h.mode === filter; });
    filtered.sort(function (a, b) { return a.startDate - b.startDate; });

    els.hackathonGrid.innerHTML = filtered.map(function (h) {
      var score = calcMatchScore(h.tags);
      var modeClass = 'hackathon-card__mode--' + h.mode;
      var modeLabel = h.mode === 'in-person' ? 'In-Person' : h.mode.charAt(0).toUpperCase() + h.mode.slice(1);

      var tagsHtml = h.tags.map(function (t) {
        var isMatch = userSkills.indexOf(t.toLowerCase()) !== -1;
        return '<span class="hackathon-card__tag' + (isMatch ? ' hackathon-card__tag--match' : '') + '">' + t + '</span>';
      }).join('');

      return '<article class="hackathon-card">' +
        '<div class="hackathon-card__header">' +
          '<span class="hackathon-card__name">' + h.name + '</span>' +
          '<span class="hackathon-card__mode ' + modeClass + '">' + modeLabel + '</span>' +
        '</div>' +
        '<p class="hackathon-card__date">' + formatDate(h.startDate) + ' — ' + formatDate(h.endDate) + '</p>' +
        '<span class="hackathon-card__prize">' + h.prize + '</span>' +
        '<div class="hackathon-card__tags">' + tagsHtml + '</div>' +
        '<div class="hackathon-card__meta">' +
          '<span class="hackathon-card__platform">' + h.platform + '</span>' +
          '<span class="hackathon-card__match">' + score + '% match</span>' +
        '</div>' +
      '</article>';
    }).join('');

    /* D14: fade + scale(0.9) entry */
    if (!prefersReducedMotion) {
      $$('.hackathon-card').forEach(function (card, i) {
        gsap.from(card, {
          scale: 0.9, opacity: 0, duration: 0.5, delay: i * 0.06, ease: 'power3.out',
        });
      });
    }
  }

  /* ---------- Filter ---------- */
  function initFilters() {
    els.filterBar.addEventListener('click', function (e) {
      var btn = e.target.closest('.filter-btn');
      if (!btn) return;
      $$('.filter-btn').forEach(function (b) { b.classList.remove('filter-btn--active'); });
      btn.classList.add('filter-btn--active');
      renderHackathons(btn.dataset.filter);
    });
  }

  /* ---------- Radar Chart ---------- */
  var radarChartInstance = null;

  function getChartColors() {
    var style = getComputedStyle(document.documentElement);
    return {
      text: style.getPropertyValue('--chart-text').trim(),
      grid: style.getPropertyValue('--chart-grid').trim(),
      accent: style.getPropertyValue('--color-accent').trim(),
    };
  }

  function renderRadarChart() {
    els.radarSkeleton.remove();
    var labels = SKILL_CATEGORIES.map(function (c) { return c.label; });
    var scores = SKILL_CATEGORIES.map(function (c) {
      var matched = 0;
      c.keywords.forEach(function (k) {
        if (userSkills.indexOf(k) !== -1) matched++;
      });
      return Math.round((matched / c.keywords.length) * 100);
    });

    var cc = getChartColors();
    radarChartInstance = new Chart(els.radarChart, {
      type: 'radar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Your Skills',
          data: scores,
          backgroundColor: cc.accent + '22',
          borderColor: cc.accent,
          borderWidth: 2,
          pointBackgroundColor: cc.accent,
          pointBorderColor: cc.accent,
          pointRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            titleFont: { family: "'Source Code Pro', monospace", size: 12 },
            bodyFont: { family: "'Nunito', sans-serif", size: 13 },
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: function (ctx) { return ctx.parsed.r + '% match'; },
            },
          },
        },
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            ticks: {
              stepSize: 25,
              color: cc.text,
              backdropColor: 'transparent',
              font: { family: "'Source Code Pro', monospace", size: 10 },
            },
            grid: { color: cc.grid },
            angleLines: { color: cc.grid },
            pointLabels: {
              color: cc.text,
              font: { family: "'Fredoka', sans-serif", size: 13, weight: '600' },
            },
          },
        },
      },
    });
  }

  function updateChartColors() {
    if (!radarChartInstance) return;
    var cc = getChartColors();
    radarChartInstance.data.datasets[0].backgroundColor = cc.accent + '22';
    radarChartInstance.data.datasets[0].borderColor = cc.accent;
    radarChartInstance.data.datasets[0].pointBackgroundColor = cc.accent;
    radarChartInstance.data.datasets[0].pointBorderColor = cc.accent;
    radarChartInstance.options.scales.r.ticks.color = cc.text;
    radarChartInstance.options.scales.r.grid.color = cc.grid;
    radarChartInstance.options.scales.r.angleLines.color = cc.grid;
    radarChartInstance.options.scales.r.pointLabels.color = cc.text;
    radarChartInstance.update('none');
  }

  /* ---------- Calendar ---------- */
  var calendarDate = new Date();

  function renderCalendar() {
    var year = calendarDate.getFullYear();
    var month = calendarDate.getMonth();
    els.calMonth.textContent = calendarDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    var firstDay = new Date(year, month, 1).getDay();
    var daysInMonth = new Date(year, month + 1, 0).getDate();
    var today = new Date();

    // Find event days this month
    var eventDays = {};
    HACKATHONS.forEach(function (h) {
      var start = new Date(h.startDate);
      var end = new Date(h.endDate);
      for (var d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
        if (d.getFullYear() === year && d.getMonth() === month) {
          eventDays[d.getDate()] = h.name;
        }
      }
    });

    var html = '';
    // Empty cells before first day
    for (var i = 0; i < firstDay; i++) {
      html += '<div class="cal-day cal-day--empty"></div>';
    }
    for (var day = 1; day <= daysInMonth; day++) {
      var isToday = today.getFullYear() === year && today.getMonth() === month && today.getDate() === day;
      var isEvent = eventDays[day];
      var classes = 'cal-day';
      if (isToday) classes += ' cal-day--today';
      if (isEvent) classes += ' cal-day--event';
      var title = isEvent ? ' title="' + eventDays[day] + '"' : '';
      html += '<div class="' + classes + '"' + title + '>' + day + '</div>';
    }
    els.calGrid.innerHTML = html;
  }

  function initCalendar() {
    renderCalendar();
    els.calPrev.addEventListener('click', function () {
      calendarDate.setMonth(calendarDate.getMonth() - 1);
      renderCalendar();
    });
    els.calNext.addEventListener('click', function () {
      calendarDate.setMonth(calendarDate.getMonth() + 1);
      renderCalendar();
    });
  }

  /* ---------- Past Winners ---------- */
  function renderWinners() {
    els.winnersGrid.innerHTML = PAST_WINNERS.map(function (w) {
      var techHtml = w.tech.map(function (t) { return '<span>' + t + '</span>'; }).join(' · ');
      return '<article class="winner-card">' +
        '<span class="winner-card__badge">&#127942; ' + w.prize + '</span>' +
        '<h3 class="winner-card__name">' + w.name + '</h3>' +
        '<p class="winner-card__desc">' + w.desc + '</p>' +
        '<div class="winner-card__meta">' +
          '<span>' + w.hackathon + '</span>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  /* ---------- Countdown Timer (H13) ---------- */
  function updateCountdown() {
    var nextHack = HACKATHONS.filter(function (h) { return h.startDate > new Date(); })
      .sort(function (a, b) { return a.startDate - b.startDate; })[0];
    if (!nextHack) return;

    var diff = nextHack.startDate - new Date();
    if (diff <= 0) return;

    var days = Math.floor(diff / 86400000);
    var hours = Math.floor((diff % 86400000) / 3600000);
    var mins = Math.floor((diff % 3600000) / 60000);
    var secs = Math.floor((diff % 60000) / 1000);

    var dEl = document.getElementById('countdown-days');
    var hEl = document.getElementById('countdown-hours');
    var mEl = document.getElementById('countdown-mins');
    var sEl = document.getElementById('countdown-secs');
    if (dEl) dEl.textContent = String(days).padStart(2, '0');
    if (hEl) hEl.textContent = String(hours).padStart(2, '0');
    if (mEl) mEl.textContent = String(mins).padStart(2, '0');
    if (sEl) sEl.textContent = String(secs).padStart(2, '0');
  }

  /* ---------- GSAP Animations — D14: fade + scale(0.9) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero entrance with scale */
    gsap.from('.hero__content', {
      scale: 0.9, opacity: 0, duration: 1, ease: 'power3.out',
    });
    gsap.from('.hero__countdown', {
      scale: 0.9, opacity: 0, duration: 0.8, delay: 0.3, ease: 'power3.out',
    });

    /* Calendar side */
    gsap.from('.calendar-side', {
      scrollTrigger: { trigger: '.calendar-side', start: 'top 85%', once: true },
      scale: 0.9, opacity: 0, duration: 0.8, ease: 'power3.out',
    });

    /* Section titles */
    $$('.section').forEach(function (section) {
      var title = section.querySelector('.section__title');
      if (title) {
        gsap.from(title, {
          scrollTrigger: { trigger: section, start: 'top 80%', once: true },
          scale: 0.9, opacity: 0, duration: 0.8, ease: 'power3.out',
        });
      }
      var desc = section.querySelector('.section__desc');
      if (desc) {
        gsap.from(desc, {
          scrollTrigger: { trigger: section, start: 'top 80%', once: true },
          scale: 0.9, opacity: 0, duration: 0.8, delay: 0.1, ease: 'power3.out',
        });
      }
    });

    /* Winner cards — D14 */
    setTimeout(function () {
      $$('.winner-card').forEach(function (card, i) {
        gsap.from(card, {
          scrollTrigger: { trigger: card, start: 'top 85%', once: true },
          scale: 0.9, opacity: 0, duration: 0.6, delay: i * 0.08, ease: 'power3.out',
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
    setInterval(updateHeroStats, 60000);

    updateHeroStats();
    updateCountdown();
    setInterval(updateCountdown, 1000);
    renderHackathons('all');
    initFilters();
    renderRadarChart();
    initCalendar();
    renderWinners();
    initAnimations();

    setTimeout(function () { ScrollTrigger.refresh(); }, 300);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
