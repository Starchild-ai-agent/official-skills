/* ============================================================
   Pixel Art Editor — script.js
   Skeleton: A3 Split Screen · Hover: C9 box-shadow
   Entrance: D1 translateY(40px) · Hero: H7 Minimal
   ============================================================ */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return document.querySelectorAll(s); };

  var PALETTE_COLORS = [
    '#e11d48', '#f97316', '#eab308', '#22c55e',
    '#06b6d4', '#6366f1', '#a855f7', '#ec4899',
    '#000000', '#374151', '#6b7280', '#9ca3af',
    '#d1d5db', '#f3f4f6', '#ffffff', '#92400e'
  ];

  var gridSize = 16;
  var pixelSize = 24;
  var currentTool = 'pen';
  var currentColor = '#e11d48';
  var isDrawing = false;
  var grid = [];
  var undoStack = [];
  var redoStack = [];
  var canvas = $('#pixelCanvas');
  var ctx = canvas.getContext('2d');

  /* ---------- Theme ---------- */
  var savedTheme = localStorage.getItem('pe_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  $('#themeToggle').addEventListener('click', function () {
    var cur = document.documentElement.getAttribute('data-theme');
    var nxt = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nxt);
    localStorage.setItem('pe_theme', nxt);
    drawGrid();
  });

  /* ---------- Init Grid ---------- */
  function initGrid() {
    grid = [];
    for (var y = 0; y < gridSize; y++) {
      grid[y] = [];
      for (var x = 0; x < gridSize; x++) {
        grid[y][x] = null;
      }
    }
    canvas.width = gridSize * pixelSize;
    canvas.height = gridSize * pixelSize;
    undoStack = [];
    redoStack = [];
    drawGrid();
  }

  function drawGrid() {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var bgColor = isDark ? '#1a1a1a' : '#f0f0f0';
    var lineColor = isDark ? '#333' : '#ddd';

    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (var y = 0; y < gridSize; y++) {
      for (var x = 0; x < gridSize; x++) {
        if (grid[y][x]) {
          ctx.fillStyle = grid[y][x];
          ctx.fillRect(x * pixelSize, y * pixelSize, pixelSize, pixelSize);
        }
      }
    }

    // Grid lines
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 0.5;
    for (var i = 0; i <= gridSize; i++) {
      ctx.beginPath();
      ctx.moveTo(i * pixelSize, 0);
      ctx.lineTo(i * pixelSize, canvas.height);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * pixelSize);
      ctx.lineTo(canvas.width, i * pixelSize);
      ctx.stroke();
    }
  }

  /* ---------- Save State ---------- */
  function saveState() {
    undoStack.push(grid.map(function (row) { return row.slice(); }));
    if (undoStack.length > 50) undoStack.shift();
    redoStack = [];
  }

  /* ---------- Tools ---------- */
  function getPixelCoords(e) {
    var rect = canvas.getBoundingClientRect();
    var scaleX = canvas.width / rect.width;
    var scaleY = canvas.height / rect.height;
    var x = Math.floor((e.clientX - rect.left) * scaleX / pixelSize);
    var y = Math.floor((e.clientY - rect.top) * scaleY / pixelSize);
    return { x: Math.max(0, Math.min(x, gridSize - 1)), y: Math.max(0, Math.min(y, gridSize - 1)) };
  }

  function applyTool(x, y) {
    if (currentTool === 'pen') {
      grid[y][x] = currentColor;
    } else if (currentTool === 'eraser') {
      grid[y][x] = null;
    } else if (currentTool === 'fill') {
      floodFill(x, y, grid[y][x], currentColor);
    }
    drawGrid();
  }

  function floodFill(x, y, targetColor, fillColor) {
    if (x < 0 || x >= gridSize || y < 0 || y >= gridSize) return;
    if (grid[y][x] !== targetColor) return;
    if (targetColor === fillColor) return;
    grid[y][x] = fillColor;
    floodFill(x + 1, y, targetColor, fillColor);
    floodFill(x - 1, y, targetColor, fillColor);
    floodFill(x, y + 1, targetColor, fillColor);
    floodFill(x, y - 1, targetColor, fillColor);
  }

  /* ---------- Canvas Events ---------- */
  canvas.addEventListener('mousedown', function (e) {
    isDrawing = true;
    saveState();
    var p = getPixelCoords(e);
    applyTool(p.x, p.y);
  });
  canvas.addEventListener('mousemove', function (e) {
    if (!isDrawing) return;
    if (currentTool === 'fill') return;
    var p = getPixelCoords(e);
    applyTool(p.x, p.y);
  });
  canvas.addEventListener('mouseup', function () { isDrawing = false; });
  canvas.addEventListener('mouseleave', function () { isDrawing = false; });

  // Touch support
  canvas.addEventListener('touchstart', function (e) {
    e.preventDefault();
    isDrawing = true;
    saveState();
    var t = e.touches[0];
    var p = getPixelCoords(t);
    applyTool(p.x, p.y);
  });
  canvas.addEventListener('touchmove', function (e) {
    e.preventDefault();
    if (!isDrawing || currentTool === 'fill') return;
    var t = e.touches[0];
    var p = getPixelCoords(t);
    applyTool(p.x, p.y);
  });
  canvas.addEventListener('touchend', function () { isDrawing = false; });

  /* ---------- Tool Selection ---------- */
  $$('.tool-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      $$('.tool-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentTool = btn.dataset.tool;
    });
  });

  /* ---------- Size Selection ---------- */
  $$('.size-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      $$('.size-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      gridSize = parseInt(btn.dataset.size);
      pixelSize = gridSize === 16 ? 24 : 14;
      initGrid();
    });
  });

  /* ---------- Color ---------- */
  $('#colorPicker').addEventListener('input', function (e) {
    currentColor = e.target.value;
  });

  /* ---------- Palette ---------- */
  var paletteEl = $('#palette');
  PALETTE_COLORS.forEach(function (c) {
    var swatch = document.createElement('div');
    swatch.className = 'palette__swatch';
    swatch.style.backgroundColor = c;
    swatch.addEventListener('click', function () {
      currentColor = c;
      $('#colorPicker').value = c;
    });
    paletteEl.appendChild(swatch);
  });

  /* ---------- Undo / Redo ---------- */
  $('#undoBtn').addEventListener('click', function () {
    if (undoStack.length === 0) return;
    redoStack.push(grid.map(function (row) { return row.slice(); }));
    grid = undoStack.pop();
    drawGrid();
  });
  $('#redoBtn').addEventListener('click', function () {
    if (redoStack.length === 0) return;
    undoStack.push(grid.map(function (row) { return row.slice(); }));
    grid = redoStack.pop();
    drawGrid();
  });

  /* ---------- Clear ---------- */
  $('#clearBtn').addEventListener('click', function () {
    saveState();
    initGrid();
  });

  /* ---------- Export ---------- */
  $('#exportBtn').addEventListener('click', function () {
    var exportCanvas = document.createElement('canvas');
    exportCanvas.width = gridSize;
    exportCanvas.height = gridSize;
    var ectx = exportCanvas.getContext('2d');
    for (var y = 0; y < gridSize; y++) {
      for (var x = 0; x < gridSize; x++) {
        if (grid[y][x]) {
          ectx.fillStyle = grid[y][x];
          ectx.fillRect(x, y, 1, 1);
        }
      }
    }
    var link = document.createElement('a');
    link.download = 'pixel-art-' + gridSize + 'x' + gridSize + '.png';
    link.href = exportCanvas.toDataURL('image/png');
    link.click();
  });

  /* ---------- Init ---------- */
  initGrid();

  /* ---------- GSAP ---------- */
  if (typeof gsap !== 'undefined') {
    var mm = gsap.matchMedia();
    mm.add('(prefers-reduced-motion: no-preference)', function () {
      gsap.from('.toolbar__title', { y: 40, opacity: 0, duration: 0.6, ease: 'power2.out' });
      gsap.from('.toolbar__section', { y: 40, opacity: 0, duration: 0.5, stagger: 0.08, delay: 0.1, ease: 'power2.out' });
      gsap.from('.canvas-wrap', { y: 40, opacity: 0, duration: 0.7, delay: 0.3, ease: 'power2.out' });
    });
  }
})();
