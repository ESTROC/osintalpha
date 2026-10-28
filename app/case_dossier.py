"""Answer-first case dossier assembled from original case records and immutable snapshots.

Rank/order and claim-to-excerpt proof are separate operations. Search relevance
cannot establish publisher authenticity, ownership or person identity.
"""
from __future__ import annotations
from typing import Literal
from collections import Counter
from fastapi import APIRouter,Depends,HTTPException,Query
from . import db,main as core
from .report_continuity import latest_snapshot
from .claim_support import index as claim_index
from .retrieval import rank_case_evidence,words
from .portfolio import classify_url
from .source_quality import expiration
router=APIRouter()

def _format_source(record,question):
    query=set(words(question))
    title=set(words(record.get('label') or ''))
    summary=set(words(record.get('summary') or ''))
    terms=sorted((query&title)|(query&summary))[:10]
    status=record['status']
    kind=classify_url(record['source_url'])
    source_class='account_or_profile_url' if kind in {'github','orcid','openalex','linkedin_lead'} else 'public_document_or_mention'
    return {
       'id':record['id'],'provider':record['provider'],'label':record['label'],
       'summary':record['summary'][:550],'sourceUrl':record['source_url'],
       'reviewStatus':status,'fetchedAt':record['fetched_at'],
       'sourceClass':source_class,
       'datePolicy':expiration(record['provider'],record['fetched_at']),
       'rankingExplanation':{
          'matchedQuestionTerms':terms,
          'reviewedSource':status in ('corroborated','disputed'),
          'noVerifiedIdentity':True,
          'noCalibratedRelevanceProbability':True}}

def build_dossier(conn,case,*,status='all',sort='relevance',source_class='all',limit=35):
    saved=conn.execute('SELECT original_question FROM case_search_plans WHERE case_id=?',(case['id'],)).fetchone()
    question=saved['original_question'] if saved else case['query']
    records=[dict(r) for r in conn.execute(
        'SELECT id,provider,label,summary,source_url,raw_json,status,fetched_at '
        'FROM evidence WHERE case_id=? ORDER BY fetched_at DESC,id DESC LIMIT 800',(case['id'],))]
    ranking,_=rank_case_evidence(records,question,limit=800)
    ordinal={r['id']:i for i,r in enumerate(ranking)}
    shaped=[_format_source(r,question) for r in records]
    if status!='all':shaped=[r for r in shaped if r['reviewStatus']==status]
    if source_class!='all':shaped=[r for r in shaped if r['sourceClass']==source_class]
    if sort=='relevance':shaped.sort(key=lambda r:(ordinal.get(r['id'],9999),r['id']))
    elif sort=='newest':shaped.sort(key=lambda r:(r['fetchedAt'],r['id']),reverse=True)
    elif sort=='source':shaped.sort(key=lambda r:(r['provider'],r['label'].casefold(),r['id']))
    elif sort=='reviewed':shaped.sort(key=lambda r:(r['reviewStatus'] not in ('corroborated','disputed'),
                                        ordinal.get(r['id'],9999),r['id']))
    total=len(shaped)
    citations=claim_index(conn,case['id'])
    candidate_rows=[dict(r) for r in conn.execute(
        'SELECT id,display_name,classification,reason FROM candidate_profiles '
        'WHERE case_id=? ORDER BY updated_at DESC,id DESC LIMIT 15',(case['id'],))]
    queries=[dict(r) for r in conn.execute(
        'SELECT provider,status,query_text,message,created_at FROM research_queries '
        'WHERE case_id=? ORDER BY created_at DESC,id DESC LIMIT 90',(case['id'],))]
    last=latest_snapshot(conn,case['id'])
    provenance=last if last and last.get('snapshotIntegrityOk') is True else None
    provider_failures=[{'provider':r['provider'],'query':r['query_text'][:160],
        'status':r['status'],'message':r['message'][:220],'at':r['created_at']}
        for r in queries if r['status'] in ('error','unavailable','blocked','failed')]
    missing=[]
    if not provenance:missing.append('No intact saved answer-time provenance snapshot')
    if not records:missing.append('No public-source records have been saved')
    if not citations['claimsWithCurrentExactQuotes']:
        missing.append('No currently source-bound exact quotations support a manual claim')
    if any(x['status']=='disputed' for x in records):
        missing.append('Disputed sources need analyst resolution')
    if any(x['status']=='candidate' for x in records):
        missing.append('Unreviewed source candidates remain')
    if provider_failures:missing.append('Some provider calls failed; search coverage is incomplete')
    if not candidate_rows and case['subject_type']=='person':
        missing.append('No distinct namesake hypotheses have been recorded')
    return {'caseId':case['id'],'question':question,
        'answer':{'text':provenance.get('answer') if provenance else None,
            'snapshotVersion':provenance.get('snapshotVersion') if provenance else 0,
            'integrityOk':bool(provenance),'createdAt':provenance.get('createdAt') if provenance else None,
            'evidence':provenance.get('evidence',[]) if provenance else [],
            'webLeads':provenance.get('webLeads',[]) if provenance else [],
            'searchTrace':provenance.get('searchTrace') if provenance else None},
        'candidates':candidate_rows,'claims':citations['items'][:70],
        'claimsWithCurrentQuote':citations['claimsWithCurrentExactQuotes'],
        'claimCount':citations['totalClaims'],
        'sourceResults':shaped[:limit],'totalFilteredSourceResults':total,
        'sorting':sort,'sourceClassFilter':source_class,'reviewStatusFilter':status,
        'providerFailures':provider_failures[:20],
        'missingInformation':missing[:20],
        'nextReviewActions':['Inspect the original publisher for each material claim',
          'Compare namesakes before any identity attribution',
          'Review failed/unsampled providers and historical dates',
          'Record exact captured passages and an analyst assessment'],
        'identityVerified':False,'factsIndependentlyVerified':False,
        'warning':'An answer and ranked public leads are not an authenticated dossier or verified biography.'}

@router.get('/api/cases/{case_id}/dossier')
def dossier(case_id:str,sort:Literal['relevance','newest','source','reviewed']='relevance',
            status:Literal['all','candidate','corroborated','disputed','rejected']='all',
            source_class:Literal['all','account_or_profile_url','public_document_or_mention']='all',
            limit:int=Query(default=35,ge=1,le=100),actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        return build_dossier(conn,case,sort=sort,status=status,source_class=source_class,limit=limit)

@router.get('/api/cases/{case_id}/claims/{claim_id}/explain')
def explain_claim(case_id:str,claim_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        full=claim_index(conn,case_id)
    item=next((x for x in full['items'] if x['claimId']==claim_id),None)
    if not item:raise HTTPException(404,'Claim does not exist in the authorized case')
    return {**item,'verificationStatus':'exact_stored_text_only',
            'notice':'Captured quote, original URL, capture SHA and review classification are source attribution, not proof of truth.'}
