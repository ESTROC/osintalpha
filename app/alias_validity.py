"""Date-scoped alias validity; annotation is not a verified identity merge."""
from __future__ import annotations
from datetime import date
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

class AliasValidity(BaseModel):
    review_state:Literal['active_hypothesis','retired','disputed']
    valid_from:date|None=None
    valid_until:date|None=None
    rationale:str=Field(min_length=20,max_length=500)

@router.put('/api/cases/{case_id}/aliases/{alias_id}/validity')
def record_validity(case_id:str,alias_id:str,body:AliasValidity,actor=Depends(core.protect)):
    if body.valid_from and body.valid_until and body.valid_from>body.valid_until:
        raise HTTPException(422,'The alias start date must precede its end date.')
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        linked=c.execute('SELECT id FROM research_aliases WHERE case_id=? AND id=?',(case_id,alias_id)).fetchone()
        if not linked:raise HTTPException(404,'Alias not part of this authorized case.')
        c.execute('DELETE FROM alias_validity_reviews WHERE alias_id=?',(alias_id,))
        c.execute('INSERT INTO alias_validity_reviews VALUES (?,?,?,?,?,?,?,?)',
            (alias_id,case_id,body.valid_from.isoformat() if body.valid_from else None,
            body.valid_until.isoformat() if body.valid_until else None,body.review_state,
            body.rationale.strip(),core.iso_now(),actor['id']))
    core.write_audit(actor['id'],'alias_validity_review','case',case_id,body.review_state)
    return {'reviewState':body.review_state,'identityVerified':False}

@router.get('/api/cases/{case_id}/aliases/validated')
def validated_aliases(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        rows=[dict(x) for x in c.execute(
            'SELECT a.id,a.alias,a.alias_type,a.source_url,r.valid_from,r.valid_until,'
            'r.review_state,r.review_rationale FROM research_aliases a '
            'LEFT JOIN alias_validity_reviews r ON r.alias_id=a.id '
            'WHERE a.case_id=? ORDER BY a.created_at DESC,a.id DESC LIMIT 100',(case_id,))]
    return {'items':rows,'autoMerged':False,
        'notice':'Absent validity review means unknown, not currently valid or the same real person.'}
