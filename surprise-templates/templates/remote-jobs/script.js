/* ============================================================
   Remote Job Board — script.js
   Mock data · GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var rm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var CATS = ['All','Engineering','Design','Product','Data','DevOps'];
  var JOBS = [
    {title:'Senior Frontend Engineer',company:'Vercel',salary:'$180-220K',skills:['React','TypeScript','Next.js'],remote:'Fully Remote',tz:'Any',category:'Engineering',match:'high'},
    {title:'Staff Backend Engineer',company:'Stripe',salary:'$200-260K',skills:['Go','PostgreSQL','gRPC'],remote:'Fully Remote',tz:'US/EU',category:'Engineering',match:'medium'},
    {title:'Product Designer',company:'Figma',salary:'$160-200K',skills:['Figma','Design Systems','Prototyping'],remote:'Fully Remote',tz:'US',category:'Design',match:'low'},
    {title:'Senior Data Engineer',company:'Databricks',salary:'$170-220K',skills:['Python','Spark','SQL'],remote:'Fully Remote',tz:'Any',category:'Data',match:'high'},
    {title:'DevOps Engineer',company:'GitLab',salary:'$150-190K',skills:['Kubernetes','Terraform','CI/CD'],remote:'Fully Remote',tz:'Any',category:'DevOps',match:'medium'},
    {title:'Product Manager',company:'Notion',salary:'$160-210K',skills:['Strategy','Analytics','Roadmapping'],remote:'Fully Remote',tz:'US/EU',category:'Product',match:'low'},
    {title:'Full Stack Engineer',company:'Supabase',salary:'$150-200K',skills:['TypeScript','PostgreSQL','React'],remote:'Fully Remote',tz:'Any',category:'Engineering',match:'high'},
    {title:'UX Researcher',company:'Linear',salary:'$140-180K',skills:['User Research','Interviews','Analytics'],remote:'Fully Remote',tz:'US/EU',category:'Design',match:'low'},
    {title:'ML Engineer',company:'Hugging Face',salary:'$180-240K',skills:['Python','PyTorch','Transformers'],remote:'Fully Remote',tz:'Any',category:'Data',match:'medium'},
    {title:'Site Reliability Engineer',company:'Cloudflare',salary:'$160-210K',skills:['Linux','Go','Observability'],remote:'Fully Remote',tz:'US/EU/APAC',category:'DevOps',match:'medium'},
    {title:'React Native Developer',company:'Expo',salary:'$140-180K',skills:['React Native','TypeScript','iOS'],remote:'Fully Remote',tz:'Any',category:'Engineering',match:'high'},
    {title:'Senior Product Designer',company:'Loom',salary:'$170-210K',skills:['Figma','Motion Design','Systems'],remote:'Fully Remote',tz:'US',category:'Design',match:'low'},
    {title:'Data Analyst',company:'dbt Labs',salary:'$120-160K',skills:['SQL','dbt','Python'],remote:'Fully Remote',tz:'US/EU',category:'Data',match:'medium'},
    {title:'Platform Engineer',company:'Fly.io',salary:'$160-200K',skills:['Rust','Elixir','Distributed Systems'],remote:'Fully Remote',tz:'Any',category:'Engineering',match:'medium'},
    {title:'Head of Product',company:'Cal.com',salary:'$180-230K',skills:['Product Strategy','Open Source','Growth'],remote:'Fully Remote',tz:'EU/US',category:'Product',match:'low'}
  ];
  var af = 'All';
  var sortBy = 'match';
  var $ = function(s){return document.querySelector(s);};
  var saved = localStorage.getItem('remote-jobs-theme');
  if(saved==='dark') document.documentElement.setAttribute('data-theme','dark');
  $('#theme-toggle').addEventListener('click',function(){
    var d=document.documentElement.getAttribute('data-theme')==='dark';
    document.documentElement.setAttribute('data-theme',d?'light':'dark');
    localStorage.setItem('remote-jobs-theme',d?'light':'dark');
  });
  function renderKPIs(){
    var el=$('#kpi-bar');
    var kpis=[
      {label:'Open Positions',value:JOBS.length},
      {label:'Fully Remote',value:JOBS.length},
      {label:'Avg Salary',value:'$175K'},
      {label:'High Match',value:JOBS.filter(function(j){return j.match==='high';}).length}
    ];
    el.innerHTML=kpis.map(function(k){return '<div class="kpi-item"><div class="kpi-item__value">'+k.value+'</div><div class="kpi-item__label">'+k.label+'</div></div>';}).join('');
  }
  function renderFilters(){
    var el=$('#filter-tabs');
    el.innerHTML=CATS.map(function(c){return '<button class="filter-tab '+(c===af?'active':'')+'" data-cat="'+c+'">'+c+'</button>';}).join('');
    el.querySelectorAll('.filter-tab').forEach(function(t){t.addEventListener('click',function(){af=t.dataset.cat;renderFilters();renderTable();});});
  }
  function renderTable(){
    var items=af==='All'?JOBS.slice():JOBS.filter(function(j){return j.category===af;});
    if(sortBy==='salary'){
      items.sort(function(a,b){var av=parseInt(a.salary.replace(/[^0-9]/g,''));var bv=parseInt(b.salary.replace(/[^0-9]/g,''));return bv-av;});
    } else if(sortBy==='match'){
      var mo={high:0,medium:1,low:2};
      items.sort(function(a,b){return mo[a.match]-mo[b.match];});
    }
    var tbl=$('#job-table');
    var h='<thead><tr><th>Position</th><th>Company</th><th>Salary</th><th>Skills</th><th>Remote</th><th>Timezone</th><th>Match</th></tr></thead>';
    var b='<tbody>'+items.map(function(j){
      var sk=j.skills.map(function(s){return '<span class="skill-tag">'+s+'</span>';}).join('');
      return '<tr><td class="job-title">'+j.title+'</td><td class="company">'+j.company+'</td><td class="salary">'+j.salary+'</td><td>'+sk+'</td><td class="remote-type">'+j.remote+'</td><td class="remote-type">'+j.tz+'</td><td><span class="match-badge match-badge--'+j.match+'">'+j.match.toUpperCase()+'</span></td></tr>';
    }).join('')+'</tbody>';
    tbl.innerHTML=h+b;
    if(!rm) gsap.from('.job-table tbody tr',{x:30,opacity:0,duration:0.4,stagger:0.03,ease:'power3.out',clearProps:'transform,opacity'});
  }
  $('#sort-select').addEventListener('change',function(e){sortBy=e.target.value;renderTable();});
  function initAnimations(){
    if(rm) return;
    gsap.timeline({defaults:{ease:'power3.out'}})
      .from('.hero__label',{x:30,opacity:0,duration:0.5})
      .from('.hero__title',{x:30,opacity:0,duration:0.7},'-=0.3')
      .from('.hero__subtitle',{x:30,opacity:0,duration:0.5},'-=0.3')
      .from('.hero__kpi-bar',{x:30,opacity:0,duration:0.5},'-=0.2');
  }
  function init(){renderKPIs();renderFilters();renderTable();initAnimations();}
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);
  else init();
})();
