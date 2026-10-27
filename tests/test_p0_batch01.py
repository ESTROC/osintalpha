"""P0 batch 001–010 synthetic acceptance regression.

Passing these tests validates program behavior, NOT live provider accuracy,
independent person-identification ground truth or publisher licensing.
"""
import asyncio
import hashlib
import json
import pytest
from app import db, main, agent, brave_context, smart_search
from app.evidence_gates import (source_fitness, evidence_coverage, source_quote_match,
                                guard_synthesis, identity_review_gate)
from app.identity_benchmark import score_reference_set
from app.query_parse import parse_question


def test_001_two_namesakes_stay_independent():
    a={'id':'a','label':'Example Person','summary':'developer projects','status':'candidate',
       'provider':'github','source_url':'https://github.com/example-a',
       'raw_json':json.dumps({'company':'First Company','location':'Delhi'})}
    b={'id':'b','label':'Example Person','summary':'developer projects','status':'candidate',
       'provider':'openalex','source_url':'https://openalex.org/a',
       'raw_json':json.dumps({'company':'Second Company','location':'Boston'})}
    decision=guard_synthesis('Example Person works for First Company.',
        'Example Person developer', 'person',[a,b],'Example Person',
        {'organization':'First Company'},has_fresh_context=True)
    assert decision['action']=='candidate_only'
    assert 'not independently identified' in decision['answer']
    assert decision['gate']['identityVerified'] is False


def test_002_original_question_and_unverified_clues():
    q='Ayush cybersecurity Indian Navy'
    parsed=parse_question(q)
    assert parsed.query_variants[0]==q
    assert not parsed.attribution_allowed
    assert smart_search.deterministic_route(q)['subject']==q
    assert smart_search.deterministic_route(q)['needsClarification']


async def _fake_result_provider(case,job,choice,actor_id,step_no):
    return {'status':'ok' if step_no==1 else 'empty','returned':1 if step_no==1 else 0,
            'new':0,'changed':0,'message':''}

@pytest.mark.parametrize('steps',[1,2])
def test_003_bounded_multi_step_research_audited(client,auth,case,monkeypatch,steps):
    plan=client.post(f'/api/cases/{case}/jobs',headers=auth,
      json={'objective':'Review two synthetic public sources with preserved query scope',
            'mode':'guided','max_steps':2,'allow_web':False})
    assert plan.status_code==201,plan.text
    jid=plan.json()['id']
    async def next_step(case_record,job,prior,context):
        return {'provider':'github','query':f"Synthetic Test Subject round {len(prior)+1}",
                'rationale':'Distinct bounded public API search'}
    monkeypatch.setattr(agent,'choose_next',next_step)
    monkeypatch.setattr(agent,'execute_provider',_fake_result_provider)
    r=client.post(f'/api/cases/{case}/jobs/{jid}/run-bounded',headers=auth,
                  json={'steps':steps,'consent':True})
    assert r.status_code==200,r.text
    data=r.json()
    assert len(data['executedSteps'])==steps
    assert data['job']['completedSteps']==steps
    assert all(s['provider']=='github' for s in data['executedSteps'])
    assert len(set(s['query'] for s in data['executedSteps']))==steps
    assert client.get(f'/api/cases/{case}/jobs/{jid}').json()['completedSteps']==steps


def test_004_no_evidence_no_biography():
    result=guard_synthesis('A fictional person is a naval officer','Who is Example Person?',
                           'person',[],'Example Person')
    assert result['action']=='abstain'
    assert 'No attributable public-source record' in result['answer']
    assert result['gate']['coverage']['questionRelevant']==0


def _seed_capture(case):
    original="The public event is scheduled for 2 November according to the official 2026 organizer's notice."
    hash_value=hashlib.sha256(original.encode()).hexdigest()
    with db.connect() as c:
        c.execute('''INSERT INTO evidence
           (id,case_id,provider,label,summary,source_url,source_ref,fetched_at,
            sha256,raw_json) VALUES (?,?,?,?,?,?,?,?,?,?)''',
            ('batch1evidence',case,'analyst','Public notice',original,
             'https://example.org/notice','public-notice','2026-10-27T12:00:00Z',
             hash_value,'{}'))
        c.execute('''INSERT INTO source_captures
          (id,case_id,evidence_id,source_url,content_type,extracted_text,
           content_sha256,fetched_at,fetch_status,error_message)
          VALUES (?,?,?,?,?,?,?,?,?,?)''',
          ('batch1capture',case,'batch1evidence','https://example.org/notice',
           'text/html',original,hash_value,'2026-10-27T12:10:00Z','captured',''))
    return original


def test_005_claim_binding_rejects_unrelated_sources_and_matches_exact_text(client,auth,case):
    original=_seed_capture(case)
    snippet="The public event is scheduled for 2 November"
    assert source_quote_match(snippet,original)
    assert not source_quote_match("This quote was completely fabricated",original)
    excerpt=client.post(f'/api/cases/{case}/excerpts',headers=auth,json={
        'evidence_id':'batch1evidence','capture_id':'batch1capture',
        'quote_text':snippet,'interpretation':'The document asserts a planned event date.'})
    assert excerpt.status_code==201,excerpt.text
    claim=client.post(f'/api/cases/{case}/claims',headers=auth,json={
        'evidence_id':'batch1evidence','claim_text':'The notice states a date for a planned public event',
        'stance':'supports'})
    assert claim.status_code==201,claim.text
    linked=client.post(f'/api/cases/{case}/claim-passages',headers=auth,json={
        'claim_id':claim.json()['id'],'excerpt_id':excerpt.json()['id']})
    assert linked.status_code==201,linked.text
    assert linked.json()['status']=='text_match_only'
    assert linked.json()['supportsTruth'] is False
    proof=client.get(f'/api/cases/{case}/claim-passages')
    assert proof.status_code==200
    assert proof.json()['items'][0]['quote_text']==snippet
    bad=client.post(f'/api/cases/{case}/claim-passages',headers=auth,json={
        'claim_id':'different-case-claim','excerpt_id':excerpt.json()['id']})
    assert bad.status_code==422


def test_006_contextual_negative_outweighs_name_hit():
    r={'id':'x','label':'Example Engineer','summary':'Public engineering activities',
       'source_url':'https://example.org/public-profile','status':'candidate',
       'raw_json':{'company':'Unrelated Org','location':'London'}}
    fit=source_fitness(r,'Example Engineer public engineering','Example Engineer',
                       {'organization':'Different Organization','city':'Delhi'})
    assert fit['usable'] is False
    assert 'organization' in fit['conflictingClues']
    assert 'city' in fit['conflictingClues']


@pytest.mark.parametrize('q,lens',[
 ('Find a local plumbing service','trade'),
 ('Student science competition results','education'),
 ('Find developer GitHub portfolio','professional'),
 ('Public ceremony schedule','general')])
def test_007_backend_discovery_lens(q,lens):
    plan=smart_search.deterministic_route(q)
    assert plan['discoveryLens']==lens


def test_008_business_only_local_recall(monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','not-real')
    captures=[]
    class R:
        def raise_for_status(self):pass
        def json(self):return {'grounding':{'generic':[]},'sources':{}}
    class C:
        async def post(self,url,headers,json):
            captures.append({'headers':headers,'body':json})
            return R()
    async def go():
        await brave_context.retrieve({'query':'Sample Plumber','subject_type':'organization'},
            'Find plumbing service provider near public business locations',
            {'city':'Delhi'},client=C(),country='IN')
        await brave_context.retrieve({'query':'Example Person','subject_type':'person'},
            'Who wrote the technical article?',
            {'city':'Delhi'},client=C(),country='IN')
    asyncio.run(go())
    assert captures[0]['body']['enable_local'] is True
    assert captures[0]['headers']['X-Loc-City']=='Delhi'
    assert captures[0]['headers']['X-Loc-Country']=='IN'
    assert captures[1]['body']['enable_local'] is False
    assert 'X-Loc-City' not in captures[1]['headers']


def test_009_public_excerpt_samples_require_explicit_opt_in(client,auth,case,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','fake-model')
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','fake-search')
    assert client.put(f'/api/cases/{case}/ai-consent',headers=auth,json={'enabled':True}).status_code==200
    source={'title':'Public publisher example','url':'https://example.org/notice',
            'snippet':'Public publisher excerpt content. '*16,'sourceDate':'2026-10-27'}
    async def retrieve(*args,**kwargs):
        return {'sources':[source],'query':'synthetic notice','searchedNow':True}
    monkeypatch.setattr(brave_context,'retrieve',retrieve)
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':json.dumps({
            'answer':'Multiple public candidates; identity remains unverified',
            'evidence_ids':[],'follow_up':'','needs_disambiguation':True})}}]}
    class HTTP:
        def __init__(self,*a,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def post(self,*a,**kw):return Response()
    monkeypatch.setattr(main.httpx,'AsyncClient',HTTP)
    denied=client.post(f'/api/cases/{case}/chat',headers=auth,json={
        'question':'What is public?','provider':'groq','save_bounded_excerpts':True})
    assert denied.status_code==422
    r=client.post(f'/api/cases/{case}/chat',headers=auth,json={
        'question':'What is public?','provider':'groq',
        'brave_context':True,'save_bounded_excerpts':True})
    assert r.status_code==200,r.text
    stored=client.get(f'/api/cases/{case}/research-excerpts')
    assert stored.status_code==200
    sample=stored.json()['items'][0]
    assert len(sample['excerpt_text'])<=160
    assert sample['retention_basis']=='explicit_case_analyst_opt_in'
    assert sample['review_state']=='unverified_search_excerpt'


def test_010_reference_metric_refuses_fake_ground_truth():
    examples=[{
        'pair_id':f'pair-{i:02}',
        'adjudicated_same_person':i<10,
        'source_signal':'candidate_link' if i%3==0 else 'abstain',
        'adjudication_reference':f'internal://consented-review/{i}',
        'independent_reviewer_ids':['reviewer-1','reviewer-2']} for i in range(20)]
    scored=score_reference_set(examples)
    assert scored['totalPairs']==20
    assert scored['negativeNamesakePairs']==10
    assert scored['groundTruthStatus']=='reviewer_supplied_not_independently_audited_by_software'
    bad=[dict(x) for x in examples]
    bad[0]['independent_reviewer_ids']=['reviewer-1']
    with pytest.raises(ValueError):
        score_reference_set(bad)


def test_002_auditable_manual_subject_correction_before_collection(client,auth):
    created=client.post('/api/search/start',headers=auth,json={
        'question':'Demo cyber-security public projects',
        'purpose':'Authorized synthetic analyst disambiguation acceptance',
        'authority_confirmed':True})
    assert created.status_code==201,created.text
    cid=created.json()['id']
    review=client.post(f'/api/cases/{cid}/search-plan/subject-review',headers=auth,json={
        'reviewed_subject':'Demo Example Person',
        'rationale':'Analyst supplied a distinguishing full public search label.',
        'acknowledges_unverified':True})
    assert review.status_code==200,review.text
    assert review.json()['identityVerified'] is False
    assert review.json()['originalQuestion']=='Demo cyber-security public projects'
    assert client.get(f'/api/cases/{cid}').json()['case']['query']=='Demo Example Person'
    recovered=client.get(f'/api/cases/{cid}/search-plan').json()['plan']
    assert recovered['analystSubjectReview']['identityVerified'] is False
    assert recovered['subject']=='Demo Example Person'
