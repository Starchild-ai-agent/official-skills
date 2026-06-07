/* ============================================
 * Kanban Board — D27
 * HTML5 Drag & Drop, localStorage persistence
 * ============================================ */

(function () {
  'use strict';

  /* ---------- DOM ---------- */
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  const modalOverlay = $('#modalOverlay');
  const taskForm = $('#taskForm');
  const taskIdField = $('#taskId');
  const taskStatusField = $('#taskStatus');
  const taskTitleInput = $('#taskTitleInput');
  const taskDesc = $('#taskDesc');
  const modalTitle = $('#modalTitle');
  const cancelModal = $('#cancelModal');
  const themeToggle = $('#themeToggle');

  const lists = {
    todo: $('#listTodo'),
    progress: $('#listProgress'),
    done: $('#listDone'),
  };

  /* ---------- State ---------- */
  let tasks = [];
  let selectedPriority = 'low';

  /* ---------- Theme ---------- */
  function initTheme() {
    const saved = localStorage.getItem('kanban-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('kanban-theme', next);
  });

  /* ---------- Persistence ---------- */
  function loadTasks() {
    try {
      tasks = JSON.parse(localStorage.getItem('kanban-tasks') || '[]');
    } catch {
      tasks = [];
    }
    if (tasks.length === 0) {
      tasks = getDefaultTasks();
    }
  }

  function saveTasks() {
    localStorage.setItem('kanban-tasks', JSON.stringify(tasks));
  }

  function getDefaultTasks() {
    return [
      { id: genId(), title: 'Design landing page', desc: 'Create wireframes and mockups', priority: 'high', status: 'todo', created: Date.now() },
      { id: genId(), title: 'Set up CI/CD pipeline', desc: 'Configure GitHub Actions', priority: 'medium', status: 'todo', created: Date.now() },
      { id: genId(), title: 'Write API documentation', desc: '', priority: 'low', status: 'progress', created: Date.now() },
      { id: genId(), title: 'Fix login bug', desc: 'Session token expiry issue', priority: 'high', status: 'progress', created: Date.now() },
      { id: genId(), title: 'Deploy staging server', desc: 'Completed and verified', priority: 'medium', status: 'done', created: Date.now() },
    ];
  }

  function genId() {
    return 'task_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 7);
  }

  /* ---------- Render ---------- */
  function render() {
    Object.values(lists).forEach((list) => (list.innerHTML = ''));

    tasks.forEach((task) => {
      const card = createCardElement(task);
      if (lists[task.status]) {
        lists[task.status].appendChild(card);
      }
    });

    updateCounts();
    saveTasks();
  }

  function createCardElement(task) {
    const card = document.createElement('div');
    card.className = 'kanban-card';
    card.draggable = true;
    card.dataset.id = task.id;

    card.innerHTML = `
      <div class="card-top">
        <span class="card-title">${escapeHtml(task.title)}</span>
        <div class="card-actions">
          <button class="card-action-btn edit" aria-label="Edit" data-id="${task.id}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="card-action-btn delete" aria-label="Delete" data-id="${task.id}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </button>
        </div>
      </div>
      ${task.desc ? `<p class="card-desc">${escapeHtml(task.desc)}</p>` : ''}
      <span class="card-priority ${task.priority}">${task.priority}</span>
    `;

    // Drag events
    card.addEventListener('dragstart', handleDragStart);
    card.addEventListener('dragend', handleDragEnd);

    // Action buttons
    card.querySelector('.edit').addEventListener('click', () => openEditModal(task.id));
    card.querySelector('.delete').addEventListener('click', () => deleteTask(task.id));

    return card;
  }

  function updateCounts() {
    const counts = { todo: 0, progress: 0, done: 0 };
    tasks.forEach((t) => { if (counts[t.status] !== undefined) counts[t.status]++; });
    $('#countTodo').textContent = counts.todo;
    $('#countProgress').textContent = counts.progress;
    $('#countDone').textContent = counts.done;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------- Drag & Drop ---------- */
  let draggedId = null;

  function handleDragStart(e) {
    draggedId = e.currentTarget.dataset.id;
    e.currentTarget.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', draggedId);
  }

  function handleDragEnd(e) {
    e.currentTarget.classList.remove('dragging');
    draggedId = null;
    $$('.card-list').forEach((l) => l.classList.remove('drag-over'));
  }

  // Setup drop zones
  Object.values(lists).forEach((list) => {
    list.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      list.classList.add('drag-over');
    });

    list.addEventListener('dragleave', () => {
      list.classList.remove('drag-over');
    });

    list.addEventListener('drop', (e) => {
      e.preventDefault();
      list.classList.remove('drag-over');
      const id = e.dataTransfer.getData('text/plain');
      const newStatus = list.dataset.status;
      const task = tasks.find((t) => t.id === id);
      if (task && task.status !== newStatus) {
        task.status = newStatus;
        render();
      }
    });
  });

  /* ---------- Modal ---------- */
  function openAddModal(status) {
    modalTitle.textContent = 'Add Task';
    taskIdField.value = '';
    taskStatusField.value = status;
    taskTitleInput.value = '';
    taskDesc.value = '';
    setSelectedPriority('low');
    modalOverlay.classList.add('active');
    taskTitleInput.focus();
  }

  function openEditModal(id) {
    const task = tasks.find((t) => t.id === id);
    if (!task) return;
    modalTitle.textContent = 'Edit Task';
    taskIdField.value = task.id;
    taskStatusField.value = task.status;
    taskTitleInput.value = task.title;
    taskDesc.value = task.desc || '';
    setSelectedPriority(task.priority);
    modalOverlay.classList.add('active');
    taskTitleInput.focus();
  }

  function closeModal() {
    modalOverlay.classList.remove('active');
  }

  function setSelectedPriority(p) {
    selectedPriority = p;
    $$('.priority-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.priority === p);
    });
  }

  $$('.priority-btn').forEach((btn) => {
    btn.addEventListener('click', () => setSelectedPriority(btn.dataset.priority));
  });

  $$('.add-task-btn').forEach((btn) => {
    btn.addEventListener('click', () => openAddModal(btn.dataset.status));
  });

  cancelModal.addEventListener('click', closeModal);
  modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) closeModal();
  });

  taskForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const title = taskTitleInput.value.trim();
    if (!title) return;

    const id = taskIdField.value;
    if (id) {
      // Edit
      const task = tasks.find((t) => t.id === id);
      if (task) {
        task.title = title;
        task.desc = taskDesc.value.trim();
        task.priority = selectedPriority;
      }
    } else {
      // Add
      tasks.push({
        id: genId(),
        title,
        desc: taskDesc.value.trim(),
        priority: selectedPriority,
        status: taskStatusField.value || 'todo',
        created: Date.now(),
      });
    }

    closeModal();
    render();
  });

  /* ---------- Delete ---------- */
  function deleteTask(id) {
    tasks = tasks.filter((t) => t.id !== id);
    render();
  }

  /* ---------- GSAP Entrance ---------- */
  function initAnimations() {
    gsap.registerPlugin(ScrollTrigger);

    // Cascade from top-left to bottom-right (D20)
    const columns = $$('.column');
    columns.forEach((col, i) => {
      gsap.to(col, {
        opacity: 1,
        x: 0,
        y: 0,
        duration: 0.55,
        ease: 'power2.out',
        delay: 0.12 + i * 0.12,
      });
    });

    // Stats bar
    gsap.from('.stat-pill', {
      y: -10,
      opacity: 0,
      duration: 0.4,
      stagger: 0.06,
      ease: 'power2.out',
      delay: 0.3,
    });
  }

  /* ---------- Init ---------- */
  initTheme();
  loadTasks();
  render();
  initAnimations();
})();
