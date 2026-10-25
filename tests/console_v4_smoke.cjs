/* V4 UI smoke: verifies rendered analyst journey with mock API, not browser E2E. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let markup='',listeners={};const root={set innerHTML(v){markup=v},get innerHTML(){return markup}};
const document={
 getElementById(id){return id==='app'?root:null},
 addEventListener(name,fn){listeners[name]=fn},
 createElement(){return {className:'',textContent:'',remove(){}}},
 body:{append(){}}
};
const caseId='case-synthetic-1';
const record={id:'record-1',provider:'github',label:'Sample Engineer',
 summary:'Public profile candidate, not identity verification',
 status:'candidate',source_url:'https://github.com/example',sha256:'testhash',
 fetched_at:'2026-10-25T09:00:00Z',reviewer_notes:''};
const assessment={case_id:caseId,status:'researching',executive_summary:'',
 assessment:'',limitations:'',next_actions:''};
const mocks={
 '/api/auth/me':{user:{id:'u1',username:'admin',role:'admin'},groqConfigured:true,aiConfigured:false},
 '/api/cases':{items:[{id:caseId,title:'Sample background review',subject_type:'person',query:'Sample Person',created_at:'2026-10-25',evidence_count:1}]},
 '/api/overview':{cases:1,evidence:1,corroborated:0},
 '/api/sources':{items:[{id:'github',title:'GitHub',scope:['person'],description:'Public profiles',
    terms:'API rules',url:'https://github.com'}]},
 '/api/projects':{items:[]},
 '/api/capabilities':{workflows:[]},
 '/api/users':{items:[{id:'u1',username:'admin',role:'admin',active:1}]},
 ['/api/cases/'+caseId]:{case:{id:caseId,title:'Sample background review',subject_type:'person',
    query:'Sample Person',purpose:'Authorized example research',ai_opt_in:true},
    evidence:[record],context:{city:'Delhi',organization:'Sample Labs',profession:'engineer',public_handle:'sample'},
    runs:[]},
 ['/api/cases/'+caseId+'/brief']:{total:1,counts:{candidate:1,corroborated:0},sourceStates:{}},
 ['/api/cases/'+caseId+'/triage']:{candidates:[{id:'record-1',label:'Sample Engineer',
    provider:'github',relevance:3,signals:['city'],status:'candidate'}]},
 ['/api/cases/'+caseId+'/conversations']:{items:[]},
 ['/api/cases/'+caseId+'/search-history']:{items:[]},
 ['/api/cases/'+caseId+'/research-plan?depth=standard']:{queries:[
     {provider:'github',query:'Sample Person',reason:'Original subject query'},
     {provider:'github',query:'sample',reason:'Known public handle'}]},
 ['/api/cases/'+caseId+'/research-history']:{items:[{provider:'github',query_text:'Sample Person',
    returned_count:1,new_count:1,status:'ok',created_at:'2026-10-25',message:'1 candidate'}]},
 ['/api/cases/'+caseId+'/candidates']:{items:[{id:'candidate-1',display_name:'Sample Person · Delhi',
    classification:'unresolved',reason:'Unknown account association',sources:[]}]},
 ['/api/cases/'+caseId+'/intelligence']:{assessment,metrics:{records:1,reviewed:0,
    failedQueries:0},claims:[],evidence:[record],candidates:[]}
};
const fetch=async path=>({ok:true,status:200,headers:{get(){return 'application/json'}},json:async()=>mocks[path]||{}});
const win={L:null}; const context={document,window:win,fetch,URL,console,setTimeout,clearTimeout};
vm.runInNewContext(fs.readFileSync('static/console.js','utf8'),context);
async function sleep(){await new Promise(r=>setTimeout(r,25))}
async function click(dataset,value){
 const target={dataset:{[dataset]:value},hasAttribute(){return false}};
 await listeners.click({target:{closest(){return target}}});await sleep();
}
(async()=>{
 await sleep();assert(markup.includes('Find relevant public records.'));
 await click('open',caseId);
 assert(markup.includes('Transparent research plan'),'research plan not displayed');
 assert(markup.includes('Sample Labs'),'identity context missing');
 assert(markup.includes('data-deletecase'),'case deletion control missing');
 await click('tab','candidates');
 assert(markup.includes('Create an identity hypothesis'),'candidate workflow not rendered');
 assert(markup.includes('Sample Person · Delhi'),'saved hypothesis hidden');
 await click('tab','evidence');
 assert(markup.includes('bulk-review-form'),'bulk evidence review missing');
 assert(markup.includes('evidence-search'),'filter unavailable');
 await click('tab','findings');
 assert(markup.includes('assessment-form'),'assessment editor missing');
 assert(markup.includes('Attributed research claims'),'claim workspace missing');
 await click('tab','reports');
 assert(markup.includes('report-v4.pdf'),'assessment PDF link missing');
 await click('tab','activity');
 assert(markup.includes('Source changes between research runs'),'version comparison panel missing');
 assert(markup.includes('Sample Person'),'query history missing');
 console.log('V4 analyst UI smoke: landing, research plan, candidates, evidence, findings, report, history PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
