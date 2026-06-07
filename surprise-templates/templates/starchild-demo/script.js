/* starchild-demo — E14 — Starchild Capabilities Showcase */
(function(){
  'use strict';

  /* ── Theme Toggle ── */
  const toggle=document.getElementById('themeToggle');
  const root=document.documentElement;
  function setTheme(t){
    root.setAttribute('data-theme',t);
    toggle.textContent=t==='dark'?'🌙':'☀️';
    localStorage.setItem('starchild-demo-theme',t);
  }
  toggle.addEventListener('click',()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark'));
  const saved=localStorage.getItem('starchild-demo-theme');
  if(saved)setTheme(saved);
  else if(matchMedia('(prefers-color-scheme:dark)').matches)setTheme('dark');

  /* ── Interactive Feature Toggle ── */
  document.querySelectorAll('.demo-feature').forEach(card=>{
    card.addEventListener('click',()=>{
      const wasOpen=card.classList.contains('is-open');
      /* Close all first */
      document.querySelectorAll('.demo-feature.is-open').forEach(c=>c.classList.remove('is-open'));
      if(!wasOpen)card.classList.add('is-open');
    });
  });

  /* ── Explore Button — scroll to sections ── */
  const btnExplore=document.getElementById('btnExplore');
  if(btnExplore){
    btnExplore.addEventListener('click',()=>{
      const target=document.getElementById('sectionAgent');
      if(target)target.scrollIntoView({behavior:'smooth',block:'start'});
    });
  }

  /* ── Demo Button — toggle all features open ── */
  const btnDemo=document.getElementById('btnDemo');
  if(btnDemo){
    btnDemo.addEventListener('click',()=>{
      const features=document.querySelectorAll('.demo-feature');
      const allOpen=[...features].every(f=>f.classList.contains('is-open'));
      features.forEach(f=>{
        if(allOpen)f.classList.remove('is-open');
        else f.classList.add('is-open');
      });
    });
  }

  /* ── GSAP Entrance — D12 Alternating Direction ── */
  if(!matchMedia('(prefers-reduced-motion:reduce)').matches){
    gsap.registerPlugin(ScrollTrigger);

    /* Hero content fade in */
    gsap.from('.hero__content',{
      y:40,opacity:0,duration:0.8,ease:'power2.out',delay:0.15
    });

    /* Section headers — alternating direction */
    gsap.utils.toArray('.demo-section__header').forEach((header,i)=>{
      const xDir=i%2===0?-30:30;
      gsap.to(header,{
        x:0,opacity:1,duration:0.6,ease:'power2.out',
        scrollTrigger:{trigger:header,start:'top 85%',once:true}
      });
    });

    /* Feature cards — alternating stagger */
    gsap.utils.toArray('.demo-section').forEach((section,sIdx)=>{
      const cards=section.querySelectorAll('.demo-feature,.tool-card,.build-card,.community-card');
      if(!cards.length)return;
      const xDir=sIdx%2===0?-30:30;
      gsap.to(cards,{
        x:0,opacity:1,duration:0.5,stagger:0.1,ease:'power2.out',
        scrollTrigger:{trigger:section,start:'top 80%',once:true}
      });
    });

  }else{
    /* No animation — show immediately */
    document.querySelectorAll('.demo-section__header,.demo-feature,.tool-card,.build-card,.community-card').forEach(el=>{
      el.style.transform='none';el.style.opacity='1';
    });
  }

})();
