"""Original-question preserving case title edits and saved-methodology appendix."""
from __future__ import annotations
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

class TitleUpdate(BaseModel):
    title:str=Field(min_length=4,max_length=100)

@router.patch('/api/cases/{case_id}/title')
def title_update(case_id:str,body:TitleUpdate,actor=Depends(core.protect)):
    title=' '.join(body.title.split())
    if len(title)<4:raise HTTPException(422,'Use a concise meaningful case title.')
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        old=case['title']
        conn.execute('UPDATE cases SET title=? WHERE id=?',(title,case_id))
    core.write_audit(actor['id'],'case_title_edit','case',case_id,old[:100]+' => '+title)
    return {'title':title,'fullOriginalQuestionRetained':True,'queryUntouched':True}

def methodology_data(conn,case_id):
    row=conn.execute('SELECT query,subject_type,purpose,created_at FROM cases WHERE id=?',(case_id,)).fetchone()
    plan=conn.execute('SELECT original_question,plan_json,updated_at FROM case_search_plans WHERE case_id=?',(case_id,)).fetchone()
    searches=[dict(x) for x in conn.execute('SELECT provider,query_text,status,returned_count,'
       'new_count,message,created_at,run_id FROM research_queries WHERE case_id=? '
       'ORDER BY created_at,id LIMIT 500',(case_id,))]
    stage_status={'error','failed','unavailable','blocked','skipped','fallback'}
    runs=[dict(x) for x in conn.execute('SELECT provider,state,result_count,ran_at,message FROM collection_runs '
       'WHERE case_id=? ORDER BY ran_at DESC LIMIT 200',(case_id,))]
    return {'originalQuestion':plan['original_question'] if plan else row['query'],
        'caseCreatedAt':row['created_at'],'subjectType':row['subject_type'],
        'purpose':row['purpose'],'planLastUpdatedAt':plan['updated_at'] if plan else None,
        'recordedQueries':searches,
        'recordedCollectionRuns':runs,
        'recordedFailures':[{'provider':x['provider'],'stage':x['status'],
           'attemptedAt':x['created_at'],'detail':x['message'][:250]}
            for x in searches if x['status'] in stage_status],
        'queriedProviders':sorted({x['provider'] for x in searches}),
        'unqueriedProviderCoverage':'unknown',
        'searchComplete':False,'allRegionsCovered':False,
        'humanAssessmentRequired':True,
        'notice':'Only saved attempted calls. Failed and skipped stages are not proof of no public records. Retrieval time is not publication time.'}

@router.get('/api/cases/{case_id}/methodology-appendix')
def methodology_appendix(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        return methodology_data(c,case_id)
