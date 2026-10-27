"""Evidence quality checklist; internal review cannot independently prove a fact."""
from __future__ import annotations
import hashlib,json
from collections import Counter
from fastapi import APIRouter,Depends
from . import db,main as core
router=APIRouter()

def evidence_digest(conn,case_id):
    evidence=[dict(r) for r in conn.execute(
        'SELECT id,status,sha256,reviewer_notes FROM evidence WHERE case_id=? ORDER BY id',(case_id,))]
    claims=[dict(r) for r in conn.execute(
        'SELECT id,evidence_id,claim_text,stance FROM claim_links WHERE case_id=? ORDER BY id',(case_id,))]
    proofs=[dict(r) for r in conn.execute(
        'SELECT id,claim_id,excerpt_id,link_status FROM claim_passage_proofs WHERE case_id=? ORDER BY id',(case_id,))]
    packed=json.dumps({'evidence':evidence,'claims':claims,'proofs':proofs},sort_keys=True,ensure_ascii=False)
    return hashlib.sha256(packed.encode('utf-8')).hexdigest()

def summarize(rows,queries,claims,passages,jobs,ass,baseline_match):
    states=Counter(str(e.get('status') or 'candidate') for e in rows)
    failures=sum(str(q.get('status') or '') in {'error','blocked','unavailable'} for q in queries)
    incomplete_jobs=sum(j.get('status')!='completed' for j in jobs)
    questions=[]
    if not queries:questions.append('No executed queries recorded for this objective')
    if failures:questions.append('Provider errors or blocked searches leave coverage incomplete')
    if states.get('candidate',0):questions.append('Unreviewed candidate source records remain')
    if states.get('disputed',0):questions.append('Disputed source records require review')
    if not states.get('corroborated',0):questions.append('No analyst-reviewed corroborated source records')
    if not passages:questions.append('No bound source passages; claims lack passage verification')
    if not ass or ass.get('status')!='completed':questions.append('No completed analyst assessment')
    if ass and ass.get('status')=='completed' and baseline_match is not True:
        questions.append('Completed assessment predates the current source-state review')
    if not jobs:questions.append('No bounded research job; assignment completeness is unknown')
    elif incomplete_jobs:questions.append('Research job(s) unfinished or interrupted')
    return {
      'objectiveCompleted':False,
      'sourceRecordsTotal':len(rows),
      'sourceRecordsReviewed':sum(v for k,v in states.items() if k!='candidate'),
      'unreviewedCandidateCount':states.get('candidate',0),
      'analystCorroboratedSourceCount':states.get('corroborated',0),
      'disputedSourceCount':states.get('disputed',0),
      'sourceClaimsCount':len(claims),
      'exactPassageLinksCount':len(passages),
      'independentlyVerifiedFactCount':0,
      'independentlyVerifiedIdentityCount':0,
      'calibratedConfidence':None,
      'measuredClaimPrecision':None,
      'providerFailures':failures,
      'jobsCompleted':len(jobs)-incomplete_jobs,
      'jobsOutstanding':incomplete_jobs,
      'assessmentCurrentWithReviewedEvidence':baseline_match,
      'openQuestions':questions,
      'readiness':'review_needed' if questions else 'ready_for_external_independent_acceptance',
      'automaticallyCertified':False,
      'disclaimer':'Reviewed source leads, an answer, a completed job or exact passage cannot independently verify fact or identity.'
    }

@router.get('/api/cases/{case_id}/decision-readiness')
def decision_readiness(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        ev=[dict(x) for x in c.execute('SELECT id,status FROM evidence WHERE case_id=?',(case_id,))]
        queries=[dict(x) for x in c.execute('SELECT status FROM research_queries WHERE case_id=?',(case_id,))]
        claims=[dict(x) for x in c.execute('SELECT id FROM claim_links WHERE case_id=?',(case_id,))]
        proof=[dict(x) for x in c.execute('SELECT id FROM claim_passage_proofs WHERE case_id=?',(case_id,))]
        jobs=[dict(x) for x in c.execute('SELECT status FROM research_jobs WHERE case_id=?',(case_id,))]
        ass=c.execute('SELECT status FROM case_assessments WHERE case_id=?',(case_id,)).fetchone()
        baseline=c.execute('SELECT evidence_digest FROM assessment_review_baselines WHERE case_id=?',(case_id,)).fetchone()
        current=bool(baseline and baseline['evidence_digest']==evidence_digest(c,case_id))
    return {'caseId':case_id,**summarize(ev,queries,claims,proof,jobs,
        dict(ass) if ass else None,current if baseline else None)}
