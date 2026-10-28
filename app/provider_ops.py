"""Case-bound provider call caps and observed HTTP error/latency history.

Never call these metrics contractual uptime, identity accuracy, or billed cost.
"""
from __future__ import annotations
import os,secrets
from datetime import datetime,timezone,timedelta
from fastapi import APIRouter,Depends,HTTPException
from . import db,main as core
router=APIRouter()
LIMITS={'brave_web':18,'brave_context':12,'groq':12,'xai':12}
PROVIDERS=set(LIMITS)|{'github','stackoverflow','openalex','crossref','gleif','wikipedia','wikidata','gdelt'}

def limit(provider):
    try:return max(1,min(300,int(os.getenv('OSINTALPHA_CASE_DAILY_'+provider.upper()+'_LIMIT',LIMITS[provider]))))
    except (ValueError,TypeError):return LIMITS[provider]

def reserve(case_id,user_id,provider):
    if provider not in LIMITS:raise ValueError('Unknown external budget class')
    day=datetime.now(timezone.utc).date().isoformat()
    with db.connect() as conn:
        conn.execute('INSERT OR IGNORE INTO external_api_daily_counters VALUES (?,?,?,0)',
           (case_id,provider,day))
        changed=conn.execute(
           'UPDATE external_api_daily_counters SET used=used+1 WHERE case_id=? AND provider=? AND day=? AND used<?',
           (case_id,provider,day,limit(provider))).rowcount
        if changed!=1:
            raise HTTPException(429,'The daily per-case external-call cap for '+provider+' has been reached.')
        now_used=conn.execute(
           'SELECT used FROM external_api_daily_counters WHERE case_id=? AND provider=? AND day=?',
           (case_id,provider,day)).fetchone()['used']
        conn.execute('INSERT INTO external_api_call_ledger VALUES (?,?,?,?,?)',
           (secrets.token_hex(12),case_id,provider,datetime.now(timezone.utc).isoformat(timespec='seconds'),user_id))
    return {'provider':provider,'reservedToday':now_used,'dailyCap':limit(provider)}

def record(provider,outcome,latency_ms=0,http_status=None):
    if provider not in PROVIDERS:return
    try:
        with db.connect() as conn:
            conn.execute('INSERT INTO provider_health_events VALUES (?,?,?,?,?,?)',
               (secrets.token_hex(12),provider,outcome,http_status,max(0,min(120000,int(latency_ms))),
                datetime.now(timezone.utc).isoformat(timespec='microseconds')))
    except Exception:
        # Telemetry failures cannot block legitimate research or leak source data.
        pass

def cooling(provider):
    if provider not in PROVIDERS:return False
    since=(datetime.now(timezone.utc)-timedelta(seconds=90)).isoformat(timespec='seconds')
    try:
        with db.connect() as conn:
            rows=[x['outcome'] for x in conn.execute(
               'SELECT outcome FROM provider_health_events WHERE provider=? AND observed_at>=? '
               'ORDER BY observed_at DESC,id DESC LIMIT 3',(provider,since))]
    except Exception:return False
    return len(rows)==3 and all(x in ('throttled','unavailable') for x in rows)

def guard(provider):
    if cooling(provider):
        raise HTTPException(503,'Upstream provider cooldown: recent rate limit or unavailable responses. Use saved sources.')

@router.get('/api/cases/{case_id}/research-budget')
def case_budget(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=[dict(x) for x in conn.execute(
            'SELECT provider,used n FROM external_api_daily_counters WHERE case_id=? AND day=?',
            (case_id,datetime.now(timezone.utc).date().isoformat()))]
    used={x['provider']:x['n'] for x in rows}
    return {'caseId':case_id,'dailyCallReservations':[{
         'provider':p,'used':used.get(p,0),'cap':limit(p),'remaining':max(0,limit(p)-used.get(p,0))
         } for p in LIMITS],
         'estimatedCurrencyCost':None,'vendorQuotaRemaining':None,
         'notice':'Counted outbound reservations, including failures. Vendor bill, tokens and total quota are unknown.'}

def percentile(values,q):
    if not values:return None
    values.sort()
    return values[int((len(values)-1)*q)]

@router.get('/api/research/source-health')
def source_health(actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        events=[dict(x) for x in conn.execute(
           'SELECT provider,outcome,latency_ms,observed_at FROM provider_health_events '
           'ORDER BY observed_at DESC,id DESC LIMIT 1200')]
    items=[]
    for provider in sorted(PROVIDERS):
        sample=[x for x in events if x['provider']==provider][:100]
        lat=[x['latency_ms'] for x in sample]
        items.append({'provider':provider,'observedCalls':len(sample),
          'p50Ms':percentile(lat[:],.50),'p95Ms':percentile(lat[:],.95),
          'errorPercent':round(100*sum(x['outcome']!='ok' for x in sample)/len(sample),1) if sample else None,
          'lastObserved':sample[0]['observed_at'] if sample else None,
          'cooldownActive':cooling(provider),'contractSlaVerified':False})
    return {'items':items,'continuousSyntheticMonitoring':False,'serviceLevelTarget':None,
         'notice':'These are observed calls only. No uptime, provider contract, or real-world accuracy SLA can be inferred.'}
