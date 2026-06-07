/* ============================================================
   Technical Interview Prep — script.js

   Skeleton: A6 Sidebar + Content
   Entry:   D4 stagger top-to-bottom
   Hero:    H10 Inline Hero

   Pure frontend — no external APIs required.
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
      if (raw.startsWith('{{')) return 'General';
      return raw;
    })(),
  };

  var STORAGE_KEY = 'interview-prep-progress';
  var STREAK_KEY = 'interview-prep-streak';

  var CATEGORIES = [
    { id: 'arrays', name: 'Arrays', icon: '📊' },
    { id: 'strings', name: 'Strings', icon: '🔤' },
    { id: 'trees', name: 'Trees', icon: '🌳' },
    { id: 'graphs', name: 'Graphs', icon: '🕸' },
    { id: 'dp', name: 'Dynamic Programming', icon: '🧮' },
    { id: 'system', name: 'System Design', icon: '🏗' },
  ];

  var PROBLEMS = [
    { id: 'arr-1', category: 'arrays', difficulty: 'Easy', title: 'Two Sum', desc: 'Given an array of integers and a target, return indices of two numbers that add up to the target.', hint: 'Use a hash map to store complements as you iterate.' },
    { id: 'arr-2', category: 'arrays', difficulty: 'Medium', title: 'Container With Most Water', desc: 'Given n non-negative integers representing heights, find two lines that form a container holding the most water.', hint: 'Use two pointers starting from both ends. Move the shorter line inward.' },
    { id: 'arr-3', category: 'arrays', difficulty: 'Medium', title: 'Three Sum', desc: 'Find all unique triplets in the array that give the sum of zero.', hint: 'Sort the array first, then use two pointers for each fixed element.' },
    { id: 'arr-4', category: 'arrays', difficulty: 'Hard', title: 'Median of Two Sorted Arrays', desc: 'Given two sorted arrays, find the median. Run time should be O(log(m+n)).', hint: 'Binary search on the shorter array to find the correct partition.' },
    { id: 'arr-5', category: 'arrays', difficulty: 'Easy', title: 'Best Time to Buy and Sell Stock', desc: 'Given an array of prices, find the maximum profit from one transaction.', hint: 'Track the minimum price seen so far and calculate profit at each step.' },
    { id: 'arr-6', category: 'arrays', difficulty: 'Medium', title: 'Product of Array Except Self', desc: 'Return an array where each element is the product of all elements except itself, without division.', hint: 'Use prefix and suffix product arrays.' },
    { id: 'str-1', category: 'strings', difficulty: 'Easy', title: 'Valid Palindrome', desc: 'Determine if a string is a palindrome, considering only alphanumeric characters.', hint: 'Use two pointers from both ends, skip non-alphanumeric characters.' },
    { id: 'str-2', category: 'strings', difficulty: 'Medium', title: 'Longest Substring Without Repeating', desc: 'Find the length of the longest substring without repeating characters.', hint: 'Sliding window with a Set to track characters in the current window.' },
    { id: 'str-3', category: 'strings', difficulty: 'Medium', title: 'Group Anagrams', desc: 'Given an array of strings, group the anagrams together.', hint: 'Sort each string to create a key, then group by that key using a hash map.' },
    { id: 'str-4', category: 'strings', difficulty: 'Hard', title: 'Minimum Window Substring', desc: 'Find the minimum window substring of s that contains all characters of t.', hint: 'Sliding window with character frequency maps. Expand right, contract left.' },
    { id: 'str-5', category: 'strings', difficulty: 'Easy', title: 'Valid Anagram', desc: 'Given two strings s and t, return true if t is an anagram of s.', hint: 'Count character frequencies in both strings and compare.' },
    { id: 'tree-1', category: 'trees', difficulty: 'Easy', title: 'Maximum Depth of Binary Tree', desc: 'Return the maximum depth of a binary tree.', hint: 'Recursive DFS: max depth = 1 + max(left depth, right depth).' },
    { id: 'tree-2', category: 'trees', difficulty: 'Easy', title: 'Invert Binary Tree', desc: 'Invert a binary tree (mirror it) and return its root.', hint: 'Recursively swap left and right children at each node.' },
    { id: 'tree-3', category: 'trees', difficulty: 'Medium', title: 'Validate Binary Search Tree', desc: 'Determine if a binary tree is a valid BST.', hint: 'In-order traversal should produce a sorted sequence.' },
    { id: 'tree-4', category: 'trees', difficulty: 'Medium', title: 'Level Order Traversal', desc: 'Return the level order traversal of a binary tree.', hint: 'Use BFS with a queue. Process all nodes at each level.' },
    { id: 'tree-5', category: 'trees', difficulty: 'Hard', title: 'Serialize and Deserialize Tree', desc: 'Design an algorithm to serialize and deserialize a binary tree.', hint: 'Use preorder traversal with null markers.' },
    { id: 'tree-6', category: 'trees', difficulty: 'Medium', title: 'Lowest Common Ancestor', desc: 'Find the lowest common ancestor of two nodes in a binary tree.', hint: 'If current node is p or q, return it. Recurse left and right.' },
    { id: 'graph-1', category: 'graphs', difficulty: 'Medium', title: 'Number of Islands', desc: 'Count the number of islands in a 2D grid of land and water.', hint: 'BFS or DFS from each unvisited land cell, marking visited cells.' },
    { id: 'graph-2', category: 'graphs', difficulty: 'Medium', title: 'Clone Graph', desc: 'Return a deep copy of a connected undirected graph.', hint: 'Use BFS/DFS with a hash map mapping original nodes to clones.' },
    { id: 'graph-3', category: 'graphs', difficulty: 'Medium', title: 'Course Schedule', desc: 'Determine if you can finish all courses given prerequisites.', hint: 'Topological sort or DFS with cycle detection.' },
    { id: 'graph-4', category: 'graphs', difficulty: 'Hard', title: 'Word Ladder', desc: 'Find the shortest transformation sequence from beginWord to endWord.', hint: 'BFS where each level represents one transformation.' },
    { id: 'graph-5', category: 'graphs', difficulty: 'Medium', title: 'Pacific Atlantic Water Flow', desc: 'Find all cells where water can flow to both oceans.', hint: 'BFS/DFS from ocean borders inward. Intersect reachable cells.' },
    { id: 'dp-1', category: 'dp', difficulty: 'Easy', title: 'Climbing Stairs', desc: 'How many distinct ways can you climb n steps taking 1 or 2 steps at a time?', hint: 'Fibonacci-like: dp[i] = dp[i-1] + dp[i-2].' },
    { id: 'dp-2', category: 'dp', difficulty: 'Medium', title: 'Coin Change', desc: 'Find the fewest coins needed to make up a given amount.', hint: 'Bottom-up DP: dp[amount] = min(dp[amount], dp[amount - coin] + 1).' },
    { id: 'dp-3', category: 'dp', difficulty: 'Medium', title: 'Longest Increasing Subsequence', desc: 'Return the length of the longest strictly increasing subsequence.', hint: 'O(n log n) with patience sorting or O(n^2) DP.' },
    { id: 'dp-4', category: 'dp', difficulty: 'Hard', title: 'Edit Distance', desc: 'Return the minimum operations to convert one string to another.', hint: '2D DP table comparing prefixes of both strings.' },
    { id: 'dp-5', category: 'dp', difficulty: 'Medium', title: 'House Robber', desc: 'Find the maximum amount you can rob without robbing adjacent houses.', hint: 'dp[i] = max(dp[i-1], dp[i-2] + nums[i]).' },
    { id: 'dp-6', category: 'dp', difficulty: 'Medium', title: 'Unique Paths', desc: 'How many unique paths exist in an m x n grid moving only right or down?', hint: 'dp[i][j] = dp[i-1][j] + dp[i][j-1].' },
    { id: 'sys-1', category: 'system', difficulty: 'Medium', title: 'Design URL Shortener', desc: 'Design a URL shortening service. Consider encoding, database, and redirect flow.', hint: 'Base62 encoding of auto-increment ID. Consider caching and analytics.' },
    { id: 'sys-2', category: 'system', difficulty: 'Hard', title: 'Design a Chat System', desc: 'Design a real-time chat app supporting 1:1 and group messaging.', hint: 'WebSocket for real-time. Message queue for reliability.' },
    { id: 'sys-3', category: 'system', difficulty: 'Medium', title: 'Design Rate Limiter', desc: 'Design a rate limiter for API requests in a given time window.', hint: 'Token bucket or sliding window counter. Consider Redis for distributed.' },
    { id: 'sys-4', category: 'system', difficulty: 'Hard', title: 'Design a News Feed', desc: 'Design a social media news feed with ranking and real-time updates.', hint: 'Fan-out on write for active users, fan-out on read for celebrities.' },
    { id: 'sys-5', category: 'system', difficulty: 'Medium', title: 'Design Key-Value Store', desc: 'Design a distributed key-value store with high availability.', hint: 'Consistent hashing, replication, vector clocks. Consider CAP theorem.' },
  ];

  var TIPS = [
    { icon: '🎯', title: 'Clarify First', desc: 'Always ask clarifying questions before coding. Understand input constraints, edge cases, and expected output.' },
    { icon: '📝', title: 'Think Aloud', desc: 'Verbalize your thought process. Interviewers want to see how you approach problems.' },
    { icon: '🔄', title: 'Brute Force First', desc: 'Start with the simplest solution, then optimize. Mention brute force and its complexity.' },
    { icon: '⏱', title: 'Time and Space', desc: 'Always analyze time and space complexity. State Big-O before and after optimization.' },
    { icon: '🧪', title: 'Test Your Code', desc: 'Walk through your solution with examples. Test edge cases: empty input, single element, duplicates.' },
    { icon: '🏗', title: 'System Design Framework', desc: 'Requirements, High-Level Design, Deep Dive, Trade-offs. Use diagrams and be specific.' },
    { icon: '📊', title: 'Know Data Structures', desc: 'Master arrays, hash maps, trees, graphs, heaps, and tries. Know when to use each.' },
    { icon: '🧘', title: 'Stay Calm', desc: 'If stuck, take a breath. Try a different approach, draw examples, or simplify the problem.' },
  ];

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return Array.from(document.querySelectorAll(sel)); };

  var els = {
    themeToggle: $('#theme-toggle'),
    heroTime: $('#hero-time'),
    heroBgImage: $('.hero__bg-image'),
    statCompleted: $('#stat-completed'),
    statTotal: $('#stat-total'),
    statStreak: $('#stat-streak'),
    statPercent: $('#stat-percent'),
    progressFill: $('#progress-fill'),
    categoriesNav: $('#categories-nav'),
    btnRandom: $('#btn-random'),
    problemCategoryFilter: $('#problem-category-filter'),
    problemDifficultyFilter: $('#problem-difficulty-filter'),
    problemEmpty: $('#problem-empty'),
    problemContent: $('#problem-content'),
    problemCat: $('#problem-cat'),
    problemDiff: $('#problem-diff'),
    problemTitle: $('#problem-title'),
    problemDesc: $('#problem-desc'),
    problemHint: $('#problem-hint'),
    problemHintText: $('#problem-hint-text'),
    btnHint: $('#btn-hint'),
    btnComplete: $('#btn-complete'),
    btnSkip: $('#btn-skip'),
    tipsGrid: $('#tips-grid'),
    btnResetProgress: $('#btn-reset-progress'),
  };

  var completedIds = new Set();
  var currentProblem = null;
  var progressChart = null;
  var activeCategory = 'all';

  /* ---- Theme ---- */
  function initTheme() {
    var saved = localStorage.getItem('interview-prep-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else {
      var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    }
  }

  function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme');
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('interview-prep-theme', next);
    updateChart();
  }

  /* ---- Clock ---- */
  function updateClock() {
    var now = new Date();
    var timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    var dateStr = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    els.heroTime.textContent = dateStr + ' ' + timeStr;
    els.heroTime.setAttribute('datetime', now.toISOString());
  }

  /* ---- Hero BG ---- */
  function initHeroImage() {
    if (CONFIG.heroImageUrl && els.heroBgImage) {
      els.heroBgImage.style.backgroundImage = "url('" + CONFIG.heroImageUrl + "')";
      els.heroBgImage.style.backgroundSize = 'cover';
      els.heroBgImage.style.backgroundPosition = 'center';
      els.heroBgImage.style.opacity = '0.10';
    }
  }

  /* ---- Progress Persistence ---- */
  function loadProgress() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        var arr = JSON.parse(saved);
        completedIds = new Set(arr);
      }
    } catch (e) {
      completedIds = new Set();
    }
  }

  function saveProgress() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(completedIds)));
  }

  function getStreak() {
    try {
      var data = JSON.parse(localStorage.getItem(STREAK_KEY) || '{}');
      var today = new Date().toISOString().slice(0, 10);
      if (data.lastDate === today) return data.streak || 0;
      var yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
      if (data.lastDate === yesterday) return data.streak || 0;
      return 0;
    } catch (e) {
      return 0;
    }
  }

  function updateStreak() {
    var today = new Date().toISOString().slice(0, 10);
    try {
      var data = JSON.parse(localStorage.getItem(STREAK_KEY) || '{}');
      if (data.lastDate === today) return;
      var yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
      var streak = data.lastDate === yesterday ? (data.streak || 0) + 1 : 1;
      localStorage.setItem(STREAK_KEY, JSON.stringify({ lastDate: today, streak: streak }));
    } catch (e) {
      localStorage.setItem(STREAK_KEY, JSON.stringify({ lastDate: today, streak: 1 }));
    }
  }

  /* ---- Stats ---- */
  function updateStats() {
    var total = PROBLEMS.length;
    var completed = completedIds.size;
    var percent = total > 0 ? Math.round((completed / total) * 100) : 0;
    els.statCompleted.textContent = completed;
    els.statTotal.textContent = total;
    els.statStreak.textContent = getStreak();
    els.statPercent.textContent = percent;
    els.progressFill.style.width = percent + '%';
  }

  /* ---- Sidebar Categories (A6) ---- */
  function renderSidebarCategories() {
    els.categoriesNav.innerHTML = '';
    els.problemCategoryFilter.innerHTML = '<option value="all">All Categories</option>';

    /* "All" nav item */
    var allItem = document.createElement('div');
    allItem.className = 'sidebar__nav-item' + (activeCategory === 'all' ? ' active' : '');
    allItem.innerHTML =
      '<span class="sidebar__nav-icon">📋</span>' +
      '<span class="sidebar__nav-label">All Problems</span>' +
      '<span class="sidebar__nav-count">' + completedIds.size + '/' + PROBLEMS.length + '</span>';
    allItem.addEventListener('click', function () {
      activeCategory = 'all';
      els.problemCategoryFilter.value = 'all';
      updateSidebarActive();
      generateRandomProblem();
    });
    els.categoriesNav.appendChild(allItem);

    CATEGORIES.forEach(function (cat) {
      var problems = PROBLEMS.filter(function (p) { return p.category === cat.id; });
      var completed = problems.filter(function (p) { return completedIds.has(p.id); }).length;

      var item = document.createElement('div');
      item.className = 'sidebar__nav-item' + (activeCategory === cat.id ? ' active' : '');
      item.setAttribute('data-category', cat.id);
      item.innerHTML =
        '<span class="sidebar__nav-icon">' + cat.icon + '</span>' +
        '<span class="sidebar__nav-label">' + cat.name + '</span>' +
        '<span class="sidebar__nav-count">' + completed + '/' + problems.length + '</span>';

      item.addEventListener('click', function () {
        activeCategory = cat.id;
        els.problemCategoryFilter.value = cat.id;
        updateSidebarActive();
        generateRandomProblem();
      });
      els.categoriesNav.appendChild(item);

      var opt = document.createElement('option');
      opt.value = cat.id;
      opt.textContent = cat.name;
      els.problemCategoryFilter.appendChild(opt);
    });
  }

  function updateSidebarActive() {
    $$('.sidebar__nav-item').forEach(function (item) {
      var cat = item.getAttribute('data-category');
      var isActive = (activeCategory === 'all' && !cat) || cat === activeCategory;
      item.classList.toggle('active', isActive);
    });
  }

  /* ---- Problem Generation ---- */
  function generateRandomProblem() {
    var catFilter = els.problemCategoryFilter.value;
    var diffFilter = els.problemDifficultyFilter.value;

    var pool = PROBLEMS.filter(function (p) { return !completedIds.has(p.id); });
    if (catFilter !== 'all') pool = pool.filter(function (p) { return p.category === catFilter; });
    if (diffFilter !== 'all') pool = pool.filter(function (p) { return p.difficulty === diffFilter; });

    if (pool.length === 0) {
      pool = PROBLEMS.slice();
      if (catFilter !== 'all') pool = pool.filter(function (p) { return p.category === catFilter; });
      if (diffFilter !== 'all') pool = pool.filter(function (p) { return p.difficulty === diffFilter; });
    }

    if (pool.length === 0) return;
    var problem = pool[Math.floor(Math.random() * pool.length)];
    showProblem(problem);
  }

  function showProblem(problem) {
    currentProblem = problem;
    els.problemEmpty.style.display = 'none';
    els.problemContent.style.display = 'block';
    els.problemHint.style.display = 'none';

    var cat = CATEGORIES.find(function (c) { return c.id === problem.category; });
    els.problemCat.textContent = cat ? cat.name : problem.category;
    els.problemDiff.textContent = problem.difficulty;
    els.problemDiff.className = 'question-card__difficulty ' + problem.difficulty.toLowerCase();
    els.problemTitle.textContent = problem.title;
    els.problemDesc.textContent = problem.desc;
    els.problemHintText.textContent = problem.hint;

    if (completedIds.has(problem.id)) {
      els.btnComplete.textContent = 'Completed \u2713';
      els.btnComplete.disabled = true;
    } else {
      els.btnComplete.textContent = 'Mark Complete';
      els.btnComplete.disabled = false;
    }

    if (!prefersReducedMotion) {
      gsap.from(els.problemContent, { y: 20, opacity: 0, duration: 0.4, ease: 'power2.out' });
    }
  }

  function completeProblem() {
    if (!currentProblem || completedIds.has(currentProblem.id)) return;
    completedIds.add(currentProblem.id);
    saveProgress();
    updateStreak();
    updateStats();
    renderSidebarCategories();
    updateChart();
    els.btnComplete.textContent = 'Completed \u2713';
    els.btnComplete.disabled = true;
  }

  /* ---- Chart.js ---- */
  function initChart() {
    var ctx = document.getElementById('progress-chart');
    if (!ctx) return;

    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var textColor = isDark ? '#ede8df' : '#1c1810';
    var gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

    var labels = CATEGORIES.map(function (c) { return c.name; });
    var completedData = CATEGORIES.map(function (c) {
      return PROBLEMS.filter(function (p) { return p.category === c.id && completedIds.has(p.id); }).length;
    });
    var remainingData = CATEGORIES.map(function (c) {
      var total = PROBLEMS.filter(function (p) { return p.category === c.id; }).length;
      var done = PROBLEMS.filter(function (p) { return p.category === c.id && completedIds.has(p.id); }).length;
      return total - done;
    });

    progressChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Completed',
            data: completedData,
            backgroundColor: isDark ? 'rgba(234,179,8,0.7)' : 'rgba(202,138,4,0.7)',
            borderRadius: 4,
          },
          {
            label: 'Remaining',
            data: remainingData,
            backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: textColor,
              font: { family: "'Source Serif 4', Georgia, serif", size: 12 },
              padding: 16,
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            ticks: { color: textColor, font: { family: "'Source Serif 4', Georgia, serif", size: 11 } },
            grid: { display: false },
          },
          y: {
            stacked: true,
            beginAtZero: true,
            ticks: {
              color: textColor,
              font: { family: "'Fira Code', monospace", size: 11 },
              stepSize: 1,
            },
            grid: { color: gridColor },
          },
        },
      },
    });
  }

  function updateChart() {
    if (!progressChart) return;

    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var textColor = isDark ? '#ede8df' : '#1c1810';
    var gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

    var completedData = CATEGORIES.map(function (c) {
      return PROBLEMS.filter(function (p) { return p.category === c.id && completedIds.has(p.id); }).length;
    });
    var remainingData = CATEGORIES.map(function (c) {
      var total = PROBLEMS.filter(function (p) { return p.category === c.id; }).length;
      var done = PROBLEMS.filter(function (p) { return p.category === c.id && completedIds.has(p.id); }).length;
      return total - done;
    });

    progressChart.data.datasets[0].data = completedData;
    progressChart.data.datasets[0].backgroundColor = isDark ? 'rgba(234,179,8,0.7)' : 'rgba(202,138,4,0.7)';
    progressChart.data.datasets[1].data = remainingData;
    progressChart.data.datasets[1].backgroundColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';
    progressChart.options.plugins.legend.labels.color = textColor;
    progressChart.options.scales.x.ticks.color = textColor;
    progressChart.options.scales.y.ticks.color = textColor;
    progressChart.options.scales.y.grid.color = gridColor;
    progressChart.update();
  }

  /* ---- Tips ---- */
  function renderTips() {
    els.tipsGrid.innerHTML = '';
    TIPS.forEach(function (tip) {
      var card = document.createElement('div');
      card.className = 'tip-card';
      card.innerHTML =
        '<div class="tip-card__icon">' + tip.icon + '</div>' +
        '<div class="tip-card__title">' + tip.title + '</div>' +
        '<div class="tip-card__desc">' + tip.desc + '</div>';
      els.tipsGrid.appendChild(card);
    });
  }

  /* ---- GSAP Animations: D4 stagger top-to-bottom ---- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero entrance */
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__status-bar', { y: -20, opacity: 0, duration: 0.6 })
      .from('.hero__title', { y: 30, opacity: 0, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { y: 20, opacity: 0, duration: 0.5 }, '-=0.4')
      .from('.hero__right', { y: 20, opacity: 0, duration: 0.5 }, '-=0.3');

    /* D4: Sidebar nav items stagger top-to-bottom */
    gsap.from('.sidebar__nav-item', {
      y: 20,
      opacity: 0,
      duration: 0.4,
      stagger: 0.08,
      ease: 'power2.out',
      delay: 0.3,
    });

    /* D4: Content sections stagger top-to-bottom */
    var sections = $$('.content__section');
    sections.forEach(function (sec, i) {
      gsap.from(sec, {
        scrollTrigger: {
          trigger: sec,
          start: 'top 85%',
          toggleActions: 'play none none none',
        },
        y: 40,
        opacity: 0,
        duration: 0.7,
        delay: i * 0.1,
        ease: 'power2.out',
      });
    });

    /* D4: Tip cards stagger */
    gsap.from('.tip-card', {
      scrollTrigger: {
        trigger: '#section-tips',
        start: 'top 80%',
        toggleActions: 'play none none none',
      },
      y: 30,
      opacity: 0,
      duration: 0.5,
      stagger: 0.08,
      ease: 'power2.out',
    });
  }

  /* ---- Event Listeners ---- */
  function bindEvents() {
    els.themeToggle.addEventListener('click', toggleTheme);

    els.btnRandom.addEventListener('click', generateRandomProblem);

    els.btnHint.addEventListener('click', function () {
      els.problemHint.style.display = els.problemHint.style.display === 'none' ? 'block' : 'none';
    });

    els.btnComplete.addEventListener('click', completeProblem);

    els.btnSkip.addEventListener('click', generateRandomProblem);

    els.btnResetProgress.addEventListener('click', function () {
      if (confirm('Reset all progress? This cannot be undone.')) {
        completedIds = new Set();
        saveProgress();
        localStorage.removeItem(STREAK_KEY);
        updateStats();
        renderSidebarCategories();
        updateChart();
        els.problemEmpty.style.display = 'block';
        els.problemContent.style.display = 'none';
        currentProblem = null;
      }
    });
  }

  /* ---- Init ---- */
  function init() {
    initTheme();
    initHeroImage();
    loadProgress();
    updateClock();
    setInterval(updateClock, 1000);
    updateStats();
    renderSidebarCategories();
    renderTips();
    initChart();
    bindEvents();

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
