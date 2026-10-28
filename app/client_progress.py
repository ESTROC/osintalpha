"""Preserve client-observed smart-search stage failures without trusting browser claims as provider logs."""
from __future__ import annotations
from typing import Literal
from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

class StageEvent(BaseModel):
    stage:Literal['structured','brave_index','brave_context','groq_analysis','xai_analysis']
    outcome:Literal['error','fallback','skipped']
    reason:Literal['provider_error','network_unavailable','not_configured','permission','other']='other'
    original_question:str=Field(min_length=3,max_length=200)

@router.post('/api/cases/{case_id}/client-stage-events',status_code=201)
def record_stage_event(case_id:str,body:StageEvent,actor=Depends(core.protect)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        existing=conn.execute(
            "SELECT count(*) n FROM research_queries WHERE case_id=? AND provider LIKE 'client_stage_%'",
            (case_id,)).fetchone()['n']
        if existing>=80:
            from fastapi import HTTPException
            raise HTTPException(429,'Client-stage diagnostics limit reached for this case.')
        now=core.iso_now();event_id=core.uid()
        notice=('Browser-reported stage outcome; not independently confirmed from provider logs. '
                f'Code={body.reason}; fallback={body.outcome=="fallback"}')
        conn.execute('INSERT INTO research_queries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (event_id,case_id,actor['id'],event_id,'client_stage_'+body.stage,
             body.original_question.strip(),body.outcome,0,0,notice,now))
    core.write_audit(actor['id'],'client_stage_observation','case',case_id,body.stage+':'+body.outcome)
    return {'id':event_id,'recorded':True,'source':'client_reported_not_provider_verified',
            'caseId':case_id,'stage':body.stage,'outcome':body.outcome}

@router.get('/api/cases/{case_id}/client-stage-events')
def list_stage_events(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        rows=[dict(x) for x in c.execute(
           "SELECT id,provider,status,query_text,message,created_at FROM research_queries "
           "WHERE case_id=? AND provider LIKE 'client_stage_%' "
           "ORDER BY created_at DESC,id DESC LIMIT 80",(case_id,))]
    return {'items':rows,'providerConfirmed':False,
            'notice':'Client stage observations are not provider audit logs; redacted reasons only.'}
