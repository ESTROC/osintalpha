"""Limited-distribution source-bound report gate and reproducible method appendix.

A reviewer approval is a human workflow decision, not publisher authentication,
identity certainty, legal authorization, or independent evidence certification.
"""
from __future__ import annotations
import hashlib,html,json
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field
from . import main as core,db
from .agency_ops import review_digest
from .claim_support import index as claim_index
router=APIRouter()

def _pack(conn,case_id):
    case=conn.execute('SELECT title,subject_type,query,purpose FROM cases WHERE id=?',(case_id,)).fetchone()
    idx=claim_index(conn,case_id)
    allowed=[];excluded=[]
    for claim in idx['items']:
        source=conn.execute('SELECT label,status,fetched_at FROM evidence WHERE case_id=? AND id=?',
            (case_id,claim['evidenceId'])).fetchone()
        if not source or source['status']!='corroborated' or claim['claimBindingState']!='current_text_bound_only':
            excluded.append({'claimId':claim['claimId'],'reason':claim['claimBindingState']})
            continue
        original=next((p for p in claim['quoteEvidence'] if p['validCurrentTextBinding']),None)
        if not original:
            excluded.append({'claimId':claim['claimId'],'reason':'broken_original_quote'});continue
        allowed.append({'claimId':claim['claimId'],'claim':claim['claim'][:450],
           'stance':claim['stance'],'originalSourceUrl':claim['originalSourceUrl'],
           'originalQuote':original['quoteText'][:650],'captureSha256':original['captureHash'],
           'sourceRetrievedAt':source['fetched_at'],
           'sourceLabel':'[redacted source label]'})
    out={'caseId':case_id,'subjectType':case['subject_type'],
         'limitedDistribution':True,'reviewedClaims':allowed[:100],
         'excludedClaimIds':excluded[:100],
         'missingSourceCount':len(excluded),'reviewedQuoteCount':len(allowed),
         'redactedFields':['person_contact_details','source_labels','unreviewed_evidence',
                           'rejected_or_disputed_sources','raw_provider_payloads'],
         'notice':'Only current analyst-corroborated, exact-quote claims are considered. Original-source truth and identity remain unverified.'}
    return out

def _sha(pack):
    return hashlib.sha256(json.dumps(pack,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def current_release(conn,case_id,require_approval=False):
    latest=conn.execute('SELECT * FROM report_release_approvals WHERE case_id=? '
      'ORDER BY issued_at DESC,id DESC LIMIT 1',(case_id,)).fetchone()
    digest=review_digest(conn,case_id)
    if not latest or latest['review_digest']!=digest:
        if require_approval:raise HTTPException(409,'Report requires current review and distribution approval.')
        return None
    return dict(latest)

@router.get('/api/cases/{case_id}/controlled-export-preview')
def preview(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        data=_pack(c,case_id)
        sign=c.execute('SELECT id,decision,review_digest FROM case_signoffs WHERE case_id=? '
          'ORDER BY signed_at DESC,id DESC LIMIT 1',(case_id,)).fetchone()
        digest=review_digest(c,case_id)
        release=current_release(c,case_id)
    return {'preview':data,'previewSha256':_sha(data),
       'latestSignoff':{'id':sign['id'],'decision':sign['decision'],
          'current':sign['review_digest']==digest} if sign else None,
       'currentDistributionApproved':bool(release),
       'requiresNamedReviewer':True,'unreviewedMaterialExcluded':True,
       'notice':'Inspect exclusions and source quotations; draft HTML/PDF/JSON exports are not controlled distribution outputs.'}

class Approval(BaseModel):
    expected_preview_sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
    confirm_originals_reviewed:bool=False
    confirm_exclusions_reviewed:bool=False
    confirm_scope_authorized:bool=False
    review_note:str=Field(min_length=40,max_length=800)

@router.post('/api/cases/{case_id}/distribution-approval',status_code=201)
def approve(case_id:str,body:Approval,actor=Depends(core.protect)):
    core.admin_only(actor)
    if not all((body.confirm_originals_reviewed,body.confirm_exclusions_reviewed,body.confirm_scope_authorized)):
        raise HTTPException(422,'All approval and redaction checklist confirmations are required.')
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        pack=_pack(c,case_id)
        if pack['reviewedQuoteCount']==0 or pack['missingSourceCount']>0:
            raise HTTPException(422,'All material claims must have current corroborated exact-source quotations.')
        current=_sha(pack)
        if body.expected_preview_sha256!=current:
            raise HTTPException(409,'Reviewed source preview changed; inspect a new one.')
        sign=c.execute('SELECT id,decision,review_digest FROM case_signoffs WHERE case_id=? '
           'ORDER BY signed_at DESC,id DESC LIMIT 1',(case_id,)).fetchone()
        dig=review_digest(c,case_id)
        if not sign or sign['decision']!='reviewed_with_limitations' or sign['review_digest']!=dig:
            raise HTTPException(409,'Current named analyst signoff with limitations is required.')
        id=core.uid()
        c.execute('INSERT INTO report_release_approvals VALUES (?,?,?,?,?,?,?)',
          (id,case_id,actor['id'],sign['id'],dig,current,core.iso_now()))
    core.write_audit(actor['id'],'limited_distribution_approval','case',case_id,id)
    return {'id':id,'status':'reviewer_approved_limited_distribution',
        'independentFactualVerification':False,'reviewerId':actor['id'],
        'approvalRevokedOnSourceChange':True}

@router.get('/api/cases/{case_id}/controlled-report.html')
def controlled_html(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        approval=current_release(c,case_id,require_approval=True)
        pack=_pack(c,case_id)
        if approval['preview_sha256']!=_sha(pack):
            raise HTTPException(409,'Report source quotations changed after approval.')
    lines=['<!doctype html><html lang="en"><meta charset="utf-8"><title>Reviewed limited report</title>',
       '<body><h1>Reviewed source-bound report</h1><p>Limited distribution; no independent identity certification.</p>']
    for x in pack['reviewedClaims']:
        lines.append('<article><h2>'+html.escape(x['claim'])+'</h2><blockquote>'+html.escape(x['originalQuote'])+'</blockquote>'+
            '<p><a rel="noopener noreferrer" href="'+html.escape(x['originalSourceUrl'],quote=True)+
            '">Original source</a> · capture '+html.escape(x['captureSha256'])+'</p></article>')
    lines.append('<p>Reviewed source text is not proof of truth, rights or identity.</p></body></html>')
    core.write_audit(actor['id'],'controlled_report_export','case',case_id,approval['id'])
    return HTMLResponse(''.join(lines),headers={'Cache-Control':'no-store',
      'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'"})

@router.get('/api/cases/{case_id}/methodology-appendix')
def methodology(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        case=core.case_or_404(c,case_id,actor)
        saved=c.execute('SELECT original_question,plan_json,updated_at FROM case_search_plans '
            'WHERE case_id=?',(case_id,)).fetchone()
        rows=[dict(x) for x in c.execute(
            'SELECT provider,query_text,status,returned_count,new_count,message,created_at '
            'FROM research_queries WHERE case_id=? ORDER BY created_at,id LIMIT 400',(case_id,))]
    try:plan=json.loads(saved['plan_json']) if saved else {}
    except (ValueError,TypeError):plan={}
    result={'caseId':case_id,'originalQuestion':saved['original_question'] if saved else case['query'],
       'planUpdatedAt':saved['updated_at'] if saved else None,
       'announcedProviders':plan.get('providers',[]),
       'searchEvents':[{'provider':x['provider'],'query':x['query_text'],
          'outcome':x['status'],'returnedCount':x['returned_count'],
          'newSourceCount':x['new_count'],'queriedAt':x['created_at'],
          'failureDiagnostic':x['message'][:180] if x['status'] in ('error','blocked','unavailable') else None}
          for x in rows],
       'searchEventCount':len(rows),'eventHistoryTruncated':len(rows)==400,
       'unsearchedProviderCoverage':None,'extractionLimitations':['Original text may not be archived',
          'Provider search indices are incomplete','Failed and unavailable are not no-hit',
          'Exact text is not publisher/authorship/identity validation'],
       'independentlyAudited':False}
    return result
