(()=>{'use strict';
const safe=v=>String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
function originPanel(origin,review){
 const groups=origin?.duplicateOriginGroups||[],tasks=review?.items||[];
 return '<section class="panel" aria-label="Citation source independence"><div class="panel-head"><strong class="panel-title">Citation origins & pending verification</strong></div><div class="panel-pad">'+
 '<p class="help">Repeated original URLs or DOIs are not independent sources.</p>'+
 groups.slice(0,10).map(x=>'<div class="sourcehealth">'+safe(x.sourceCount)+' records, origin '+safe(String(x.originKeySha256||'').slice(0,12))+
 ' · '+safe(x.classification)+' · '+safe((x.providers||[]).join(', '))+'</div>').join('')+
 '<p class="help">'+tasks.filter(x=>x.status!=='done').length+' obligations awaiting human review.</p>'+
 '<button class="btn small" data-tab="tasks">Open human review queue</button>'+
 '<p class="help">No automatic truth verification or identity resolution from citations.</p></div></section>';
}
function timingPanel(m){
 const fmt=v=>v==null?'Not measured':(Number(v)/3600).toFixed(1)+' hours';
 return '<section class="panel" aria-label="Review timeliness"><div class="panel-head"><strong class="panel-title">Review timeliness</strong></div><div class="panel-pad">'+
 (m?'<p>'+safe(m.casesWithUsefulCorroboratedReview)+' / '+safe(m.casesInspected)+' cases with a useful corroborated review</p>'+
 '<p>Median first useful review: '+safe(fmt(m.firstUsefulReviewSecondsMedian))+'</p>'+
 '<p>Oldest open task: '+safe(fmt(m.oldestOutstandingTaskSeconds))+'</p>'+
 '<p>Provider failures: '+safe(m.observedProviderFailures)+'</p>':'<p class="help">Load observed review measures to inspect current case workflow.</p>')+
 '<p class="help">No validated SLA or accuracy measure.</p></div></section>';
}
window.OSINTAlphaPanels=Object.freeze({originPanel,timingPanel});
})();