"""Explainable source recency/utility and syndication cautions.

These diagnostic weights are NOT calibrated truth probabilities, legal source
authenticity, or proof of independent publisher ownership.
"""
from __future__ import annotations
import json,re
from collections import Counter
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends
from . import db,main as core
from .search_policy import publisher_group
router=APIRouter()
TTL_DAYS={'gdelt':3,'brave_web':7,'brave_llm_context':7,
    'github':30,'stackoverflow':30,'wikidata':90,'wikipedia':60,
    'crossref':180,'openalex':180,'gleif':30,'analyst':14}
RUBRIC={'captured_original':2,'analyst_publisher_review':1,
    'original_url_present':1,'source_recent':1,'analyst_reviewed':1}

def parse_utc(raw):
    try:
        if not raw:return None
        dt=datetime.fromisoformat(str(raw).replace('Z','+00:00'))
        return dt.replace(tzinfo=timezone.utc) if not dt.tzinfo else dt.astimezone(timezone.utc)
    except (ValueError,TypeError):return None

def expiration(provider,retrieved_at,now=None):
    now=now or datetime.now(timezone.utc)
    retrieved=parse_utc(retrieved_at)
    days=TTL_DAYS.get(str(provider),14)
    if retrieved is None:
        return {'ttlDays':days,'stale':None,'expiresAt':None,
                'reason':'retrieval_time_missing_or_invalid'}
    expiry=retrieved+timedelta(days=days)
    return {'ttlDays':days,'stale':now>expiry,
            'expiresAt':expiry.isoformat(timespec='seconds'),
            'reason':'heuristic_provider_recheck_due' if now>expiry else 'recently_retrieved_not_current_fact'}

def source_rubric(record,attribution=None,has_capture=False,now=None):
    attr=attribution or {}
    url=str(record.get('source_url') or '')
    recent=expiration(record.get('provider'),record.get('fetched_at'),now)
    reasons=[]
    score=0
    if url.startswith('https://') and urlsplit(url).hostname:
        score+=1;reasons.append('original_public_https_reference')
    if has_capture:
        score+=2;reasons.append('stored_source_text_capture_not_original_authentication')
    if attr.get('publisher_authentication') in {'publisher_website_checked','publisher_record_checked'}:
        score+=1;reasons.append('analyst_reports_publisher_checked_not_independently_validated')
    if recent['stale'] is False:
        score+=1;reasons.append('recent_retrieval_not_current_source_claim')
    if record.get('status') in ('corroborated','disputed','rejected'):
        score+=1;reasons.append('analyst_disposition_recorded_not_fact_verified')
    if record.get('status')=='rejected':
        score=0;reasons.append('rejected_by_analyst')
    return {'rubricPoints':score,'rubricMaximum':6,'dimensions':reasons,
            'scoreIsProbability':False,'sourceTruthVerified':False,
            'identityVerified':False,'retrievalPolicy':recent,
            'publisherGroup':publisher_group(url),
            'notice':'Weights describe review availability, not credibility of claims or independence of owners.'}

@router.get('/api/cases/{case_id}/source-quality')
def source_quality(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        rows=[dict(x) for x in c.execute(
           'SELECT id,provider,label,source_url,fetched_at,status FROM evidence '
           'WHERE case_id=? ORDER BY fetched_at DESC,id DESC LIMIT 500',(case_id,))]
        sources={row['id']:dict(row) for row in c.execute(
           'SELECT r.evidence_id,r.publisher_authentication FROM evidence_source_reviews r '
           'WHERE r.case_id=? ORDER BY r.reviewed_at DESC,r.id DESC',(case_id,))}
        captures={row['evidence_id'] for row in c.execute(
           'SELECT DISTINCT evidence_id FROM source_captures WHERE case_id=?',(case_id,))}
    items=[{'evidenceId':x['id'],'label':x['label'],
            **source_rubric(x,sources.get(x['id']),x['id'] in captures)} for x in rows]
    return {'items':items,'total':len(items),
        'staleOrUnknown':sum(x['retrievalPolicy']['stale'] is not False for x in items),
        'independentSourceIndependenceVerified':False,
        'notice':'A stale result should be revisited explicitly; never infer that the underlying public fact changed.'}
