
/* OSINT Alpha v2 research console. Source records are candidates, not verdicts. */
(()=>{'use strict';
const app=document.getElementById('app'), s={user:null,where:'home',mode:'person',cases:[],overview:{},sources:[],projects:[],capabilities:{},server:{},case:null,brief:null,id:null,tab:'overview',selected:null,messages:[],provider:'local',webSearch:false,sessionId:null,conversations:[],triage:null,searchHistory:[],researchPlan:null,researchRuns:[],candidates:[],intel:null,lastResearch:null,depth:'standard',evidenceFilter:'all',evidenceSearch:'',evidenceSelected:[],users:[],busy:false,feed:'earthquakes',geo:[],geoStatus:'idle',geoError:''};
const modes={person:{name:'People',icon:'user',tip:'Public profiles and identity candidates',placeholder:'e.g. Jane Researcher',sources:['github','openalex','crossref','wikidata','wikipedia']},organization:{name:'Organizations',icon:'building',tip:'Companies and public entity references',placeholder:'e.g. Example Systems Ltd',sources:['gleif','github','wikipedia','wikidata','gdelt']},domain:{name:'Domains',icon:'globe',tip:'Passive DNS and domain metadata',placeholder:'e.g. example.org',sources:['dns']},ip:{name:'Public IPs',icon:'shield',tip:'Passive network exposure intelligence',placeholder:'e.g. 8.8.8.8',sources:['internetdb']}};
const h=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const url=x=>{try{const u=new URL(x);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password?u.href:'#'}catch{return '#'}};
const when=x=>{if(!x)return 'Unknown';const n=Number(x);const d=new Date(typeof x==='number'||(/^\d{10,13}$/.test(String(x)))?(n<1e11?n*1000:n):x);return Number.isFinite(+d)?d.toLocaleString():String(x)};
const link=(href,label)=>'<a class="text-link" target="_blank" rel="noopener noreferrer" href="'+h(url(href))+'">'+h(label)+' ↗</a>';
const tag=x=>'<span class="tag '+({corroborated:'ok',configured:'ok',ok:'ok',candidate:'warn',error:'bad',disputed:'warn',rejected:'bad',not_configured:'warn'}[x]||'')+'">'+h(x)+'</span>';
const icon=k=>{const paths={home:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',search:'<circle cx="10.5" cy="10.5" r="7"/><path d="m16 16 5 5"/>',case:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h6"/>',user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c0-5 16-5 16 0"/>',building:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h2m4 0h2M8 11h2m4 0h2"/>',globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/>',shield:'<path d="m12 2 8 4v6c0 6-4 9-8 10-4-1-8-4-8-10V6Z"/><path d="m9 12 2 2 4-4"/>',world:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c-5 5-5 13 0 18m0-18c5 5 5 13 0 18"/>',sources:'<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',settings:'<circle cx="12" cy="12" r="3"/><path d="M4 12H2m20 0h-2M12 4V2m0 20v-2M6 6 4 4m14 14 2 2"/>',arrow:'<path d="M4 12h16m-7-7 7 7-7 7"/>',back:'<path d="M20 12H4m7 7-7-7 7-7"/>',refresh:'<path d="M20 8a8 8 0 0 0-14-2L4 9m0-6v6h6M4 16a8 8 0 0 0 14 2l2-3m0 6v-6h-6"/>',plus:'<path d="M12 4v16M4 12h16"/>'};return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(paths[k]||paths.case)+'</svg>'};
function toast(text,error=false){const n=document.createElement('div');n.className='toast'+(error?' bad':'');n.textContent=text;document.body.append(n);setTimeout(()=>n.remove(),5100)}
async function api(path,opts={}){const ini={credentials:'same-origin',method:opts.method||'GET',headers:{}};if('body'in opts){ini.body=JSON.stringify(opts.body);ini.headers['Content-Type']='application/json'}if(ini.method!=='GET')ini.headers['X-OSINT-Alpha-Action']='1';let r;try{r=await fetch(path,ini)}catch{throw Error('Network unavailable. Check Render backend status.')}let j;try{j=(r.headers.get('content-type')||'').includes('json')?await r.json():await r.text()}catch{j={}}if(!r.ok){if(r.status===401&&path!=='/api/auth/login'){s.user=null;login()}throw Error(j?.detail||j?.message||'HTTP '+r.status)}return j}
const nav=(id,title,k)=>'<button class="nav-item '+(s.where===id||(id==='cases'&&s.where==='case')?'active':'')+'" data-nav="'+id+'">'+icon(k)+' '+title+'</button>';
function frame(inner){return '<div class="shell"><aside class="sidebar"><div class="brand"><div class="brand-symbol">A</div><div><div class="brand-name">OSINT ALPHA</div><div class="brand-meta">ANALYST WORKBENCH / V4</div></div></div><nav>'+nav('home','Workspace','home')+nav('cases','Investigations','case')+nav('world','World intelligence','world')+'<div class="nav-label">PLATFORM</div>'+nav('sources','Source integrations','sources')+nav('settings','Settings & security','settings')+(s.user?.role==='admin'?nav('admin','Analyst accounts','user'):'')+'</nav><div class="sidebar-spacer"></div><div class="sidebar-note"><strong><span class="status-dot"></span> Evidence-first research</strong><p>Public-source findings are leads. Verify identities and security claims before relying on them.</p></div></aside><div class="workspace"><header class="topbar"><div class="crumb">OSINT ALPHA / '+h((s.where==='case'?'INVESTIGATIONS':s.where).toUpperCase())+'</div><div class="top-right"><span class="top-status"><span class="status-dot"></span> API CONNECTED</span><span class="user-chip">'+h((s.user?.username||'A')[0].toUpperCase())+'</span></div></header><main class="main">'+inner+'</main></div></div>'}
function login(){app.innerHTML='<div class="login"><section class="login-art"><div class="brand"><div class="brand-symbol">A</div><div><div class="brand-name">OSINT ALPHA</div><div class="brand-meta">INTELLIGENCE WORKSPACE</div></div></div><div class="eyebrow">Source-linked public intelligence</div><h1>From questions to <em>verifiable findings.</em></h1><p>One environment for authorized public identity research, company due diligence, defensive domain and IP enrichment, and geographic observations. Evidence remains attributable.</p><div class="login-tiles"><span>PUBLIC RECORDS</span><span>DEFENSIVE INTELLIGENCE</span><span>TRACEABLE REPORTS</span></div></section><section class="login-panel"><div class="login-card"><div class="eyebrow">SECURE WORKSPACE</div><h2>Welcome back</h2><p>Use the administrator credentials configured privately in Render.</p><form id="login-form"><div class="field"><label class="field-label">Username</label><input name="username" required value="admin" autocomplete="username"></div><div class="field"><label class="field-label">Password</label><input name="password" type="password" required autocomplete="current-password" placeholder="Enter your password"></div><button class="btn primary">Sign in '+icon('arrow')+'</button><div id="login-error" class="form-error"></div></form><p class="footer-note">Prototype. No private-source surveillance, confirmed identity matching or persistent enterprise data guarantees.</p></div></section></div>'}
const heading=(type,title,desc,action='')=>'<div class="section-row" style="margin:0 0 25px"><div><div class="eyebrow">'+h(type)+'</div><h1 class="page-title">'+h(title)+'</h1><p class="page-sub">'+h(desc)+'</p></div>'+action+'</div>';
const caseRow=c=>'<div class="item-row"><div class="row-main"><div class="item-title">'+h(c.title)+'</div><div class="item-sub">'+h(c.subject_type)+' / '+h(c.query)+' · '+h(when(c.created_at))+'</div></div><div class="row-actions"><span class="tag">'+Number(c.evidence_count||0)+' records</span><button data-open="'+h(c.id)+'" class="btn small">Open case '+icon('arrow')+'</button></div></div>';
const modeButton=key=>'<button type="button" class="chip '+(key===s.mode?'active':'')+'" data-mode="'+key+'">'+icon(modes[key].icon)+' '+modes[key].name+'</button>';
function home(){const ov=s.overview||{};return '<section class="hero"><div class="eyebrow">AUTHORIZED PUBLIC-SOURCE INVESTIGATION</div><h1>Find relevant public records.<br><span>Defend every conclusion.</span></h1><p class="desc">Research public profiles, organizations, domains or public IP assets through transparent source queries. Compare possible identities, record analyst decisions and generate a source-backed assessment.</p><form id="start-form" class="input-stack"><div class="chips">'+Object.keys(modes).map(modeButton).join('')+'</div><label class="field-label">Enter a '+h(modes[s.mode].name.toLowerCase())+' search</label><div class="search-box"><input name="query" id="query" placeholder="'+h(modes[s.mode].placeholder)+'" minlength="3" maxlength="160" required><button class="btn primary" '+(s.busy?'disabled':'')+'>'+icon('search')+' '+(s.busy?'Collecting…':'Start investigation')+'</button></div><div class="form-row" style="max-width:850px;margin-top:10px"><div><label class="field-label">Authorized research purpose</label><input name="purpose" required minlength="12" maxlength="550" placeholder="e.g. Authorized supplier due diligence"></div><div class="input-stack"><label class="check"><input type="checkbox" name="authority" required> I have a legitimate purpose and appropriate authorization.</label><label class="check"><input type="checkbox" name="ai_opt_in"> Permit remote AI on this case only when selected.</label></div></div><div class="panel-pad" style="background:rgba(9,16,29,.55);border:1px solid #34415d;border-radius:12px;max-width:850px"><div class="eyebrow" style="margin-bottom:11px">OPTIONAL IDENTITY CLUES · REDUCE NAMESAKES</div><div class="form-row"><input name="city" maxlength="120" placeholder="City or region (e.g. Delhi)"><input name="organization" maxlength="160" placeholder="Known employer / institution"></div><div class="form-row" style="margin-top:10px"><input name="profession" maxlength="120" placeholder="Profession / field"><input name="public_handle" maxlength="120" placeholder="Known public username"></div><p class="help">Clues prioritize potential records; they do not prove identity. Avoid private contact details or home addresses.</p></div><div class="search-foot">Public sources only. The investigation will keep search history, provider outcomes and analyst decisions.</div></form></section><div class="section-row"><h2 class="section-heading">Investigation types</h2><span class="section-note">CHOOSE A RESEARCH WORKFLOW</span></div><div class="cards4">'+Object.entries(modes).map(([id,m])=>'<button class="panel usecase" data-mode="'+id+'"><span class="symbol">'+icon(m.icon)+'</span><strong>'+m.name+'</strong><p>'+m.tip+'</p></button>').join('')+'</div><div class="section-row"><h2 class="section-heading">Workspace at a glance</h2><span class="section-note">AUDITABLE CASE DATA</span></div><div class="stat-grid">'+[['CASES',ov.cases||0,'Saved investigations'],['EVIDENCE',ov.evidence||0,'Candidate records'],['CORROBORATED',ov.corroborated||0,'Human classified'],['INTEGRATED ADAPTERS',s.sources.length,'Actually integrated']].map(x=>'<div class="panel stat"><div class="stat-label">'+x[0]+'</div><div class="stat-number">'+x[1]+'</div><div class="stat-tail">'+x[2]+'</div></div>').join('')+'</div><div class="section-row"><h2 class="section-heading">Recent investigations</h2><button class="btn small subtle" data-nav="cases">View all '+icon('arrow')+'</button></div><div class="panel">'+(s.cases.length?s.cases.slice(0,6).map(caseRow).join(''):'<div class="empty"><div class="large">Start with one question</div><p>Enter a search above. Cases and collected records will appear here.</p></div>')+'</div>'}
function cases(){return heading('CASE REGISTRY','Investigations','Saved public-source findings, reviews and exports.','<button data-nav="home" class="btn primary">'+icon('plus')+' New investigation</button>')+'<div class="panel">'+(s.cases.length?s.cases.map(caseRow).join(''):'<div class="empty">No saved cases. Start from Workspace.</div>')+'</div>'}
const tabs=['overview','candidates','evidence','assistant','findings','reports','activity'];
function casePage(){const c=s.case?.case;if(!c)return '<div class="empty">Loading case…</div>';const b=s.brief||{};return '<div class="casehead"><div><button data-nav="cases" class="back-link">'+icon('back')+' Investigations</button><div class="eyebrow">'+h(c.subject_type)+' / EVIDENCE WORKSPACE</div><h1 class="h1">'+h(c.title)+'</h1><p class="page-sub">'+h(c.purpose)+'</p><div class="badge-row" style="margin-top:12px"><span class="tag">'+h(c.query)+'</span><span class="tag">'+Number(b.total||0)+' records</span><span class="tag ok">'+Number(b.counts?.corroborated||0)+' corroborated</span></div></div><div class="inline-actions"><button class="btn small" data-webstart>'+icon('search')+' Research public web</button><button class="btn small" data-collect '+(s.busy?'disabled':'')+'>'+icon('refresh')+' '+(s.busy?'Working…':'Run sources')+'</button><a class="btn small primary" target="_blank" rel="noopener" href="/api/cases/'+h(c.id)+'/report-v4.pdf">Export report</a></div></div><div class="tabs">'+tabs.map(id=>'<button class="tab '+(s.tab===id?'active':'')+'" data-tab="'+id+'">'+({assistant:'Research copilot',activity:'Source coverage',candidates:'Identity candidates',findings:'Analyst findings'}[id]||id.charAt(0).toUpperCase()+id.slice(1))+'</button>').join('')+'</div>'+({overview:caseOverview,candidates:caseCandidates,evidence:caseEvidence,assistant:caseAssistant,findings:caseFindings,reports:caseReports,activity:caseActivity}[s.tab]||caseOverview)()}
function caseOverview(){
 const c=s.case.case,ctx=s.case.context||{},ins=s.intel||{},stats=ins.metrics||{},
       run=s.lastResearch,steps=s.researchPlan?.queries||[],triage=s.triage?.candidates||[];
 const current=(ins.assessment||{}).status||'open';
 const useful=triage.filter(x=>x.relevance>0).slice(0,5);
 const cards=[
 ['SOURCE RECORDS',stats.records||0,'Public candidates, not verified people'],
 ['REVIEWED',stats.reviewed||0,'Records examined by an analyst'],
 ['IDENTITY HYPOTHESES',s.candidates.length,'Explicit candidate profiles'],
 ['UNAVAILABLE QUERIES',stats.failedQueries||0,'Upstream searches that failed']
 ];
 const header='<div class="analyst-intro"><div><div class="eyebrow">ACTIVE INVESTIGATION · '+h(current.toUpperCase().replaceAll('_',' '))+'</div><h2>What have we actually established?</h2><p>Separate relevant sources from namesakes, record uncertainties, and deliver a source-backed assessment. Nothing is automatically called a verified identity.</p></div><button class="btn primary" data-tab="findings">Write assessment →</button></div>';
 const context='<section class="panel" style="margin:0 0 20px"><div class="panel-head"><div><div class="panel-title">Target identity · known public context</div><div class="panel-meta">These clues now influence research planning and should guide verification.</div></div><span class="tag accent">Editable</span></div><form class="panel-pad input-stack" id="context-form"><div class="form-row"><input name="city" aria-label="Known city or region" maxlength="120" value="'+h(ctx.city||'')+'" placeholder="City or region"><input name="organization" aria-label="Known employer or organization" maxlength="160" value="'+h(ctx.organization||'')+'" placeholder="Known organization"></div><div class="form-row"><input name="profession" aria-label="Known professional field" maxlength="120" value="'+h(ctx.profession||'')+'" placeholder="Profession or field"><input name="public_handle" aria-label="Known public username" maxlength="120" value="'+h(ctx.public_handle||'')+'" placeholder="Known public username"></div><div class="inline-actions"><button type="submit" class="btn small">Save identity clues</button><span class="help">Unknown context remains unknown. Never interpret missing fields as a contradiction.</span></div></form></section>';
 const plan='<section class="panel"><div class="panel-head"><div><div class="panel-title">Transparent research plan</div><div class="panel-meta">Allowlisted source APIs; no claim of universal internet coverage.</div></div><span class="tag accent">'+steps.length+' planned searches</span></div><div class="panel-pad"><div class="form-row" style="align-items:end"><div><label class="field-label" for="research-depth">Research depth</label><select id="research-depth">'+['quick','standard','thorough'].map(d=>'<option value="'+d+'" '+(s.depth===d?'selected':'')+'>'+d[0].toUpperCase()+d.slice(1)+'</option>').join('')+'</select></div><button class="btn primary" data-collect '+(s.busy?'disabled':'')+'>'+icon('search')+' '+(s.busy?'Researching…':'Run source research')+'</button></div>'+
 (steps.length?'<div class="plan-steps">'+steps.map((x,i)=>'<div class="plan-step"><span class="plan-n">'+(i+1)+'</span><div><strong>'+h(x.provider)+'</strong><div class="meta">'+h(x.query)+'</div><small>'+h(x.reason)+'</small></div></div>').join('')+'</div>':'<div class="empty">There is no compatible source plan for this investigation.</div>')+
 (run?'<div class="callout '+(run.errors?'warn':'ok')+'">Last run: '+run.returned+' returned candidates; '+run.new+' newly saved; '+run.errors+' provider errors. A returned candidate is not a verified match.</div>':'')+'</div></section>';
 const candidates='<section class="panel"><div class="panel-head"><div class="panel-title">Potentially relevant source leads</div><button class="btn small subtle" data-tab="candidates">Compare identities →</button></div>'+
 (useful.length?useful.map(x=>'<div class="item-row"><div class="row-main"><div class="item-title">'+h(x.label)+'</div><div class="item-sub">'+h(x.provider)+' · matched public clues: '+h(x.signals.join(', ')||'none')+'</div></div><button data-go-evidence="'+h(x.id)+'" class="btn small">Inspect</button></div>').join(''):'<div class="empty">No source records presently match supplied public clues. Do not assume the target has no online presence.</div>')+'</section>';
 return header+context+'<div class="stat-grid">'+cards.map(x=>'<div class="panel stat"><div class="stat-label">'+x[0]+'</div><div class="stat-number">'+x[1]+'</div><div class="stat-tail">'+x[2]+'</div></div>').join('')+'</div><div class="grid2">'+plan+candidates+'</div>';
}

function caseCandidates(){
 const items=s.candidates||[],ev=s.case.evidence||[];
 return '<div class="analyst-intro"><div><div class="eyebrow">IDENTITY RESOLUTION / ANALYST CONTROL</div><h2>Compare namesakes. Do not merge blindly.</h2><p>Group only records supported by matching public identifiers. An analyst confirmation is a documented decision, not legal identity verification.</p></div></div>'+
 '<div class="grid2"><section class="panel"><div class="panel-head"><div class="panel-title">Candidate profiles ('+items.length+')</div></div>'+
 (items.length?items.map(x=>'<article class="candidate-card"><div class="badge-row">'+tag(x.classification)+'</div><h3>'+h(x.display_name)+'</h3><p class="page-sub">'+h(x.reason||'No rationale yet.')+'</p><div class="meta">'+x.sources.length+' linked public-source record(s)</div>'+
 x.sources.map(y=>'<div class="sourcehealth">'+link(y.source_url,y.label)+' <span class="tag">'+h(y.status)+'</span></div>').join('')+
 '<form data-candidate-review="'+h(x.id)+'" class="input-stack"><label class="field-label">Analyst hypothesis</label><select name="classification">'+['unresolved','potential_match','excluded','confirmed_by_analyst'].map(v=>'<option value="'+v+'" '+(x.classification===v?'selected':'')+'>'+h(v.replaceAll('_',' '))+'</option>').join('')+'</select><textarea name="reason" maxlength="1500" aria-label="Reason for analyst hypothesis" placeholder="Explain corroborating or conflicting evidence">'+h(x.reason||'')+'</textarea><button class="btn small">Save decision</button></form>'+
 (ev.length?'<form data-candidate-link="'+h(x.id)+'" class="input-stack" style="margin-top:15px"><label class="field-label">Associate a source record</label><select name="evidence_id">'+ev.map(y=>'<option value="'+h(y.id)+'">'+h(y.provider+' · '+y.label.slice(0,80))+'</option>').join('')+'</select><input name="rationale" maxlength="1200" placeholder="Why might these records refer to the same subject?"><button class="btn small subtle">Attach candidate evidence</button></form>':'')+'</article>').join(''):'<div class="empty"><div class="large">No candidate identities yet</div><p>Run a source search, then create an explicit hypothesis instead of merging matching names automatically.</p></div>')+'</section>'+
 '<section class="panel"><div class="panel-head"><div class="panel-title">Create an identity hypothesis</div></div><form class="panel-pad input-stack" id="candidate-create-form"><label class="field-label">Candidate identifier</label><input name="display_name" minlength="2" maxlength="180" required placeholder="e.g. Ayush Tripathi — Delhi developer"><label class="field-label">Reason this might be a distinct person</label><textarea name="reason" maxlength="1500" placeholder="Known public account, employer, city, source references…"></textarea><button class="btn primary">Create candidate group</button><p class="help">This does not prove two accounts belong to the same person. Source linking always requires an analyst review.</p></form>'+
 '<div class="insight"><h3>What counts as a reliable match?</h3><p>Use specific independent identifiers or corroborating source claims. A name match, shared city or similar profession alone should not establish identity. Record exclusions and contradictions.</p></div></section></div>';
}

function caseEvidence(){
 const ev=s.case.evidence||[],shown=ev.filter(x=>
    (s.evidenceFilter==='all'||x.status===s.evidenceFilter)&&
    (!s.evidenceSearch||[x.label,x.summary,x.provider].join(' ').toLowerCase().includes(s.evidenceSearch.toLowerCase()))),
 selected=ev.find(x=>x.id===s.selected)||shown[0]||ev[0];
 const toolbar='<div class="filterbar"><input id="evidence-search" aria-label="Search evidence by title, summary or source" placeholder="Find a public-source record…" value="'+h(s.evidenceSearch)+'"><select id="evidence-status" aria-label="Filter review status">'+['all','candidate','corroborated','disputed','rejected'].map(x=>'<option value="'+x+'" '+(s.evidenceFilter===x?'selected':'')+'>'+h(x.replaceAll('_',' '))+'</option>').join('')+'</select><span class="meta">'+shown.length+'/'+ev.length+' shown</span></div>';
 const bulk='<form id="bulk-review-form" class="bulkbar"><strong>Bulk review</strong><span class="meta">'+s.evidenceSelected.length+' selected</span><select name="status" aria-label="Bulk classification"><option value="rejected">Reject namesakes</option><option value="disputed">Mark disputed</option><option value="candidate">Return to candidate</option><option value="corroborated">Analyst corroboration</option></select><input name="notes" minlength="12" maxlength="1200" required placeholder="Reason for every selected classification"><button class="btn small" type="submit" '+(!s.evidenceSelected.length?'disabled':'')+'>Apply to selected</button></form>';
 const list=shown.length?shown.map(x=>'<div class="evidence-tile '+(x.id===selected?.id?'selected':'')+'"><label class="pick"><input type="checkbox" data-pick-evidence="'+h(x.id)+'" '+(s.evidenceSelected.includes(x.id)?'checked':'')+' aria-label="Select '+h(x.label)+'"></label><button class="evidence-tile-body" data-evidence="'+h(x.id)+'"><span class="badge-row">'+tag(x.status)+'<span class="tag">'+h(x.provider)+'</span></span><strong>'+h(x.label)+'</strong><span class="ev-description">'+h(x.summary)+'</span><span class="ev-meta">Collected '+h(when(x.fetched_at))+'</span></button></div>').join(''):
 '<div class="empty">No records match this filter. Clear your search or run new source queries.</div>';
 const inspector=selected?'<div class="inspector"><div class="badge-row">'+tag(selected.status)+'<span class="tag">'+h(selected.provider)+'</span></div><h3>'+h(selected.label)+'</h3><p>'+h(selected.summary)+'</p><div class="source-item"><strong>Original source</strong><p>'+link(selected.source_url,'Inspect public source')+'</p><div class="meta">Collected: '+h(when(selected.fetched_at))+'</div><div class="meta">Record hash: '+h(selected.sha256||'Unknown')+'</div></div><div class="divider"></div><form id="review-form" class="input-stack"><input type="hidden" name="id" value="'+h(selected.id)+'"><label class="field-label">Analyst review classification</label><select name="status">'+['candidate','corroborated','disputed','rejected'].map(x=>'<option value="'+x+'" '+(x===selected.status?'selected':'')+'>'+x+'</option>').join('')+'</select><label class="field-label">Reason, caveats and potential namesakes</label><textarea name="notes" maxlength="1200" placeholder="Record your reason and uncertainty…">'+h(selected.reviewer_notes||'')+'</textarea><button class="btn primary">Save review decision</button></form><div class="divider"></div><form id="claim-form" class="input-stack"><input type="hidden" name="evidence_id" value="'+h(selected.id)+'"><label class="field-label">Source-linked assertion</label><textarea name="claim_text" minlength="10" maxlength="1200" required placeholder="What does this source actually say?"></textarea><select name="stance"><option value="supports">Supports</option><option value="contradicts">Contradicts</option><option value="context">Context only</option></select><button class="btn small">Record claim and source</button></form><p class="help">Do not mark a person verified merely because this record includes the subject name.</p></div>':'<div class="empty">Select a record to inspect.</div>';
 return '<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div><div class="panel-title">Evidence workbench</div><div class="panel-meta">Filter, inspect and record decisions against individual original sources</div></div><button class="btn small" data-add>Add source lead</button></div><div class="panel-pad">'+toolbar+bulk+'</div></section>'+
 '<div class="evidence"><section class="panel"><div class="panel-head"><div class="panel-title">Source records</div><span class="panel-meta">'+shown.length+' matching</span></div><div class="evidence-list" id="ev-list">'+list+'</div></section>'+
 '<section class="panel"><div class="panel-head"><div class="panel-title">Source inspector</div><span class="panel-meta">PROVENANCE · REVIEW</span></div>'+inspector+'</section></div>';
}

function rich(text){let html='',ul=false;const inline=x=>h(x).replace(/\*\*([^*]{1,150})\*\*/g,'<strong>$1</strong>').replace(/\[([^\]]{1,160})\]\((https?:\/\/[^\s)]+)\)/g,(_,title,raw)=>{const href=url(raw.replace(/&amp;/g,'&'));return href==='#'?title:'<a class="text-link" href="'+h(href)+'" target="_blank" rel="noopener noreferrer">'+title+' ↗</a>'});for(const raw of String(text||'').split(/\r?\n/)){const line=raw.trim();if(!line){if(ul){html+='</ul>';ul=false}continue}const heading=line.match(/^#{1,4}\s+(.+)/);if(heading){if(ul){html+='</ul>';ul=false}html+='<h4>'+inline(heading[1])+'</h4>';continue}if(/^[•*-]\s+/.test(line)){if(!ul){html+='<ul>';ul=true}html+='<li>'+inline(line.replace(/^[•*-]\s+/,''))+'</li>';continue}if(ul){html+='</ul>';ul=false}html+='<p>'+inline(line)+'</p>'}if(ul)html+='</ul>';return html||'<p>No evidence was returned.</p>'}
function citations(ids){const ev=s.case?.evidence||[];return (ids||[]).map(id=>ev.find(e=>e.id===id)).filter(Boolean).map((x,n)=>'<a class="tag accent" target="_blank" rel="noopener noreferrer" href="'+h(url(x.source_url))+'">Source '+(n+1)+': '+h(x.provider)+'</a>').join('')}
function caseAssistant(){
 const c=s.case.case,p=s.provider;
 const history='<div class="source-item"><div class="eyebrow" style="margin-bottom:10px">SAVED RESEARCH CONVERSATIONS</div><div class="inline-actions"><select id="conversation-select" style="flex:1;min-width:130px"><option value="">New conversation</option>'+
 (s.conversations||[]).map(x=>'<option value="'+h(x.id)+'" '+(s.sessionId===x.id?'selected':'')+'>'+h(x.title.slice(0,55))+'</option>').join('')+
 '</select><button class="btn small" data-newchat>New chat</button></div><p class="help">Chats and source links are saved to the investigation database.</p></div>';
 const canRemote=!!s.server.groqConfigured||!!s.server.aiConfigured;
 const intro='<div class="callout '+(p==='local'?'warn':'ok')+'">'+(
  p==='local'?'Offline guidance is rule-based, not an AI chatbot. Choose a configured model for conversational research.':
  'Conversational AI is active. It can discuss this case and previous messages, ask for identity clues and cite stored evidence. It uses saved case evidence; optional Groq browser search can be enabled per request.'
 )+'</div>';
 const messages=s.messages.length?s.messages.map((m,idx)=>'<div class="message '+m.role+'"><div class="bubble">'+
  (m.role==='assistant'?rich(m.text):'<p>'+h(m.text)+'</p>')+'</div>'+
  (m.role==='assistant'?'<div class="message-foot">'+h(m.model||'Assistant')+(m.webSearch?' · Public web search':'')+(m.error?' · Request failed':' · Sources require review')+'</div>'+
   (m.followUp?'<button class="btn small subtle" data-question="'+h(m.followUp)+'" style="justify-content:flex-start;white-space:normal;text-align:left">'+h(m.followUp)+' →</button>':'')+
   '<div class="citation-row">'+citations(m.ids)+'</div>'+
   (m.webSearch?(m.webLeads?.length?'<div class="source-item" style="margin-top:11px"><strong>Public web leads · analyst review required</strong><p>These URLs are suggested by the model and have not been independently fetched, validated or matched to this person.</p>'+
       m.webLeads.map((lead,leadIndex)=>'<div class="sourcehealth" style="display:block"><div style="margin-bottom:7px">'+link(lead.url,lead.title)+'</div><button type="button" class="btn small subtle" data-websave="'+idx+':'+leadIndex+'">Save as unverified lead</button></div>').join('')+
       '</div>':'<div class="callout warn">Groq returned no extractable source URLs. Ask for original HTTPS source links; do not treat uncited claims as evidence.</div>'):''):'')+'</div>').join(''):
  '<div class="empty"><div class="large">Tell me what you want to verify</div><p>For a common name, start with a city, organization, public handle or known profile. The assistant will ask for one distinguishing clue rather than invent a biography.</p></div>';
 const needsConsent=!c.ai_opt_in&&canRemote?
  '<div class="callout warn"><strong>Remote AI is currently off for this case.</strong><p>To activate GroqCloud, you must explicitly permit sending up to 35 saved source records and recent chat messages to the model provider when you send a message.</p><button type="button" data-consent class="btn primary small">Enable remote AI for this case</button></div>':
  '<div class="callout '+(c.ai_opt_in?'ok':'warn')+'">'+(c.ai_opt_in?'Remote-AI consent enabled for this case. Records are sent only when a remote provider is selected.':'Remote-AI consent disabled. A remote key is required for model reasoning.')+'</div>';
 return '<div class="ai-layout"><section class="panel"><div class="panel-head"><div><div class="panel-title">Case research assistant</div><div class="panel-meta">Conversation, identity disambiguation and attributable evidence</div></div><span class="tag '+(p==='local'?'warn':'ok')+'">'+h(({local:'OFFLINE RULES · NO AI',groq:'GROQCLOUD · AI',grok:'XAI GROK · AI'})[p])+'</span></div>'+
 '<div id="chat-history" class="chat-history">'+messages+'</div>'+
 '<form id="ask-form" class="chat-composer"><textarea name="question" maxlength="2000" required placeholder="Ask naturally: Who is this person? I mean the one in Delhi..."></textarea><button type="submit" class="btn primary" '+(s.busy?'disabled':'')+'>'+(s.busy?'Analyzing…':'Send →')+'</button></form>'+
 '</section><aside class="panel"><div class="panel-head"><div class="panel-title">Research intelligence</div></div><div class="panel-pad input-stack">'+intro+
 history+'<label class="field-label" for="ai-provider">Reasoning mode</label><select id="ai-provider"><option value="local" '+(p==='local'?'selected':'')+'>Offline guidance · Not AI</option><option value="groq" '+(p==='groq'?'selected':'')+'>GroqCloud · '+(s.server.groqConfigured?'AI ready':'No API key')+'</option><option value="grok" '+(p==='grok'?'selected':'')+'>xAI Grok · '+(s.server.aiConfigured?'AI ready':'No API key')+'</option></select>'+
 needsConsent+'<div class="divider"></div><div class="eyebrow">SMART STARTERS</div>'+
 ['Who is '+c.query+'?','I think these publications belong to different people.','Which sources support this identity?','What identifying detail should I provide?'].map(q=>'<button type="button" class="btn small subtle wide" style="white-space:normal;text-align:left;justify-content:flex-start" data-question="'+h(q)+'">'+h(q)+'</button>').join('')+
 '<label class="check" style="margin-top:6px"><input type="checkbox" id="research-web" '+(s.webSearch?'checked':'')+' '+(p==='groq'&&c.ai_opt_in&&s.server.groqConfigured?'':'disabled')+'> Search public web with Groq browser tool for this message</label>'+
 '<p class="help">Web search is optional, may use additional quota, and returns unverified third-party leads. Results are not automatically added to the case evidence database.</p>'+
 '<p class="help">Different people can share the same name. A model does not independently verify identity.</p></div></aside></div>';
}
function caseGraph(){return '<div class="panel"><div class="panel-head"><div class="panel-title">Source-linked provenance</div><div class="panel-meta">Connections are collection relationships, not confirmed identity links</div></div><div class="panel-pad"><div class="flow"><span class="step">'+h(s.case.case.query)+'</span><span class="arrow">→</span>'+(s.case.evidence||[]).slice(0,12).map(e=>'<span class="step">'+h(e.provider)+': '+h(e.label.slice(0,28))+'</span>').join('<span class="arrow">→</span>')+'</div><div class="insight"><h3>How to read this view</h3><p>These are case-to-record relationships. No unverified account has been merged into a person or company identity automatically.</p></div></div></div>'}
function caseFindings(){
 const inf=s.intel||{},a=inf.assessment||{},claims=inf.claims||[],metrics=inf.metrics||{};
 const claimItems=claims.length?claims.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.claim_text)+'</strong><div class="item-sub">'+h(x.stance)+' · '+link(x.source_url,x.label)+'</div></div>'+tag(x.status)+'</div>').join(''):
 '<div class="empty">No evidence-backed claims have been recorded. Open Evidence and attach statements to original source records.</div>';
 return '<div class="analyst-intro"><div><div class="eyebrow">DELIVERABLE / ANALYST-ASSESSED FINDINGS</div><h2>Write the answer, not a database dump.</h2><p>Explain what is known, what remains uncertain, and the evidence supporting each conclusion.</p></div><a class="btn small" target="_blank" rel="noopener" href="/api/cases/'+h(s.id)+'/report-v4.html">Preview evidence report ↗</a></div>'+
 '<div class="grid2"><section class="panel"><div class="panel-head"><div class="panel-title">Case assessment</div><span class="tag">'+h(a.status||'open')+'</span></div><form id="assessment-form" class="panel-pad input-stack"><label class="field-label">Executive summary</label><textarea name="executive_summary" maxlength="2400" placeholder="Answer the original question in language the reader can act upon…">'+h(a.executive_summary||'')+'</textarea><label class="field-label">Findings and analyst interpretation</label><textarea name="assessment" maxlength="5000" placeholder="Which evidence supports or disputes your conclusions?">'+h(a.assessment||'')+'</textarea><label class="field-label">Limitations and uncertainties</label><textarea name="limitations" maxlength="2000" placeholder="Missing sources, similar names, unverifiable claims, collection limits">'+h(a.limitations||'')+'</textarea><label class="field-label">Next recommended research actions</label><textarea name="next_actions" maxlength="2000" placeholder="Concrete next step to resolve remaining unknowns">'+h(a.next_actions||'')+'</textarea><label class="field-label">Investigation status</label><select name="status">'+['open','researching','awaiting_review','completed'].map(v=>'<option value="'+v+'" '+(a.status===v?'selected':'')+'>'+h(v.replaceAll('_',' '))+'</option>').join('')+'</select><button class="btn primary">Save assessment</button><p class="help">Completed cases require substantive summary and analysis; case conclusions remain analyst opinions.</p></form></section>'+
 '<section class="panel"><div class="panel-head"><div class="panel-title">Attributed research claims</div><span class="tag">'+claims.length+' statements</span></div>'+claimItems+
 '<div class="insight"><h3>Evidence quality check</h3><p>'+Number(metrics.reviewed||0)+' of '+Number(metrics.records||0)+' source records classified, '+Number(metrics.failedQueries||0)+' failed external queries and '+(s.candidates||[]).length+' candidate identity groups. A recorded claim still requires human checking that its source supports it.</p></div></section></div>';
}

function caseReports(){
 const id=h(s.id),ass=s.intel?.assessment||{};
 const ready=ass.status==='completed';
 return '<div class="analyst-intro"><div><div class="eyebrow">DELIVERABLES / REPRODUCIBLE SOURCE RECORDS</div><h2>Investigation report</h2><p>Your report includes the analyst assessment, candidate hypotheses, source-linked assertions, evidence and search coverage.</p></div></div>'+
 '<div class="grid2"><section class="panel panel-pad"><div class="badge-row">'+tag(ready?'ok':'draft')+'</div><h3>'+h(s.case.case.title)+'</h3><p class="page-sub">'+h(ass.executive_summary||'Draft: no executive assessment yet. Add an answer in Analyst findings before sharing this report.')+'</p><div class="reportlinks" style="margin:20px 0"><a class="btn primary" target="_blank" rel="noopener" href="/api/cases/'+id+'/report-v4.pdf">Download assessment PDF</a><a class="btn" target="_blank" rel="noopener" href="/api/cases/'+id+'/report-v4.html">Review HTML report ↗</a><a class="btn subtle" target="_blank" rel="noopener" href="/api/cases/'+id+'/report.json">Raw evidence JSON ↗</a></div><p class="help">A report may be a useful negative finding: insufficient evidence is a legitimate outcome. Do not invent identity certainty.</p></section>'+
 '<section class="panel panel-pad"><h3>Before distributing</h3><div class="input-stack"><div class="sourcehealth">Confirm the intended subject and distinguish namesakes.</div><div class="sourcehealth">Review whether each material claim is supported by the linked source.</div><div class="sourcehealth">Record unavailable sources, dates and contradictions.</div><div class="sourcehealth">Remove unsupported allegations and unnecessary personal information.</div></div></section></div>';
}

function caseActivity(){
 const q=s.researchRuns||[],recent=s.case.runs||[];
 return '<div class="analyst-intro"><div><div class="eyebrow">AUDITABILITY / EXTERNAL SOURCE COVERAGE</div><h2>What did the platform search?</h2><p>Every V4 research request is recorded with its exact query, provider, result count and error. Source coverage is not universal.</p></div><button class="btn small" data-collect>Repeat research ↻</button></div>'+
 '<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div class="panel-title">V4 source queries ('+q.length+')</div><span class="panel-meta">LATEST 250</span></div>'+
 (q.length?q.map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.provider)+' · '+h(x.query_text)+'</strong><div class="item-sub">'+h(when(x.created_at))+' · '+h(x.message||'No details')+'</div></div><div class="badge-row">'+tag(x.status)+'<span class="tag">'+Number(x.returned_count)+' returned</span><span class="tag">'+Number(x.new_count)+' new</span></div></div>').join(''):
 '<div class="empty">No planned queries executed. Begin from Overview to understand what will be searched.</div>')+'</section>'+
 '<section class="panel"><div class="panel-head"><div class="panel-title">Previous collector activity</div></div>'+
 (recent.length?recent.slice(0,35).map(x=>'<div class="item-row"><div class="row-main"><strong>'+h(x.provider)+'</strong><div class="item-sub">'+h(x.message||'No status')+' · '+h(when(x.ran_at))+'</div></div>'+tag(x.state)+'</div>').join(''):
 '<div class="empty">No legacy collector activity.</div>')+'</section>';
}

function sources(){return heading('INTEGRATION REGISTRY','Source integrations','Connected APIs are separate from referenced upstream products.')+'<div class="insight"><h3>Honest source coverage</h3><p><strong>'+s.sources.length+'</strong> implemented adapters can return data. <strong>'+s.projects.length+'</strong> external products are reference links only, not installed tools. Each source can fail or return unverified candidates.</p></div><div class="section-row"><h2 class="section-heading">Integrated adapters</h2><span class="tag ok">Working connector implementations</span></div><div class="grid-equal">'+s.sources.map(x=>'<article class="panel panel-pad"><div class="badge-row">'+tag('configured')+'<span class="mono">'+h(x.scope.join(', '))+'</span></div><h3>'+h(x.title)+'</h3><p class="page-sub">'+h(x.description)+'</p><p class="help">'+h(x.terms)+'</p>'+link(x.url,'Provider documentation')+'</article>').join('')+'</div><div class="section-row"><h2 class="section-heading">External open-source references</h2><span class="tag warn">Not integrated</span></div><div class="grid-equal">'+s.projects.map(x=>'<article class="panel panel-pad"><span class="tag warn">Reference only</span><h3>'+h(x.name)+'</h3><p class="page-sub">'+h(x.strength)+'</p><p class="help">'+h(x.integration)+' · '+h(x.license)+'</p>'+link(x.repo,'Review repository')+(x.live?' · '+link(x.live,'Original site'):'')+'</article>').join('')+'</div>'}
function settings(){return heading('OPERATIONS','Settings & security','Live provider configuration and documented pilot limitations.')+'<div class="grid-equal"><section class="panel"><div class="panel-head"><div class="panel-title">Model configuration</div></div><div class="panel-pad">'+[['GroqCloud',s.server.groqConfigured],['xAI Grok',s.server.aiConfigured],['TfL camera feed',s.server.tflConfigured]].map(x=>'<div class="sourcehealth">'+h(x[0])+tag(x[1]?'configured':'not_configured')+'</div>').join('')+'<p class="help">Credentials are stored on Render, never in this browser. A configured key does not guarantee provider availability or quota.</p><button class="btn warn" data-logout>Sign out</button><div class="divider"></div><p class="help">User accounts and case ownership are stored in the database. Non-admin analysts can access only their own cases.</p></div></section><section class="panel"><div class="panel-head"><div class="panel-title">Current release scope</div></div><div class="panel-pad"><div class="callout warn">Free Render SQLite storage is ephemeral. Do not enter personal customer investigation data. No enterprise multi-tenant authorization, durable data retention, or completed security audit.</div><p class="page-sub" style="margin-top:15px">Public sources may be stale, inaccurate, or unavailable. Do not infer risk scores or automatic identity verification.</p><a class="btn" href="/api/docs" target="_blank" rel="noopener">API reference ↗</a></div></section></div>'}
function administration(){
 if(s.user?.role!=='admin')return '<div class="callout warn">Administrator access required.</div>';
 return heading('SECURITY OPERATIONS','Analyst accounts','Create individual access instead of sharing administrator credentials.')+
 '<div class="grid2"><div class="panel"><div class="panel-head"><strong class="panel-title">Users</strong></div>'+
 (s.users?.length?s.users.map(x=>'<div class="item-row"><div class="row-main"><div class="item-title">'+h(x.username)+'</div><div class="item-sub">'+h(x.role)+'</div></div>'+tag(x.active?'ok':'error')+'</div>').join(''):'<div class="empty">No user records loaded.</div>')+
 '</div><section class="panel"><div class="panel-head"><strong class="panel-title">Create account</strong></div><form class="panel-pad input-stack" id="user-form"><input name="username" required minlength="3" maxlength="60" placeholder="Username"><input name="password" type="password" minlength="12" required autocomplete="new-password" placeholder="Initial password (12+ characters)"><select name="role"><option value="analyst">Analyst</option><option value="admin">Administrator</option></select><button class="btn primary">Create user</button><p class="help">Share the password securely; it is never returned by the API.</p></form></section></div>';
}
function world(){return heading('GEO INTELLIGENCE','World intelligence','Source-labeled natural events and public-authority camera metadata; not universal live tracking.')+'<div class="toolbar" style="margin:20px 0"><label class="field-label" style="margin:0">Source layer</label><select id="geo-feed">'+[['earthquakes','USGS · Earthquakes'],['nasa','NASA · Natural events'],['caltrans','Caltrans · Cameras (metadata)'],['tfl','TfL · London JamCams']].map(([id,name])=>'<option value="'+id+'" '+(s.feed===id?'selected':'')+'>'+name+'</option>').join('')+'</select><button class="btn small" data-refresh>Refresh source</button><span class="tag">'+s.geo.length+' records</span></div><div class="world-layout"><section class="panel"><div class="panel-head"><div class="panel-title">Geographic observations</div><span class="panel-meta">'+h(s.feed.toUpperCase())+'</span></div><div class="map" id="geo-map"><div class="map-fallback">Loading map library…</div></div></section><section class="panel"><div class="panel-head"><div class="panel-title">Observed records</div>'+tag(s.geoStatus)+'</div><div class="world-list">'+(s.geoError?'<div class="callout warn">'+h(s.geoError)+'</div>':'')+(s.geo.length?s.geo.slice(0,100).map((x,k)=>'<div class="world-item"><strong>'+h(x.name||'Event')+'</strong><span>'+h(x.provider)+' · '+h(when(x.observedAt))+'</span><div style="margin-top:10px">'+link(x.url,'Official source')+' <button class="btn small subtle" data-locate="'+k+'">Locate</button></div></div>').join(''):'<div class="empty">No records available for this source. Source errors are shown explicitly.</div>')+'</div></section></div><div class="insight"><h3>Map provenance</h3><p>Only the selected official feed populates this map. OSIRIS, World Monitor, God’s Eye View, Argus and CamForge are reference links, not live merged services. Camera entries are publisher metadata, not unrestricted streams.</p></div>'}
let map=null,marks={};
function drawMap(){const el=document.getElementById('geo-map');if(!el)return;if(map){try{map.remove()}catch{}map=null}if(!window.L){el.innerHTML='<div class="map-fallback">Map library unavailable. Use the source list instead.</div>';return}
map=window.L.map(el,{worldCopyJump:true}).setView([18,8],2);window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:17}).addTo(map);const bounds=[];marks={};s.geo.forEach((x,k)=>{const lat=Number(x.lat),lon=Number(x.lon);if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)return;const marker=window.L.circleMarker([lat,lon],{radius:5,color:'#a2b4ff',weight:1.4,fillOpacity:.7}).addTo(map);marker.bindPopup('<strong>'+h(x.name||'Observation')+'</strong><p>'+h(x.provider)+'</p>'+link(x.url,'Original source'));marks[k]=marker;bounds.push([lat,lon])});if(bounds.length&&bounds.length<400)map.fitBounds(bounds,{padding:[32,32],maxZoom:6})}
function render(){if(!s.user){login();return}app.innerHTML=frame(({home,cases,case:casePage,world,sources,settings,admin:administration}[s.where]||home)());if(s.where==='world')setTimeout(drawMap,0);if(s.where==='case'&&s.tab==='assistant'){const e=document.getElementById('chat-history');if(e)e.scrollTop=e.scrollHeight}}
async function refreshCases(){const [ca,ov]=await Promise.all([api('/api/cases'),api('/api/overview')]);s.cases=ca.items||[];s.overview=ov}
async function openCase(id){s.where='case';s.id=id;s.tab='overview';s.messages=[];s.sessionId=null;s.conversations=[];s.selected=null;s.webSearch=false;s.evidenceSelected=[];s.evidenceSearch='';s.evidenceFilter='all';s.lastResearch=null;await fetchCase();s.provider=(s.server.groqConfigured&&s.case.case.ai_opt_in)?'groq':'local';await loadResearchState();render()}
async function loadResearchState(){
 const [tr,conv,history,researchPlan,runs,candidates,intel]=await Promise.all([
   api('/api/cases/'+s.id+'/triage'),
   api('/api/cases/'+s.id+'/conversations'),
   api('/api/cases/'+s.id+'/search-history'),
   api('/api/cases/'+s.id+'/research-plan?depth='+s.depth),
   api('/api/cases/'+s.id+'/research-history'),
   api('/api/cases/'+s.id+'/candidates'),
   api('/api/cases/'+s.id+'/intelligence')
 ]);
 s.triage=tr;s.conversations=conv.items||[];s.searchHistory=history.items||[];
 s.researchPlan=researchPlan;s.researchRuns=runs.items||[];s.candidates=candidates.items||[];s.intel=intel;
 if(s.conversations.length)await loadConversation(s.conversations[0].id);
}
async function loadConversation(id){
 const result=await api('/api/cases/'+s.id+'/conversations/'+id);
 s.sessionId=result.session.id;
 s.messages=(result.messages||[]).map(m=>({
   role:m.role,text:m.text,model:m.provider,ids:m.ids||[],webLeads:m.webLeads||[],
   webSearch:!!m.webLeads?.length
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
async function launch(form){const d=Object.fromEntries(new FormData(form).entries());s.busy=true;render();try{const ca=await api('/api/cases',{method:'POST',body:{title:modes[s.mode].name+' · '+d.query.trim(),subject_type:s.mode,query:d.query.trim(),purpose:d.purpose.trim(),authority_confirmed:!!d.authority,ai_opt_in:!!d.ai_opt_in,city:d.city||'',organization:d.organization||'',profession:d.profession||'',public_handle:d.public_handle||''}});await refreshCases();await openCase(ca.id);try{await collect()}catch(err){toast('Case created, but source lookup failed: '+err.message,true)}}finally{s.busy=false;render()}}
async function loadGeo(){s.geoStatus='loading';s.geoError='';render();try{const out=await api(['earthquakes','nasa'].includes(s.feed)?'/api/geo/events?feed='+s.feed:'/api/geo/cameras?provider='+(s.feed==='caltrans'?'caltrans':'tfl'));s.geo=out.items||[];s.geoStatus=out.status||'ok';s.geoError=out.note||out.message||''}catch(err){s.geo=[];s.geoError=err.message;s.geoStatus='unavailable'}render()}
async function init(){const auth=await api('/api/auth/me');s.user=auth.user;s.server=auth;const [ca,ov,so,pr,cap]=await Promise.all([api('/api/cases'),api('/api/overview'),api('/api/sources'),api('/api/projects'),api('/api/capabilities')]);s.cases=ca.items||[];s.overview=ov;s.sources=so.items||[];s.projects=pr.items||[];s.capabilities=cap;if(s.user?.role==='admin')s.users=(await api('/api/users')).items;s.where='home';render()}
document.addEventListener('click',async e=>{const t=e.target.closest('button[data-nav],button[data-mode],button[data-tab],button[data-open],button[data-evidence],button[data-collect],button[data-add],button[data-refresh],button[data-locate],button[data-question],button[data-consent],button[data-webstart],button[data-websave],button[data-newchat],button[data-go-evidence],button[data-logout]');if(!t)return;try{
if(t.dataset.nav){s.where=t.dataset.nav;render();if(s.where==='world'&&s.geoStatus==='idle')await loadGeo()}
else if(t.dataset.mode){s.mode=t.dataset.mode;s.where='home';render();document.getElementById('query')?.focus()}
else if(t.dataset.tab){s.tab=t.dataset.tab;render()}
else if(t.dataset.open)await openCase(t.dataset.open)
else if(t.dataset.evidence){s.selected=t.dataset.evidence;render()}
else if(t.dataset.goEvidence){s.tab='evidence';s.selected=t.dataset.goEvidence;render()}
else if(t.hasAttribute('data-newchat')){s.sessionId=null;s.messages=[];render()}
else if(t.hasAttribute('data-collect'))await collect()
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
document.addEventListener('change',async e=>{if(e.target.id==='ai-provider'){s.provider=e.target.value;render()}if(e.target.id==='geo-feed'){s.feed=e.target.value;await loadGeo()}if(e.target.id==='research-web'){s.webSearch=!!e.target.checked;render()}if(e.target.id==='conversation-select'){if(e.target.value)await loadConversation(e.target.value);else{s.sessionId=null;s.messages=[];render()}}
if(e.target.id==='research-depth'){s.depth=e.target.value;s.researchPlan=await api('/api/cases/'+s.id+'/research-plan?depth='+s.depth);render()}
if(e.target.id==='evidence-status'){s.evidenceFilter=e.target.value;render()}
if(e.target.id==='evidence-search'){s.evidenceSearch=e.target.value.trim().slice(0,160);render()}
if(e.target.dataset?.pickEvidence){
 const val=e.target.dataset.pickEvidence;
 s.evidenceSelected=e.target.checked?[...new Set([...s.evidenceSelected,val])]:s.evidenceSelected.filter(x=>x!==val);
 render()
}});
document.addEventListener('submit',async e=>{const f=e.target;if(!(['login-form','start-form','review-form','manual-form','ask-form','context-form','user-form','claim-form','assessment-form','bulk-review-form','candidate-create-form'].includes(f.id)||!!f.dataset?.candidateReview||!!f.dataset?.candidateLink))return;e.preventDefault();if(s.busy)return;const button=f.querySelector('button[type="submit"]')||f.querySelector('button');if(button)button.disabled=true;try{
if(f.id==='login-form'){const d=Object.fromEntries(new FormData(f).entries());await api('/api/auth/login',{method:'POST',body:d});await init();toast('Signed in.')}
if(f.id==='start-form')await launch(f);
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
if(f.id==='assessment-form'){
 const d=Object.fromEntries(new FormData(f).entries());
 await api('/api/cases/'+s.id+'/assessment',{method:'PUT',body:d});
 s.intel=await api('/api/cases/'+s.id+'/intelligence');render();
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
 await fetchCase();const [tr,rp]=await Promise.all([api('/api/cases/'+s.id+'/triage'),api('/api/cases/'+s.id+'/research-plan?depth='+s.depth)]);s.triage=tr;s.researchPlan=rp;s.intel=await api('/api/cases/'+s.id+'/intelligence');render();
 toast('Identity clues updated. Candidates reranked for analyst review.');
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
   {method:'POST',body:{provider:s.provider,question:q,history,web_search:!!(s.webSearch&&s.provider==='groq'),session_id:s.sessionId}});
 s.sessionId=r.sessionId||s.sessionId;
 s.conversations=(await api('/api/cases/'+s.id+'/conversations')).items;
 s.messages.push({role:'assistant',text:r.answer,model:r.model,ids:r.evidenceIds||[],
                  followUp:r.followUp||'',needsDisambiguation:!!r.needsDisambiguation,webSearch:!!r.webSearch,webLeads:r.webLeads||[]});
 s.busy=false;render();
}
}catch(err){s.busy=false;toast(err.message,true);if(f.id==='login-form'){const el=document.getElementById('login-error');if(el)el.textContent=err.message}else if(f.id==='ask-form'){s.messages.push({role:'assistant',text:'The AI provider could not complete this request: '+err.message,model:'Provider error',error:true});render()}}finally{if(button)button.disabled=false}});
init().catch(()=>login());
})();
