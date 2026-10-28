"""Measured review timeliness, without unsupported accuracy/productivity scores."""
from __future__ import annotations
from datetime import datetime,timezone
from statistics import median
from urllib.parse import urlsplit
import json,re
from fastapi import APIRouter,Depends
from . import db,main as core
router=APIRouter()

def seconds(earlier,later):
    try:
        a=datetime.fromisoformat(earlier.replace('Z','+00:00'))
        b=datetime.fromisoformat(later.replace('Z','+00:00'))
        if a.tzinfo is None:a=a.replace(tzinfo=timezone.utc)
        if b.tzinfo is None:b=b.replace(tzinfo=timezone.utc)
        return max(0,round((b-a).total_seconds()))
    except (ValueError,AttributeError,TypeError):return None

def source_origin(src):
    """Only explicit declared original/DOI or identical URL can imply a shared origin."""
    url=src['source_url']
    try:raw=json.loads(src.get('raw_json') or '{}')
    except (ValueError,TypeError):raw={}
    if not isinstance(raw,dict):raw={}
    doi=str(raw.get('DOI') or raw.get('doi') or '').strip().casefold()
    if re.fullmatch(r'10\.[0-9]{4,9}/[^\s]{1,180}',doi):
        return 'doi:'+doi,'publisher_declared_doi_unverified'
    declared=raw.get('original_url') or raw.get('canonical_url')
    if isinstance(declared,str):
        try:
            p=urlsplit(declared)
            if p.scheme=='https' and p.hostname and not p.username and not p.password and len(declared)<600:
                return 'published:'+declared.split('#')[0],'publisher_declared_canonical_unverified'
        except ValueError:pass
    return 'exact:'+url.split('#')[0],'same_exact_original_url_only'

@router.get('/api/cases/{case_id}/source-origin-review')
def origin_review(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=[dict(x) for x in conn.execute(
          'SELECT id,provider,source_url,status,raw_json FROM evidence '
          'WHERE case_id=? ORDER BY fetched_at DESC,id DESC LIMIT 1500',(case_id,))]
    by_key={}
    for x in rows:
        key,reason=source_origin(x)
        group=by_key.setdefault(key,{'originKeySha256':None,'sourceCount':0,
             'evidenceIds':[],'providers':set(),'reviewedCount':0,'classification':reason})
        group['sourceCount']+=1;group['evidenceIds'].append(x['id'])
        group['providers'].add(x['provider'])
        if x['status']=='corroborated':group['reviewedCount']+=1
    import hashlib
    result=[]
    for key,val in by_key.items():
        if val['sourceCount']>1:
            val['originKeySha256']=hashlib.sha256(key.encode()).hexdigest()
            val['providers']=sorted(val['providers'])
            val['evidenceIds']=val['evidenceIds'][:30]
            result.append(val)
    return {'duplicateOriginGroups':result[:60],
        'totalSourceRecordsInspected':len(rows),'distinctOriginKeys':len(by_key),
        'independentSourceCountCertified':None,'coverageComplete':len(rows)<1500,
        'warning':'Same exact/canonical URL or DOI counts as one candidate origin, not independent corroboration. Publisher-declared canonical links are unverified; different URLs may still syndicate text.'}

@router.get('/api/agency/review-timeliness')
def review_timeliness(actor=Depends(core.actor_from_cookie)):
    now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    with db.connect() as conn:
        if actor['role']=='admin':
            cases=[dict(x) for x in conn.execute('SELECT id,created_at FROM cases ORDER BY created_at DESC LIMIT 200')]
        else:
            cases=[dict(x) for x in conn.execute(
                'SELECT DISTINCT c.id,c.created_at FROM cases c LEFT JOIN case_members m ON m.case_id=c.id '
                'WHERE c.created_by=? OR m.user_id=? ORDER BY c.created_at DESC LIMIT 200',
                (actor['id'],actor['id']))]
        times=[];queue_ages=[];errors=0;tasks=0;measured=0
        for case in cases:
            first=conn.execute(
              "SELECT MIN(e.reviewed_at) started FROM evidence e WHERE e.case_id=? "
              "AND e.status='corroborated' AND e.reviewed_at IS NOT NULL "
              "AND EXISTS(SELECT 1 FROM source_feedback f WHERE f.evidence_id=e.id AND f.case_id=e.case_id AND f.relevance='useful')",
              (case['id'],)).fetchone()['started']
            diff=seconds(case['created_at'],first) if first else None
            if diff is not None:times.append(diff)
            tasks_rows=conn.execute(
              "SELECT created_at FROM investigation_tasks WHERE case_id=? "
              "AND status IN ('todo','in_progress','blocked','awaiting_review')",(case['id'],))
            for t in tasks_rows:
                age=seconds(t['created_at'],now)
                if age is not None:queue_ages.append(age)
            errors+=conn.execute(
              "SELECT count(*) n FROM research_queries WHERE case_id=? AND status IN ('error','blocked','unavailable')",
              (case['id'],)).fetchone()['n']
        tasks=len(queue_ages)
    return {'casesInspected':len(cases),'casesWithUsefulCorroboratedReview':len(times),
       'firstUsefulReviewSecondsMedian':round(median(times)) if times else None,
       'oldestOutstandingTaskSeconds':max(queue_ages) if queue_ages else None,
       'medianOutstandingTaskAgeSeconds':round(median(queue_ages)) if queue_ages else None,
       'openTasksWithKnownCreatedAt':tasks,'observedProviderFailures':errors,
       'targetSlaSeconds':None,'slaCompliant':None,'analystAccuracyMeasured':False,
       'warning':'Only analyst-rated useful AND corroborated sources count. Review timestamps are not source truth; no SLA target or independent investigation quality score exists.'}
