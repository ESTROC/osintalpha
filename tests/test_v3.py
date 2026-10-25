"""V3 regression: users, access isolation, persisted chats, source runs and ranking."""
import os
import json
from app import db

def test_v3_database_tables(client,auth):
    with db.connect() as c:
        for table in ['users','sessions','cases','evidence','case_context',
                      'research_sessions','research_messages','search_history','claim_links']:
            assert c.execute("SELECT count(*) n FROM "+table).fetchone()['n']>=0
    r=client.get('/api/health')
    assert r.json()['version']=='4.0.0'

def test_case_context_and_candidate_triage(client,auth,case):
    assert client.put('/api/cases/'+case+'/context',headers=auth,json={
       'city':'Delhi','organization':'ESTROC','profession':'software engineer',
       'public_handle':'estroctech'}).status_code==200
    triage=client.get('/api/cases/'+case+'/triage')
    assert triage.status_code==200
    d=triage.json()
    assert d['hasDisambiguationClues'] is True
    assert d['clues']['city']=='Delhi'
    assert d['candidates']==[]
    assert 'not automatically verified' in d['notice']

def test_chat_history_survives_new_request(client,auth,case):
    first=client.post('/api/cases/'+case+'/chat',headers=auth,json={
        'provider':'local','question':'hi'})
    assert first.status_code==200,first.text
    sid=first.json()['sessionId']
    assert len(sid)>10
    second=client.post('/api/cases/'+case+'/chat',headers=auth,json={
        'provider':'local','question':'Who is Test Person?','session_id':sid,
        'history':[{'role':'user','content':'hi'}]})
    assert second.status_code==200,second.text
    assert second.json()['sessionId']==sid
    chats=client.get('/api/cases/'+case+'/conversations').json()['items']
    assert len(chats)==1
    messages=client.get('/api/cases/'+case+'/conversations/'+sid).json()['messages']
    assert [m['role'] for m in messages]==['user','assistant','user','assistant']
    assert messages[0]['text']=='hi'
    assert messages[-1]['provider']=='local'

def test_different_chat_session_requires_ownership(client,auth,case):
    sid='f'*24
    assert client.post('/api/cases/'+case+'/chat',headers=auth,json={
        'provider':'local','question':'hi','session_id':sid}).status_code==404
    assert client.get('/api/cases/'+case+'/conversations/'+sid).status_code==404

def test_search_history_and_claim_provenance(client,auth,case,monkeypatch):
    from app import main
    from app.connectors import Evidence
    async def provider(*args,**kwargs):
        return [Evidence('Candidate Profile','Public professional profile lists Delhi and engineering',
              'https://example.com/profile','profile-1',
              {'location':'Delhi','bio':'software engineer','login':'sample'})]
    monkeypatch.setattr(main,'collect_one',provider)
    result=client.post('/api/cases/'+case+'/collect',headers=auth,json={'providers':['github']})
    assert result.status_code==200,result.text
    history=client.get('/api/cases/'+case+'/search-history').json()['items']
    assert len(history)==1
    assert history[0]['results_count']==1
    evid=client.get('/api/cases/'+case).json()['evidence'][0]
    triage=client.get('/api/cases/'+case+'/triage').json()['candidates']
    assert triage and triage[0]['relevance']>=0
    claim=client.post('/api/cases/'+case+'/claims',headers=auth,json={
        'evidence_id':evid['id'],'claim_text':'This public candidate lists Delhi.',
        'stance':'supports'})
    assert claim.status_code==201,claim.text
    claims=client.get('/api/cases/'+case+'/claims').json()['items']
    assert len(claims)==1 and claims[0]['label']=='Candidate Profile'
    assert client.post('/api/cases/'+case+'/claims',headers=auth,json={
        'evidence_id':'invalid','claim_text':'A claim without a source must fail'}).status_code==422

def test_admin_create_analyst_and_case_isolation(client,auth,case):
    response=client.post('/api/users',headers=auth,json={
        'username':'analyst1','password':'DistinctStrongAccountPass123',
        'role':'analyst'})
    assert response.status_code==201,response.text
    assert len(client.get('/api/users').json()['items'])==2
    client.post('/api/auth/logout',headers=auth)
    login=client.post('/api/auth/login',json={
        'username':'analyst1','password':'DistinctStrongAccountPass123'})
    assert login.status_code==200,login.text
    assert client.get('/api/users').status_code==403
    assert client.get('/api/cases').json()['items']==[]
    assert client.get('/api/cases/'+case).status_code==404
    assert client.get('/api/cases/'+case+'/triage').status_code==404
    assert client.get('/api/cases/'+case+'/report.json').status_code==404
    assert client.get('/api/cases/'+case+'/conversations').status_code==404
    assert client.post('/api/cases/'+case+'/chat',headers=auth,json={
        'question':'hello','provider':'local'}).status_code==404
    assert client.post('/api/cases/'+case+'/collect',headers=auth,json={
        'providers':['github']}).status_code==404
    own=client.post('/api/cases',headers=auth,json={
        'title':'Analyst own research','subject_type':'person','query':'Example Name',
        'purpose':'Authorized example identity verification','authority_confirmed':True})
    assert own.status_code==201,own.text
    assert len(client.get('/api/cases').json()['items'])==1
    assert client.get('/api/overview').json()['cases']==1

def test_no_automatic_identity_merge(client,auth,case):
    r=client.get('/api/cases/'+case+'/triage')
    assert r.status_code==200
    assert r.json()['candidates']==[]
    assert 'not automatically verified' in r.json()['notice']

def test_duplicate_account_rejected(client,auth):
    body={'username':'analyst_unique','password':'StrongPasswordForTests123'}
    assert client.post('/api/users',headers=auth,json=body).status_code==201
    assert client.post('/api/users',headers=auth,json=body).status_code==409
