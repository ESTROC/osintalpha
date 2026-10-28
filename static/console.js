
/* OSINT Alpha release 8.1.0 pilot public research console. Source records are candidates, not verdicts. */
(()=>{'use strict';
const app=document.getElementById('app'), s={user:null,where:'home',mode:'person',cases:[],overview:{},sources:[],projects:[],capabilities:{},server:{},providerIssues:null,case:null,brief:null,dossier:null,dossierSort:'relevance',dossierStatus:'all',dossierClass:'all',claimDetail:null,chronology:null,cursorSources:[],cursorNext:null,runEvolution:null,budget:null,reviewedDraft:null,refinements:null,id:null,tab:'overview',selected:null,messages:[],provider:'local',webSearch:false,braveContext:false,sessionId:null,conversations:[],triage:null,searchHistory:[],researchPlan:null,readiness:null,searchProgress:null,researchRuns:[],candidates:[],intel:null,lastResearch:null,depth:'standard',evidenceFilter:'all',evidenceSearch:'',evidenceSelected:[],changes:null,versions:{},jobs:[],job:null,tasks:[],taskAssignees:[],taskTotal:0,taskHistory:{},members:null,duplicateSources:null,identityQuality:null,excerpts:[],identity:null,draft:null,caseSearch:'',casePage:1,casePageSize:25,caseTotal:0,caseTotalPages:1,caseStatus:'all',caseType:'all',caseSort:'newest',caseOwner:'',caseFrom:'',caseTo:'',webProviders:null,portfolio:null,portfolioLocation:null,captures:{},users:[],busy:false,feed:'earthquakes',geo:[],geoStatus:'idle',geoError:'',cameraSelection:-1,satelliteEnabled:false,satelliteDate:new Date(Date.now()-86400000).toISOString().slice(0,10),smartPlan:null,smartStage:'',smartIssues:[],smartQuestion:'',smartCoverage:null};
const modes={person:{name:'People',icon:'user',tip:'Public profiles and identity candidates',placeholder:'Full name or public handle',sources:['github','openalex','crossref','wikidata','wikipedia']},organization:{name:'Organizations',icon:'building',tip:'Companies and public entity references',placeholder:'Organization or registered business',sources:['gleif','github','wikipedia','wikidata','gdelt']},domain:{name:'Domains',icon:'globe',tip:'Passive DNS and domain metadata',placeholder:'Public domain name',sources:['dns']},ip:{name:'Public IPs',icon:'shield',tip:'Passive network exposure intelligence',placeholder:'Public IP address',sources:['internetdb']}};
const h=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const url=x=>{try{const u=new URL(x);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password?u.href:'#'}catch{return '#'}};
const when=x=>{if(!x)return 'Unknown';const n=Number(x);const d=new Date(typeof x==='number'||(/^\d{10,13}$/.test(String(x)))?(n<1e11?n*1000:n):x);return Number.isFinite(+d)?d.toLocaleString():String(x)};
const link=(href,label)=>'<a class="text-link" target="_blank" rel="noopener noreferrer" href="'+h(url(href))+'">'+h(label)+' ↗</a>';
const tag=x=>'<span class="tag '+({corroborated:'ok',configured:'ok',ok:'ok',candidate:'warn',error:'bad',disputed:'warn',rejected:'bad',not_configured:'warn'}[x]||'')+'">'+h(x)+'</span>';
const icon=k=>{const paths={home:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',search:'<circle cx="10.5" cy="10.5" r="7"/><path d="m16 16 5 5"/>',case:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h6"/>',user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c0-5 16-5 16 0"/>',building:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h2m4 0h2M8 11h2m4 0h2"/>',globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/>',shield:'<path d="m12 2 8 4v6c0 6-4 9-8 10-4-1-8-4-8-10V6Z"/><path d="m9 12 2 2 4-4"/>',world:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c-5 5-5 13 0 18m0-18c5 5 5 13 0 18"/>',sources:'<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',settings:'<circle cx="12" cy="12" r="3"/><path d="M4 12H2m20 0h-2M12 4V2m0 20v-2M6 6 4 4m14 14 2 2"/>',arrow:'<path d="M4 12h16m-7-7 7 7-7 7"/>',back:'<path d="M20 12H4m7 7-7-7 7-7"/>',refresh:'<path d="M20 8a8 8 0 0 0-14-2L4 9m0-6v6h6M4 16a8 8 0 0 0 14 2l2-3m0 6v-6h-6"/>',plus:'<path d="M12 4v16M4 12h16"/>'};return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(paths[k]||paths.case)+'</svg>'};
function toast(text,error=false){const n=document.createElement('div');n.className='toast'+(error?' bad':'');n.textContent=text;document.body.append(n);setTimeout(()=>n.remove(),5100)}
async function api(path,opts={}){const ini={credentials:'same-origin',method:opts.method||'GET',headers:{}};if('body'in opts){ini.body=JSON.stringify(opts.body);ini.headers['Content-Type']='application/json'}if(ini.method!=='GET')ini.headers['X-OSINT-Alpha-Action']='1';let r;try{r=await fetch(path,ini)}catch{throw Error('Network unavailable. Check Render backend status.')}let j;try{j=(r.headers.get('content-type')||'').includes('json')?await r.json():await r.text()}catch{j={}}if(!r.ok){if(r.status===401&&path!=='/api/auth/login'){s.user=null;login()}throw Error(j?.detail||j?.message||'HTTP '+r.status)}return j}
const nav=(id,title,k)=>'<button class="nav-item '+(s.where===id||(id==='cases'&&s.where==='case')?'active':'')+'" data-nav="'+id+'">'+icon(k)+' '+title+'</button>';
function frame(inner){return '<div class="shell"><aside class="sidebar"><div class="brand"><div class="brand-symbol">A</div><div><div class="brand-name">OSINT ALPHA</div><div class="brand-meta">INTELLIGENCE OPERATIONS / V8</div></div></div><nav>'+nav('home','Workspace','home')+nav('cases','Investigations','case')+(s.where==='case'?'<details class="sidebar-tools"><summary>Other workspaces</summary>'+nav('world','World intelligence','world')+nav('sources','Source integrations','sources')+nav('settings','Settings & security','settings')+(s.user?.role==='admin'?nav('admin','Analyst accounts','user'):'')+'</details>':nav('world','World intelligence','world')+'<div class="nav-label">PLATFORM</div>'+nav('sources','Source integrations','sources')+nav('settings','Settings & security','settings')+(s.user?.role==='admin'?nav('admin','Analyst accounts','user'):'') )+'</nav><div class="sidebar-spacer"></div><div class="sidebar-note"><strong><span class="status-dot"></span> Evidence-first research</strong><p>Public-source findings are leads. Verify identities and security claims before relying on them.</p></div></aside><div class="workspace"><header class="topbar"><div class="crumb">OSINT ALPHA / '+h((s.where==='case'?'INVESTIGATIONS':s.where).toUpperCase())+'</div><div class="top-right"><span class="top-status"><span class="status-dot"></span> API CONNECTED</span><span class="user-chip">'+h((s.user?.username||'A')[0].toUpperCase())+'</span></div></header><main class="main">'+inner+'</main></div></div>'}
function login(){app.innerHTML='<div class="login"><section class="login-art"><div class="brand"><div class="brand-symbol">A</div><div><div class="brand-name">OSINT ALPHA</div><div class="brand-meta">INTELLIGENCE WORKSPACE</div></div></div><div class="eyebrow">Source-linked public intelligence</div><h1>From questions to <em>verifiable findings.</em></h1><p>One environment for authorized public identity research, company due diligence, defensive domain and IP enrichment, and geographic observations. Evidence remains attributable.</p><div class="login-tiles"><span>PUBLIC RECORDS</span><span>DEFENSIVE INTELLIGENCE</span><span>TRACEABLE REPORTS</span></div></section><section class="login-panel"><div class="login-card"><div class="eyebrow">SECURE WORKSPACE</div><h2>Welcome back</h2><p>Sign in using your assigned analyst or administrator account.</p><form id="login-form"><div class="field"><label class="field-label">Username</label><input name="username" required autocomplete="username" placeholder="Account username"></div><div class="field"><label class="field-label">Password</label><input name="password" type="password" required autocomplete="current-password" placeholder="Enter your password"></div><button class="btn primary">Sign in '+icon('arrow')+'</button><div id="login-error" class="form-error"></div></form><p class="footer-note">Authorized public-source analysis. Validate original records before making decisions.</p></div></section></div>'}
const heading=(type,title,desc,action='')=>'<div class="section-row" style="margin:0 0 25px"><div><div class="eyebrow">'+h(type)+'</div><h1 class="page-title">'+h(title)+'</h1><p class="page-sub">'+h(desc)+'</p></div>'+action+'</div>';
const caseRow=c=>'<div class="item-row"><div class="row-main"><div class="item-title">'+h(c.title)+'</div><div class="item-sub">'+h(c.subject_type)+' / '+h(c.query)+' · '+h(when(c.created_at))+'</div></div><div class="row-actions"><span class="tag">'+h(c.assessment_status||'open')+'</span><span class="tag">'+Number(c.evidence_count||0)+' public leads</span><button data-open="'+h(c.id)+'" class="btn small">Open case '+icon('arrow')+'</button></div></div>';
const modeButton=key=>'<button type="button" class="chip '+(key===s.mode?'active':'')+'" data-mode="'+key+'">'+icon(modes[key].icon)+' '+modes[key].name+'</button>';
function home(){const ov=s.overview||{};const globalPanel='<section class="mission-map panel"><div class="mission-meta"><div class="eyebrow">OPEN-SOURCE GEO DATA</div><h2>World observation layer</h2><p>Interactive OpenStreetMap base map. Add publisher-observed USGS events; observations are unrelated to a person unless independently established.</p><div class="inline-actions"><button class="btn small primary" data-home-load-events>Load USGS events</button><button class="btn small" data-nav="world">Open geographic workspace</button></div><div class="meta">'+h(s.geoStatus==='idle'?'No live feed loaded':s.geoStatus+' · '+s.geo.length+' publisher records')+'</div></div><div class="mission-map-view" id="geo-map"><div class="map-fallback">Loading map tiles…</div></div></section>';const smart='<section class="hero smart-hero"><div class="eyebrow">OSINT ALPHA / INTELLIGENCE SEARCH</div><h1>Search beyond the obvious.<br><span>Follow the evidence.</span></h1><p class="desc">One question. Relevant public sources. Groq-powered analysis with inspectable Brave references and clear identity uncertainty.</p>'+
 '<form id="smart-search-form" class="input-stack"><label class="field-label" for="smart-query">Enter a research question</label>'+
 '<div class="search-box"><input id="smart-query" name="question" minlength="3" maxlength="200" required autocomplete="off" placeholder="Ask about a public subject, business, event or asset"><button class="btn primary" type="submit">Search public sources '+icon('arrow')+'</button></div>'+
 '<div class="form-row smart-subject-row"><label>Research target<select name="subject_type" id="smart-subject-type"><option value="">Auto-detect and review when ambiguous</option><option value="person">Person</option><option value="organization">Organization / business / public event</option><option value="domain">Domain</option><option value="ip">Public IP asset</option></select></label><label>Research objective<select name="research_purpose"><option value="public_research">Public-source research and verification</option><option value="supplier">Authorized supplier / organizational review</option><option value="security">Defensive security assessment</option><option value="academic">Academic or public-record verification</option></select></label></div>'+
 '<div id="smart-preflight-review" role="status" aria-live="polite"></div>'+
 '<div class="smart-consent"><label class="check"><input type="checkbox" name="authority" required> I confirm a legitimate, authorized purpose for this research; no private tracking or credential access.</label>'+
 '<label class="check"><input type="checkbox" name="ai_opt_in"> Use AI-assisted search and source analysis (Groq and Brave). Query and relevant public excerpts may be sent to configured providers.</label></div>'+
 '<details class="smart-options"><summary>Advanced research scope and public clues</summary><div class="form-row"><label>Research purpose<input name="purpose" minlength="12" maxlength="550" placeholder="Describe the legitimate investigation purpose"></label><label>Work-order category<select name="research_scope"><option value="public_reference">Public-source reference review</option><option value="supplier">Authorized supplier due diligence</option><option value="research">Academic or technology research</option><option value="security">Defensive asset assessment</option></select></label></div><div class="form-row"><input name="city" maxlength="120" placeholder="Known public city / region (optional)"><input name="organization" maxlength="160" placeholder="Known organization (optional)"></div><div class="form-row"><input name="profession" maxlength="120" placeholder="Known public field (optional)"><input name="public_handle" maxlength="120" placeholder="Known public handle (optional)"></div><div class="form-row"><label class="check"><input type="checkbox" name="save_bounded_excerpts"> Save short (up to 160-character) unverified public-index excerpts in this case for later review. Publisher rights must be assessed separately.</label><label>Search freshness<select name="freshness"><option value="all">Any time</option><option value="pd">Last day</option><option value="pw">Last week</option><option value="pm">Last 31 days</option><option value="py">Last year</option></select></label><label>Jurisdiction<select name="country"><option value="US">United States</option><option value="IN">India</option><option value="GB">United Kingdom</option><option value="CA">Canada</option><option value="AU">Australia</option><option value="DE">Germany</option><option value="FR">France</option></select></label></div><div class="form-row"><label>Language<select name="search_lang"><option value="en">English</option><option value="hi">Hindi</option><option value="bn">Bengali</option><option value="ta">Tamil</option><option value="te">Telugu</option><option value="mr">Marathi</option><option value="de">German</option><option value="fr">French</option></select></label><label>Restrict to public site<input name="site" maxlength="80" placeholder="example.org"></label></div><div class="form-row"><label>Exact phrase<input name="exact_phrase" maxlength="80" placeholder="Published phrase"></label><label>Exclude term<input name="exclude" maxlength="40" placeholder="Unrelated term"></label></div></details>'+
 '<p class="help">Source links retain original publishers. Candidate records are not verified identities. Provider usage may incur costs.</p></form></section>'+
 '<div class="section-row"><h2 class="section-heading">Recent investigations</h2><button class="btn small" data-nav="cases">All cases</button></div>'+
 '<div class="panel">'+(s.cases.length?s.cases.slice(0,5).map(caseRow).join(''):'<div class="empty">Your saved investigations will appear here. Start with a natural-language question.</div>')+'</div>';return smart+globalPanel+'<details class="legacy-entry"><summary>Manual research workspace · advanced entry</summary>'+'<section class="hero"><div class="eyebrow">AUTHORIZED PUBLIC-SOURCE INVESTIGATION</div><h1>Find relevant public records.<br><span>Defend every conclusion.</span></h1><p class="desc">Research public profiles, organizations, domains or public IP assets through transparent source queries. Compare possible identities, record analyst decisions and generate a source-backed assessment.</p><form id="start-form" class="input-stack"><div class="chips">'+Object.keys(modes).map(modeButton).join('')+'</div><label class="field-label">Enter a '+h(modes[s.mode].name.toLowerCase())+' search</label><div class="search-box"><input name="query" id="query" placeholder="'+h(modes[s.mode].placeholder)+'" minlength="3" maxlength="160" required><button class="btn primary" '+(s.busy?'disabled':'')+'>'+icon('search')+' '+(s.busy?'Collecting…':'Start investigation')+'</button></div><div class="form-row" style="max-width:850px;margin-top:10px"><div><label class="field-label">Authorized research purpose</label><input name="purpose" required minlength="12" maxlength="550" placeholder="e.g. Authorized supplier due diligence"></div><div class="input-stack"><label class="check"><input type="checkbox" name="authority" required> I have a legitimate purpose and appropriate authorization.</label><label class="check"><input type="checkbox" name="ai_opt_in"> Permit remote AI on this case only when selected.</label></div></div><div class="panel-pad" style="background:rgba(9,16,29,.55);border:1px solid #34415d;border-radius:12px;max-width:850px"><div class="eyebrow" style="margin-bottom:11px">OPTIONAL IDENTITY CLUES · REDUCE NAMESAKES</div><div class="form-row"><input name="city" maxlength="120" placeholder="City or region (e.g. Delhi)"><input name="organization" maxlength="160" placeholder="Known employer / institution"></div><div class="form-row" style="margin-top:10px"><input name="profession" maxlength="120" placeholder="Profession / field"><input name="public_handle" maxlength="120" placeholder="Known public username"></div><p class="help">Clues prioritize potential records; they do not prove identity. Avoid private contact details or home addresses.</p></div><div class="search-foot">Public sources only. The investigation will keep search history, provider outcomes and analyst decisions.</div></form></section><div class="section-row"><h2 class="section-heading">Investigation types</h2><span class="section-note">CHOOSE A RESEARCH WORKFLOW</span></div><div class="cards4">'+Object.entries(modes).map(([id,m])=>'<button class="panel usecase" data-mode="'+id+'"><span class="symbol">'+icon(m.icon)+'</span><strong>'+m.name+'</strong><p>'+m.tip+'</p></button>').join('')+'</div><div class="section-row"><h2 class="section-heading">Workspace at a glance</h2><span class="section-note">AUDITABLE CASE DATA</span></div><div class="stat-grid">'+[['CASES',ov.cases||0,'Saved investigations'],['EVIDENCE',ov.evidence||0,'Candidate records'],['CORROBORATED',ov.corroborated||0,'Human classified'],['INTEGRATED ADAPTERS',s.sources.length,'Actually integrated']].map(x=>'<div class="panel stat"><div class="stat-label">'+x[0]+'</div><div class="stat-number">'+x[1]+'</div><div class="stat-tail">'+x[2]+'</div></div>').join('')+'</div><div class="section-row"><h2 class="section-heading">Recent investigations</h2><button class="btn small subtle" data-nav="cases">View all '+icon('arrow')+'</button></div><div class="panel">'+(s.cases.length?s.cases.slice(0,6).map(caseRow).join(''):'<div class="empty"><div class="large">Start with one question</div><p>Enter a search above. Cases and collected records will appear here.</p></div>')+'</div>'+'</details>';}
function cases(){
 const page=s.casePage||1,total=s.caseTotal||0,pages=Math.max(1,s.caseTotalPages||1);
 const options=(values,current)=>values.map(([id,label])=>'<option value="'+h(id)+'" '+(id===current?'selected':'')+'>'+h(label)+'</option>').join('');
 const filters='<form id="case-filter-form" class="panel panel-pad" style="margin-bottom:14px;display:grid;gap:12px">'+
 '<label class="field-label" for="case-search">Search across all accessible investigations</label>'+
 '<input id="case-search" name="q" maxlength="160" value="'+h(s.caseSearch)+'" placeholder="Title, subject, purpose or known organization">'+
 '<div class="form-row"><label>Status<select name="status">'+options([['all','Any status'],['open','Open'],['researching','Researching'],['awaiting_review','Awaiting review'],['completed','Completed']],s.caseStatus)+'</select></label>'+
 '<label>Subject<select name="subject_type">'+options([['all','All types'],['person','Person'],['organization','Organization'],['domain','Domain'],['ip','Public IP']],s.caseType)+'</select></label>'+
 '<label>Sort<select name="sort">'+options([['newest','Newest first'],['oldest','Oldest first'],['most_evidence','Most evidence'],['recent_activity','Recent source activity']],s.caseSort)+'</select></label></div>'+
 '<div class="form-row"><label>From<input type="date" name="date_from" value="'+h(s.caseFrom)+'"></label>'+
 '<label>To<input type="date" name="date_to" value="'+h(s.caseTo)+'"></label>'+
 (s.user?.role==='admin'?'<label>Analyst owner<input name="owner" value="'+h(s.caseOwner)+'" placeholder="Exact username"></label>':'')+
 '<label>Per page<select name="page_size">'+options([['10','10 cases'],['25','25 cases'],['50','50 cases'],['100','100 cases']],String(s.casePageSize))+'</select></label></div>'+
 '<div class="inline-actions"><button class="btn primary" type="submit">Apply filters</button><button class="btn small subtle" type="button" data-case-reset>Reset</button></div>'+
 '</form>';
 const controls='<div class="panel panel-pad" style="display:flex;gap:14px;align-items:center;justify-content:space-between;flex-wrap:wrap"><span class="meta">'+total+' matching cases · page '+page+' of '+pages+'</span>'+
 '<div class="inline-actions"><button class="btn small" type="button" data-case-page="'+(page-1)+'" '+(page<=1?'disabled':'')+'>Previous</button>'+
 '<button class="btn small" type="button" data-case-page="'+(page+1)+'" '+(page>=pages?'disabled':'')+'>Next</button></div></div>';
 return heading('RESEARCH PORTFOLIO','Investigations','Search and filter your complete accessible case registry, then resume a saved investigation.','<button data-nav="home" class="btn primary">'+icon('plus')+' New investigation</button>')+
 filters+'<div class="panel">'+(s.cases.length?s.cases.map(caseRow).join(''):'<div class="empty">No investigations match these filters.</div>')+'</div>'+controls;
}
const tabs=['overview','assistant','evidence','reports'];
const advancedTabs=['portfolio','investigate','tasks','team','candidates','findings','activity'];
function casePage(){const c=s.case?.case;if(!c)return '<div class="empty">Loading case…</div>';const b=s.brief||{};return '<div class="casehead"><div><button data-nav="cases" class="back-link">'+icon('back')+' Investigations</button><div class="eyebrow">'+h(c.subject_type)+' / EVIDENCE WORKSPACE</div><h1 class="h1">'+h(c.title)+'</h1><p class="page-sub">'+h(c.purpose)+'</p><div class="badge-row" style="margin-top:12px"><span class="tag">'+h(c.query)+'</span><span class="tag">'+Number(b.total||0)+' records</span><span class="tag ok">'+Number(b.counts?.corroborated||0)+' corroborated</span></div></div><div class="inline-actions"><button class="btn small" data-webstart>'+icon('search')+' Research public web</button><button class="btn small" data-collect '+(s.busy?'disabled':'')+'>'+icon('refresh')+' '+(s.busy?'Working…':'Run sources')+'</button><a class="btn small primary" target="_blank" rel="noopener" href="/api/cases/'+h(c.id)+'/report-v4.pdf">Export report</a><button class="btn small subtle" type="button" data-deletecase title="Permanently delete this investigation">Delete case</button></div></div><div class="tabs">'+[...tabs,...(advancedTabs.includes(s.tab)?[s.tab]:[])].map(id=>'<button class="tab '+(s.tab===id?'active':'')+'" data-tab="'+id+'">'+({assistant:'Search & answer',evidence:'Sources',reports:'Report',overview:'Case overview',investigate:'Guided investigator',activity:'Source coverage',candidates:'Identity candidates',findings:'Analyst findings'}[id]||id.charAt(0).toUpperCase()+id.slice(1))+'</button>').join('')+'</div><details class="advanced-tools"><summary>More analyst tools · identities, collaboration, history</summary><div class="advanced-actions"><a class="btn small" target="_blank" rel="noopener" href="/assets/agency.html?case='+h(c.id)+'">Advanced agency toolkit</a>'+advancedTabs.map(id=>'<button class="btn small subtle" data-tab="'+id+'">'+h(id==='investigate'?'Guided research':id==='candidates'?'Identity review':id==='portfolio'?'Candidate profiles':id==='activity'?'Source history':id)+'</button>').join('')+'</div></details>'+({overview:caseOverview,portfolio:casePortfolio,investigate:caseInvestigate,tasks:caseTasks,team:caseTeam,candidates:caseCandidates,evidence:caseEvidence,assistant:caseAssistant,findings:caseFindings,reports:caseReports,activity:caseActivity}[s.tab]||caseOverview)()}

function casePortfolio(){
 const p=s.portfolio||{},profiles=p.accountCandidates||[],mentions=p.documentsAndMentions||[],records=p.items||[],city=p.contextCity||'';
 const intro='<div class="analyst-intro"><div><div class="eyebrow">PUBLIC-SOURCE RECORDS · CANDIDATES ONLY</div><h2>Attributable research portfolio</h2><p>Find public leads relevant to the question—students, tradespeople, community participants, researchers or companies—not only employment profiles. Inspect each source and separate namesakes. No records or photos are automatically confirmed as belonging to the investigated person.</p></div><label class="field-label">Discovery focus <select id="profile-lens"><option value="general">General public information</option><option value="trade">Trades, services and local business</option><option value="education">Education and public activities</option><option value="professional">Professional profiles</option></select></label><button class="btn small" data-profile-search>Search selected focus</button></div>';
 const warnings='<div class="callout warn">This is a candidate portfolio, NOT a verified biography. An account photo shows the source account image, not confirmed identification. LinkedIn items come from public search snippets, without restricted LinkedIn profile access.</div>';
 const mapPanel='<section class="panel panel-pad"><h3>Public location clue</h3><p class="page-sub">Only your supplied city or region can be mapped. The map never pinpoints a person, home or current location.</p>'+
 (city?'<div class="badge-row"><span class="tag">'+h(city)+'</span></div><button class="btn small" data-profile-map>Preview public city map</button>':'<p class="help">Add a city or region in the Overview clues to enable a map preview.</p>')+
 (s.portfolioLocation?'<div class="map" id="profile-map" style="height:300px;margin-top:14px"><div class="map-fallback">Loading map...</div></div><p class="help">'+h(s.portfolioLocation.notice)+' '+(s.portfolioLocation.ambiguous?'Place name may be ambiguous. Check the source.':'')+'</p>':'')+
 '<p class="help">One-click preview sends only the city name to OpenStreetMap Nominatim. © OpenStreetMap contributors.</p></section>';
 const cardsFor=(list)=>list.map(x=>'<article class="profile-card"><div class="profile-top">'+
 (x.photoUrl?'<img class="profile-avatar" src="'+h(url(x.photoUrl))+'" alt="Candidate public-account avatar; identity unverified" loading="lazy" referrerpolicy="no-referrer">':'<div class="profile-avatar profile-avatar-empty" aria-hidden="true">'+icon('user')+'</div>')+
 '<div class="profile-info"><h3>'+h(x.displayName)+'</h3><p>'+h(x.platform.replaceAll('_',' '))+' · '+h(x.sourceProvider)+'</p><div class="badge-row">'+tag(x.reviewStatus)+'<span class="tag">'+Number(x.clues.matched.length)+' matching clues</span>'+(x.clues.different.length?'<span class="tag warn">'+x.clues.different.length+' conflicting clues</span>':'')+'</div></div></div>'+
 '<div class="meta">'+h(x.organization||'Organization not published')+(x.publishedLocation?' · Public location: '+h(x.publishedLocation):'')+(x.publicHandle?' · @'+h(x.publicHandle):'')+'</div>'+
 '<p class="page-sub">'+h(x.summary)+'</p><p class="help">'+h(x.note)+' · Retrieved '+h(when(x.retrievedAt))+'</p>'+
 '<div class="inline-actions">'+link(x.sourceUrl,'Original public source')+(x.website?' '+link(x.website,'Public website'):'')+
 '<button type="button" class="btn small" data-go-evidence="'+h(x.evidenceId)+'">Review evidence</button></div></article>').join('');
 return intro+warnings+'<div class="grid2"><section class="panel"><div class="panel-head"><strong class="panel-title">Public account and author candidates</strong><span class="tag">'+profiles.length+' source candidates / 0 verified identities</span></div><div class="profile-list">'+(cardsFor(profiles)||'<div class="empty">No attributable public-account candidate. Generic web mentions are separate below.</div>')+'</div></section>'+mapPanel+'</div>'+
 '<section class="panel" style="margin-top:18px"><div class="panel-head"><strong class="panel-title">Public documents, articles and search mentions</strong><span class="tag">'+mentions.length+' unverified leads</span></div><div class="profile-list">'+(cardsFor(mentions)||'<div class="empty">No other documents or mentions recorded.</div>')+'</div></section>';
}
let portfolioMap=null;
function drawPortfolioMap(){
 const el=document.getElementById('profile-map');if(!el||!s.portfolioLocation)return;
 if(portfolioMap){try{portfolioMap.remove()}catch{}portfolioMap=null}
 if(!window.L){el.innerHTML='<div class="map-fallback">Leaflet unavailable. City clue: '+h(s.portfolioLocation.cityClue)+'</div>';return}
 const loc=s.portfolioLocation;
 portfolioMap=window.L.map(el,{scrollWheelZoom:false}).setView([loc.lat,loc.lon],8);
 window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:17,attribution:'© OpenStreetMap contributors'}).addTo(portfolioMap);
 window.L.circle([loc.lat,loc.lon],{radius:20000,color:'#96afe2',weight:2,fillOpacity:.08}).addTo(portfolioMap)
 .bindPopup('<strong>'+h(loc.cityClue)+'</strong><p>Approximate public city clue, not a person location.</p>');
}

function caseTeam(){
 const data=s.members||{},editors=data.editors||[],owner=data.owner||{};
 return '<div class="analyst-intro"><div><div class="eyebrow">CASE MEMBERSHIP</div><h2>Authorized case collaboration</h2><p>Grant access to registered analysts for this case only. Editors can research and review but cannot delete or share the investigation.</p></div></div>'+
 '<div class="grid2"><section class="panel"><div class="panel-head"><div class="panel-title">Authorized people</div></div><div class="item-row"><strong>'+h(owner.username||'Unknown')+'</strong><span class="tag ok">Case owner</span></div>'+
 (editors.length?editors.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.username)+'</strong><div class="item-sub">Case editor · '+h(when(x.granted_at))+'</div></div>'+(data.canManage?'<button type="button" class="btn small subtle" data-member-remove="'+h(x.user_id)+'">Revoke</button>':'<span class="tag">Editor</span>')+'</div>').join(''):'<div class="empty">No additional case editors.</div>')+'</section>'+
 (data.canManage?'<section class="panel"><div class="panel-head"><div class="panel-title">Add editor</div></div><form id="member-form" class="panel-pad input-stack"><label>Existing analyst username<input name="username" required minlength="2" maxlength="60" placeholder="Exact account username"></label><button type="submit" class="btn primary">Grant access</button><p class="help">Only the case owner or administrator can change membership. Do not share cases outside the investigation’s authorized purpose.</p></form></section>':'<div class="insight">You have permission to work in this case, but not manage its membership.</div>')+'</div>';
}

function caseTasks(){
 const items=s.tasks||[],options=[['todo','To do'],['in_progress','In progress'],['blocked','Blocked'],['awaiting_review','Awaiting review'],['done','Done'],['cancelled','Cancelled']];
 const opt=(current)=>options.map(([v,label])=>'<option value="'+v+'" '+(v===current?'selected':'')+'>'+label+'</option>').join('');
 const team=(s.taskAssignees||[]).map(a=>'<option value="'+h(a.id)+'">'+h(a.username)+'</option>').join('');
 const form='<section class="panel"><div class="panel-head"><div class="panel-title">New research task</div></div><form id="task-form" class="panel-pad input-stack"><label>Task objective<input name="title" minlength="3" maxlength="180" required placeholder="Verify employer from official website"></label><label>Instructions and evidence needed<textarea name="description" maxlength="2500" placeholder="What needs checking, expected source, accepted completion criteria"></textarea></label><div class="form-row"><label>Priority<select name="priority"><option value="normal">Normal</option><option value="high">High</option><option value="critical">Critical</option><option value="low">Low</option></select></label><label>Owner<select name="assigned_to"><option value="">Unassigned</option>'+team+'</select></label><label>Due date<input name="due_date" type="date"></label></div><button class="btn primary" type="submit">Create research task</button><p class="help">Assignment does not grant access to a different case. Only authorized case owner/administrator assignments are offered.</p></form></section>';
 const cards=items.length?items.map(x=>'<article class="candidate-card"><div class="badge-row"><span class="tag '+(x.status==='done'?'ok':x.status==='blocked'?'warn':'')+'">'+h(x.status.replaceAll('_',' '))+'</span><span class="tag">'+h(x.priority)+'</span></div><h3>'+h(x.title)+'</h3><p class="page-sub">'+h(x.description||'No instructions provided.')+'</p><div class="meta">Assigned to '+h(x.assignee_name||'unassigned')+' · Due '+h(x.due_date||'not scheduled')+'</div><form data-task-change="'+h(x.id)+'" class="input-stack" style="margin-top:15px"><label>Update status<select name="status">'+opt(x.status)+'</select></label><label>Reason or reviewed result<textarea name="note" minlength="8" maxlength="1200" required placeholder="Summarize work completed, blockers, supporting source or uncertainty"></textarea></label><button type="submit" class="btn small">Save task update</button><button type="button" data-task-history="'+h(x.id)+'" class="btn small subtle">View decision history</button></form>'+
 ((s.taskHistory[x.id]||[]).length?'<div class="sourcehealth" style="display:block;margin-top:12px">'+s.taskHistory[x.id].map(a=>'<p class="meta">'+h(when(a.created_at))+' · '+h(a.actor)+' · '+h(a.old_status)+' → '+h(a.new_status)+' · '+h(a.details)+'</p>').join('')+'</div>':'')+'</article>').join(''):'<div class="empty">No assigned research tasks yet. Record work that needs checking, ownership and completion evidence.</div>';
 return '<div class="analyst-intro"><div><div class="eyebrow">INVESTIGATION / HUMAN TASK TRACKING</div><h2>Research assignments and review</h2><p>Capture who will verify which public claims, by when, and document why a task was completed or blocked. Completing a task does not automatically verify a person.</p></div></div><div class="grid2">'+form+'<section class="panel"><div class="panel-head"><div class="panel-title">Task queue ('+Number(s.taskTotal||0)+')</div></div>'+cards+'</section></div>';
}

function caseDossier(){
 const d=s.dossier||{}, a=d.answer||{}, claims=d.claims||[], sources=d.sourceResults||[], names=d.candidates||[];
 const answer=a.integrityOk&&a.text?'<div class="dossier-answer">'+rich(a.text)+'</div>':'<div class="empty">No intact saved source-attributed answer. Review the original records before forming a conclusion.</div>';
 const refs=(a.evidence||[]).slice(0,8).map(x=>'<button type="button" class="btn small" data-go-evidence="'+h(x.id)+'">'+h(x.label||'Saved source')+'</button>').join('')+
  (a.webLeads||[]).slice(0,6).map(x=>link(x.url,x.title||'Web index lead')).join(' ');
 const failures=(d.providerFailures||[]).slice(0,8).map(x=>'<div class="callout warn"><strong>'+h(x.provider)+' · '+h(x.status)+'</strong><p>'+h(x.message||'Provider failed')+'</p><small>'+h(x.query)+'</small></div>').join('');
 const main='<section class="panel dossier-primary"><div class="panel-head"><div><div class="eyebrow">CASE ANSWER · PROVENANCE FIRST</div><h2>Research answer and cited originals</h2></div><span class="tag warn">'+(a.integrityOk?'Saved citation snapshot':'Not source-certified')+'</span></div><div class="panel-pad">'+answer+'<div class="badge-row">'+refs+'</div><p class="help">A saved answer is not a verified biography, identity or independently authenticated fact.</p>'+
  (failures?'<details open><summary>Recorded provider failures ('+d.providerFailures.length+')</summary>'+failures+'</details>':'<p class="help">No provider failure in the recorded window; unsearched sources remain unknown.</p>')+'</div></section>';
 const people='<section class="panel"><div class="panel-head"><strong class="panel-title">Separate identity candidates</strong><button class="btn small" data-tab="candidates">Compare</button></div>'+
  (names.length?names.slice(0,6).map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.display_name)+'</strong><p class="item-sub">'+h(x.classification||'unresolved')+' · '+h(x.reason||'No review reason recorded')+'</p></div></div>').join(''):'<div class="empty">No distinct candidate hypotheses saved. Do not infer that the subject lacks a public presence.</div>')+'</section>';
 const claimRows=claims.slice(0,12).map(x=>'<div class="dossier-claim"><strong>'+h(x.claim)+'</strong><p class="meta">'+h(x.stance)+' · '+h(x.claimBindingState.replaceAll('_',' '))+'</p><div class="inline-actions"><button class="btn small" data-explain-claim="'+h(x.claimId)+'">Inspect quotation</button><button class="btn small subtle" data-go-evidence="'+h(x.evidenceId)+'">Source record</button>'+link(x.originalSourceUrl,'Original URL')+'</div></div>').join('');
 const claimPanel='<section class="panel"><div class="panel-head"><strong class="panel-title">Claim-by-claim cited evidence</strong><span class="tag">'+claims.length+' recorded</span></div>'+
   (claimRows||'<div class="empty">No manual source claims yet. Record statements and capture verbatim passages before signoff.</div>')+'</section>';
 const selected=s.claimDetail;
 const detail=selected?'<section class="panel panel-pad dossier-inspection"><h3>Quotation and capture integrity</h3><p>'+h(selected.claim)+'</p><p class="help">'+h(selected.claimBindingState)+' · Captured text presence is not verified truth.</p>'+
    (selected.quoteEvidence||[]).slice(0,6).map(x=>'<blockquote>'+h(x.quoteText)+'</blockquote><p class="meta">SHA '+h(x.captureHash)+' · Current: '+h(x.currentSourceVersion)+' · Bound: '+h(x.validCurrentTextBinding)+'</p>').join('')+
    link(selected.originalSourceUrl,'Open original page')+'</section>':'';
 const missing='<section class="panel"><div class="panel-head"><strong class="panel-title">Contradictions and missing information</strong><span class="tag warn">Independent review needed</span></div><div class="panel-pad">'+
    (d.missingInformation||[]).map(t=>'<div class="plan-step">'+h(t)+'</div>').join('')+
    (d.nextReviewActions||[]).slice(0,5).map(t=>'<p class="help">• '+h(t)+'</p>').join('')+'</div></section>';
 const select=(id,opts,value)=>'<select id="'+id+'">'+opts.map(x=>'<option value="'+x[0]+'" '+(value===x[0]?'selected':'')+'>'+h(x[1])+'</option>').join('')+'</select>';
 const filters='<div class="form-row panel-pad dossier-filters"><label>Sort '+select('dossier-sort',[['relevance','Question fit'],['newest','Newest'],['source','Publisher source'],['reviewed','Reviewed first']],s.dossierSort)+'</label>'+
   '<label>Review '+select('dossier-status',[['all','Any'],['candidate','Unreviewed'],['corroborated','Corroborated by analyst'],['disputed','Disputed'],['rejected','Rejected']],s.dossierStatus)+'</label>'+
   '<label>Class '+select('dossier-class',[['all','Any'],['account_or_profile_url','Public account leads'],['public_document_or_mention','Documents and mentions']],s.dossierClass)+'</label></div>';
 const items=sources.map(x=>'<div class="item-row dossier-source"><div class="row-main">'+
  (x.licensedThumbnail?'<img class="dossier-thumb" src="'+h(url(x.licensedThumbnail.url))+'" loading="lazy" referrerpolicy="no-referrer" alt="Licensed publisher source media; not a verified person photograph">':'')+
  '<strong>'+h(x.label)+'</strong><p class="item-sub">'+h(x.provider)+' · '+h(x.reviewStatus)+' · '+h(x.sourceClass.replaceAll('_',' '))+' · '+h(when(x.fetchedAt))+'</p><p class="help">'+h(x.summary)+'</p>'+
  '<p class="meta">Ranking terms: '+h((x.rankingExplanation?.matchedQuestionTerms||[]).join(', ')||'none')+' · No calibrated person match</p>'+
  (x.licensedThumbnail?'<p class="meta">Source media credit: '+h(x.licensedThumbnail.credit)+' · '+h(x.licensedThumbnail.license)+'</p>':'')+
  '</div><button class="btn small" data-go-evidence="'+h(x.id)+'">Inspect</button></div>').join('');
 const sourcePanel='<section class="panel"><div class="panel-head"><strong class="panel-title">Sortable, filterable public-source leads</strong><span class="tag">'+Number(d.totalFilteredSourceResults||0)+' candidates</span></div>'+filters+
   (items||'<div class="empty">No results for these filters. This does not establish source absence.</div>')+'</section>';
 const budget=s.budget||{},draft=s.reviewedDraft||{},refinements=s.refinements?.items||[];
 const budgetPanel='<section class="panel" style="margin:14px 0"><div class="panel-head"><strong class="panel-title">External request allowance · today (UTC)</strong><span class="tag warn">Billed cost unknown</span></div><div class="panel-pad"><div class="badge-row">'+
 (budget.dailyCallReservations||[]).map(x=>'<span class="tag">'+h(x.provider)+' '+Number(x.used)+' / '+Number(x.cap)+' reserved</span>').join('')+
 '</div><p class="help">Counts reserve attempts, not vendor invoices or monthly provider quota. Quota failures may prevent a new search.</p></div></section>';
 const refinePanel=names.length?'<section class="panel" style="margin:16px 0"><div class="panel-head"><strong class="panel-title">Refine one candidate without restarting this case</strong></div>'+
 '<form id="case-candidate-refine-form" class="panel-pad input-stack"><label>Candidate hypothesis<select name="candidate_id" required>'+
 names.map(x=>'<option value="'+h(x.id)+'">'+h(x.display_name)+'</option>').join('')+'</select></label>'+
 '<label>Published context<select name="clue_kind"><option value="public_organization">Organization</option><option value="public_city">Public city</option><option value="published_field">Field</option><option value="public_handle">Handle</option></select></label>'+
 '<input name="clue_value" minlength="3" maxlength="120" required placeholder="Known published clue, not private contact details">'+
 '<input name="rationale" minlength="20" maxlength="400" required placeholder="Why this published clue belongs in research">'+
 '<label class="check"><input type="checkbox" name="consent" required> Authorize recording this public-source research pivot</label>'+
 '<button class="btn small primary" type="submit">Save candidate refinement</button></form>'+
 (refinements.slice(0,5).map(x=>'<div class="item-row"><div class="row-main">'+h(x.display_name)+' · '+h(x.clue_kind)+'<p class="meta">'+h(x.search_query)+'</p></div>'+
 '<button class="btn small" data-use-refinement="'+h(x.search_query)+'">Open as research question</button></div>').join(''))+
 '<p class="help">A refinement does not query providers, verify identity or merge different people.</p></section>':'';
 const draftPanel='<section class="panel" style="margin:16px 0"><div class="panel-head"><strong class="panel-title">Reviewed-source report draft</strong><span class="tag warn">Human signoff required</span></div><div class="panel-pad">'+
 '<p class="help">'+Number(draft.sourceCount||0)+' current corroborated, exact-quote-bound claim(s). These are not independently confirmed facts.</p>'+
 '<p>'+h(draft.executive_summary||'No reviewed material yet.')+'</p>'+
 (draft.selectedClaims||[]).slice(0,4).map(x=>'<blockquote>'+h(x.quote)+'</blockquote>'+link(x.sourceUrl,'Original source')).join('')+
 '<p class="help">'+h(draft.limitations||'Missing source limitations')+'</p>'+
 (draft.sourceCount?'<button class="btn small primary" data-approve-report-draft="'+h(draft.reviewToken)+'">I reviewed these excerpts · save pending report</button>':
 '<p class="help">Corroborate and attach exact quotations before a report draft can be saved.</p>')+
 '</div></section>';
 return main+budgetPanel+'<div class="grid2 dossier-grid">'+people+claimPanel+'</div>'+detail+missing+refinePanel+draftPanel+sourcePanel;
}

function caseOverview(){
 const c=s.case.case,ctx=s.case.context||{},ins=s.intel||{},stats=ins.metrics||{},
       run=s.lastResearch,steps=s.researchPlan?.queries||[],triage=s.triage?.candidates||[];
 const current=(ins.assessment||{}).status||'open';
 const useful=triage.filter(x=>x.relevance>0).slice(0,5);
 const readiness=s.readiness||{},pending=readiness.openQuestions||[];
 const cards=[
 ['REVIEWED SOURCES',readiness.sourceRecordsReviewed||0,'Review is not independent fact verification'],
 ['OPEN QUESTIONS',pending.length,'Unresolved investigative scope'],
 ['UNREVIEWED LEADS',readiness.unreviewedCandidateCount||0,'Not verified; possible namesakes'],
 ['FAILED SOURCES',readiness.providerFailures||0,'Failed queries are not no-hit results']
 ];
 const readinessPanel='<section class="panel"><div class="panel-head"><div class="panel-title">What remains unverified?</div><span class="tag warn">Independent review required</span></div><div class="panel-pad">'+
 '<p class="help">Verified facts: 0 without independent adjudication. Calibrated confidence: unavailable. Raw record totals cannot measure identity accuracy.</p>'+
 (pending.length?pending.slice(0,7).map(q=>'<div class="plan-step"><span class="tag warn">Open</span> '+h(q)+'</div>').join(''):'<p class="help">No current internal checklist warnings. Independent source verification and reviewer signoff are still required.</p>')+'</div></section>';
 const header='<div class="analyst-intro"><div><div class="eyebrow">ACTIVE INVESTIGATION · '+h(current.toUpperCase().replaceAll('_',' '))+'</div><h2>What have we actually established?</h2><p>Separate relevant sources from namesakes, record uncertainties, and deliver a source-backed assessment. Nothing is automatically called a verified identity.</p></div><button class="btn primary" data-tab="findings">Write assessment →</button></div>';
 const context='<section class="panel" style="margin:0 0 20px"><div class="panel-head"><div><div class="panel-title">Target identity · known public context</div><div class="panel-meta">These clues now influence research planning and should guide verification.</div></div><span class="tag accent">Editable</span></div><form class="panel-pad input-stack" id="context-form"><div class="form-row"><input name="city" aria-label="Known city or region" maxlength="120" value="'+h(ctx.city||'')+'" placeholder="City or region"><input name="organization" aria-label="Known employer or organization" maxlength="160" value="'+h(ctx.organization||'')+'" placeholder="Known organization"></div><div class="form-row"><input name="profession" aria-label="Known professional field" maxlength="120" value="'+h(ctx.profession||'')+'" placeholder="Profession or field"><input name="public_handle" aria-label="Known public username" maxlength="120" value="'+h(ctx.public_handle||'')+'" placeholder="Known public username"></div><div class="inline-actions"><button type="submit" class="btn small">Save identity clues</button><span class="help">Unknown context remains unknown. Never interpret missing fields as a contradiction.</span></div></form></section>';
 const plan='<section class="panel"><div class="panel-head"><div><div class="panel-title">Transparent research plan</div><div class="panel-meta">Allowlisted source APIs; no claim of universal internet coverage.</div></div><span class="tag accent">'+steps.length+' planned searches</span></div><div class="panel-pad"><div class="form-row" style="align-items:end"><div><label class="field-label" for="research-depth">Research depth</label><select id="research-depth">'+['quick','standard','thorough'].map(d=>'<option value="'+d+'" '+(s.depth===d?'selected':'')+'>'+d[0].toUpperCase()+d.slice(1)+'</option>').join('')+'</select></div><button class="btn primary" data-collect '+(s.busy?'disabled':'')+'>'+icon('search')+' '+(s.busy?'Researching…':'Run source research')+'</button><button type="button" class="btn small" data-web-discover '+(s.busy?'disabled':'')+'>'+icon('globe')+' Discover public web</button></div><p class="help">Broad web: '+(s.webProviders?.web?.configured?'Brave provider configured':'requires private Brave Search API key')+'. Search results are leads, not verified person records.</p>'+
 (steps.length?'<div class="plan-steps">'+steps.map((x,i)=>'<div class="plan-step"><span class="plan-n">'+(i+1)+'</span><div><strong>'+h(x.provider)+'</strong><div class="meta">'+h(x.query)+'</div><small>'+h(x.reason)+'</small></div></div>').join('')+'</div>':'<div class="empty">There is no compatible source plan for this investigation.</div>')+
 (run?'<div class="callout '+(run.errors?'warn':'ok')+'">Last run: '+run.returned+' returned candidates; '+run.new+' newly saved; '+run.errors+' provider errors. A returned candidate is not a verified match.</div>':'')+'</div></section>';
 const diagnostics=s.queryExplain||{};
 const explain='<section class="panel"><div class="panel-head"><div class="panel-title">Why sources were searched or skipped</div><span class="tag">Recorded outcomes</span></div><div class="panel-pad">'+
 ((diagnostics.executedQueries||[]).length?diagnostics.executedQueries.slice(0,12).map(x=>'<div class="plan-step"><strong>'+h(x.provider)+'</strong> · '+h(x.status)+' · '+Number(x.returned||0)+' hits<div class="meta">'+h(x.query)+'</div><small>'+h(x.message||'')+'</small></div>').join(''):'<p class="help">No recorded search calls; an unsearched source is not a no-hit result.</p>')+
 '<p class="help">'+Number((diagnostics.skippedStructuredProviders||[]).length)+' compatible or unselected structured providers were not searched. No-hit and failures cannot prove absence.</p></div></section>';
  const sideBySide=(s.candidates||[]).length>1?
 '<section class="panel"><div class="panel-head"><div class="panel-title">Distinct candidate identities · compare before linking</div><button class="btn small" data-tab="candidates">Review candidate evidence</button></div><div class="grid2">'+
 s.candidates.slice(0,4).map(p=>'<article class="candidate-card"><div class="badge-row"><span class="tag warn">Hypothesis only</span><span class="tag">'+h(p.classification||'unresolved')+'</span></div><h3>'+h(p.display_name||'Unknown candidate')+'</h3><p class="help">'+h((p.reason||'No review rationale')?.slice(0,220))+'</p>'+
 '<div class="meta">'+Number((p.sources||[]).length)+' linked public candidate sources</div>'+
 (p.sources||[]).slice(0,4).map(x=>'<div class="item-sub">'+h(x.provider)+' · '+h(x.status)+' · '+h(x.label||'Source')+'</div>').join('')+
 '<p class="help">No identity verified by display name or shared username.</p></article>').join('')+
 '</div></section>': '';
 const counterSources=(ins.evidence||[]).filter(x=>x.status==='rejected'||x.status==='disputed').slice(0,8);
 const excludedPeople=(s.candidates||[]).filter(x=>x.classification==='excluded').slice(0,6);
 const counterPanel='<section class="panel"><div class="panel-head"><div class="panel-title">Counter-evidence and explicitly excluded namesakes</div><span class="tag warn">Review before attribution</span></div>'+
 (counterSources.length?counterSources.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.label)+'</strong><div class="item-sub">'+h(x.status)+' · '+h((x.reviewer_notes||'Reason pending review').slice(0,300))+'</div></div><button class="btn small" data-go-evidence="'+h(x.id)+'">Inspect</button></div>').join(''):'<div class="empty">No rejected or disputed source records documented. This does not mean the candidate has no contradicting evidence.</div>')+
 (excludedPeople.length?excludedPeople.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.display_name)+'</strong><div class="item-sub">Excluded candidate hypothesis · '+h((x.reason||'Unspecified review').slice(0,240))+'</div></div></div>').join(''):'')+
 '<div class="panel-pad"><p class="help">Excluded namesakes and contradictory records must remain visible; none independently establishes a person identity.</p></div></section>';
  const progress=s.searchProgress||{};
 const savedProgressPanel=progress.available?'<section class="panel"><div class="panel-head"><div class="panel-title">Saved question · reproducible search progress</div><span class="tag">Case history</span></div><div class="panel-pad"><p class="help">Original question: '+h(progress.originalQuestion||'')+'</p>'+
 (progress.plannedStructuredSources||[]).map(x=>'<div class="plan-step"><strong>'+h(x.provider)+'</strong> · '+h(x.status)+' · '+Number(x.executedQueries)+' searches · '+Number(x.resultsRecorded)+' indexed candidates</div>').join('')+
 '<p class="help">Public web: '+h(progress.publicWebIndexState)+' · Saved assistant outputs: '+Number(progress.savedAssistantMessages||0)+'. No search has independently established complete coverage.</p>'+
 '<button class="btn small primary" data-resume-saved-plan '+(s.busy?'disabled':'')+'>Open resumable source investigation</button></div></section>':'';
  const candidates='<section class="panel"><div class="panel-head"><div class="panel-title">Potentially relevant source leads</div><button class="btn small subtle" data-tab="candidates">Compare identities →</button></div>'+
 (useful.length?useful.map(x=>'<div class="item-row"><div class="row-main"><div class="item-title">'+h(x.label)+'</div><div class="item-sub">'+h(x.provider)+' · matched public clues: '+h(x.signals.join(', ')||'none')+'</div></div><button data-go-evidence="'+h(x.id)+'" class="btn small">Inspect</button></div>').join(''):'<div class="empty">No source records presently match supplied public clues. Do not assume the target has no online presence.</div>')+'</section>';
 return header+caseDossier()+context+'<div class="stat-grid">'+cards.map(x=>'<div class="panel stat"><div class="stat-label">'+x[0]+'</div><div class="stat-number">'+x[1]+'</div><div class="stat-tail">'+x[2]+'</div></div>').join('')+'</div>'+readinessPanel+'<div class="grid2">'+plan+candidates+'</div>'+savedProgressPanel+counterPanel+sideBySide+explain;
}

function caseInvestigate(){
 const jobs=s.jobs||[],job=s.job||{},current=(job.id&&s.jobs.find(x=>x.id===job.id))||null;
 const canGroq=!!s.server.groqConfigured&&!!s.case.case.ai_opt_in;
 const canWeb=!!s.webProviders?.web?.configured;
 const workflow='<div class="analyst-intro"><div><div class="eyebrow">BOUNDED RESEARCH / SAVED STEPS</div><h2>Investigate. Follow the evidence.</h2><p>Run source queries iteratively, retain each result, and revise the plan. With case-level remote AI consent, Groq may propose the next <em>allowed</em> search. Nothing is automatically considered a verified identity.</p></div></div>';
 const form='<section class="panel"><div class="panel-head"><div><div class="panel-title">New investigation run</div><div class="panel-meta">Each step is saved; interrupted work can be recovered.</div></div><span class="tag">1–8 source queries</span></div><form id="job-form" class="panel-pad input-stack"><label class="field-label" for="job-objective">What are you trying to establish?</label>'+
 '<textarea id="job-objective" name="objective" minlength="12" maxlength="500" required placeholder="Find corroborated public professional accounts while distinguishing namesakes">'+h(s.case.case.purpose||'')+'</textarea>'+
 '<div class="form-row"><label class="field-label">Research planner<select name="mode"><option value="guided">Guided source plan (no model)</option><option value="groq" '+(!canGroq?'disabled':'')+'>Groq model proposes follow-up source queries</option></select></label>'+
 '<label class="field-label">Step budget<select name="max_steps">'+[3,5,8].map(n=>'<option value="'+n+'" '+(n===5?'selected':'')+'>'+n+' source requests</option>').join('')+'</select></label></div>'+
 '<label class="checkbox-row"><input type="checkbox" name="allow_web" value="on" '+(!canWeb?'disabled':'')+'> Include Brave public-web discovery '+(canWeb?'':'(API key unavailable)')+'</label>'+
 '<label class="checkbox-row"><input type="checkbox" name="consent" value="on"> I authorize sending this public-source research subject to the selected external providers</label>'+
 (!canGroq?'<p class="help">Model-led search requires GROQ_API_KEY and explicit remote-AI consent in the Research copilot. Otherwise the source planner remains rules-based.</p>':'')+
 '<button class="btn primary" type="submit" '+(s.busy?'disabled':'')+'>Create and run investigation</button><p class="help">The browser drives one saved step at a time. Closing it pauses execution; you can resume. This is not a 24/7 background agent.</p></form></section>';
 const list='<section class="panel"><div class="panel-head"><div class="panel-title">Saved research runs</div><span class="tag">'+jobs.length+' runs</span></div>'+
 (jobs.length?jobs.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.objective)+'</strong><div class="item-sub">'+h(x.mode)+' · '+h(x.status)+' · '+Number(x.completed_steps)+'/'+Number(x.max_steps)+' steps · '+h(when(x.updated_at))+'</div></div><button class="btn small" data-job-select="'+h(x.id)+'">Inspect / resume</button></div>').join(''):
 '<div class="empty">No guided runs yet. Set a clear objective above to start a reproducible research sequence.</div>')+'</section>';
 const steps=job.id?'<section class="panel" style="margin-top:18px"><div class="panel-head"><div><div class="panel-title">Current investigation</div><div class="panel-meta">'+h(job.objective)+' · '+h(job.mode)+'</div></div>'+tag(job.status)+'</div><div class="panel-pad"><div class="badge-row"><span class="tag">'+Number(job.completedSteps)+'/'+Number(job.maxSteps)+' steps</span><span class="tag">'+h(job.mode==='groq'?'Model-directed pivots with allowlisted sources':'Deterministic public-source plan')+'</span></div>'+
 (job.lastError?'<p class="help">'+h(job.lastError)+'</p>':'')+
 '<div class="inline-actions"><button class="btn primary" data-job-run '+(s.busy||job.status==='completed'||job.status==='running'||job.status==='failed'?'disabled':'')+'>'+h(s.busy?'Running source queries…':'Continue saved research')+'</button>'+
 ((job.status==='failed'||job.status==='running')?'<button class="btn small" data-job-recover '+(s.busy?'disabled':'')+'>Recover interrupted run</button>':'')+
 '<button class="btn small subtle" data-tab="evidence">Review discovered sources</button></div></div>'+
 ((job.steps||[]).length?job.steps.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.number+'. '+x.provider+' · '+x.query)+'</strong><div class="item-sub">'+h(x.rationale)+'</div><div class="meta">'+h(x.error||'')+'</div></div><div class="badge-row">'+tag(x.status)+'<span class="tag">'+Number(x.returned)+' returned</span><span class="tag">'+Number(x.new)+' new</span></div></div>').join(''):
 '<div class="empty">No search steps executed. Start or continue the saved research run.</div>')+
 '</section>':'';
 return workflow+'<div class="grid2">'+form+list+'</div>'+steps;
}

function caseCandidates(){
 const items=s.candidates||[],ev=s.case.evidence||[];
 const identity=s.identity||{},records=identity.records||[],proposals=identity.pairSuggestions||[],
    compared=identity.comparison||null;
 const selectSource=(name,selected)=>'<select name="'+name+'" required aria-label="Source record '+name+'">'+records.map(x=>'<option value="'+h(x.recordId)+'" '+(selected===x.recordId?'selected':'')+'>'+h(x.provider+' · '+x.label.slice(0,95))+'</option>').join('')+'</select>';
 const comparison=compared?'<div class="panel-pad"><div class="badge-row">'+tag(compared.signalLevel)+'</div><p class="help">'+h(compared.limitation)+'</p>'+
 '<div class="grid2">'+[compared.left,compared.right].map(x=>'<div class="sourcehealth" style="display:block;padding:14px"><strong>'+h(x.provider)+' · '+h(x.label)+'</strong>'+
 ['name','organization','location','publicHandle','website'].map(k=>'<p class="meta">'+h(k)+': '+h(x[k]||'Not published')+'</p>').join('')+
 link(x.url,'Original public record')+'</div>').join('')+'</div>'+
 '<div class="divider"></div><strong>Matching published attributes</strong>'+
 (compared.matching.length?compared.matching.map(m=>'<p class="meta">'+h(m.field)+': '+h(m.value)+'</p>').join(''):'<p class="help">No explicit matching identifiers found.</p>')+
 '<strong>Differences requiring human interpretation</strong>'+
 (compared.differing.length?compared.differing.map(m=>'<p class="meta">'+h(m.field)+': '+h(m.left)+' / '+h(m.right)+'</p>').join(''):'<p class="help">No explicit different attributes recorded.</p>')+'</div>':'';
 const metric=s.identityQuality||{},matrix=metric.confusion||{};
 const quality='<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div><div class="panel-title">Identity signal evaluation</div><div class="panel-meta">Against analyst-labelled public source pairs; not ground-truth identity accuracy.</div></div><span class="tag">'+Number(metric.latestLabelledPairs||0)+' labelled pairs</span></div><div class="panel-pad"><div class="stat-grid">'+[
 ['SIGNAL PRECISION',metric.precisionAgainstAnalystLabels],
 ['SIGNAL RECALL',metric.recallAgainstAnalystLabels],
 ['FALSE ALERT RATE',metric.falseAlertRateAgainstAnalystLabels]
 ].map(([name,value])=>'<div class="panel stat"><div class="stat-label">'+h(name)+'</div><div class="stat-number">'+(typeof value==='number'?(value*100).toFixed(1)+'%':'N/A')+'</div></div>').join('')+'</div><p class="help">'+h(metric.limitation||'An empty labelled set cannot establish measured identity quality.')+'</p>'+
 (metric.sampleSufficientForInternalTrend?'':'<p class="help">Not enough diverse reviewed examples for even an internal trend. Collect at least 20 pairs with both classes represented.</p>')+
 '<div class="meta">Review matches: '+Number(matrix.tp||0)+' · false signals: '+Number(matrix.fp||0)+' · missed signals: '+Number(matrix.fn||0)+' · correctly unflagged: '+Number(matrix.tn||0)+'</div></div></section>';
 const labelForm=compared?'<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div class="panel-title">Record an analyst evaluation example</div></div><form id="identity-label-form" class="panel-pad input-stack"><input type="hidden" name="left_id" value="'+h(compared.left.recordId)+'"><input type="hidden" name="right_id" value="'+h(compared.right.recordId)+'"><label>Assessment of this record pair<select name="decision"><option value="different_people">Different people / not linked</option><option value="possible_same_person">Possible same person (unverified)</option></select></label><label>Why does the current public evidence support this label?<textarea name="rationale" minlength="30" maxlength="1500" required placeholder="Mention original accounts, conflicting identifiers or independent corroboration. Do not use a shared name alone."></textarea></label><button class="btn small" type="submit">Save review label</button><p class="help">Human labels are hypotheses, not verified identities. They measure internal signal agreement only.</p></form></section>':'';
 const sourceMatrix='<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div><div class="panel-title">Identity source comparison</div><div class="panel-meta">Compare public attributes side by side. A shared display name is insufficient to link accounts.</div></div><span class="tag">'+records.length+' candidate records</span></div>'+
 (records.length>=2?'<form id="identity-compare-form" class="panel-pad input-stack"><div class="form-row">'+
 selectSource('left',compared?.left?.recordId)+selectSource('right',compared?.right?.recordId)+
 '</div><button class="btn small" type="submit">Compare published attributes</button></form>':
 '<div class="empty">At least two source candidates are required. Run source research first.</div>')+comparison+
 '<div class="panel-head"><div class="panel-title">Potential shared public identifiers</div><span class="tag">'+proposals.length+' to inspect</span></div>'+
 (proposals.length?proposals.slice(0,18).map(p=>'<div class="item-row"><div class="row-main"><strong>'+h(p.leftLabel)+' / '+h(p.rightLabel)+'</strong><div class="item-sub">'+h(p.providers.join(' · '))+' · '+h(p.matching.map(x=>x.field).join(', '))+'</div></div><button type="button" class="btn small" data-identity-pair="'+h(p.leftId+':'+p.rightId)+'">Compare</button></div>').join(''):
 '<div class="empty">No cross-source explicit public identifier overlap found. Do not treat name-only matches as a linked identity.</div>')+
 '<div class="panel-head"><div class="panel-title">Known-clue relevance</div></div>'+
 records.slice(0,18).map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.label)+'</strong><div class="item-sub">'+h(x.provider)+' · matched: '+h(x.clues.matched.join(', ')||'none')+' · differing: '+h(x.clues.different.map(d=>d.field).join(', ')||'none')+'</div></div>'+link(x.url,'Source')+'</div>').join('')+
 '<p class="help panel-pad">'+h(identity.notice||'This does not verify ownership or identity.')+'</p></section>';

 return '<div class="analyst-intro"><div><div class="eyebrow">IDENTITY RESOLUTION / ANALYST CONTROL</div><h2>Compare namesakes. Do not merge blindly.</h2><p>Group only records supported by matching public identifiers. An analyst confirmation is a documented decision, not legal identity verification.</p></div></div>'+
 sourceMatrix+quality+labelForm+'<div class="grid2"><section class="panel"><div class="panel-head"><div class="panel-title">Candidate profiles ('+items.length+')</div></div>'+
 (items.length?items.map(x=>'<article class="candidate-card"><div class="badge-row">'+tag(x.classification)+'</div><h3>'+h(x.display_name)+'</h3><p class="page-sub">'+h(x.reason||'No rationale yet.')+'</p><div class="meta">'+x.sources.length+' linked public-source record(s)</div>'+
 x.sources.map(y=>'<div class="sourcehealth">'+link(y.source_url,y.label)+' <span class="tag">'+h(y.status)+'</span></div>').join('')+
 '<form data-candidate-review="'+h(x.id)+'" class="input-stack"><label class="field-label">Analyst hypothesis</label><select name="classification">'+['unresolved','potential_match','excluded','confirmed_by_analyst'].map(v=>'<option value="'+v+'" '+(x.classification===v?'selected':'')+'>'+h(String(v).replaceAll('_',' '))+'</option>').join('')+'</select><textarea name="reason" maxlength="1500" aria-label="Reason for analyst hypothesis" placeholder="Explain corroborating or conflicting evidence">'+h(x.reason||'')+'</textarea><button class="btn small">Save decision</button></form>'+
 (ev.length?'<form data-candidate-link="'+h(x.id)+'" class="input-stack" style="margin-top:15px"><label class="field-label">Associate a source record</label><select name="evidence_id">'+ev.map(y=>'<option value="'+h(y.id)+'">'+h(y.provider+' · '+y.label.slice(0,80))+'</option>').join('')+'</select><input name="rationale" maxlength="1200" placeholder="Why might these records refer to the same subject?"><button class="btn small subtle">Attach candidate evidence</button></form>':'')+'</article>').join(''):'<div class="empty"><div class="large">No candidate identities yet</div><p>Run a source search, then create an explicit hypothesis instead of merging matching names automatically.</p></div>')+'</section>'+
 '<section class="panel"><div class="panel-head"><div class="panel-title">Create an identity hypothesis</div></div><form class="panel-pad input-stack" id="candidate-create-form"><label class="field-label">Candidate identifier</label><input name="display_name" minlength="2" maxlength="180" required placeholder="e.g. Ayush Tripathi — Delhi developer"><label class="field-label">Reason this might be a distinct person</label><textarea name="reason" maxlength="1500" placeholder="Known public account, employer, city, source references…"></textarea><button class="btn primary">Create candidate group</button><p class="help">This does not prove two accounts belong to the same person. Source linking always requires an analyst review.</p></form>'+
 '<div class="insight"><h3>What counts as a reliable match?</h3><p>Use specific independent identifiers or corroborating source claims. A name match, shared city or similar profession alone should not establish identity. Record exclusions and contradictions.</p></div></section></div>';
}

async function runJobFlow(){
 if(s.busy||!s.job?.id||s.job.status!=='ready')return;
 s.busy=true;render();
 try{
  let count=0;
  while(s.job?.status==='ready'&&count<8){
   s.job=await api('/api/cases/'+s.id+'/jobs/'+s.job.id+'/step',{method:'POST',body:{}});
   count++;render();
  }
  await Promise.all([fetchCase(),refreshCases(),loadResearchState()]);
  toast('Research saved: '+s.job.completedSteps+' public-source requests. Review the records before concluding.');
 }finally{s.busy=false;render()}
}
function caseEvidence(){
 const ev=s.case.evidence||[],shown=ev.filter(x=>
    (s.evidenceFilter==='all'||x.status===s.evidenceFilter)&&
    (!s.evidenceSearch||[x.label,x.summary,x.provider].join(' ').toLowerCase().includes(s.evidenceSearch.toLowerCase()))),
 selected=ev.find(x=>x.id===s.selected)||shown[0]||ev[0];
 const suggestions=s.duplicateSources||{},pairs=suggestions.pairs||[];
 const duplicates='<section class="panel" style="margin-bottom:16px"><div class="panel-head"><div><div class="panel-title">Potential duplicate source records</div><div class="panel-meta">Exact DOI/URL links are not independent corroboration; similar titles need human review.</div></div><span class="tag accent">'+Number(suggestions.totalPairs||0)+' source pairs</span></div>'+
 (pairs.length?pairs.slice(0,12).map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.leftLabel)+' / '+h(x.rightLabel)+'</strong><div class="item-sub">'+h(x.rule.replaceAll('_',' '))+' · '+h(x.reason)+'</div></div><div class="inline-actions"><button class="btn small" data-go-evidence="'+h(x.leftId)+'">First source</button><button class="btn small subtle" data-go-evidence="'+h(x.rightId)+'">Second</button></div></div>').join(''):'<div class="empty">No likely duplicate source pairs identified in the indexed case records. This is not proof that all sources are independent.</div>')+
 '<div class="panel-pad"><p class="help">'+h(suggestions.caveat||'Suggestions only; no automatic identity or source merging.')+'</p></div></section>';
 const toolbar='<div class="filterbar"><input id="evidence-search" aria-label="Search evidence by title, summary or source" placeholder="Find a public-source record…" value="'+h(s.evidenceSearch)+'"><select id="evidence-status" aria-label="Filter review status">'+['all','candidate','corroborated','disputed','rejected'].map(x=>'<option value="'+x+'" '+(s.evidenceFilter===x?'selected':'')+'>'+h(x.replaceAll('_',' '))+'</option>').join('')+'</select><span class="meta">'+shown.length+'/'+ev.length+' shown</span></div>';
 const bulk='<form id="bulk-review-form" class="bulkbar"><strong>Bulk review</strong><span class="meta">'+s.evidenceSelected.length+' selected</span><select name="status" aria-label="Bulk classification"><option value="rejected">Reject namesakes</option><option value="disputed">Mark disputed</option><option value="candidate">Return to candidate</option><option value="corroborated">Analyst corroboration</option></select><input name="notes" minlength="12" maxlength="1200" required placeholder="Reason for every selected classification"><button class="btn small" type="submit" '+(!s.evidenceSelected.length?'disabled':'')+'>Apply to selected</button></form>';
 const list=shown.length?shown.map(x=>'<div class="evidence-tile '+(x.id===selected?.id?'selected':'')+'"><label class="pick"><input type="checkbox" data-pick-evidence="'+h(x.id)+'" '+(s.evidenceSelected.includes(x.id)?'checked':'')+' aria-label="Select '+h(x.label)+'"></label><button class="evidence-tile-body" data-evidence="'+h(x.id)+'"><span class="badge-row">'+tag(x.status)+'<span class="tag">'+h(x.provider)+'</span></span><strong>'+h(x.label)+'</strong><span class="ev-description">'+h(x.summary)+'</span><span class="ev-meta">Collected '+h(when(x.fetched_at))+'</span></button></div>').join(''):
 '<div class="empty">No records match this filter. Clear your search or run new source queries.</div>';
 const excerptForm=selected&&(s.captures[selected.id]||[]).length?
 '<form id="excerpt-form" class="input-stack" style="margin:15px 0;border-top:1px solid var(--stroke);padding-top:14px"><strong>Save exact source quotation</strong>'+
 '<input type="hidden" name="evidence_id" value="'+h(selected.id)+'"><label class="field-label">Captured page<select name="capture_id">'+
 (s.captures[selected.id]||[]).map(c=>'<option value="'+h(c.id)+'">'+h(when(c.fetchedAt))+' · '+h(c.sha256.slice(0,12))+'</option>').join('')+'</select></label>'+
 '<textarea name="quote_text" minlength="25" maxlength="700" placeholder="Paste an exact quote from the captured text" required></textarea>'+
 '<textarea name="interpretation" minlength="10" maxlength="1000" placeholder="State what the passage suggests, including uncertainty" required></textarea>'+
 '<button class="btn small primary">Save matched passage</button>'+
 '<p class="help">Matching a captured passage does not establish its truth or the author’s identity.</p></form>':'';
 const inspector=selected?'<div class="inspector"><div class="badge-row">'+tag(selected.status)+'<span class="tag">'+h(selected.provider)+'</span></div><h3>'+h(selected.label)+'</h3><p>'+h(selected.summary)+'</p><div class="source-item"><strong>Original source</strong><p>'+link(selected.source_url,'Inspect public source')+'</p><div class="meta">Collected: '+h(when(selected.fetched_at))+'</div><div class="meta">Record hash: '+h(selected.sha256||'Unknown')+'</div></div><div class="source-item"><div class="eyebrow">SOURCE CAPTURE / VERIFICATION</div><p class="help">Page text captures are restricted to approved public hosts. They are not independently verified facts.</p><div class="inline-actions"><button type="button" class="btn small" data-capture-source="'+h(selected.id)+'">Capture permitted source text</button><button type="button" class="btn small subtle" data-show-captures="'+h(selected.id)+'">View captures</button><button type="button" class="btn small subtle" data-version-history="'+h(selected.id)+'">Record versions</button></div>'+
 ((s.versions[selected.id]||[]).length?'<section class="sourcehealth" style="display:block;padding:12px;margin:12px 0"><strong>Observed record versions</strong>'+
 (s.versions[selected.id]||[]).map(v=>'<p class="meta">'+h(when(v.captured_at))+' · '+h(v.disposition)+' · '+h(v.content_sha256.slice(0,16))+'…<span style="display:block">'+h(v.summary)+'</span></p>').join('')+'</section>':'')+
 ((s.captures[selected.id]||[]).length?(s.captures[selected.id]||[]).slice(0,2).map(c=>'<div class="sourcehealth" style="display:block;margin-top:12px"><div class="meta">'+h(when(c.fetchedAt))+' · SHA '+h(c.sha256.slice(0,18))+'</div><p style="max-height:270px;overflow:auto;white-space:pre-wrap">'+h(c.text)+'</p></div>').join(''):'')+
 excerptForm+'</div><div class="divider"></div><form id="review-form" class="input-stack"><input type="hidden" name="id" value="'+h(selected.id)+'"><label class="field-label">Analyst review classification</label><select name="status">'+['candidate','corroborated','disputed','rejected'].map(x=>'<option value="'+x+'" '+(x===selected.status?'selected':'')+'>'+x+'</option>').join('')+'</select><label class="field-label">Reason, caveats and potential namesakes</label><textarea name="notes" maxlength="1200" placeholder="Record your reason and uncertainty…">'+h(selected.reviewer_notes||'')+'</textarea><button class="btn primary">Save review decision</button></form><div class="divider"></div><form id="claim-form" class="input-stack"><input type="hidden" name="evidence_id" value="'+h(selected.id)+'"><label class="field-label">Source-linked assertion</label><textarea name="claim_text" minlength="10" maxlength="1200" required placeholder="What does this source actually say?"></textarea><select name="stance"><option value="supports">Supports</option><option value="contradicts">Contradicts</option><option value="context">Context only</option></select><button class="btn small">Record claim and source</button></form><p class="help">Do not mark a person verified merely because this record includes the subject name.</p></div>':'<div class="empty">Select a record to inspect.</div>';
 return duplicates+'<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div><div class="panel-title">Evidence workbench</div><div class="panel-meta">Filter, inspect and record decisions against individual original sources</div></div><button class="btn small" data-add>Add source lead</button></div><div class="panel-pad">'+toolbar+bulk+'</div></section>'+
 '<div class="evidence"><section class="panel"><div class="panel-head"><div class="panel-title">Source records</div><span class="panel-meta">'+shown.length+' matching</span></div><div class="evidence-list" id="ev-list">'+list+'</div></section>'+
 '<section class="panel"><div class="panel-head"><div class="panel-title">Source inspector</div><span class="panel-meta">PROVENANCE · REVIEW</span></div>'+inspector+'</section></div>';
}

function rich(text){let html='',ul=false;const inline=x=>h(x).replace(/\*\*([^*]{1,150})\*\*/g,'<strong>$1</strong>').replace(/\[([^\]]{1,160})\]\((https?:\/\/[^\s)]+)\)/g,(_,title,raw)=>{const href=url(raw.replace(/&amp;/g,'&'));return href==='#'?title:'<a class="text-link" href="'+h(href)+'" target="_blank" rel="noopener noreferrer">'+title+' ↗</a>'});for(const raw of String(text||'').split(/\r?\n/)){const line=raw.trim();if(!line){if(ul){html+='</ul>';ul=false}continue}const heading=line.match(/^#{1,4}\s+(.+)/);if(heading){if(ul){html+='</ul>';ul=false}html+='<h4>'+inline(heading[1])+'</h4>';continue}if(/^[•*-]\s+/.test(line)){if(!ul){html+='<ul>';ul=true}html+='<li>'+inline(line.replace(/^[•*-]\s+/,''))+'</li>';continue}if(ul){html+='</ul>';ul=false}html+='<p>'+inline(line)+'</p>'}if(ul)html+='</ul>';return html||'<p>No evidence was returned.</p>'}
function citations(ids){const ev=s.case?.evidence||[];return (ids||[]).map(id=>ev.find(e=>e.id===id)).filter(Boolean).map((x,n)=>'<a class="tag accent" target="_blank" rel="noopener noreferrer" href="'+h(url(x.source_url))+'">Source '+(n+1)+': '+h(x.provider)+'</a>').join('')}
function caseAssistant(){
 const c=s.case.case,p=s.provider;
 const route=s.smartPlan||null;
 const history='<div class="source-item"><div class="eyebrow" style="margin-bottom:10px">SAVED RESEARCH CONVERSATIONS</div><div class="inline-actions"><select id="conversation-select" style="flex:1;min-width:130px"><option value="">New conversation</option>'+
 (s.conversations||[]).map(x=>'<option value="'+h(x.id)+'" '+(s.sessionId===x.id?'selected':'')+'>'+h(x.title.slice(0,55))+'</option>').join('')+
 '</select><button class="btn small" data-newchat>New chat</button></div><p class="help">Chats and source links are saved to the investigation database.</p></div>';
 const canRemote=!!s.server.groqConfigured||!!s.server.aiConfigured;
 const intro='<div class="callout '+(p==='local'?'warn':'ok')+'">'+(
  p==='local'?'Offline guidance is rule-based, not an AI chatbot. Choose a configured model for conversational research.':
  'Conversational AI can combine saved case evidence with consented, question-specific Brave excerpts or Groq-hosted browser search. Public results are candidate sources, never verified facts.'
 )+'</div>';
 const messages=s.messages.length?s.messages.map((m,idx)=>'<div class="message '+m.role+'"><div class="bubble">'+
  (m.role==='assistant'?rich(m.text):'<p>'+h(m.text)+'</p>')+'</div>'+
  (m.role==='assistant'?'<div class="message-foot">'+h(m.model||'Assistant')+(m.braveContextUsed?' · Brave fresh context':m.webSearch?' · Public web search':'')+(m.retrieval?' · '+m.retrieval.selected+'/'+m.retrieval.totalRecords+' relevant stored records selected':'')+(m.error?' · Request failed':' · Sources require review')+'</div>'+
   (m.provenance?.integrityOk?'<details class="answer-provenance"><summary>Saved source and provider trace</summary>'+
    '<p class="help">Snapshot SHA '+h(m.provenance.snapshotSha256||'')+'</p>'+
    (m.provenance.evidence||[]).map(x=>'<button class="btn small" data-go-evidence="'+h(x.id)+'">'+h(x.label)+'</button>').join('')+
    (m.provenance.searchTrace?.providerFailures||[]).map(x=>'<div class="callout warn">'+h(x.provider)+' · '+h(x.status)+' · '+h(x.message||'Provider unavailable')+'</div>').join('')+
    '<p class="help">This trace records past retrieval, not universal coverage or verified identity.</p></details>':
    m.provenance?.integrityOk===false?'<div class="callout warn">Saved answer provenance integrity mismatch. Do not rely on this message.</div>':'')+
   (m.followUp?'<button class="btn small subtle" data-question="'+h(m.followUp)+'" style="justify-content:flex-start;white-space:normal;text-align:left">'+h(m.followUp)+' →</button>':'')+
   '<div class="citation-row">'+citations(m.ids)+'</div>'+
   (m.webSearch?(m.webLeads?.length?'<div class="source-item" style="margin-top:11px"><strong>Public web leads · analyst review required</strong><p>These URLs are suggested by the model and have not been independently fetched, validated or matched to this person.</p>'+
       m.webLeads.map((lead,leadIndex)=>'<div class="sourcehealth" style="display:block"><div style="margin-bottom:7px">'+link(lead.url,lead.title)+'</div><button type="button" class="btn small subtle" data-websave="'+idx+':'+leadIndex+'">Save as unverified lead</button></div>').join('')+
       '</div>':'<div class="callout warn">Groq returned no extractable source URLs. Ask for original HTTPS source links; do not treat uncited claims as evidence.</div>'):''):'')+'</div>').join(''):
  '<div class="empty"><div class="large">Tell me what you want to verify</div><p>For a common name, start with a city, organization, public handle or known profile. The assistant will ask for one distinguishing clue rather than invent a biography.</p></div>';
 const needsConsent=!c.ai_opt_in&&canRemote?
  '<div class="callout warn"><strong>Remote AI is currently off for this case.</strong><p>To activate GroqCloud, you must explicitly permit sending up to 35 saved source records and recent chat messages to the model provider when you send a message.</p><button type="button" data-consent class="btn primary small">Enable remote AI for this case</button></div>':
  '<div class="callout '+(c.ai_opt_in?'ok':'warn')+'">'+(c.ai_opt_in?'Remote-AI consent enabled for this case. Records are sent only when a remote provider is selected.':'Remote-AI consent disabled. A remote key is required for model reasoning.')+'</div>';
 const sourceCards=(s.case?.evidence||[]).slice(0,12).map(x=>'<div class="smart-source"><div><strong>'+h(x.label)+'</strong><p>'+h(x.provider)+' · '+h(x.status)+' · '+h(when(x.fetched_at))+'</p></div>'+link(x.source_url,'Original source')+'</div>').join('');
 const statusCard=(route||s.smartStage||s.smartIssues.length)?
 '<section class="panel smart-status"><div class="panel-head"><strong class="panel-title">Search coverage and source trace</strong>'+tag(s.smartStage?'researching':'candidate')+'</div>'+
 '<div class="panel-pad"><p class="page-sub">'+h(s.smartStage||'Search run completed; review candidate records and verify identities.')+'</p>'+
 (route?'<div class="badge-row"><span class="tag">Subject (tentative): '+h(route.subject)+'</span><span class="tag">Router: '+h(route.aiPlanned?'Groq-guided':'Rules fallback')+'</span><span class="tag">Selected APIs: '+h(route.providers.join(', ')||'Web index only')+'</span></div><p class="help">'+h(route.caveat)+'</p>':'')+
 (s.smartCoverage?'<div class="badge-row">'+Object.entries(s.smartCoverage).map(([k,v])=>'<span class="tag '+(v==='ok'?'ok':v==='error'?'bad':v==='partial'?'warn':'')+'">'+h(({structured:'Structured APIs',braveIndex:'Brave Web',braveContext:'Brave Context',groq:'Groq Analysis'})[k])+' · '+h(String(v).replaceAll('_',' '))+'</span>').join('')+'</div>':'')+
 s.smartIssues.map(x=>'<div class="callout warn">'+h(x)+'</div>').join('')+
 (s.sessionId&&s.messages.some(m=>m.role==='assistant'&&(m.webLeads||[]).length)?'<button class="btn small subtle" data-cross-engine>Check this question with a separate Groq browser search (uses API quota)</button>':'')+
 (s.crossEngineReport?'<div class="callout warn">Second engine returned '+h(String((s.crossEngineReport.secondaryCandidateUrls||[]).length))+' unverified URL suggestions. Publisher group overlap: '+h((s.crossEngineReport.overlappingPublisherGroups||[]).join(', ')||'none')+'. This is not factual corroboration.</div>':'')+'</div></section>':'';
 const sourcePanel='<details class="smart-sources" '+(s.messages.length?'':'open')+'><summary>Saved source leads · '+(s.case?.evidence||[]).length+' records (not verified)</summary><div class="smart-source-list">'+(sourceCards||'<div class="empty">No source records yet. A missing result is not proof a record does not exist.</div>')+'</div></details>';
 const publicPhotos=(s.portfolio?.items||[]).filter(x=>x.photoUrl&&/^https:\/\/avatars\.githubusercontent\.com\/u\/[0-9]+(?:[/?#]|$)/.test(x.photoUrl)).slice(0,5);
 const photosPanel=publicPhotos.length?'<section class="panel public-account-assets"><div class="panel-head"><strong class="panel-title">Publisher account images · identity unverified</strong><span class="tag">No photo identity matching</span></div><div class="account-asset-row">'+
 publicPhotos.map(x=>'<div class="account-asset"><img src="'+h(x.photoUrl)+'" alt="Candidate public account image; ownership not confirmed" loading="lazy" referrerpolicy="no-referrer"><strong>'+h(x.displayName)+'</strong>'+link(x.sourceUrl,'Original account')+'</div>').join('')+'</div></section>':'';
 const city=s.case?.context?.city||'';
 const mapNote=s.portfolioLocation;
 const mapPanel='<section class="intel-map-panel"><div class="intel-map-explainer"><div class="eyebrow">GEOSPATIAL CONTEXT</div><strong>Public geography, not person tracking</strong>'+
 (city?'<p>Entered public city or region: '+h(city)+'. A map plots only an approximate area.</p><button class="btn small" data-case-city-map>Show public city context</button>':
 '<p>No documented public city clue was entered. This investigation has no geocoded person location.</p><button class="btn small" data-nav="world">Open public global observations</button>')+
 (mapNote?'<p class="help">'+h(mapNote.notice)+'</p>':'')+'</div>'+
 (mapNote?'<div class="map" id="profile-map"><div class="map-fallback">Loading public city tiles…</div></div>':
 '<div class="intel-map-empty"><div class="map-fallback">Map available once a public city/region clue is provided and preview authorized.</div></div>')+'</section>';
 return statusCard+sourcePanel+photosPanel+mapPanel+'<div class="ai-layout"><section class="panel"><div class="panel-head"><div><div class="panel-title">Case research assistant</div><div class="panel-meta">Conversation, identity disambiguation and attributable evidence</div></div><span class="tag '+(p==='local'?'warn':'ok')+'">'+h(({local:'OFFLINE RULES · NO AI',groq:'GROQCLOUD · AI',grok:'XAI GROK · AI'})[p])+'</span></div>'+
 '<div id="chat-history" class="chat-history">'+messages+'</div>'+
 '<form id="ask-form" class="chat-composer"><textarea name="question" maxlength="2000" required placeholder="Ask a follow-up question about the retrieved evidence"></textarea><button type="submit" class="btn primary" '+(s.busy?'disabled':'')+'>'+(s.busy?'Analyzing…':'Send →')+'</button></form>'+
 '</section><aside class="panel"><div class="panel-head"><div class="panel-title">Research intelligence</div></div><div class="panel-pad input-stack">'+intro+
 history+'<label class="field-label" for="ai-provider">Reasoning mode</label><select id="ai-provider"><option value="local" '+(p==='local'?'selected':'')+'>Offline guidance · Not AI</option><option value="groq" '+(p==='groq'?'selected':'')+'>GroqCloud · '+(s.server.groqConfigured?'AI ready':'No API key')+'</option><option value="grok" '+(p==='grok'?'selected':'')+'>xAI Grok · '+(s.server.aiConfigured?'AI ready':'No API key')+'</option></select>'+
 needsConsent+'<div class="divider"></div><div class="eyebrow">SMART STARTERS</div>'+
 ['Summarize what these sources establish.','Which independent sources corroborate the main claims?','What information remains unverified?','Which records may concern different people?'].map(q=>'<button type="button" class="btn small subtle wide" style="white-space:normal;text-align:left;justify-content:flex-start" data-question="'+h(q)+'">'+h(q)+'</button>').join('')+
 '<label class="check" style="margin-top:6px"><input type="checkbox" id="research-brave" '+(s.braveContext?'checked':'')+' '+(p==='groq'&&c.ai_opt_in&&s.server.groqConfigured&&s.webProviders?.web?.configured?'':'disabled')+'> Retrieve fresh, attributed Brave context for this question</label>'+
 '<label class="check" style="margin-top:6px"><input type="checkbox" id="research-web" '+(s.webSearch?'checked':'')+' '+(p==='groq'&&c.ai_opt_in&&s.server.groqConfigured?'':'disabled')+'> Or use Groq-hosted browser search</label>'+
 '<p class="help">Choose one retrieval method. Brave passes recent public excerpts and actual source URLs to Groq without saving full third-party pages. They are unverified and consume your Brave/Groq quotas.</p>'+
 '<p class="help">Different people can share the same name. A model does not independently verify identity.</p></div></aside></div>';
}
function caseGraph(){return '<div class="panel"><div class="panel-head"><div class="panel-title">Source-linked provenance</div><div class="panel-meta">Connections are collection relationships, not confirmed identity links</div></div><div class="panel-pad"><div class="flow"><span class="step">'+h(s.case.case.query)+'</span><span class="arrow">→</span>'+(s.case.evidence||[]).slice(0,12).map(e=>'<span class="step">'+h(e.provider)+': '+h(e.label.slice(0,28))+'</span>').join('<span class="arrow">→</span>')+'</div><div class="insight"><h3>How to read this view</h3><p>These are case-to-record relationships. No unverified account has been merged into a person or company identity automatically.</p></div></div></div>'}
function caseFindings(){
 const inf=s.intel||{},a=inf.assessment||{},claims=inf.claims||[],metrics=inf.metrics||{},draft=s.draft?.draft||null;
 const excerpts=s.excerpts||[];
 const passages=excerpts.length?excerpts.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.label)+'</strong><blockquote style="font-size:.86rem">'+h(x.quote_text)+'</blockquote><div class="item-sub">'+h(x.interpretation)+'</div><div class="meta">'+link(x.source_url,'Original source')+' · '+h(x.captureIntegrityOk?'capture hash matched':'capture hash invalid')+' · '+h(x.latestCaptureUnchanged?'latest capture unchanged':'later capture differs')+'</div></div><span class="tag">'+h(x.review_status)+'</span></div>').join(''):
 '<div class="empty">No exact source-text quotations yet. Capture an approved public record, inspect its original text, and save a verbatim passage from Evidence.</div>';
 const claimItems=claims.length?claims.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.claim_text)+'</strong><div class="item-sub">'+h(x.stance)+' · '+link(x.source_url,x.label)+'</div></div>'+tag(x.status)+'</div>').join(''):
 '<div class="empty">No evidence-backed claims have been recorded. Open Evidence and attach statements to original source records.</div>';
 return '<div class="analyst-intro"><div><div class="eyebrow">DELIVERABLE / ANALYST-ASSESSED FINDINGS</div><h2>Write the answer, not a database dump.</h2><p>Explain what is known, what remains uncertain, and the evidence supporting each conclusion.</p></div><a class="btn small" target="_blank" rel="noopener" href="/api/cases/'+h(s.id)+'/report-v4.html">Preview evidence report ↗</a></div>'+
 '<div class="grid2"><section class="panel"><div class="panel-head"><div class="panel-title">Case assessment</div><span class="tag">'+h(a.status||'open')+'</span></div><div class="panel-pad input-stack"><label class="field-label">Create a source-grounded draft</label><div class="form-row"><select id="draft-provider" aria-label="Draft preparation mode"><option value="local">Captured-source ledger (no external AI)</option><option value="groq" '+(!(s.server.groqConfigured&&s.case.case.ai_opt_in)?'disabled':'')+'>Groq interpretation with captured-source excerpts</option></select><button type="button" class="btn small" data-draft-assessment '+(!excerpts.length?'disabled':'')+'>Prepare reviewable draft</button></div><p class="help">Requires a current exact-match quotation. A draft never marks a case completed and does not auto-save.</p>'+
 (draft?'<div class="callout ok">Unsaved source-grounded draft ('+h(s.draft.provider)+'). Review every sentence and press Save assessment to accept it.</div>':'')+'</div><form id="assessment-form" class="panel-pad input-stack"><label class="field-label">Executive summary</label><textarea name="executive_summary" maxlength="2400" placeholder="Answer the original question in language the reader can act upon…">'+h(draft?.executive_summary??a.executive_summary??'')+'</textarea><label class="field-label">Findings and analyst interpretation</label><textarea name="assessment" maxlength="5000" placeholder="Which evidence supports or disputes your conclusions?">'+h(draft?.assessment??a.assessment??'')+'</textarea><label class="field-label">Limitations and uncertainties</label><textarea name="limitations" maxlength="2000" placeholder="Missing sources, similar names, unverifiable claims, collection limits">'+h(draft?.limitations??a.limitations??'')+'</textarea><label class="field-label">Next recommended research actions</label><textarea name="next_actions" maxlength="2000" placeholder="Concrete next step to resolve remaining unknowns">'+h(draft?.next_actions??a.next_actions??'')+'</textarea><label class="field-label">Investigation status</label><select name="status">'+['open','researching','awaiting_review','completed'].map(v=>'<option value="'+v+'" '+(a.status===v?'selected':'')+'>'+h(String(v).replaceAll('_',' '))+'</option>').join('')+'</select><button class="btn primary">Save assessment</button><p class="help">Completed cases require substantive summary and analysis; case conclusions remain analyst opinions.</p></form></section>'+
 '<section class="panel"><div class="panel-head"><div class="panel-title">Attributed research claims</div><span class="tag">'+claims.length+' statements</span></div>'+claimItems+
 '<div class="panel-head"><div class="panel-title">Matched source passages</div><span class="tag">'+excerpts.length+' captured quotations</span></div>'+passages+'<div class="insight"><h3>Evidence quality check</h3><p>'+Number(metrics.reviewed||0)+' of '+Number(metrics.records||0)+' source records classified, '+Number(metrics.failedQueries||0)+' failed external queries and '+(s.candidates||[]).length+' candidate identity groups. A recorded claim still requires human checking that its source supports it.</p></div></section></div>';
}

function caseReports(){
 const id=h(s.id),ass=s.intel?.assessment||{};
 const ready=ass.status==='completed';
 return '<div class="analyst-intro"><div><div class="eyebrow">DELIVERABLES / REPRODUCIBLE SOURCE RECORDS</div><h2>Investigation report</h2><p>Your report includes the analyst assessment, candidate hypotheses, source-linked assertions, evidence and search coverage.</p></div></div>'+
 '<div class="grid2"><section class="panel panel-pad"><div class="badge-row">'+tag(ready?'ok':'draft')+'</div><h3>'+h(s.case.case.title)+'</h3><p class="page-sub">'+h(ass.executive_summary||'Draft: no executive assessment yet. Add an answer in Analyst findings before sharing this report.')+'</p><div class="reportlinks" style="margin:20px 0"><a class="btn primary" target="_blank" rel="noopener" href="/api/cases/'+id+'/report-v4.pdf">Download assessment PDF</a><a class="btn" target="_blank" rel="noopener" href="/api/cases/'+id+'/report-v4.html">Review HTML report ↗</a><a class="btn subtle" target="_blank" rel="noopener" href="/api/cases/'+id+'/report.json">Raw evidence JSON ↗</a></div><p class="help">A report may be a useful negative finding: insufficient evidence is a legitimate outcome. Do not invent identity certainty.</p></section>'+
 '<section class="panel panel-pad"><h3>Before distributing</h3><div class="input-stack"><div class="sourcehealth">Confirm the intended subject and distinguish namesakes.</div><div class="sourcehealth">Review whether each material claim is supported by the linked source.</div><div class="sourcehealth">Record unavailable sources, dates and contradictions.</div><div class="sourcehealth">Remove unsupported allegations and unnecessary personal information.</div></div></section></div>';
}

function caseActivity(){
 const chronological=(s.chronology?.items||[]).slice(0,40).map(x=>
  '<div class="item-row"><div class="row-main"><strong>'+h(x.title)+'</strong><div class="item-sub">'+
   link(x.sourceUrl,'Original source')+'</div><p class="meta">'+
  'Event: '+h(x.eventDate||'unknown')+' · Published: '+h(x.publicationDate||'unknown')+
  ' · Source observed: '+h(x.sourceObservedDate||'unknown')+
  ' · Retrieved: '+h(x.retrievalDate||'unknown')+' · Reviewed: '+h(x.reviewDate||'unreviewed')+'</p>'+
  (x.quotedPassage?'<blockquote>'+h(x.quotedPassage)+'</blockquote>':'')+
  '<p class="help">This event has not been independently authenticated.</p></div></div>').join('');
 const historyPanel='<section class="panel" style="margin-bottom:18px"><div class="panel-head"><strong class="panel-title">Source-linked chronology</strong><span class="tag warn">Event dates are not retrieval dates</span></div>'+
 (chronological||'<div class="empty">No dated source events yet; retrieval alone does not establish an event.</div>')+'</section>';
 const page=(s.cursorSources||[]).map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.label)+'</strong>'+
  '<div class="item-sub">'+h(x.provider)+' · '+h(x.status)+' · '+link(x.source_url,'Original page')+'</div></div></div>').join('');
 const paging='<section class="panel" style="margin-bottom:18px"><div class="panel-head"><strong class="panel-title">All source records · stable cursor pages</strong></div>'+
 (page||'<div class="empty">No case sources to page through.</div>')+
 '<div class="panel-pad">'+(s.cursorNext?'<button class="btn small" data-load-cursor>Load next 50 sources</button>':
 '<p class="help">No further saved source pages.</p>')+
 '<p class="help">New records will not shift an existing keyset page; records amended in-place may reorder.</p></div></section>';
 const runDiff=s.runEvolution?'<section class="panel"><div class="panel-head"><strong class="panel-title">Recorded source changes, not factual retractions</strong></div>'+
 (s.runEvolution.items||[]).slice(0,55).map(x=>'<div class="item-row"><div class="row-main">'+h(x.status)+
 ' · '+link(x.sourceUrl,'Original')+'<p class="meta">'+h(x.olderCapturedAt||'no old capture')+
 ' → '+h(x.newerCapturedAt||'no recent capture')+'</p></div></div>').join('')+
 '<p class="help">A source absent from a new search might still exist online.</p></section>':'';

 const history=s.researchRuns||[],recent=s.case.runs||[],data=s.changes||{},
   runs=data.runs||[],events=data.items||[],summary=data.summary||{};
 const note='<p class="help">'+h(data.warning||'Provider records are not a complete web archive. Absence from a single search does not mean deletion.')+'</p>';
 const selector='<div class="form-row" style="align-items:end"><label class="field-label">Compare with research run<select id="compare-previous-run">'+runs.filter(x=>x.run_id!==data.currentRunId).map(r=>'<option value="'+h(r.run_id)+'" '+(r.run_id===data.previousRunId?'selected':'')+'>'+h(when(r.started_at))+' · '+r.query_count+' queries</option>').join('')+'</select></label><button type="button" class="btn small" data-compare-runs>Compare source records</button><button type="button" class="btn small subtle" data-run-evolution>Inspect captured source hashes</button></div>';
 const changes='<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div class="panel-title">Source changes between research runs</div><span class="tag accent">'+Number(data.totalCompared||0)+' compared</span></div>'+
 '<div class="panel-pad">'+selector+'<div class="badge-row"><span class="tag ok">'+Number(summary.changed||0)+' changed</span><span class="tag">'+Number(summary.new_to_comparison||0)+' new to comparison</span><span class="tag warn">'+Number(summary.not_returned||0)+' not returned</span><span class="tag">'+Number(summary.unchanged||0)+' unchanged</span></div>'+
 (data.comparedSameQueryScope?'':'<p class="help">Different source queries were used. Compare with caution: different query coverage creates false differences.</p>')+note+'</div>'+
 (events.length?events.slice(0,80).map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.label)+'</strong><div class="item-sub">'+h(x.provider)+' · '+link(x.url,'Original source')+'</div>'+
 (x.change==='changed'?'<p class="help"><strong>Earlier:</strong> '+h(x.previousSummary)+' <strong>Now:</strong> '+h(x.summary)+'</p>':'')+
 '</div><span class="tag '+(x.change==='changed'?'warn':'')+'">'+h(x.change.replaceAll('_',' '))+'</span></div>').join(''):'<div class="empty">No versioned observations to compare. Run public-source research twice to obtain a meaningful comparison.</div>')+'</section>';
 return historyPanel+paging+runDiff+'<div class="analyst-intro"><div><div class="eyebrow">AUDITABILITY / RECORDED SOURCE DIFFERENCES</div><h2>What changed since the last research?</h2><p>Compare each recorded source version and investigate material changes; do not treat missing API results as withdrawn records.</p></div><button class="btn small" data-collect>Repeat research ↻</button></div>'+
 changes+'<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div class="panel-title">Individual source queries ('+history.length+')</div><span class="panel-meta">LATEST 250</span></div>'+
 (history.length?history.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.provider)+' · '+h(x.query_text)+'</strong><div class="item-sub">'+h(when(x.created_at))+' · '+h(x.message||'No details')+'</div></div><div class="badge-row">'+tag(x.status)+'<span class="tag">'+Number(x.returned_count)+' returned</span><span class="tag">'+Number(x.new_count)+' new</span></div></div>').join(''):
 '<div class="empty">No source queries executed. Begin from Overview.</div>')+'</section>'+
 '<section class="panel"><div class="panel-head"><div class="panel-title">Legacy collection activity</div></div>'+
 (recent.length?recent.slice(0,35).map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.provider)+'</strong><div class="item-sub">'+h(x.message||'No status')+' · '+h(when(x.ran_at))+'</div></div>'+tag(x.state)+'</div>').join(''):
 '<div class="empty">No prior collector activity.</div>')+'</section>';
}

function sources(){return heading('INTEGRATION REGISTRY','Source integrations','Connected APIs are separate from referenced upstream products.')+'<div class="insight"><h3>Honest source coverage</h3><p><strong>'+s.sources.length+'</strong> implemented adapters can return data. <strong>'+s.projects.length+'</strong> external products are reference links only, not installed tools. Each source can fail or return unverified candidates.</p></div><div class="section-row"><h2 class="section-heading">Integrated adapters</h2><span class="tag ok">Working connector implementations</span></div><div class="grid-equal">'+s.sources.map(x=>'<article class="panel panel-pad"><div class="badge-row">'+tag('configured')+'<span class="mono">'+h(x.scope.join(', '))+'</span></div><h3>'+h(x.title)+'</h3><p class="page-sub">'+h(x.description)+'</p><p class="help">'+h(x.terms)+'</p>'+link(x.url,'Provider documentation')+'</article>').join('')+'</div><div class="section-row"><h2 class="section-heading">External open-source references</h2><span class="tag warn">Not integrated</span></div><div class="grid-equal">'+s.projects.map(x=>'<article class="panel panel-pad"><span class="tag warn">Reference only</span><h3>'+h(x.name)+'</h3><p class="page-sub">'+h(x.strength)+'</p><p class="help">'+h(x.integration)+' · '+h(x.license)+'</p>'+link(x.repo,'Review repository')+(x.live?' · '+link(x.live,'Original site'):'')+'</article>').join('')+'</div>'}
function credentialRotationForm(forced=false){
 return '<section class="panel"><div class="panel-head"><strong class="panel-title">'+(forced?'Required password change':'Rotate your password')+'</strong></div>'+
 '<form id="credential-change-form" class="panel-pad input-stack"><label>Current password<input type="password" name="current_password" required autocomplete="current-password"></label>'+
 '<label>New unique password (16+ characters)<input type="password" name="new_password" minlength="16" maxlength="160" required autocomplete="new-password"></label>'+
 '<button class="btn primary" type="submit">Change password and sign out all sessions</button></form>'+
 '<p class="panel-pad help">Password-only authentication is not phishing-resistant MFA. All active sessions will be revoked after rotation.</p></section>';
}
function requiredPasswordChange(){
 return '<div class="page narrow">'+heading('ACCOUNT SECURITY','Password rotation required','An administrator reset your credentials. Change this temporary secret before accessing any case.')+credentialRotationForm(true)+'</div>';
}
function settings(){
 const providers=s.providerIssues?.items||[];
 const diagnosis='<section class="panel" style="margin:12px 0"><div class="panel-head"><strong class="panel-title">Source provider diagnostics</strong><button class="btn small" data-provider-issues>Refresh observations</button></div>'+
 '<p class="panel-pad help">Observed requests only: no uptime guarantee, no account keys or source search terms. Retry-after is unknown unless supplied by the upstream.</p>'+
 (providers.length?providers.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.provider)+'</strong><div class="item-sub">'+h(x.currentStatus)+' · Last success: '+h(x.lastSuccessAt||'not measured')+'</div><p class="help">'+h(x.nextStep)+'</p></div><span class="tag">'+h(x.lastStatusClass||'no error recorded')+'</span></div>').join(''):'<div class="panel-pad help">Use Refresh observations to inspect bounded source-health outcomes.</div>')+
 '</section>';
 return heading('OPERATIONS','Settings & security','Release '+h(s.server?.releaseVersion||'unavailable')+' · research pilot; provider contract/QA verification remains limited.')+credentialRotationForm()+diagnosis+'<div class="grid-equal"><section class="panel"><div class="panel-head"><div class="panel-title">Model configuration</div></div><div class="panel-pad">'+[['GroqCloud',s.server.groqConfigured],['xAI Grok',s.server.aiConfigured],['Brave public-web search',s.webProviders?.web?.configured===undefined?'not_checked':s.webProviders.web.configured],['TfL camera feed',s.server.tflConfigured]].map(x=>'<div class="sourcehealth">'+h(x[0])+tag(x[1]==='not_checked'?'not_checked':(x[1]?'configured':'not_configured'))+'</div>').join('')+'<p class="help">Credentials are stored on Render, never in this browser. A configured key does not guarantee provider availability or quota.</p><button class="btn warn" data-logout>Sign out</button><div class="divider"></div><p class="help">User accounts and case ownership are stored in the database. Non-admin analysts can access only their own cases.</p></div></section><section class="panel"><div class="panel-head"><div class="panel-title">Current release scope</div></div><div class="panel-pad"><div class="callout warn">Render PostgreSQL Free is time-limited and is not enterprise-durable. Backups, retention controls, MFA/SSO and an independent security audit remain necessary before real customer investigations.</div><p class="page-sub" style="margin-top:15px">Public sources may be stale, inaccurate, or unavailable. Do not infer risk scores or automatic identity verification.</p><a class="btn" href="/api/docs" target="_blank" rel="noopener">API reference ↗</a></div></section></div>'}
function administration(){
 if(s.user?.role!=='admin')return '<div class="callout warn">Administrator access required.</div>';
 return heading('SECURITY OPERATIONS','Analyst accounts','Create individual access instead of sharing administrator credentials.')+
 '<div class="grid2"><div class="panel"><div class="panel-head"><strong class="panel-title">Users</strong></div>'+
 (s.users?.length?s.users.map(x=>'<div class="item-row"><div class="row-main"><div class="item-title">'+h(x.username)+'</div><div class="item-sub">'+h(x.role)+' · '+(x.active?'active':'disabled')+'</div></div>'+tag(x.active?'ok':'error')+'</div>'+
 '<details class="panel-pad"><summary>Manage credentials and access</summary>'+
 '<form class="input-stack" data-admin-reset="'+h(x.id)+'"><label>Administrator password<input type="password" name="administrator_password" autocomplete="current-password" required></label><label>Temporary password (16+ characters)<input type="password" name="temporary_password" minlength="16" maxlength="160" autocomplete="new-password" required></label><button class="btn small" type="submit">Reset password; revoke sessions</button></form>'+
 '<form class="input-stack" data-admin-status="'+h(x.id)+'"><label>Administrator password<input type="password" name="administrator_password" autocomplete="current-password" required></label><label>Account status<select name="active"><option value="true" '+(x.active?'selected':'')+'>Enabled</option><option value="false" '+(!x.active?'selected':'')+'>Disabled</option></select></label><button class="btn small warn" type="submit">Apply account status</button></form></details>').join(''):'<div class="empty">No user records loaded.</div>')+
 '</div><section class="panel"><div class="panel-head"><strong class="panel-title">Create account</strong></div><form class="panel-pad input-stack" id="user-form"><input name="username" required minlength="3" maxlength="60" placeholder="Username"><input name="password" type="password" minlength="12" required autocomplete="new-password" placeholder="Initial password (12+ characters)"><select name="role"><option value="analyst">Analyst</option><option value="admin">Administrator</option></select><button class="btn primary">Create user</button><p class="help">Share the password securely; it is never returned by the API.</p></form></section></div>';
}
const safeTflStill=x=>typeof x==='string'&&/^https:\/\/s3-eu-west-1\.amazonaws\.com\/jamcams\.tfl\.gov\.uk\/[0-9.]+\.jpg$/i.test(x);
function world(){return heading('GEO INTELLIGENCE','World intelligence','Source-labeled natural events and public-authority camera metadata; not universal live tracking.')+'<div class="toolbar" style="margin:20px 0"><label class="field-label" style="margin:0">Source layer</label><select id="geo-feed">'+[['earthquakes','USGS · Earthquakes'],['nasa','NASA · Natural events'],['caltrans','Caltrans · Cameras (metadata)'],['tfl','TfL · London JamCams']].map(([id,name])=>'<option value="'+id+'" '+(s.feed===id?'selected':'')+'>'+name+'</option>').join('')+'</select><button class="btn small" data-refresh>Refresh source</button><span class="tag">'+s.geo.length+' records</span></div>'+
'<div class="toolbar" style="margin:0 0 12px"><label class="check"><input type="checkbox" id="satellite-toggle" '+(s.satelliteEnabled?'checked':'')+'> NASA GIBS satellite base imagery</label>'+
'<label class="field-label" for="satellite-date">Image date (UTC)</label><input style="width:190px;padding:7px 9px" type="date" id="satellite-date" min="2012-01-01" max="'+new Date().toISOString().slice(0,10)+'" value="'+h(s.satelliteDate)+'"><span class="help">Archival daily publisher tiles; coverage and clouds vary. Not a live camera or real-time satellite.</span></div>'+
'<div class="world-layout"><section class="panel"><div class="panel-head"><div class="panel-title">Geographic observations</div><span class="panel-meta">'+h(s.feed.toUpperCase())+'</span></div><div class="map" id="geo-map"><div class="map-fallback">Loading map library…</div></div></section><section class="panel"><div class="panel-head"><div class="panel-title">Observed records</div>'+tag(s.geoStatus)+'</div><div class="world-list">'+(s.geoError?'<div class="callout warn">'+h(s.geoError)+'</div>':'')+(s.geo.length?s.geo.slice(0,100).map((x,k)=>'<div class="world-item"><strong>'+h(x.name||'Event')+'</strong><span>'+h(x.provider)+' · '+h(when(x.observedAt))+'</span><div style="margin-top:10px">'+link(x.url,'Official source')+' <button class="btn small subtle" data-locate="'+k+'">Locate</button>'+
(s.feed==='tfl'&&safeTflStill(x.feedUrl)?' <button type="button" class="btn small" data-camera-preview="'+k+'">View public still</button>':'')+
'</div>'+(s.feed==='tfl'&&s.cameraSelection===k&&safeTflStill(x.feedUrl)?'<figure class="camera-still"><img alt="Official public road traffic still; not a person location" loading="lazy" referrerpolicy="no-referrer" src="'+h(x.feedUrl)+'"><figcaption>'+h(x.mediaStatus||'Capture time unknown')+' · Powered by TfL Open Data</figcaption></figure>':'')+'</div>').join(''):'<div class="empty">No records available for this source. Source errors are shown explicitly.</div>')+'</div></section></div><div class="insight"><h3>Map provenance</h3><p>Only the selected official feed populates this map. OSIRIS, World Monitor, God’s Eye View, Argus and CamForge are reference links, not live merged services. Publisher camera stills are available only on demand, without independently verified capture times. Camera imagery cannot establish an individual location.</p></div>'}
let map=null,marks={};
function drawMap(){const el=document.getElementById('geo-map');if(!el)return;if(map){try{map.remove()}catch{}map=null}if(!window.L){el.innerHTML='<div class="map-fallback">Map library unavailable. Use the source list instead.</div>';return}
map=window.L.map(el,{worldCopyJump:true}).setView([18,8],2);window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:17}).addTo(map);
if(s.satelliteEnabled&&/^20[12][0-9]-[0-9]{2}-[0-9]{2}$/.test(s.satelliteDate)){
 window.L.tileLayer('https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/'+s.satelliteDate+'/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg',
  {maxZoom:9,opacity:.78,attribution:'Imagery: NASA GIBS · requested date '+s.satelliteDate+' (availability unverified)'}).addTo(map);
}
const bounds=[];marks={};s.geo.forEach((x,k)=>{const lat=Number(x.lat),lon=Number(x.lon);if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)return;const marker=window.L.circleMarker([lat,lon],{radius:5,color:'#a2b4ff',weight:1.4,fillOpacity:.7}).addTo(map);marker.bindPopup('<strong>'+h(x.name||'Observation')+'</strong><p>'+h(x.provider)+'</p>'+link(x.url,'Original source'));marks[k]=marker;bounds.push([lat,lon])});if(bounds.length&&bounds.length<400)map.fitBounds(bounds,{padding:[32,32],maxZoom:6})}
function render(){if(!s.user){login();return}if(s.user.must_change_password){app.innerHTML=requiredPasswordChange();return}app.innerHTML=frame(({home,cases,case:casePage,world,sources,settings,admin:administration}[s.where]||home)());if(s.where==='world'||s.where==='home')setTimeout(drawMap,0);if(s.where==='case'&&s.portfolioLocation&&(s.tab==='portfolio'||s.tab==='assistant'))setTimeout(drawPortfolioMap,0);if(s.where==='case'&&s.tab==='assistant'){const e=document.getElementById('chat-history');if(e)e.scrollTop=e.scrollHeight}}
async function refreshCases(){
 const params={q:s.caseSearch,status:s.caseStatus,subject_type:s.caseType,
  owner:s.caseOwner,date_from:s.caseFrom,date_to:s.caseTo,sort:s.caseSort,
  page:s.casePage,page_size:s.casePageSize};
 const defaultFilters=!params.q&&params.status==='all'&&params.subject_type==='all'&&!params.owner&&!params.date_from&&!params.date_to&&params.sort==='newest'&&params.page===1&&params.page_size===25;
 const request=defaultFilters?'/api/cases':'/api/cases?'+Object.entries(params).filter(([key,val])=>val!==''&&val!==null).map(([key,val])=>encodeURIComponent(key)+'='+encodeURIComponent(val)).join('&');
 const [ca,ov]=await Promise.all([api(request),api('/api/overview')]);
 s.cases=ca.items||[];s.overview=ov;s.caseTotal=ca.total??s.cases.length;s.caseTotalPages=ca.totalPages??Math.max(1,Math.ceil(s.caseTotal/s.casePageSize));
}
async function openCase(id){if(typeof window!=='undefined'&&window.history?.replaceState)window.history.replaceState(null,'','/?case='+encodeURIComponent(id));s.where='case';s.id=id;s.tab='overview';s.messages=[];s.sessionId=null;s.conversations=[];s.selected=null;s.webSearch=false;s.evidenceSelected=[];s.evidenceSearch='';s.evidenceFilter='all';s.lastResearch=null;s.captures={};s.versions={};s.changes=null;s.jobs=[];s.job=null;s.tasks=[];s.taskAssignees=[];s.taskTotal=0;s.taskHistory={};s.members=null;s.duplicateSources=null;s.identityQuality=null;s.excerpts=[];s.identity=null;s.draft=null;s.portfolio=null;s.portfolioLocation=null;s.triage=null;s.researchPlan=null;s.queryExplain=null;s.readiness=null;s.searchProgress=null;s.dossier=null;s.claimDetail=null;s.chronology=null;s.cursorSources=[];s.cursorNext=null;s.runEvolution=null;s.budget=null;s.reviewedDraft=null;s.refinements=null;s.dossierSort='relevance';s.dossierStatus='all';s.dossierClass='all';s.searchHistory=[];s.candidates=[];s.intel=null;s.smartPlan=null;s.smartStage='';s.smartIssues=[];s.smartCoverage=null;await fetchCase();
 try{const saved=await api('/api/cases/'+id+'/search-plan');if(saved.available){s.smartPlan=saved.plan;s.smartQuestion=saved.question}}catch(e){/* Legacy case; no versioned plan */}s.provider=(s.server.groqConfigured&&s.case.case.ai_opt_in)?'groq':'local';await loadResearchState();render()}
async function loadResearchState(){
 // Initial response is one authorized request. Specialist tabs refresh their
 // own data when visited; no hidden background provider calls are started.
 const all=await api('/api/cases/'+s.id+'/initial-view?depth='+encodeURIComponent(s.depth));
 s.triage=all.triage;
 s.conversations=all.conversations?.items||[];
 s.researchPlan=all.researchPlan;
 s.researchRuns=all.runs?.items||[];
 s.intel=all.intelligence;
 s.webProviders=all.webProviders;
 s.candidates=all.candidates?.items||[];
 s.queryExplain=all.queryExplain;
 s.readiness=all.readiness;
 s.searchProgress=all.searchProgress;
 s.dossier=all.dossier;
 s.budget=all.budget;
 s.reviewedDraft=all.draft;
 s.refinements=all.refinements;
 if(s.conversations.length)await loadConversation(s.conversations[0].id);
}
async function loadAdvancedCaseState(tab){
 const id=s.id;
 // No speculative cross-case cache: data is read only for the authorized case.
 if(tab==='portfolio'){s.portfolio=await api('/api/cases/'+id+'/public-portfolio');return}
 const endpoint={
  investigate:['jobs'],
  tasks:['tasks','task-assignees'],
  team:['members','task-assignees'],
  candidates:['candidates','identity-analysis','identity-quality'],
  evidence:['duplicate-sources','excerpts'],
  findings:['intelligence','excerpts','candidates'],
  reports:['intelligence','candidates'],
  activity:['search-history','changes','research-history','chronology','evidence-cursor'],
 }[tab]||[];
 const result=await Promise.all(endpoint.map(name=>api('/api/cases/'+id+'/'+name)));
 endpoint.forEach((name,i)=>{
  const value=result[i];
  if(name==='jobs')s.jobs=value.items||[];
  else if(name==='tasks'){s.tasks=value.items||[];s.taskTotal=value.total||0}
  else if(name==='task-assignees')s.taskAssignees=value.items||[];
  else if(name==='members')s.members=value;
  else if(name==='candidates')s.candidates=value.items||[];
  else if(name==='identity-analysis')s.identity=value;
  else if(name==='identity-quality')s.identityQuality=value;
  else if(name==='duplicate-sources')s.duplicateSources=value;
  else if(name==='excerpts')s.excerpts=value.items||[];
  else if(name==='intelligence')s.intel=value;
  else if(name==='search-history')s.searchHistory=value.items||[];
  else if(name==='changes')s.changes=value;
  else if(name==='research-history')s.researchRuns=value.items||[];
  else if(name==='chronology')s.chronology=value;
  else if(name==='evidence-cursor'){s.cursorSources=value.items||[];s.cursorNext=value.nextCursor||null;}
 });
}
async function loadConversation(id){
 const result=await api('/api/cases/'+s.id+'/conversations/'+id);
 s.sessionId=result.session.id;
 s.messages=(result.messages||[]).map(m=>({
   role:m.role,text:m.text,model:m.provider,ids:m.ids||[],webLeads:m.webLeads||[],
   webSearch:!!m.webLeads?.length,provenance:m.provenance||null
 }));
 render();
}
async function fetchCase(){const [ca,brief]=await Promise.all([api('/api/cases/'+s.id),api('/api/cases/'+s.id+'/brief')]);s.case=ca;s.brief=brief;render()}
async function collect(){
 if(s.busy)return;
 s.busy=true;render();
 try{
  const out=await api('/api/cases/'+s.id+'/research',{method:'POST',body:{depth:s.depth}});
  s.lastResearch=out;
  await Promise.all([fetchCase(),refreshCases()]);
  await loadResearchState();
  toast(out.returned+' records returned, '+out.new+' newly saved; '+out.errors+' errors.',out.errors>0);
 }finally{s.busy=false;render()}
}

async function saveClientStageError(caseId,stage,question,outcome='error'){
 try{await api('/api/cases/'+caseId+'/client-stage-events',{method:'POST',
   body:{stage,outcome,reason:'provider_error',original_question:question.slice(0,200)}});
 }catch(err){s.smartIssues.push('Source stage diagnostic could not be persisted. Verify provider logs independently.');}
}

async function smartLaunch(form){
 const d=Object.fromEntries(new FormData(form).entries());
 const question=String(d.question||'').trim();
 const freshness=['pd','pw','pm','py'].includes(d.freshness)?d.freshness:'all';
 const country=['US','IN','GB','CA','AU','DE','FR'].includes(d.country)?d.country:'US';
 const search_lang=['en','hi','bn','ta','te','mr','de','fr'].includes(d.search_lang)?d.search_lang:'en';
 const site=String(d.site||'').trim();
 if(site&&!/^[A-Za-z0-9][A-Za-z0-9.-]{1,76}\.[A-Za-z]{2,15}$/.test(site))throw Error('Enter a public website domain, without URL or path.');
 const phrase=String(d.exact_phrase||'').replace(/"/g,'').trim().slice(0,65);
 const excluded=String(d.exclude||'').replace(/[^A-Za-z0-9_-]/g,'').slice(0,30);
 const webQuestion=(question+(phrase?' "'+phrase+'"':'')+(site?' site:'+site:'')+(excluded?' -'+excluded:'')).slice(0,200);
 if(!question||s.busy)return;
 // No remote AI, external search, or case creation occurs in this preflight.
 const preflight=await api('/api/search/preflight?question='+encodeURIComponent(question)+
    (d.subject_type?'&subject_type='+encodeURIComponent(d.subject_type):''));
 const requiresReview=preflight.requiresHumanReview||
     (!d.subject_type&&preflight.typeConfidence==='tentative_low');
 if(requiresReview&&form.dataset.preflightConfirmed!==question){
   const select=form.querySelector('[name="subject_type"]');
   if(select&&!select.value)select.value=preflight.suggestedType;
   const panel=form.querySelector('#smart-preflight-review');
   if(panel)panel.innerHTML='<div class="callout warn"><strong>Confirm the tentative research target before creating a case.</strong>'+
       '<p>'+h(preflight.reason)+' Suggested target: '+h(preflight.suggestedSubject)+
       ' · Type: '+h(preflight.suggestedType)+'. Edit the category above and select Search again to confirm.</p>'+
       '<p class="help">This preview made no external searches and created no case.</p></div>';
   form.dataset.preflightConfirmed=question;
   return;
 }
 const allowedPurposes={public_research:'Authorized public-source research and record verification',
 supplier:'Authorized supplier or organizational due-diligence assessment',
 security:'Authorized defensive security assessment of public assets',
 academic:'Authorized academic and public-record verification'};
 s.busy=true;s.smartStage='Planning relevant public sources';s.smartIssues=[];s.smartQuestion=question;s.smartCoverage={structured:'not_run',braveIndex:'not_run',braveContext:'not_run',groq:'not_run'};render();
 try{
  const started=await api('/api/search/start',{method:'POST',body:{
    question,purpose:(d.purpose||allowedPurposes[d.research_purpose]||allowedPurposes.public_research),
    authority_confirmed:!!d.authority,ai_opt_in:!!d.ai_opt_in,
    subject_type:d.subject_type||null,city:d.city||'',organization:d.organization||'',
    profession:d.profession||'',public_handle:d.public_handle||''
  }});
  s.smartPlan=started.plan;s.id=started.id;s.where='case';s.tab='assistant';
  s.messages=[];s.conversations=[];s.sessionId=null;s.case=null;s.brief=null;
  s.provider=(started.groqConfigured&&d.ai_opt_in)?'groq':'local';
  s.braveContext=!!(started.braveConfigured&&started.groqConfigured&&d.ai_opt_in);
  s.webSearch=false;
  const providerInfo=await api('/api/research/providers');
  s.webProviders=providerInfo;
  await Promise.all([fetchCase(),refreshCases()]);
  if(started.plan?.deferExternalSearch || (started.plan?.subjectType==='person' && started.plan?.needsClarification)){
    const prompt=started.plan.clarification||'Provide an identifying public clue before searching a single given name.';
    s.smartStage='Clarification required before external research';
    s.smartIssues.push(prompt);
    s.smartCoverage.structured='skipped clarification';
    s.smartCoverage.braveIndex='skipped clarification';
    s.smartCoverage.braveContext='skipped clarification';
    s.smartCoverage.groq='skipped clarification';
    s.messages=[{role:'user',text:question},{role:'assistant',text:prompt+
      ' No external provider was queried. This is a search-target clarification, not proof of identity.',model:'Source planner'}];
    s.provider='local';
    return;
  }
  const providers=started.plan.providers||[];
  if(providers.length){
    s.smartStage='Checking '+providers.join(', ')+' public sources';render();
    try{
      const collected=await api('/api/cases/'+started.id+'/collect',{method:'POST',body:{providers}});
      const failures=(collected.results||[]).filter(r=>r.status==='error');
      s.smartCoverage.structured=failures.length?'partial':'ok';
      if(failures.length)s.smartIssues.push(failures.length+' structured source(s) unavailable; check original source coverage.');
    }catch(error){
      s.smartCoverage.structured='error';s.smartIssues.push('Some structured sources could not be collected: '+error.message);await saveClientStageError(started.id,'structured',question);
    }
  }
  if(started.braveConfigured){
    s.smartStage='Retrieving attributable results from Brave Search';render();
    try{
      const indexed=await api('/api/cases/'+started.id+'/web-discovery',{
        method:'POST',body:{query:webQuestion,depth:3,pages:2,adaptive:true,lens:started.plan.searchLens||'general',consent:true,freshness,country,search_lang}});
      s.smartCoverage.braveIndex=indexed.errors?'partial':indexed.returned?'ok':'empty';
      s.smartCoverage.braveScope=indexed.stopReason||'unknown';
      s.smartCoverage.braveQueries=indexed.executedQueries||0;
      if(indexed.errors)s.smartIssues.push('Brave web discovery reported '+indexed.errors+' provider error(s).');
    }catch(error){
      s.smartCoverage.braveIndex='error';s.smartIssues.push('Public web discovery unavailable: '+error.message);await saveClientStageError(started.id,'brave_index',question);
    }
  }
  await fetchCase();
  // One bounded refinement round only when the first pass has no records,
  // the analyst explicitly enabled remote analysis, and the backend planner
  // named relevant structured sources. This is not a completeness claim.
  if(d.ai_opt_in&&providers.length&&!(s.case?.evidence||[]).length){
    s.smartStage='Evaluating empty coverage and trying one distinct source';render();
    try{
      const work=await api('/api/cases/'+started.id+'/jobs',{
        method:'POST',body:{objective:question+' - seek an independent public source',
          mode:'guided',allow_web:false,consent:false,max_steps:1}});
      const rerun=await api('/api/cases/'+started.id+'/jobs/'+work.id+'/run-bounded',{
        method:'POST',body:{steps:1,consent:true}});
      const tested=rerun.executedSteps||[];
      if(tested.some(x=>x.status==='error'))
        s.smartIssues.push('Secondary provider unavailable; first-pass evidence remains incomplete.');
      await fetchCase();
    }catch(e){
      s.smartIssues.push('Bounded second-pass lookup could not complete: '+e.message);
    }
  }
  try{s.portfolio=await api('/api/cases/'+started.id+'/public-portfolio')}catch(err){s.smartIssues.push('Public profile assets unavailable: '+err.message)}
  s.smartStage=s.provider==='groq'?'Grounding Groq in collected records and fresh Brave context':'Organizing saved public-source leads';
  s.messages=[{role:'user',text:question}];render();
  if(s.provider==='groq'){
    try{
      let response;
      try{
        response=await api('/api/cases/'+started.id+'/chat',{method:'POST',
          body:{question:webQuestion,provider:'groq',brave_context:s.braveContext,web_search:false,freshness,country,search_lang,save_bounded_excerpts:!!d.save_bounded_excerpts}});
      }catch(err){
        if(!s.braveContext)throw err;
        s.smartCoverage.braveContext='error';s.smartIssues.push('Fresh Brave-to-Groq context failed: '+err.message+'; AI retried with saved evidence only.');await saveClientStageError(started.id,'brave_context',question,'fallback');
        response=await api('/api/cases/'+started.id+'/chat',{method:'POST',
          body:{question:webQuestion,provider:'groq',brave_context:false,web_search:false,freshness,country,search_lang}});
      }
      s.smartCoverage.groq='ok';if(response.braveContextUsed)s.smartCoverage.braveContext=response.freshSourcesCount?'ok':'empty';
      s.sessionId=response.sessionId||null;
      s.messages.push({role:'assistant',text:response.answer,model:response.model,
        ids:response.evidenceIds||[],followUp:response.followUp||'',webSearch:!!response.webSearch,
        braveContextUsed:!!response.braveContextUsed,webLeads:response.webLeads||[],
        retrieval:response.retrieval||null});
      s.conversations=(await api('/api/cases/'+started.id+'/conversations')).items||[];
    }catch(err){
      s.smartCoverage.groq='error';s.smartIssues.push('AI summary unavailable: '+err.message);await saveClientStageError(started.id,'groq_analysis',question);
      s.messages.push({role:'assistant',text:'The AI answer is unavailable. Open the source records below and review each original. A search result alone does not identify a person.',model:'Source-only fallback'});
    }
  }else{
    const amount=(s.case?.evidence||[]).length;
    s.messages.push({role:'assistant',text:'Found '+amount+' saved public-source candidates. Groq analysis was not enabled for this case. Review the Sources tab and original URLs; no profile or person identity has been established.',model:'Source-only mode'});
  }
  s.smartStage='';s.tab='assistant';
 }finally{s.busy=false;render()}
}

async function launch(form){const d=Object.fromEntries(new FormData(form).entries());s.busy=true;render();try{const ca=await api('/api/cases',{method:'POST',body:{title:modes[s.mode].name+' · '+d.query.trim(),subject_type:s.mode,query:d.query.trim(),purpose:d.purpose.trim(),authority_confirmed:!!d.authority,ai_opt_in:!!d.ai_opt_in,city:d.city||'',organization:d.organization||'',profession:d.profession||'',public_handle:d.public_handle||''}});await refreshCases();await openCase(ca.id);s.busy=false;try{await collect()}catch(err){toast('Case created, but source lookup failed: '+err.message,true)}}finally{s.busy=false;render()}}
async function loadGeo(){s.cameraSelection=-1;s.geoStatus='loading';s.geoError='';render();try{const out=await api(['earthquakes','nasa'].includes(s.feed)?'/api/geo/events?feed='+s.feed:'/api/geo/cameras?provider='+(s.feed==='caltrans'?'caltrans':'tfl'));s.geo=out.items||[];s.geoStatus=out.status||'ok';s.geoError=out.note||out.message||''}catch(err){s.geo=[];s.geoError=err.message;s.geoStatus='unavailable'}render()}
async function refreshDossier(){
 const qs=new URLSearchParams({sort:s.dossierSort,status:s.dossierStatus,source_class:s.dossierClass});
 s.dossier=await api('/api/cases/'+s.id+'/dossier?'+qs.toString());
 render();
}
async function init(){const auth=await api('/api/auth/me');s.user=auth.user;s.server=auth;if(auth.mustChangePassword){s.user.must_change_password=true;render();return}const [ca,ov,so,pr,cap]=await Promise.all([api('/api/cases'),api('/api/overview'),api('/api/sources'),api('/api/projects'),api('/api/capabilities')]);s.cases=ca.items||[];s.overview=ov;s.sources=so.items||[];s.projects=pr.items||[];s.capabilities=cap;if(s.user?.role==='admin')s.users=(await api('/api/users')).items;s.where='home';render();const fromUrl=(typeof window!=='undefined'&&window.location)?new URLSearchParams(window.location.search).get('case'):null;
if(fromUrl&&/^[a-f0-9]{24}$/.test(fromUrl)){try{await openCase(fromUrl)}catch(e){toast('Saved case could not be reopened: '+e.message,true)}}
}
document.addEventListener('click',async e=>{const t=e.target.closest('button[data-nav],button[data-mode],button[data-tab],button[data-open],button[data-evidence],button[data-collect],button[data-add],button[data-refresh],button[data-locate],button[data-question],button[data-consent],button[data-webstart],button[data-websave],button[data-newchat],button[data-go-evidence],button[data-task-history],button[data-member-remove],button[data-deletecase],button[data-case-page],button[data-case-reset],button[data-web-discover],button[data-capture-source],button[data-show-captures],button[data-version-history],button[data-compare-runs],button[data-job-select],button[data-job-run],button[data-job-recover],button[data-identity-pair],button[data-draft-assessment],button[data-logout],button[data-profile-map],button[data-profile-search],button[data-home-load-events],button[data-case-city-map],button[data-camera-preview],button[data-cross-engine],button[data-resume-saved-plan],button[data-explain-claim],button[data-approve-report-draft],button[data-use-refinement],button[data-load-cursor],button[data-run-evolution],button[data-provider-issues]');if(!t)return;try{
if(t.dataset.nav){s.where=t.dataset.nav;if(typeof window!=='undefined'&&window.history?.replaceState)window.history.replaceState(null,'','/');render();if(s.where==='world'&&s.geoStatus==='idle')await loadGeo()}
else if(t.dataset.mode){s.mode=t.dataset.mode;s.where='home';render();document.getElementById('query')?.focus()}
else if(t.dataset.tab){s.tab=t.dataset.tab;await loadAdvancedCaseState(s.tab);render()}
else if(t.hasAttribute('data-provider-issues')){
 s.providerIssues=await api('/api/research/provider-issues');
 render();
 toast('Source diagnostics refreshed; unobserved providers remain unknown.');
}
else if(t.hasAttribute('data-resume-saved-plan')){
 const continuation=await api('/api/cases/'+s.id+'/resume-saved-research',{method:'POST',body:{}});
 s.job=await api('/api/cases/'+s.id+'/jobs/'+continuation.jobId);
 s.tab='investigate';
 await loadAdvancedCaseState('investigate');
 render();
 toast(continuation.reusedExisting?'Existing saved research job restored.':'New bounded research continuation saved. Choose Continue to execute provider steps.');
}
else if(t.hasAttribute('data-approve-report-draft')){
 const r=await api('/api/cases/'+s.id+'/reviewed-report-draft/accept',{method:'POST',
   body:{review_token:t.dataset.approveReportDraft,reviewer_confirmed:true}});
 s.intel=await api('/api/cases/'+s.id+'/intelligence');
 s.reviewedDraft=await api('/api/cases/'+s.id+'/reviewed-report-draft');
 render();toast('Structured report saved as awaiting independent review, not approved.');
}
else if(t.hasAttribute('data-use-refinement')){
 s.tab='assistant';render();const area=document.querySelector('#ask-form textarea');
 if(area){area.value=t.dataset.useRefinement;area.focus()}
}
else if(t.hasAttribute('data-load-cursor')){
 if(!s.cursorNext)return;
 const page=await api('/api/cases/'+s.id+'/evidence-cursor?limit=50&cursor='+encodeURIComponent(s.cursorNext));
 s.cursorSources=[...(s.cursorSources||[]),...(page.items||[])];
 s.cursorNext=page.nextCursor;render();
}
else if(t.hasAttribute('data-run-evolution')){
 const newer=s.changes?.currentRunId,older=document.getElementById('compare-previous-run')?.value;
 if(!newer||!older)throw Error('Run at least two source searches to compare their saved observations.');
 s.runEvolution=await api('/api/cases/'+s.id+'/run-source-evolution?older_run='+encodeURIComponent(older)+
   '&newer_run='+encodeURIComponent(newer));
 render();
}
else if(t.hasAttribute('data-explain-claim')){
 s.claimDetail=await api('/api/cases/'+s.id+'/claims/'+encodeURIComponent(t.dataset.explainClaim)+'/explain');
 s.tab='overview';render();
}
else if(t.hasAttribute('data-cross-engine')){
 if(!s.sessionId)throw Error('Run a source-grounded conversation before a second-engine check.');
 if(typeof window.confirm==='function'&&!window.confirm('Run a second Groq browser search? This sends your query to the provider and consumes additional API quota. URL overlap is not verification.'))return;
 s.crossEngineReport=await api('/api/cases/'+s.id+'/cross-engine-check',{
  method:'POST',body:{session_id:s.sessionId,question:(s.smartQuestion||s.case?.case?.query||'Public source verification').slice(0,500),consent:true}});
 render();toast('Second-source suggestions returned. Verify actual publisher pages before corroborating.');
}
else if(t.hasAttribute('data-home-load-events')){s.feed='earthquakes';await loadGeo()}
else if(t.hasAttribute('data-profile-search')){
 if(!s.webProviders?.web?.configured)throw Error('Set BRAVE_SEARCH_API_KEY privately in Render before searching professional public web.');
 if(typeof window.confirm==='function'&&!window.confirm('Send this case subject and public context clues to Brave Search (up to four searches)? Results will be saved as unverified leads.'))return;
 const focus=document.getElementById('profile-lens')?.value||'general';
 const out=await api('/api/cases/'+s.id+'/web-discovery',{method:'POST',body:{depth:4,lens:focus,consent:true}});
 await fetchCase();s.portfolio=await api('/api/cases/'+s.id+'/public-portfolio');
 render();toast(out.returned+' public web leads returned, '+out.new+' newly saved, '+out.errors+' provider errors.',out.errors>0);
}
else if(t.hasAttribute('data-case-city-map')){s.portfolioLocation=await api('/api/cases/'+s.id+'/public-location-preview',{method:'POST',body:{consent:true}});render();}
else if(t.hasAttribute('data-profile-map')){s.portfolioLocation=await api('/api/cases/'+s.id+'/public-location-preview',{method:'POST',body:{consent:true}});render();toast('Approximate city clue displayed; not a person location.')}
else if(t.dataset.open)await openCase(t.dataset.open)
else if(t.hasAttribute('data-case-page')){
 const next=Number(t.dataset.casePage);
 if(!Number.isInteger(next)||next<1||next>Math.max(1,s.caseTotalPages))return;
 s.casePage=next;await refreshCases();render();
}
else if(t.hasAttribute('data-case-reset')){
 s.caseSearch='';s.caseStatus='all';s.caseType='all';s.caseSort='newest';s.caseOwner='';s.caseFrom='';s.caseTo='';s.casePage=1;s.casePageSize=25;
 await refreshCases();render();
}
else if(t.dataset.evidence){s.selected=t.dataset.evidence;render()}
else if(t.dataset.goEvidence){s.tab='evidence';s.selected=t.dataset.goEvidence;render()}
else if(t.hasAttribute('data-deletecase')){
 if(typeof window.confirm!=='function'||!window.confirm('Permanently delete this investigation including its saved chats, evidence and assessments? This cannot be undone.'))return;
 await api('/api/cases/'+s.id,{method:'DELETE'});
 await refreshCases();s.where='cases';s.case=null;s.id=null;render();
 toast('Investigation deleted.');
}
else if(t.hasAttribute('data-newchat')){s.sessionId=null;s.messages=[];render()}
else if(t.hasAttribute('data-draft-assessment')){
 if(!s.excerpts.length)throw Error('Capture and match a source quotation before preparing an assessment.');
 if(typeof window.confirm==='function'&&!window.confirm('Replace unsaved assessment form text with a draft based on captured quotations?'))return;
 const mode=document.getElementById('draft-provider')?.value||'local';
 s.draft=await api('/api/cases/'+s.id+'/assessment-draft',{method:'POST',body:{provider:mode}});
 s.tab='findings';render();
 toast('Unapproved source-grounded draft prepared. Review and explicitly save it.');
}
else if(t.dataset.memberRemove){
 if(typeof window.confirm==='function'&&!window.confirm('Revoke this analyst’s access to this investigation?'))return;
 await api('/api/cases/'+s.id+'/members/'+encodeURIComponent(t.dataset.memberRemove),{method:'DELETE'});
 s.members=await api('/api/cases/'+s.id+'/members');s.taskAssignees=(await api('/api/cases/'+s.id+'/task-assignees')).items||[];
 render();toast('Editor access revoked.');
}
else if(t.dataset.taskHistory){
 const key=t.dataset.taskHistory;
 s.taskHistory[key]=(await api('/api/cases/'+s.id+'/tasks/'+key+'/history')).items||[];
 render();
}
else if(t.dataset.jobSelect){
 s.job=await api('/api/cases/'+s.id+'/jobs/'+t.dataset.jobSelect);
 s.tab='investigate';render();
}
else if(t.hasAttribute('data-job-run'))await runJobFlow()
else if(t.dataset.identityPair){
 const ids=t.dataset.identityPair.split(':');
 if(ids.length===2){
  s.identity=await api('/api/cases/'+s.id+'/identity-analysis?left='+encodeURIComponent(ids[0])+'&right='+encodeURIComponent(ids[1]));
  s.tab='candidates';render();
 }
}
else if(t.hasAttribute('data-job-recover')){
 s.job=await api('/api/cases/'+s.id+'/jobs/'+s.job.id+'/recover',{method:'POST',body:{}});
 render();toast('Interrupted research checkpoint recovered.');
}
else if(t.hasAttribute('data-collect'))await collect()
else if(t.hasAttribute('data-web-discover')){
 if(!s.webProviders?.web?.configured)throw Error('Set BRAVE_SEARCH_API_KEY in Render to enable broad public-web discovery.');
 if(typeof window.confirm==='function'&&!window.confirm('This will send the subject and known public context to Brave Web Search. Continue?'))return;
 if(s.busy)return;s.busy=true;render();
 try{const out=await api('/api/cases/'+s.id+'/web-discovery',{method:'POST',body:{depth:3,consent:true}});
 s.lastResearch=out;await Promise.all([fetchCase(),refreshCases()]);await loadResearchState();
 toast('Web source search: '+out.returned+' candidates, '+out.new+' newly saved and '+out.errors+' failed.',out.errors>0)
 }finally{s.busy=false;render()}
}
else if(t.hasAttribute('data-compare-runs')){
 const params=new URLSearchParams();
 if(s.changes?.currentRunId)params.set('run_id',s.changes.currentRunId);
 const previous=document.getElementById('compare-previous-run')?.value||'';
 if(previous)params.set('against',previous);
 s.changes=await api('/api/cases/'+s.id+'/changes?'+params.toString());render();
}
else if(t.dataset.versionHistory){
 const eid=t.dataset.versionHistory;
 s.versions[eid]=(await api('/api/cases/'+s.id+'/evidence/'+eid+'/versions')).items;render();
}
else if(t.dataset.showCaptures){
 const id=t.dataset.showCaptures;
 s.captures[id]=(await api('/api/cases/'+s.id+'/evidence/'+id+'/captures')).items;render()
}
else if(t.dataset.captureSource){
 const id=t.dataset.captureSource;
 await api('/api/cases/'+s.id+'/evidence/'+id+'/capture',{method:'POST',body:{}});
 s.captures[id]=(await api('/api/cases/'+s.id+'/evidence/'+id+'/captures')).items;render();
 toast('Public source text captured. Inspect the original record before relying on it.');
}
else if(t.hasAttribute('data-camera-preview')){const i=Number(t.dataset.cameraPreview);if(!Number.isInteger(i)||!s.geo[i]||!safeTflStill(s.geo[i].feedUrl))throw Error('Official still unavailable');s.cameraSelection=i;render()}
else if(t.hasAttribute('data-refresh'))await loadGeo()
else if(t.dataset.locate){const k=Number(t.dataset.locate),x=s.geo[k];if(map&&marks[k]&&x){map.setView([x.lat,x.lon],8);marks[k].openPopup()}}
else if(t.hasAttribute('data-add')){const box=document.getElementById('ev-list');if(box){box.insertAdjacentHTML('afterbegin','<form class="panel-pad input-stack" id="manual-form"><strong>Add attributed public-source lead</strong><input name="label" required minlength="3" placeholder="Record title"><textarea name="summary" required minlength="5" placeholder="Observed source claim and limitations"></textarea><input type="url" name="source_url" required placeholder="https://source.example/record"><button class="btn primary">Save unverified lead</button></form>');box.scrollTop=0}}
else if(t.dataset.question){const input=document.querySelector('#ask-form textarea');if(input){input.value=t.dataset.question;input.focus()}}
else if(t.hasAttribute('data-webstart')){
  s.tab='assistant';s.provider=s.server.groqConfigured?'groq':'local';
  s.webSearch=!!s.server.groqConfigured;render();
  const area=document.querySelector('#ask-form textarea');
  const cx=s.case.context||{};
  const hints=[cx.city,cx.organization,cx.profession,cx.public_handle].filter(Boolean).join('; ');
  if(area){area.value='Research public professional information about '+s.case.case.query+
     (hints?'. Known public context: '+hints:'')+'. Separate namesakes, cite original HTTPS sources and state uncertainty.';area.focus()}
  if(!s.server.groqConfigured)toast('Set GROQ_API_KEY on Render to enable public web search.',true);
}
else if(t.dataset.websave){
 const parts=t.dataset.websave.split(':').map(Number);
 const candidate=s.messages[parts[0]]?.webLeads?.[parts[1]];
 if(!candidate||url(candidate.url)==='#')throw Error('Source URL unavailable.');
 await api('/api/cases/'+s.id+'/evidence',{method:'POST',body:{
  label:candidate.title.slice(0,230),source_url:candidate.url,
  summary:'Unverified URL suggested during an AI web search and saved by the analyst. The page has not been independently fetched or authenticated; subject association remains unconfirmed.'
 }});
 await fetchCase();s.tab='evidence';render();toast('Saved as an unverified web lead. Inspect the original page before corroborating.');
}
else if(t.hasAttribute('data-consent')){await api('/api/cases/'+s.id+'/ai-consent',{method:'PUT',body:{enabled:true}});await fetchCase();s.provider=s.server.groqConfigured?'groq':s.server.aiConfigured?'grok':'local';render();toast('Remote AI enabled for this case. Select the provider and ask your question.')}
else if(t.hasAttribute('data-logout')){await api('/api/auth/logout',{method:'POST'});s.user=null;login()}
}catch(err){toast(err.message,true)}});
document.addEventListener('change',async e=>{
 if(['dossier-sort','dossier-status','dossier-class'].includes(e.target.id)){
   const field={'dossier-sort':'dossierSort','dossier-status':'dossierStatus','dossier-class':'dossierClass'}[e.target.id];
   s[field]=e.target.value;await refreshDossier();return;
 }
if(e.target.id==='ai-provider'){s.provider=e.target.value;render()}if(e.target.id==='geo-feed'){s.feed=e.target.value;await loadGeo()}
if(e.target.id==='satellite-toggle'){s.satelliteEnabled=!!e.target.checked;render()}
if(e.target.id==='satellite-date'){const date=e.target.value;if(!/^20[12][0-9]-[0-9]{2}-[0-9]{2}$/.test(date)||date>new Date().toISOString().slice(0,10))throw Error('Invalid imagery date');s.satelliteDate=date;render()}if(e.target.id==='research-web'){s.webSearch=!!e.target.checked;if(s.webSearch)s.braveContext=false;render()}
if(e.target.id==='research-brave'){s.braveContext=!!e.target.checked;if(s.braveContext)s.webSearch=false;render()}if(e.target.id==='conversation-select'){if(e.target.value)await loadConversation(e.target.value);else{s.sessionId=null;s.messages=[];render()}}
if(e.target.id==='research-depth'){s.depth=e.target.value;s.researchPlan=await api('/api/cases/'+s.id+'/research-plan?depth='+s.depth);render()}

if(e.target.id==='evidence-status'){s.evidenceFilter=e.target.value;render()}
if(e.target.id==='evidence-search'){s.evidenceSearch=e.target.value.trim().slice(0,160);const wasFocused=document.activeElement?.id==='evidence-search';render();if(wasFocused){const n=document.getElementById('evidence-search');if(n){n.focus();n.setSelectionRange(n.value.length,n.value.length)}}}
if(e.target.dataset?.pickEvidence){
 const val=e.target.dataset.pickEvidence;
 s.evidenceSelected=e.target.checked?[...new Set([...s.evidenceSelected,val])]:s.evidenceSelected.filter(x=>x!==val);
 render()
}});
document.addEventListener('submit',async e=>{const f=e.target;if(!(['login-form','start-form','smart-search-form','review-form','manual-form','ask-form','context-form','user-form','claim-form','assessment-form','bulk-review-form','candidate-create-form','case-filter-form','job-form','excerpt-form','identity-compare-form','identity-label-form','task-form','member-form','case-candidate-refine-form','credential-change-form'].includes(f.id)||!!f.dataset?.taskChange||!!f.dataset?.candidateReview||!!f.dataset?.candidateLink||!!f.dataset?.adminReset||!!f.dataset?.adminStatus))return;e.preventDefault();if(s.busy)return;const button=f.querySelector('button[type="submit"]')||f.querySelector('button');if(button)button.disabled=true;try{
if(f.id==='login-form'){const d=Object.fromEntries(new FormData(f).entries());await api('/api/auth/login',{method:'POST',body:d});await init();toast('Signed in.')}
if(f.id==='start-form')await launch(f);
if(f.id==='smart-search-form')await smartLaunch(f);
if(f.id==='identity-label-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/identity-reviews',{method:'POST',body:d});
 s.identityQuality=await api('/api/cases/'+s.id+'/identity-quality');render();
 toast('Analyst identity-signal review saved. This is not independently verified ground truth.');
}
if(f.id==='identity-compare-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 s.identity=await api('/api/cases/'+s.id+'/identity-analysis?left='+encodeURIComponent(d.left)+'&right='+encodeURIComponent(d.right));
 s.tab='candidates';render();
}
if(f.id==='member-form'){
 const data=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/members',{method:'POST',body:data});
 s.members=await api('/api/cases/'+s.id+'/members');s.taskAssignees=(await api('/api/cases/'+s.id+'/task-assignees')).items||[];
 render();toast('Editor granted case access.');
}
if(f.id==='task-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/tasks',{method:'POST',body:d});
 const out=await api('/api/cases/'+s.id+'/tasks');s.tasks=out.items||[];s.taskTotal=out.total||0;
 render();toast('Case research task saved.');
}
if(f.dataset?.taskChange){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/tasks/'+f.dataset.taskChange,{method:'PATCH',body:d});
 const out=await api('/api/cases/'+s.id+'/tasks');s.tasks=out.items||[];s.taskTotal=out.total||0;
 s.taskHistory[f.dataset.taskChange]=(await api('/api/cases/'+s.id+'/tasks/'+f.dataset.taskChange+'/history')).items||[];
 render();toast('Research task update recorded with decision history.');
}
if(f.id==='job-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 const create=await api('/api/cases/'+s.id+'/jobs',{method:'POST',body:{
    objective:d.objective,mode:d.mode||'guided',max_steps:Number(d.max_steps)||5,
    allow_web:!!d.allow_web,consent:!!d.consent}});
 s.job=await api('/api/cases/'+s.id+'/jobs/'+create.id);
 s.jobs=(await api('/api/cases/'+s.id+'/jobs')).items||[];render();
 await runJobFlow();
}
if(f.id==='excerpt-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/excerpts',{method:'POST',body:d});
 s.excerpts=(await api('/api/cases/'+s.id+'/excerpts')).items||[];
 render();toast('Exact quote matched to saved source text. Its factual interpretation remains unverified.');
}
if(f.id==='case-filter-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 s.caseSearch=String(d.q||'').trim();
 s.caseStatus=d.status||'all';s.caseType=d.subject_type||'all';s.caseSort=d.sort||'newest';
 s.caseOwner=d.owner||'';s.caseFrom=d.date_from||'';s.caseTo=d.date_to||'';
 s.casePageSize=Number(d.page_size)||25;s.casePage=1;
 await refreshCases();render();
}
if(f.id==='candidate-create-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/candidates',{method:'POST',body:d});
 s.candidates=(await api('/api/cases/'+s.id+'/candidates')).items;
 s.intel=await api('/api/cases/'+s.id+'/intelligence');render();
 toast('Candidate hypothesis created; now attach public source records.');
}
if(f.dataset?.candidateReview){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/candidates/'+f.dataset.candidateReview,{method:'PATCH',body:d});
 s.candidates=(await api('/api/cases/'+s.id+'/candidates')).items;
 s.intel=await api('/api/cases/'+s.id+'/intelligence');render();
 toast('Candidate classification and rationale saved.');
}
if(f.dataset?.candidateLink){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/candidates/'+f.dataset.candidateLink+'/sources',{method:'POST',body:d});
 s.candidates=(await api('/api/cases/'+s.id+'/candidates')).items;
 s.intel=await api('/api/cases/'+s.id+'/intelligence');render();
 toast('Source attached to an identity hypothesis.');
}
if(f.id==='case-candidate-refine-form'){
 const data=Object.fromEntries(new FormData(f).entries());
 data.consent=!!data.consent;
 await api('/api/cases/'+s.id+'/candidate-refinements',{method:'POST',body:data});
 s.refinements=await api('/api/cases/'+s.id+'/candidate-refinements');
 render();toast('Candidate refinement saved; original question remains intact. No search was run.');
}
if(f.id==='assessment-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/assessment',{method:'PUT',body:d});
 s.draft=null;s.intel=await api('/api/cases/'+s.id+'/intelligence');render();
 toast('Assessment saved. Your report now includes these findings.');
}
if(f.id==='bulk-review-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/evidence/bulk-review',{method:'POST',
 body:{status:d.status,notes:d.notes,evidence_ids:s.evidenceSelected}});
 s.evidenceSelected=[];
 await fetchCase();
 const [triage,intel]=await Promise.all([api('/api/cases/'+s.id+'/triage'),api('/api/cases/'+s.id+'/intelligence')]);
 s.triage=triage;s.intel=intel;render();
 toast('Selected records classified with an audit trail.');
}
if(f.id==='context-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/context',{method:'PUT',body:d});
 s.portfolio=null;s.portfolioLocation=null;
 await fetchCase();const [tr,rp]=await Promise.all([api('/api/cases/'+s.id+'/triage'),api('/api/cases/'+s.id+'/research-plan?depth='+s.depth)]);s.triage=tr;s.researchPlan=rp;s.intel=await api('/api/cases/'+s.id+'/intelligence');render();
 toast('Identity clues updated. Candidates reranked for analyst review.');
}
if(f.id==='credential-change-form'){
 const data=Object.fromEntries(new FormData(f).entries());
 await api('/api/auth/change-password',{method:'POST',body:data});
 s.user=null;login();toast('Password changed. All sessions revoked; sign in with the new password.');
}
if(f.dataset?.adminReset){
 const data=Object.fromEntries(new FormData(f).entries());
 await api('/api/users/'+encodeURIComponent(f.dataset.adminReset)+'/reset-credential',{method:'POST',body:data});
 s.users=(await api('/api/users')).items;render();
 toast('Temporary password set. Deliver it securely; the user must rotate it at next login.');
}
if(f.dataset?.adminStatus){
 const data=Object.fromEntries(new FormData(f).entries());
 await api('/api/users/'+encodeURIComponent(f.dataset.adminStatus)+'/status',{method:'PATCH',
  body:{administrator_password:data.administrator_password,active:data.active==='true'}});
 s.users=(await api('/api/users')).items;render();toast('Account status saved; disabled sessions revoked.');
}
if(f.id==='user-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/users',{method:'POST',body:d});
 s.users=(await api('/api/users')).items;render();toast('Analyst account created.');
}
if(f.id==='claim-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/claims',{method:'POST',body:d});
 s.intel=await api('/api/cases/'+s.id+'/intelligence');toast('Attributed claim recorded with its source.');render();
}
if(f.id==='review-form'){const d=Object.fromEntries(new FormData(f).entries());await api('/api/evidence/'+d.id,{method:'PATCH',body:{status:d.status,reviewer_notes:d.notes||''}});await fetchCase();s.triage=await api('/api/cases/'+s.id+'/triage');s.intel=await api('/api/cases/'+s.id+'/intelligence');render();toast('Evidence review saved.')}
if(f.id==='manual-form'){const d=Object.fromEntries(new FormData(f).entries());await api('/api/cases/'+s.id+'/evidence',{method:'POST',body:d});await fetchCase();s.intel=await api('/api/cases/'+s.id+'/intelligence');render();toast('Unverified source lead added.')}
if(f.id==='ask-form'){
 const q=f.querySelector('textarea')?.value.trim();if(!q)return;
 if(s.provider!=='local'&&!s.case.case.ai_opt_in)
   throw Error('Remote AI requires explicit consent for this case. Use the Enable remote AI button.');
 if(s.provider==='groq'&&!s.server.groqConfigured)
   throw Error('GroqCloud requires GROQ_API_KEY on the Render backend.');
 if(s.provider==='grok'&&!s.server.aiConfigured)
   throw Error('xAI Grok requires XAI_API_KEY. GroqCloud is a different provider.');
 const history=s.messages.slice(-8).map(m=>({role:m.role,content:m.text.slice(0,2000)}));
 s.messages.push({role:'user',text:q});s.busy=true;render();
 const r=await api('/api/cases/'+s.id+'/chat',
   {method:'POST',body:{provider:s.provider,question:q,history,web_search:!!(s.webSearch&&s.provider==='groq'),brave_context:!!(s.braveContext&&s.provider==='groq'),session_id:s.sessionId}});
 s.sessionId=r.sessionId||s.sessionId;
 s.conversations=(await api('/api/cases/'+s.id+'/conversations')).items;
 s.messages.push({role:'assistant',text:r.answer,model:r.model,ids:r.evidenceIds||[],
                  followUp:r.followUp||'',needsDisambiguation:!!r.needsDisambiguation,webSearch:!!r.webSearch,braveContextUsed:!!r.braveContextUsed,webLeads:r.webLeads||[],retrieval:r.retrieval||null});
 s.busy=false;render();
}
}catch(err){s.busy=false;toast(err.message,true);if(f.id==='login-form'){const el=document.getElementById('login-error');if(el)el.textContent=err.message}else if(f.id==='ask-form'){s.messages.push({role:'assistant',text:'The AI provider could not complete this request: '+err.message,model:'Provider error',error:true});render()}}finally{if(button)button.disabled=false}});
init().catch(()=>login());
})();
