/* ============================================================
   Open Source Monetization Guide — script.js

   Skeleton: A17 Full-width Sections
   Hover: C22 outline
   Entrance: D17 translateY(-30px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Data ---------- */
  var STRATEGIES = [
    { icon: '\u2764\uFE0F', title: 'Sponsorships & Donations', desc: 'Set up GitHub Sponsors, Open Collective, or Patreon. Offer sponsor tiers with perks like logo placement, priority support, and early access to features. Most sustainable for projects with strong community engagement.', revenue: 'Typical: $500-$10,000/mo for popular projects' },
    { icon: '\u{1F4BB}', title: 'Open Core / SaaS', desc: 'Keep the core open source while offering a hosted version or premium features. This is the most scalable model. Examples: GitLab, Supabase, PostHog. Requires significant engineering investment.', revenue: 'Typical: $5,000-$500,000+/mo at scale' },
    { icon: '\u{1F393}', title: 'Consulting & Training', desc: 'Offer paid consulting, implementation services, or training workshops. You are the expert on your own tool. Companies will pay for your time to help them adopt and customize it.', revenue: 'Typical: $150-$400/hr consulting rate' },
    { icon: '\u{1F4DA}', title: 'Courses & Content', desc: 'Create premium courses, books, or video content teaching advanced usage of your project. Platforms like Gumroad, Teachable, or self-hosted. Low ongoing cost, high margin.', revenue: 'Typical: $2,000-$20,000/mo passive income' },
  ];

  var STORIES = [
    { name: 'Caleb Porzio', project: 'Livewire / Alpine.js', desc: 'Built a sustainable business through GitHub Sponsors and premium screencasts, earning over $100k/year.', revenue: '$100k+/yr' },
    { name: 'Guillermo Rauch', project: 'Next.js / Vercel', desc: 'Turned an open source framework into a $2.5B company by offering a managed hosting platform.', revenue: '$2.5B valuation' },
    { name: 'Evan You', project: 'Vue.js', desc: 'Full-time open source maintainer funded entirely by sponsors and Patreon supporters.', revenue: '$40k+/mo sponsors' },
    { name: 'Adam Wathan', project: 'Tailwind CSS', desc: 'Created Tailwind UI, a premium component library, generating millions in revenue alongside the free framework.', revenue: '$10M+ total' },
    { name: 'Sindre Sorhus', project: '1000+ npm packages', desc: 'Pioneered the full-time open source model through GitHub Sponsors with transparent funding goals.', revenue: '$10k+/mo sponsors' },
    { name: 'Zeno Rocha', project: 'Dracula Theme', desc: 'Monetized a popular open source theme through a PRO version with additional features and support.', revenue: '$500k+ total' },
  ];

  var ACTIONS = [
    'Set up GitHub Sponsors profile with compelling description',
    'Create a FUNDING.yml file in your repository',
    'Add a "Sponsor" button to your README',
    'Write a blog post about your project sustainability goals',
    'Create sponsor tiers with clear value propositions',
    'Set up Open Collective for organizational sponsors',
    'Build a landing page for your premium offering',
    'Create a mailing list for potential customers',
    'Reach out to companies using your project',
    'Document your monetization journey publicly',
  ];

  /* ---------- Theme ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('osm-theme', theme);
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'dark';
    setTheme(current === 'dark' ? 'light' : 'dark');
  });
  var savedTheme = localStorage.getItem('osm-theme') ||
    (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  setTheme(savedTheme);

  /* ---------- Render Strategies ---------- */
  function renderStrategies() {
    var list = document.getElementById('strategies-list');
    var html = '';
    STRATEGIES.forEach(function (s) {
      html += '<div class="strategy-block">' +
        '<div class="strategy-block__icon">' + s.icon + '</div>' +
        '<div class="strategy-block__title">' + s.title + '</div>' +
        '<div class="strategy-block__desc">' + s.desc + '</div>' +
        '<div class="strategy-block__revenue">' + s.revenue + '</div>' +
        '</div>';
    });
    list.innerHTML = html;
  }

  /* ---------- Calculator ---------- */
  function updateCalculator() {
    var stars = parseInt(document.getElementById('calc-stars').value) || 0;
    var downloads = parseInt(document.getElementById('calc-downloads').value) || 0;
    var sponsorRate = parseFloat(document.getElementById('calc-sponsors').value) || 0;

    var sponsorCount = Math.floor(stars * (sponsorRate / 100));
    var avgSponsor = 10;
    var sponsorRevenue = sponsorCount * avgSponsor;
    var downloadRevenue = Math.floor(downloads * 0.001) * 5;
    var total = sponsorRevenue + downloadRevenue;

    document.getElementById('calc-result').textContent = '$' + total.toLocaleString();
  }

  document.getElementById('calc-stars').addEventListener('input', updateCalculator);
  document.getElementById('calc-downloads').addEventListener('input', updateCalculator);
  document.getElementById('calc-sponsors').addEventListener('input', updateCalculator);
  updateCalculator();

  /* ---------- Render Stories ---------- */
  function renderStories() {
    var grid = document.getElementById('stories-grid');
    var html = '';
    STORIES.forEach(function (s) {
      html += '<div class="story-card">' +
        '<div class="story-card__name">' + s.name + '</div>' +
        '<div class="story-card__project">' + s.project + '</div>' +
        '<div class="story-card__desc">' + s.desc + '</div>' +
        '<div class="story-card__revenue">' + s.revenue + '</div>' +
        '</div>';
    });
    grid.innerHTML = html;
  }

  /* ---------- Render Actions ---------- */
  function renderActions() {
    var list = document.getElementById('action-list');
    var html = '';
    ACTIONS.forEach(function (a, i) {
      html += '<div class="action-item" data-index="' + i + '">' +
        '<div class="action-item__check">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' +
        '</div>' +
        '<span class="action-item__text">' + a + '</span>' +
        '</div>';
    });
    list.innerHTML = html;

    list.querySelectorAll('.action-item').forEach(function (el) {
      el.addEventListener('click', function () {
        el.classList.toggle('done');
      });
    });
  }

  /* ---------- GSAP Animations (D17 translateY(-30px)) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__label', { opacity: 0, y: -30, duration: 0.5, ease: 'power3.out' });
    gsap.from('.hero__title', { opacity: 0, y: -30, duration: 0.7, delay: 0.1, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { opacity: 0, y: -20, duration: 0.5, delay: 0.2, ease: 'power3.out' });
    gsap.from('.hero__stat-card', { opacity: 0, y: -30, duration: 0.6, delay: 0.3, ease: 'power2.out' });

    gsap.utils.toArray('.strategy-block').forEach(function (el, i) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%', toggleActions: 'play none none none' },
        opacity: 0, y: -30, duration: 0.6, delay: i * 0.08, ease: 'power2.out',
      });
    });

    gsap.from('.calculator-card', {
      scrollTrigger: { trigger: '.calculator-card', start: 'top 85%' },
      opacity: 0, y: -30, duration: 0.7, ease: 'power2.out',
    });

    gsap.utils.toArray('.story-card').forEach(function (el, i) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%' },
        opacity: 0, y: -30, duration: 0.5, delay: i * 0.06, ease: 'power2.out',
      });
    });

    gsap.utils.toArray('.action-item').forEach(function (el, i) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 92%' },
        opacity: 0, y: -20, duration: 0.4, delay: i * 0.04, ease: 'power2.out',
      });
    });

    gsap.utils.toArray('.section__title').forEach(function (el) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%' },
        opacity: 0, y: -25, duration: 0.6, ease: 'power3.out',
      });
    });
  }

  /* ---------- Init ---------- */
  renderStrategies();
  renderStories();
  renderActions();
  initAnimations();

})();
