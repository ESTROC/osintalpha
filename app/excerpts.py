"""Source-linked passage extraction with exact-match verification.

Matching a passage demonstrates text appeared in a saved capture. It does not
prove the author, page authenticity or factual truth of its interpretation.
"""
from __future__ import annotations
import hashlib
import re
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db
from . import main as core

router=APIRouter()

class ExcerptInput(BaseModel):
    evidence_id:str=Field(min_length=1,max_length=80)
    capture_id:str=Field(min_length=1,max_length=80)
    quote_text:str=Field(min_length=25,max_length=700)
    interpretation:str=Field(min_length=10,max_length=1000)

def norm(value):
    return ' '.join(re.sub(r'\s+',' ',value).split()).casefold()

def exact_span(original,quote):
    # A semantically similar paraphrase is never accepted as verbatim evidence.
    return bool(norm(quote)) and norm(quote) in norm(original)

@router.post('/api/cases/{case_id}/excerpts',status_code=201)
def add_excerpt(case_id:str,body:ExcerptInput,actor=Depends(core.protect)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        record=c.execute('''SELECT sc.id,sc.content_sha256,sc.extracted_text,sc.fetched_at,
              e.status,e.source_url FROM source_captures sc JOIN evidence e ON e.id=sc.evidence_id
              WHERE sc.id=? AND sc.evidence_id=? AND sc.case_id=?''',
              (body.capture_id,body.evidence_id,case_id)).fetchone()
        if not record:raise HTTPException(422,'Capture must belong to this evidence record and investigation.')
        if record['status']=='rejected':raise HTTPException(422,'Rejected source records cannot support new excerpts.')
        if not exact_span(record['extracted_text'],body.quote_text):
            raise HTTPException(422,'The quoted words were not found verbatim in the stored source-text capture.')
        # Check the hash of the saved text at the time the excerpt is registered.
        digest=hashlib.sha256(record['extracted_text'].encode('utf-8')).hexdigest()
        if digest!=record['content_sha256']:
            raise HTTPException(409,'Stored capture integrity check failed.')
        id=core.uid()
        c.execute('INSERT INTO verified_excerpts VALUES (?,?,?,?,?,?,?,?,?,?)',
              (id,case_id,body.evidence_id,body.capture_id,body.quote_text.strip(),
               body.interpretation.strip(),digest,'excerpt_matched',actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'excerpt_match','evidence',body.evidence_id,body.capture_id)
    return {'id':id,'status':'excerpt_matched',
            'note':'Exact text match only. The statement is not independently established as fact.'}

@router.get('/api/cases/{case_id}/excerpts')
def list_excerpts(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        rows=c.execute('''SELECT q.id,q.evidence_id,q.capture_id,q.quote_text,q.interpretation,
             q.content_sha256,q.review_status,q.created_at,
             e.label,e.source_url,e.status evidence_status,
             sc.content_sha256 capture_sha,
             (SELECT content_sha256 FROM source_captures
              WHERE evidence_id=q.evidence_id AND case_id=q.case_id
              ORDER BY fetched_at DESC,id DESC LIMIT 1) latest_sha
             FROM verified_excerpts q JOIN evidence e ON e.id=q.evidence_id
             JOIN source_captures sc ON sc.id=q.capture_id
             WHERE q.case_id=? ORDER BY q.created_at DESC,q.id DESC LIMIT 250''',(case_id,))
        items=[dict(row) for row in rows]
    for row in items:
        row['captureIntegrityOk']=row['content_sha256']==row['capture_sha']
        row['latestCaptureUnchanged']=row['content_sha256']==row['latest_sha']
        row['supportsTruth']=False
        del row['capture_sha']
        del row['latest_sha']
    return {'items':items,'note':'Only exact-match quotation with capture hash validation. Source authenticity, account ownership and factual truth are not verified.'}
