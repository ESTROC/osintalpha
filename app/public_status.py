"""Public, fact-based pilot service notice page; never imply continuous uptime."""
from __future__ import annotations
import html,os
from datetime import datetime,timezone,timedelta
from fastapi import APIRouter,Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field
from typing import Literal
from . import db,main as core
from .release import VERSION,RELEASE_STAGE
router=APIRouter()

class Notice(BaseModel):
    state:Literal['degraded','maintenance','resolved']
    message:str=Field(min_length=25,max_length=400)

@router.post('/api/admin/service-notices',status_code=201)
def publish_notice(body:Notice,actor=Depends(core.protect)):
    core.admin_only(actor)
    ident=core.uid()
    with db.connect() as conn:
        conn.execute('INSERT INTO public_service_notices VALUES (?,?,?,?,?)',
             (ident,body.state,body.message.strip(),core.iso_now(),actor['id']))
    core.write_audit(actor['id'],'public_service_notice','status',ident,body.state)
    return {'id':ident,'published':True,'state':body.state}

def snapshot_status():
    now=datetime.now(timezone.utc)
    with db.connect() as conn:
        conn.execute('SELECT 1').fetchone()
        notices=[dict(x) for x in conn.execute(
           'SELECT id,status,message,published_at FROM public_service_notices '
           'ORDER BY published_at DESC,id DESC LIMIT 12')]
        cutoff=(now-timedelta(hours=24)).isoformat(timespec='seconds')
        statuses=[dict(x) for x in conn.execute(
          'SELECT provider,outcome,observed_at FROM provider_health_events '
          'WHERE observed_at>=? ORDER BY observed_at DESC LIMIT 500',(cutoff,))]
    by_provider={}
    for record in statuses:
        obj=by_provider.setdefault(record['provider'],{'provider':record['provider'],
            'observedCalls':0,'observedFailures':0,'lastObservationAt':record['observed_at']})
        obj['observedCalls']+=1
        if record['outcome']!='ok':obj['observedFailures']+=1
    state=notices[0]['status'] if notices else 'no_active_notice'
    if state=='resolved':state='no_active_notice'
    return {'version':VERSION,'stage':RELEASE_STAGE,'checkedAt':now.isoformat(timespec='seconds'),
       'appDatabaseResponding':True,'currentPublishedNotice':state,
       'publishedNotices':notices,'observedProviderCallsLast24h':list(by_provider.values()),
       'providerUptimeVerified':False,'continuousMonitoringEnabled':False,
       'databaseBackupVerified':False,
       'warning':'This is a single live API/DB response and published operator notices, not an independently monitored uptime SLA.'}

@router.get('/api/public/status')
def public_status():
    return snapshot_status()

@router.get('/status',response_class=HTMLResponse)
def status_page():
    data=snapshot_status()
    esc=html.escape
    notice=data['publishedNotices'][0] if data['publishedNotices'] else None
    entry=(('<h2>Latest published notice</h2><p><strong>'+esc(notice['status'])+'</strong> · '+
           esc(notice['published_at'])+'</p><p>'+esc(notice['message'])+'</p>') if notice else
          '<p>No operator incident notice is recorded. Provider uptime is unknown.</p>')
    history=''.join('<li>'+esc(x['published_at'])+' · '+esc(x['status'])+
          ' · '+esc(x['message'])+'</li>' for x in data['publishedNotices'])
    body=('<!doctype html><html lang="en"><head><meta charset="utf-8">'+
      '<meta name="viewport" content="width=device-width, initial-scale=1">'+
      '<title>OSINT Alpha service status</title></head><body>'+
      '<main><h1>OSINT Alpha · pilot service status</h1><p>Release '+
      esc(VERSION)+' · '+esc(RELEASE_STAGE)+'</p>'+
      '<p>Live check: API and database responded at '+esc(data['checkedAt'])+'</p>'+
      entry+'<h2>Published notice history</h2><ul>'+history+'</ul>'+
      '<p>Provider observations are incomplete; no uptime SLA, backup recovery or model accuracy is certified.</p>'+
      '<p>Raw provider diagnostics require an authenticated analyst.</p></main></body></html>')
    return HTMLResponse(body,headers={'Cache-Control':'no-store',
        'Content-Security-Policy':"default-src 'none'; base-uri 'none'"})
