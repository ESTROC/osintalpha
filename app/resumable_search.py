"""Persisted saved-question execution trace and manual resumable research job.

The original initial smart-search HTTP chain remains browser-driven; this
exposes a stable, resumable investigation path instead of falsely claiming
a server background worker or completed coverage.
"""
from __future__ import annotations
import json
from collections import defaultdict
from fastapi import APIRouter,Depends,HTTPException
from . import db,main as core
from .agent import NewJob,create_job
router=APIRouter()

def derive_progress(question,plan,queries,assistant_messages):
    providers=list(dict.fromkeys(plan.get('providers') or []))
    byprovider=defaultdict(list)
    for r in queries:byprovider[str(r['provider'])].append(r)
    stages=[]
    for provider in providers:
        entries=byprovider.get(provider,[])
        status=('not_searched' if not entries else 'error' if all(r['status']=='error' for r in entries)
                else 'partial_failure' if any(r['status']=='error' for r in entries) else
                'no_hits' if all(r['status']=='empty' for r in entries) else 'candidate_results_recorded')
        stages.append({'provider':provider,'status':status,
            'executedQueries':len(entries),
            'resultsRecorded':sum(int(r['returned_count']) for r in entries)})
    web=byprovider.get('brave_web',[])
    web_state=('not_searched' if not web else
               'partial_failure' if any(r['status']=='error' for r in web) else
               'no_hits' if all(r['status']=='empty' for r in web) else 'candidate_results_recorded')
    return {'originalQuestion':question,'plannedStructuredSources':stages,
        'publicWebIndexState':web_state,
        'savedAssistantMessages':len(assistant_messages),
        'aiAnswerAvailable':bool(assistant_messages),
        'allPlannedStructuredQueried':bool(providers and all(x['status']!='not_searched' for x in stages)),
        'researchCompletenessVerified':False,'identitiesVerified':False,
        'notice':'A saved question and query trace permit manual continuation. Search provider completion is NOT objective or identity verification.'}

@router.get('/api/cases/{case_id}/search-progress')
def search_progress(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        saved=c.execute('SELECT original_question,plan_json,updated_at FROM case_search_plans WHERE case_id=?',
                        (case_id,)).fetchone()
        queries=[dict(x) for x in c.execute(
           'SELECT provider,status,returned_count,query_text FROM research_queries '
           'WHERE case_id=? ORDER BY created_at DESC,id DESC LIMIT 350',(case_id,))]
        recent=[dict(x) for x in c.execute(
           "SELECT m.id FROM research_messages m JOIN research_sessions s ON s.id=m.session_id "
           "WHERE s.case_id=? AND m.role='assistant' ORDER BY m.created_at DESC LIMIT 30",(case_id,))]
    if not saved:
        return {'available':False,'originalQuestion':None,
                'notice':'Legacy case with no stored question-routing plan.'}
    try:plan=json.loads(saved['plan_json'] or '{}')
    except (ValueError,TypeError):plan={}
    result=derive_progress(saved['original_question'],plan,queries,recent)
    result.update({'available':True,'planVersionUpdatedAt':saved['updated_at'],
                   'continuationMode':'bounded guided source jobs require explicit analyst action'})
    return result

@router.post('/api/cases/{case_id}/resume-saved-research',status_code=201)
def resume_saved_research(case_id:str,actor=Depends(core.protect)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        plan=c.execute('SELECT original_question FROM case_search_plans WHERE case_id=?',(case_id,)).fetchone()
        if not plan:raise HTTPException(409,'Legacy case lacks a saved search plan.')
        objective=('Continue saved public research: '+plan['original_question'])[:500]
        old=c.execute('SELECT id,status FROM research_jobs WHERE case_id=? AND owner_id=? '
           'AND objective=? AND status IN (\'ready\',\'running\',\'failed\',\'cancel_requested\') '
           'ORDER BY updated_at DESC,id DESC LIMIT 1',
           (case_id,actor['id'],objective)).fetchone()
        if old:
            return {'jobId':old['id'],'status':old['status'],'reusedExisting':True,
                    'requiresExplicitSteps':True}
    created=create_job(case_id,NewJob(objective=objective,mode='guided',
                         allow_web=False,consent=False,max_steps=5),actor)
    return {'jobId':created['id'],'status':created['status'],'reusedExisting':False,
            'requiresExplicitSteps':True,
            'notice':'Saved guided job created; nothing runs until analyst clicks Continue. The initial browser search was not a durable server queue.'}
