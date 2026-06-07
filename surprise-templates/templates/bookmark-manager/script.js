/* ============================================================
   Bookmark Manager — script.js
   ============================================================ */
;(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const themeToggle = document.getElementById('themeToggle');
  const savedTheme = localStorage.getItem('bookmark-theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);

  themeToggle.addEventListener('click', () => {
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('bookmark-theme', next);
  });

  /* ---------- Sidebar Toggle (mobile) ---------- */
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');

  sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 &&
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        e.target !== sidebarToggle) {
      sidebar.classList.remove('open');
    }
  });

  /* ---------- Modal ---------- */
  const addModal = document.getElementById('addModal');
  const btnAdd = document.getElementById('btnAdd');
  const modalClose = document.getElementById('modalClose');

  btnAdd.addEventListener('click', () => {
    addModal.classList.add('open');
    document.getElementById('inputUrl').focus();
  });

  modalClose.addEventListener('click', () => addModal.classList.remove('open'));
  addModal.addEventListener('click', (e) => {
    if (e.target === addModal) addModal.classList.remove('open');
  });

  /* ---------- Data Store ---------- */
  let bookmarks = JSON.parse(localStorage.getItem('bookmark-data')) || [];
  let activeCategory = 'all';
  let searchQuery = '';

  function saveBookmarks() {
    localStorage.setItem('bookmark-data', JSON.stringify(bookmarks));
  }

  function getCategories() {
    const cats = new Set();
    bookmarks.forEach(b => {
      if (b.category) cats.add(b.category);
    });
    return Array.from(cats).sort();
  }

  function getFilteredBookmarks() {
    let filtered = bookmarks;
    if (activeCategory !== 'all') {
      filtered = filtered.filter(b => b.category === activeCategory);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(b =>
        b.title.toLowerCase().includes(q) ||
        b.url.toLowerCase().includes(q) ||
        (b.category && b.category.toLowerCase().includes(q))
      );
    }
    return filtered;
  }

  function getFaviconUrl(url) {
    try {
      const domain = new URL(url).hostname;
      return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
    } catch {
      return '';
    }
  }

  /* ---------- Render Category Nav ---------- */
  function renderCategoryNav() {
    const nav = document.getElementById('categoryNav');
    const cats = getCategories();
    nav.innerHTML = '';

    cats.forEach(cat => {
      const count = bookmarks.filter(b => b.category === cat).length;
      const btn = document.createElement('button');
      btn.className = 'nav-category' + (activeCategory === cat ? ' active' : '');
      btn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        ${cat}
        <span class="nav-count">${count}</span>
      `;
      btn.addEventListener('click', () => {
        activeCategory = cat;
        updateActiveNav();
        renderBookmarks();
      });
      nav.appendChild(btn);
    });

    // Update "All" count
    document.getElementById('countAll').textContent = bookmarks.length;

    // Update datalist for category input
    const datalist = document.getElementById('categoryList');
    datalist.innerHTML = '';
    cats.forEach(cat => {
      const opt = document.createElement('option');
      opt.value = cat;
      datalist.appendChild(opt);
    });
  }

  function updateActiveNav() {
    document.querySelectorAll('.nav-item, .nav-category').forEach(el => {
      el.classList.remove('active');
    });
    if (activeCategory === 'all') {
      document.querySelector('.nav-item[data-category="all"]').classList.add('active');
    } else {
      document.querySelectorAll('.nav-category').forEach(el => {
        if (el.textContent.trim().startsWith(activeCategory)) {
          el.classList.add('active');
        }
      });
    }
  }

  // "All" button click
  document.querySelector('.nav-item[data-category="all"]').addEventListener('click', () => {
    activeCategory = 'all';
    updateActiveNav();
    renderBookmarks();
  });

  /* ---------- Render Bookmarks ---------- */
  function renderBookmarks() {
    const grid = document.getElementById('bookmarkGrid');
    const empty = document.getElementById('emptyState');
    const filtered = getFilteredBookmarks();

    grid.innerHTML = '';

    document.getElementById('heroCount').textContent =
      `${filtered.length} bookmark${filtered.length !== 1 ? 's' : ''}`;

    if (filtered.length === 0) {
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    filtered.forEach((bm, index) => {
      const card = document.createElement('div');
      card.className = 'bookmark-card';

      const faviconSrc = getFaviconUrl(bm.url);

      card.innerHTML = `
        <div class="bookmark-header">
          ${faviconSrc ? `<img class="bookmark-favicon" src="${faviconSrc}" alt="" loading="lazy" />` : ''}
          <span class="bookmark-title">${escapeHtml(bm.title)}</span>
        </div>
        <a class="bookmark-url" href="${escapeHtml(bm.url)}" target="_blank" rel="noopener">${escapeHtml(bm.url)}</a>
        <div class="bookmark-footer">
          ${bm.category ? `<span class="bookmark-tag">${escapeHtml(bm.category)}</span>` : '<span></span>'}
          <div class="bookmark-actions">
            <button class="bookmark-action copy-btn" aria-label="Copy URL" data-url="${escapeHtml(bm.url)}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            </button>
            <button class="bookmark-action open-btn" aria-label="Open link" data-url="${escapeHtml(bm.url)}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15,3 21,3 21,9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            </button>
            <button class="bookmark-action delete" aria-label="Delete bookmark" data-index="${index}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      `;

      grid.appendChild(card);
    });

    // Bind actions
    grid.querySelectorAll('.copy-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const url = btn.dataset.url;
        try {
          await navigator.clipboard.writeText(url);
          btn.style.color = 'var(--color-accent)';
          setTimeout(() => { btn.style.color = ''; }, 1000);
        } catch {
          // Fallback
          const ta = document.createElement('textarea');
          ta.value = url;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
        }
      });
    });

    grid.querySelectorAll('.open-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        window.open(btn.dataset.url, '_blank', 'noopener');
      });
    });

    grid.querySelectorAll('.delete').forEach(btn => {
      btn.addEventListener('click', () => {
        const realIndex = findRealIndex(filtered[parseInt(btn.dataset.index)]);
        if (realIndex !== -1) {
          bookmarks.splice(realIndex, 1);
          saveBookmarks();
          renderCategoryNav();
          renderBookmarks();
        }
      });
    });

    animateCards();
  }

  function findRealIndex(bm) {
    return bookmarks.findIndex(b => b.url === bm.url && b.title === bm.title);
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------- Add Bookmark ---------- */
  document.getElementById('addForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const url = document.getElementById('inputUrl').value.trim();
    const title = document.getElementById('inputTitle').value.trim();
    const category = document.getElementById('inputCategory').value.trim();

    if (!url || !title) return;

    bookmarks.unshift({ url, title, category: category || 'Uncategorized' });
    saveBookmarks();
    renderCategoryNav();
    renderBookmarks();

    // Reset form
    document.getElementById('inputUrl').value = '';
    document.getElementById('inputTitle').value = '';
    document.getElementById('inputCategory').value = '';
    addModal.classList.remove('open');
  });

  /* ---------- Search ---------- */
  const searchInput = document.getElementById('searchInput');
  let searchTimeout;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      searchQuery = searchInput.value.trim();
      renderBookmarks();
    }, 200);
  });

  /* ---------- GSAP Animations (D4 stagger top-to-bottom) ---------- */
  function animateCards() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    gsap.registerPlugin(ScrollTrigger);

    const cards = document.querySelectorAll('.bookmark-card');
    gsap.fromTo(cards,
      { opacity: 0, y: 20 },
      {
        opacity: 1,
        y: 0,
        duration: 0.4,
        stagger: 0.06,
        ease: 'power2.out',
      }
    );
  }

  function initAnimations() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.querySelectorAll('[data-animate]').forEach(el => {
        el.style.opacity = '1';
      });
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    document.querySelectorAll('[data-animate="stagger"]').forEach((el, i) => {
      gsap.fromTo(el,
        { opacity: 0, y: 16 },
        {
          opacity: 1,
          y: 0,
          duration: 0.5,
          delay: i * 0.1,
          ease: 'power2.out',
        }
      );
    });
  }

  /* ---------- Init ---------- */
  renderCategoryNav();
  renderBookmarks();
  initAnimations();
})();
