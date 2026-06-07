/* ============================================================
   Quick Notes — script.js
   ============================================================ */
;(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const themeToggle = document.getElementById('themeToggle');
  const savedTheme = localStorage.getItem('qnotes-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);

  themeToggle.addEventListener('click', () => {
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('qnotes-theme', next);
  });

  /* ---------- List Toggle (mobile) ---------- */
  const listPanel = document.getElementById('listPanel');
  const listToggle = document.getElementById('listToggle');

  listToggle.addEventListener('click', () => {
    listPanel.classList.toggle('open');
  });

  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 &&
        listPanel.classList.contains('open') &&
        !listPanel.contains(e.target) &&
        e.target !== listToggle) {
      listPanel.classList.remove('open');
    }
  });

  /* ---------- Data Store ---------- */
  let notes = JSON.parse(localStorage.getItem('qnotes-data')) || [];
  let activeNoteId = null;
  let isPreviewMode = false;
  let searchQuery = '';

  function saveNotes() {
    localStorage.setItem('qnotes-data', JSON.stringify(notes));
  }

  function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }

  function getActiveNote() {
    return notes.find(n => n.id === activeNoteId) || null;
  }

  function getFilteredNotes() {
    if (!searchQuery) return notes;
    const q = searchQuery.toLowerCase();
    return notes.filter(n =>
      n.title.toLowerCase().includes(q) ||
      n.content.toLowerCase().includes(q)
    );
  }

  function formatDate(ts) {
    const d = new Date(ts);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  /* ---------- Render Note List ---------- */
  function renderNoteList() {
    const list = document.getElementById('noteList');
    const empty = document.getElementById('listEmpty');
    const filtered = getFilteredNotes();

    list.innerHTML = '';

    if (filtered.length === 0) {
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    filtered.forEach(note => {
      const btn = document.createElement('button');
      btn.className = 'note-item' + (note.id === activeNoteId ? ' active' : '');

      const preview = note.content.replace(/[#*`>\-\[\]]/g, '').trim().slice(0, 60);

      btn.innerHTML = `
        <div class="note-item-title">${escapeHtml(note.title || 'Untitled')}</div>
        <div class="note-item-preview">${escapeHtml(preview || 'Empty note')}</div>
        <div class="note-item-date">${formatDate(note.updatedAt)}</div>
      `;

      btn.addEventListener('click', () => {
        selectNote(note.id);
        if (window.innerWidth <= 768) {
          listPanel.classList.remove('open');
        }
      });

      list.appendChild(btn);
    });
  }

  /* ---------- Select Note ---------- */
  function selectNote(id) {
    activeNoteId = id;
    const note = getActiveNote();

    const editorEmpty = document.getElementById('editorEmpty');
    const editorToolbar = document.getElementById('editorToolbar');
    const textarea = document.getElementById('editorTextarea');
    const preview = document.getElementById('editorPreview');

    if (!note) {
      editorEmpty.classList.remove('hidden');
      editorToolbar.style.display = 'none';
      textarea.style.display = 'none';
      preview.classList.add('hidden');
      renderNoteList();
      return;
    }

    editorEmpty.classList.add('hidden');
    editorToolbar.style.display = '';

    document.getElementById('toolbarTitle').textContent = note.title || 'Untitled';
    textarea.value = note.content;

    if (isPreviewMode) {
      textarea.style.display = 'none';
      preview.classList.remove('hidden');
      renderPreview(note.content);
    } else {
      textarea.style.display = '';
      preview.classList.add('hidden');
      textarea.focus();
    }

    renderNoteList();
  }

  /* ---------- New Note ---------- */
  document.getElementById('btnNew').addEventListener('click', () => {
    const note = {
      id: generateId(),
      title: 'Untitled',
      content: '',
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    notes.unshift(note);
    saveNotes();
    selectNote(note.id);
  });

  /* ---------- Editor Input ---------- */
  const textarea = document.getElementById('editorTextarea');
  let saveTimeout;

  textarea.addEventListener('input', () => {
    const note = getActiveNote();
    if (!note) return;

    note.content = textarea.value;

    // Extract title from first line
    const firstLine = textarea.value.split('\n')[0].replace(/^#+\s*/, '').trim();
    note.title = firstLine || 'Untitled';
    note.updatedAt = Date.now();

    document.getElementById('toolbarTitle').textContent = note.title;
    document.getElementById('toolbarSaved').textContent = 'editing…';

    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
      saveNotes();
      renderNoteList();
      document.getElementById('toolbarSaved').textContent = 'saved';
      setTimeout(() => {
        document.getElementById('toolbarSaved').textContent = '';
      }, 1500);
    }, 500);
  });

  // Tab key support
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      textarea.value = textarea.value.substring(0, start) + '  ' + textarea.value.substring(end);
      textarea.selectionStart = textarea.selectionEnd = start + 2;
      textarea.dispatchEvent(new Event('input'));
    }
  });

  /* ---------- Ctrl+S Save ---------- */
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      const note = getActiveNote();
      if (!note) return;
      note.content = textarea.value;
      const firstLine = textarea.value.split('\n')[0].replace(/^#+\s*/, '').trim();
      note.title = firstLine || 'Untitled';
      note.updatedAt = Date.now();
      saveNotes();
      renderNoteList();
      document.getElementById('toolbarSaved').textContent = 'saved ✓';
      setTimeout(() => {
        document.getElementById('toolbarSaved').textContent = '';
      }, 2000);
    }
  });

  /* ---------- Preview Toggle ---------- */
  const btnPreview = document.getElementById('btnPreview');

  btnPreview.addEventListener('click', () => {
    isPreviewMode = !isPreviewMode;
    btnPreview.classList.toggle('active', isPreviewMode);

    const note = getActiveNote();
    if (!note) return;

    if (isPreviewMode) {
      textarea.style.display = 'none';
      document.getElementById('editorPreview').classList.remove('hidden');
      renderPreview(note.content);
    } else {
      textarea.style.display = '';
      document.getElementById('editorPreview').classList.add('hidden');
      textarea.focus();
    }
  });

  function renderPreview(content) {
    const preview = document.getElementById('editorPreview');
    try {
      preview.innerHTML = marked.parse(content || '', {
        breaks: true,
        gfm: true,
      });
      // Apply Prism highlighting to code blocks
      preview.querySelectorAll('pre code').forEach(block => {
        Prism.highlightElement(block);
      });
    } catch {
      preview.innerHTML = '<p>Error rendering markdown</p>';
    }
  }

  /* ---------- Export ---------- */
  document.getElementById('btnExport').addEventListener('click', () => {
    const note = getActiveNote();
    if (!note) return;

    const blob = new Blob([note.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (note.title || 'note') + '.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  /* ---------- Delete ---------- */
  document.getElementById('btnDelete').addEventListener('click', () => {
    const note = getActiveNote();
    if (!note) return;

    const idx = notes.findIndex(n => n.id === note.id);
    if (idx !== -1) {
      notes.splice(idx, 1);
      saveNotes();
      activeNoteId = notes.length > 0 ? notes[0].id : null;
      selectNote(activeNoteId);
    }
  });

  /* ---------- Search ---------- */
  const searchInput = document.getElementById('searchInput');
  let searchTimeout2;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout2);
    searchTimeout2 = setTimeout(() => {
      searchQuery = searchInput.value.trim();
      renderNoteList();
    }, 200);
  });

  /* ---------- GSAP Animations (D7 translateX from left) ---------- */
  function initAnimations() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.querySelectorAll('[data-animate]').forEach(el => {
        el.style.opacity = '1';
      });
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    document.querySelectorAll('[data-animate="slide"]').forEach((el, i) => {
      gsap.fromTo(el,
        { opacity: 0, x: -20 },
        {
          opacity: 1,
          x: 0,
          duration: 0.5,
          delay: i * 0.1,
          ease: 'power2.out',
        }
      );
    });
  }

  /* ---------- Helpers ---------- */
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------- Init ---------- */
  // Select first note if exists
  if (notes.length > 0) {
    activeNoteId = notes[0].id;
  }
  renderNoteList();
  selectNote(activeNoteId);
  initAnimations();
})();
