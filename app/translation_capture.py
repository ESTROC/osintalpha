"""Human-attested multilingual text review bound to preserved source capture offsets.

No OCR or automatic translation engine is installed. An analyst must supply
translation and review; quote offsets prove only string presence, not semantics.
"""
from __future__ import annotations
import hashlib,re
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

class TranslationCaptureReview(BaseModel):
    evidence_id:str=Field(min_length=1,max_length=80)
    capture_id:str=Field(min_length=1,max_length=80)
    source_start:int=Field(ge=0,le=50000)
    source_end:int=Field(gt=0,le=50000)
    original_text:str=Field(min_length=5,max_length=2000)
    translated_text:str=Field(min_length=5,max_length=3000)
    language_from:str=Field(min_length=2,max_length=15)
    language_to:str=Field(min_length=2,max_length=15)
    method:Literal['human_attested']='human_attested'
    reviewer_note:str=Field(min_length=25,max_length=600)
    rights_confirmed:bool=False

@router.post('/api/cases/{case_id}/captured-translations',status_code=201)
def record_translation(case_id:str,body:TranslationCaptureReview,actor=Depends(core.protect)):
    if not body.rights_confirmed:
        raise HTTPException(422,'Confirm permission to retain quoted and translated text.')
    if not all(re.fullmatch(r'[a-z]{2,3}(?:-[A-Z]{2})?',x) for x in (body.language_from,body.language_to)):
        raise HTTPException(422,'Use explicit IETF base language codes (e.g. hi, en, de).')
    if body.source_end<=body.source_start:
        raise HTTPException(422,'Invalid source text offset range.')
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        cap=conn.execute('SELECT extracted_text,content_sha256 FROM source_captures WHERE '
            'case_id=? AND evidence_id=? AND id=?',
            (case_id,body.evidence_id,body.capture_id)).fetchone()
        if not cap:raise HTTPException(404,'Captured text was not found in this case.')
        text=cap['extracted_text']
        if hashlib.sha256(text.encode('utf-8')).hexdigest()!=cap['content_sha256']:
            raise HTTPException(409,'Source text digest changed; recapture and review.')
        if text[body.source_start:body.source_end]!=body.original_text:
            raise HTTPException(422,'Original passage does not match the saved source at those offsets.')
        ident=core.uid()
        conn.execute('INSERT INTO translation_capture_reviews VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
          (ident,case_id,body.evidence_id,body.capture_id,cap['content_sha256'],
           body.source_start,body.source_end,body.original_text,body.translated_text,
           body.language_from,body.language_to,body.method,'human-attested-v1',
           body.reviewer_note.strip(),actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'captured_translation','evidence',body.evidence_id,ident)
    return {'id':ident,'sourceSha256':cap['content_sha256'],'methodVersion':'human-attested-v1',
            'translationIndependentlyVerified':False,'machineOcrPerformed':False}

@router.get('/api/cases/{case_id}/captured-translations')
def list_translations(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=[dict(x) for x in conn.execute(
            'SELECT * FROM translation_capture_reviews WHERE case_id=? '
            'ORDER BY reviewed_at DESC,id DESC LIMIT 80',(case_id,))]
    return {'items':rows,'machineTranslationEnabled':False,'ocrEnabled':False,
            'notice':'Human-submitted translation and exact source offsets; linguistic accuracy requires independent QA.'}
