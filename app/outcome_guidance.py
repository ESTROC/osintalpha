"""Concrete source outcome guidance and case title edits; no claim of missing identity."""
from __future__ import annotations
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

@router.get('/api/cases/{case_id}/outcome-guidance')
def outcome_guidance(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        queries=[dict(x) for x in conn.execute(
          'SELECT provider,status,returned_count,created_at FROM research_queries '
          'WHERE case_id=? ORDER BY created_at DESC,id DESC LIMIT 100',(case_id,))]
        count=conn.execute('SELECT count(*) n FROM evidence WHERE case_id=?',(case_id,)).fetchone()['n']
        candidates=conn.execute("SELECT count(*) n FROM evidence WHERE case_id=? AND status='candidate'",(case_id,)).fetchone()['n']
    counts={}
    for x in queries:counts[x['status']]=counts.get(x['status'],0)+1
    if not case['authority_confirmed']:
        state='authorization_missing';action='Document a lawful purpose and authority before any external discovery.'
    elif not queries:
        state='never_searched';action='Review a bounded official or public source plan, then start a consented search.'
    elif not count and any(x in counts for x in ('error','blocked','unavailable','failed')):
        state='provider_failed';action='Inspect provider diagnostics and retry only after the documented cooldown or use a permitted alternative official source.'
    elif not count:
        state='no_results';action='Try another authorized public source or distinguishing published organization or date; no-hit does not prove the subject does not exist.'
    elif candidates and case['subject_type']=='person':
        state='ambiguous_candidates';action='Review distinct namesakes and compare original published identifiers; do not automatically merge candidate records.'
    elif candidates:
        state='unreviewed_sources';action='Open source originals, capture exact quotations and mark review states with rationale.'
    else:
        state='review_or_report';action='Inspect evidence contradictions, exact source bindings and current signoff before limited distribution.'
    return {'state':state,'nextAction':action,'caseId':case_id,
      'sourceCandidateCount':count,'unreviewedCount':candidates,'searchStatusCounts':counts,
      'providerCoverageComplete':False,'identityVerified':False,
      'notice':'A failed provider, no-hit, unsupported query or stale index are distinct. No source absence proves a person or organization does not exist.'}

def suggested_title(case):
    import re
    query=' '.join(case['query'].split())
    kind={'person':'Person','organization':'Organization','domain':'Domain','ip':'Public IP'}.get(case['subject_type'],'Case')
    intent='Public research'
    purpose=case['purpose'].casefold()
    if 'supplier' in purpose:intent='Supplier review'
    elif 'security' in purpose or 'domain' in purpose:intent='Defensive review'
    elif 'event' in purpose:intent='Event review'
    elif 'education' in purpose:intent='Academic review'
    return (kind+' · '+query[:36]+' · '+intent+' · '+datetime.now(timezone.utc).date().isoformat())[:110]

@router.get('/api/cases/{case_id}/title-suggestion')
def title_suggestion(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
    return {'suggestedTitle':suggested_title(case),'originalQuery':case['query'],
       'queryWillBeChanged':False,'duplicateTitlesAllowed':True}

class TitleChange(BaseModel):
    title:str=Field(min_length=6,max_length=110)

@router.patch('/api/cases/{case_id}/title')
def rename_case(case_id:str,body:TitleChange,actor=Depends(core.protect)):
    value=' '.join(body.title.strip().split())
    if len(value)<6:raise HTTPException(422,'Use a meaningful concise case title.')
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        conn.execute('UPDATE cases SET title=? WHERE id=?',(value,case_id))
    core.write_audit(actor['id'],'case_title_change','case',case_id,'Title changed; objective preserved')
    return {'title':value,'originalQuestionPreserved':True,'originalQuery':case['query']}
