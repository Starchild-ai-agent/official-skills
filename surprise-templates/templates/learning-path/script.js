/* ============================================================
   Learning Path Generator — script.js

   Skeleton: A14 Vertical Timeline
   Hover: C13 底部边框
   Entrance: D3 translateX(30px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Data ---------- */
  var SKILLS = ['HTML/CSS', 'JavaScript', 'React', 'Node.js', 'TypeScript', 'Testing'];
  var SKILL_LEVELS = {
    beginner:     [30, 20, 10, 5, 5, 5],
    intermediate: [80, 65, 50, 40, 35, 30],
    advanced:     [95, 90, 85, 80, 75, 70],
  };

  var TIMELINE = {
    beginner: [
      { phase: 'Week 1-2', title: 'HTML & CSS Fundamentals', desc: 'Learn semantic HTML, CSS box model, flexbox, and grid layouts.', duration: '2 weeks', topics: ['HTML5', 'CSS3', 'Flexbox', 'Grid'] },
      { phase: 'Week 3-5', title: 'JavaScript Basics', desc: 'Variables, functions, DOM manipulation, events, and async patterns.', duration: '3 weeks', topics: ['ES6+', 'DOM', 'Fetch API', 'Promises'] },
      { phase: 'Week 6-8', title: 'React Introduction', desc: 'Components, JSX, props, state, and basic hooks.', duration: '3 weeks', topics: ['JSX', 'useState', 'useEffect', 'Props'] },
      { phase: 'Week 9-10', title: 'Build Your First Project', desc: 'Create a complete application combining everything learned.', duration: '2 weeks', topics: ['Project', 'Git', 'Deploy'] },
    ],
    intermediate: [
      { phase: 'Week 1-3', title: 'Advanced React Patterns', desc: 'Custom hooks, context, reducers, and performance optimization.', duration: '3 weeks', topics: ['Custom Hooks', 'Context', 'useReducer', 'Memo'] },
      { phase: 'Week 4-6', title: 'TypeScript Integration', desc: 'Type system, generics, utility types, and React with TypeScript.', duration: '3 weeks', topics: ['Types', 'Generics', 'Interfaces', 'TSX'] },
      { phase: 'Week 7-9', title: 'Backend with Node.js', desc: 'Express, REST APIs, authentication, and database integration.', duration: '3 weeks', topics: ['Express', 'REST', 'Auth', 'PostgreSQL'] },
      { phase: 'Week 10-12', title: 'Testing & CI/CD', desc: 'Unit testing, integration testing, and deployment pipelines.', duration: '3 weeks', topics: ['Jest', 'RTL', 'GitHub Actions', 'Docker'] },
    ],
    advanced: [
      { phase: 'Week 1-3', title: 'System Design', desc: 'Architecture patterns, microservices, and scalability strategies.', duration: '3 weeks', topics: ['Microservices', 'Event-Driven', 'CQRS', 'DDD'] },
      { phase: 'Week 4-6', title: 'Performance Engineering', desc: 'Profiling, optimization, caching strategies, and monitoring.', duration: '3 weeks', topics: ['Profiling', 'Caching', 'CDN', 'Monitoring'] },
      { phase: 'Week 7-9', title: 'DevOps & Infrastructure', desc: 'Kubernetes, Terraform, observability, and incident response.', duration: '3 weeks', topics: ['K8s', 'Terraform', 'Grafana', 'SRE'] },
      { phase: 'Week 10-12', title: 'Open Source Contribution', desc: 'Contributing to major projects, RFC process, and community building.', duration: '3 weeks', topics: ['OSS', 'RFC', 'Community', 'Mentoring'] },
    ],
  };

  var RESOURCES = [
    { type: 'Course', title: 'Frontend Masters', desc: 'In-depth courses from industry experts', meta: ['Video', 'Paid'] },
    { type: 'Book', title: 'Eloquent JavaScript', desc: 'Comprehensive guide to modern JavaScript', meta: ['Free', 'Online'] },
    { type: 'Practice', title: 'LeetCode', desc: 'Algorithm and data structure challenges', meta: ['Interactive', 'Free tier'] },
    { type: 'Docs', title: 'MDN Web Docs', desc: 'The definitive web technology reference', meta: ['Free', 'Mozilla'] },
    { type: 'Community', title: 'Dev.to', desc: 'Developer community with tutorials and discussions', meta: ['Free', 'Social'] },
    { type: 'Tool', title: 'CodeSandbox', desc: 'Online IDE for rapid prototyping', meta: ['Free', 'Browser'] },
  ];

  var MILESTONES = [
    'Complete HTML/CSS basics',
    'Build first responsive page',
    'Write first JavaScript function',
    'Create a React component',
    'Deploy to production',
    'Write first unit test',
    'Contribute to open source',
    'Build a full-stack app',
  ];

  var currentLevel = 'beginner';
  var radarChart = null;

  /* ---------- Theme ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('lp-theme', theme);
    if (radarChart) updateRadarColors();
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    setTheme(current === 'light' ? 'dark' : 'light');
  });
  var savedTheme = localStorage.getItem('lp-theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(savedTheme);

  /* ---------- Level Selector ---------- */
  document.querySelectorAll('.level-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.level-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentLevel = btn.getAttribute('data-level');
      updateRadarData();
      renderTimeline();
    });
  });

  /* ---------- Radar Chart ---------- */
  function initRadar() {
    var ctx = document.getElementById('radar-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)';
    var labelColor = isDark ? 'rgba(232,245,232,0.6)' : 'rgba(26,46,26,0.6)';

    radarChart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: SKILLS,
        datasets: [{
          label: 'Skill Level',
          data: SKILL_LEVELS[currentLevel],
          backgroundColor: 'rgba(5,150,105,0.15)',
          borderColor: '#059669',
          borderWidth: 2,
          pointBackgroundColor: '#059669',
          pointRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            ticks: { stepSize: 20, display: false },
            grid: { color: gridColor },
            angleLines: { color: gridColor },
            pointLabels: { color: labelColor, font: { family: "'Karla', sans-serif", size: 12 } },
          },
        },
        plugins: { legend: { display: false } },
      },
    });
  }

  function updateRadarData() {
    if (!radarChart) return;
    radarChart.data.datasets[0].data = SKILL_LEVELS[currentLevel];
    radarChart.update();
  }

  function updateRadarColors() {
    if (!radarChart) return;
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)';
    var labelColor = isDark ? 'rgba(232,245,232,0.6)' : 'rgba(26,46,26,0.6)';
    var accent = isDark ? '#34d399' : '#059669';
    radarChart.options.scales.r.grid.color = gridColor;
    radarChart.options.scales.r.angleLines.color = gridColor;
    radarChart.options.scales.r.pointLabels.color = labelColor;
    radarChart.data.datasets[0].borderColor = accent;
    radarChart.data.datasets[0].pointBackgroundColor = accent;
    radarChart.data.datasets[0].backgroundColor = isDark ? 'rgba(52,211,153,0.15)' : 'rgba(5,150,105,0.15)';
    radarChart.update();
  }

  /* ---------- Render Timeline ---------- */
  function renderTimeline() {
    var list = document.getElementById('timeline-list');
    var items = TIMELINE[currentLevel];
    var html = '';
    items.forEach(function (item) {
      var topicsHtml = item.topics.map(function (t) {
        return '<span class="timeline-item__topic">' + t + '</span>';
      }).join('');
      html += '<div class="timeline-item">' +
        '<div class="timeline-item__dot"></div>' +
        '<div class="timeline-item__phase">' + item.phase + '</div>' +
        '<div class="timeline-item__title">' + item.title + '</div>' +
        '<div class="timeline-item__desc">' + item.desc + '</div>' +
        '<div class="timeline-item__duration">' + item.duration + '</div>' +
        '<div class="timeline-item__topics">' + topicsHtml + '</div>' +
        '</div>';
    });
    list.innerHTML = html;

    if (!prefersReducedMotion) {
      gsap.utils.toArray('.timeline-item').forEach(function (el, i) {
        gsap.from(el, {
          scrollTrigger: { trigger: el, start: 'top 88%', toggleActions: 'play none none none' },
          opacity: 0, x: 30, duration: 0.5, delay: i * 0.08, ease: 'power2.out',
        });
      });
    }
  }

  /* ---------- Render Resources ---------- */
  function renderResources() {
    var grid = document.getElementById('resources-grid');
    var html = '';
    RESOURCES.forEach(function (res) {
      var metaHtml = res.meta.map(function (m) { return '<span>' + m + '</span>'; }).join(' \u00b7 ');
      html += '<div class="resource-card">' +
        '<div class="resource-card__type">' + res.type + '</div>' +
        '<div class="resource-card__title">' + res.title + '</div>' +
        '<div class="resource-card__desc">' + res.desc + '</div>' +
        '<div class="resource-card__meta">' + metaHtml + '</div>' +
        '</div>';
    });
    grid.innerHTML = html;
  }

  /* ---------- Render Milestones ---------- */
  function renderMilestones() {
    var list = document.getElementById('milestones-list');
    var html = '';
    MILESTONES.forEach(function (m, i) {
      html += '<div class="milestone" data-index="' + i + '">' +
        '<div class="milestone__check">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' +
        '</div>' +
        '<span class="milestone__text">' + m + '</span>' +
        '</div>';
    });
    list.innerHTML = html;

    list.querySelectorAll('.milestone').forEach(function (el) {
      el.addEventListener('click', function () {
        el.classList.toggle('completed');
        updateProgress();
      });
    });
  }

  function updateProgress() {
    var total = MILESTONES.length;
    var completed = document.querySelectorAll('.milestone.completed').length;
    var pct = Math.round((completed / total) * 100);
    document.getElementById('progress-fill').style.width = pct + '%';
    document.getElementById('progress-label').textContent = completed + ' / ' + total + ' completed';
  }

  /* ---------- GSAP Animations (D3 translateX(30px)) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__inline', { opacity: 0, x: 30, duration: 0.6, ease: 'power3.out' });
    gsap.from('.hero__title', { opacity: 0, x: 30, duration: 0.7, delay: 0.1, ease: 'power3.out' });
    gsap.from('.hero__level-selector', { opacity: 0, x: 30, duration: 0.5, delay: 0.25, ease: 'power3.out' });

    gsap.from('.radar-wrapper', {
      scrollTrigger: { trigger: '.radar-wrapper', start: 'top 85%' },
      opacity: 0, x: 30, duration: 0.7, ease: 'power2.out',
    });

    gsap.utils.toArray('.resource-card').forEach(function (el, i) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%' },
        opacity: 0, x: 30, duration: 0.5, delay: i * 0.06, ease: 'power2.out',
      });
    });

    gsap.utils.toArray('.milestone').forEach(function (el, i) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 90%' },
        opacity: 0, x: 30, duration: 0.4, delay: i * 0.04, ease: 'power2.out',
      });
    });

    gsap.utils.toArray('.section__title').forEach(function (el) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%' },
        opacity: 0, x: 30, duration: 0.6, ease: 'power3.out',
      });
    });
  }

  /* ---------- Init ---------- */
  initRadar();
  renderTimeline();
  renderResources();
  renderMilestones();
  updateProgress();
  initAnimations();

})();
