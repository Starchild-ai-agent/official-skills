/* ============================================================
   Developer Tools Radar — script.js
   Mock data · GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var rm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var CATS = ['All','IDE','CLI','Framework','Library'];
  var TOOLS = [
    {name:'Cursor IDE',version:'v0.45',category:'IDE',desc:'AI-first code editor with built-in chat and codebase understanding.',stars:'45.2K',wide:true},
    {name:'Bun',version:'v1.2',category:'CLI',desc:'All-in-one JS runtime, bundler, transpiler, and package manager.',stars:'72.8K',wide:false},
    {name:'Astro',version:'v5.0',category:'Framework',desc:'Content-focused web framework with zero JS by default.',stars:'44.1K',wide:false},
    {name:'Biome',version:'v2.0',category:'CLI',desc:'Fast formatter and linter for JS/TS. Written in Rust.',stars:'13.5K',wide:false},
    {name:'SvelteKit',version:'v2.5',category:'Framework',desc:'Full-stack framework for Svelte with SSR and routing.',stars:'18.2K',wide:true},
    {name:'Zed',version:'v0.150',category:'IDE',desc:'High-performance multiplayer code editor built in Rust.',stars:'38.6K',wide:false},
    {name:'Hono',version:'v4.5',category:'Framework',desc:'Ultrafast web framework for the edge.',stars:'17.8K',wide:false},
    {name:'Turborepo',version:'v2.1',category:'CLI',desc:'High-performance build system for JS monorepos.',stars:'25.4K',wide:false},
    {name:'Drizzle ORM',version:'v0.33',category:'Library',desc:'TypeScript ORM with SQL-like syntax. Zero dependencies.',stars:'22.1K',wide:false},
    {name:'tRPC',version:'v11.0',category:'Library',desc:'End-to-end typesafe APIs. No code generation needed.',stars:'33.7K',wide:true},
    {name:'Oxlint',version:'v0.10',category:'CLI',desc:'Blazing fast JS linter written in Rust. 50-100x faster.',stars:'9.8K',wide:false},
    {name:'Tauri',version:'v2.0',category:'Framework',desc:'Build desktop apps with web tech. Smaller than Electron.',stars:'79.5K',wide:false}
  ];
  var TL = [
    {date:'Today',name:'Bun',version:'v1.2.0',change:'Native Windows support, 40% faster npm install'},
    {date:'Yesterday',name:'Astro',version:'v5.0.0',change:'Server Islands, Content Layer API'},
    {date:'2 days ago',name:'Biome',version:'v2.0.0',change:'CSS formatting, GraphQL support'},
    {date:'3 days ago',name:'Drizzle',version:'v0.33.0',change:'SQLite vector extension'},
    {date:'4 days ago',name:'Hono',version:'v4.5.0',change:'RPC mode improvements'},
    {date:'5 days ago',name:'tRPC',version:'v11.0.0',change:'Server-sent events, FormData support'},
    {date:'1 week ago',name:'Tauri',version:'v2.0.0',change:'Mobile support (iOS/Android)'},
    {date:'1 week ago',name:'Turborepo',version:'v2.1.0',change:'Rust-based task runner'}
  ];
  var TR = [
    {name:'Cursor IDE',category:'IDE',stars:'+2.4K'},
    {name:'Bun',category:'CLI',stars:'+1.8K'},
    {name:'Tauri',category:'Framework',stars:'+1.5K'},
    {name:'Astro',category:'Framework',stars:'+1.2K'},
    {name:'Biome',category:'CLI',stars:'+980'},
    {name:'Drizzle ORM',category:'Library',stars:'+870'},
    {name:'Hono',category:'Framework',stars:'+750'},
    {name:'tRPC',category:'Library',stars:'+620'}
  ];
  var af = 'All';
  var $ = function(s){return document.querySelector(s);};
  var saved = localStorage.getItem('devtools-radar-theme');
  if(saved==='light') document.documentElement.setAttribute('data-theme','light');
  $('#theme-toggle').addEventListener('click',function(){
    var l=document.documentElement.getAttribute('data-theme')==='light';
    document.documentElement.setAttribute('data-theme',l?'':'light');
    localStorage.setItem('devtools-radar-theme',l?'dark':'light');
  });
  function renderFilters(){
    var el=$('#filter-tabs');
    el.innerHTML=CATS.map(function(c){return '<button class="filter-tab '+(c===af?'active':'')+'" data-cat="'+c+'">'+c+'</button>';}).join('');
    el.querySelectorAll('.filter-tab').forEach(function(t){t.addEventListener('click',function(){af=t.dataset.cat;renderFilters();renderBento();});});
  }
  function renderBento(){
    var items=af==='All'?TOOLS:TOOLS.filter(function(t){return t.category===af;});
    $('#bento-grid').innerHTML=items.map(function(t){
      return '<div class="bento-card '+(t.wide?'bento-card--wide':'')+'"><div class="bento-card__category">'+t.category+'</div><div class="bento-card__name">'+t.name+'</div><div class="bento-card__version">'+t.version+'</div><div class="bento-card__desc">'+t.desc+'</div><div class="bento-card__stars">'+t.stars+' stars</div></div>';
    }).join('');
    if(!rm) gsap.from('.bento-card',{y:40,opacity:0,duration:0.5,stagger:0.05,ease:'power3.out',clearProps:'transform,opacity'});
  }
  function renderTimeline(){
    $('#timeline-list').innerHTML=TL.map(function(t){
      return '<div class="timeline-item"><div class="timeline-item__date">'+t.date+'</div><div class="timeline-item__name">'+t.name+' <span class="timeline-item__version">'+t.version+'</span></div><div class="timeline-item__change">'+t.change+'</div></div>';
    }).join('');
  }
  function renderTrending(){
    $('#trending-list').innerHTML=TR.map(function(t,i){
      return '<div class="trending-item"><span class="trending-item__rank">#'+(i+1)+'</span><span class="trending-item__name">'+t.name+'</span><span class="trending-item__cat">'+t.category+'</span><span class="trending-item__stars">'+t.stars+'</span></div>';
    }).join('');
  }
  function initAnimations(){
    if(rm) return;
    gsap.timeline({defaults:{ease:'power3.out'}})
      .from('.hero__label',{y:40,opacity:0,duration:0.5})
      .from('.hero__title',{y:40,opacity:0,duration:0.7},'-=0.3')
      .from('.hero__subtitle',{y:40,opacity:0,duration:0.5},'-=0.3')
      .from('.hero__stat-card',{y:40,opacity:0,duration:0.4,stagger:0.1},'-=0.2');
    gsap.from('.timeline-item',{scrollTrigger:{trigger:'#timeline',start:'top 80%',once:true},y:40,opacity:0,duration:0.4,stagger:0.05,ease:'power3.out'});
    gsap.from('.trending-item',{scrollTrigger:{trigger:'#trending',start:'top 80%',once:true},y:40,opacity:0,duration:0.3,stagger:0.04,ease:'power3.out'});
  }
  function init(){renderFilters();renderBento();renderTimeline();renderTrending();initAnimations();}
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);
  else init();
})();
