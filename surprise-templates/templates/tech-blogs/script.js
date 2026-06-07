/* ============================================================
   Tech Blog Aggregator — script.js

   Skeleton: A19 Feed/Stream
   Hover: C8 border-left+translateX
   Entrance: D10 translateX(-50px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Mock Data ---------- */
  var ARTICLES = [
    { id: 1, source: 'Overreacted', title: 'A Complete Guide to useEffect', excerpt: 'Understanding the mental model behind useEffect and how it differs from lifecycle methods in class components.', category: 'frontend', readTime: 12, time: '2h ago', bookmarked: false },
    { id: 2, source: 'Martin Fowler', title: 'Microservices Trade-Offs', excerpt: 'When microservices make sense and when a monolith is the better choice for your team and product stage.', category: 'backend', readTime: 8, time: '4h ago', bookmarked: false },
    { id: 3, source: 'The Pragmatic Engineer', title: 'CI/CD Pipeline Best Practices', excerpt: 'Lessons from scaling deployment pipelines at companies processing millions of deployments per day.', category: 'devops', readTime: 15, time: '6h ago', bookmarked: false },
    { id: 4, source: 'Lilian Weng', title: 'Prompt Engineering Deep Dive', excerpt: 'A systematic exploration of prompt engineering techniques, from chain-of-thought to tree-of-thought reasoning.', category: 'ai', readTime: 20, time: '8h ago', bookmarked: false },
    { id: 5, source: 'CSS Tricks', title: 'Modern CSS Layout Techniques', excerpt: 'Container queries, subgrid, and the new CSS features that are changing how we build responsive layouts.', category: 'frontend', readTime: 10, time: '12h ago', bookmarked: false },
    { id: 6, source: 'Netflix Tech Blog', title: 'Scaling GraphQL at Netflix', excerpt: 'How Netflix evolved their API layer from REST to federated GraphQL serving billions of requests daily.', category: 'backend', readTime: 14, time: '1d ago', bookmarked: false },
    { id: 7, source: 'Kelsey Hightower', title: 'Kubernetes the Hard Way 2025', excerpt: 'Updated guide to bootstrapping Kubernetes clusters from scratch for deep understanding of the platform.', category: 'devops', readTime: 25, time: '1d ago', bookmarked: false },
    { id: 8, source: 'Andrej Karpathy', title: 'Building GPT from Scratch', excerpt: 'Step-by-step implementation of a GPT model, from tokenization to attention mechanisms to training loops.', category: 'ai', readTime: 30, time: '2d ago', bookmarked: false },
    { id: 9, source: 'Josh Comeau', title: 'The Joy of React Server Components', excerpt: 'A visual, interactive guide to understanding React Server Components and when to use them effectively.', category: 'frontend', readTime: 18, time: '2d ago', bookmarked: false },
    { id: 10, source: 'Stripe Engineering', title: 'Idempotency Keys in Practice', excerpt: 'How Stripe uses idempotency keys to ensure exactly-once semantics in distributed payment processing.', category: 'backend', readTime: 11, time: '3d ago', bookmarked: false },
  ];

  var currentCategory = 'all';
  var bookmarks = new Set();

  /* ---------- Theme ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('tb-theme', theme);
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    setTheme(current === 'light' ? 'dark' : 'light');
  });
  var savedTheme = localStorage.getItem('tb-theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(savedTheme);

  /* ---------- Category Tabs ---------- */
  document.querySelectorAll('.cat-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      document.querySelectorAll('.cat-tab').forEach(function (t) { t.classList.remove('active'); });
      tab.classList.add('active');
      currentCategory = tab.getAttribute('data-cat');
      renderFeed();
    });
  });

  /* ---------- Filter ---------- */
  function getFilteredArticles() {
    if (currentCategory === 'all') return ARTICLES;
    if (currentCategory === 'bookmarks') {
      return ARTICLES.filter(function (a) { return bookmarks.has(a.id); });
    }
    return ARTICLES.filter(function (a) { return a.category === currentCategory; });
  }

  /* ---------- Render Feed ---------- */
  function renderFeed() {
    var list = document.getElementById('feed-list');
    var articles = getFilteredArticles();

    if (articles.length === 0) {
      list.innerHTML = '<div class="feed-empty">No articles in this category</div>';
      return;
    }

    var html = '';
    articles.forEach(function (a) {
      var isBookmarked = bookmarks.has(a.id);
      var bookmarkIcon = isBookmarked ? '\u2665' : '\u2661';
      var bookmarkClass = isBookmarked ? 'feed-item__bookmark bookmarked' : 'feed-item__bookmark';

      html += '<article class="feed-item" data-id="' + a.id + '">' +
        '<div class="feed-item__content">' +
        '<div class="feed-item__meta">' +
        '<span class="feed-item__source">' + a.source + '</span>' +
        '<span class="feed-item__time">' + a.time + '</span>' +
        '</div>' +
        '<h3 class="feed-item__title">' + a.title + '</h3>' +
        '<p class="feed-item__excerpt">' + a.excerpt + '</p>' +
        '<div class="feed-item__footer">' +
        '<div class="feed-item__tags"><span class="feed-item__tag">' + a.category + '</span></div>' +
        '<span class="feed-item__reading-time">' + a.readTime + ' min read</span>' +
        '<button class="' + bookmarkClass + '" data-id="' + a.id + '" type="button" aria-label="Bookmark">' + bookmarkIcon + '</button>' +
        '</div></div></article>';
    });
    list.innerHTML = html;

    /* Bookmark click handlers */
    list.querySelectorAll('.feed-item__bookmark').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var id = parseInt(btn.getAttribute('data-id'));
        if (bookmarks.has(id)) {
          bookmarks.delete(id);
        } else {
          bookmarks.add(id);
        }
        renderFeed();
      });
    });

    /* Animate feed items */
    if (!prefersReducedMotion) {
      gsap.utils.toArray('.feed-item').forEach(function (el, i) {
        gsap.from(el, {
          scrollTrigger: { trigger: el, start: 'top 92%', toggleActions: 'play none none none' },
          opacity: 0, x: -50, duration: 0.5, delay: i * 0.06, ease: 'power2.out',
        });
      });
    }
  }

  /* ---------- GSAP Animations (D10 translateX(-50px)) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__banner', { opacity: 0, x: -50, duration: 0.5, ease: 'power3.out' });
    gsap.from('.hero__title', { opacity: 0, x: -50, duration: 0.7, delay: 0.1, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { opacity: 0, x: -50, duration: 0.5, delay: 0.2, ease: 'power3.out' });
    gsap.from('.category-tabs', { opacity: 0, x: -50, duration: 0.6, delay: 0.3, ease: 'power2.out' });
  }

  /* ---------- Init ---------- */
  renderFeed();
  initAnimations();

})();
