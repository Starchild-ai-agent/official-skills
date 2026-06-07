/* ============================================================
   Side Project Idea Generator — script.js

   Skeleton: A11 Centered
   Hover: C20 scale(1.03)
   Entrance: D14 fade+scale(0.9)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Ideas Pool ---------- */
  var IDEAS = [
    { title: 'CLI Bookmark Manager', desc: 'A terminal-based bookmark manager that syncs across devices using Git as the backend. Supports tags, search, and fuzzy matching.', tech: ['Node.js', 'CLI', 'Git'], difficulty: 'easy', time: '1 week' },
    { title: 'Code Screenshot Generator', desc: 'Generate beautiful code screenshots with custom themes, fonts, and backgrounds. Export as PNG or SVG with watermark options.', tech: ['React', 'Canvas API', 'CSS'], difficulty: 'medium', time: '2 weeks' },
    { title: 'Personal Analytics Dashboard', desc: 'Track your coding habits, GitHub contributions, and learning progress in a single dashboard with charts and streaks.', tech: ['Next.js', 'Chart.js', 'GitHub API'], difficulty: 'medium', time: '3 weeks' },
    { title: 'Markdown Resume Builder', desc: 'Write your resume in Markdown and export to PDF with multiple professional templates. Live preview included.', tech: ['Vue.js', 'Markdown', 'PDF'], difficulty: 'easy', time: '1 week' },
    { title: 'API Rate Limiter Tester', desc: 'A tool to test and visualize API rate limiting behavior. Send configurable bursts and see how different strategies respond.', tech: ['Python', 'FastAPI', 'D3.js'], difficulty: 'medium', time: '2 weeks' },
    { title: 'Git Commit Art Generator', desc: 'Generate pixel art patterns in your GitHub contribution graph by creating backdated commits. Choose from preset patterns or draw your own.', tech: ['Node.js', 'Git', 'Canvas'], difficulty: 'easy', time: '3 days' },
    { title: 'Real-time Collaboration Whiteboard', desc: 'A multiplayer whiteboard with drawing tools, sticky notes, and real-time cursor tracking using WebSockets.', tech: ['React', 'WebSocket', 'Canvas'], difficulty: 'hard', time: '4 weeks' },
    { title: 'Dependency Vulnerability Scanner', desc: 'Scan your project dependencies for known vulnerabilities and suggest safe upgrade paths with breaking change warnings.', tech: ['Rust', 'npm API', 'CLI'], difficulty: 'hard', time: '3 weeks' },
    { title: 'Pomodoro with Spotify Integration', desc: 'A Pomodoro timer that automatically plays focus playlists during work sessions and pauses during breaks.', tech: ['React', 'Spotify API', 'PWA'], difficulty: 'medium', time: '2 weeks' },
    { title: 'Open Source Contribution Finder', desc: 'Find beginner-friendly issues across GitHub repos matching your tech stack. Filters by language, label, and activity.', tech: ['Next.js', 'GitHub API', 'Tailwind'], difficulty: 'medium', time: '2 weeks' },
    { title: 'Terminal Portfolio Website', desc: 'A portfolio website that looks and behaves like a terminal. Visitors type commands to navigate sections.', tech: ['Vanilla JS', 'CSS', 'HTML'], difficulty: 'easy', time: '1 week' },
    { title: 'Smart Meeting Notes', desc: 'Record meetings, transcribe with AI, extract action items, and sync to your task manager automatically.', tech: ['Python', 'Whisper API', 'React'], difficulty: 'hard', time: '4 weeks' },
    { title: 'CSS Battle Clone', desc: 'A game where players recreate target designs using minimal CSS. Scoring based on character count and visual accuracy.', tech: ['Svelte', 'Node.js', 'Canvas'], difficulty: 'hard', time: '5 weeks' },
    { title: 'Browser Extension: Tab Organizer', desc: 'Automatically group and color-code browser tabs by project or topic using AI classification.', tech: ['Chrome API', 'JavaScript', 'AI'], difficulty: 'medium', time: '2 weeks' },
    { title: 'Changelog Generator', desc: 'Generate beautiful changelogs from Git commits following conventional commit format. Export as Markdown or HTML.', tech: ['Node.js', 'Git', 'CLI'], difficulty: 'easy', time: '4 days' },
  ];

  var savedIdeas = [];
  var currentIdea = null;

  /* ---------- Theme ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('spi-theme', theme);
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    setTheme(current === 'light' ? 'dark' : 'light');
  });
  var savedTheme = localStorage.getItem('spi-theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(savedTheme);

  /* ---------- Generate Random Idea ---------- */
  document.getElementById('generate-btn').addEventListener('click', generateIdea);

  function generateIdea() {
    var idx = Math.floor(Math.random() * IDEAS.length);
    currentIdea = IDEAS[idx];
    renderIdeaCard(currentIdea);

    if (!prefersReducedMotion) {
      gsap.from('.idea-card', { opacity: 0, scale: 0.9, duration: 0.5, ease: 'back.out(1.7)' });
    }
  }

  function renderIdeaCard(idea) {
    var card = document.getElementById('idea-card');
    var diffClass = 'idea-card__badge--difficulty-' + idea.difficulty;
    var techBadges = idea.tech.map(function (t) {
      return '<span class="idea-card__badge">' + t + '</span>';
    }).join('');

    card.innerHTML =
      '<h3 class="idea-card__title">' + idea.title + '</h3>' +
      '<p class="idea-card__desc">' + idea.desc + '</p>' +
      '<div class="idea-card__meta">' +
      techBadges +
      '<span class="idea-card__badge ' + diffClass + '">' + idea.difficulty + '</span>' +
      '<span class="idea-card__badge">' + idea.time + '</span>' +
      '</div>' +
      '<div class="idea-card__actions">' +
      '<button class="idea-card__action idea-card__action--save" id="save-idea" type="button">Save</button>' +
      '<button class="idea-card__action" id="share-idea" type="button">Copy</button>' +
      '</div>';

    document.getElementById('save-idea').addEventListener('click', function () {
      saveIdea(idea);
    });
    document.getElementById('share-idea').addEventListener('click', function () {
      var text = idea.title + ' - ' + idea.desc + ' [' + idea.tech.join(', ') + ']';
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text);
      }
    });
  }

  /* ---------- Save / Remove Ideas ---------- */
  function saveIdea(idea) {
    var exists = savedIdeas.some(function (s) { return s.title === idea.title; });
    if (!exists) {
      savedIdeas.push(idea);
      renderSavedGrid();
    }
  }

  function removeIdea(index) {
    savedIdeas.splice(index, 1);
    renderSavedGrid();
  }

  function renderSavedGrid() {
    var grid = document.getElementById('saved-grid');
    if (savedIdeas.length === 0) {
      grid.innerHTML = '<p class="saved-empty">No saved ideas yet. Generate and save some!</p>';
      return;
    }

    var html = '';
    savedIdeas.forEach(function (idea, i) {
      html += '<div class="saved-card">' +
        '<button class="saved-card__remove" data-index="' + i + '" type="button" aria-label="Remove">&times;</button>' +
        '<div class="saved-card__title">' + idea.title + '</div>' +
        '<div class="saved-card__tech">' + idea.tech.join(' \u00b7 ') + '</div>' +
        '<div class="saved-card__difficulty">' + idea.difficulty + ' \u00b7 ' + idea.time + '</div>' +
        '</div>';
    });
    grid.innerHTML = html;

    grid.querySelectorAll('.saved-card__remove').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        removeIdea(parseInt(btn.getAttribute('data-index')));
      });
    });

    /* Animate new saved cards */
    if (!prefersReducedMotion) {
      gsap.utils.toArray('.saved-card').forEach(function (el, i) {
        gsap.from(el, {
          scrollTrigger: { trigger: el, start: 'top 92%', toggleActions: 'play none none none' },
          opacity: 0, scale: 0.9, duration: 0.4, delay: i * 0.05, ease: 'back.out(1.4)',
        });
      });
    }
  }

  /* ---------- GSAP Animations (D14 fade+scale(0.9)) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__title', { opacity: 0, scale: 0.9, duration: 0.7, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { opacity: 0, scale: 0.9, duration: 0.6, delay: 0.1, ease: 'power3.out' });
    gsap.from('.hero__generate-btn', { opacity: 0, scale: 0.9, duration: 0.5, delay: 0.25, ease: 'back.out(1.7)' });

    gsap.from('.idea-card', {
      scrollTrigger: { trigger: '.idea-card', start: 'top 85%' },
      opacity: 0, scale: 0.9, duration: 0.6, ease: 'power2.out',
    });

    gsap.utils.toArray('.section__title').forEach(function (el) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%' },
        opacity: 0, scale: 0.9, duration: 0.5, ease: 'power3.out',
      });
    });
  }

  /* ---------- Init ---------- */
  renderSavedGrid();
  initAnimations();

})();
