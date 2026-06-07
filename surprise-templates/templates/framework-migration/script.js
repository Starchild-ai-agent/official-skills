/* ============================================================
   Framework Migration Guide — script.js

   Skeleton: A5 Vertical Stacked
   Hover: C11 底部阴影
   Entrance: D12 交替方向
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Mock Data ---------- */
  const CHECKLIST_DATA = [
    { label: 'Node.js version >= 18', hint: 'Check with node -v', checked: false },
    { label: 'All tests passing', hint: 'Run full test suite before migration', checked: false },
    { label: 'Dependencies audit', hint: 'Check for deprecated packages', checked: false },
    { label: 'TypeScript strict mode', hint: 'Enable strict for better type safety', checked: false },
    { label: 'Git branch created', hint: 'Create a dedicated migration branch', checked: false },
    { label: 'CI/CD pipeline ready', hint: 'Ensure pipeline supports new framework', checked: false },
    { label: 'Backup database', hint: 'Snapshot current state before changes', checked: false },
    { label: 'Team notified', hint: 'Communicate migration timeline to team', checked: false },
  ];

  var TIMELINE_DATA = [
    { step: 1, title: 'Audit Current Codebase', desc: 'Analyze existing patterns, dependencies, and custom configurations that need migration.', tags: ['analysis', 'planning'] },
    { step: 2, title: 'Update Build Tooling', desc: 'Migrate build configuration, update bundler plugins, and verify dev server compatibility.', tags: ['tooling', 'config'] },
    { step: 3, title: 'Install New Dependencies', desc: 'Add new framework packages, remove deprecated ones, resolve peer dependency conflicts.', tags: ['npm', 'dependencies'] },
    { step: 4, title: 'Migrate Core Components', desc: 'Convert foundational components first: layouts, providers, routing setup.', tags: ['components', 'core'] },
    { step: 5, title: 'Update State Management', desc: 'Adapt store patterns to new framework idioms. Migrate actions, reducers, and selectors.', tags: ['state', 'store'] },
    { step: 6, title: 'Migrate Feature Modules', desc: 'Convert feature-specific components, hooks, and utilities module by module.', tags: ['features', 'modules'] },
    { step: 7, title: 'Update Tests', desc: 'Rewrite unit and integration tests for new component APIs and testing utilities.', tags: ['testing', 'jest'] },
    { step: 8, title: 'Performance and QA', desc: 'Run lighthouse audits, check bundle size, verify SSR/SSG, and conduct full QA pass.', tags: ['performance', 'qa'] },
  ];

  var CODE_DIFFS = [
    {
      title: 'Component Definition',
      old: '// Old: Class Component\nclass UserCard extends Component {\n  constructor(props) {\n    super(props);\n    this.state = { loading: true };\n  }\n\n  componentDidMount() {\n    this.fetchUser();\n  }\n\n  render() {\n    return <div>{this.state.name}</div>;\n  }\n}',
      new: '// New: Function Component\nfunction UserCard({ userId }) {\n  const [user, setUser] = useState(null);\n  const [loading, setLoading] = useState(true);\n\n  useEffect(() => {\n    fetchUser(userId).then(setUser);\n  }, [userId]);\n\n  return <div>{user?.name}</div>;\n}',
    },
    {
      title: 'State Management',
      old: '// Old: Redux connect HOC\nconst mapState = (state) => ({\n  items: state.cart.items,\n  total: state.cart.total,\n});\n\nconst mapDispatch = { addItem, removeItem };\n\nexport default connect(\n  mapState, mapDispatch\n)(CartView);',
      new: '// New: Redux hooks\nfunction CartView() {\n  const items = useSelector(\n    (s) => s.cart.items\n  );\n  const total = useSelector(\n    (s) => s.cart.total\n  );\n  const dispatch = useDispatch();\n\n  return <div>...</div>;\n}',
    },
    {
      title: 'Routing',
      old: '// Old: Route config array\nconst routes = [\n  {\n    path: "/dashboard",\n    component: Dashboard,\n    exact: true,\n  },\n  {\n    path: "/settings",\n    component: Settings,\n  },\n];\n\n<Switch>\n  {routes.map(r => <Route ...r />)}\n</Switch>',
      new: '// New: File-based routing\n// app/dashboard/page.tsx\nexport default function Dashboard() {\n  return <DashboardView />;\n}\n\n// app/settings/page.tsx\nexport default function Settings() {\n  return <SettingsView />;\n}',
    },
  ];

  var RISK_DATA = [
    { level: 'high', title: 'Breaking API Changes', desc: 'Core framework APIs have changed significantly between versions.', mitigation: 'Use codemods where available. Migrate incrementally with compatibility layers.' },
    { level: 'high', title: 'Third-party Compatibility', desc: 'Some libraries may not support the new framework version yet.', mitigation: 'Audit all dependencies before starting. Find alternatives for unsupported packages.' },
    { level: 'medium', title: 'Performance Regression', desc: 'New rendering model may cause unexpected performance changes.', mitigation: 'Benchmark critical paths before and after. Use profiling tools to identify regressions.' },
    { level: 'medium', title: 'Team Learning Curve', desc: 'New patterns and APIs require team ramp-up time.', mitigation: 'Schedule knowledge-sharing sessions. Create internal migration cookbook.' },
    { level: 'low', title: 'CSS-in-JS Changes', desc: 'Styling approach may need updates for SSR compatibility.', mitigation: 'Test styling in both CSR and SSR modes. Consider CSS Modules as fallback.' },
    { level: 'low', title: 'Build Time Increase', desc: 'New tooling may initially increase build times.', mitigation: 'Enable incremental builds. Use SWC or esbuild for faster compilation.' },
  ];

  var RESOURCES_DATA = [
    { icon: '\u{1F4D6}', name: 'Official Migration Guide', url: 'https://framework.dev/migration' },
    { icon: '\u{1F527}', name: 'Codemod CLI Tool', url: 'https://github.com/codemod-com/codemod' },
    { icon: '\u{1F4E6}', name: 'Compatibility Checker', url: 'https://npmjs.com/package/check-compat' },
    { icon: '\u{1F4AC}', name: 'Community Discord', url: 'https://discord.gg/framework' },
    { icon: '\u{1F4DD}', name: 'Migration Blog Post', url: 'https://blog.framework.dev/migration-guide' },
    { icon: '\u{1F3A5}', name: 'Video Walkthrough', url: 'https://youtube.com/watch?v=migration' },
  ];

  /* ---------- Theme Toggle ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('fm-theme', theme);
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    setTheme(current === 'light' ? 'dark' : 'light');
  });
  var savedTheme = localStorage.getItem('fm-theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(savedTheme);

  /* ---------- Render Checklist ---------- */
  function renderChecklist() {
    var grid = document.getElementById('checklist-grid');
    var html = '';
    CHECKLIST_DATA.forEach(function (item, i) {
      html += '<div class="checklist-item" data-index="' + i + '">' +
        '<div class="checklist-item__check">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' +
        '</div>' +
        '<div class="checklist-item__text">' +
        '<div class="checklist-item__label">' + item.label + '</div>' +
        '<div class="checklist-item__hint">' + item.hint + '</div>' +
        '</div></div>';
    });
    grid.innerHTML = html;

    grid.querySelectorAll('.checklist-item').forEach(function (el) {
      el.addEventListener('click', function () {
        el.classList.toggle('checked');
      });
    });
  }

  /* ---------- Render Timeline ---------- */
  function renderTimeline() {
    var list = document.getElementById('timeline-list');
    var html = '';
    TIMELINE_DATA.forEach(function (item) {
      var tagsHtml = item.tags.map(function (t) {
        return '<span class="timeline-step__tag">' + t + '</span>';
      }).join('');
      html += '<div class="timeline-step">' +
        '<div class="timeline-step__dot"></div>' +
        '<div class="timeline-step__number">Step ' + item.step + '</div>' +
        '<div class="timeline-step__title">' + item.title + '</div>' +
        '<div class="timeline-step__desc">' + item.desc + '</div>' +
        '<div class="timeline-step__tags">' + tagsHtml + '</div>' +
        '</div>';
    });
    list.innerHTML = html;
  }

  /* ---------- Render Code Diffs ---------- */
  function renderCodeDiffs() {
    var container = document.getElementById('code-diffs');
    var html = '';
    CODE_DIFFS.forEach(function (diff) {
      html += '<div class="code-diff">' +
        '<div class="code-diff__header">' + diff.title + '</div>' +
        '<div class="code-diff__panels">' +
        '<div class="code-diff__panel code-diff__panel--old">' +
        '<div class="code-diff__panel-label">Before</div>' +
        '<code>' + escapeHtml(diff.old) + '</code></div>' +
        '<div class="code-diff__panel code-diff__panel--new">' +
        '<div class="code-diff__panel-label">After</div>' +
        '<code>' + escapeHtml(diff.new) + '</code></div>' +
        '</div></div>';
    });
    container.innerHTML = html;
  }

  /* ---------- Render Risk Grid ---------- */
  function renderRiskGrid() {
    var grid = document.getElementById('risk-grid');
    var html = '';
    RISK_DATA.forEach(function (risk) {
      html += '<div class="risk-card">' +
        '<div class="risk-card__level risk-card__level--' + risk.level + '">' + risk.level.toUpperCase() + ' RISK</div>' +
        '<div class="risk-card__title">' + risk.title + '</div>' +
        '<div class="risk-card__desc">' + risk.desc + '</div>' +
        '<div class="risk-card__mitigation"><strong>Mitigation:</strong> ' + risk.mitigation + '</div>' +
        '</div>';
    });
    grid.innerHTML = html;
  }

  /* ---------- Render Resources ---------- */
  function renderResources() {
    var list = document.getElementById('resources-list');
    var html = '';
    RESOURCES_DATA.forEach(function (res) {
      html += '<a class="resource-item" href="' + res.url + '" target="_blank" rel="noopener noreferrer">' +
        '<div class="resource-item__icon">' + res.icon + '</div>' +
        '<div class="resource-item__info">' +
        '<div class="resource-item__name">' + res.name + '</div>' +
        '<div class="resource-item__url">' + res.url + '</div>' +
        '</div>' +
        '<span class="resource-item__arrow">\u2192</span>' +
        '</a>';
    });
    list.innerHTML = html;
  }

  /* ---------- Utility ---------- */
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------- GSAP Animations (D12 alternating direction) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero entrance */
    gsap.from('.hero__label', { opacity: 0, y: 20, duration: 0.6, ease: 'power3.out' });
    gsap.from('.hero__title', { opacity: 0, y: 30, duration: 0.8, delay: 0.15, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { opacity: 0, y: 20, duration: 0.6, delay: 0.3, ease: 'power3.out' });
    gsap.from('.hero__meta', { opacity: 0, y: 15, duration: 0.5, delay: 0.45, ease: 'power3.out' });

    /* Checklist items — alternating left/right */
    gsap.utils.toArray('.checklist-item').forEach(function (el, i) {
      var fromX = i % 2 === 0 ? -30 : 30;
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%', toggleActions: 'play none none none' },
        opacity: 0, x: fromX, duration: 0.5, delay: i * 0.05, ease: 'power2.out',
      });
    });

    /* Timeline steps — alternating */
    gsap.utils.toArray('.timeline-step').forEach(function (el, i) {
      var fromX = i % 2 === 0 ? -40 : 40;
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 85%', toggleActions: 'play none none none' },
        opacity: 0, x: fromX, duration: 0.6, delay: i * 0.08, ease: 'power2.out',
      });
    });

    /* Code diffs — alternating */
    gsap.utils.toArray('.code-diff').forEach(function (el, i) {
      var fromX = i % 2 === 0 ? -50 : 50;
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 85%', toggleActions: 'play none none none' },
        opacity: 0, x: fromX, duration: 0.7, ease: 'power2.out',
      });
    });

    /* Risk cards — alternating */
    gsap.utils.toArray('.risk-card').forEach(function (el, i) {
      var fromX = i % 2 === 0 ? -30 : 30;
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%', toggleActions: 'play none none none' },
        opacity: 0, x: fromX, duration: 0.5, delay: i * 0.06, ease: 'power2.out',
      });
    });

    /* Resources — alternating */
    gsap.utils.toArray('.resource-item').forEach(function (el, i) {
      var fromX = i % 2 === 0 ? -25 : 25;
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 90%', toggleActions: 'play none none none' },
        opacity: 0, x: fromX, duration: 0.4, delay: i * 0.05, ease: 'power2.out',
      });
    });

    /* Section titles */
    gsap.utils.toArray('.section__title').forEach(function (el) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%', toggleActions: 'play none none none' },
        opacity: 0, y: 25, duration: 0.6, ease: 'power3.out',
      });
    });
  }

  /* ---------- Init ---------- */
  renderChecklist();
  renderTimeline();
  renderCodeDiffs();
  renderRiskGrid();
  renderResources();
  initAnimations();

})();
