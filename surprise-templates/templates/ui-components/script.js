/* ui-components — E8 — UI Components Gallery */
(function(){
  'use strict';

  /* ── Theme Toggle ── */
  const toggle=document.getElementById('themeToggle');
  const root=document.documentElement;
  function setTheme(t){
    root.setAttribute('data-theme',t);
    toggle.textContent=t==='dark'?'🌙':'☀️';
    localStorage.setItem('ui-comp-theme',t);
  }
  toggle.addEventListener('click',()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark'));
  const saved=localStorage.getItem('ui-comp-theme');
  if(saved)setTheme(saved);
  else if(matchMedia('(prefers-color-scheme:dark)').matches)setTheme('dark');

  /* ── Component Data ── */
  const components=[
    {
      name:'Primary Button',category:'form',
      preview:'<button class="preview-btn">Click Me</button>',
      code:'<button class="btn btn-primary">\n  Click Me\n</button>'
    },
    {
      name:'Outline Button',category:'form',
      preview:'<button class="preview-btn preview-btn--outline">Outline</button>',
      code:'<button class="btn btn-outline">\n  Outline\n</button>'
    },
    {
      name:'Text Input',category:'form',
      preview:'<input class="preview-input" placeholder="Enter text…" readonly>',
      code:'<input\n  type="text"\n  class="input"\n  placeholder="Enter text…"\n/>'
    },
    {
      name:'Badge',category:'feedback',
      preview:'<span class="preview-badge">New</span>',
      code:'<span class="badge badge-accent">\n  New\n</span>'
    },
    {
      name:'Toggle Switch',category:'form',
      preview:'<button class="preview-toggle on" onclick="this.classList.toggle(\'on\')"></button>',
      code:'<label class="toggle">\n  <input type="checkbox" />\n  <span class="toggle__slider" />\n</label>'
    },
    {
      name:'Avatar',category:'data',
      preview:'<div class="preview-avatar">JD</div>',
      code:'<div class="avatar avatar-md">\n  JD\n</div>'
    },
    {
      name:'Info Card',category:'layout',
      preview:'<div class="preview-card-mini"><div class="preview-card-mini__title">Card Title</div><div class="preview-card-mini__text">Brief description of the card content.</div></div>',
      code:'<div class="card">\n  <h3 class="card__title">Card Title</h3>\n  <p class="card__text">Brief description.</p>\n</div>'
    },
    {
      name:'Tab Navigation',category:'navigation',
      preview:'<nav class="preview-nav"><span class="preview-nav__item active">Tab 1</span><span class="preview-nav__item">Tab 2</span><span class="preview-nav__item">Tab 3</span></nav>',
      code:'<nav class="tabs">\n  <button class="tab active">Tab 1</button>\n  <button class="tab">Tab 2</button>\n  <button class="tab">Tab 3</button>\n</nav>'
    },
    {
      name:'Progress Bar',category:'feedback',
      preview:'<div class="preview-progress"><div class="preview-progress__bar"></div></div>',
      code:'<div class="progress">\n  <div class="progress__bar"\n    style="width:68%"\n  />\n</div>'
    },
    {
      name:'Tooltip',category:'feedback',
      preview:'<div class="preview-tooltip-wrap"><div class="preview-tooltip">Helpful tip</div><button class="preview-btn" style="font-size:.8rem;padding:6px 14px">Hover me</button></div>',
      code:'<div class="tooltip-wrap">\n  <span class="tooltip">Helpful tip</span>\n  <button>Hover me</button>\n</div>'
    },
    {
      name:'Breadcrumb',category:'navigation',
      preview:'<nav style="font-size:.82rem;color:var(--text-secondary)">Home <span style="margin:0 6px;opacity:.4">/</span> Components <span style="margin:0 6px;opacity:.4">/</span> <span style="color:var(--accent)">Button</span></nav>',
      code:'<nav class="breadcrumb">\n  <a href="#">Home</a>\n  <span class="sep">/</span>\n  <a href="#">Components</a>\n  <span class="sep">/</span>\n  <span class="current">Button</span>\n</nav>'
    },
    {
      name:'Skeleton Loader',category:'feedback',
      preview:'<div style="display:flex;flex-direction:column;gap:8px;width:100%;max-width:200px"><div style="height:12px;border-radius:4px;background:var(--border-color);animation:pulse 1.5s infinite"></div><div style="height:12px;width:70%;border-radius:4px;background:var(--border-color);animation:pulse 1.5s infinite .2s"></div></div>',
      code:'<div class="skeleton">\n  <div class="skeleton__line" />\n  <div class="skeleton__line w-70" />\n</div>'
    },
    {
      name:'Divider',category:'layout',
      preview:'<div style="width:100%;display:flex;align-items:center;gap:12px"><div style="flex:1;height:1px;background:var(--border-color)"></div><span style="font-size:.75rem;color:var(--text-tertiary)">OR</span><div style="flex:1;height:1px;background:var(--border-color)"></div></div>',
      code:'<div class="divider">\n  <span>OR</span>\n</div>'
    },
    {
      name:'Chip / Tag',category:'data',
      preview:'<div style="display:flex;gap:6px"><span style="padding:3px 10px;border-radius:4px;background:var(--accent-muted);color:var(--accent);font-size:.75rem;font-weight:600">React</span><span style="padding:3px 10px;border-radius:4px;background:var(--accent-muted);color:var(--accent);font-size:.75rem;font-weight:600">Vue</span></div>',
      code:'<div class="chip-group">\n  <span class="chip">React</span>\n  <span class="chip">Vue</span>\n</div>'
    },
    {
      name:'Alert Banner',category:'feedback',
      preview:'<div style="padding:10px 14px;border-radius:6px;background:var(--accent-light);border-left:3px solid var(--accent);font-size:.82rem;color:var(--accent)">⚠ This is an alert message.</div>',
      code:'<div class="alert alert-warning">\n  ⚠ This is an alert message.\n</div>'
    },
    {
      name:'Stat Card',category:'data',
      preview:'<div style="text-align:center"><div style="font-size:1.6rem;font-weight:700;letter-spacing:-0.03em;color:var(--accent)">2,847</div><div style="font-size:.72rem;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.06em">Downloads</div></div>',
      code:'<div class="stat-card">\n  <div class="stat-card__value">2,847</div>\n  <div class="stat-card__label">Downloads</div>\n</div>'
    }
  ];

  /* ── Render ── */
  const gallery=document.getElementById('gallery');
  const noResults=document.getElementById('noResults');
  let copyCounter=parseInt(localStorage.getItem('ui-comp-copies')||'0',10);

  document.getElementById('totalCount').textContent=components.length;
  const cats=[...new Set(components.map(c=>c.category))];
  document.getElementById('categoryCount').textContent=cats.length;
  document.getElementById('copyCount').textContent=copyCounter;

  function escapeHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

  function renderCards(list){
    gallery.innerHTML='';
    if(!list.length){noResults.style.display='block';return}
    noResults.style.display='none';

    list.forEach(comp=>{
      const card=document.createElement('div');
      card.className='component-card';
      card.setAttribute('data-category',comp.category);
      card.innerHTML=`
        <div class="component-card__header">
          <span class="component-card__name">${comp.name}</span>
          <span class="component-card__category">${comp.category}</span>
        </div>
        <div class="component-card__preview">${comp.preview}</div>
        <div class="component-card__code">
          <pre>${escapeHtml(comp.code)}</pre>
          <button class="component-card__copy" data-code="${btoa(unescape(encodeURIComponent(comp.code)))}">Copy</button>
        </div>
      `;
      gallery.appendChild(card);
    });

    animateCards();
  }

  /* ── Copy ── */
  gallery.addEventListener('click',e=>{
    const btn=e.target.closest('.component-card__copy');
    if(!btn)return;
    const code=decodeURIComponent(escape(atob(btn.dataset.code)));
    navigator.clipboard.writeText(code).then(()=>{
      btn.textContent='Copied!';btn.classList.add('copied');
      copyCounter++;
      localStorage.setItem('ui-comp-copies',copyCounter);
      document.getElementById('copyCount').textContent=copyCounter;
      setTimeout(()=>{btn.textContent='Copy';btn.classList.remove('copied')},1500);
    });
  });

  /* ── Filter ── */
  let activeFilter='all';
  let searchQuery='';

  function applyFilters(){
    let filtered=components;
    if(activeFilter!=='all')filtered=filtered.filter(c=>c.category===activeFilter);
    if(searchQuery)filtered=filtered.filter(c=>c.name.toLowerCase().includes(searchQuery)||c.category.toLowerCase().includes(searchQuery));
    renderCards(filtered);
  }

  document.getElementById('filterTags').addEventListener('click',e=>{
    const tag=e.target.closest('.filter-tag');
    if(!tag)return;
    document.querySelectorAll('.filter-tag').forEach(t=>t.classList.remove('active'));
    tag.classList.add('active');
    activeFilter=tag.dataset.filter;
    applyFilters();
  });

  document.getElementById('searchBox').addEventListener('input',e=>{
    searchQuery=e.target.value.trim().toLowerCase();
    applyFilters();
  });

  /* ── GSAP Animations ── */
  gsap.registerPlugin(ScrollTrigger);

  const prefersReduced=matchMedia('(prefers-reduced-motion:reduce)').matches;

  function animateCards(){
    if(prefersReduced)return void document.querySelectorAll('.component-card').forEach(c=>{c.style.opacity=1;c.style.transform='none'});

    gsap.utils.toArray('.component-card').forEach((card,i)=>{
      gsap.fromTo(card,
        {opacity:0,scale:0.9},
        {opacity:1,scale:1,duration:0.5,delay:i*0.06,ease:'power2.out',
          scrollTrigger:{trigger:card,start:'top 92%',toggleActions:'play none none none'}
        }
      );
    });
  }

  /* Hero entrance */
  if(!prefersReduced){
    gsap.from('.hero__title',{opacity:0,y:30,duration:0.7,ease:'power2.out'});
    gsap.from('.hero__subtitle',{opacity:0,y:20,duration:0.6,delay:0.15,ease:'power2.out'});
    gsap.from('.hero__stats',{opacity:0,y:20,duration:0.6,delay:0.25,ease:'power2.out'});
    gsap.from('.hero__preview-bar',{opacity:0,y:15,duration:0.5,delay:0.35,ease:'power2.out'});
    gsap.from('.toolbar',{opacity:0,y:10,duration:0.4,delay:0.45,ease:'power2.out'});
  }

  /* ── Init ── */
  renderCards(components);

  /* Skeleton pulse keyframe */
  const style=document.createElement('style');
  style.textContent='@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}';
  document.head.appendChild(style);
})();
