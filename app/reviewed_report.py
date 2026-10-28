"""Deterministic draft from reviewed, exact-quote-bound claims; NOT final approval."""
from __future__ import annotations
import hashlib,json
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
from .claim_support import index as claim_support_index
from .decision_readiness import evidence_digest
router=APIRouter()

def prepare(conn,case_id):
    case=conn.execute('SELECT query,subject_type,purpose FROM cases WHERE id=?',(case_id,)).fetchone()
    source=claim_support_index(conn,case_id)
    selected=[]
    for claim in source['items']:
        if claim['claimBindingState']!='current_text_bound_only':
            continue
        status=conn.execute('SELECT status FROM evidence WHERE case_id=? AND id=?',
            (case_id,claim['evidenceId'])).fetchone()
        if not status or status['status']!='corroborated':continue
        quote=next((p for p in claim['quoteEvidence'] if p['validCurrentTextBinding']),None)
        if not quote:continue
        selected.append({'claim':claim['claim'][:250],'sourceUrl':claim['originalSourceUrl'],
             'quote':quote['quoteText'][:280],'captureSha':quote['captureHash']})
        if len(selected)>=8:break
    lines=['Source-bound analyst findings (not independent fact confirmation):']
    for i,item in enumerate(selected,1):
        lines.append(f'{i}. Analyst claim: {item["claim"]}. Quoted text: {item["quote"]}.')
    assessment='\n'.join(lines) if selected else 'No currently corroborated, source-bound claim available for a reviewed draft.'
    limitations=('Text capture and analyst source review do not independently verify human identity, '
      'original publisher ownership, affiliation, or allegations. Unsearched providers and '
      'unavailable sources remain unknown. Check every original URL and capture SHA.')
    summary=(f'Preliminary evidence review of {case["query"][:100]}: '
        f'{len(selected)} source-bound analyst-reviewed claim(s). '
        'No independently certified identity or factual correctness.')
    next_actions='Review quoted source links, resolve namesakes, inspect contradictions and request independent signoff.'
    draft={'executive_summary':summary[:2400],'assessment':assessment[:5000],
         'limitations':limitations[:2000],'next_actions':next_actions[:2000],
         'sourceCount':len(selected),'selectedClaims':selected,
         'status':'awaiting_review','automaticApproval':False,
         'verifiedFacts':0,'subjectIdentityVerified':False}
    current=evidence_digest(conn,case_id)
    canonical=json.dumps({'draft':draft,'digest':current},sort_keys=True,ensure_ascii=False)
    draft['reviewToken']=hashlib.sha256(canonical.encode()).hexdigest()
    return draft

@router.get('/api/cases/{case_id}/reviewed-report-draft')
def preview_reviewed_draft(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        return prepare(conn,case_id)

class AcceptDraft(BaseModel):
    review_token:str=Field(min_length=64,max_length=64)
    reviewer_confirmed:bool=False

@router.post('/api/cases/{case_id}/reviewed-report-draft/accept',status_code=201)
def accept_reviewed_draft(case_id:str,body:AcceptDraft,actor=Depends(core.protect)):
    if not body.reviewer_confirmed:
        raise HTTPException(422,'Explicit analyst review is required before saving a report draft.')
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        draft=prepare(conn,case_id)
        if draft['sourceCount']<1:
            raise HTTPException(422,'At least one corroborated source with a current captured exact quotation is required.')
        if draft['reviewToken']!=body.review_token:
            raise HTTPException(409,'Evidence or source review changed; load and inspect a fresh preview.')
        now=core.iso_now()
        conn.execute('DELETE FROM case_assessments WHERE case_id=?',(case_id,))
        conn.execute('INSERT INTO case_assessments VALUES (?,?,?,?,?,?,?,?)',
            (case_id,draft['executive_summary'],draft['assessment'],
             draft['limitations'],draft['next_actions'],'awaiting_review',actor['id'],now))
        conn.execute('DELETE FROM assessment_review_baselines WHERE case_id=?',(case_id,))
        conn.execute('INSERT INTO assessment_review_baselines VALUES (?,?,?,?)',
            (case_id,evidence_digest(conn,case_id),now,actor['id']))
    core.write_audit(actor['id'],'reviewed_report_draft','case',case_id,'pending independent approval')
    return {'saved':True,'status':'awaiting_review','automaticApproval':False,
            'sourceCount':draft['sourceCount'],
            'notice':'Draft saved for independent reviewer; it is NOT a signed, released or independently verified report.'}
