"""Draft redaction preview and approved reviewed-only exports.

No automatic allegation classification is treated as fact or a redaction guarantee.
"""
from __future__ import annotations
import html
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response,HTMLResponse
from pydantic import BaseModel
from . import db,main as core
from .report_distribution import snapshot,approved_state
router=APIRouter()

class RedactionRequest(BaseModel):
    suppress_subject_title:bool=True
    suppress_original_urls:bool=True
    suppress_claim_text:bool=False
    suppress_source_labels:bool=True
    export_format:Literal['json','html','pdf']='json'

def redaction_build(data,options):
    sources=[]
    for e in data['reviewedEvidence']:
        sources.append({'id':e['id'],'reviewStatus':e['status'],'hash':e['sha256'],
            'retrievedAt':e['fetched_at'],
            'label':None if options.suppress_source_labels else e['label'],
            'originalUrl':None if options.suppress_original_urls else e['source_url']})
    claims=[]
    for c in data['sourceClaims']:
        claims.append({'id':c['id'],'sourceId':c['sourceId'],
            'text':None if options.suppress_claim_text else c['text'],
            'originalUrl':None if options.suppress_original_urls else c['sourceUrl'],
            'currentCaptureHashes':c['captureHashes']})
    suppressed=[
      k for k in ('suppress_subject_title','suppress_original_urls',
                  'suppress_claim_text','suppress_source_labels') if getattr(options,k)]
    return {'status':'redacted_report_preview','title':None if options.suppress_subject_title else data['caseTitle'],
       'claims':claims,'sources':sources,'limitations':data['limitations'],
       'fieldsSuppressed':suppressed,'excludedUnreviewedLeads':True,
       'truthIndependentlyVerified':False,
       'warning':'Only reviewed source-linked content. Redaction rules do not detect all personal information embedded in permitted claim text.'}

@router.post('/api/cases/{case_id}/distribution/redaction-preview')
def redaction_preview(case_id:str,body:RedactionRequest,actor=Depends(core.protect)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        data=snapshot(conn,case_id)
    result=redaction_build(data,body)
    result['approvedForDistribution']=False
    result['eligibleForApproval']=data['readyForIndependentReview']
    result['readOnlyPreview']=True
    return result

def html_render(result):
    esc=html.escape
    lines=['<html><head><meta charset="utf-8"><title>Redacted reviewed report</title></head><body>',
           '<h1>Redacted reviewed report</h1><p>Source hashes retained; no verified person identity is asserted.</p>']
    if result['title']:lines.append('<h2>'+esc(result['title'])+'</h2>')
    for c in result['claims']:
        lines.append('<p>'+esc(c['text'] if c['text'] is not None else '[claim text withheld]')+
                     ' (source '+esc(c['sourceId'])+')</p>')
    lines.append('<h2>Limitations</h2><p>'+esc(result['limitations'])+'</p></body></html>')
    return ''.join(lines)

@router.post('/api/cases/{case_id}/distribution/redacted-export')
def export_redacted(case_id:str,body:RedactionRequest,actor=Depends(core.protect)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        data=approved_state(conn,case_id)
    result=redaction_build(data,body)
    result['status']='approved_redacted_export'
    result['review']=data['approval']
    core.write_audit(actor['id'],'redacted_distribution_export','case',case_id,
        body.export_format+':'+','.join(result['fieldsSuppressed']))
    if body.export_format=='json':return result
    markup=html_render(result)
    if body.export_format=='html':
        return HTMLResponse(markup,headers={'Cache-Control':'no-store',
            'Content-Security-Policy':"default-src 'none'; base-uri 'none'"})
    from .pdf_worker import render_report_in_subprocess
    try:output=render_report_in_subprocess(markup)
    except (RuntimeError,TimeoutError,ValueError) as exc:
        raise HTTPException(503,'Bounded PDF redaction rendering failed.') from exc
    return Response(output,media_type='application/pdf',headers={'Cache-Control':'no-store',
       'Content-Disposition':'attachment; filename="approved-redacted-report.pdf"'})
