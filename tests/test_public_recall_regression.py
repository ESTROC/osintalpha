"""Synthetic reproduction: long-form person request must not lose a public post.

Only verifies planning, record selection and safe model context. Does not
authenticate the publisher, employment or education; no real API calls.
"""
import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest
from app import db, main, smart_search, v5
from app.retrieval import rank_case_evidence
from app.search_querying import person_name, select_queries

PROMPT=('I want to know about a person called as Ayush Tripathi who has worked '
        'in cyber security engineering in Indian Navy and is passed out from ADGIPS')


def test_explicit_person_is_extracted_from_long_request():
    assert person_name(PROMPT)=='Ayush Tripathi'
    plan=smart_search.deterministic_route(PROMPT)
    assert plan['subject']=='Ayush Tripathi'
    assert plan['parsed']['subject_text']=='Ayush Tripathi'
    assert plan['needsClarification'] is False
    assert plan['discoveryLens']=='professional'
    assert plan['context']['organization']==''  # Not a confirmed employer.


def test_long_request_expands_into_original_and_source_specific_queries():
    case={'subject_type':'person','query':'Ayush Tripathi'}
    body=SimpleNamespace(query=PROMPT,depth=4,lens='professional')
    queries=v5.make_queries(case,{},body)
    assert len(queries)==4,queries
    assert queries[0]==PROMPT
    assert any('site:linkedin.com/posts/' in q for q in queries)
    assert any('"Ayush Tripathi"' in q and 'Navy' in q for q in queries)
    assert any('"ADGIPS"' in q for q in queries)


def test_relevance_filter_excludes_unrelated_same_name_profiles():
    rows=[]
    for i,career in enumerate(['Genpact manager','IDfy DevOps','Google engineer',
                               'NCRTC cyber security','Startup founder','Bank analyst',
                               'Consultant','Student','Sales manager']):
        rows.append({'id':'unrelated'+str(i),'provider':'brave_web',
                     'label':'Ayush Tripathi - '+career,
                     'summary':'Public profile: '+career+' in unrelated company',
                     'raw_json':'{}','status':'candidate',
                     'source_url':'https://example.org/profile/'+str(i)})
    rows.append({'id':'navy_post','provider':'brave_web',
                 'label':'Ayush Tripathi — Cyber Security Internship | Indian Navy',
                 'summary':'Published post states Navy cybersecurity internship and MFA security work',
                 'raw_json':'{}','status':'candidate',
                 'source_url':'https://www.linkedin.com/posts/example_public_post'})
    selected,info=rank_case_evidence(rows,PROMPT,{},limit=35,
                                     focused_person=True,subject='Ayush Tripathi')
    assert [r['id'] for r in selected]==['navy_post'],info
    assert info['excludedAsUnrelatedCandidates']==9
    assert info['identitiesVerified']==0


def test_first_public_index_search_runs_multiple_site_and_clue_variants(client,auth,monkeypatch):
    import httpx
    created=client.post('/api/search/start',headers=auth,json={
        'question':PROMPT,
        'purpose':'Authorized synthetic provider-relevance regression',
        'authority_confirmed':True})
    assert created.status_code==201,created.text
    cid=created.json()['id']
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','synthetic-key-never-live')
    queries=[]
    class Response:
        def __init__(self,params):self.params=params
        def raise_for_status(self):pass
        def json(self):
            q=self.params['q']
            if 'site:linkedin.com/posts/' in q:
                return {'web':{'results':[{
                    'title':'Ayush Tripathi - Indian Navy cybersecurity internship',
                    'url':'https://www.linkedin.com/posts/synthetic-public-post',
                    'description':'Public self-report about an internship; school not independently verified'
                }]}}
            return {'web':{'results':[]}}
    class Client:
        def __init__(self,*args,**kwargs):
            assert kwargs.get('follow_redirects') is False
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return None
        async def get(self,url,params,headers):
            assert url=='https://api.search.brave.com/res/v1/web/search'
            queries.append(params['q'])
            assert params['country']=='ALL'
            return Response(params)
    monkeypatch.setattr(v5.httpx,'AsyncClient',Client)
    found=client.post(f'/api/cases/{cid}/web-discovery',headers=auth,json={
        'query':PROMPT,'lens':'professional','depth':4,'consent':True,'country':'ALL'})
    assert found.status_code==200,found.text
    assert len(queries)==4
    assert found.json()['new']==1
    assert any('site:linkedin.com/posts/' in q for q in queries)
    records=client.get(f'/api/cases/{cid}').json()['evidence']
    assert any('Indian Navy' in r['label'] for r in records)


def test_groq_receives_only_topic_matching_namesake_candidates(client,auth,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-groq-key')
    created=client.post('/api/cases',headers=auth,json={
        'title':'Synthetic identity ambiguity','subject_type':'person',
        'query':'Ayush Tripathi',
        'purpose':'Authorized synthetic evidence relevance regression',
        'authority_confirmed':True,'ai_opt_in':True})
    assert created.status_code==201
    cid=created.json()['id']
    with db.connect() as conn:
        for i,label in enumerate([
            'Ayush Tripathi — Genpact senior manager',
            'Ayush Tripathi — IDfy software engineer',
            'Ayush Tripathi — Indian Navy cybersecurity internship'
        ]):
            summary='Public profile with unrelated employer'
            if i==2:summary='Public post describes work with Indian Navy cybersecurity'
            conn.execute(
                '''INSERT INTO evidence (id,case_id,provider,label,summary,source_url,
                   source_ref,fetched_at,sha256,raw_json,status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                ('relevance'+str(i),cid,'brave_web',label,summary,
                 f'https://example.org/public/{i}',str(i),'2026-10-29T12:00:00Z',
                 hashlib.sha256(label.encode()).hexdigest(),'{}','candidate'))
    seen=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':json.dumps({
            'answer':'Public source candidate is unverified.',
            'evidence_ids':[],'needs_disambiguation':True,'follow_up':'Verify independently.'})}}]}
    class Client:
        def __init__(self,*args,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return None
        async def post(self,url,json,headers):
            for msg in json['messages']:
                if 'RESEARCH CONTEXT' in str(msg.get('content')):
                    seen.append(msg['content'])
            return Response()
    monkeypatch.setattr(main.httpx,'AsyncClient',Client)
    out=client.post(f'/api/cases/{cid}/chat',headers=auth,json={
        'provider':'groq','question':PROMPT})
    assert out.status_code==200,out.text
    assert out.json()['retrieval']['selected']==1
    assert out.json()['retrieval']['excludedAsUnrelatedCandidates']==2
    assert any('Indian Navy' in x for x in seen)
    assert not any('Genpact' in x or 'IDfy' in x for x in seen)


def test_model_cannot_claim_no_public_record_when_relevant_lead_exists(client,auth,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-only')
    created=client.post('/api/cases',headers=auth,json={
        'title':'Namesake accuracy regression','subject_type':'person',
        'query':'Ayush Tripathi','purpose':'Authorized synthetic evidence evaluation',
        'authority_confirmed':True,'ai_opt_in':True})
    assert created.status_code==201
    cid=created.json()['id']
    with db.connect() as conn:
        conn.execute('''INSERT INTO evidence
          (id,case_id,provider,label,summary,source_url,source_ref,fetched_at,
           sha256,raw_json,status) VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
           ('public-navy-lead',cid,'brave_web',
            'Ayush Tripathi — Indian Navy cyber security internship',
            'Self-reported public LinkedIn post about Indian Navy security internship',
            'https://www.linkedin.com/posts/synthetic-only','public-navy-lead',
            '2026-10-29T12:00:00Z',
            hashlib.sha256(b'public navy').hexdigest(),'{}','candidate'))
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':json.dumps({
            'answer':'The sources we have do not contain any record of that work.',
            'evidence_ids':[],'needs_disambiguation':True,
            'follow_up':'Please supply a second clue.'})}}]}
    class Client:
        def __init__(self,*args,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return None
        async def post(self,*args,**kwargs):return Response()
    monkeypatch.setattr(main.httpx,'AsyncClient',Client)
    r=client.post(f'/api/cases/{cid}/chat',headers=auth,json={
        'provider':'groq','question':PROMPT})
    assert r.status_code==200,r.text
    out=r.json()
    assert 'do not contain any record' not in out['answer']
    assert 'candidate pages' in out['answer']
    assert len(out['relevantCandidates'])==1
    assert out['relevantCandidates'][0]['url'].startswith('https://www.linkedin.com/posts/')
    assert out['needsDisambiguation'] is True
