/* creator-analytics — E13 — Creator Analytics Dashboard */
(function(){
  'use strict';

  /* ── Theme Toggle ── */
  const toggle=document.getElementById('themeToggle');
  const root=document.documentElement;
  function setTheme(t){
    root.setAttribute('data-theme',t);
    toggle.textContent=t==='dark'?'🌙':'☀️';
    localStorage.setItem('creator-analytics-theme',t);
    rebuildCharts();
  }
  toggle.addEventListener('click',()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark'));
  const saved=localStorage.getItem('creator-analytics-theme');
  if(saved)setTheme(saved);
  else if(matchMedia('(prefers-color-scheme:dark)').matches)setTheme('dark');

  /* ── Mock Creator Data ── */
  const creatorData={
    score:87,
    scoreTier:'Rising Star',
    totalFollowers:24680,
    totalEngagement:156420,
    bestContentType:'Thread / Tutorial',
    bestPostTime:'10:00 AM UTC',
    avgEngagementRate:'4.8%',
    topPostReach:'128K',
    regions:{
      'North America':35,
      'Europe':28,
      'Asia':22,
      'South America':9,
      'Other':6
    },
    interests:{
      'Web3 / Crypto':32,
      'Programming':26,
      'AI / ML':18,
      'Design':14,
      'Finance':10
    },
    growth:Array.from({length:30},(_,i)=>{
      const base=22000;
      const trend=i*90;
      const noise=Math.floor(Math.random()*300-150);
      return base+trend+noise;
    }),
    suggestions:[
      'Post more tutorial threads — they get 3.2× higher engagement than single tweets.',
      'Increase GitHub activity on weekends — your weekend commits get 40% more stars.',
      'Engage with replies between 9–11 AM UTC for maximum visibility.',
      'Cross-post key insights to GitHub Discussions to capture developer audience.',
      'Create a weekly "What I Learned" series — recurring formats build loyal followers.'
    ],
    twitter:{followers:18200,engagement:'5.1%',influence:82},
    github:{stars:6480,contributions:1247,influence:74}
  };

  /* ── Populate Hero ── */
  const userName=document.querySelector('.hero__title')?.textContent||'Creator';
  const letter=userName.replace(/[{}]/g,'').trim().charAt(0).toUpperCase();
  document.getElementById('avatarLetter').textContent=letter||'C';
  document.getElementById('creatorScore').textContent=creatorData.score+'/100';
  document.getElementById('scoreBadge').textContent=creatorData.scoreTier;
  document.getElementById('totalFollowers').textContent=fmt(creatorData.totalFollowers);
  document.getElementById('totalEngagement').textContent=fmt(creatorData.totalEngagement);

  /* ── Populate Performance ── */
  document.getElementById('bestType').textContent=creatorData.bestContentType;
  document.getElementById('bestTime').textContent=creatorData.bestPostTime;
  document.getElementById('avgEngagement').textContent=creatorData.avgEngagementRate;
  document.getElementById('topReach').textContent=creatorData.topPostReach;

  /* ── Populate Suggestions ── */
  const sugList=document.getElementById('suggestionList');
  creatorData.suggestions.forEach(s=>{
    const li=document.createElement('li');
    li.textContent=s;
    sugList.appendChild(li);
  });

  /* ── Populate Platform Comparison ── */
  document.getElementById('twFollowers').textContent=fmt(creatorData.twitter.followers);
  document.getElementById('twEngagement').textContent=creatorData.twitter.engagement;
  document.getElementById('twInfluence').textContent=creatorData.twitter.influence+'/100';
  document.getElementById('ghStars').textContent=fmt(creatorData.github.stars);
  document.getElementById('ghContribs').textContent=fmt(creatorData.github.contributions);
  document.getElementById('ghInfluence').textContent=creatorData.github.influence+'/100';

  /* ── Charts ── */
  let regionChart,interestChart,growthChart;

  function getChartColors(){
    const isDark=root.getAttribute('data-theme')==='dark';
    return{
      text:isDark?'#f8e8ed':'#2c1018',
      grid:isDark?'rgba(248,232,237,.08)':'rgba(44,16,24,.06)',
      accent:isDark?'#fb7199':'#e11d48',
      accentBg:isDark?'rgba(251,113,153,.15)':'rgba(225,29,72,.10)',
      regionColors:['#e11d48','#f472b6','#fb923c','#a78bfa','#6ee7b7'],
      interestColors:['#e11d48','#ec4899','#f97316','#8b5cf6','#10b981']
    };
  }

  function buildCharts(){
    const c=getChartColors();

    /* Region Doughnut */
    const regionCtx=document.getElementById('regionChart').getContext('2d');
    regionChart=new Chart(regionCtx,{
      type:'doughnut',
      data:{
        labels:Object.keys(creatorData.regions),
        datasets:[{
          data:Object.values(creatorData.regions),
          backgroundColor:c.regionColors,
          borderWidth:2,
          borderColor:root.getAttribute('data-theme')==='dark'?'#331926':'#ffffff'
        }]
      },
      options:{
        responsive:true,maintainAspectRatio:true,
        plugins:{
          legend:{position:'bottom',labels:{color:c.text,font:{family:'Nunito',size:11},padding:12}}
        },
        cutout:'55%'
      }
    });

    /* Interest Doughnut */
    const interestCtx=document.getElementById('interestChart').getContext('2d');
    interestChart=new Chart(interestCtx,{
      type:'doughnut',
      data:{
        labels:Object.keys(creatorData.interests),
        datasets:[{
          data:Object.values(creatorData.interests),
          backgroundColor:c.interestColors,
          borderWidth:2,
          borderColor:root.getAttribute('data-theme')==='dark'?'#331926':'#ffffff'
        }]
      },
      options:{
        responsive:true,maintainAspectRatio:true,
        plugins:{
          legend:{position:'bottom',labels:{color:c.text,font:{family:'Nunito',size:11},padding:12}}
        },
        cutout:'55%'
      }
    });

    /* Growth Line */
    const growthCtx=document.getElementById('growthChart').getContext('2d');
    const labels=Array.from({length:30},(_,i)=>'Day '+(i+1));
    growthChart=new Chart(growthCtx,{
      type:'line',
      data:{
        labels,
        datasets:[{
          label:'Followers',
          data:creatorData.growth,
          borderColor:c.accent,
          backgroundColor:c.accentBg,
          fill:true,
          tension:0.35,
          pointRadius:0,
          pointHoverRadius:5,
          borderWidth:2
        }]
      },
      options:{
        responsive:true,maintainAspectRatio:false,
        scales:{
          x:{ticks:{color:c.text,font:{family:'Nunito',size:10},maxTicksLimit:10},grid:{color:c.grid}},
          y:{ticks:{color:c.text,font:{family:'Source Code Pro',size:10},callback:v=>fmt(v)},grid:{color:c.grid}}
        },
        plugins:{
          legend:{display:false},
          tooltip:{
            backgroundColor:root.getAttribute('data-theme')==='dark'?'#331926':'#ffffff',
            titleColor:c.text,bodyColor:c.text,
            borderColor:c.accent,borderWidth:1,
            bodyFont:{family:'Source Code Pro'},
            callbacks:{label:ctx=>fmt(ctx.parsed.y)+' followers'}
          }
        }
      }
    });
  }

  function rebuildCharts(){
    if(regionChart)regionChart.destroy();
    if(interestChart)interestChart.destroy();
    if(growthChart)growthChart.destroy();
    buildCharts();
  }

  buildCharts();

  /* ── GSAP Entrance — D9 scale(0.95) ── */
  if(!matchMedia('(prefers-reduced-motion:reduce)').matches){
    gsap.registerPlugin(ScrollTrigger);

    /* Hero stat cards */
    gsap.to('.hero__stat-card',{
      scale:1,opacity:1,duration:0.6,stagger:0.12,ease:'power2.out',delay:0.2
    });

    /* Dashboard cards */
    gsap.utils.toArray('.analytics-card').forEach(card=>{
      gsap.to(card,{
        scale:1,opacity:1,duration:0.5,ease:'power2.out',
        scrollTrigger:{trigger:card,start:'top 88%',once:true}
      });
    });
  }else{
    /* No animation — show immediately */
    document.querySelectorAll('.hero__stat-card,.analytics-card').forEach(el=>{
      el.style.transform='none';el.style.opacity='1';
    });
  }

  /* ── Helpers ── */
  function fmt(n){
    if(n>=1e6)return(n/1e6).toFixed(1)+'M';
    if(n>=1e3)return(n/1e3).toFixed(1)+'K';
    return String(n);
  }

})();
