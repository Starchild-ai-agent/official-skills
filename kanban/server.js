#!/usr/bin/env node
/**
 * Star Child — Kanban Board Server
 *
 * Usage:
 *   node server.js
 *   → Open http://localhost:5555
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = 5555;
const DATA_FILE = path.join(__dirname, 'data.json');

// ============================================================
// Data Store
// ============================================================
function loadData() {
  try {
    if (fs.existsSync(DATA_FILE)) return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  } catch (e) { /* seed fresh */ }
  return seedData();
}

function saveData(data) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

function seedData() {
  const boardId = 'board-001';
  const list1 = 'list-backlog', list2 = 'list-progress', list3 = 'list-review', list4 = 'list-done';

  const data = {
    boards: [
      { id: boardId, front_id: boardId, workspace_id: 'ws-001', title: 'My Board', emoji: ':clipboard:', view_mode: 'grid', active_tasks: 0, connectors: [] },
    ],
    lists: [
      { id: list1, front_id: list1, board_id: boardId, title: 'Backlog', color: '#BDBDBD', order: 'b', auto_participants: [] },
      { id: list2, front_id: list2, board_id: boardId, title: 'In Progress', color: '#004dff', order: 'd', auto_participants: [] },
      { id: list3, front_id: list3, board_id: boardId, title: 'In Review', color: '#ff8607', order: 'f', auto_participants: [] },
      { id: list4, front_id: list4, board_id: boardId, title: 'Done', color: '#04aa11', order: 'h', auto_participants: [] },
    ],
    tasks: [],
  };
  saveData(data);
  return data;
}

let store = loadData();

// Re-read data.json from disk on every request so re-uploads take effect immediately
function getStore() {
  store = loadData();
  return store;
}

// ============================================================
// Server
// ============================================================
const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
  if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

  const url = new URL(req.url, `http://localhost:${PORT}`);
  const p = url.pathname;

  let body = {};
  if (req.method === 'POST') body = await parseBody(req);

  console.log(`${req.method} ${p}`);

  // Always reload from disk so re-uploaded data.json takes effect without restart
  store = loadData();

  try {
    // ---- Boards ----
    if (p === '/ajax/tasks/board/get') return json(res, { data: store.boards });
    if (p === '/ajax/tasks/board/save') { const o = body.object || {}; if (!o.id) { o.id = 'b-' + Date.now(); o.front_id = o.front_id || o.id; } const i = store.boards.findIndex(x => x.id === o.id || x.front_id === o.front_id); if (i >= 0) store.boards[i] = { ...store.boards[i], ...o }; else store.boards.push(o); saveData(store); return json(res, { data: { object: o } }); }
    if (p === '/ajax/tasks/board/remove') { const o = body.object || {}; store.boards = store.boards.filter(x => x.id !== o.id); store.lists = store.lists.filter(x => x.board_id !== o.id); store.tasks = store.tasks.filter(x => x.board_id !== o.id); saveData(store); return json(res, { data: { object: { front_id: o.front_id } } }); }

    // ---- Lists ----
    if (p === '/ajax/tasks/list/get') { const bid = (body.options || {}).board_id; return json(res, { data: bid ? store.lists.filter(x => x.board_id === bid) : store.lists }); }
    if (p === '/ajax/tasks/list/save') { const o = body.object || {}; if (!o.id) { o.id = 'l-' + Date.now(); o.front_id = o.front_id || o.id; } const i = store.lists.findIndex(x => x.id === o.id || x.front_id === o.front_id); if (i >= 0) store.lists[i] = { ...store.lists[i], ...o }; else store.lists.push(o); saveData(store); return json(res, { data: { object: o } }); }
    if (p === '/ajax/tasks/list/remove') { const o = body.object || {}; store.lists = store.lists.filter(x => x.id !== o.id); store.tasks = store.tasks.filter(x => x.list_id !== o.id); saveData(store); return json(res, { data: { object: { front_id: o.front_id } } }); }
    if (p === '/ajax/tasks/list/tasks/archive') { const o = body.object || {}; store.tasks.forEach(t => { if (t.list_id === o.id) t.archived = true; }); saveData(store); return json(res, { data: {} }); }
    if (p === '/ajax/tasks/list/tasks/remove') { const o = body.object || {}; const ao = (body.options || {}).only_archived_tasks; store.tasks = store.tasks.filter(t => t.list_id !== o.id || (ao && !t.archived)); saveData(store); return json(res, { data: {} }); }

    // ---- Tasks ----
    if (p === '/ajax/tasks/task/get') {
      const opts = body.options || {};
      let result = [...store.tasks];

      // board_id filter (existing)
      if (opts.board_id) result = result.filter(x => x.board_id === opts.board_id);

      // list_id / status filter — accepts a single list_id or column name (case-insensitive)
      if (opts.list_id) {
        result = result.filter(x => x.list_id === opts.list_id);
      } else if (opts.status) {
        // match by list title (e.g. "done", "in progress") or list_id
        const sLower = opts.status.toLowerCase();
        const matchedListIds = store.lists
          .filter(l => l.id === opts.status || l.title.toLowerCase() === sLower)
          .map(l => l.id);
        result = result.filter(x => matchedListIds.includes(x.list_id));
      }

      // owner filter — accepts a name / email string, matches against participants
      if (opts.owner) {
        const oLower = opts.owner.toLowerCase();
        result = result.filter(x =>
          (x.participants || []).some(p => (p.user_id_or_mail || '').toLowerCase().includes(oLower))
        );
      }

      // priority filter — high / medium / low
      if (opts.priority) {
        result = result.filter(x => ((x._custom_fields || {}).priority || '') === opts.priority);
      }

      // archived filter — default excludes archived; pass archived=true to include only archived
      if (opts.archived === true || opts.archived === 'true') {
        result = result.filter(x => x.archived);
      } else if (opts.archived === false || opts.archived === 'false') {
        result = result.filter(x => !x.archived);
      }
      // (omit opts.archived → return all, matching existing behaviour)

      // due_before / due_after — unix timestamps for date range filtering
      if (opts.due_before) result = result.filter(x => x.before && x.before <= Number(opts.due_before));
      if (opts.due_after)  result = result.filter(x => x.before && x.before >= Number(opts.due_after));

      // search — full-text across title, description, tags, owners
      if (opts.search) {
        const q = opts.search.toLowerCase();
        result = result.filter(x =>
          (x.title || '').toLowerCase().includes(q) ||
          ((x.description || {}).original_str || '').toLowerCase().includes(q) ||
          (x.tags || []).some(t => t.toLowerCase().includes(q)) ||
          (x.participants || []).some(p => (p.user_id_or_mail || '').toLowerCase().includes(q))
        );
      }

      // sort — title | due_date | priority
      if (opts.sort === 'title') {
        result.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
      } else if (opts.sort === 'due_date') {
        result.sort((a, b) => {
          if (!a.before && !b.before) return 0;
          if (!a.before) return 1;
          if (!b.before) return -1;
          return a.before - b.before;
        });
      } else if (opts.sort === 'priority') {
        const PO = { high: 0, medium: 1, low: 2 };
        result.sort((a, b) => {
          const pa = PO[(a._custom_fields || {}).priority] ?? 3;
          const pb = PO[(b._custom_fields || {}).priority] ?? 3;
          return pa - pb;
        });
      }

      // limit / offset — simple pagination
      if (opts.offset) result = result.slice(Number(opts.offset));
      if (opts.limit)  result = result.slice(0, Number(opts.limit));

      return json(res, { data: result, total: result.length });
    }
    if (p === '/ajax/tasks/task/save') { const o = body.object || {}; if (!o.id) { o.id = 't-' + Date.now(); o.front_id = o.front_id || o.id; } const i = store.tasks.findIndex(x => x.id === o.id || x.front_id === o.front_id); if (i >= 0) store.tasks[i] = { ...store.tasks[i], ...o }; else store.tasks.push(o); saveData(store); return json(res, { data: { object: o } }); }
    if (p === '/ajax/tasks/task/remove') { const o = body.object || {}; store.tasks = store.tasks.filter(x => x.id !== o.id); saveData(store); return json(res, { data: { object: { front_id: o.front_id } } }); }

    // ---- Static files ----
    if (p === '/' || p === '/index.html' || p === '/kanban.html') {
      return serveFile(res, path.join(__dirname, 'kanban.html'), 'text/html');
    }
    if (p === '/favicon.png') {
      return serveFile(res, path.join(__dirname, 'favicon.png'), 'image/png');
    }

    // Catch-all
    return json(res, { data: [], resources: [] });

  } catch (err) {
    console.error('Error:', err);
    res.writeHead(500); res.end(JSON.stringify({ error: err.message }));
  }
});

function parseBody(req) {
  return new Promise(r => { let d = ''; req.on('data', c => d += c); req.on('end', () => { try { r(JSON.parse(d)); } catch { r({}); } }); });
}
function json(res, data) { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(data)); }
function serveFile(res, fp, ct) { try { res.writeHead(200, { 'Content-Type': ct }); res.end(fs.readFileSync(fp)); } catch { res.writeHead(404); res.end('Not found'); } }

server.listen(PORT, () => {
  console.log(`
  Star Child — Kanban Board
  ─────────────────────────
  http://localhost:${PORT}

  ${store.boards.length} board(s), ${store.lists.length} columns, ${store.tasks.length} tasks
  Data: ${DATA_FILE}
`);
});
