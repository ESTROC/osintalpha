"""Time-qualified public affiliation *claims* with literal capture anchoring.

Time ranges are analyst interpretations of original text, never independently
verified historical employment, student enrollment, or account ownership.
"""
from __future__ import annotations
from datetime import date
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

class PublicAffiliation(BaseModel):
    candidate_id:str=Field(min_length=4,max_length=80)
    evidence_id:str=Field(min_length=4,max_length=80)
    excerpt_id:str=Field(min_length=4,max_length=80)
    organization_name:str=Field(min_length=3,max_length=200)
    role_title:str=Field(min_length=3,max_length=200)
    start_date:str=Field(min_length=10,max_length=10)
    end_date:str=Field(default='',max_length=10)
    date_precision:Literal['day','month','year']
    rationale:str=Field(min_length=30,max_length=1000)

def date_bounds(start,end):
    try:
        begin=date.fromisoformat(start)
        finish=date.fromisoformat(end) if end else None
    except (ValueError,TypeError) as exc:
        raise HTTPException(422,'Affiliation dates must be valid ISO YYYY-MM-DD.') from exc
    if finish and finish<begin:
        raise HTTPException(422,'Affiliation end cannot precede start.')
    return begin,finish

@router.post('/api/cases/{case_id}/public-affiliations',status_code=201)
def save_public_affiliation(case_id:str,body:PublicAffiliation,actor=Depends(core.protect)):
    date_bounds(body.start_date,body.end_date)
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        candidate=c.execute('SELECT id FROM candidate_profiles WHERE id=? AND case_id=?',
                            (body.candidate_id,case_id)).fetchone()
        if not candidate:raise HTTPException(422,'Choose a specific candidate identity hypothesis for this affiliation.')
        excerpt=c.execute(
            'SELECT x.id,x.quote_text,sc.extracted_text,sc.content_sha256,x.content_sha256 quoted_sha,'
            'e.status,e.id evidence_id FROM verified_excerpts x '
            'JOIN source_captures sc ON sc.id=x.capture_id AND sc.case_id=x.case_id '
            'JOIN evidence e ON e.id=x.evidence_id AND e.case_id=x.case_id '
            'WHERE x.case_id=? AND x.evidence_id=? AND x.id=?',
            (case_id,body.evidence_id,body.excerpt_id)).fetchone()
        if not excerpt or excerpt['status']=='rejected':
            raise HTTPException(422,'Current nonrejected source quotation required.')
        from .excerpts import exact_span
        import hashlib
        digest=hashlib.sha256(excerpt['extracted_text'].encode('utf-8')).hexdigest()
        if digest!=excerpt['content_sha256'] or digest!=excerpt['quoted_sha'] or not exact_span(
                excerpt['extracted_text'],excerpt['quote_text']):
            raise HTTPException(409,'Captured source text has changed or quote integrity failed.')
        id=core.uid()
        c.execute('INSERT INTO time_qualified_affiliations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
           (id,case_id,body.candidate_id,body.evidence_id,body.excerpt_id,
            body.organization_name.strip(),body.role_title.strip(),
            body.start_date,body.end_date,body.date_precision,
            body.rationale.strip(),actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'public_affiliation_claim','case',case_id,id)
    return {'id':id,'status':'unverified_time_qualified_public_affiliation',
            'employmentVerified':False,'enrolmentVerified':False,'personIdentityVerified':False}

@router.get('/api/cases/{case_id}/public-affiliations')
def list_public_affiliations(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        items=[dict(x) for x in c.execute(
           'SELECT a.*,p.display_name candidate_name,e.source_url original_url,'
           'x.quote_text from time_qualified_affiliations a '
           'JOIN candidate_profiles p ON p.id=a.candidate_id AND p.case_id=a.case_id '
           'JOIN evidence e ON e.id=a.evidence_id AND e.case_id=a.case_id '
           'JOIN verified_excerpts x ON x.id=a.excerpt_id AND x.case_id=a.case_id '
           'WHERE a.case_id=? ORDER BY a.start_date DESC,a.created_at DESC LIMIT 150',
           (case_id,))]
    return {'items':items,'verificationStatus':'analyst_linked_quote_only',
        'note':'Dates and roles are analyst interpretations, not employer/student confirmations. Missing end date means unknown, not present employment.'}
