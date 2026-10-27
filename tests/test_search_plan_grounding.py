"""P0 regression: persistent query origin, analyst access and Brave citation ledger.

Synthetic records only; these tests do not validate external factual accuracy,
provider service levels or original publisher rights.
"""
import json

from app import main


def test_search_plan_restores_original_and_unverified_clarification(client, auth):
    query='Ayush cybersecurity Indian Navy'
    created=client.post('/api/search/start',headers=auth,json={
        'question':query,'purpose':'Authorized synthetic question parsing validation',
        'authority_confirmed':True})
    assert created.status_code==201,created.text
    case_id=created.json()['id']
    plan=created.json()['plan']
    assert plan['subject']==query
    assert plan['parsed']['query_variants'][0]==query
    assert plan['needsClarification']
    assert not plan['parsed']['attribution_allowed']
    restored=client.get(f'/api/cases/{case_id}/search-plan')
    assert restored.status_code==200,restored.text
    assert restored.json()['question']==query
    assert restored.json()['plan']['parsed']['query_variants'][0]==query


def test_query_plan_is_protected_by_case_access(client, auth):
    created=client.post('/api/search/start',headers=auth,json={
        'question':'Sample Manufacturer Ltd public registration',
        'purpose':'Authorized supplier registration source validation',
        'authority_confirmed':True})
    assert created.status_code==201
    cid=created.json()['id']
    created_user=client.post('/api/users',headers=auth,json={
        'username':'reviewer.synthetic','password':'SyntheticTestCredentialOnly987654321',
        'role':'analyst'})
    assert created_user.status_code==201
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    login=client.post('/api/auth/login',json={
        'username':'reviewer.synthetic','password':'SyntheticTestCredentialOnly987654321'})
    assert login.status_code==200
    assert client.get(f'/api/cases/{cid}/search-plan').status_code==404
    assert client.get(f'/api/cases/{cid}/grounding').status_code==404


def test_brave_excerpt_digest_survives_conversation_but_text_not_copied(client,auth,case,monkeypatch):
    from app import brave_context
    monkeypatch.setenv('GROQ_API_KEY','fake-model-key-for-tests')
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','fake-index-key-for-tests')
    client.put(f'/api/cases/{case}/ai-consent',headers=auth,json={'enabled':True})
    snippet='Unverified index snippet from a synthetic community publisher'
    src={'url':'https://public.example.org/notice','title':'Synthetic public notice',
         'snippet':snippet,'sourceDate':'2026-01-03',
         'status':'unverified_extracted_search_context'}
    async def fake_retrieve(ca,q,clues,**kw):
        return {'searchedNow':True,'sources':[src],'query':q,
                'provider':'Brave LLM Context'}
    monkeypatch.setattr(brave_context,'retrieve',fake_retrieve)
    class Response:
        def raise_for_status(self):return None
        def json(self):
            return {'choices':[{'message':{'content':json.dumps({
                'answer':'A source page needs verification [notice](https://public.example.org/notice)',
                'evidence_ids':[],'follow_up':'What official identifier can verify the author?',
                'needs_disambiguation':True})}}]}
    class Provider:
        def __init__(self,*args,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        async def post(self,*args,**kwargs):return Response()
    monkeypatch.setattr(main.httpx,'AsyncClient',Provider)
    r=client.post(f'/api/cases/{case}/chat',headers=auth,json={
        'question':'Which public notice exists?','provider':'groq','brave_context':True})
    assert r.status_code==200,r.text
    assert r.json()['freshSourcesCount']==1
    ledger=client.get(f'/api/cases/{case}/grounding')
    assert ledger.status_code==200,ledger.text
    rows=ledger.json()['items']
    assert len(rows)==1
    assert rows[0]['source_url']==src['url']
    assert len(rows[0]['excerpt_sha256'])==64
    assert snippet not in str(rows)
    assert rows[0]['session_id']==r.json()['sessionId']
    conv=client.get(f"/api/cases/{case}/conversations/{r.json()['sessionId']}")
    assert conv.status_code==200
    assert any(x['role']=='assistant' and x['webLeads'][0]['url']==src['url']
               for x in conv.json()['messages'])


def test_no_evidence_assertion_abstains_without_hallucinated_biography(client,auth,case,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','fake-model-key-for-tests')
    assert client.put(f'/api/cases/{case}/ai-consent',headers=auth,json={
        'enabled':True}).status_code==200
    class Response:
        def raise_for_status(self):return None
        def json(self):
            return {'choices':[{'message':{'content':json.dumps({
                'answer':'Synthetic Test Person is definitely employed at an unverified agency.',
                'evidence_ids':[],'follow_up':'','needs_disambiguation':False})}}]}
    class Provider:
        def __init__(self,*args,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        async def post(self,*args,**kwargs):return Response()
    monkeypatch.setattr(main.httpx,'AsyncClient',Provider)
    r=client.post(f'/api/cases/{case}/chat',headers=auth,json={
        'question':'Who employs Synthetic Test Person?','provider':'groq'})
    assert r.status_code==200,r.text
    body=r.json()
    assert 'No attributable public-source record' in body['answer']
    assert 'definitely employed' not in body['answer']
    assert body['answerQuality']['verifiedIdentity'] is False
    assert body['needsDisambiguation'] is True
