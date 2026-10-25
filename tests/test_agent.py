"""Regressions for explicit research agent control and source quotations.

No real Groq or Brave account requests are made from CI.
"""
import hashlib
import json
from datetime import datetime,timedelta,timezone
import pytest
from app import db,main,agent

def test_jobs_require_opt_in_and_support_recovery(client,auth,case,monkeypatch):
    r=client.post('/api/cases/'+case+'/jobs',headers=auth,json={
      'objective':'Find public engineering work attributable to correct subject',
      'mode':'groq','max_steps':3})
    assert r.status_code==409
    r=client.post('/api/cases/'+case+'/jobs',headers=auth,json={
      'objective':'Find public engineering work attributable to correct subject',
      'allow_web':True})
    assert r.status_code==422
    monkeypatch.delenv('BRAVE_SEARCH_API_KEY',raising=False)
    r=client.post('/api/cases/'+case+'/jobs',headers=auth,json={
      'objective':'Find public engineering work attributable to correct subject',
      'allow_web':True,'consent':True})
    assert r.status_code==409
    ok=client.post('/api/cases/'+case+'/jobs',headers=auth,json={
      'objective':'Discover public professional records and identify namesakes',
      'mode':'guided','max_steps':2})
    assert ok.status_code==201,ok.text
    jid=ok.json()['id']
    assert client.get('/api/cases/'+case+'/jobs').json()['items'][0]['id']==jid
    assert client.get('/api/cases/'+case+'/jobs/'+jid).json()['status']=='ready'

def test_guided_agent_saves_incremental_steps_and_resumes(client,auth,case,monkeypatch):
    selected=[]
    async def fake(provider,query,kind,client):
        selected.append((provider,query))
        from app.connectors import Evidence
        return [Evidence('Public engineering account','Identity is an unverified public lead',
          'https://github.com/demo-profile','stable-'+provider,
          {'login':'demo-profile','company':'Demo Engineering'})]
    monkeypatch.setattr(main,'collect_one',fake)
    j=client.post('/api/cases/'+case+'/jobs',headers=auth,json={
      'objective':'Check public engineering accounts while rejecting unrelated namesakes',
      'max_steps':2}).json()
    jid=j['id']
    first=client.post('/api/cases/'+case+'/jobs/'+jid+'/step',headers=auth)
    assert first.status_code==200,first.text
    assert first.json()['status']=='ready'
    assert first.json()['completedSteps']==1
    assert first.json()['steps'][0]['provider']=='github'
    second=client.post('/api/cases/'+case+'/jobs/'+jid+'/step',headers=auth)
    assert second.status_code==200,second.text
    assert second.json()['status']=='completed'
    assert second.json()['completedSteps']==2
    assert len(second.json()['steps'])==2
    assert len(selected)==2
    assert client.post('/api/cases/'+case+'/jobs/'+jid+'/step',headers=auth).json()['completedSteps']==2
    assert client.get('/api/cases/'+case+'/research-history').json()['items']
    assert client.get('/api/cases/'+case+'/evidence/'+
        client.get('/api/cases/'+case).json()['evidence'][0]['id']+'/versions').status_code==200

def test_job_selection_invalid_model_query_falls_back(client,auth,case,monkeypatch):
    async def invalid_model(case,context,job,steps,allowed):
        return None
    monkeypatch.setattr(agent,'ai_proposed_step',invalid_model)
    async def fake(provider,query,kind,client):
        return []
    monkeypatch.setattr(main,'collect_one',fake)
    job=client.post('/api/cases/'+case+'/jobs',headers=auth,json={
       'objective':'Search for public professional records while separating namesakes',
       'max_steps':1}).json()
    r=client.post('/api/cases/'+case+'/jobs/'+job['id']+'/step',headers=auth)
    assert r.status_code==200,r.text
    assert r.json()['status']=='completed'
    assert r.json()['steps'][0]['query']=='Test Person'

def test_job_failure_cannot_double_execute_and_recovers(client,auth,case,monkeypatch):
    jid=client.post('/api/cases/'+case+'/jobs',headers=auth,json={
       'objective':'Search public professional sources with an explicit budget',
       'max_steps':3}).json()['id']
    with db.connect() as c:
        c.execute("UPDATE research_jobs SET status='running',updated_at=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(),jid))
    assert client.post('/api/cases/'+case+'/jobs/'+jid+'/step',headers=auth).status_code==409
    assert client.post('/api/cases/'+case+'/jobs/'+jid+'/recover',headers=auth).status_code==409
    with db.connect() as c:
        c.execute("UPDATE research_jobs SET updated_at=? WHERE id=?",
            ((datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat(),jid))
    good=client.post('/api/cases/'+case+'/jobs/'+jid+'/recover',headers=auth)
    assert good.status_code==200,good.text
    assert good.json()['status']=='ready'

def test_model_query_must_include_subject_or_known_public_handle():
    assert agent.acceptable_query('Test Person software engineer','Test Person',{})
    assert not agent.acceptable_query('Research private person Mary Another','Test Person',{})
    assert agent.acceptable_query('known-public-handle company','Test Person',
                                  {'public_handle':'known-public-handle'})
    assert not agent.acceptable_query('http://127.0.0.1','Test Person',{})

def test_groq_job_enforces_remote_consent(client,auth,case,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','fake-test-key')
    assert client.post('/api/cases/'+case+'/jobs',headers=auth,json={
      'objective':'Explore authorized professional records for known public subject',
      'mode':'groq'}).status_code==409
    assert client.put('/api/cases/'+case+'/ai-consent',headers=auth,json={'enabled':True}).status_code==200
    r=client.post('/api/cases/'+case+'/jobs',headers=auth,json={
      'objective':'Explore authorized professional records for known public subject',
      'mode':'groq'})
    assert r.status_code==201
    assert r.json()['mode']=='groq'

def test_jobs_are_authorized_per_case_and_owner(client,auth,case):
    jid=client.post('/api/cases/'+case+'/jobs',headers=auth,json={
      'objective':'Check authorized professional public-source findings'}).json()['id']
    assert client.post('/api/users',headers=auth,json={
        'username':'someone-else','password':'AnotherStrongTestPassword012345',
        'role':'analyst'}).status_code==201
    client.post('/api/auth/logout',headers=auth)
    assert client.post('/api/auth/login',json={
      'username':'someone-else','password':'AnotherStrongTestPassword012345'}).status_code==200
    assert client.get('/api/cases/'+case+'/jobs').status_code==404
    assert client.get('/api/cases/'+case+'/jobs/'+jid).status_code==404
    assert client.post('/api/cases/'+case+'/jobs/'+jid+'/step',headers=auth).status_code==404

def seed_capture(client,auth,case):
    e=client.post('/api/cases/'+case+'/evidence',headers=auth,json={
      'label':'Public developer profile','summary':'Unverified public source for testing quote provenance',
      'source_url':'https://github.com/example-profile'})
    assert e.status_code==200
    eid=e.json()['id']
    text='Public repository documents experience developing authenticated applications with Python and FastAPI and associated developer tools.'
    cid='capture000000000000000000012'
    with db.connect() as c:
        c.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
          (cid,case,eid,'https://github.com/example-profile','text/plain',text,
           hashlib.sha256(text.encode()).hexdigest(),'2026-10-25T12:20:00Z','captured',''))
    return eid,cid,text

def test_excerpt_requires_verbatim_capture_and_correct_case(client,auth,case):
    eid,cid,source=seed_capture(client,auth,case)
    wrong=client.post('/api/cases/'+case+'/excerpts',headers=auth,json={
      'evidence_id':eid,'capture_id':cid,
      'quote_text':'This person is independently verified and works at a defense company.',
      'interpretation':'Evidence of independently verified credentials'})
    assert wrong.status_code==422,wrong.text
    quote='experience developing authenticated applications with Python and FastAPI'
    correct=client.post('/api/cases/'+case+'/excerpts',headers=auth,json={
      'evidence_id':eid,'capture_id':cid,'quote_text':quote,
      'interpretation':'This passage describes publicly presented technical experience'})
    assert correct.status_code==201,correct.text
    assert correct.json()['status']=='excerpt_matched'
    result=client.get('/api/cases/'+case+'/excerpts')
    assert result.status_code==200
    assert len(result.json()['items'])==1
    assert result.json()['items'][0]['captureIntegrityOk']
    assert result.json()['items'][0]['latestCaptureUnchanged']
    assert not result.json()['items'][0]['supportsTruth']

def test_excerpt_becomes_stale_after_source_recaptured(client,auth,case):
    eid,cid,text=seed_capture(client,auth,case)
    quote='experience developing authenticated applications with Python and FastAPI'
    resp=client.post('/api/cases/'+case+'/excerpts',headers=auth,json={
      'evidence_id':eid,'capture_id':cid,'quote_text':quote,
      'interpretation':'Historical developer profile passage recorded from public source'})
    assert resp.status_code==201
    with db.connect() as c:
        changed='New public profile no longer includes the older credentials text.'
        c.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
           ('new-capture-000000001',case,eid,'https://github.com/example-profile','text/plain',
            changed,hashlib.sha256(changed.encode()).hexdigest(),
            '2026-10-26T13:20:00Z','captured',''))
    refreshed=client.get('/api/cases/'+case+'/excerpts').json()['items'][0]
    assert not refreshed['latestCaptureUnchanged']

def test_excerpt_requires_capture_same_case(client,auth,case):
    eid,cid,text=seed_capture(client,auth,case)
    another=client.post('/api/cases',headers=auth,json={
      'title':'Another case for ownership checks','subject_type':'person',
      'query':'Second Subject','purpose':'Authorized public source attribution',
      'authority_confirmed':True}).json()['id']
    result=client.post('/api/cases/'+another+'/excerpts',headers=auth,json={
      'evidence_id':eid,'capture_id':cid,
      'quote_text':'experience developing authenticated applications with Python and FastAPI',
      'interpretation':'Attempted cross-case quotation must not be allowed'})
    assert result.status_code==422


def test_groq_proposal_is_validated_before_source_execution(monkeypatch):
    import asyncio
    from app import agent
    monkeypatch.setenv('GROQ_API_KEY','fake-never-sent-to-real-provider')
    class FakeResponse:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':json.dumps({
            'provider':'github','query':'Test Person ESTROC',
            'rationale':'Investigate published organizational identifiers'})}}]}
    class FakeClient:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,headers,json):
            assert url.startswith('https://api.groq.com/')
            assert 'allowedProviders' in json['messages'][1]['content']
            return FakeResponse()
    monkeypatch.setattr(agent.httpx,'AsyncClient',FakeClient)
    case={'id':'case-example','query':'Test Person','subject_type':'person'}
    context={'city':'Delhi','organization':'ESTROC','public_handle':''}
    job={'id':'job-example','objective':'Find public professional accounts',
         'mode':'groq','allow_web':0}
    result=asyncio.run(agent.ai_proposed_step(case,context,job,[],{'github','stackoverflow'}))
    assert result['provider']=='github'
    assert result['query']=='Test Person ESTROC'
    assert 'Investigate' in result['rationale']


def test_model_cannot_choose_unauthorized_provider_or_unrelated_person(monkeypatch):
    import asyncio
    from app import agent
    monkeypatch.setenv('GROQ_API_KEY','synthetic-key')
    answer={'provider':'arbitrary-network-scanner','query':'Test Person',
            'rationale':'Not allowlisted'}
    class FakeResponse:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':json.dumps(answer)}}]}
    class FakeClient:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):return FakeResponse()
    monkeypatch.setattr(agent.httpx,'AsyncClient',FakeClient)
    case={'id':'example','query':'Test Person','subject_type':'person'}
    job={'id':'example','objective':'Verify public professional accounts','mode':'groq','allow_web':0}
    assert asyncio.run(agent.ai_proposed_step(case,{},job,[],{'github'})) is None
    answer['provider']='github'
    answer['query']='Unrelated Person private details'
    assert asyncio.run(agent.ai_proposed_step(case,{},job,[],{'github'})) is None
