/* enterprise-intel — E9 — Enterprise Intelligence Dashboard */
(function(){
  'use strict';

  /* ── Theme Toggle ── */
  const toggle=document.getElementById('themeToggle');
  const root=document.documentElement;
  function setTheme(t){
    root.setAttribute('data-theme',t);
    toggle.textContent=t==='dark'?'🌙':'☀️';
    localStorage.setItem('ent-intel-theme',t);
  }
  toggle.addEventListener('click',()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark'));
  const saved=localStorage.getItem('ent-intel-theme');
  if(saved)setTheme(saved);
  else if(matchMedia('(prefers-color-scheme:dark)').matches)setTheme('dark');

  /* ── Sidebar Navigation ── */
  const navItems=document.querySelectorAll('#sidebarNav .sidebar__nav-item');
  navItems.forEach(item=>{
    item.addEventListener('click',()=>{
      navItems.forEach(n=>n.classList.remove('active'));
      item.classList.add('active');
      const sec=document.getElementById('section'+item.dataset.section.charAt(0).toUpperCase()+item.dataset.section.slice(1));
      if(sec)sec.scrollIntoView({behavior:'smooth',block:'start'});
    });
  });

  /* ── Mock Data ── */
  const overviewData=[
    {label:'Founded',value:'2015'},
    {label:'Headquarters',value:'San Francisco, CA'},
    {label:'CEO',value:'Sarah Chen'},
    {label:'Industry',value:'Enterprise SaaS'},
    {label:'Revenue (TTM)',value:'$840M'},
    {label:'Employees',value:'12,400'},
    {label:'Total Funding',value:'$2.1B'},
    {label:'Valuation',value:'$18B'},
    {label:'Latest Round',value:'Series F'},
    {label:'Key Investors',value:'Sequoia, a16z'},
    {label:'Market Cap',value:'$22.4B'},
    {label:'YoY Growth',value:'+34%'}
  ];

  const competitors=[
    {name:'{{COMPANY_NAME}}',industry:'Enterprise SaaS',employees:'12,400',revenue:'$840M',growth:'+34%',share:'18.2%',isTarget:true},
    {name:'DataForge Inc.',industry:'Enterprise SaaS',employees:'8,200',revenue:'$620M',growth:'+28%',share:'14.5%'},
    {name:'CloudSync Pro',industry:'Cloud Platform',employees:'15,800',revenue:'$1.1B',growth:'+22%',share:'21.3%'},
    {name:'NexaFlow',industry:'Workflow Automation',employees:'4,600',revenue:'$310M',growth:'+45%',share:'8.7%'},
    {name:'Stratify AI',industry:'AI Analytics',employees:'3,200',revenue:'$180M',growth:'+62%',share:'5.1%'},
    {name:'OmniStack',industry:'Enterprise SaaS',employees:'9,800',revenue:'$720M',growth:'+19%',share:'16.8%'}
  ];

  const newsItems=[
    {date:'2025-12-15',title:'{{COMPANY_NAME}} Announces Series F at $18B Valuation',text:'The company raised $400M in its latest funding round led by Sequoia Capital, bringing total funding to $2.1B.'},
    {date:'2025-11-28',title:'New AI-Powered Analytics Suite Launched',text:'The company unveiled its next-generation analytics platform featuring real-time predictive insights and natural language querying.'},
    {date:'2025-10-10',title:'Strategic Partnership with CloudSync Pro',text:'A joint integration initiative aims to provide seamless data migration and hybrid cloud deployment options.'},
    {date:'2025-09-05',title:'Expansion into APAC Markets',text:'New offices in Singapore and Tokyo signal aggressive growth plans in the Asia-Pacific region.'},
    {date:'2025-08-20',title:'Industry Report: Enterprise SaaS Market to Reach $500B by 2028',text:'Analysts project continued strong growth driven by AI adoption and digital transformation initiatives.'},
    {date:'2025-07-12',title:'{{COMPANY_NAME}} Wins Enterprise Innovation Award',text:'Recognized for breakthrough contributions to enterprise workflow automation at the Global Tech Summit.'}
  ];

  const watchlistCompanies=[
    {name:'DataForge Inc.'},
    {name:'CloudSync Pro'},
    {name:'NexaFlow'},
    {name:'Stratify AI'},
    {name:'OmniStack'}
  ];

  /* ── Render Overview ── */
  const overviewGrid=document.getElementById('overviewGrid');
  overviewData.forEach(item=>{
    const el=document.createElement('div');
    el.className='overview-item';
    el.innerHTML=`<div class="overview-item__label">${item.label}</div><div class="overview-item__value">${item.value}</div>`;
    overviewGrid.appendChild(el);
  });

  /* ── Render Competitors Table ── */
  const tbody=document.getElementById('compTableBody');
  competitors.forEach(c=>{
    const tr=document.createElement('tr');
    const growthClass=c.growth.startsWith('+')?'positive':'negative';
    tr.innerHTML=`
      <td style="${c.isTarget?'font-weight:700':''}">${c.name}</td>
      <td>${c.industry}</td>
      <td>${c.employees}</td>
      <td>${c.revenue}</td>
      <td class="${growthClass}">${c.growth}</td>
      <td>${c.share}</td>
    `;
    tbody.appendChild(tr);
  });

  /* ── Render News Timeline ── */
  const timeline=document.getElementById('newsTimeline');
  newsItems.forEach(n=>{
    const item=document.createElement('div');
    item.className='timeline__item intel-card';
    item.style.cssText='border:none;border-radius:0;box-shadow:none;padding:0;padding-left:var(--space-lg);border-left:none;';
    item.innerHTML=`
      <div class="timeline__dot"></div>
      <div class="timeline__date">${n.date}</div>
      <div class="timeline__title">${n.title}</div>
      <div class="timeline__text">${n.text}</div>
    `;
    timeline.appendChild(item);
  });

  /* ── Render Watchlist ── */
  const watchlistEl=document.getElementById('watchlist');
  watchlistCompanies.forEach(c=>{
    const li=document.createElement('li');
    li.className='sidebar__nav-item';
    li.textContent=c.name;
    watchlistEl.appendChild(li);
  });

  /* ── Social Mentions Chart (Chart.js) ── */
  const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const isDark=()=>root.getAttribute('data-theme')==='dark';
  const gridColor=()=>isDark()?'rgba(255,255,255,.06)':'rgba(0,0,0,.06)';
  const textColor=()=>isDark()?'#b0aa9e':'#6e6a60';

  let mentionsChart;
  function buildMentionsChart(){
    const ctx=document.getElementById('mentionsChart').getContext('2d');
    if(mentionsChart)mentionsChart.destroy();
    mentionsChart=new Chart(ctx,{
      type:'line',
      data:{
        labels:months,
        datasets:[
          {
            label:'Twitter Mentions',
            data:[320,410,380,520,610,580,720,890,950,1100,1250,1380],
            borderColor:isDark()?'#38bdf8':'#0369a1',
            backgroundColor:isDark()?'rgba(56,189,248,.1)':'rgba(3,105,161,.08)',
            fill:true,tension:0.4,pointRadius:3,pointHoverRadius:6
          },
          {
            label:'News Articles',
            data:[45,52,38,61,73,68,82,95,110,125,140,158],
            borderColor:isDark()?'#fbbf24':'#d97706',
            backgroundColor:'transparent',
            borderDash:[5,5],tension:0.4,pointRadius:3,pointHoverRadius:6
          }
        ]
      },
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{legend:{labels:{color:textColor(),font:{family:'Source Sans 3',size:12}}}},
        scales:{
          x:{grid:{color:gridColor()},ticks:{color:textColor(),font:{family:'IBM Plex Mono',size:11}}},
          y:{grid:{color:gridColor()},ticks:{color:textColor(),font:{family:'IBM Plex Mono',size:11}}}
        }
      }
    });
  }
  buildMentionsChart();

  /* Rebuild chart on theme change */
  const origSetTheme=setTheme;
  setTheme=function(t){
    origSetTheme(t);
    setTimeout(buildMentionsChart,50);
  };
  toggle.removeEventListener('click',()=>{});
  toggle.addEventListener('click',()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark'));

  /* ── GSAP Animations ── */
  gsap.registerPlugin(ScrollTrigger);
  const prefersReduced=matchMedia('(prefers-reduced-motion:reduce)').matches;

  if(!prefersReduced){
    /* Hero */
    gsap.from('.hero__left',{opacity:0,x:-40,duration:0.7,ease:'power2.out'});
    gsap.from('.hero__right .hero__metric',{opacity:0,y:20,duration:0.5,stagger:0.1,delay:0.3,ease:'power2.out'});

    /* Overview items */
    gsap.utils.toArray('.overview-item').forEach((el,i)=>{
      gsap.from(el,{opacity:0,y:20,duration:0.4,delay:i*0.05,ease:'power2.out',
        scrollTrigger:{trigger:el,start:'top 92%'}
      });
    });

    /* Intel cards / timeline items */
    gsap.utils.toArray('.intel-card, .timeline__item').forEach(el=>{
      gsap.fromTo(el,
        {opacity:0,x:-50},
        {opacity:1,x:0,duration:0.5,ease:'power2.out',
          scrollTrigger:{trigger:el,start:'top 90%',toggleActions:'play none none none'}
        }
      );
    });

    /* Table rows */
    gsap.utils.toArray('.comp-table tbody tr').forEach((tr,i)=>{
      gsap.from(tr,{opacity:0,x:-30,duration:0.4,delay:i*0.06,ease:'power2.out',
        scrollTrigger:{trigger:tr,start:'top 95%'}
      });
    });
  }
})();
