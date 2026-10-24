/* Dependency-free render smoke test. Mock responses, never fake provider data. */
const fs=require('fs');const vm=require('vm');const assert=require('assert');
let view='';const handlers={};
const app={set innerHTML(s){view=s},get innerHTML(){return view}};
const document={getElementById(id){return id==='app'?app:null},addEventListener(kind,fn){handlers[kind]=fn},createElement(){return {style:{},remove(){},textContent:''}},body:{append(){}}};
const data={
 '/api/auth/me':{user:{username:'admin',role:'admin'},aiConfigured:false,tflConfigured:false},
 '/api/sources':{items:[{id:'github',title:'GitHub',scope:['person'],description:'Public profiles',terms:'Public API',url:'https://github.com'}]},
 '/api/projects':{items:[{id:'osiris',name:'OSIRIS',category:'Geo intelligence',strength:'Map layers',repo:'https://github.com/simplifaisoul/osiris',license:'MIT'}]},
 '/api/overview':{cases:1,evidence:2,corroborated:0,sources:1,projects:1,recent:[],runs:[]},
 '/api/cases':{items:[]},'/api/audit':{items:[]},
};
const fetch=async(u)=>({ok:true,headers:{get(){return 'application/json'}},json:async()=>data[u]||{},status:200});
const ctx={document,fetch,URL,console,setTimeout,clearTimeout,window:{open(){}}};
vm.runInNewContext(fs.readFileSync('static/app.js','utf8'),ctx);
setTimeout(()=>{
 try{assert(view.includes('Intelligence overview'),'overview missing');assert(view.includes('Open Source Library'),'sidebar missing');assert(view.includes('Recent investigations'),'panel missing');assert(view.includes('Evidence records'),'metric missing');console.log('Frontend render smoke test passed.');process.exit(0)}catch(e){console.error(e);process.exit(1)}
},110);
