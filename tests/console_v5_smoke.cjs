/* Regression: creating a case must actually execute the initial source research. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let listeners={},markup='',researchRuns=0,agentSteps=0;
const caseId='synthetic-case';
const root={set innerHTML(v){markup=v},get innerHTML(){return markup}};
const document={
 getElementById(id){return id==='app'?root:null},
 addEventListener(name,fn){listeners[name]=fn},
 createElement(){return {className:'',textContent:'',remove(){}}},
 body:{append(){}}
};
const api={
 '/api/auth/me':{user:{id:'admin',username:'admin',role:'admin'},groqConfigured:false,aiConfigured:false},
 '/api/cases':{items:[]},
 '/api/overview':{cases:0,evidence:0,corroborated:0},
 '/api/sources':{items:[{id:'github',title:'GitHub',scope:['person'],terms:'API',description:'Public'}]},
 '/api/projects':{items:[]},
 '/api/capabilities':{},
 '/api/users':{items:[{id:'admin',username:'admin',role:'admin',active:1}]},
 ['/api/cases/'+caseId]:{case:{id:caseId,title:'Person · Ada Example',query:'Ada Example',
  subject_type:'person',purpose:'Authorized public research',ai_opt_in:false},evidence:[],runs:[],
  context:{city:'Delhi',organization:'',profession:'',public_handle:''}},
 ['/api/cases/'+caseId+'/brief']:{total:0,counts:{corroborated:0}},
 ['/api/cases/'+caseId+'/triage']:{candidates:[]},
 ['/api/cases/'+caseId+'/conversations']:{items:[]},
 ['/api/cases/'+caseId+'/search-history']:{items:[]},
 ['/api/cases/'+caseId+'/research-plan?depth=standard']:{queries:[{provider:'github',query:'Ada Example',reason:'Name'}]},
 ['/api/cases/'+caseId+'/research-history']:{items:[]},
 ['/api/cases/'+caseId+'/candidates']:{items:[]},
 ['/api/cases/'+caseId+'/intelligence']:{assessment:{status:'open'},metrics:{records:0,reviewed:0,failedQueries:0},claims:[]},
 '/api/research/providers':{web:{configured:false}},
 ['/api/cases/'+caseId+'/research']:{returned:2,new:1,errors:0}
};
const requests=[];
const fetch=async(url,init={})=>{
 requests.push({url,method:init.method||'GET'});
 let result=url==='/api/cases'&&init.method==='POST'?{id:caseId}:api[url]||{};
 if(url==='/api/cases/'+caseId+'/jobs'&&init.method==='POST')result={id:'job-test',status:'ready'};
 if(url==='/api/cases/'+caseId+'/jobs'&&init.method!=='POST')result={items:[{id:'job-test',objective:'Find relevant public engineering work and isolate namesakes',status:agentSteps>=2?'completed':'ready',mode:'guided',completed_steps:agentSteps,max_steps:2,updated_at:'2026-10-25'}]};
 if(url==='/api/cases/'+caseId+'/jobs/job-test'&&init.method==='GET')result={id:'job-test',objective:'Find relevant public engineering work and isolate namesakes',status:agentSteps>=2?'completed':'ready',mode:'guided',completedSteps:agentSteps,maxSteps:2,steps:[]};
 if(url==='/api/cases/'+caseId+'/jobs/job-test/step'&&init.method==='POST'){
  agentSteps++;
  result={id:'job-test',objective:'Find relevant public engineering work and isolate namesakes',status:agentSteps>=2?'completed':'ready',mode:'guided',completedSteps:agentSteps,maxSteps:2,steps:[]};
 }
 if(url==='/api/cases/'+caseId+'/excerpts')result={items:[]};
 if(url==='/api/cases/'+caseId+'/research'&&init.method==='POST')researchRuns++;
 return {ok:true,status:200,headers:{get(){return 'application/json'}},json:async()=>result}
};
class FormData{constructor(form){this.form=form}entries(){return Object.entries(this.form.fields)}}
const env={document,window:{},fetch,FormData,URL,console,setTimeout,clearTimeout};
vm.runInNewContext(fs.readFileSync('static/console.js','utf8'),env);
const form={
 id:'start-form',dataset:{},fields:{
 query:'Ada Example',purpose:'Authorized public professional information research',
 authority:'on',city:'Delhi'
 },querySelector(){return null}
};
(async()=>{
 await new Promise(resolve=>setTimeout(resolve,65));
 assert(markup.includes('Find relevant public records.'));
 await listeners.submit({target:form,preventDefault(){}});
 assert.strictEqual(researchRuns,1,'New case creation skipped its first source research run');
 assert(markup.includes('Transparent research plan'),'Case overview did not render');
 assert(requests.some(x=>x.url==='/api/research/providers'),'Web integration configuration not fetched');
 await listeners.click({target:{closest(){return {dataset:{tab:'investigate'},hasAttribute(){return false}}}}});
 assert(markup.includes('New investigation run'),'agent planner form missing');
 const jobForm={id:'job-form',dataset:{},fields:{
   objective:'Find relevant public engineering work and isolate namesakes',
   mode:'guided',max_steps:'2',consent:'on'},querySelector(){return null}};
 await listeners.submit({target:jobForm,preventDefault(){}});
 assert.strictEqual(agentSteps,2,'Guided investigation did not execute its two saved source steps');
 assert(markup.includes('Current investigation'),'Completed source workflow not visible');
 console.log('V7 UI smoke: first search, investigation planner, two source steps PASS');
})().catch(error=>{console.error(error);process.exitCode=1});
