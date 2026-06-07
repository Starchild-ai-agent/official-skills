/* ============================================
 * Markdown Editor — D28
 * marked.js + Prism.js, localStorage auto-save
 * ============================================ */

(function () {
  'use strict';

  /* ---------- DOM ---------- */
  const $ = (s) => document.querySelector(s);
  const textarea = $('#editorTextarea');
  const previewContent = $('#previewContent');
  const wordCountEl = $('#wordCount');
  const lineCountEl = $('#lineCount');
  const autoSaveBadge = $('#autoSaveBadge');
  const themeToggle = $('#themeToggle');
  const exportHtml = $('#exportHtml');
  const exportMd = $('#exportMd');

  /* ---------- Default Content ---------- */
  const DEFAULT_MD = `# Welcome to Markdown Editor

Write your documentation here with **live preview**.

## Features

- **Bold**, *italic*, and \`inline code\`
- Headings, lists, and blockquotes
- Code blocks with syntax highlighting
- Auto-save to localStorage

## Code Example

\`\`\`javascript
function greet(name) {
  return \`Hello, \${name}!\`;
}

console.log(greet('World'));
\`\`\`

## Blockquote

> The best way to predict the future is to invent it.
> — Alan Kay

## Table

| Feature | Status |
|---------|--------|
| Live Preview | ✅ |
| Syntax Highlighting | ✅ |
| Auto-save | ✅ |
| Export | ✅ |

---

Start editing to see the magic happen!
`;

  /* ---------- Theme ---------- */
  function initTheme() {
    const saved = localStorage.getItem('md-editor-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else if (window.matchMedia('(prefers-color-scheme: light)').matches) {
      document.documentElement.setAttribute('data-theme', 'light');
    }
  }

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('md-editor-theme', next);
  });

  /* ---------- Marked Config ---------- */
  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function (code, lang) {
      if (Prism.languages[lang]) {
        return Prism.highlight(code, Prism.languages[lang], lang);
      }
      return code;
    },
  });

  /* ---------- Render Preview ---------- */
  let renderTimeout = null;

  function renderPreview() {
    const md = textarea.value;
    try {
      previewContent.innerHTML = marked.parse(md);
    } catch {
      previewContent.innerHTML = '<p style="color:var(--text-muted)">Error rendering markdown.</p>';
    }
    updateStats(md);
  }

  function debouncedRender() {
    clearTimeout(renderTimeout);
    renderTimeout = setTimeout(() => {
      renderPreview();
      autoSave();
    }, 150);
  }

  /* ---------- Stats ---------- */
  function updateStats(md) {
    const text = md.trim();
    const words = text ? text.split(/\s+/).length : 0;
    const lines = text ? text.split('\n').length : 0;
    wordCountEl.textContent = words;
    lineCountEl.textContent = lines;
  }

  /* ---------- Auto-save ---------- */
  let saveTimeout = null;

  function autoSave() {
    clearTimeout(saveTimeout);
    autoSaveBadge.textContent = 'Saving...';
    autoSaveBadge.style.opacity = '1';
    saveTimeout = setTimeout(() => {
      localStorage.setItem('md-editor-content', textarea.value);
      autoSaveBadge.textContent = 'Saved';
      setTimeout(() => { autoSaveBadge.style.opacity = '0.7'; }, 800);
    }, 500);
  }

  function loadContent() {
    const saved = localStorage.getItem('md-editor-content');
    textarea.value = saved !== null ? saved : DEFAULT_MD;
    renderPreview();
  }

  /* ---------- Toolbar Actions ---------- */
  function wrapSelection(before, after) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = textarea.value.substring(start, end);
    const replacement = before + (selected || 'text') + (after || before);
    textarea.value = textarea.value.substring(0, start) + replacement + textarea.value.substring(end);
    textarea.selectionStart = start + before.length;
    textarea.selectionEnd = start + before.length + (selected || 'text').length;
    textarea.focus();
    debouncedRender();
  }

  function insertAtLineStart(prefix) {
    const start = textarea.selectionStart;
    const val = textarea.value;
    const lineStart = val.lastIndexOf('\n', start - 1) + 1;
    textarea.value = val.substring(0, lineStart) + prefix + val.substring(lineStart);
    textarea.selectionStart = textarea.selectionEnd = start + prefix.length;
    textarea.focus();
    debouncedRender();
  }

  const actions = {
    bold: () => wrapSelection('**', '**'),
    italic: () => wrapSelection('*', '*'),
    h1: () => insertAtLineStart('# '),
    h2: () => insertAtLineStart('## '),
    h3: () => insertAtLineStart('### '),
    link: () => {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const selected = textarea.value.substring(start, end) || 'link text';
      const replacement = `[${selected}](url)`;
      textarea.value = textarea.value.substring(0, start) + replacement + textarea.value.substring(end);
      textarea.focus();
      debouncedRender();
    },
    code: () => wrapSelection('`', '`'),
    codeblock: () => {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const selected = textarea.value.substring(start, end) || 'code here';
      const replacement = '\n```\n' + selected + '\n```\n';
      textarea.value = textarea.value.substring(0, start) + replacement + textarea.value.substring(end);
      textarea.focus();
      debouncedRender();
    },
    ul: () => insertAtLineStart('- '),
    ol: () => insertAtLineStart('1. '),
  };

  document.querySelectorAll('.tool-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.action;
      if (actions[action]) actions[action]();
    });
  });

  /* ---------- Keyboard Shortcuts ---------- */
  textarea.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
      e.preventDefault();
      actions.bold();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
      e.preventDefault();
      actions.italic();
    }
    // Tab support
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = textarea.selectionStart;
      textarea.value = textarea.value.substring(0, start) + '  ' + textarea.value.substring(textarea.selectionEnd);
      textarea.selectionStart = textarea.selectionEnd = start + 2;
      debouncedRender();
    }
  });

  /* ---------- Export ---------- */
  function downloadFile(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  exportHtml.addEventListener('click', () => {
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Exported Document</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; line-height: 1.7; color: #1a1a1a; }
    code { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
    pre code { display: block; padding: 1rem; overflow-x: auto; }
    blockquote { border-left: 3px solid #059669; padding: 0.5rem 1rem; margin: 1rem 0; background: #ecfdf5; }
    table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
  </style>
</head>
<body>
${previewContent.innerHTML}
</body>
</html>`;
    downloadFile(html, 'document.html', 'text/html');
  });

  exportMd.addEventListener('click', () => {
    downloadFile(textarea.value, 'document.md', 'text/markdown');
  });

  /* ---------- Input Listener ---------- */
  textarea.addEventListener('input', debouncedRender);

  /* ---------- Divider Resize ---------- */
  const divider = $('#dividerHandle');
  const editorPane = $('#editorPane');
  const previewPane = $('#previewPane');
  let isDragging = false;

  divider.addEventListener('mousedown', (e) => {
    isDragging = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const container = document.querySelector('.split-screen');
    const rect = container.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    const clamped = Math.max(0.2, Math.min(0.8, ratio));
    editorPane.style.flex = `0 0 ${clamped * 100}%`;
    previewPane.style.flex = `0 0 ${(1 - clamped) * 100 - 0.5}%`;
  });

  document.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  });

  /* ---------- GSAP Entrance ---------- */
  function initAnimations() {
    gsap.registerPlugin(ScrollTrigger);

    // D7: translateX(-20px) entrance
    gsap.to('.editor-pane', {
      opacity: 1,
      x: 0,
      duration: 0.6,
      ease: 'power2.out',
      delay: 0.1,
    });

    gsap.to('.preview-pane', {
      opacity: 1,
      x: 0,
      duration: 0.6,
      ease: 'power2.out',
      delay: 0.25,
    });

    gsap.from('.tool-btn', {
      y: -8,
      opacity: 0,
      duration: 0.35,
      stagger: 0.03,
      ease: 'power2.out',
      delay: 0.4,
    });
  }

  /* ---------- Init ---------- */
  initTheme();
  loadContent();
  initAnimations();
})();
