"""Unified natural-language search contract; all external reasoning mocked."""
import asyncio
import json
from app import smart_search
from app.brave_context import composed_query


def test_search_requires_explicit_purpose_and_authorization(client, auth):
    endpoint='/api/search/start'
    base={'question':'Example Person cyber security Indian Navy',
          'purpose':'Authorized public-source supplier evaluation'}
    response=client.post(endpoint,headers=auth,json=base)
    assert response.status_code==422
    denied=client.post(endpoint,json={**base,'authority_confirmed':True})
    assert denied.status_code==403  # Missing required same-origin action header
    ok=client.post(endpoint,headers=auth,json={**base,'authority_confirmed':True})
    assert ok.status_code==201,ok.text
    result=ok.json()
    assert result['plan']['subjectType']=='person'
    assert result['plan']['aiPlanned'] is False
    assert result['plan']['context']['organization']==''  # Topic is not confirmed employer
    assert result['plan']['context']['profession']==''  # Topic is not confirmed profession
    assert 'github' in result['plan']['providers']
    assert client.get('/api/cases/'+result['id']).status_code==200


def test_unrelated_nonacademic_questions_do_not_invoke_academic_apis():
    for query in ('a plumber providing public services in Delhi',
                  'local community event organiser in Jaipur',
                  'Student sports activities'):
        route=smart_search.deterministic_route(query)
        assert 'crossref' not in route['providers']
        assert 'openalex' not in route['providers']
        assert route['aiPlanned'] is False


def test_explicit_dns_and_public_ip_research_is_routed():
    d=smart_search.deterministic_route('example.org')
    assert d['subjectType']=='domain' and d['providers']==['dns']
    ip=smart_search.deterministic_route('8.8.8.8')
    assert ip['subjectType']=='ip' and ip['providers']==['internetdb']


def test_private_person_tracking_queries_blocked(client,auth):
    resp=client.post('/api/search/start',headers=auth,json={
        'question':'Track this person at home right now',
        'authority_confirmed':True,
        'purpose':'Synthetic privacy test for unauthorized tracking'})
    assert resp.status_code==422


def test_ai_router_accepts_only_relevant_allowlisted_sources_and_literal_clues(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-value')
    q='Example Researcher cybersecurity Indian Navy'
    fallback=smart_search.deterministic_route(q)
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'choices':[{'message':{'content':json.dumps({
                'subject_type':'person','subject':'Example Researcher',
                'providers':['github','gdelt','evil-provider','openalex'],
                'city':'Paris','organization':'Indian Navy',
                'profession':'cybersecurity','public_handle':'secret-person'})}}]}
    class Client:
        def __init__(self,**kwargs):
            assert kwargs['follow_redirects'] is False
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return None
        async def post(self,url,headers,json):
            assert url=='https://api.groq.com/openai/v1/chat/completions'
            assert json['messages'][0]['role']=='system'
            return Response()
    monkeypatch.setattr(smart_search.httpx,'AsyncClient',Client)
    out=asyncio.run(smart_search.ai_route(q,fallback))
    assert out['aiPlanned']
    assert out['subject']=='Example Researcher'
    assert out['providers']==['github','gdelt']  # Academic source is irrelevant to this technical query
    assert out['context']['city']==''
    assert out['context']['organization']=='Indian Navy'
    assert out['context']['public_handle']==''


def test_start_uses_model_router_only_with_per_case_opt_in(client,auth,monkeypatch):
    async def boom(question,fallback):
        raise AssertionError('No AI call without explicit opt in')
    monkeypatch.setattr(smart_search,'ai_route',boom)
    r=client.post('/api/search/start',headers=auth,json={
        'question':'Example Researcher Indian Navy cybersecurity',
        'authority_confirmed':True,'ai_opt_in':False,
        'purpose':'Authorized professional source research'})
    assert r.status_code==201,r.text
    assert r.json()['plan']['aiPlanned'] is False


def test_brave_query_does_not_duplicate_known_subject():
    assert composed_query({'query':'Example Person'},'Example Person worked on public projects?',{}) == \
           'Example Person worked on public projects?'


def test_headline_question_is_not_truncated_or_polluted_and_asks_for_clarification(client, auth):
    """Regression for issues 002/019/020/032 (V7.9 sent 'Ayush cybersecurity Indian')."""
    q = 'Ayush cybersecurity Indian Navy'
    r = client.post('/api/search/start', headers=auth, json={
        'question': q, 'authority_confirmed': True,
        'purpose': 'Authorized synthetic parser regression check'})
    assert r.status_code == 201, r.text
    plan = r.json()['plan']
    assert plan['subject'] == q                      # full phrase, never 'Ayush' / pseudo-name
    assert plan['providers'] == []                   # no structured API on a bare given name
    assert plan['needsClarification'] is True and plan['clarification']
    parsed = plan['parsed']
    assert parsed['name_tokens'] == ['Ayush'] and parsed['topics'] == ['cybersecurity']
    assert parsed['organization_clues'] == ['Indian Navy']
    assert parsed['attribution_allowed'] is False
    assert plan['context']['organization'] == ''     # clue stays unverified, not a fact
