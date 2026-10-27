"""Auditable query routing, recorded provider outcome and manual official no-match.
Manual no-match is a reviewer observation, never proof the person/company does not exist.
"""
import json
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
from .connectors import CATALOG

router=APIRouter()
OFFICIAL_HOSTS=('mca.gov.in','mcacdm.nic.in','gst.gov.in','services.gst.gov.in','gov.in','nic.in')

class OfficialNonMatch(BaseModel):
    query:str=Field(min_length=3,max_length=220)
    source_url:str=Field(min_length=12,max_length=600)
    search_scope:str=Field(min_length=15,max_length=500)
    limitation:str=Field(min_length=15,max_length=600)
    confirm_reviewed:bool=False

def official_url(value):
    try:parsed=urlsplit(value)
    except ValueError:return False
    host=(parsed.hostname or '').casefold()
    return parsed.scheme=='https' and parsed.username is None and parsed.password is None and not parsed.port and (
        host in OFFICIAL_HOSTS or host.endswith('.gov.in') or host.endswith('.nic.in'))

def explain_queries(plan,queries):
    configured={x.id for x in CATALOG}
    announced=set(plan.get('providers') or [])
    logged={str(x['provider']) for x in queries}
    skipped=[{'provider':p,'reason':'not_selected_by_current_case_policy',
              'expectedEvidence':'Source-specific public indexed candidates, not definitive identity'}
             for p in sorted(configured-announced-logged)]
    planned=[{'query':x,'origin':'saved_search_plan_variant','executed':any(q.get('query_text')==x for q in queries)}
            for x in (plan.get('queryVariants') or [])]
    executed=[{'provider':q['provider'],'query':q['query_text'],
               'status':q['status'],'returned':q['returned_count'],
               'message':q.get('message',''),'at':q.get('created_at',''),
               'isProofOfAbsence':False} for q in queries]
    return {'plannedQueryVariants':planned,'executedQueries':executed,
        'skippedStructuredProviders':skipped,
        'selectedProviders':sorted(announced),
        'identityVerified':False,
        'limitations':['A planned variant is not a completed request.',
                       'Not searched, empty and provider failed are different outcomes.',
                       'No-hit results cannot establish that a person or company does not exist.']}

@router.get('/api/cases/{case_id}/query-explain')
def explain_case(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        saved=c.execute('SELECT plan_json,original_question FROM case_search_plans WHERE case_id=?',(case_id,)).fetchone()
        queries=[dict(x) for x in c.execute('SELECT provider,query_text,status,returned_count,message,created_at '
                   'FROM research_queries WHERE case_id=? ORDER BY created_at DESC,id DESC LIMIT 250',(case_id,))]
    try:plan=json.loads(saved['plan_json']) if saved else {}
    except (ValueError,TypeError):plan={}
    return {'originalQuestion':saved['original_question'] if saved else '',
            **explain_queries(plan,queries)}

@router.post('/api/cases/{case_id}/official-nonmatch',status_code=201)
def record_official_nonmatch(case_id:str,body:OfficialNonMatch,actor=Depends(core.protect)):
    if not body.confirm_reviewed:
        raise HTTPException(422,'The analyst must explicitly confirm personal review of the official page.')
    if not official_url(body.source_url):
        raise HTTPException(422,'A public HTTPS .gov.in or .nic.in official source is required.')
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        now=core.iso_now()
        payload={'sourceUrl':body.source_url,'searchScope':body.search_scope.strip(),
            'limitation':body.limitation.strip(),'analystId':actor['id'],
            'recordType':'analyst_observed_official_no_match','independentProviderSearch':False,
            'personOrCompanyAbsenceProven':False}
        record_id=core.uid()
        conn.execute('INSERT INTO research_queries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (record_id,case_id,actor['id'],record_id,'official_manual_review',
             body.query.strip(),'empty',0,0,json.dumps(payload,ensure_ascii=False),now))
    core.write_audit(actor['id'],'official_no_match','case',case_id,record_id)
    return {'id':record_id,'reviewType':'analyst_observed_no_match',
        'provesAbsence':False,'notice':'The recorded check is not an official negative certification or comprehensive search.'}

@router.get('/api/cases/{case_id}/official-nonmatches')
def official_nonmatches(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        rows=[dict(x) for x in c.execute(
            "SELECT id,query_text,message,created_at FROM research_queries WHERE case_id=? "
            "AND provider='official_manual_review' ORDER BY created_at DESC,id DESC LIMIT 100",(case_id,))]
    result=[]
    for row in rows:
        try:metadata=json.loads(row['message'])
        except (ValueError,TypeError):metadata={}
        result.append({'id':row['id'],'query':row['query_text'],'reviewedAt':row['created_at'],
           **metadata,'provesAbsence':False})
    return {'items':result,'noMatchIsProofOfNonexistence':False}
