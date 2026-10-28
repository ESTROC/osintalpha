"""Proof-of-text report annotations for EVERY manually recorded claim.

Text presence in a historical capture does not establish source authorship,
interpretation, identity, or any legal/factual allegation.
"""
from __future__ import annotations
import hashlib
from fastapi import APIRouter,Depends
from . import db,main as core
from .excerpts import norm
router=APIRouter()

def index(conn,case_id):
    claims=[dict(r) for r in conn.execute(
       'SELECT l.id,l.claim_text,l.stance,l.evidence_id,e.source_url,e.status '
       'FROM claim_links l JOIN evidence e ON e.id=l.evidence_id AND e.case_id=l.case_id '
       'WHERE l.case_id=? ORDER BY l.created_at DESC,l.id DESC LIMIT 700',(case_id,))]
    rows=[dict(r) for r in conn.execute(
       'SELECT p.claim_id,p.id proof_id,p.link_status,p.excerpt_id,'
       'x.quote_text,x.content_sha256,sc.extracted_text,sc.content_sha256 stored_sha,'
       'sc.content_type,sc.source_url capture_url,'
       '(SELECT content_sha256 FROM source_captures '
       ' WHERE case_id=p.case_id AND evidence_id=p.evidence_id '
       ' ORDER BY fetched_at DESC,id DESC LIMIT 1) latest_sha '
       'FROM claim_passage_proofs p '
       'JOIN verified_excerpts x ON x.id=p.excerpt_id AND x.case_id=p.case_id '
       'JOIN source_captures sc ON sc.id=x.capture_id AND sc.case_id=x.case_id '
       'WHERE p.case_id=? ORDER BY p.created_at DESC,p.id DESC LIMIT 1500',(case_id,))]
    byclaim={}
    for row in rows:
        exact=norm(row['quote_text'])
        text=norm(row['extracted_text'])
        checksum=hashlib.sha256(row['extracted_text'].encode('utf-8')).hexdigest()
        valid=(checksum==row['stored_sha']==row['content_sha256'] and
               row['latest_sha']==row['stored_sha'] and bool(exact) and exact in text)
        p={'id':row['proof_id'],'excerptId':row['excerpt_id'],
            'quoteText':row['quote_text'][:700],'captureUrl':row['capture_url'],
            'captureHash':row['stored_sha'],'storedCaptureIntegrityOk':checksum==row['stored_sha'],
            'currentSourceVersion':row['latest_sha']==row['stored_sha'],
            'quotePresentInCapturedText':bool(exact) and exact in text,
            'normalizedStartOffset':text.find(exact) if exact else None,
            'normalizedEndOffset':text.find(exact)+len(exact) if exact and exact in text else None,
            'pageNumber':None,'layoutCoordinatesAvailable':False,
            'validCurrentTextBinding':valid,'supportsTruth':False}
        byclaim.setdefault(row['claim_id'],[]).append(p)
    output=[]
    for c in claims:
        quotes=byclaim.get(c['id'],[])
        current=[x for x in quotes if x['validCurrentTextBinding']]
        status=('source_rejected' if c['status']=='rejected' else
                'current_text_bound_only' if current else
                'stale_or_broken_text_binding' if quotes else 'missing_exact_quote')
        output.append({'claimId':c['id'],'claim':c['claim_text'],'stance':c['stance'],
            'originalSourceUrl':c['source_url'],'evidenceId':c['evidence_id'],
            'claimBindingState':status,'quoteEvidence':quotes[:15],
            'materialClaimIndependentlyVerified':False,
            'identityIndependentlyVerified':False})
    return {'items':output,'totalClaims':len(output),
        'claimsWithCurrentExactQuotes':sum(c['claimBindingState']=='current_text_bound_only' for c in output),
        'claimsMissingCurrentExactQuotes':sum(c['claimBindingState']!='current_text_bound_only' for c in output),
        'truthVerifiedClaims':0,
        'limitation':'An exact quotation and unchanged SHA establish stored text only. Page number/layout may be unavailable, source/authorship unverified.'}

@router.get('/api/cases/{case_id}/claim-support-index')
def claim_support_index(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        return index(conn,case_id)
