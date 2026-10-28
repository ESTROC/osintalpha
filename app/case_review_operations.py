"""Opt-in, cross-case comparison of only human-reviewed, source-bound public claims."""
from __future__ import annotations
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from typing import Literal
from . import db,main as core
from .claim_support import index as claim_support_index
router=APIRouter()

def reviewed_claims(conn,case_id):
    support=claim_support_index(conn,case_id)
    reviewed={x['id'] for x in conn.execute(
        "SELECT id FROM evidence WHERE case_id=? AND status='corroborated'",(case_id,))}
    return [{'claimId':x['claimId'],'text':x['claim'],'sourceUrl':x['originalSourceUrl'],
       'evidenceId':x['evidenceId'],'stance':x['stance'],
       'quoteHashes':[p['captureHash'] for p in x['quoteEvidence'] if p['validCurrentTextBinding']],
       'identityVerified':False}
       for x in support['items'] if x['claimBindingState']=='current_text_bound_only'
       and x['evidenceId'] in reviewed][:200]

@router.get('/api/agency/reviewed-case-compare')
def compare_reviewed_cases(left:str=Query(min_length=4,max_length=80),
   right:str=Query(min_length=4,max_length=80),
   actor=Depends(core.actor_from_cookie)):
    if left==right:raise HTTPException(422,'Choose two distinct cases.')
    with db.connect() as conn:
        lcase=core.case_or_404(conn,left,actor)
        rcase=core.case_or_404(conn,right,actor)
        a=reviewed_claims(conn,left);b=reviewed_claims(conn,right)
    def key(item):return (item['text'].strip().casefold(),item['sourceUrl'])
    ka,kb={key(x) for x in a},{key(x) for x in b}
    return {'left':{'id':left,'title':lcase['title'],'reviewedClaims':a[:80]},
       'right':{'id':right,'title':rcase['title'],'reviewedClaims':b[:80]},
       'overlappingExactTextAndSource':len(ka&kb),
       'leftOnly':len(ka-kb),'rightOnly':len(kb-ka),
       'identitiesMerged':False,'casesSameSubjectVerified':False,
       'notice':'Only two explicitly selected authorized investigations. Shared language or source URLs do not prove shared person, institution, claim truth or legal affiliation.'}

class TaskBatchPreview(BaseModel):
    ids:list[str]=Field(min_length=1,max_length=20)
    status:Literal['todo','in_progress','blocked','awaiting_review','cancelled']

@router.post('/api/cases/{case_id}/tasks/batch-preview')
def preview_batch(case_id:str,body:TaskBatchPreview,actor=Depends(core.protect)):
    unique=list(dict.fromkeys(body.ids))
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=[dict(x) for x in conn.execute('SELECT id,status FROM investigation_tasks WHERE case_id=? AND id IN ('+
            ','.join('?' for _ in unique)+')',(case_id,*unique))]
    valid={x['id'] for x in rows}
    rejected=[x for x in unique if x not in valid]
    return {'canApply':not rejected,'accepted':len(unique)-len(rejected),
      'rejectedCount':len(rejected),'rejectedIds':rejected,
      'plannedStatus':body.status,'mutationsPerformed':0,
      'requiresHumanFinalCompletion':True,
      'notice':'Tasks cannot be bulk marked done, and existing reviewed identities or material claims are not automatically verified.'}
