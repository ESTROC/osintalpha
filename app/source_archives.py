"""Explicit-consent, bounded user-provided public-document evidence intake.

Never fetch an arbitrary URL, execute embedded PDF code, render arbitrary
WARC/HTML, or claim OCR/forensic capture that has not happened.
Binary retention is 1-30 days; purge operation is user-triggered, not a
guaranteed scheduled deletion or backup erasure.
"""
from __future__ import annotations
import base64,binascii,hashlib,io
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response
from pydantic import BaseModel,Field
from typing import Literal
from . import db,main as core
router=APIRouter()
MAX_ASSET=160_000

class ArtifactIntake(BaseModel):
    evidence_url:str=Field(min_length=12,max_length=600)
    asset_kind:Literal['pdf','png','warc']
    content_base64:str=Field(min_length=12,max_length=250_000)
    rights_confirmed:bool=False
    retention_days:int=Field(default=7,ge=1,le=30)

def decode_asset(encoded,kind):
    if len(encoded)>225_000:raise HTTPException(413,'Binary evidence exceeds the 160KB case-file cap.')
    try:data=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError) as exc:
        raise HTTPException(422,'Invalid base64 evidence input.') from exc
    if not 30<=len(data)<=MAX_ASSET:raise HTTPException(413,'Original evidence size must be 30 to 160000 bytes.')
    expected={'pdf':data.startswith(b'%PDF-'),
        'png':data.startswith(b'\x89PNG\r\n\x1a\n'),
        'warc':data.startswith((b'WARC/1.0\r\n',b'WARC/1.1\r\n'))}
    if not expected[kind]:raise HTTPException(422,'Original file signature does not match its declared type.')
    return data

def pdf_text(data):
    try:
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(data),strict=True)
        if reader.is_encrypted:raise HTTPException(422,'Encrypted PDFs are not supported.')
        if len(reader.pages)>8:raise HTTPException(422,'At most eight PDF pages per evidence intake.')
        sections=[]
        for page in reader.pages:
            sections.append((page.extract_text() or '')[:6000])
        result='\n'.join(sections).strip()[:35000]
        return result
    except HTTPException:raise
    except Exception as exc:
        raise HTTPException(422,'The PDF could not be parsed safely in the bounded text extractor.') from exc

@router.post('/api/cases/{case_id}/evidence/{evidence_id}/source-artifacts',status_code=201)
def add_source_artifact(case_id:str,evidence_id:str,body:ArtifactIntake,
                        actor=Depends(core.protect)):
    if not body.rights_confirmed:
        raise HTTPException(422,'Document upload requires explicit source rights and retention authorization.')
    data=decode_asset(body.content_base64,body.asset_kind)
    original_hash=hashlib.sha256(data).hexdigest()
    extracted=pdf_text(data) if body.asset_kind=='pdf' else ''
    extracted_hash=hashlib.sha256(extracted.encode('utf-8')).hexdigest() if extracted else ''
    now=datetime.now(timezone.utc)
    stamp=now.isoformat(timespec='seconds')
    expires=(now+timedelta(days=body.retention_days)).isoformat(timespec='seconds')
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        e=c.execute('SELECT source_url,status FROM evidence WHERE case_id=? AND id=?',
                    (case_id,evidence_id)).fetchone()
        if not e:raise HTTPException(404,'Case evidence not found.')
        if e['status']=='rejected':raise HTTPException(422,'Cannot archive an explicitly rejected case source.')
        if e['source_url']!=body.evidence_url:
            raise HTTPException(422,'Archive provenance URL must exactly match original case evidence.')
        existing=c.execute('SELECT count(*) n FROM source_document_archives WHERE case_id=?',
                           (case_id,)).fetchone()['n']
        if existing>=30:raise HTTPException(429,'Per-case source-artifact limit reached.')
        archive_id=core.uid()
        capture_id=None
        if body.asset_kind=='pdf' and len(extracted)>=25:
            capture_id=core.uid()
            c.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
                (capture_id,case_id,evidence_id,body.evidence_url,'application/pdf',
                 extracted,extracted_hash,stamp,'captured','Manual file; original publisher not authenticated'))
        c.execute('INSERT INTO source_document_archives VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
           (archive_id,case_id,evidence_id,capture_id,body.evidence_url,body.asset_kind,
            original_hash,len(data),base64.b64encode(data).decode('ascii'),
            extracted_hash,stamp,expires,actor['id']))
    core.write_audit(actor['id'],'source_artifact_intake','evidence',evidence_id,archive_id)
    return {'id':archive_id,'originalSha256':original_hash,'bytes':len(data),
            'kind':body.asset_kind,'captureId':capture_id,
            'textExtracted':bool(capture_id),'expiresAt':expires,
            'notice':'User-supplied original, not a screenshot or WARC captured by this system. No OCR, malware inspection, page authorship or fact authentication.'}

@router.get('/api/cases/{case_id}/source-artifacts')
def list_source_artifacts(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        rows=[dict(x) for x in c.execute(
           'SELECT id,evidence_id,capture_id,original_url,asset_kind,original_sha256,'
           'byte_count,extracted_text_sha256,stored_at,expires_at FROM source_document_archives '
           'WHERE case_id=? ORDER BY stored_at DESC,id DESC LIMIT 100',(case_id,))]
    utc=datetime.now(timezone.utc)
    for row in rows:
        row['expired']=datetime.fromisoformat(row['expires_at'])<=utc
    return {'items':rows,'limitPerCase':30,
            'warning':'Case files require retention review and manually initiated deletion; external backup retention is not independently validated.'}

@router.get('/api/cases/{case_id}/source-artifacts/{artifact_id}/original')
def get_original_artifact(case_id:str,artifact_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        item=c.execute('SELECT original_sha256,content_b64,asset_kind,expires_at '
              'FROM source_document_archives WHERE case_id=? AND id=?',
              (case_id,artifact_id)).fetchone()
    if not item:raise HTTPException(404,'Source artifact not found.')
    if datetime.fromisoformat(item['expires_at'])<=datetime.now(timezone.utc):
        raise HTTPException(410,'Original retention window has ended; authorized deletion is required.')
    data=base64.b64decode(item['content_b64'])
    if hashlib.sha256(data).hexdigest()!=item['original_sha256']:
        raise HTTPException(409,'Stored original hash mismatch; do not rely on this artifact.')
    return Response(data,media_type='application/octet-stream',
        headers={'Content-Disposition':'attachment; filename="case-evidence.'+item['asset_kind']+'"',
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@router.delete('/api/cases/{case_id}/source-artifacts/{artifact_id}')
def delete_source_artifact(case_id:str,artifact_id:str,actor=Depends(core.protect)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        record=c.execute('SELECT id FROM source_document_archives WHERE case_id=? AND id=?',
                         (case_id,artifact_id)).fetchone()
        if not record:raise HTTPException(404,'Artifact not found.')
        c.execute('DELETE FROM source_document_archives WHERE case_id=? AND id=?',(case_id,artifact_id))
    core.write_audit(actor['id'],'source_artifact_delete','case',case_id,artifact_id)
    return {'deletedFromPrimaryDatabase':True,'backupErasureVerified':False}
