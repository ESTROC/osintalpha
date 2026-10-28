"""Case-scoped immutable answer comparisons and stable keyset source paging.

Output distinguishes a missing retrieval result from a withdrawn public fact.
"""
from __future__ import annotations
import base64,hashlib,hmac,json,os,re,difflib
from fastapi import APIRouter,Depends,HTTPException,Query
from . import db,main as core
from .report_continuity import snapshot_metadata
from .lineage import observations,run_ids
router=APIRouter()

def _token(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    key=os.environ.get('OSINTALPHA_ADMIN_PASSWORD','').encode()
    digest=hmac.new(key,raw,hashlib.sha256).hexdigest()[:32]
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')+'.'+digest

def _parse(token,case_id,status,query):
    if len(token)>1000 or '.' not in token:raise HTTPException(422,'Invalid source page cursor.')
    part,digest=token.rsplit('.',1)
    try:
        raw=base64.urlsafe_b64decode(part+'='*(-len(part)%4))
        obj=json.loads(raw)
    except (ValueError,TypeError,UnicodeDecodeError) as exc:
        raise HTTPException(422,'Invalid source page cursor.') from exc
    key=os.environ.get('OSINTALPHA_ADMIN_PASSWORD','').encode()
    if not hmac.compare_digest(hmac.new(key,raw,hashlib.sha256).hexdigest()[:32],digest):
        raise HTTPException(422,'Source page cursor integrity error.')
    if (obj.get('version'),obj.get('case'),obj.get('status'),obj.get('query'))!=(1,case_id,status,query):
        raise HTTPException(422,'Source cursor belongs to a different case or filter.')
    if not isinstance(obj.get('time'),str) or not re.fullmatch(r'[a-zA-Z0-9-]{20,80}',str(obj.get('id',''))):
        raise HTTPException(422,'Source cursor is malformed.')
    return obj

@router.get('/api/cases/{case_id}/evidence-cursor')
def evidence_cursor(case_id:str,limit:int=Query(50,ge=1,le=100),
    cursor:str='',status:str='all',query:str='',actor=Depends(core.actor_from_cookie)):
    if status not in ('all','candidate','corroborated','disputed','rejected'):
        raise HTTPException(422,'Unsupported review-state filter.')
    search=' '.join(query.strip().casefold().split())
    if len(search)>90 or (search and not re.fullmatch(r'[a-z0-9 -]+',search)):
        raise HTTPException(422,'Only plain-text searchable terms are allowed.')
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        sql='SELECT id,provider,label,summary,source_url,fetched_at,observed_at,status,reviewer_notes FROM evidence WHERE case_id=?'
        args=[case_id]
        if status!='all':sql+=' AND status=?';args.append(status)
        if search:
            sql+=' AND (lower(label) LIKE ? OR lower(summary) LIKE ?)'
            args.extend(['%'+search+'%']*2)
        if cursor:
            token=_parse(cursor,case_id,status,search)
            sql+=' AND (fetched_at<? OR (fetched_at=? AND id<?))'
            args.extend([token['time'],token['time'],token['id']])
        sql+=' ORDER BY fetched_at DESC,id DESC LIMIT ?'
        rows=[dict(x) for x in conn.execute(sql,args+[limit+1])]
    more=len(rows)>limit
    result=rows[:limit]
    next_cursor=_token({'version':1,'case':case_id,'status':status,'query':search,
           'time':result[-1]['fetched_at'],'id':result[-1]['id']}) if more and result else None
    return {'items':result,'nextCursor':next_cursor,'hasMore':more,'order':'fetched_at_DESC,id_DESC',
       'identityVerified':False,'stableWithinUnchangedSourceVersions':True,
       'warning':'Keyset pages avoid offset drift from new records; changing existing records can still reorder results.'}

def _snapshot(conn,case_id,message_id):
    item=snapshot_metadata(conn,case_id,message_id)
    if not item.get('available') or not item.get('integrityOk'):
        raise HTTPException(409,'Both messages require intact contemporaneous answer provenance.')
    return item

@router.get('/api/cases/{case_id}/answer-snapshot-diff')
def compare_answer_snapshots(case_id:str,left_message:str,right_message:str,
                             actor=Depends(core.actor_from_cookie)):
    if left_message==right_message:raise HTTPException(422,'Use two different saved answer IDs.')
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        messages={}
        for mid in (left_message,right_message):
            row=conn.execute(
              'SELECT m.id,m.session_id,s.owner_id FROM research_messages m '
              'JOIN research_sessions s ON m.session_id=s.id '
              'WHERE m.id=? AND s.case_id=? AND m.role=?',(mid,case_id,'assistant')).fetchone()
            if not row or (row['owner_id']!=actor['id'] and actor['role']!='admin'):
                raise HTTPException(404,'Answer outside accessible conversation.')
            messages[mid]=_snapshot(conn,case_id,mid)
    old,new=messages[left_message],messages[right_message]
    old_ev={x['id']:x for x in old.get('evidence',[]) if x.get('id')}
    new_ev={x['id']:x for x in new.get('evidence',[]) if x.get('id')}
    added=sorted(new_ev.keys()-old_ev.keys());removed=sorted(old_ev.keys()-new_ev.keys())
    changed=sorted(x for x in old_ev.keys()&new_ev.keys()
                   if old_ev[x].get('sha256')!=new_ev[x].get('sha256'))
    txt=list(difflib.unified_diff((old.get('answer') or '').splitlines(),
        (new.get('answer') or '').splitlines(),fromfile=left_message,
        tofile=right_message,lineterm=''))[:160]
    return {'older':{'messageId':left_message,'savedAt':old.get('createdAt'),
                       'snapshotSha256':old.get('snapshotSha256')},
       'newer':{'messageId':right_message,'savedAt':new.get('createdAt'),
                       'snapshotSha256':new.get('snapshotSha256')},
       'citedSourceChanges':{'newInAnswer':added,'noLongerCited':removed,'storedSourceHashChanged':changed},
       'answerTextDiff':txt,'meaningVerified':False,'retractedFacts':[],
       'warning':'A source disappearing from an answer is NOT proof the source was deleted or a factual claim retracted. Text diffs are not factual adjudication.'}

@router.get('/api/cases/{case_id}/run-source-evolution')
def run_source_evolution(case_id:str,older_run:str,newer_run:str,
       actor=Depends(core.actor_from_cookie)):
    if older_run==newer_run:raise HTTPException(422,'Distinct source research runs required.')
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        ids={x['run_id'] for x in run_ids(conn,case_id)}
        if older_run not in ids or newer_run not in ids:
            raise HTTPException(404,'Recorded research run not found for this case.')
        older,newer=observations(conn,case_id,older_run),observations(conn,case_id,newer_run)
    items=[]
    for eid in sorted(set(older)|set(newer)):
        a,b=older.get(eid),newer.get(eid)
        typ=('new_in_run' if not a else
            'not_returned_this_run' if not b else
            'source_content_changed' if a['content_sha256']!=b['content_sha256'] else 'unchanged')
        items.append({'evidenceId':eid,'status':typ,'olderCapturedAt':a['captured_at'] if a else None,
             'newerCapturedAt':b['captured_at'] if b else None,
             'olderHash':a['content_sha256'] if a else None,
             'newerHash':b['content_sha256'] if b else None,
             'sourceUrl':(b or a)['source_url']})
    changed_ids={x['evidenceId'] for x in items
        if x['status'] in ('source_content_changed','not_returned_this_run')}
    claim_rechecks=[]
    if changed_ids:
        with db.connect() as conn:
            for x in conn.execute(
                'SELECT id,evidence_id,claim_text,stance FROM claim_links WHERE case_id=?',
                (case_id,)):
                if x['evidence_id'] in changed_ids:
                    claim_rechecks.append({'claimId':x['id'],'evidenceId':x['evidence_id'],
                        'claimText':x['claim_text'][:240],
                        'status':'needs_revalidation_due_to_source_change_or_coverage',
                        'factRetracted':False})
    return {'claimRechecks':claim_rechecks[:100],
        'olderRun':older_run,'newerRun':newer_run,'items':items[:500],
       'truncated':len(items)>500,'withdrawnFactsVerified':False,
       'notice':'No longer returned in a finite query != withdrawn or deleted. Source changes require independent review.'}
