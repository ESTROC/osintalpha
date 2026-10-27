/* V7.9 smoke: one natural-language query routes sources and reaches evidence-grounded AI. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let markup='',listeners={},requests=[],smartBodies=[];
const cid='new-case-v79';
const app={set innerHTML(v){markup=v},get innerHTML(){return markup}};
const responses={
 '/api/auth/me':{user:{id:'admin',username:'admin',role:'admin'},groqConfigured:true,aiConfigured:false},
 '/api/cases':{items:[]},
 '/api/overview':{cases:0,evidence:0,corroborated:0},
 '/api/sources':{items:[]},'/api/projects':{items:[]},'/api/capabilities':{},
 '/api/users':{items:[]},
 '/api/research/providers':{web:{configured:true}},
 ['/api/cases/'+cid]:{case:{id:cid,title:'Investigation - Example Person',subject_type:'person',query:'Example Person',purpose:'Authorized public research',ai_opt_in:1},context:{},evidence:[{id:'sample-evidence',label:'Public account candidate',summary:'Possible namesake',provider:'github',status:'candidate',source_url:'https://github.com/candidate',fetched_at:'2026-10-27'}],runs:[]},
 ['/api/cases/'+cid+'/brief']:{total:1,counts:{corroborated:0}},
 ['/api/cases/'+cid+'/conversations']:{items:[]},
 ['/api/cases/'+cid+'/collect']:{results:[{provider:'github',status:'ok',new:1}]},
 ['/api/cases/'+cid+'/chat']:{answer:'The account is only a candidate and not proven the subject.',model:'groq-test-model',provider:'groq',evidenceIds:['sample-evidence'],webLeads:[{title:'Public source',url:'https://example.org/source'}],braveContextUsed:true,webSearch:true,sessionId:'s1'}
};
const document={
 getElementById(id){return id==='app'?app:null},
 addEventListener(k,fn){listeners[k]=fn},
 createElement(){return {remove(){},set className(x){},set textContent(x){}}},
 body:{append(){}}
};
const fetch=async(url,init={})=>{
 requests.push({url,method:init.method||'GET'});
 if(url==='/api/search/start')return response({id:cid,plan:{subjectType:'person',subject:'Ayush cybersecurity Indian Navy',providers:[],deferExternalSearch:true,clarification:'Please supply a full public name or public handle.',aiPlanned:false,caveat:'Unverified subject'},braveConfigured:true,groqConfigured:true});
 if(url==='/api/cases/'+cid+'/chat')smartBodies.push(JSON.parse(init.body));
 return response(responses[url]||{});
};
function response(data){return {ok:true,status:200,headers:{get(){return 'application/json'}},json:async()=>data};}
class FormData{constructor(form){this.form=form}entries(){return Object.entries(this.form.fields)}}
const env={document,window:{},fetch,FormData,URL,console,setTimeout,clearTimeout};
vm.runInNewContext(fs.readFileSync('static/console.js','utf8'),env);
(async()=>{
 await new Promise(done=>setTimeout(done,80));
 assert(markup.includes('Search beyond the obvious.'),'Primary smart search not displayed');
 assert(markup.includes('smart-search-form'),'Single-search form missing');
 assert(markup.includes('mission-map'),'Homepage geo map panel missing');
 assert(!markup.includes('Ayush cybersecurity'),'A personal demo query leaked into the live search placeholder');
 assert(markup.includes('Manual research workspace'),'Advanced/manual search not retained');
 const form={id:'smart-search-form',dataset:{},fields:{
  question:'Ayush cybersecurity Indian Navy',
  authority:'on',ai_opt_in:'on',
  purpose:'Authorized public-source due diligence'
 },querySelector(){return null}};
 await listeners.submit({target:form,preventDefault(){}});
 assert(requests.some(x=>x.url==='/api/search/start'),'Natural-language route not invoked');
 assert(!requests.some(x=>x.url==='/api/cases/'+cid+'/collect'),'Ambiguous given name should not collect source records');
 assert(!requests.some(x=>x.url==='/api/cases/'+cid+'/web-discovery'),'Clarification must precede Brave search');
 assert.strictEqual(smartBodies.length,0,'Clarification must precede Groq answer');
 assert(markup.includes('Please supply a full public name or public handle.'),'Clarification prompt absent');
 assert(markup.includes('Clarification required before external research'),'Safe abstention state absent');
 assert(markup.includes('Public account candidate'),'Source trace missing');
 assert(markup.includes('More analyst tools'),'Advanced controls missing');
 assert(markup.includes('Brave Web'),'Provider-specific diagnostic missing');
 assert(markup.includes('GEOSPATIAL CONTEXT'),'Public city map context panel missing');
 console.log('P1 clarification smoke: no paid calls before first-name disambiguation PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
