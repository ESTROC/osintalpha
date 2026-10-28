"""Evidence bundle v1: metadata custody, exact-text quotes, and byte-level integrity.

A SHA-256 digest and actor access history do not prove publisher authenticity,
court admissibility, legal chain of custody, or third-party licensing.
"""
from __future__ import annotations
import hashlib,json,secrets,base64
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
from .claim_support import index as claim_index
router=APIRouter()
MAX_BUNDLE=300_000

def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')

def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def custody_event(conn,case_id,artifact_id,actor_id,kind,sha):
    conn.execute('INSERT INTO source_custody_access VALUES (?,?,?,?,?,?,?)',
         (core.uid(),case_id,artifact_id,actor_id,kind,sha,core.iso_now()))

def original_integrity(item):
    try:
        raw=base64.b64decode(item['content_b64'],validate=True)
        return len(raw)==item['byte_count'] and hashlib.sha256(raw).hexdigest()==item['original_sha256']
    except Exception:return False

@router.get('/api/cases/{case_id}/custody-access')
def custody_history(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=[dict(x) for x in conn.execute(
            'SELECT artifact_id,access_kind,original_sha256,occurred_at,actor_id '
            'FROM source_custody_access WHERE case_id=? ORDER BY occurred_at DESC,id DESC LIMIT 200',
            (case_id,))]
    return {'events':rows,'completeAccessChainCertified':False,
       'warning':'App recorded actions only; no tamper-evident external timestamp, privileged DB read detection, or legal certification.'}

@router.get('/api/cases/{case_id}/reviewed-source-bundle')
def reviewed_bundle(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        claims=claim_index(conn,case_id)['items']
        ids=[x['evidenceId'] for x in claims if x['claimBindingState']=='current_text_bound_only']
        selected=[]
        for c in claims:
            if c['claimBindingState']!='current_text_bound_only':continue
            evidence=conn.execute(
             'SELECT id,label,source_url,sha256,status,reviewed_at,fetched_at FROM evidence WHERE case_id=? AND id=?',
              (case_id,c['evidenceId'])).fetchone()
            if not evidence or evidence['status']!='corroborated':continue
            exact=next((p for p in c['quoteEvidence'] if p['validCurrentTextBinding']),None)
            if not exact:continue
            archives=[dict(x) for x in conn.execute(
              'SELECT id,original_sha256,byte_count,content_b64,stored_at,uploaded_by FROM '
              'source_document_archives WHERE case_id=? AND evidence_id=? ORDER BY stored_at DESC,id DESC LIMIT 10',
              (case_id,c['evidenceId']))]
            originals=[{'artifactId':x['id'],'originalSha256':x['original_sha256'],
                 'byteCount':x['byte_count'],'acquiredAt':x['stored_at'],'operator':x['uploaded_by'],
                 'integrityOk':original_integrity(x)} for x in archives]
            selected.append({'claimId':c['claimId'],'claimText':c['claim'][:400],
              'stance':c['stance'],'sourceId':evidence['id'],'sourceUrl':evidence['source_url'],
              'sourceRecordSha256':evidence['sha256'],'sourceRetrievedAt':evidence['fetched_at'],
              'reviewedAt':evidence['reviewed_at'],'capturedTextSha256':exact['captureHash'],
              'sourceQuote':exact['quoteText'][:700],
              'sourceCaptureIntegrityOk':exact['storedCaptureIntegrityOk'],
              'originals':originals})
            if len(selected)>=100:break
        if not selected:raise HTTPException(409,'No reviewed claims with current exact captured quotations to export.')
    pack={'format':'osintalpha-reviewed-source-manifest-v1','caseId':case_id,
       'caseSubjectType':case['subject_type'],'sources':selected,
       'sourceCount':len(selected),'independentIdentityVerification':False,
       'factsIndependentlyVerified':False,
       'limitation':'Only corroborated analyst-reviewed current exact-text claims. Publisher identity, licensing, evidence authenticity and legal custody are not independently certified.'}
    if len(canonical(pack))>MAX_BUNDLE:
        raise HTTPException(413,'Reviewed manifest too large; narrow export scope.')
    return {'manifest':pack,'sha256':digest(pack),'algorithm':'SHA-256',
        'signed':False,'archiveBytesIncluded':False,
        'note':'Original binaries stay case-authorized; manifest hashes are not an evidentiary certification.'}

class VerifyBundle(BaseModel):
    manifest:dict
    sha256:str=Field(min_length=64,max_length=64)

@router.post('/api/cases/{case_id}/reviewed-source-bundle/verify')
def verify_bundle(case_id:str,body:VerifyBundle,actor=Depends(core.protect)):
    with db.connect() as conn:core.case_or_404(conn,case_id,actor)
    if len(canonical(body.manifest))>MAX_BUNDLE:
        raise HTTPException(413,'Manifest verification size exceeded.')
    if body.manifest.get('format')!='osintalpha-reviewed-source-manifest-v1' or body.manifest.get('caseId')!=case_id:
        raise HTTPException(422,'Manifest version or case scope invalid.')
    import hmac
    match=hmac.compare_digest(digest(body.manifest),body.sha256)
    return {'sha256Matches':match,'publisherAuthenticityVerified':False,
       'legalAdmissibilityCertified':False,
       'warning':'A self-contained unsigned hash verifies bytes against itself, not provenance or original author.'}
