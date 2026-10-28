"""Case-scoped reviewed-source comparison and safe partial bulk workflow updates.

Comparison is evidence-review overlap, never proof two people or organizations
are identical. Bulk transitions cannot mark assertions or identities verified.
"""
from __future__ import annotations
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
from .claim_support import index as claim_index
router=APIRouter()

def _case_claims(conn,case_id,actor):
    case=core.case_or_404(conn,case_id,actor)
    support=claim_index(conn,case_id)
    selected=[]
    for claim in support['items']:
        if claim['claimBindingState']!='current_text_bound_only':continue
        source=conn.execute('SELECT status FROM evidence WHERE id=? AND case_id=?',
          (claim['evidenceId'],case_id)).fetchone()
        if not source or source['status']!='corroborated':continue
        quote=next((q for q in claim['quoteEvidence'] if q['validCurrentTextBinding']),None)
        if not quote:continue
        selected.append({'claimId':claim['claimId'],'claim':claim['claim'][:300],
            'evidenceId':claim['evidenceId'],'sourceUrl':claim['originalSourceUrl'],
            'captureSha256':quote['captureHash'],'status':'analyst_reviewed_text_only'})
    return case,selected[:80]

@router.get('/api/agency/compare-reviewed')
def compare_reviewed(left:str,right:str,actor=Depends(core.actor_from_cookie)):
    if left==right:raise HTTPException(422,'Comparison requires two different authorized cases.')
    with db.connect() as conn:
        a,claims_a=_case_claims(conn,left,actor)
        b,claims_b=_case_claims(conn,right,actor)
    by_left={x['sourceUrl']:x for x in claims_a}
    by_right={x['sourceUrl']:x for x in claims_b}
    intersect=sorted(set(by_left)&set(by_right))
    return {'left':{'id':left,'title':a['title'],'reviewedClaims':claims_a},
      'right':{'id':right,'title':b['title'],'reviewedClaims':claims_b},
      'reusedExactSourceUrls':intersect[:50],
      'commonClaimIdentityVerified':False,
      'twoCasesRepresentSameSubjectVerified':False,
      'reviewedClaimTruthCertified':False,
      'warning':'Shared source URLs are not independent corroboration. Differences in review coverage and namesakes remain unknown.'}

class BatchTaskReview(BaseModel):
    ids:list[str]=Field(min_length=1,max_length=20)
    status:Literal['todo','in_progress','blocked','awaiting_review','cancelled']
    note:str=Field(min_length=20,max_length=800)
    execute:bool=False

@router.post('/api/cases/{case_id}/tasks/safe-batch')
def safe_batch(case_id:str,body:BatchTaskReview,actor=Depends(core.protect)):
    unique=list(dict.fromkeys(body.ids))
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        marks=','.join('?' for _ in unique)
        found={x['id']:dict(x) for x in conn.execute(
            'SELECT id,status FROM investigation_tasks WHERE case_id=? AND id IN ('+marks+')',
            [case_id]+unique)}
        rejected=[{'taskId':tid,'reason':'not_in_authorized_case'} for tid in unique if tid not in found]
        selected=[x for x in unique if x in found]
        if body.execute:
            for tid in selected:
                current=found[tid]
                stamp=core.iso_now()
                conn.execute('UPDATE investigation_tasks SET status=?,updated_at=? WHERE case_id=? AND id=?',
                     (body.status,stamp,case_id,tid))
                conn.execute('INSERT INTO investigation_task_events VALUES (?,?,?,?,?,?,?,?)',
                     (core.uid(),tid,case_id,actor['id'],current['status'],body.status,
                      body.note.strip(),stamp))
    if body.execute and selected:
        core.write_audit(actor['id'],'safe_batch_task_status','case',case_id,
                          str(len(selected))+' '+body.status)
    return {'previewOnly':not body.execute,'updatedCount':len(selected) if body.execute else 0,
      'eligibleIds':selected,'rejected':rejected,
      'noAutomaticCertification':True,'bulkCompletionAllowed':False,
      'note':'Only selected case-scoped tasks may be advanced to non-completed workflow states. Review completion remains individual.'}
