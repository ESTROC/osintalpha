/* V3 current-console render and navigation smoke test. No provider data fabricated for users. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let html='',handlers={};
const app={set innerHTML(x){html=x},get innerHTML(){return html}};
const document={
 getElementById(id){return id==='app'?app:null},
 addEventListener(n,cb){handlers[n]=cb},
 createElement(){return {className:'',textContent:'',remove(){}}},
 body:{append(){}}
};
const mock={
 '/api/auth/me':{user:{id:'admin-test',username:'admin',role:'admin'},groqConfigured:true,aiConfigured:false,tflConfigured:false},
 '/api/cases':{items:[]},
 '/api/overview':{cases:0,evidence:0,corroborated:0},
 '/api/sources':{items:[{id:'github',title:'GitHub',scope:['person','organization'],description:'Public candidate accounts',terms:'API',url:'https://github.com'}]},
 '/api/projects':{items:[]},
 '/api/capabilities':{workflows:[],integratedSources:1,referencesOnly:0},
 '/api/users':{items:[{id:'admin-test',username:'admin',role:'admin',active:1}]}
};
const fetch=async url=>({ok:true,status:200,headers:{get(){return 'application/json'}},json:async()=>mock[url]||{}});
const sandbox={document,window:{},fetch,URL,console,setTimeout,clearTimeout};
vm.runInNewContext(fs.readFileSync('static/console.js','utf8'),sandbox);
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function click(key,value){
 const target={dataset:{[key]:value},hasAttribute(n){return false}};
 await handlers.click({target:{closest(){return target}}});
 await sleep(15);
}
(async()=>{
 await sleep(120);
 assert(html.includes('Research the open world'),'home not rendered');
 assert(html.includes('name="city"'),'identity clue form missing');
 assert(html.includes('Analyst accounts'),'admin navigation missing');
 assert(!html.includes('Researching forever'));
 await click('nav','admin');
 assert(html.includes('Create account'),'admin create flow missing');
 assert(html.includes('name="password"'),'user password field missing');
 await click('nav','cases');
 assert(html.includes('No saved cases'),'empty case state missing');
 console.log('V3 console smoke: home, clues, admin, cases PASS');
})().catch(err=>{console.error(err);process.exitCode=1});
