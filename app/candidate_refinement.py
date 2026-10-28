"""Analyst-directed in-case candidate refinement, without automatic identity merge."""
from __future__ import annotations
import re
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

class Refinement(BaseModel):
    candidate_id:str=Field(min_length=4,max_length=80)
    clue_kind:Literal['public_organization','public_city','public_handle','published_field']
    clue_value:str=Field(min_length=3,max_length=120)
    rationale:str=Field(min_length=20,max_length=400)
    consent:bool=False

@router.post('/api/cases/{case_id}/candidate-refinements',status_code=201)
def candidate_refinement(case_id:str,body:Refinement,actor=Depends(core.protect)):
    if not body.consent:raise HTTPException(422,'Explicit analyst public-source refinement consent required.')
    val=' '.join(body.clue_value.strip().split())
    if re.search(r'(?:https?://|@|[\n\r\x00-\x1f])',val):
        raise HTTPException(422,'Use non-sensitive published text, not contact details or a URL.')
    from .research_safety import require_safe_remote_query
    with db.connect() as c:
        case=core.case_or_404(c,case_id,actor)
        candidate=c.execute('SELECT id,display_name FROM candidate_profiles WHERE case_id=? AND id=?',
                           (case_id,body.candidate_id)).fetchone()
        if not candidate:raise HTTPException(422,'Candidate hypothesis outside this case.')
        plan=c.execute('SELECT original_question FROM case_search_plans WHERE case_id=?',(case_id,)).fetchone()
        original=plan['original_question'] if plan else case['query']
        query=(str(candidate['display_name'])[:100]+' '+val)[:200]
        require_safe_remote_query(query,case['subject_type'])
        id=core.uid()
        c.execute('INSERT INTO candidate_refinements VALUES (?,?,?,?,?,?,?,?,?)',
             (id,case_id,body.candidate_id,original,body.clue_kind,val,query,
              actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'refine_candidate','case',case_id,id)
    return {'id':id,'query':query,'candidateId':body.candidate_id,'originalQuestion':original,
      'externalCallsMade':False,'sourceClaimsVerified':False,
      'nextStep':'Analyst may execute this query with existing consent and public search quota.'}

@router.get('/api/cases/{case_id}/candidate-refinements')
def list_refinements(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        records=[dict(x) for x in c.execute(
          'SELECT r.id,r.candidate_id,r.original_question,r.clue_kind,r.clue_value,'
          'r.search_query,r.reviewed_at,p.display_name FROM candidate_refinements r '
          'JOIN candidate_profiles p ON p.id=r.candidate_id AND p.case_id=r.case_id '
          'WHERE r.case_id=? ORDER BY r.reviewed_at DESC,r.id DESC LIMIT 80',(case_id,))]
    return {'items':records,'autoExecuted':False,'identityVerified':False}
