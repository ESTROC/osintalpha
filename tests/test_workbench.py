import asyncio
from app import main
from app.connectors import Evidence, AdapterError, geo_events, tfl_cameras, caltrans_cameras


def test_health_and_ui(client):
    assert client.get('/api/health').json()['ok'] is True
    assert 'OSINTALPHA' in client.get('/').text
    assert client.get('/assets/app.js').status_code==200
    assert client.get('/api/cases').status_code==401


def test_login_failure(client):
    assert client.post('/api/auth/login',json={'username':'admin','password':'wrong'}).status_code==401
    for _ in range(7): client.post('/api/auth/login',json={'username':'admin','password':'bad'})
    assert client.post('/api/auth/login',json={'username':'admin','password':'bad'}).status_code==429


def test_reject_unauthorized_case(client,auth):
    body={'title':'Example','subject_type':'person','query':'Sample Name','purpose':'This is just an example','authority_confirmed':False}
    assert client.post('/api/cases',headers=auth,json=body).status_code==422
    body['authority_confirmed']=True
    assert client.post('/api/cases',json=body).status_code==403


def test_case_lifecycle(client,auth,case):
    c=client.get('/api/cases/'+case).json()['case']
    assert c['query']=='Test Person'
    assert client.get('/api/overview').json()['cases']==1
    assert client.get('/api/cases/'+case+'/report.html').status_code==200
    pdf=client.get('/api/cases/'+case+'/report.pdf')
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
    assert client.get('/api/cases/'+case+'/report.json').json()['case']['id']==case
    assert client.delete('/api/cases/'+case,headers=auth).status_code==200
    assert client.get('/api/cases/'+case).status_code==404
    assert any(r['action']=='delete' for r in client.get('/api/audit').json()['items'])


def test_manual_evidence_validation(client,auth,case):
    base={'label':'Documented lead','summary':'Public profile appears to claim an affiliation','source_url':'https://example.org/profile'}
    assert client.post('/api/cases/'+case+'/evidence',headers=auth,json={**base,'source_url':'file:///etc/passwd'}).status_code==422
    assert client.post('/api/cases/'+case+'/evidence',headers=auth,json={**base,'source_url':'https://admin:123@example.org'}).status_code==422
    ev=client.post('/api/cases/'+case+'/evidence',headers=auth,json=base)
    assert ev.status_code==200
    eid=ev.json()['id']
    d=client.get('/api/cases/'+case).json()['evidence'][0]
    assert d['status']=='candidate'
    r=client.patch('/api/evidence/'+eid,headers=auth,json={'status':'disputed','reviewer_notes':'Source identity does not match case'})
    assert r.status_code==200
    assert client.get('/api/cases/'+case).json()['evidence'][0]['status']=='disputed'
    assert 'disputed' in client.get('/api/cases/'+case+'/report.html').text


def test_html_escapes_untrusted_source(client,auth,case):
    client.post('/api/cases/'+case+'/evidence',headers=auth,json={
        'label':'<script>alert(1)</script>','summary':'<img src=x onerror=alert(1)>',
        'source_url':'https://example.org/a?q=x&y=1'})
    body=client.get('/api/cases/'+case+'/report.html').text
    assert '<script>alert(1)</script>' not in body
    assert '&lt;script&gt;' in body
    assert '<img src=x onerror' not in body


def test_collect_saves_and_deduplicates(client,auth,case,monkeypatch):
    async def fake(provider,query,kind,client=None):
        assert kind=='person'
        return [Evidence('Candidate Jane','Unverified public record','https://example.org/jane','one',{'id':'one'})]
    monkeypatch.setattr(main,'collect_one',fake)
    for expected in (1,0):
        r=client.post('/api/cases/'+case+'/collect',headers=auth,json={'providers':['github']})
        assert r.status_code==200
        assert r.json()['results'][0]['new']==expected
    assert len(client.get('/api/cases/'+case).json()['evidence'])==1


def test_collect_errors_not_reported_as_absence(client,auth,case,monkeypatch):
    async def fake(*args,**kwargs):raise AdapterError('Rate limit exceeded')
    monkeypatch.setattr(main,'collect_one',fake)
    response=client.post('/api/cases/'+case+'/collect',headers=auth,json={'providers':['github']})
    assert response.status_code==200
    assert response.json()['results'][0]['status']=='error'
    assert 'Rate limit' in client.get('/api/cases/'+case).json()['runs'][0]['message']


def test_incompatible_source(client,auth,case):
    assert client.post('/api/cases/'+case+'/collect',headers=auth,json={'providers':['gleif']}).status_code==422
    assert client.post('/api/cases/'+case+'/collect',headers=auth,json={'providers':['fake']}).status_code==422


def test_offline_chat_and_grok_consent(client,auth,case):
    r=client.post('/api/cases/'+case+'/chat',headers=auth,json={'question':'Summarize my findings'})
    assert r.status_code==200 and r.json()['remote'] is False
    r=client.post('/api/cases/'+case+'/chat',headers=auth,json={'question':'Summarize my findings','use_grok':True})
    assert r.status_code==409


def test_project_and_source_catalogues(client,auth):
    ids=[x['id'] for x in client.get('/api/projects').json()['items']]
    assert {'osiris','worldmonitor','argus','camforge','gods-eye-view'}.issubset(ids)
    sources={x['id'] for x in client.get('/api/sources').json()['items']}
    assert {'github','openalex','crossref','gleif','wikipedia','wikidata','gdelt'}.issubset(sources)


def test_logout(client,auth):
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    assert client.get('/api/cases').status_code==401

class StubClient:
    def __init__(self,raw):self.raw=raw
    async def get(self,url,params=None):
        import httpx
        return httpx.Response(200,json=self.raw,request=httpx.Request('GET',url))


def test_geodata_normalization():
    eq=asyncio.run(geo_events('earthquakes',StubClient({'features':[{'id':'abc','geometry':{'coordinates':[73.1,19.2,5]},'properties':{'mag':5.0,'place':'Test','time':1000,'url':'https://earthquake.usgs.gov'}}]})))
    assert eq[0]['lat']==19.2 and eq[0]['provider']=='USGS'
    nasa=asyncio.run(geo_events('nasa',StubClient({'events':[{'id':'a','title':'Event','geometry':[{'type':'Point','coordinates':[18,40],'date':'2026-10-20'}]}]})))
    assert nasa[0]['lon']==18


def test_camera_metadata_normalization():
    listings=asyncio.run(tfl_cameras(StubClient([{'id':'x','lat':51.5,'lon':-.12,'commonName':'Road','additionalProperties':[]} ])))
    assert listings[0]['observedAt'] is None and listings[0]['feedUrl'] is None
    cal=asyncio.run(caltrans_cameras(StubClient({'features':[{'attributes':{'OBJECTID':8,'latitude':34.1,'longitude':-118.2,'locationName':'LA'}}]})))
    assert cal[0]['name']=='LA'


def test_geo_source_failure_is_explicit(client,auth,monkeypatch):
    async def boom(*a,**k):raise AdapterError('upstream failed')
    monkeypatch.setattr(main,'geo_events',boom)
    r=client.get('/api/geo/events?feed=nasa')
    assert r.status_code==502 and r.json()['status']=='unavailable'

def test_groq_missing_key_and_consent(client,auth,case,monkeypatch):
    r=client.post('/api/cases/'+case+'/chat',headers=auth,json={'question':'Summarize the evidence','provider':'groq'})
    assert r.status_code==409
    monkeypatch.setenv('GROQ_API_KEY','fake-groq-test-key')
    r=client.post('/api/cases/'+case+'/chat',headers=auth,json={'question':'Summarize the evidence','provider':'groq'})
    assert r.status_code==403


def test_groq_chat_uses_provider_endpoint(client,auth,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','fake-groq-test-key')
    c=client.post('/api/cases',headers=auth,json={'title':'Synthetic AI Chat Case','subject_type':'person',
        'query':'Demo Person','purpose':'Authorized demonstration of controlled AI summary',
        'authority_confirmed':True,'ai_opt_in':True})
    assert c.status_code==201
    case_id=c.json()['id']
    from app import main
    import httpx
    class FakeResponse:
        def raise_for_status(self): return None
        def json(self): return {'choices':[{'message':{'content':'No evidence is available.'}}]}
    class FakeClient:
        def __init__(self,*args,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): return None
        async def post(self,url,json,headers):
            assert url=='https://api.groq.com/openai/v1/chat/completions'
            assert json['model']=='openai/gpt-oss-120b'
            assert headers['Authorization']=='Bearer fake-groq-test-key'
            return FakeResponse()
    monkeypatch.setattr(main.httpx,'AsyncClient',FakeClient)
    r=client.post('/api/cases/'+case_id+'/chat',headers=auth,json={'question':'Summarize case evidence','provider':'groq'})
    assert r.status_code==200, r.text
    assert r.json()['provider']=='groq'
    assert r.json()['remote'] is True

def test_groq_explicit_provider_wins_over_legacy_flag(client,auth,case,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','dummy-groq-key-for-test')
    monkeypatch.delenv('XAI_API_KEY',raising=False)
    response=client.post('/api/cases/'+case+'/chat',headers=auth,json={
        'question':'Summarize the public-source records', 'provider':'groq','use_grok':True})
    assert response.status_code==403
    assert 'groq' in response.json()['detail']


def test_grok_error_guides_groq_configuration(client,auth,case,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','dummy-groq-key-for-test')
    monkeypatch.delenv('XAI_API_KEY',raising=False)
    response=client.post('/api/cases/'+case+'/chat',headers=auth,json={
        'question':'Summarize the public-source records', 'provider':'grok'})
    assert response.status_code==409
    assert 'choose GroqCloud' in response.json()['detail']
