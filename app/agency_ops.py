"""Agency extensions: scoped research productivity tools, no automatic identity assertions."""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from . import db
from . import main as core
from .connectors import CATALOG

router=APIRouter()

def case_record(conn,case_id,actor):
    return core.case_or_404(conn,case_id,actor)

def source_in_case(conn,case_id,evidence_id):
    row=conn.execute('SELECT id,label,source_url,status,provider,fetched_at,observed_at,raw_json FROM evidence WHERE case_id=? AND id=?',
                     (case_id,evidence_id)).fetchone()
    if not row:
        raise HTTPException(404,'Evidence source not found in authorized case.')
    return dict(row)

def ensure_url(value):
    if not value:return ''
    try:
        p=urlparse(value)
        if p.scheme!='https' or not p.hostname or p.username or p.password or len(value)>500:
            raise ValueError()
    except ValueError:
        raise HTTPException(422,'Use an original public HTTPS URL without credentials.')
    return value

def review_digest(conn,case_id):
    ass=conn.execute('SELECT * FROM case_assessments WHERE case_id=?',(case_id,)).fetchone()
    claims=[dict(r) for r in conn.execute(
        'SELECT claim_text,evidence_id,stance FROM claim_links WHERE case_id=? ORDER BY id',(case_id,))]
    evidence=[dict(r) for r in conn.execute(
        'SELECT id,status,sha256 FROM evidence WHERE case_id=? ORDER BY id',(case_id,))]
    raw=json.dumps({'assessment':dict(ass) if ass else None,'claims':claims,
                    'evidence':evidence},sort_keys=True,default=str)
    return hashlib.sha256(raw.encode()).hexdigest()

class AliasInput(BaseModel):
    alias:str=Field(min_length=2,max_length=160)
    alias_type:Literal['alternative_name','transliteration','brand','former_name','known_public_handle']
    source_url:str=Field(default='',max_length=500)
    rationale:str=Field(min_length=12,max_length=700)

@router.get('/api/cases/{case_id}/aliases')
def get_aliases(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        case_record(c,case_id,actor)
        rows=[dict(x) for x in c.execute('SELECT * FROM research_aliases WHERE case_id=? ORDER BY created_at DESC,id DESC LIMIT 150',(case_id,))]
    return {'items':rows,'notice':'Aliases are analyst assertions with cited source/rationale; not independently verified names.'}

@router.post('/api/cases/{case_id}/aliases',status_code=201)
def add_alias(case_id:str,body:AliasInput,actor=Depends(core.protect)):
    url=ensure_url(body.source_url)
    with db.connect() as c:
        case_record(c,case_id,actor)
        duplicate=c.execute('SELECT id FROM research_aliases WHERE case_id=? AND lower(alias)=lower(?) AND alias_type=?',
                            (case_id,body.alias.strip(),body.alias_type)).fetchone()
        if duplicate:raise HTTPException(409,'This alias is already recorded for the case.')
        ident=core.uid()
        c.execute('INSERT INTO research_aliases VALUES (?,?,?,?,?,?,?,?)',
                  (ident,case_id,body.alias.strip(),body.alias_type,url,body.rationale.strip(),actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'alias_add','case',case_id,ident)
    return {'id':ident,'status':'unverified_alias'}

@router.get('/api/source-taxonomy')
def source_taxonomy(actor=Depends(core.actor_from_cookie)):
    source_rows=[]
    for x in CATALOG:
        coverage=('Global public API, may omit local or nonindexed records')
        if x.id in ('wikipedia','wikidata'):
            coverage='Global (the configured endpoint is English-language)'
        elif x.id=='gleif':
            coverage='LEI-covered legal entities; not every registered business'
        elif x.id in ('github','stackoverflow'):
            coverage='Public technical accounts only, not a general population directory'
        source_rows.append({'id':x.id,'name':x.title,'scope':x.scope,
                            'jurisdiction':'variable_or_global','coverage':coverage,'dataRights':'Check publisher conditions'})
    return {'sources':source_rows,'notice':'Coverage is descriptive, not an independently tested jurisdictional completeness certification.'}

class RelationshipInput(BaseModel):
    left_name:str=Field(min_length=2,max_length=160)
    right_name:str=Field(min_length=2,max_length=160)
    relationship:str=Field(min_length=3,max_length=100)
    evidence_id:str=Field(min_length=4,max_length=80)
    rationale:str=Field(min_length=20,max_length=900)

@router.get('/api/cases/{case_id}/relationships')
def relations(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        case_record(c,case_id,actor)
        rows=[dict(x) for x in c.execute(
            'SELECT r.*,e.source_url evidence_url,e.status evidence_status FROM sourced_relationships r JOIN evidence e ON e.id=r.evidence_id WHERE r.case_id=? ORDER BY r.created_at DESC LIMIT 200',(case_id,))]
    return {'items':rows,'notice':'Edges are proposed assertions, not established people or legal relationships.'}

@router.post('/api/cases/{case_id}/relationships',status_code=201)
def relation_add(case_id:str,body:RelationshipInput,actor=Depends(core.protect)):
    with db.connect() as c:
        case_record(c,case_id,actor)
        source_in_case(c,case_id,body.evidence_id)
        ident=core.uid()
        c.execute('INSERT INTO sourced_relationships VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                  (ident,case_id,body.left_name.strip(),body.right_name.strip(),
                   body.relationship.strip(),body.evidence_id,body.rationale.strip(),
                   'proposed',actor['id'],core.iso_now(),None,None))
    core.write_audit(actor['id'],'relationship_proposed','case',case_id,ident)
    return {'id':ident,'reviewState':'proposed'}

class RelationshipReview(BaseModel):
    review_state:Literal['reviewed_public_record','disputed','rejected']
    note:str=Field(min_length=20,max_length=800)

@router.patch('/api/cases/{case_id}/relationships/{relation_id}')
def relation_review(case_id:str,relation_id:str,body:RelationshipReview,actor=Depends(core.protect)):
    with db.connect() as c:
        case_record(c,case_id,actor)
        x=c.execute('SELECT id FROM sourced_relationships WHERE id=? AND case_id=?',(relation_id,case_id)).fetchone()
        if not x:raise HTTPException(404,'Relationship not found.')
        c.execute('UPDATE sourced_relationships SET review_state=?,rationale=?,reviewed_by=?,reviewed_at=? WHERE id=?',
                  (body.review_state,body.note.strip(),actor['id'],core.iso_now(),relation_id))
    core.write_audit(actor['id'],'relationship_review','case',case_id,body.review_state)
    return {'reviewState':body.review_state}

@router.get('/api/cases/{case_id}/timeline')
def timeline(case_id:str,limit:int=Query(default=120,ge=1,le=500),actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        case_record(c,case_id,actor)
        items=[]
        rows=c.execute('SELECT id,label,provider,status,source_url,observed_at,fetched_at FROM evidence WHERE case_id=? ORDER BY fetched_at DESC LIMIT ?',
                       (case_id,limit))
        for r in rows:
            row=dict(r)
            # Observation date supplied by publisher != time we fetched it.
            items.append({'evidenceId':row['id'],'title':row['label'],'provider':row['provider'],
                          'eventDate':row['observed_at'] or None,
                          'fetchedAt':row['fetched_at'],'dateBasis':'publisher_observed' if row['observed_at'] else 'retrieved_only',
                          'url':row['source_url'],'reviewStatus':row['status'],
                          'note':'Date only reflects source metadata, not a verified real-world event.'})
    return {'items':items,'dateType':'observation_or_retrieval','notice':'A retrieval time is never proof that an event occurred then.'}

@router.get('/api/cases/{case_id}/evidence-page')
def evidence_page(case_id:str,limit:int=Query(default=25,ge=1,le=100),
                  offset:int=Query(default=0,ge=0,le=1000000),
                  status:Literal['all','candidate','corroborated','disputed','rejected']='all',
                  actor=Depends(core.actor_from_cookie)):
    clause=' AND status=?' if status!='all' else ''
    args=[case_id]+([status] if status!='all' else [])
    with db.connect() as c:
        case_record(c,case_id,actor)
        total=c.execute('SELECT count(*) n FROM evidence WHERE case_id=?'+clause,args).fetchone()['n']
        rows=[dict(x) for x in c.execute(
            'SELECT id,provider,label,summary,source_url,fetched_at,observed_at,status,reviewer_notes FROM evidence WHERE case_id=?'+clause+
            ' ORDER BY fetched_at DESC,id DESC LIMIT ? OFFSET ?',args+[limit,offset])]
    return {'items':rows,'total':total,'limit':limit,'offset':offset,'hasMore':offset+len(rows)<total}

@router.get('/api/cases/{case_id}/methodology')
def methodology(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        case=case_record(c,case_id,actor)
        queries=[dict(r) for r in c.execute(
            'SELECT provider,query_text,status,returned_count,message,created_at FROM research_queries WHERE case_id=? ORDER BY created_at,id LIMIT 1000',
            (case_id,))]
        providers={p.id:p.title for p in CATALOG}
        ignored=[p for p in providers if p not in {x['provider'] for x in queries}]
    return {'caseId':case_id,'scope':case['purpose'],
            'queries':queries,'unqueriedStructuredSources':ignored,
            'method':'Public indexed web and selected public APIs; unverified candidates requiring original-page checking.',
            'limitations':['Provider indexes are incomplete','Missing records are not proof of absence',
                           'Retrieval dates differ from publication dates','Namesakes must be independently excluded'],
            'generatedAt':core.iso_now()}

@router.get('/api/cases/{case_id}/evidence-pack')
def evidence_pack(case_id:str,reviewed_only:bool=True,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        case=case_record(c,case_id,actor)
        clause=" AND e.status='corroborated'" if reviewed_only else ''
        evidence=[dict(x) for x in c.execute(
            'SELECT e.id,e.provider,e.label,e.summary,e.source_url,e.fetched_at,e.observed_at,e.sha256,e.status,e.reviewer_notes FROM evidence e WHERE e.case_id=?'+clause+' ORDER BY e.provider,e.label LIMIT 1500',
            (case_id,))]
        claims=[dict(x) for x in c.execute(
            'SELECT l.claim_text,l.stance,l.evidence_id,e.status evidence_status,e.source_url FROM claim_links l JOIN evidence e ON e.id=l.evidence_id WHERE l.case_id=?'+
            (" AND e.status='corroborated'" if reviewed_only else '')+' ORDER BY l.created_at LIMIT 1000',(case_id,))]
        stamp=c.execute('SELECT decision,note,signed_at,review_digest FROM case_signoffs WHERE case_id=? ORDER BY signed_at DESC,id DESC LIMIT 1',(case_id,)).fetchone()
        current=review_digest(c,case_id)
    signer=dict(stamp) if stamp else None
    return {'caseId':case_id,'subject':case['query'],'generatedAt':core.iso_now(),
            'reviewedOnly':reviewed_only,'claims':claims,'evidence':evidence,
            'signoff':signer,'signoffCurrent':bool(signer and signer['review_digest']==current),
            'integrityNotice':'Source metadata hashes are NOT a forensic capture or certified chain of custody.',
            'distributionNotice':'Review source authenticity, identity, rights and sensitive assertions before sharing.'}

class SignoffInput(BaseModel):
    decision:Literal['reviewed_with_limitations','not_approved']
    note:str=Field(min_length=30,max_length=1500)

@router.post('/api/cases/{case_id}/signoffs',status_code=201)
def signoff(case_id:str,body:SignoffInput,actor=Depends(core.protect)):
    with db.connect() as c:
        case_record(c,case_id,actor)
        pending=c.execute("SELECT count(*) n FROM evidence WHERE case_id=? AND status='disputed'",(case_id,)).fetchone()['n']
        ass=c.execute('SELECT executive_summary,limitations FROM case_assessments WHERE case_id=?',(case_id,)).fetchone()
        if body.decision=='reviewed_with_limitations' and (pending or not ass or not ass['executive_summary'] or not ass['limitations']):
            raise HTTPException(422,'Resolve disputed evidence and complete assessment limitations before signoff.')
        if body.decision=='reviewed_with_limitations':
            from .decision_readiness import evidence_digest
            baseline=c.execute('SELECT evidence_digest FROM assessment_review_baselines WHERE case_id=?',(case_id,)).fetchone()
            if not baseline or baseline['evidence_digest']!=evidence_digest(c,case_id):
                raise HTTPException(409,'Assessment must be re-reviewed and saved after source changes before a current signoff.')
        digest=review_digest(c,case_id)
        ident=core.uid()
        c.execute('INSERT INTO case_signoffs VALUES (?,?,?,?,?,?,?)',
                  (ident,case_id,actor['id'],body.decision,body.note.strip(),core.iso_now(),digest))
    core.write_audit(actor['id'],'report_signoff','case',case_id,body.decision)
    return {'id':ident,'decision':body.decision,'reviewDigest':digest}

@router.get('/api/cases/{case_id}/signoffs')
def signoffs(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        case_record(c,case_id,actor)
        rows=[dict(r) for r in c.execute(
            'SELECT s.*,u.username signer FROM case_signoffs s JOIN users u ON u.id=s.actor_id WHERE s.case_id=? ORDER BY s.signed_at DESC LIMIT 100',(case_id,))]
        current=review_digest(c,case_id)
    for x in rows:x['stillCurrent']=x['review_digest']==current
    return {'items':rows}

@router.get('/api/agency/compare-cases')
def compare_cases(left:str,right:str,actor=Depends(core.actor_from_cookie)):
    if left==right:raise HTTPException(422,'Choose two distinct authorized investigations.')
    with db.connect() as c:
        a=case_record(c,left,actor);b=case_record(c,right,actor)
        def read(caseid):
            return [dict(x) for x in c.execute(
                "SELECT provider,source_url,status FROM evidence WHERE case_id=? ORDER BY source_url LIMIT 2000",(caseid,))]
        ar,br=read(left),read(right)
    la={(e['provider'],e['source_url']) for e in ar}
    lb={(e['provider'],e['source_url']) for e in br}
    return {'left':{'id':left,'title':a['title'],'records':len(ar)},
            'right':{'id':right,'title':b['title'],'records':len(br)},
            'commonSources':len(la&lb),'leftOnly':len(la-lb),'rightOnly':len(lb-la),
            'notice':'Same original URL may be reused across cases; this does NOT prove a shared person or relationship.'}

@router.get('/api/cases/{case_id}/answer-diff')
def answer_diff(case_id:str,left:str,right:str,actor=Depends(core.actor_from_cookie)):
    if left==right:raise HTTPException(422,'Select distinct saved conversation IDs.')
    with db.connect() as c:
        case_record(c,case_id,actor)
        answers=[]
        for sid in (left,right):
            row=c.execute('SELECT owner_id FROM research_sessions WHERE id=? AND case_id=?',(sid,case_id)).fetchone()
            if not row or (row['owner_id']!=actor['id'] and actor['role']!='admin'):
                raise HTTPException(404,'Conversation not available to this analyst.')
            recent=c.execute("SELECT content FROM research_messages WHERE session_id=? AND role='assistant' ORDER BY message_index DESC LIMIT 1",(sid,)).fetchone()
            answers.append((recent['content'] if recent else '')[:12000])
    delta=list(difflib.unified_diff(answers[0].splitlines(),answers[1].splitlines(),fromfile=left,tofile=right,lineterm=''))[:500]
    return {'diff':delta,'note':'Text differences are not proof that a factual claim changed or that new evidence is correct.'}

@router.get('/api/cases/{case_id}/citation-overlap')
def citation_overlap(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        case_record(c,case_id,actor)
        records=[dict(x) for x in c.execute(
            "SELECT m.web_leads_json,m.evidence_ids_json FROM research_messages m JOIN research_sessions s ON s.id=m.session_id WHERE s.case_id=? AND m.role='assistant' AND (?='admin' OR s.owner_id=?) ORDER BY m.created_at DESC LIMIT 100",(case_id,actor['role'],actor['id']))]
    counts=Counter()
    for row in records:
        try:leads=json.loads(row['web_leads_json'] or '[]')
        except (ValueError,TypeError):leads=[]
        for v in leads:
            if isinstance(v,dict) and v.get('url'):counts[v['url']]+=1
    return {'repeatedWebCitations':[{'url':x,'answerCount':n} for x,n in counts.most_common(30) if n>1],
            'notice':'Repeated links across AI answers are not independent corroborating sources.'}

RECIPES=[
 {'id':'general','title':'Public source review','question':'Find verifiable public records and clearly separate unrelated namesakes'},
 {'id':'organization','title':'Organization due diligence','question':'Find public company registration, official publications and relevant business disclosures'},
 {'id':'student','title':'Student public activities','question':'Find publicly documented education, projects, events and participation without assuming publication records'},
 {'id':'trade','title':'Service/business public footprint','question':'Find public service listings, websites and registries without implying the owner is identified'},
 {'id':'domain','title':'Passive domain assessment','question':'Review published passive domain and public infrastructure metadata without active scanning'}]

@router.get('/api/research/recipes')
def recipes(actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        owned=[dict(r) for r in c.execute('SELECT * FROM agency_recipes WHERE owner_id=? ORDER BY updated_at DESC LIMIT 100',(actor['id'],))]
    return {'builtIn':RECIPES,'saved':owned}

class RecipeInput(BaseModel):
    title:str=Field(min_length=4,max_length=90)
    description:str=Field(default='',max_length=240)
    question:str=Field(min_length=12,max_length=280)

@router.post('/api/research/recipes',status_code=201)
def save_recipe(body:RecipeInput,actor=Depends(core.protect)):
    with db.connect() as c:
        ident=core.uid();stamp=core.iso_now()
        c.execute('INSERT INTO agency_recipes VALUES (?,?,?,?,?,?,?,?)',
                  (ident,actor['id'],body.title.strip(),body.description.strip(),body.question.strip(),1,stamp,stamp))
    core.write_audit(actor['id'],'recipe_create','user',actor['id'],ident)
    return {'id':ident,'version':1}

@router.get('/api/research/ops-status')
def operations(actor=Depends(core.actor_from_cookie)):
    import os
    with db.connect() as c:
        aggregate=[dict(x) for x in c.execute(
            """SELECT r.provider,r.state,count(*) n,MAX(r.ran_at) lastAttempt
               FROM collection_runs r JOIN cases c ON c.id=r.case_id
               WHERE (?='admin' OR c.created_by=? OR EXISTS
                   (SELECT 1 FROM case_members m WHERE m.case_id=c.id AND m.user_id=?))
               GROUP BY r.provider,r.state ORDER BY r.provider,r.state LIMIT 80""",
            (actor['role'],actor['id'],actor['id']))]
    return {'apiStatus':'ok','utc':core.iso_now(),'version':'8.0.0',
            'configured':{'Brave':bool(os.getenv('BRAVE_SEARCH_API_KEY')),
                          'Groq':bool(os.getenv('GROQ_API_KEY')),
                          'TfL':bool(os.getenv('TFL_APP_KEY'))},
            'collectionCounts':aggregate,
            'notice':'Observed case collection history, NOT continuous provider uptime monitoring.'}

@router.get('/api/agency/metrics')
def metrics(actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        clause='' if actor['role']=='admin' else ' WHERE created_by=?'
        args=[] if actor['role']=='admin' else [actor['id']]
        cases=c.execute('SELECT count(*) n FROM cases'+clause,args).fetchone()['n']
        q=c.execute('SELECT count(*) n FROM evidence WHERE case_id IN (SELECT id FROM cases'+clause+')',args).fetchone()['n']
        open_tasks=c.execute("SELECT count(*) n FROM investigation_tasks WHERE status IN ('todo','in_progress','blocked','awaiting_review') AND case_id IN (SELECT id FROM cases"+clause+')',args).fetchone()['n']
        errors=c.execute("SELECT count(*) n FROM research_queries WHERE status='error' AND case_id IN (SELECT id FROM cases"+clause+')',args).fetchone()['n']
    return {'cases':cases,'sourceCandidates':q,'outstandingTasks':open_tasks,'providerErrors':errors,
            'notice':'These workload counts do not measure useful findings, accuracy or analyst performance.'}

class FeedbackInput(BaseModel):
    evidence_id:str
    relevance:Literal['useful','irrelevant','wrong_subject','needs_review']
    rationale:str=Field(min_length=20,max_length=900)

@router.post('/api/cases/{case_id}/source-feedback',status_code=201)
def feedback(case_id:str,body:FeedbackInput,actor=Depends(core.protect)):
    with db.connect() as c:
        case_record(c,case_id,actor);source_in_case(c,case_id,body.evidence_id)
        ident=core.uid()
        c.execute('INSERT INTO source_feedback VALUES (?,?,?,?,?,?,?)',
                  (ident,case_id,body.evidence_id,actor['id'],body.relevance,
                   body.rationale.strip(),core.iso_now()))
    core.write_audit(actor['id'],'source_feedback','case',case_id,body.relevance)
    return {'id':ident,'trainingStatus':'feedback_recorded_not_automatically_trained'}

class TranslationInput(BaseModel):
    evidence_id:str
    language:str=Field(min_length=2,max_length=60)
    source_quote:str=Field(min_length=10,max_length=3000)
    translation:str=Field(min_length=10,max_length=3000)
    translator:str=Field(min_length=3,max_length=100)

@router.post('/api/cases/{case_id}/translation-notes',status_code=201)
def translation_note(case_id:str,body:TranslationInput,actor=Depends(core.protect)):
    with db.connect() as c:
        case_record(c,case_id,actor);source_in_case(c,case_id,body.evidence_id)
        ident=core.uid()
        c.execute('INSERT INTO translation_notes VALUES (?,?,?,?,?,?,?,?,?)',
                  (ident,case_id,body.evidence_id,body.language,body.source_quote,
                   body.translation,body.translator,actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'translation_note','case',case_id,ident)
    return {'id':ident,'notice':'Analyst-supplied translation note, not machine OCR or independently verified translation.'}

@router.get('/api/cases/{case_id}/translation-notes')
def get_translations(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        case_record(c,case_id,actor)
        rows=[dict(x) for x in c.execute('SELECT * FROM translation_notes WHERE case_id=? ORDER BY created_at DESC LIMIT 100',(case_id,))]
    return {'items':rows}


class TaskBatchInput(BaseModel):
    ids:list[str]=Field(min_length=1,max_length=20)
    status:Literal['todo','in_progress','blocked','awaiting_review','cancelled']
    note:str=Field(min_length=20,max_length=800)

@router.post('/api/cases/{case_id}/tasks/batch')
def task_batch(case_id:str,body:TaskBatchInput,actor=Depends(core.protect)):
    ids=list(dict.fromkeys(body.ids))
    if len(ids)>20:raise HTTPException(422,'At most twenty tasks may be updated at once.')
    with db.connect() as c:
        case_record(c,case_id,actor)
        # Fail the entire batch if even one id is outside this case.
        rows=[dict(x) for x in c.execute(
            'SELECT id,status FROM investigation_tasks WHERE case_id=? AND id IN ('+
            ','.join('?' for _ in ids)+')',[case_id]+ids)]
        if len(rows)!=len(ids):
            raise HTTPException(404,'One or more tasks are not in the authorized case.')
        now=core.iso_now()
        for row in rows:
            c.execute('UPDATE investigation_tasks SET status=?,updated_at=? WHERE id=?',
                      (body.status,now,row['id']))
            c.execute('INSERT INTO investigation_task_events VALUES (?,?,?,?,?,?,?,?)',
                      (core.uid(),row['id'],case_id,actor['id'],row['status'],body.status,body.note.strip(),now))
    core.write_audit(actor['id'],'batch_task_update','case',case_id,str(len(rows))+' '+body.status)
    return {'changed':len(rows),'status':body.status,
            'notice':'Batch marking tasks done is intentionally disabled; final review requires individual evidence.'}

@router.post('/api/cases/{case_id}/suggest-review-tasks')
def suggest_review_tasks(case_id:str,limit:int=Query(default=5,ge=1,le=10),actor=Depends(core.protect)):
    with db.connect() as c:
        case_record(c,case_id,actor)
        candidates=[dict(r) for r in c.execute(
            "SELECT id,label,status,source_url FROM evidence WHERE case_id=? AND status IN ('candidate','disputed') ORDER BY fetched_at DESC,id DESC LIMIT 50",(case_id,))]
        existing=[x['description'] for x in c.execute(
            'SELECT description FROM investigation_tasks WHERE case_id=?',(case_id,))]
        created=[]
        for ev in candidates:
            if any(ev['id'] in desc for desc in existing):continue
            tid=core.uid();now=core.iso_now()
            title=('Verify original source: '+ev['label'])[:150]
            details=('Review source ownership, namesakes and factual reliability; evidence ID: '+ev['id']+
                     '; original URL: '+ev['source_url'])[:1100]
            c.execute('INSERT INTO investigation_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                      (tid,case_id,title,details,'todo','high' if ev['status']=='disputed' else 'normal',
                       actor['id'],'',actor['id'],now,now))
            c.execute('INSERT INTO investigation_task_events VALUES (?,?,?,?,?,?,?,?)',
                      (core.uid(),tid,case_id,actor['id'],'','todo','Source verification proposed by analyst',now))
            created.append(tid)
            if len(created)>=limit:break
    core.write_audit(actor['id'],'suggest_review_tasks','case',case_id,str(len(created)))
    return {'created':len(created),'taskIds':created,
            'notice':'Suggested work, not automated identity corroboration.'}

@router.get('/api/cases/{case_id}/export-preview')
def export_preview(case_id:str,reviewed_only:bool=True,redact_labels:bool=True,actor=Depends(core.actor_from_cookie)):
    pack=evidence_pack(case_id,reviewed_only,actor)
    # Redacted preview is distinct from full evidence pack; original URLs are
    # intentionally not leaked in redacted previews.
    rows=[]
    for e in pack['evidence']:
        rows.append({'provider':e['provider'],
                     'label':'[redacted candidate label]' if redact_labels else e['label'],
                     'status':e['status'],
                     'fetchedAt':e['fetched_at'],
                     'url':None if redact_labels else e['source_url']})
    return {'caseId':case_id,'preview':rows,'counts':{
               'included':len(rows),'claims':len(pack['claims'])},
            'signedOff':bool(pack['signoffCurrent'] and pack['signoff'] and
                             pack['signoff']['decision']=='reviewed_with_limitations'),
            'redactLabels':redact_labels,'reviewedOnly':reviewed_only,
            'notice':'Preview is not a signed or automatically redacted PDF. A reviewer must inspect the final export and sources.'}


class CanaryInput(BaseModel):
    provider:Literal['github','stackoverflow','openalex','crossref','gleif','wikipedia','wikidata','gdelt']
    consent:bool=False

@router.post('/api/research/provider-canary')
async def provider_canary(body:CanaryInput,actor=Depends(core.protect)):
    """On-demand real public API compatibility smoke; no private case or personal input."""
    if not body.consent:
        raise HTTPException(422,'Authorize a real upstream provider canary request.')
    from .connectors import collect_one
    samples={
        'github':('octocat','person'),
        'stackoverflow':('John Carmack','person'),
        'openalex':('Ada Lovelace','person'),
        'crossref':('Ada Lovelace','person'),
        'gleif':('Apple Inc','organization'),
        'wikipedia':('Ada Lovelace','person'),
        'wikidata':('Ada Lovelace','person'),
        'gdelt':('NASA','organization'),
    }
    query,kind=samples[body.provider]
    try:
        results=await collect_one(body.provider,query,kind)
        status='ok' if results else 'empty'
        note='Received compatible public-source candidate records' if results else 'No results for fixed canary term; this alone does not indicate outage'
        count=len(results)
    except Exception as exc:
        status='error';note='Provider request unsuccessful: '+type(exc).__name__;count=0
    core.write_audit(actor['id'],'provider_canary','source',body.provider,status)
    return {'provider':body.provider,'status':status,'candidateCount':count,
            'checkedAt':core.iso_now(),'sampleQuery':query,'message':note,
            'notice':'Manual live connectivity check only; this does not verify relevance, coverage, uptime or an identity match.'}

@router.get('/api/research/model-configuration')
def model_configuration(actor=Depends(core.actor_from_cookie)):
    import os
    model=os.getenv('GROQ_MODEL','openai/gpt-oss-120b')
    return {'provider':'Groq','model':model,'configured':bool(os.getenv('GROQ_API_KEY')),
            'toolModes':['structured_output','browser_search_separate'],
            'validation':'configured only, not a live model capability probe',
            'testedAgainst':'Mocked API and CI model fixtures; real-model release acceptance still required.'}
