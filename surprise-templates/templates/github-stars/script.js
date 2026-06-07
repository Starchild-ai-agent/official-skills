/* ============================================================
   GitHub Stars Explorer — script.js

   Fetches starred repos from GitHub API (unauthenticated, 60 req/hr).
   Renders language distribution (doughnut), star timeline (bar),
   top repos list, and interest tag cloud.

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
    githubUsername: (function () {
      var raw = '{{GITHUB_USERNAME}}';
      if (raw.startsWith('{{')) return 'torvalds';
      return raw;
    })(),
  };

  var GITHUB_LANG_COLORS = {
    JavaScript: '#f1e05a', TypeScript: '#3178c6', Python: '#3572A5',
    Java: '#b07219', Go: '#00ADD8', Rust: '#dea584',
    'C++': '#f34b7d', C: '#555555', 'C#': '#178600',
    Ruby: '#701516', PHP: '#4F5D95', Swift: '#F05138',
    Kotlin: '#A97BFF', Dart: '#00B4AB', Scala: '#c22d40',
    Shell: '#89e051', Lua: '#000080', Vim: '#199f4b',
    HTML: '#e34c26', CSS: '#563d7c', Vue: '#41b883',
    Svelte: '#ff3e00', Jupyter: '#DA5B0B', R: '#198CE7',
    Elixir: '#6e4a7e', Haskell: '#5e5086', Clojure: '#db5855',
    Zig: '#ec915c', Nix: '#7e7eff', OCaml: '#3be133',
  };

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return Array.from(document.querySelectorAll(sel)); };

  var els = {
    themeToggle: $('#theme-toggle'),
    heroTime: $('#hero-time'),
    heroBgImage: $('.hero__bg-image'),
    statTotalStars: $('#stat-total-stars'),
    statTopLang: $('#stat-top-lang'),
    statPattern: $('#stat-pattern'),
    langChartContainer: $('#lang-chart-container'),
    langSkeleton: $('#lang-skeleton'),
    langError: $('#lang-error'),
    langRetry: $('#lang-retry'),
    langChart: $('#lang-chart'),
    langLegend: $('#lang-legend'),
    timelineChartContainer: $('#timeline-chart-container'),
    timelineSkeleton: $('#timeline-skeleton'),
    timelineError: $('#timeline-error'),
    timelineRetry: $('#timeline-retry'),
    timelineChart: $('#timeline-chart'),
    reposGrid: $('#repos-grid'),
    reposError: $('#repos-error'),
    reposRetry: $('#repos-retry'),
    tagCloud: $('#tag-cloud'),
    footerTime: $('#footer-time'),
  };

  /* ---------- Theme ---------- */
  function initTheme() {
    var saved = localStorage.getItem('github-stars-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    }
    els.themeToggle.addEventListener('click', function () {
      var current = document.documentElement.getAttribute('data-theme');
      var next = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('github-stars-theme', next);
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

  /* ---------- Fetch with Retry ---------- */
  function fetchWithRetry(url, opts, retries) {
    retries = retries || 3;
    return fetch(url, opts).then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res;
    }).catch(function (err) {
      if (retries <= 1) throw err;
      return new Promise(function (resolve) {
        setTimeout(resolve, 1000);
      }).then(function () {
        return fetchWithRetry(url, opts, retries - 1);
      });
    });
  }

  /* ---------- Fallback Data ---------- */
  var FALLBACK_STARRED = [
    { repo: { full_name: 'torvalds/linux', description: 'Linux kernel source tree', language: 'C', stargazers_count: 178000, forks_count: 53000, topics: ['linux', 'kernel', 'os'], html_url: 'https://github.com/torvalds/linux' }, starred_at: '2023-01-15T10:00:00Z' },
    { repo: { full_name: 'golang/go', description: 'The Go programming language', language: 'Go', stargazers_count: 124000, forks_count: 17000, topics: ['go', 'programming-language'], html_url: 'https://github.com/golang/go' }, starred_at: '2023-03-20T08:00:00Z' },
    { repo: { full_name: 'rust-lang/rust', description: 'Empowering everyone to build reliable and efficient software', language: 'Rust', stargazers_count: 98000, forks_count: 12600, topics: ['rust', 'compiler', 'systems'], html_url: 'https://github.com/rust-lang/rust' }, starred_at: '2023-05-10T12:00:00Z' },
    { repo: { full_name: 'facebook/react', description: 'The library for web and native user interfaces', language: 'JavaScript', stargazers_count: 228000, forks_count: 46500, topics: ['react', 'javascript', 'ui', 'frontend'], html_url: 'https://github.com/facebook/react' }, starred_at: '2022-11-05T09:00:00Z' },
    { repo: { full_name: 'tensorflow/tensorflow', description: 'An Open Source Machine Learning Framework', language: 'C++', stargazers_count: 186000, forks_count: 74000, topics: ['machine-learning', 'deep-learning', 'tensorflow', 'python'], html_url: 'https://github.com/tensorflow/tensorflow' }, starred_at: '2022-08-18T14:00:00Z' },
    { repo: { full_name: 'microsoft/vscode', description: 'Visual Studio Code', language: 'TypeScript', stargazers_count: 164000, forks_count: 29000, topics: ['editor', 'typescript', 'electron'], html_url: 'https://github.com/microsoft/vscode' }, starred_at: '2023-07-22T16:00:00Z' },
    { repo: { full_name: 'denoland/deno', description: 'A modern runtime for JavaScript and TypeScript', language: 'Rust', stargazers_count: 94000, forks_count: 5200, topics: ['deno', 'typescript', 'runtime', 'rust'], html_url: 'https://github.com/denoland/deno' }, starred_at: '2023-09-01T11:00:00Z' },
    { repo: { full_name: 'python/cpython', description: 'The Python programming language', language: 'Python', stargazers_count: 63000, forks_count: 30000, topics: ['python', 'cpython'], html_url: 'https://github.com/python/cpython' }, starred_at: '2023-02-14T07:00:00Z' },
  ];

  /* ---------- Fetch All Starred Repos (paginated) ---------- */
  function fetchAllStarred(username) {
    var allRepos = [];
    var perPage = 100;
    var maxPages = 3; // limit to 300 repos for unauthenticated

    function fetchPage(page) {
      if (page > maxPages) return Promise.resolve(allRepos);
      var url = 'https://api.github.com/users/' + encodeURIComponent(username) + '/starred?per_page=' + perPage + '&page=' + page;
      return fetchWithRetry(url, {
        headers: { 'Accept': 'application/vnd.github.v3.star+json' }
      }).then(function (res) {
        return res.json();
      }).then(function (data) {
        if (!Array.isArray(data) || data.length === 0) return allRepos;
        allRepos = allRepos.concat(data);
        if (data.length < perPage) return allRepos;
        return fetchPage(page + 1);
      });
    }

    return fetchPage(1);
  }

  /* ---------- Data Processing ---------- */
  function processStarData(starredData) {
    var repos = starredData.map(function (item) {
      return {
        name: item.repo ? item.repo.full_name : (item.full_name || ''),
        description: item.repo ? item.repo.description : (item.description || ''),
        language: item.repo ? item.repo.language : (item.language || null),
        stars: item.repo ? item.repo.stargazers_count : (item.stargazers_count || 0),
        forks: item.repo ? item.repo.forks_count : (item.forks_count || 0),
        topics: item.repo ? (item.repo.topics || []) : (item.topics || []),
        url: item.repo ? item.repo.html_url : (item.html_url || '#'),
        starred_at: item.starred_at || null,
      };
    });

    // Language distribution
    var langMap = {};
    repos.forEach(function (r) {
      var lang = r.language || 'Unknown';
      langMap[lang] = (langMap[lang] || 0) + 1;
    });
    var langEntries = Object.entries(langMap).sort(function (a, b) { return b[1] - a[1]; });

    // Star timeline (by month)
    var timelineMap = {};
    repos.forEach(function (r) {
      if (r.starred_at) {
        var d = new Date(r.starred_at);
        var key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
        timelineMap[key] = (timelineMap[key] || 0) + 1;
      }
    });
    var timelineEntries = Object.entries(timelineMap).sort(function (a, b) { return a[0].localeCompare(b[0]); });

    // Top repos by stars
    var topRepos = repos.slice().sort(function (a, b) { return b.stars - a.stars; }).slice(0, 12);

    // Topic cloud
    var topicMap = {};
    repos.forEach(function (r) {
      r.topics.forEach(function (t) {
        topicMap[t] = (topicMap[t] || 0) + 1;
      });
    });
    var topicEntries = Object.entries(topicMap).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 40);

    // Interest pattern
    var topLang = langEntries.length > 0 ? langEntries[0][0] : 'N/A';
    var pattern = 'Explorer';
    if (langEntries.length >= 5) pattern = 'Polyglot';
    if (langEntries.length <= 2 && repos.length > 10) pattern = 'Specialist';
    if (repos.length > 100) pattern = 'Collector';

    return {
      total: repos.length,
      topLang: topLang,
      pattern: pattern,
      langEntries: langEntries,
      timelineEntries: timelineEntries,
      topRepos: topRepos,
      topicEntries: topicEntries,
    };
  }

  /* ---------- Charts ---------- */
  var langChartInstance = null;
  var timelineChartInstance = null;

  function getChartColors() {
    var style = getComputedStyle(document.documentElement);
    return {
      text: style.getPropertyValue('--chart-text').trim(),
      grid: style.getPropertyValue('--chart-grid').trim(),
      accent: style.getPropertyValue('--color-accent').trim(),
    };
  }

  function renderLangChart(langEntries) {
    els.langSkeleton.remove();
    var top = langEntries.slice(0, 10);
    var otherCount = langEntries.slice(10).reduce(function (s, e) { return s + e[1]; }, 0);
    if (otherCount > 0) top.push(['Other', otherCount]);

    var labels = top.map(function (e) { return e[0]; });
    var data = top.map(function (e) { return e[1]; });
    var colors = top.map(function (e) {
      return GITHUB_LANG_COLORS[e[0]] || '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
    });

    var cc = getChartColors();
    langChartInstance = new Chart(els.langChart, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors,
          borderColor: 'transparent',
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            titleFont: { family: "'JetBrains Mono', monospace", size: 12 },
            bodyFont: { family: "'Figtree', sans-serif", size: 13 },
            padding: 10,
            cornerRadius: 6,
          },
        },
      },
    });

    // Render legend
    var total = data.reduce(function (s, v) { return s + v; }, 0);
    els.langLegend.innerHTML = top.map(function (e, i) {
      var pct = ((e[1] / total) * 100).toFixed(1);
      return '<div class="lang-legend__item">' +
        '<span class="lang-legend__dot" style="background:' + colors[i] + '"></span>' +
        '<span class="lang-legend__name">' + e[0] + '</span>' +
        '<span class="lang-legend__count">' + e[1] + '</span>' +
        '<span class="lang-legend__pct">' + pct + '%</span>' +
        '</div>';
    }).join('');
  }

  function renderTimelineChart(timelineEntries) {
    els.timelineSkeleton.remove();
    if (timelineEntries.length === 0) {
      els.timelineChartContainer.innerHTML = '<p style="text-align:center;padding:2rem;color:var(--color-text-secondary)">No timeline data available (starred_at requires star+json accept header)</p>';
      return;
    }

    var labels = timelineEntries.map(function (e) { return e[0]; });
    var data = timelineEntries.map(function (e) { return e[1]; });
    var cc = getChartColors();

    timelineChartInstance = new Chart(els.timelineChart, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Stars',
          data: data,
          backgroundColor: cc.accent + '88',
          borderColor: cc.accent,
          borderWidth: 1,
          borderRadius: 3,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            titleFont: { family: "'JetBrains Mono', monospace", size: 12 },
            bodyFont: { family: "'Figtree', sans-serif", size: 13 },
            padding: 10,
            cornerRadius: 6,
          },
        },
        scales: {
          x: {
            ticks: { color: cc.text, font: { family: "'JetBrains Mono', monospace", size: 10 }, maxRotation: 45 },
            grid: { color: cc.grid },
          },
          y: {
            beginAtZero: true,
            ticks: { color: cc.text, font: { family: "'JetBrains Mono', monospace", size: 10 }, stepSize: 1 },
            grid: { color: cc.grid },
          },
        },
      },
    });
  }

  function updateChartColors() {
    var cc = getChartColors();
    if (timelineChartInstance) {
      timelineChartInstance.data.datasets[0].backgroundColor = cc.accent + '88';
      timelineChartInstance.data.datasets[0].borderColor = cc.accent;
      timelineChartInstance.options.scales.x.ticks.color = cc.text;
      timelineChartInstance.options.scales.x.grid.color = cc.grid;
      timelineChartInstance.options.scales.y.ticks.color = cc.text;
      timelineChartInstance.options.scales.y.grid.color = cc.grid;
      timelineChartInstance.update('none');
    }
  }

  /* ---------- Render Repos ---------- */
  function renderRepos(topRepos) {
    els.reposGrid.innerHTML = topRepos.map(function (r) {
      var langBadge = r.language
        ? '<span class="star-card__lang">' + r.language + '</span>'
        : '';
      return '<article class="star-card">' +
        '<div class="star-card__header">' +
          '<a class="star-card__name" href="' + r.url + '" target="_blank" rel="noopener">' + r.name + '</a>' +
          langBadge +
        '</div>' +
        '<p class="star-card__desc">' + (r.description || 'No description') + '</p>' +
        '<div class="star-card__meta">' +
          '<span class="star-card__meta-item">★ ' + formatNumber(r.stars) + '</span>' +
          '<span class="star-card__meta-item">⑂ ' + formatNumber(r.forks) + '</span>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  /* ---------- Render Tag Cloud ---------- */
  function renderTagCloud(topicEntries) {
    if (topicEntries.length === 0) {
      els.tagCloud.innerHTML = '<p style="color:var(--color-text-secondary)">No topics found in starred repositories</p>';
      return;
    }
    var maxCount = topicEntries[0][1];
    els.tagCloud.innerHTML = topicEntries.map(function (e) {
      var ratio = e[1] / maxCount;
      var sizeClass = 'tag--xs';
      if (ratio > 0.8) sizeClass = 'tag--xl';
      else if (ratio > 0.5) sizeClass = 'tag--lg';
      else if (ratio > 0.3) sizeClass = 'tag--md';
      else if (ratio > 0.15) sizeClass = 'tag--sm';
      return '<span class="tag ' + sizeClass + '" title="' + e[1] + ' repos">' + e[0] + '</span>';
    }).join('');
  }

  /* ---------- Helpers ---------- */
  function formatNumber(n) {
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
    return String(n);
  }

  /* ---------- GSAP Animations — D8: translateX(40px) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero: asymmetric entrance */
    gsap.from('.hero__main', {
      x: 40, opacity: 0, duration: 1, ease: 'power3.out',
    });
    gsap.from('.hero__aside', {
      x: 40, opacity: 0, duration: 1, delay: 0.2, ease: 'power3.out',
    });

    /* D8: Bento cells slide from right */
    $$('.bento-cell').forEach(function (cell, i) {
      gsap.from(cell, {
        scrollTrigger: { trigger: cell, start: 'top 85%', once: true },
        x: 40, opacity: 0, duration: 0.7, delay: i * 0.08, ease: 'power3.out',
      });
    });
  }

  function animateCards() {
    if (prefersReducedMotion) return;
    $$('.star-card').forEach(function (card, i) {
      gsap.from(card, {
        scrollTrigger: { trigger: card, start: 'top 85%', once: true },
        x: 40, opacity: 0, duration: 0.6, delay: i * 0.05, ease: 'power3.out',
      });
    });
    $$('.tag').forEach(function (tag, i) {
      gsap.from(tag, {
        scrollTrigger: { trigger: tag, start: 'top 90%', once: true },
        x: 40, opacity: 0, duration: 0.4, delay: i * 0.02, ease: 'power3.out',
      });
    });
  }

  /* ---------- Main Load ---------- */
  function loadData() {
    fetchAllStarred(CONFIG.githubUsername)
      .then(function (data) {
        var processed = processStarData(data);

        // Update hero stats
        els.statTotalStars.textContent = processed.total;
        els.statTopLang.textContent = processed.topLang;
        els.statPattern.textContent = processed.pattern;

        // Render charts
        renderLangChart(processed.langEntries);
        renderTimelineChart(processed.timelineEntries);

        // Render repos
        renderRepos(processed.topRepos);

        // Render tag cloud
        renderTagCloud(processed.topicEntries);

        // Animate after render
        setTimeout(function () {
          animateCards();
          ScrollTrigger.refresh();
        }, 100);
      })
      .catch(function (err) {
        console.warn('GitHub API failed, using fallback data:', err.message);
        var processed = processStarData(FALLBACK_STARRED);
        els.statTotalStars.textContent = processed.total;
        els.statTopLang.textContent = processed.topLang;
        els.statPattern.textContent = processed.pattern;
        renderLangChart(processed.langEntries);
        renderTimelineChart(processed.timelineEntries);
        renderRepos(processed.topRepos);
        renderTagCloud(processed.topicEntries);
        setTimeout(function () { animateCards(); ScrollTrigger.refresh(); }, 100);
      });
  }

  function showError(section) {
    if (section === 'lang') {
      els.langSkeleton.remove();
      els.langError.hidden = false;
    } else if (section === 'timeline') {
      els.timelineSkeleton.remove();
      els.timelineError.hidden = false;
    } else if (section === 'repos') {
      els.reposGrid.innerHTML = '';
      els.reposError.hidden = false;
    }
  }

  /* ---------- Init ---------- */
  function init() {
    initTheme();
    initHeroImage();
    updateClock();
    setInterval(updateClock, 1000);
    initAnimations();
    loadData();

    // Retry buttons
    els.langRetry.addEventListener('click', function () {
      els.langError.hidden = true;
      loadData();
    });
    els.timelineRetry.addEventListener('click', function () {
      els.timelineError.hidden = true;
      loadData();
    });
    els.reposRetry.addEventListener('click', function () {
      els.reposError.hidden = true;
      loadData();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
