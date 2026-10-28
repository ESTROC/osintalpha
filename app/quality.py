"""Analyst-labelled identity-link signal evaluation.

Metrics describe agreement with analyst labels, not verified identity accuracy.
A public-handle or website overlap is an INVESTIGATION SIGNAL, not same-person proof.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
from .identity import attributes,compare

router=APIRouter()
PROFILE_SOURCES={'github','stackoverflow','openalex','analyst'}

class PairReview(BaseModel):
    left_id:str=Field(min_length=1,max_length=90)
    right_id:str=Field(min_length=1,max_length=90)
    decision:Literal['possible_same_person','different_people']
    rationale:str=Field(min_length=30,max_length=1500)

def validate_pair(conn,case_id,left,right):
    if left==right:raise HTTPException(422,'Two distinct source records are required.')
    rows=[dict(x) for x in conn.execute(
        'SELECT id,provider,label,source_url,raw_json,status FROM evidence WHERE case_id=? AND id IN (?,?)',
        (case_id,left,right))]
    if len(rows)!=2:raise HTTPException(422,'Both source records must belong to the current investigation.')
    if any(x['provider'] not in PROFILE_SOURCES for x in rows):
        raise HTTPException(422,'Select two public profile candidate records, not publication or news snippets.')
    return {x['id']:x for x in rows}

@router.post('/api/cases/{case_id}/identity-reviews',status_code=201)
def add_review(case_id:str,body:PairReview,actor=Depends(core.protect)):
    left,right=sorted((body.left_id,body.right_id))
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=validate_pair(conn,case_id,left,right)
        id=core.uid()
        conn.execute('INSERT INTO identity_pair_reviews VALUES (?,?,?,?,?,?,?,?)',
          (id,case_id,left,right,body.decision,body.rationale.strip(),
           actor['id'],datetime.now(timezone.utc).isoformat(timespec='microseconds')))
        if body.decision=='different_people':
            from .analyst_governance import queue
            queue(conn,case_id,actor['id'],'namesake_conflict',left+'-'+right,
                  'Review conflicting same-name public profiles',
                  'Different-source pair '+left+' / '+right+' must remain separate until reviewer checks each source; do not auto-merge.')
    core.write_audit(actor['id'],'identity_signal_review','case',case_id,id)
    return {'id':id,'decision':body.decision,'notice':'Analyst-labelled example only; not independently verified ground truth.'}

def get_reviews(conn,case_id):
    rows=[dict(x) for x in conn.execute('''SELECT r.*,u.username reviewer
       FROM identity_pair_reviews r JOIN users u ON u.id=r.reviewer_id
       WHERE r.case_id=? ORDER BY r.reviewed_at DESC,r.id DESC LIMIT 2000''',(case_id,))]
    seen=set();latest=[]
    for r in rows:
        pair=(r['left_evidence_id'],r['right_evidence_id'])
        if pair not in seen:
            seen.add(pair);latest.append(r)
    return rows,latest

@router.get('/api/cases/{case_id}/identity-quality')
def identity_quality(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        events,latest=get_reviews(conn,case_id)
        evidence=[dict(x) for x in conn.execute(
           'SELECT id,provider,label,source_url,raw_json,status FROM evidence WHERE case_id=?',
           (case_id,))]
    byid={x['id']:x for x in evidence}
    stats=Counter()
    details=[]
    for label in latest:
        left=byid.get(label['left_evidence_id'])
        right=byid.get(label['right_evidence_id'])
        if not left or not right:continue
        result=compare(attributes(left),attributes(right))
        predicted=result['signalLevel']=='investigate_public_identifier'
        expected=label['decision']=='possible_same_person'
        category='tp' if predicted and expected else 'fp' if predicted else 'fn' if expected else 'tn'
        stats[category]+=1
        details.append({'leftId':left['id'],'rightId':right['id'],
           'label':label['decision'],'signalLevel':result['signalLevel'],
           'signalRaised':predicted,'outcome':category,
           'rationale':label['rationale'],'reviewer':label['reviewer'],
           'reviewedAt':label['reviewed_at']})
    tp,fp,fn,tn=[stats[k] for k in ('tp','fp','fn','tn')]
    def ratio(num,den):
        return round(num/den,4) if den else None
    # More than one human-labelled class must be represented. This remains an
    # internal consistency measure even when the sample size is large.
    usable=(tp+fn)>=5 and (tn+fp)>=5 and len(details)>=20
    return {'pairs':details,'reviewEvents':len(events),'latestLabelledPairs':len(details),
      'confusion':{'tp':tp,'fp':fp,'fn':fn,'tn':tn},
      'precisionAgainstAnalystLabels':ratio(tp,tp+fp),
      'recallAgainstAnalystLabels':ratio(tp,tp+fn),
      'falseAlertRateAgainstAnalystLabels':ratio(fp,fp+tn),
      'sampleSufficientForInternalTrend':usable,
      'limitation':'These are agreement rates against case-specific analyst labels, NOT validated true identity accuracy. Shared usernames/websites only generate review signals, never verified identity decisions. For meaningful benchmarks use representative, independently adjudicated diverse labels and report confidence intervals.'}
