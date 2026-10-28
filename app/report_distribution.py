"""Independent reviewed-report release gate, with stale-signature protection.

Ordinary legacy report exports are drafts. Only the /distribution/... endpoints
may assert an independently reviewed report was approved for distribution.
"""
from __future__ import annotations
import hashlib,html,json
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import HTMLResponse,Response
from pydantic import BaseModel,Field
from . import db,main as core
from .agency_ops import review_digest
from .claim_support import index as claim_support_index
from .decision_readiness import evidence_digest
router=APIRouter()

def snapshot(conn,case_id):
    case=conn.execute('SELECT * FROM cases WHERE id=?',(case_id,)).fetchone()
    ass=conn.execute('SELECT * FROM case_assessments WHERE case_id=?',(case_id,)).fetchone()
    baseline=conn.execute('SELECT evidence_digest FROM assessment_review_baselines WHERE case_id=?',(case_id,)).fetchone()
    support=claim_support_index(conn,case_id)
    rows=[dict(x) for x in conn.execute(
        "SELECT id,label,source_url,status,sha256,fetched_at FROM evidence "
        "WHERE case_id=? AND status='corroborated' ORDER BY id",(case_id,))]
    signed=conn.execute('SELECT actor_id,decision,review_digest,signed_at FROM case_signoffs '
       'WHERE case_id=? ORDER BY signed_at DESC,id DESC LIMIT 1',(case_id,)).fetchone()
    manual=review_digest(conn,case_id)
    evidence_now=evidence_digest(conn,case_id)
    acceptable=(bool(ass) and ass['status'] in ('awaiting_review','completed') and
        bool(ass['limitations'].strip()) and bool(baseline) and
        baseline['evidence_digest']==evidence_now and
        bool(signed) and signed['decision']=='reviewed_with_limitations' and signed['review_digest']==manual and
        bool(rows) and support['totalClaims']>0 and
        support['claimsMissingCurrentExactQuotes']==0)
    reviewed_source={x['id'] for x in rows}
    acceptable=acceptable and all(x['evidenceId'] in reviewed_source for x in support['items'])
    assessed_by=ass['updated_by'] if ass else None
    source_claims=[{'id':x['claimId'],'text':x['claim'],'stance':x['stance'],
      'sourceId':x['evidenceId'],'sourceUrl':x['originalSourceUrl'],
      'captureHashes':[p['captureHash'] for p in x['quoteEvidence'] if p['validCurrentTextBinding']]}
       for x in support['items']]
    material={'caseId':case_id,'title':case['title'],'purpose':case['purpose'],
      'reviewedDigest':manual,'claims':source_claims,'sources':rows,
      'assessment':dict(ass) if ass else None,
      'signoff':dict(signed) if signed else None}
    token=hashlib.sha256(json.dumps(material,sort_keys=True,default=str).encode()).hexdigest()
    return {'currentDigest':token,'readyForIndependentReview':bool(acceptable),
        'sourceCount':len(rows),'claimCount':len(source_claims),'sourceClaims':source_claims,
        'reviewedEvidence':rows,'assessmentReviewerId':assessed_by,
        'limitations':ass['limitations'] if ass else '',
        'caseTitle':case['title'],'casePurpose':case['purpose'],
        'blockers':([] if acceptable else ['Current assessment, reviewed corroborated sources, exact quotations and signed source state must pass first.']),
        'originalReportIsDraft':True,'identityIndependentlyVerified':False}

@router.get('/api/cases/{case_id}/distribution/preview')
def preview(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        data=snapshot(conn,case_id)
    return data

class DistributionApproval(BaseModel):
    report_digest:str=Field(min_length=64,max_length=64)
    material_claims_checked:bool=False
    source_rights_checked:bool=False
    sensitive_content_checked:bool=False
    methodology_checked:bool=False
    limitations_checked:bool=False
    reviewer_note:str=Field(min_length=50,max_length=1200)

@router.post('/api/cases/{case_id}/distribution/approve',status_code=201)
def approve(case_id:str,body:DistributionApproval,actor=Depends(core.protect)):
    core.admin_only(actor)
    checks={key:getattr(body,key) for key in (
      'material_claims_checked','source_rights_checked','sensitive_content_checked',
      'methodology_checked','limitations_checked')}
    if not all(checks.values()):
        raise HTTPException(422,'All material claim, source-rights, privacy, methodology and limitation review checks must be confirmed.')
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        current=snapshot(conn,case_id)
        if not current['readyForIndependentReview']:
            raise HTTPException(422,'Current reviewed and source-quoted assessment is not eligible for distribution.')
        if current['assessmentReviewerId']==actor['id']:
            raise HTTPException(422,'A separate reviewer is required for the final distribution approval.')
        if body.report_digest!=current['currentDigest']:
            raise HTTPException(409,'Report changed since preview; inspect the latest version before approval.')
        ident=core.uid()
        conn.execute('INSERT INTO report_distribution_reviews VALUES (?,?,?,?,?,?,?,?)',
            (ident,case_id,current['currentDigest'],actor['id'],core.iso_now(),
             json.dumps(checks,sort_keys=True),'approved',body.reviewer_note.strip()))
    core.write_audit(actor['id'],'report_distribution_approval','case',case_id,ident)
    return {'approved':True,'approvalId':ident,'reportDigest':current['currentDigest'],
        'independentReviewerId':actor['id'],'legalCertification':False}

def approved_state(conn,case_id):
    data=snapshot(conn,case_id)
    row=conn.execute('SELECT r.id,r.report_digest,r.reviewed_at,r.reviewed_by,u.username '
      'FROM report_distribution_reviews r JOIN users u ON u.id=r.reviewed_by '
      "WHERE r.case_id=? AND r.decision='approved' ORDER BY r.reviewed_at DESC,r.id DESC LIMIT 1",
       (case_id,)).fetchone()
    if not row or not data['readyForIndependentReview'] or row['report_digest']!=data['currentDigest']:
        raise HTTPException(409,'No current independent report distribution approval; the report is still a draft.')
    data['approval']={'id':row['id'],'reviewer':row['username'],'reviewedAt':row['reviewed_at']}
    return data

@router.get('/api/cases/{case_id}/distribution/approved.json')
def approved_json(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        data=approved_state(conn,case_id)
    core.write_audit(actor['id'],'approved_report_export','case',case_id,'reviewed-only and source-bound')
    return {'reportStatus':'approved_for_distribution','review':data['approval'],
      'caseTitle':data['caseTitle'],'claims':data['sourceClaims'],
      'sources':data['reviewedEvidence'],'limitations':data['limitations'],
      'identityIndependentlyVerified':False,'unreviewedSourcesExcluded':True}

@router.get('/api/cases/{case_id}/distribution/approved.html',response_class=HTMLResponse)
def approved_html(case_id:str,actor=Depends(core.actor_from_cookie)):
    result=approved_json(case_id,actor)
    esc=html.escape
    claims=''.join('<li>'+esc(x['text'])+' · <a href="'+esc(x['sourceUrl'],quote=True)+'">Source</a></li>'
                   for x in result['claims'])
    rendered=('<html><head><meta charset="utf-8"><title>Reviewed report</title></head><body>'
      '<h1>'+esc(result['caseTitle'])+'</h1><p>Approved for distribution by '
      +esc(result['review']['reviewer'])+' at '+esc(result['review']['reviewedAt'])+'</p>'
      '<p>Original source text and citations are not independent proof of factual accuracy.</p>'
      '<ul>'+claims+'</ul><h2>Limitations</h2><p>'+esc(result['limitations'])+'</p></body></html>')
    return HTMLResponse(rendered,headers={'Cache-Control':'no-store',
      'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'"})
