/* Separate, case-scoped agency tools; values from remote sources are untrusted. */
(()=>{'use strict';
 const root=document.getElementById('agency-output'),status=document.getElementById('agency-status');
 const state={id:new URLSearchParams(location.search).get('case')||'',offset:0,limit:25,more:false,recipes:[]};
 const $=id=>document.getElementById(id);
 const escape=x=>String(x??'').replace(/[&<>"']/g,k=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[k]));
 const available=()=>{if(!state.id)throw Error('Enter and open an authorized case ID first.');return state.id};
 function notice(message,good=true){status.textContent=message;status.className=good?'agency-ok':'agency-error'}
 function output(name,record){root.textContent=name+'\n\n'+JSON.stringify(record,null,2)}
 async function api(path,options={}){
   const method=options.method||'GET';
   const headers={};
   if(method!=='GET')headers['X-OSINT-Alpha-Action']='1';
   if(options.body!==undefined)headers['Content-Type']='application/json';
   const response=await fetch(path,{method,credentials:'same-origin',headers,
     body:options.body===undefined?undefined:JSON.stringify(options.body)});
   const contentType=response.headers.get('content-type')||'';
   const value=contentType.includes('json')?await response.json():await response.text();
   if(!response.ok)throw Error(value?.detail||value?.message||'Request failed: HTTP '+response.status);
   return value;
 }
 async function openCase(){
   const id=$('agency-case').value.trim();
   if(!/^[a-zA-Z0-9_-]{3,80}$/.test(id))throw Error('Enter a valid saved case ID.');
   const result=await api('/api/cases/'+encodeURIComponent(id));
   state.id=id;state.offset=0;history.replaceState({},'',location.pathname+'?case='+encodeURIComponent(id));
   notice('Authorized case: '+result.case.title);
   await page(); 
 }
 function sourceNode(e){
   const div=document.createElement('div');div.className='agency-source';
   const strong=document.createElement('strong');strong.textContent=e.label;
   const meta=document.createElement('small');
   meta.textContent=e.provider+' · '+e.status+' · Retrieved '+e.fetched_at+
        (e.observed_at?' · Publisher observed '+e.observed_at:' · Original date unknown');
   const link=document.createElement('a');link.className='text-link';link.textContent='Original public source';
   const u=(()=>{try{const v=new URL(e.source_url);return v.protocol==='https:'&&!v.username&&!v.password?v.href:'#'}catch{return '#'}})();
   link.href=u;link.target='_blank';link.rel='noopener noreferrer';
   div.append(strong,meta,link);
   const feedback=document.createElement('button');feedback.className='btn small subtle';feedback.textContent='Mark irrelevant for future review';
   feedback.addEventListener('click',async()=>{
     const reason=prompt('Explain why this source is irrelevant or concerns a different subject (at least 20 characters):');
     if(reason===null)return;
     if(reason.trim().length<20)throw Error('Specific relevance rationale must be at least 20 characters.');
     await api('/api/cases/'+available()+'/source-feedback',{method:'POST',
       body:{evidence_id:e.id,relevance:'irrelevant',rationale:reason.trim()}});
     notice('Analyst feedback recorded. No automatic model retraining occurred.');
   });
   div.append(feedback);return div;
 }
 async function page(){
   const data=await api('/api/cases/'+available()+'/evidence-page?limit='+state.limit+'&offset='+state.offset);
   state.more=data.hasMore;
   $('agency-page').textContent=(data.total?'Items '+(state.offset+1)+'–'+(state.offset+data.items.length):'No source records')+' of '+data.total;
   const shell=$('agency-evidence');shell.replaceChildren();
   if(!data.items.length){
     const p=document.createElement('p');p.className='help';
     p.textContent='No public source records on this page. Try a different source or verify whether earlier searches failed. No hit does not establish absence.';
     shell.append(p);
   }else data.items.forEach(x=>shell.append(sourceNode(x)));
   $('page-previous').disabled=state.offset===0;
   $('page-next').disabled=!state.more;
 }
 async function recipes(){
   const data=await api('/api/research/recipes');
   state.recipes=[...data.builtIn,...data.saved];
   const holder=$('recipe-options');holder.replaceChildren();
   for(const r of state.recipes){
     const b=document.createElement('button');b.type='button';b.className='btn small subtle';
     b.textContent=r.title;b.style.margin='0 7px 9px 0';
     b.addEventListener('click',()=>{
       document.querySelector('#recipe-form textarea[name="question"]').value=r.question;
       $('recipe-form').querySelector('input[name="title"]').value=r.title;
       notice('Procedure loaded into editor. Edit and save it, or copy the question to your main search.');
     });
     holder.append(b);
   }
 }
 function fields(form){return Object.fromEntries(new FormData(form).entries())}
 async function action(name){
   let path='';
   const id=state.id?encodeURIComponent(state.id):null;
   const map={
     timeline:'/api/cases/'+id+'/timeline',
     methodology:'/api/cases/'+id+'/methodology',
     overlap:'/api/cases/'+id+'/citation-overlap',
     preview:'/api/cases/'+id+'/export-preview?reviewed_only=true&redact_labels=true',
     pack:'/api/cases/'+id+'/evidence-pack?reviewed_only=true',
     signoffs:'/api/cases/'+id+'/signoffs',
     tasks:'/api/cases/'+id+'/tasks',
     metrics:'/api/agency/metrics',
     status:'/api/research/ops-status'
   };
   if(name==='suggest-tasks'){
     available();
     const r=await api('/api/cases/'+id+'/suggest-review-tasks',{method:'POST'});
     output('Proposed verification tasks',r);notice('Verification suggestions created: '+r.created);
     return;
   }
   if(name!=='metrics'&&name!=='status')available();
   path=map[name];if(!path)throw Error('Unknown agency tool.');
   const r=await api(path);output(name,r);
   if(name==='pack'){
     if(!confirm('Download reviewed-source JSON? Inspect identity and confidentiality before sharing.'))return;
     const blob=new Blob([JSON.stringify(r,null,2)],{type:'application/json'});
     const temp=URL.createObjectURL(blob),el=document.createElement('a');
     el.href=temp;el.download='osintalpha-reviewed-sources-'+id+'.json';
     document.body.append(el);el.click();el.remove();URL.revokeObjectURL(temp);
     notice('Reviewed-source metadata exported. This is not forensic custody or permission to distribute.');
   }else notice(name+' information retrieved.');
 }
 async function submit(form){
   const id=state.id?encodeURIComponent(state.id):'';
   const d=fields(form);
   let result;
   if(form.id==='recipe-form'){
     result=await api('/api/research/recipes',{method:'POST',body:d});
     await recipes();
   }else if(form.id==='alias-form'){
     available();result=await api('/api/cases/'+id+'/aliases',{method:'POST',body:d});
   }else if(form.id==='relationship-form'){
     available();result=await api('/api/cases/'+id+'/relationships',{method:'POST',body:d});
   }else if(form.id==='signoff-form'){
     available();result=await api('/api/cases/'+id+'/signoffs',{method:'POST',body:d});
   }else if(form.id==='compare-form'){
     available();result=await api('/api/agency/compare-cases?left='+id+'&right='+encodeURIComponent(d.right));
   }else return;
   output(form.id,result);notice(form.id+' completed with an auditable record.');
   form.reset();
 }
 function commandPalette(){
   let dialog=document.getElementById('agency-dialog');
   if(!dialog){
     dialog=document.createElement('dialog');dialog.id='agency-dialog';
     dialog.style.cssText='background:#101b2d;border:1px solid #50607d;border-radius:14px;color:#dbe7ff;padding:20px;width:min(560px,95vw)';
     const h=document.createElement('h2');h.textContent='Agency commands';
     const input=document.createElement('input');input.placeholder='Type timeline, sources, preview, status or recipes';
     input.id='agency-command';
     const hint=document.createElement('p');hint.className='help';hint.textContent='Press Enter to select a command, Escape to close.';
     dialog.append(h,input,hint);document.body.append(dialog);
     input.addEventListener('keydown',async e=>{
       if(e.key!=='Enter')return;
       e.preventDefault();
       const value=input.value.trim().toLowerCase();
       dialog.close();
       if(value==='sources'){await page();return}
       if(value==='recipes'){await recipes();return}
       const matched=['timeline','methodology','preview','pack','signoffs','status','metrics','overlap','tasks'].find(x=>x.startsWith(value)&&value.length>=2);
       if(matched)await action(matched);
       else notice('Unknown command. Try timeline, sources, preview, status or recipes.',false);
     });
   }
   dialog.showModal();dialog.querySelector('input').focus();
 }
 async function safe(fn){
   try{await fn()}catch(e){notice(e.message||String(e),false);output('Action failed',{error:e.message||String(e)})}
 }
 $('agency-case').value=state.id;
 $('agency-open').addEventListener('click',()=>safe(openCase));
 $('page-previous').addEventListener('click',()=>safe(async()=>{state.offset=Math.max(0,state.offset-state.limit);await page()}));
 $('page-next').addEventListener('click',()=>safe(async()=>{if(state.more){state.offset+=state.limit;await page()}}));
 $('agency-clear').addEventListener('click',()=>{root.textContent='No action selected.'});
 document.querySelectorAll('[data-action]').forEach(btn=>btn.addEventListener('click',()=>safe(()=>action(btn.dataset.action))));
 ['recipe-form','alias-form','relationship-form','signoff-form','compare-form'].forEach(id=>
   $(id).addEventListener('submit',e=>{e.preventDefault();safe(()=>submit(e.target))}));
 document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();commandPalette()}});
 safe(async()=>{await recipes();if(state.id)await openCase();else notice('Enter and open an authorized case ID.')});
})();