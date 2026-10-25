"""Versioned public-source observations and honest run-to-run change comparison.

A search API omitting a record does NOT mean it was deleted from the web.
The observation log preserves what THIS collector actually returned.
"""
from __future__ import annotations
import hashlib
import json
from collections import Counter
from fastapi import APIRouter,Depends,HTTPException,Query
from . import db
from . import main as core

router=APIRouter()

def canonical_data(raw):
    if isinstance(raw,str):
        try: value=json.loads(raw)
        except (TypeError,ValueError):value={'source_text':raw}
    else:value=raw
    # The query is a property of the search, not the underlying source.
    if isinstance(value,dict):
        value={key:val for key,val in value.items() if key not in ('query','search_query','fetched_at')}
    packed=json.dumps(value,sort_keys=True,ensure_ascii=False,default=str)
    return packed,hashlib.sha256(packed.encode('utf-8')).hexdigest()

def save_observation(conn,*,case_id,run_id,query,provider,source_ref,label,summary,url,raw,actor_id,observed_at=None):
    """Atomic insert/version/update; reset stale analyst verdicts when a source changes."""
    packed,digest=canonical_data(raw)
    source_ref=(str(source_ref or digest))[:500]
    existing=conn.execute('SELECT * FROM evidence WHERE case_id=? AND provider=? AND source_ref=?',
                          (case_id,provider,source_ref)).fetchone()
    now=core.iso_now()
    if existing:
        eid=existing['id']
        oldraw,olddigest=canonical_data(existing['raw_json'])
        disposition='unchanged' if olddigest==digest else 'changed'
        if disposition=='changed':
            # Backfill the original state for historical cases that predate this feature.
            captured=conn.execute('SELECT count(*) n FROM source_observations WHERE evidence_id=?',
                                  (eid,)).fetchone()['n']
            if not captured:
                conn.execute('''INSERT INTO source_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                   (core.uid(),case_id,eid,'legacy-'+eid,'previous stored record',provider,
                    source_ref,olddigest,existing['label'],existing['summary'],existing['source_url'],
                    oldraw,'historical',existing['fetched_at']))
            conn.execute('''UPDATE evidence SET label=?,summary=?,source_url=?,fetched_at=?,
                observed_at=COALESCE(?,observed_at),sha256=?,raw_json=?,status='candidate',
                reviewed_at=NULL,reviewed_by=NULL WHERE id=?''',
                (label,summary,url,now,observed_at,digest,packed,eid))
            if existing['status']!='candidate':
                conn.execute('INSERT INTO review_decisions VALUES (?,?,?,?,?,?,?,?)',
                    (core.uid(),case_id,eid,actor_id,existing['status'],'candidate',
                     'Previously reviewed source content changed; re-review required.',now))
            affected=conn.execute('''SELECT p.id,p.classification,p.reason FROM candidate_profiles p
                JOIN candidate_evidence ce ON ce.profile_id=p.id
                WHERE ce.evidence_id=? AND p.classification='confirmed_by_analyst' ''',(eid,))
            for group in affected:
                conn.execute('''UPDATE candidate_profiles SET classification='potential_match',
                    reason=?,updated_at=? WHERE id=?''',
                    ((group['reason'] or '')[:900]+' [Source changed; analyst re-verification required.]',
                     now,group['id']))
    else:
        eid=core.uid()
        conn.execute('''INSERT INTO evidence
            (id,case_id,provider,label,summary,source_url,source_ref,fetched_at,observed_at,
             sha256,raw_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (eid,case_id,provider,label,summary,url,source_ref,now,observed_at,digest,packed))
        disposition='new'
    conn.execute('''INSERT INTO source_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (core.uid(),case_id,eid,run_id,query,provider,source_ref,digest,
         label,summary,url,packed,disposition,now))
    return disposition

def run_ids(conn,case_id):
    rows=conn.execute('''SELECT run_id,MIN(created_at) started_at,
       count(*) query_count, SUM(returned_count) returned_count
       FROM research_queries WHERE case_id=? GROUP BY run_id ORDER BY started_at DESC,run_id DESC LIMIT 30''',
       (case_id,))
    return [dict(x) for x in rows]

def observations(conn,case_id,run_id):
    return {x['evidence_id']:dict(x) for x in conn.execute(
        '''SELECT evidence_id,source_ref,provider,content_sha256,label,summary,source_url,disposition,captured_at
           FROM source_observations WHERE case_id=? AND run_id=? ORDER BY captured_at,id''',
           (case_id,run_id))}

@router.get('/api/cases/{case_id}/changes')
def compare_case_runs(case_id:str,run_id:str='',against:str='',actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        runs=run_ids(conn,case_id)
        ids={r['run_id'] for r in runs}
        if run_id and run_id not in ids:raise HTTPException(404,'Research run not found')
        current=run_id or (runs[0]['run_id'] if runs else '')
        if against and against not in ids:raise HTTPException(404,'Comparison run not found')
        older=against or next((r['run_id'] for r in runs if r['run_id']!=current),'')
        current_items=observations(conn,case_id,current) if current else {}
        older_items=observations(conn,case_id,older) if older else {}
        queries={rid:[dict(x) for x in conn.execute(
            'SELECT provider,query_text,status FROM research_queries WHERE case_id=? AND run_id=?',
            (case_id,rid))] for rid in (current,older) if rid}
    items=[]
    for eid,value in current_items.items():
        previous=older_items.get(eid)
        if previous:
            change='changed' if previous['content_sha256']!=value['content_sha256'] else 'unchanged'
        else:change='new_to_comparison'
        items.append({'evidenceId':eid,'change':change,'provider':value['provider'],
                      'label':value['label'],'url':value['source_url'],
                      'previousLabel':previous['label'] if previous else '',
                      'previousSummary':previous['summary'] if previous else '',
                      'summary':value['summary'],'sourceHash':value['content_sha256']})
    for eid,value in older_items.items():
        if eid not in current_items:
            items.append({'evidenceId':eid,'change':'not_returned','provider':value['provider'],
                          'label':value['label'],'url':value['source_url'],
                          'previousLabel':value['label'],'previousSummary':value['summary'],
                          'summary':'','sourceHash':''})
    order={'changed':0,'new_to_comparison':1,'not_returned':2,'unchanged':3}
    items.sort(key=lambda x:(order.get(x['change'],4),x['provider'],x['label'],x['evidenceId']))
    coverage={rid:{(q['provider'],q['query_text']) for q in qs} for rid,qs in queries.items()}
    matching_queries=bool(current and older and coverage.get(current)==coverage.get(older))
    return {'runs':runs,'currentRunId':current,'previousRunId':older,
            'comparedSameQueryScope':matching_queries,
            'summary':dict(Counter(x['change'] for x in items)),
            'items':items[:500],
            'totalCompared':len(items),
            'warning':('Only records returned by the selected source queries are compared. '
             'Not returned does NOT establish deletion or disappearance from the internet. '
             'Query or provider scope differs.' if current and older and not matching_queries else
             'Not returned does NOT establish deletion or disappearance from the internet.')}

@router.get('/api/cases/{case_id}/evidence/{evidence_id}/versions')
def versions(case_id:str,evidence_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        row=conn.execute('SELECT id FROM evidence WHERE id=? AND case_id=?',(evidence_id,case_id)).fetchone()
        if not row:raise HTTPException(404,'Source record not found')
        entries=[dict(r) for r in conn.execute('''SELECT id,run_id,query_text,provider,
               content_sha256,label,summary,source_url,disposition,captured_at FROM source_observations
               WHERE case_id=? AND evidence_id=? ORDER BY captured_at DESC,id DESC LIMIT 100''',
               (case_id,evidence_id))]
    return {'items':entries,'sourceId':evidence_id,
      'note':'These are API-record versions, not archived source webpages. Changes require fresh review.'}
