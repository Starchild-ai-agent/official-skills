/* ============================================
 * JSON Formatter & Validator — D29
 * Pure frontend, syntax highlighting, tree view
 * ============================================ */

(function () {
  'use strict';

  /* ---------- DOM ---------- */
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  const jsonInput = $('#jsonInput');
  const formattedOutput = $('#formattedOutput');
  const treeOutput = $('#treeOutput');
  const errorBar = $('#errorBar');
  const pathDisplay = $('#pathDisplay');
  const pasteBtn = $('#pasteBtn');
  const sampleBtn = $('#sampleBtn');
  const clearBtn = $('#clearBtn');
  const copyBtn = $('#copyBtn');
  const themeToggle = $('#themeToggle');

  /* ---------- State ---------- */
  let currentIndent = 2;
  let currentView = 'formatted';
  let parsedJson = null;
  let lastFormatted = '';

  /* ---------- Sample JSON ---------- */
  const SAMPLE_JSON = {
    name: 'JSON Formatter',
    version: '1.0.0',
    description: 'A powerful JSON formatting and validation tool',
    features: ['syntax highlighting', 'tree view', 'path finder', 'minify'],
    config: {
      theme: 'auto',
      indent: 2,
      maxDepth: null,
      strict: true,
    },
    stats: {
      users: 12450,
      rating: 4.8,
      downloads: 98200,
    },
    tags: ['developer', 'productivity', 'json'],
    repository: {
      type: 'git',
      url: 'https://github.com/example/json-formatter',
    },
    active: true,
    deprecated: false,
    license: 'MIT',
  };

  /* ---------- Theme ---------- */
  function initTheme() {
    const saved = localStorage.getItem('json-fmt-theme');
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
    localStorage.setItem('json-fmt-theme', next);
  });

  /* ---------- Parse & Validate ---------- */
  function parseInput() {
    const raw = jsonInput.value.trim();
    if (!raw) {
      parsedJson = null;
      errorBar.classList.remove('visible');
      formattedOutput.innerHTML = '<span style="color:var(--text-muted)">Output will appear here...</span>';
      treeOutput.innerHTML = '';
      pathDisplay.textContent = '';
      return;
    }

    try {
      parsedJson = JSON.parse(raw);
      errorBar.classList.remove('visible');
      renderOutput();
    } catch (err) {
      parsedJson = null;
      const msg = err.message;
      // Try to extract position
      const posMatch = msg.match(/position\s+(\d+)/i);
      let detail = msg;
      if (posMatch) {
        const pos = parseInt(posMatch[1], 10);
        const line = raw.substring(0, pos).split('\n').length;
        const col = pos - raw.lastIndexOf('\n', pos - 1);
        detail = `${msg} (line ${line}, col ${col})`;
      }
      errorBar.textContent = '✗ ' + detail;
      errorBar.classList.add('visible');
      formattedOutput.innerHTML = '';
      treeOutput.innerHTML = '';
    }
  }

  /* ---------- Render Output ---------- */
  function renderOutput() {
    if (parsedJson === null) return;

    if (currentView === 'formatted') {
      formattedOutput.style.display = '';
      treeOutput.style.display = 'none';
      const indentStr = currentIndent === 'tab' ? '\t' : parseInt(currentIndent, 10);
      lastFormatted = JSON.stringify(parsedJson, null, indentStr);
      formattedOutput.innerHTML = syntaxHighlight(lastFormatted);
    } else if (currentView === 'minified') {
      formattedOutput.style.display = '';
      treeOutput.style.display = 'none';
      lastFormatted = JSON.stringify(parsedJson);
      formattedOutput.innerHTML = syntaxHighlight(lastFormatted);
    } else if (currentView === 'tree') {
      formattedOutput.style.display = 'none';
      treeOutput.style.display = '';
      treeOutput.innerHTML = '';
      lastFormatted = JSON.stringify(parsedJson, null, currentIndent === 'tab' ? '\t' : parseInt(currentIndent, 10));
      buildTree(parsedJson, treeOutput, '$');
    }
  }

  /* ---------- Syntax Highlighting ---------- */
  function syntaxHighlight(json) {
    return json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(
        /("(\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
        function (match) {
          let cls = 'syn-number';
          if (/^"/.test(match)) {
            if (/:$/.test(match)) {
              cls = 'syn-key';
            } else {
              cls = 'syn-string';
            }
          } else if (/true|false/.test(match)) {
            cls = 'syn-bool';
          } else if (/null/.test(match)) {
            cls = 'syn-null';
          }
          return '<span class="' + cls + '">' + match + '</span>';
        }
      );
  }

  /* ---------- Tree View ---------- */
  function buildTree(data, container, path) {
    if (data === null) {
      appendLeaf(container, 'null', 'syn-null', path);
      return;
    }

    if (typeof data !== 'object') {
      const cls = typeof data === 'string' ? 'syn-string' : typeof data === 'number' ? 'syn-number' : typeof data === 'boolean' ? 'syn-bool' : 'syn-null';
      const val = typeof data === 'string' ? `"${escapeHtml(data)}"` : String(data);
      appendLeaf(container, val, cls, path);
      return;
    }

    const isArray = Array.isArray(data);
    const entries = isArray ? data.map((v, i) => [i, v]) : Object.entries(data);

    entries.forEach(([key, value]) => {
      const childPath = isArray ? `${path}[${key}]` : `${path}.${key}`;

      if (value !== null && typeof value === 'object') {
        // Collapsible node
        const node = document.createElement('div');
        node.className = 'tree-node';

        const keyEl = document.createElement('span');
        keyEl.className = 'tree-key';

        const toggle = document.createElement('span');
        toggle.className = 'tree-toggle';
        toggle.textContent = '▼';

        const label = document.createElement('span');
        const bracket = Array.isArray(value) ? `[${value.length}]` : `{${Object.keys(value).length}}`;
        label.innerHTML = `<span class="syn-key">${escapeHtml(String(key))}</span>: <span class="syn-bracket">${bracket}</span>`;

        keyEl.appendChild(toggle);
        keyEl.appendChild(label);
        node.appendChild(keyEl);

        const children = document.createElement('div');
        children.className = 'tree-children';
        buildTree(value, children, childPath);
        node.appendChild(children);

        // Toggle collapse
        keyEl.addEventListener('click', (e) => {
          e.stopPropagation();
          toggle.classList.toggle('collapsed');
          children.classList.toggle('collapsed');
        });

        // Path click
        keyEl.addEventListener('dblclick', (e) => {
          e.stopPropagation();
          pathDisplay.textContent = childPath;
        });

        container.appendChild(node);
      } else {
        // Leaf
        const leaf = document.createElement('div');
        leaf.className = 'tree-leaf';
        const cls = value === null ? 'syn-null' : typeof value === 'string' ? 'syn-string' : typeof value === 'number' ? 'syn-number' : 'syn-bool';
        const val = value === null ? 'null' : typeof value === 'string' ? `"${escapeHtml(value)}"` : String(value);
        leaf.innerHTML = `<span class="syn-key">${escapeHtml(String(key))}</span>: <span class="${cls}">${val}</span>`;

        leaf.style.cursor = 'pointer';
        leaf.addEventListener('click', () => {
          pathDisplay.textContent = childPath;
        });

        container.appendChild(leaf);
      }
    });
  }

  function appendLeaf(container, val, cls, path) {
    const leaf = document.createElement('div');
    leaf.className = 'tree-leaf';
    leaf.innerHTML = `<span class="${cls}">${val}</span>`;
    leaf.style.cursor = 'pointer';
    leaf.addEventListener('click', () => {
      pathDisplay.textContent = path;
    });
    container.appendChild(leaf);
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------- Controls ---------- */
  // Indent selector
  $$('.indent-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      $$('.indent-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentIndent = btn.dataset.indent === 'tab' ? 'tab' : parseInt(btn.dataset.indent, 10);
      renderOutput();
    });
  });

  // View selector
  $$('.view-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      $$('.view-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentView = btn.dataset.view;
      renderOutput();
    });
  });

  // Paste
  pasteBtn.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      jsonInput.value = text;
      parseInput();
    } catch {
      // Fallback: focus input for manual paste
      jsonInput.focus();
    }
  });

  // Sample
  sampleBtn.addEventListener('click', () => {
    jsonInput.value = JSON.stringify(SAMPLE_JSON, null, 2);
    parseInput();
  });

  // Clear
  clearBtn.addEventListener('click', () => {
    jsonInput.value = '';
    parseInput();
    pathDisplay.textContent = '';
  });

  // Copy
  copyBtn.addEventListener('click', async () => {
    if (!lastFormatted) return;
    try {
      await navigator.clipboard.writeText(lastFormatted);
      const orig = copyBtn.innerHTML;
      copyBtn.innerHTML = '✓ Copied!';
      setTimeout(() => { copyBtn.innerHTML = orig; }, 1500);
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = lastFormatted;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
  });

  /* ---------- Input Listener ---------- */
  let parseTimeout = null;
  jsonInput.addEventListener('input', () => {
    clearTimeout(parseTimeout);
    parseTimeout = setTimeout(parseInput, 200);
  });

  /* ---------- GSAP Entrance ---------- */
  function initAnimations() {
    gsap.registerPlugin(ScrollTrigger);

    // D13: blur(8px) → blur(0)
    gsap.to('.hero-tool', {
      opacity: 1,
      filter: 'blur(0px)',
      duration: 0.7,
      ease: 'power2.out',
      delay: 0.1,
    });

    gsap.to('.output-section', {
      opacity: 1,
      filter: 'blur(0px)',
      duration: 0.6,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '.output-section',
        start: 'top 90%',
      },
    });

    gsap.from('.controls-row > *', {
      y: 10,
      opacity: 0,
      duration: 0.4,
      stagger: 0.06,
      ease: 'power2.out',
      delay: 0.5,
    });
  }

  /* ---------- Init ---------- */
  initTheme();

  // Load from localStorage if available
  const savedInput = localStorage.getItem('json-fmt-input');
  if (savedInput) {
    jsonInput.value = savedInput;
  }

  // Auto-save input
  jsonInput.addEventListener('input', () => {
    localStorage.setItem('json-fmt-input', jsonInput.value);
  });

  parseInput();
  initAnimations();
})();
