"""Case preservation schedule metadata, held-case guard and non-destructive review preview."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

class PreservationPolicy(BaseModel):
    review_in_days:int=Field(ge=30,le=3650)
    legal_hold:bool=False
    rationale:str=Field(min_length=30,max_length=600)

@router.get('/api/cases/{case_id}/preservation')
def preservation(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        row=c.execute('SELECT review_after,legal_hold,rationale,reviewed_at FROM '
              'case_preservation_policy WHERE case_id=?',(case_id,)).fetchone()
    return {'configured':bool(row),'policy':dict(row) if row else None,
        'automatedRemovalEnabled':False,'legalPolicyApproved':False}

@router.put('/api/cases/{case_id}/preservation')
def update_preservation(case_id:str,body:PreservationPolicy,actor=Depends(core.protect)):
    core.admin_only(actor)
    stamp=(datetime.now(timezone.utc)+timedelta(days=body.review_in_days)).isoformat(timespec='seconds')
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        existing=c.execute('SELECT legal_hold FROM case_preservation_policy WHERE case_id=?',(case_id,)).fetchone()
        if existing and existing['legal_hold'] and not body.legal_hold and len(body.rationale.strip())<50:
            raise HTTPException(422,'A preservation hold release requires a 50-character authorization rationale.')
        c.execute('INSERT OR IGNORE INTO case_preservation_policy VALUES (?,?,?,?,?,?)',
           (case_id,stamp,int(body.legal_hold),body.rationale.strip(),actor['id'],core.iso_now()))
        c.execute('UPDATE case_preservation_policy SET review_after=?,legal_hold=?,rationale=?,'
          'reviewed_by=?,reviewed_at=? WHERE case_id=?',
          (stamp,int(body.legal_hold),body.rationale.strip(),actor['id'],core.iso_now(),case_id))
    core.write_audit(actor['id'],'case_preservation','case',case_id,'hold='+str(body.legal_hold))
    return {'reviewAfter':stamp,'legalHold':body.legal_hold,'scheduledDeletion':False}

@router.get('/api/admin/preservation/review-due')
def review_due(actor=Depends(core.actor_from_cookie)):
    core.admin_only(actor)
    with db.connect() as c:
        records=[dict(x) for x in c.execute('SELECT case_id,review_after,legal_hold '
         'FROM case_preservation_policy WHERE review_after<=? ORDER BY review_after LIMIT 100',
         (core.iso_now(),))]
    return {'items':records,'autoDeleted':0,
        'notice':'A preservation review date is not an automatic deletion date. Holds and backups require independent review.'}
