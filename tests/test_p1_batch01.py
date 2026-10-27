"""P1 029–038: scoped synthetic acceptance, not independent provider accuracy."""
import asyncio
import json
from urllib.parse import urlsplit

import pytest

from app import db,main,smart_search,v5
from app.search_policy import (
    plan_question,question_type,publisher_group,balance_results,
    coverage_decision,permitted_sources
)
from app.connectors import CATALOG


@pytest.mark.parametrize('q,task',[
 ('Public employment history of Example Person','professional'),
 ('Local electrician repair business','business'),
 ('Published academic research papers','academic'),
 ('A public community festival schedule','public_event'),
 ('Cybersecurity vulnerability advisory','public_security'),
 ('Passive DNS for example.org','passive_technical'),
 ('Student school competition notice','education'),
 ('Legal company registration record','legal_entity')
])
def test_029_030_taxonomy_and_original_query(q,task):
    plan=plan_question(q,'person',CATALOG)
    assert plan['questionType']==task
    assert plan['parsed']['original']==q
    assert plan['variants'][0]==q
    assert plan['parsed']['attribution_allowed'] is False


def test_031_model_cannot_override_task_specific_source_allowlist(monkeypatch):
    assert 'openalex' not in permitted_sources('person','business',CATALOG)
    assert 'github' not in permitted_sources('person','academic',CATALOG)
    assert 'crossref' not in permitted_sources('person','public_security',CATALOG)
    monkeypatch.setenv('GROQ_API_KEY','fake-planner-test-key')
    class R:
        def raise_for_status(self): pass
        def json(self):
            return {'choices':[{'message':{'content':json.dumps({
                'subject_type':'person','subject':'Example Person',
                'providers':['openalex','crossref','github','gdelt'],
                'organization':'','city':''})}}]}
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):return R()
    monkeypatch.setattr(smart_search.httpx,'AsyncClient',Client)
    query='Example Person cybersecurity public projects'
    out=asyncio.run(smart_search.ai_route(query,smart_search.deterministic_route(query)))
    assert out['providers']==['github','gdelt']
    assert out['questionType']=='public_security'


def test_032_first_name_stops_expensive_groq_routing(client,auth,monkeypatch):
    called=[]
    async def reject(*args,**kwargs):
        called.append(True)
        raise AssertionError('Remote planner must not run before clarification')
    monkeypatch.setattr(smart_search,'ai_route',reject)
    r=client.post('/api/search/start',headers=auth,json={
        'question':'Ayush cybersecurity Indian Navy',
        'purpose':'Authorized public synthetic namesake test',
        'authority_confirmed':True,'ai_opt_in':True})
    assert r.status_code==201,r.text
    plan=r.json()['plan']
    assert plan['needsClarification']
    assert plan['deferExternalSearch'] is True
    assert plan['originalQuery']=='Ayush cybersecurity Indian Navy'
    assert called==[]


def test_033_036_037_publisher_diversity_and_stop_budget():
    rows=[{'url':f'https://news.example.org/item/{i}'} for i in range(8)]
    rows += [{'url':'https://anothernews.org/article'},
             {'url':'https://thirdsite.co.in/article'},
             {'url':'https://fourthsite.org/record'}]
    selected=balance_results(rows,max_per_site=2)
    assert len(selected)==5
    assert publisher_group('https://cdn.thirdsite.co.in/foo')=='thirdsite.co.in'
    assert len({publisher_group(i['url']) for i in selected})==4
    decision=coverage_decision(rows,queries_executed=1)
    assert decision['stop'] is True
    assert decision['reason']=='candidate_diversity_target_met_not_exhaustive'
    assert coverage_decision([],queries_executed=3)['reason']=='query_budget_exhausted'


def test_036_brave_pages_with_realistic_mocked_responses(client,auth,case,monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','test-credential')
    calls=[]
    class Resp:
        def __init__(self,data):self.data=data
        def raise_for_status(self):return None
        def json(self):return self.data
    class HTTP:
        def __init__(self,*args,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        async def get(self,url,params,headers):
            assert 'api.search.brave.com' in url
            calls.append(params['offset'])
            page=params['offset']
            if page==0:
                found=[{'title':'Publisher original','description':'Candidate source text',
                        'url':f'https://publisher.org/{i}'} for i in range(8)]
            else:
                found=[{'title':'Different publisher','description':'Additional public lead',
                        'url':f'https://newsite{i}.org/doc'} for i in range(4)]
            return Resp({'web':{'results':found},
                         'query':{'more_results_available':page==0}})
    monkeypatch.setattr(v5.httpx,'AsyncClient',HTTP)
    r=client.post(f'/api/cases/{case}/web-discovery',headers=auth,json={
        'query':'Synthetic Public Subject','depth':1,'pages':2,'adaptive':True,'consent':True})
    assert r.status_code==200,r.text
    result=r.json()
    assert calls==[0,1]
    assert result['publisherHosts']>=4
    assert result['executedQueries']==1
    assert result['returned']<=36
    assert result['indexScope'].startswith('Brave public index')


def test_034_035_cross_engine_requires_consent_and_preserves_caveat(client,auth,case,monkeypatch):
    with db.connect() as c:
        user=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    actor={'id':user['id'],'role':'admin'}
    sid=main.save_chat(case,actor,main.ChatMessage(
        question='Public source claims',provider='groq'),
        'Public source claims',{
        'answer':'Unverified public source found',
        'evidenceIds':[],
        'webLeads':[{'url':'https://public.org/article','title':'Publisher candidate'}]},'groq')
    assert client.put(f'/api/cases/{case}/ai-consent',
                      headers=auth,json={'enabled':True}).status_code==200
    async def fake_chat(case_id,body,actor):
        assert body.web_search is True and body.brave_context is False
        assert body.session_id==sid
        return {'sessionId':sid,'answer':'Two candidate links; neither is verified.',
            'webLeads':[{'url':'https://public.org/different','title':'Same publisher'},
                        {'url':'https://second.org/record','title':'Different publisher'}]}
    monkeypatch.setattr(main,'chat',fake_chat)
    path=f'/api/cases/{case}/cross-engine-check'
    no=client.post(path,headers=auth,json={'session_id':sid,'question':'Check public claim','consent':False})
    assert no.status_code==422
    result=client.post(path,headers=auth,json={'session_id':sid,
        'question':'Check public claim','consent':True})
    assert result.status_code==200,result.text
    report=result.json()
    assert report['independentCorroborationVerified'] is False
    assert report['overlappingPublisherGroups']==['public.org']


def test_038_local_index_is_case_scoped_and_not_a_global_web_index(client,auth,case):
    with db.connect() as conn:
        conn.execute("""INSERT INTO evidence(id,case_id,provider,label,summary,
            source_url,source_ref,fetched_at,sha256,raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            ('p1-local-index-test',case,'analyst','Synthetic public software project',
             'Public open-source portfolio candidate only','https://example.org/work',
             'test','2026-10-27T00:00:00Z','samplehash','{}'))
    r=client.get(f'/api/cases/{case}/local-source-index',params={'q':'software project'})
    assert r.status_code==200,r.text
    data=r.json()
    assert data['scope']=='case_saved_sources_only'
    assert data['searchedGlobalWeb'] is False
    assert data['hasIndependentIndex'] is False
    assert data['identityVerified'] is False
    assert [row['id'] for row in data['items']]==['p1-local-index-test']
