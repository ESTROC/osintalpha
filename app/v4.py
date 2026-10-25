"""V4 investigator workflow: planned collection, candidates, source claims, assessment."""
from __future__ import annotations
import asyncio
import hashlib
import html
import json
from typing import Literal
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response as ApiResponse
from pydantic import BaseModel, Field
from . import db
from . import main as core
from .research import plan
router=APIRouter()

class ResearchInput(BaseModel):
    depth:Literal['quick','standard','thorough']='standard'
    providers:list[str]|None=Field(default=None,max_length=8)

def read_case(case_id,actor):
    with db.connect() as c:
        return core.case_or_404(c,case_id,actor)

def get_context(case_id):
    with db.connect() as c:
        r=c.execute('SELECT city,organization,profession,public_handle FROM case_context WHERE case_id=?',(case_id,)).fetchone()
    return dict(r) if r else {}

@router.get('/api/cases/{case_id}/research-plan')
def research_plan(case_id:str,depth:Literal['quick','standard','thorough']='standard',actor=Depends(core.actor_from_cookie)):
    case=read_case(case_id,actor)
    steps=plan(case,get_context(case_id),depth)
    return {'subject':case['query'],'depth':depth,'queries':[vars(p) for p in steps],
            'limitation':'Queries target allowlisted public-source APIs. No general-web index or validated identity resolution.'}

@router.post('/api/cases/{case_id}/research')
async def research(case_id:str,body:ResearchInput,actor=Depends(core.protect)):
    case=read_case(case_id,actor)
    context=get_context(case_id)
    steps=plan(case,context,body.depth,body.providers)
    if not steps:raise HTTPException(422,'No compatible collectors selected.')
    run_id=core.uid()
    sem=asyncio.Semaphore(4)
    async with httpx.AsyncClient(timeout=15,headers={'User-Agent':'OSINTAlpha/4.0 permitted public-source research'},follow_redirects=False) as client:
        async def run(step):
            async with sem:
                try:return await core.collect_one(step.provider,step.query,case['subject_type'],client)
                except Exception as exc:return exc
        responses=await asyncio.gather(*(run(step) for step in steps))
    result=[]
    with db.connect() as c:
        for step,returned in zip(steps,responses):
            count=0
            received=0
            if isinstance(returned,Exception):
                status='error';message=str(returned)[:240]
            else:
                status='ok' if returned else 'empty'
                received=len(returned)
                for record in returned[:60]:
                    raw=json.dumps(record.raw,sort_keys=True,ensure_ascii=False,default=str)
                    digest=hashlib.sha256(raw.encode()).hexdigest()
                    cur=c.execute('''INSERT OR IGNORE INTO evidence
                     (id,case_id,provider,label,summary,source_url,source_ref,fetched_at,observed_at,sha256,raw_json)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                     (core.uid(),case_id,step.provider,record.label,record.summary,record.url,
                      record.source_ref or digest,core.iso_now(),record.observed_at,digest,raw))
                    count+=cur.rowcount
                message=f'{received} public-source candidate(s); {count} new. Identity not verified.'
            c.execute('INSERT INTO research_queries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
              (core.uid(),case_id,actor['id'],run_id,step.provider,step.query,status,received,count,message,core.iso_now()))
            c.execute('INSERT INTO collection_runs VALUES (?,?,?,?,?,?,?)',
              (core.uid(),case_id,step.provider,status,count,message+' Query: '+step.query[:70],core.iso_now()))
            result.append({'provider':step.provider,'query':step.query,'reason':step.reason,
                           'status':status,'returned':received,'new':count,'message':message})
        c.execute('UPDATE cases SET last_collected=? WHERE id=?',(core.iso_now(),case_id))
        c.execute('INSERT INTO search_history VALUES (?,?,?,?,?,?,?,?,?)',
          (core.uid(),case_id,actor['id'],case['query'],case['subject_type'],
           json.dumps([p.provider for p in steps]),sum(r['new'] for r in result),
           sum(r['status']=='error' for r in result),core.iso_now()))
    core.write_audit(actor['id'],'research','case',case_id,f'{len(steps)} source queries')
    return {'runId':run_id,'queries':result,'attempted':len(result),
            'returned':sum(r['returned'] for r in result),'new':sum(r['new'] for r in result),
            'errors':sum(r['status']=='error' for r in result),
            'note':'Returned is not a verified identity match; new means newly saved records.'}

@router.get('/api/cases/{case_id}/research-history')
def research_history(case_id:str,actor=Depends(core.actor_from_cookie)):
    read_case(case_id,actor)
    with db.connect() as c:
        rows=c.execute('SELECT id,run_id,provider,query_text,status,returned_count,new_count,message,created_at FROM research_queries WHERE case_id=? ORDER BY created_at DESC,id DESC LIMIT 250',(case_id,))
        return {'items':[dict(r) for r in rows]}

class CandidateInput(BaseModel):
    display_name:str=Field(min_length=2,max_length=180)
    reason:str=Field(default='',max_length=1500)
    classification:Literal['unresolved','potential_match']='unresolved'

class CandidateReview(BaseModel):
    reason:str=Field(default='',max_length=1500)
    classification:Literal['unresolved','potential_match','excluded','confirmed_by_analyst']

class CandidateLink(BaseModel):
    evidence_id:str=Field(min_length=1,max_length=70)
    rationale:str=Field(default='',max_length=1200)

@router.get('/api/cases/{case_id}/candidates')
def candidates(case_id:str,actor=Depends(core.actor_from_cookie)):
    read_case(case_id,actor)
    with db.connect() as c:
        profiles=[dict(r) for r in c.execute(
          'SELECT * FROM candidate_profiles WHERE case_id=? ORDER BY updated_at DESC,id',(case_id,))]
        links=[dict(r) for r in c.execute('''SELECT l.profile_id,l.evidence_id,l.rationale,
          e.label,e.provider,e.source_url,e.status FROM candidate_evidence l
          JOIN evidence e ON e.id=l.evidence_id
          JOIN candidate_profiles p ON p.id=l.profile_id
          WHERE p.case_id=? ORDER BY e.provider,e.label''',(case_id,))]
    for p in profiles:p['sources']=[x for x in links if x['profile_id']==p['id']]
    return {'items':profiles,'notice':'Analyst candidate groups are hypotheses, not identity verification.'}

@router.post('/api/cases/{case_id}/candidates',status_code=201)
def new_candidate(case_id:str,body:CandidateInput,actor=Depends(core.protect)):
    read_case(case_id,actor)
    id=core.uid()
    with db.connect() as c:
        c.execute('INSERT INTO candidate_profiles VALUES (?,?,?,?,?,?,?,?)',
          (id,case_id,body.display_name.strip(),body.reason.strip(),body.classification,
           actor['id'],core.iso_now(),core.iso_now()))
    core.write_audit(actor['id'],'candidate_create','case',case_id)
    return {'id':id}

@router.patch('/api/cases/{case_id}/candidates/{candidate_id}')
def review_candidate(case_id:str,candidate_id:str,body:CandidateReview,actor=Depends(core.protect)):
    read_case(case_id,actor)
    if body.classification in ('excluded','confirmed_by_analyst') and len(body.reason.strip())<20:
        raise HTTPException(422,'Record a specific evidence-based rationale of at least 20 characters.')
    if body.classification=='confirmed_by_analyst':
        with db.connect() as check:
            providers=check.execute('SELECT count(DISTINCT e.provider) n FROM candidate_evidence l JOIN evidence e ON e.id=l.evidence_id WHERE l.profile_id=? AND e.case_id=? AND e.status=?',
                 (candidate_id,case_id,'corroborated')).fetchone()['n']
        if providers<2:
            raise HTTPException(422,'Analyst identity confirmation requires two separately sourced corroborated records. This remains an analyst classification, not official verification.')
    with db.connect() as c:
        count=c.execute('UPDATE candidate_profiles SET classification=?,reason=?,updated_at=? WHERE case_id=? AND id=?',
          (body.classification,body.reason.strip(),core.iso_now(),case_id,candidate_id)).rowcount
        if not count:raise HTTPException(404,'Candidate not found')
    core.write_audit(actor['id'],'candidate_review','candidate',candidate_id,body.classification)
    return {'ok':True}

@router.post('/api/cases/{case_id}/candidates/{candidate_id}/sources',status_code=201)
def link_candidate(case_id:str,candidate_id:str,body:CandidateLink,actor=Depends(core.protect)):
    read_case(case_id,actor)
    with db.connect() as c:
        if not c.execute('SELECT id FROM candidate_profiles WHERE id=? AND case_id=?',(candidate_id,case_id)).fetchone():
            raise HTTPException(404,'Candidate not found')
        if not c.execute('SELECT id FROM evidence WHERE id=? AND case_id=?',(body.evidence_id,case_id)).fetchone():
            raise HTTPException(422,'Evidence must belong to the same case')
        c.execute('INSERT OR IGNORE INTO candidate_evidence VALUES (?,?,?)',
          (candidate_id,body.evidence_id,body.rationale.strip()))
    core.write_audit(actor['id'],'candidate_source','candidate',candidate_id,body.evidence_id)
    return {'ok':True}

class AssessmentInput(BaseModel):
    executive_summary:str=Field(default='',max_length=2400)
    assessment:str=Field(default='',max_length=5000)
    limitations:str=Field(default='',max_length=2000)
    next_actions:str=Field(default='',max_length=2000)
    status:Literal['open','researching','awaiting_review','completed']='open'

@router.get('/api/cases/{case_id}/assessment')
def assessment(case_id:str,actor=Depends(core.actor_from_cookie)):
    read_case(case_id,actor)
    with db.connect() as c:
        row=c.execute('SELECT * FROM case_assessments WHERE case_id=?',(case_id,)).fetchone()
    return dict(row) if row else {'case_id':case_id,'executive_summary':'','assessment':'',
        'limitations':'','next_actions':'','status':'open'}

@router.put('/api/cases/{case_id}/assessment')
def save_assessment(case_id:str,body:AssessmentInput,actor=Depends(core.protect)):
    read_case(case_id,actor)
    if body.status=='completed':
        if len(body.executive_summary.strip())<40 or len(body.assessment.strip())<40 or len(body.limitations.strip())<30:
            raise HTTPException(422,'Completion requires substantive findings and explicit limitations.')
        with db.connect() as check:
            claims=check.execute('SELECT count(*) n FROM claim_links WHERE case_id=?',(case_id,)).fetchone()['n']
            queries=check.execute('SELECT count(*) n FROM research_queries WHERE case_id=?',(case_id,)).fetchone()['n']
        if not claims and not queries:
            raise HTTPException(422,'Completion requires a linked source claim or a documented executed research query.')
    with db.connect() as c:
        c.execute('DELETE FROM case_assessments WHERE case_id=?',(case_id,))
        c.execute('INSERT INTO case_assessments VALUES (?,?,?,?,?,?,?,?)',
          (case_id,body.executive_summary.strip(),body.assessment.strip(),
           body.limitations.strip(),body.next_actions.strip(),body.status,
           actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'assessment_update','case',case_id,body.status)
    return {'ok':True,'status':body.status}

class BulkReview(BaseModel):
    evidence_ids:list[str]=Field(min_length=1,max_length=70)
    status:Literal['candidate','corroborated','disputed','rejected']
    notes:str=Field(min_length=12,max_length=1200)

@router.post('/api/cases/{case_id}/evidence/bulk-review')
def bulk_review(case_id:str,body:BulkReview,actor=Depends(core.protect)):
    read_case(case_id,actor)
    if body.status=='corroborated' and len(body.notes.strip())<20:
        raise HTTPException(422,'Corroboration requires a specific analyst rationale of at least 20 characters.')
    ids=list(dict.fromkeys(body.evidence_ids))
    with db.connect() as c:
        count=c.execute('SELECT count(*) n FROM evidence WHERE case_id=? AND id IN ('+
            ','.join('?'*len(ids))+')',(case_id,*ids)).fetchone()['n']
        if count!=len(ids):raise HTTPException(422,'Some evidence IDs do not belong to this case.')
        for item in ids:
            old=c.execute('SELECT status FROM evidence WHERE id=?',(item,)).fetchone()
            c.execute('UPDATE evidence SET status=?,reviewer_notes=?,reviewed_at=?,reviewed_by=? WHERE id=?',
              (body.status,body.notes,core.iso_now(),actor['id'],item))
            c.execute('INSERT INTO review_decisions VALUES (?,?,?,?,?,?,?,?)',
              (core.uid(),case_id,item,actor['id'],old['status'],body.status,body.notes.strip(),core.iso_now()))
    core.write_audit(actor['id'],'evidence_bulk_review','case',case_id,f'{len(ids)}: {body.status}')
    return {'ok':True,'updated':len(ids)}

@router.get('/api/cases/{case_id}/intelligence')
def intelligence(case_id:str,actor=Depends(core.actor_from_cookie)):
    case=read_case(case_id,actor)
    with db.connect() as c:
        ev=[dict(r) for r in c.execute(
            'SELECT id,label,summary,provider,status,source_url,reviewer_notes,fetched_at FROM evidence WHERE case_id=?',(case_id,))]
        claims=[dict(r) for r in c.execute('''SELECT l.claim_text,l.stance,l.created_at,e.id evidence_id,e.label,
          e.source_url,e.provider,e.status FROM claim_links l JOIN evidence e ON e.id=l.evidence_id
          WHERE l.case_id=? ORDER BY l.created_at DESC LIMIT 250''',(case_id,))]
        history=[dict(r) for r in c.execute('SELECT provider,query_text,status,returned_count,new_count,message,created_at FROM research_queries WHERE case_id=? ORDER BY created_at DESC LIMIT 100',(case_id,))]
        snapshots=[dict(r) for r in c.execute('''SELECT e.label,c.source_url,c.content_sha256,
            c.fetched_at,c.extracted_text FROM source_captures c JOIN evidence e ON e.id=c.evidence_id
            WHERE c.case_id=? ORDER BY c.fetched_at DESC LIMIT 50''',(case_id,))]
        reviews=[dict(r) for r in c.execute('''SELECT e.label,d.old_status,d.new_status,d.rationale,d.created_at
            FROM review_decisions d LEFT JOIN evidence e ON e.id=d.evidence_id
            WHERE d.case_id=? ORDER BY d.created_at DESC LIMIT 100''',(case_id,))]
    assessment_data=assessment(case_id,actor)
    candidates_data=candidates(case_id,actor)
    context=get_context(case_id)
    return {'case':case,'context':context,'assessment':assessment_data,
      'evidence':ev,'claims':claims,'candidates':candidates_data['items'],
      'researchQueries':history,'sourceCaptures':snapshots,'reviewHistory':reviews,
      'metrics':{'records':len(ev),'reviewed':sum(e['status']!='candidate' for e in ev),
                 'corroborated':sum(e['status']=='corroborated' for e in ev),
                 'excludedCandidates':sum(p['classification']=='excluded' for p in candidates_data['items']),
                 'failedQueries':sum(q['status']=='error' for q in history)},
      'caveat':'These are public-source leads and human findings; do not infer verified identity from a matching name.'}

def render_report(info):
    esc=lambda v:html.escape(str(v or ''),quote=True)
    case=info['case'];ass=info['assessment'];ctx=info['context'];metrics=info['metrics']
    def para(value,empty='Not yet assessed'):
        return '<p>'+esc(value or empty).replace('\n','<br>')+'</p>'
    sections=['''<!doctype html><html lang="en"><head><meta charset="utf-8">
    <title>OSINT Alpha — Research assessment</title><style>
    body{font:14px/1.65 Arial,sans-serif;color:#162238;margin:42px auto;max-width:1050px;padding:0 26px}
    h1{font-size:27px;margin-bottom:3px}h2{font-size:17px;margin-top:27px;border-bottom:1px solid #dbe3ee;padding-bottom:6px}
    h3{font-size:14px;margin:14px 0 3px}table{width:100%;border-collapse:collapse}
    th,td{border-bottom:1px solid #e4e9f1;padding:9px 6px;vertical-align:top;text-align:left;overflow-wrap:anywhere}
    th{background:#f4f7fb}.meta{color:#55637a;font-size:12px}.warning{border-left:4px solid #dc9b54;padding:12px;background:#fff7ed}
    a{color:#1656a7}@page{size:A4;margin:15mm}
    </style></head><body>''',
    '<div class="meta">OSINT ALPHA / CASE ASSESSMENT / '+esc(core.iso_now())+'</div>',
    '<h1>'+esc(case['title'])+'</h1>',
    '<p class="meta">Subject: '+esc(case['query'])+' · Type: '+esc(case['subject_type'])+
      ' · Status: '+esc(ass['status'])+'</p>',
    '<p class="warning">Candidate names, user-generated content and source claims are not independent identity verification. Analyst decisions are identified as such.</p>',
    '<h2>Research objective and subject clues</h2>',para(case['purpose']),
    '<p><strong>Context:</strong> '+esc('; '.join(k+': '+v for k,v in ctx.items() if v) or 'Not supplied')+'</p>',
    '<h2>Executive summary</h2>',para(ass['executive_summary']),
    '<h2>Assessment and limitations</h2>',para(ass['assessment']),
    '<h3>Uncertainty and scope limits</h3>',para(ass['limitations']),
    '<h3>Recommended next actions</h3>',para(ass['next_actions']),
    '<h2>Analyst candidate profiles ('+str(len(info['candidates']))+')</h2>']
    for p in info['candidates']:
        sections.append('<h3>'+esc(p['display_name'])+' — '+esc(p['classification'])+'</h3>'+
                        para(p['reason'],'No analyst rationale recorded'))
        for src in p['sources']:
            sections.append('<p class="meta">Linked candidate record: <a href="'+esc(core.safe_href(src['source_url']))+'">'+
                            esc(src['label'])+'</a> ('+esc(src['provider'])+')</p>')
    sections.append('<h2>Source-linked claims ('+str(len(info['claims']))+')</h2>')
    sections.append('<table><tr><th>Claim</th><th>Stance</th><th>Attributed source</th></tr>')
    for c in info['claims']:
        sections.append('<tr><td>'+esc(c['claim_text'])+'</td><td>'+esc(c['stance'])+'</td><td><a href="'+
          esc(core.safe_href(c['source_url']))+'">'+esc(c['label'])+'</a> · '+esc(c['status'])+'</td></tr>')
    sections.append('</table><h2>Source-text captures ('+str(len(info.get('sourceCaptures',[])))+')</h2>')
    sections.append('<p class="meta">Source captures preserve selected extracted text, not a forensic copy or proof that claims are true.</p>')
    for capture in info.get('sourceCaptures',[])[:30]:
        sections.append('<h3>'+esc(capture['label'])+'</h3><p class="meta">Retrieved '+
            esc(capture['fetched_at'])+' · SHA-256 '+esc(capture['content_sha256'])+'</p>'+
            '<p>'+esc(capture['extracted_text'][:550])+'</p>')
    sections.append('<h2>Analyst review decisions ('+str(len(info.get('reviewHistory',[])))+')</h2>')
    sections.append('<table><tr><th>Record</th><th>Change</th><th>Reason</th><th>Date</th></tr>')
    for d in info.get('reviewHistory',[])[:100]:
        sections.append('<tr><td>'+esc(d['label'])+'</td><td>'+esc(d['old_status'])+' → '+
            esc(d['new_status'])+'</td><td>'+esc(d['rationale'])+'</td><td>'+esc(d['created_at'])+'</td></tr>')
    sections.append('</table><h2>Collected records ('+str(metrics['records'])+')</h2>')
    sections.append('<table><tr><th>Source</th><th>Record</th><th>Status</th><th>Analyst notes</th></tr>')
    for e in info['evidence'][:250]:
        sections.append('<tr><td>'+esc(e['provider'])+'</td><td><a href="'+
          esc(core.safe_href(e['source_url']))+'">'+esc(e['label'])+'</a><br><span class="meta">'+
          esc(e['summary'])+'</span></td><td>'+esc(e['status'])+'</td><td>'+
          esc(e['reviewer_notes'])+'</td></tr>')
    sections.append('</table><h2>Collection coverage ('+str(len(info['researchQueries']))+' logged requests)</h2>')
    sections.append('<table><tr><th>Provider</th><th>Query</th><th>Outcome</th></tr>')
    for r in info['researchQueries'][:100]:
        sections.append('<tr><td>'+esc(r['provider'])+'</td><td>'+esc(r['query_text'])+
                        '</td><td>'+esc(r['status'])+' / '+str(r['returned_count'])+' returned</td></tr>')
    sections.append('</table><p class="meta">This document contains analyst-provided assessments. Sources may change. No independent forensic archive or chain-of-custody guarantee.</p></body></html>')
    return ''.join(sections)

@router.get('/api/cases/{case_id}/report-v4.html',response_class=HTMLResponse)
def report(case_id:str,actor=Depends(core.actor_from_cookie)):
    info=intelligence(case_id,actor)
    core.write_audit(actor['id'],'export_v4','case',case_id,'HTML')
    return HTMLResponse(render_report(info),headers={'Cache-Control':'no-store',
         'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"})

@router.get('/api/cases/{case_id}/report-v4.pdf')
def pdf(case_id:str,actor=Depends(core.actor_from_cookie)):
    info=intelligence(case_id,actor)
    try:
        from weasyprint import HTML
        result=HTML(string=render_report(info)).write_pdf()
    except (ImportError,OSError) as exc:
        raise HTTPException(503,'PDF renderer unavailable; use HTML.') from exc
    core.write_audit(actor['id'],'export_v4','case',case_id,'PDF')
    return ApiResponse(result,media_type='application/pdf',headers={'Cache-Control':'no-store',
        'Content-Disposition':'attachment; filename="osintalpha-assessment.pdf"'})
