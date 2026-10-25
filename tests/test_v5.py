"""V5 integrity and provider regressions. No live credentials or untrusted requests."""
from app import db
from app import v5

def add_evidence(client,auth,case,url='https://github.com/known'):
    r=client.post('/api/cases/'+case+'/evidence',headers=auth,json={
      'label':'Test profile record','summary':'A public profile that needs analyst verification',
      'source_url':url})
    assert r.status_code==200,r.text
    return r.json()['id']

def test_source_retrieval_blocks_arbitrary_hosts_and_local_ips(client,auth,case):
    assert not v5.capture_allowed('http://github.com/somebody')
    assert not v5.capture_allowed('https://127.0.0.1/')
    assert not v5.capture_allowed('https://github.com.evil.example.net/')
    assert not v5.capture_allowed('https://localhost/')
    assert v5.capture_allowed('https://github.com/known')
    eid=add_evidence(client,auth,case,'https://www.external.example.net/page')
    result=client.post('/api/cases/'+case+'/evidence/'+eid+'/capture',headers=auth)
    assert result.status_code==422
    assert client.get('/api/cases/'+case+'/evidence/'+eid+'/captures').json()['items']==[]

def test_text_extraction_suppresses_scripts_and_styles():
    text=v5.extract_text(b'<html><head><title>Secret title</title></head><body>'
       b'<script>DO_NOT_INCORPORATE</script><article><h1>Public profile</h1><p>Verified?</p></article>'
       b'</body></html>','text/html')
    assert 'Public profile' in text and 'Verified?' in text
    assert 'DO_NOT_INCORPORATE' not in text

def test_web_search_requires_consent_and_configuration(client,auth,case,monkeypatch):
    monkeypatch.delenv('BRAVE_SEARCH_API_KEY',raising=False)
    caps=client.get('/api/research/providers')
    assert caps.status_code==200 and not caps.json()['web']['configured']
    r=client.post('/api/cases/'+case+'/web-discovery',headers=auth,json={'depth':2})
    assert r.status_code==422
    r=client.post('/api/cases/'+case+'/web-discovery',headers=auth,json={'depth':2,'consent':True})
    assert r.status_code==409

def test_real_web_result_metadata_is_ingested_without_identity_verification(client,auth,case,monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','synthetic-key-not-real')
    class SearchResponse:
        def raise_for_status(self):pass
        def json(self):return {'web':{'results':[
            {'title':'Public university page','url':'https://university.example.org/people/known','description':'Unverified researcher'},
            {'title':'Local service','url':'https://127.0.0.1/internal','description':'Must be dropped'},
            {'title':'Unencrypted','url':'http://example.org/data','description':'Must be dropped'}]}}
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,*args,**kwargs):
            assert kwargs['headers']['X-Subscription-Token']=='synthetic-key-not-real'
            return SearchResponse()
    monkeypatch.setattr(v5.httpx,'AsyncClient',Client)
    r=client.post('/api/cases/'+case+'/web-discovery',headers=auth,json={'depth':1,'consent':True})
    assert r.status_code==200,r.text
    assert r.json()['returned']==1 and r.json()['new']==1
    ev=client.get('/api/cases/'+case).json()['evidence']
    assert ev[0]['provider']=='brave_web'
    assert ev[0]['status']=='candidate'
    assert 'page not yet captured' in ev[0]['summary']
    h=client.get('/api/cases/'+case+'/research-history').json()['items']
    assert h[0]['provider']=='brave_web'

def test_public_page_capture_preserves_extracted_text_and_digest(client,auth,case,monkeypatch):
    eid=add_evidence(client,auth,case)
    class Page:
        status_code=200
        headers={'content-type':'text/html;charset=utf-8'}
        def raise_for_status(self):pass
        async def aiter_bytes(self):
            yield b'<html><body><h1>Example public developer page</h1>'
            yield b'<p>This profile is a candidate, not independent confirmation.</p></body></html>'
    class Stream:
        async def __aenter__(self):return Page()
        async def __aexit__(self,*args):pass
    class Client:
        def __init__(self,**kwargs):assert not kwargs['follow_redirects']
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        def stream(self,method,url,headers):
            assert method=='GET' and url=='https://github.com/known'
            return Stream()
    monkeypatch.setattr(v5.httpx,'AsyncClient',Client)
    r=client.post('/api/cases/'+case+'/evidence/'+eid+'/capture',headers=auth)
    assert r.status_code==200,r.text
    assert len(r.json()['sha256'])==64
    captured=client.get('/api/cases/'+case+'/evidence/'+eid+'/captures').json()['items']
    assert len(captured)==1
    assert 'Example public developer page' in captured[0]['text']
    assert 'not independent confirmation' in captured[0]['text']

def test_identity_confirmation_requires_two_distinct_reviewed_providers(client,auth,case):
    candidate=client.post('/api/cases/'+case+'/candidates',headers=auth,json={
      'display_name':'Test Candidate','classification':'confirmed_by_analyst'})
    assert candidate.status_code==422
    cid=client.post('/api/cases/'+case+'/candidates',headers=auth,json={
      'display_name':'Test Candidate'}).json()['id']
    response=client.patch('/api/cases/'+case+'/candidates/'+cid,headers=auth,json={
      'classification':'confirmed_by_analyst',
      'reason':'Two matching verified institutional and employer profile links were reviewed'})
    assert response.status_code==422

def test_single_source_corroboration_needs_specific_rationale_and_audit(client,auth,case):
    eid=add_evidence(client,auth,case)
    bad=client.patch('/api/evidence/'+eid,headers=auth,json={'status':'corroborated','reviewer_notes':''})
    assert bad.status_code==422
    good=client.patch('/api/evidence/'+eid,headers=auth,json={
      'status':'disputed','reviewer_notes':'This appears to be another person based on the employer'})
    assert good.status_code==200
    with db.connect() as c:
        rows=[dict(x) for x in c.execute('SELECT old_status,new_status,rationale FROM review_decisions WHERE case_id=?',(case,))]
    assert len(rows)==1
    assert rows[0]['old_status']=='candidate'
    assert rows[0]['new_status']=='disputed'

def test_cannot_mark_empty_case_complete(client,auth,case):
    r=client.put('/api/cases/'+case+'/assessment',headers=auth,json={
      'status':'completed','executive_summary':'Enough characters to fill the summary but no evidence is actually present',
      'assessment':'Enough characters to fill an assessment, still with no evidence attached',
      'limitations':'Research was not actually completed, so this should be rejected'})
    assert r.status_code==422,r.text
