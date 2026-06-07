/* ============================================================
   Indie Developer Dashboard — script.js

   Pure frontend with built-in simulated indie community data.
   Renders trending projects, revenue milestones, tech stack
   trends chart, and startup idea generator.

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
      if (raw.startsWith('{{')) return 'Next.js, Python, Stripe';
      return raw;
    })(),
  };

  /* ---------- Simulated Indie Projects ---------- */
  var PROJECTS = [
    { name: 'Plausible Analytics', mrr: '$98K', desc: 'Simple, privacy-friendly alternative to Google Analytics. No cookies, fully compliant with GDPR.', tags: ['Elixir', 'React', 'PostgreSQL'], launched: 'Jan 2019', upvotes: 2847 },
    { name: 'Buttondown', mrr: '$45K', desc: 'The easiest way to start and grow your email newsletter. Markdown-first, developer-friendly.', tags: ['Python', 'Django', 'Stripe'], launched: 'Mar 2018', upvotes: 1923 },
    { name: 'Typefully', mrr: '$72K', desc: 'Write, schedule, and publish great tweets and threads. Built for creators who care about quality.', tags: ['TypeScript', 'Next.js', 'Prisma'], launched: 'Sep 2020', upvotes: 3102 },
    { name: 'Cal.com', mrr: '$120K', desc: 'Open-source scheduling infrastructure. The Calendly alternative for individuals and teams.', tags: ['TypeScript', 'Next.js', 'tRPC'], launched: 'Jun 2021', upvotes: 4521 },
    { name: 'Dub.co', mrr: '$35K', desc: 'Open-source link management for modern marketing teams. Analytics, QR codes, and branded links.', tags: ['TypeScript', 'Next.js', 'Tailwind'], launched: 'Aug 2022', upvotes: 2156 },
    { name: 'Pocketbase', mrr: '$8K', desc: 'Open-source backend in a single file. Realtime database, auth, file storage, and admin dashboard.', tags: ['Go', 'SQLite', 'Svelte'], launched: 'Jul 2022', upvotes: 5234 },
    { name: 'Logsnag', mrr: '$22K', desc: 'Event tracking for your projects. Get real-time notifications for signups, purchases, and errors.', tags: ['TypeScript', 'React', 'Redis'], launched: 'Nov 2021', upvotes: 1678 },
    { name: 'Resend', mrr: '$85K', desc: 'Email API for developers. Build, test, and deliver transactional emails at scale.', tags: ['TypeScript', 'React', 'Node.js'], launched: 'Jan 2023', upvotes: 3890 },
  ];

  /* ---------- Revenue Milestones ---------- */
  var MILESTONES = [
    { amount: '$0', title: 'The Idea', desc: 'You have a problem worth solving. Validate with 10 potential customers before writing code.', reached: true, examples: ['Talk to users', 'Landing page test', 'Waitlist'] },
    { amount: '$100 MRR', title: 'First Paying Customer', desc: 'Someone values your solution enough to pay. This is the hardest milestone — celebrate it.', reached: true, examples: ['Indie Hackers', 'Product Hunt', 'Twitter launch'] },
    { amount: '$1K MRR', title: 'Ramen Profitable', desc: 'You can cover basic expenses. Focus on retention and finding your ideal customer profile.', reached: true, examples: ['Plausible at 6mo', 'Buttondown at 8mo'] },
    { amount: '$5K MRR', title: 'Sustainable Solo', desc: 'Enough to live comfortably in many cities. Consider going full-time if you haven\'t already.', reached: false, examples: ['Quit day job', 'Hire first contractor'] },
    { amount: '$10K MRR', title: 'Real Business', desc: 'You\'re running a real business. Think about systems, automation, and maybe your first hire.', reached: false, examples: ['Typefully at 14mo', 'Cal.com at 10mo'] },
    { amount: '$50K MRR', title: 'Growth Engine', desc: 'Product-market fit is clear. Invest in growth channels and build a small team.', reached: false, examples: ['SEO flywheel', 'Content marketing'] },
    { amount: '$100K MRR', title: 'Financial Freedom', desc: 'You\'ve built something exceptional. Most indie hackers dream of reaching this level.', reached: false, examples: ['Plausible', 'Cal.com', 'Resend'] },
  ];

  /* ---------- Tech Stack Trends Data ---------- */
  var TECH_TRENDS = [
    { name: 'Next.js', count: 34, color: '#38bdf8' },
    { name: 'TypeScript', count: 31, color: '#3178c6' },
    { name: 'React', count: 28, color: '#61dafb' },
    { name: 'Tailwind CSS', count: 25, color: '#06b6d4' },
    { name: 'Python', count: 22, color: '#3572A5' },
    { name: 'Node.js', count: 20, color: '#68a063' },
    { name: 'PostgreSQL', count: 18, color: '#336791' },
    { name: 'Stripe', count: 16, color: '#635bff' },
    { name: 'Prisma', count: 14, color: '#2D3748' },
    { name: 'Go', count: 12, color: '#00ADD8' },
    { name: 'Svelte', count: 10, color: '#ff3e00' },
    { name: 'Redis', count: 9, color: '#dc382d' },
  ];

  /* ---------- Startup Ideas ---------- */
  var IDEAS = [
    { category: 'Developer Tools', title: 'AI Code Review Bot', desc: 'A GitHub bot that automatically reviews PRs for security vulnerabilities, performance issues, and code style. Charges per repo per month.', difficulty: 'Medium', market: 'B2B SaaS', tech: ['Python', 'GitHub API', 'OpenAI'] },
    { category: 'Productivity', title: 'Async Standup Tool', desc: 'Replace daily standup meetings with async text/video updates. Integrates with Slack, Linear, and GitHub to auto-generate progress reports.', difficulty: 'Medium', market: 'B2B SaaS', tech: ['Next.js', 'Slack API', 'PostgreSQL'] },
    { category: 'Creator Economy', title: 'Newsletter Analytics Dashboard', desc: 'Deep analytics for newsletter creators — open rates by segment, click heatmaps, subscriber lifetime value, and churn prediction.', difficulty: 'Hard', market: 'B2C SaaS', tech: ['TypeScript', 'React', 'Stripe'] },
    { category: 'E-commerce', title: 'Micro-SaaS for Shopify Reviews', desc: 'AI-powered review management for Shopify stores. Auto-respond to reviews, generate review request emails, and analyze sentiment trends.', difficulty: 'Medium', market: 'Shopify App', tech: ['Node.js', 'Shopify API', 'OpenAI'] },
    { category: 'Health & Wellness', title: 'Developer Ergonomics Tracker', desc: 'Desktop app that monitors posture, screen time, and typing patterns. Sends break reminders and generates weekly health reports.', difficulty: 'Hard', market: 'B2C Desktop', tech: ['Electron', 'Python', 'TensorFlow'] },
    { category: 'Education', title: 'Interactive SQL Playground', desc: 'Learn SQL by solving real-world data puzzles. Progressive difficulty, instant feedback, and a leaderboard. Monetize with premium courses.', difficulty: 'Easy', market: 'B2C Freemium', tech: ['Next.js', 'PostgreSQL', 'Stripe'] },
    { category: 'Finance', title: 'Freelancer Invoice Automation', desc: 'Auto-generate invoices from time tracking data. Supports multiple currencies, tax calculations, and payment reminders via Stripe.', difficulty: 'Easy', market: 'B2C SaaS', tech: ['React', 'Node.js', 'Stripe'] },
    { category: 'Developer Tools', title: 'API Monitoring Dashboard', desc: 'Monitor your API endpoints for uptime, latency, and error rates. Get alerts via Slack, email, or SMS when things break.', difficulty: 'Medium', market: 'B2B SaaS', tech: ['Go', 'React', 'Redis'] },
    { category: 'Content', title: 'Blog SEO Optimizer', desc: 'Analyze blog posts for SEO best practices. Suggest keyword improvements, internal linking opportunities, and readability scores.', difficulty: 'Easy', market: 'B2C Freemium', tech: ['Python', 'Next.js', 'NLP'] },
    { category: 'Social', title: 'Community Engagement Platform', desc: 'Help community managers track engagement metrics, identify top contributors, and automate welcome sequences across Discord and Slack.', difficulty: 'Hard', market: 'B2B SaaS', tech: ['TypeScript', 'Discord API', 'PostgreSQL'] },
    { category: 'Design', title: 'Component Screenshot Tool', desc: 'Capture beautiful screenshots of UI components with customizable backgrounds, shadows, and device frames. One-click export for docs and social.', difficulty: 'Easy', market: 'B2C Freemium', tech: ['React', 'Canvas API', 'Tailwind'] },
    { category: 'Productivity', title: 'Meeting Cost Calculator', desc: 'Chrome extension that shows the real-time cost of meetings based on attendee salaries. Integrates with Google Calendar to track weekly meeting spend.', difficulty: 'Easy', market: 'B2C Free + Premium', tech: ['Chrome Extension', 'JavaScript', 'Google API'] },
  ];

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return Array.from(document.querySelectorAll(sel)); };

  var els = {
    themeToggle: $('#theme-toggle'),
    heroTime: $('#hero-time'),
    heroBgImage: $('.hero__bg-image'),
    statInspiration: $('#stat-inspiration'),
    statFeatured: $('#stat-featured'),
    projectsGrid: $('#projects-grid'),
    milestonesTimeline: $('#milestones-timeline'),
    trendsChartContainer: $('#trends-chart-container'),
    trendsSkeleton: $('#trends-skeleton'),
    trendsChart: $('#trends-chart'),
    ideaCategory: $('#idea-category'),
    ideaTitle: $('#idea-title'),
    ideaDesc: $('#idea-desc'),
    ideaDifficulty: $('#idea-difficulty'),
    ideaMarket: $('#idea-market'),
    ideaStack: $('#idea-stack'),
    btnGenerate: $('#btn-generate'),
    footerTime: $('#footer-time'),
  };

  /* ---------- Theme ---------- */
  function initTheme() {
    var saved = localStorage.getItem('indie-dev-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    }
    els.themeToggle.addEventListener('click', function () {
      var current = document.documentElement.getAttribute('data-theme');
      var next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('indie-dev-theme', next);
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
    var inspiration = Math.floor(Math.random() * 30) + 70;
    els.statInspiration.textContent = inspiration + '/100';
    var featured = PROJECTS[Math.floor(Math.random() * PROJECTS.length)];
    els.statFeatured.textContent = featured.name;
  }

  /* ---------- Render Projects ---------- */
  function renderProjects() {
    els.projectsGrid.innerHTML = PROJECTS.map(function (p) {
      var tagsHtml = p.tags.map(function (t) {
        return '<span class="project-item__tag">' + t + '</span>';
      }).join('');
      return '<article class="project-item">' +
        '<div class="project-item__header">' +
          '<span class="project-item__name">' + p.name + '</span>' +
          '<span class="project-item__mrr">' + p.mrr + ' MRR</span>' +
        '</div>' +
        '<p class="project-item__desc">' + p.desc + '</p>' +
        '<div class="project-item__tags">' + tagsHtml + '</div>' +
        '<div class="project-item__meta">' +
          '<span>Launched ' + p.launched + '</span>' +
          '<span>' + p.upvotes.toLocaleString() + ' upvotes</span>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  /* ---------- Render Milestones ---------- */
  function renderMilestones() {
    els.milestonesTimeline.innerHTML = MILESTONES.map(function (m) {
      var reachedClass = m.reached ? ' milestone--reached' : '';
      var examplesHtml = m.examples.map(function (e) {
        return '<span class="milestone__example">' + e + '</span>';
      }).join('');
      return '<div class="milestone' + reachedClass + '">' +
        '<div class="milestone__dot"></div>' +
        '<div class="milestone__amount">' + m.amount + '</div>' +
        '<div class="milestone__title">' + m.title + '</div>' +
        '<p class="milestone__desc">' + m.desc + '</p>' +
        '<div class="milestone__examples">' + examplesHtml + '</div>' +
      '</div>';
    }).join('');
  }

  /* ---------- Tech Trends Chart ---------- */
  var trendsChartInstance = null;

  function getChartColors() {
    var style = getComputedStyle(document.documentElement);
    return {
      text: style.getPropertyValue('--chart-text').trim(),
      grid: style.getPropertyValue('--chart-grid').trim(),
      accent: style.getPropertyValue('--color-accent').trim(),
    };
  }

  function renderTrendsChart() {
    els.trendsSkeleton.remove();
    var cc = getChartColors();

    trendsChartInstance = new Chart(els.trendsChart, {
      type: 'bar',
      data: {
        labels: TECH_TRENDS.map(function (t) { return t.name; }),
        datasets: [{
          label: 'Projects Using',
          data: TECH_TRENDS.map(function (t) { return t.count; }),
          backgroundColor: TECH_TRENDS.map(function (t) { return t.color + 'cc'; }),
          borderColor: TECH_TRENDS.map(function (t) { return t.color; }),
          borderWidth: 1,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            titleFont: { family: "'IBM Plex Mono', monospace", size: 12 },
            bodyFont: { family: "'Karla', sans-serif", size: 13 },
            padding: 10,
            cornerRadius: 6,
            callbacks: {
              label: function (ctx) { return ctx.parsed.x + ' indie projects'; },
            },
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: { color: cc.text, font: { family: "'IBM Plex Mono', monospace", size: 10 } },
            grid: { color: cc.grid },
          },
          y: {
            ticks: { color: cc.text, font: { family: "'IBM Plex Mono', monospace", size: 11 } },
            grid: { display: false },
          },
        },
      },
    });
  }

  function updateChartColors() {
    if (!trendsChartInstance) return;
    var cc = getChartColors();
    trendsChartInstance.options.scales.x.ticks.color = cc.text;
    trendsChartInstance.options.scales.x.grid.color = cc.grid;
    trendsChartInstance.options.scales.y.ticks.color = cc.text;
    trendsChartInstance.update('none');
  }

  /* ---------- Idea Generator ---------- */
  var currentIdeaIndex = -1;

  function generateIdea() {
    var idx;
    do {
      idx = Math.floor(Math.random() * IDEAS.length);
    } while (idx === currentIdeaIndex && IDEAS.length > 1);
    currentIdeaIndex = idx;

    var idea = IDEAS[idx];
    els.ideaCategory.textContent = idea.category;
    els.ideaTitle.textContent = idea.title;
    els.ideaDesc.textContent = idea.desc;
    els.ideaDifficulty.textContent = 'Difficulty: ' + idea.difficulty;
    els.ideaMarket.textContent = idea.market;
    els.ideaStack.innerHTML = idea.tech.map(function (t) {
      return '<span class="idea-card__tech">' + t + '</span>';
    }).join('');

    if (!prefersReducedMotion) {
      gsap.from('.idea-card', { scale: 0.98, opacity: 0.5, duration: 0.4, ease: 'power2.out' });
    }
  }

  /* ---------- GSAP Animations — D1: translateY(40px) stagger 0.1s ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero minimal entrance */
    gsap.from('.hero__minimal', {
      y: 40, opacity: 0, duration: 0.8, ease: 'power3.out',
    });

    /* D1: Feed items stagger from top */
    $$('.feed-item').forEach(function (item, i) {
      gsap.from(item, {
        scrollTrigger: { trigger: item, start: 'top 85%', once: true },
        y: 40, opacity: 0, duration: 0.7, delay: i * 0.1, ease: 'power3.out',
      });
    });

    /* D1: Project items stagger */
    setTimeout(function () {
      $$('.project-item').forEach(function (card, i) {
        gsap.from(card, {
          scrollTrigger: { trigger: card, start: 'top 85%', once: true },
          y: 40, opacity: 0, duration: 0.6, delay: i * 0.1, ease: 'power3.out',
        });
      });

      /* D1: Milestones stagger */
      $$('.milestone').forEach(function (m, i) {
        gsap.from(m, {
          scrollTrigger: { trigger: m, start: 'top 85%', once: true },
          y: 40, opacity: 0, duration: 0.6, delay: i * 0.1, ease: 'power3.out',
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

    updateHeroStats();
    renderProjects();
    renderMilestones();
    renderTrendsChart();
    generateIdea();

    els.btnGenerate.addEventListener('click', generateIdea);

    initAnimations();
    setTimeout(function () { ScrollTrigger.refresh(); }, 300);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
