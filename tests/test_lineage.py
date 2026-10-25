"""Full source-version lineage and run-difference regression coverage.

All providers are deterministic fakes. Passing these tests validates version
handling, not accuracy or completeness of real public-source intelligence.
"""
from app import db,main
from app.connectors import Evidence

def adapter(state):
    async def fake(provider,query,kind,client):
        if state.get('empty'):return []
        return [Evidence('Public software profile',
           'Company and location as published by public source',
           'https://github.com/example-researcher','stable-profile-120',
           {'login':'example-researcher','location':'Delhi','company':state['company'],'bio':'Software engineer'})]
    return fake

def test_source_versions_are_recorded_and_no_change_does_not_reset_review(client,auth,case,monkeypatch):
    value={'company':'Company A'}
    monkeypatch.setattr(main,'collect_one',adapter(value))
    def research():
        res=client.post('/api/cases/'+case+'/research',headers=auth,json={'providers':['github'],'depth':'quick'})
        assert res.status_code==200,res.text
        return res.json()
    first=research()
    assert first['new']==1 and first['changed']==0
    evidence=client.get('/api/cases/'+case).json()['evidence'][0]
    eid=evidence['id']
    reviewed=client.patch('/api/evidence/'+eid,headers=auth,json={
      'status':'corroborated','reviewer_notes':'I reviewed this source record and its original public page.'})
    assert reviewed.status_code==200
    second=research()
    assert second['new']==0 and second['changed']==0
    assert client.get('/api/cases/'+case).json()['evidence'][0]['status']=='corroborated'
    value['company']='Company B'
    third=research()
    assert third['new']==0 and third['changed']==1
    new=client.get('/api/cases/'+case).json()['evidence'][0]
    assert new['id']==eid and new['status']=='candidate'
    versions=client.get('/api/cases/'+case+'/evidence/'+eid+'/versions')
    assert versions.status_code==200
    assert len(versions.json()['items'])==3
    hashes={x['content_sha256'] for x in versions.json()['items']}
    assert len(hashes)==2
    assert any(x['disposition']=='changed' for x in versions.json()['items'])
    with db.connect() as c:
        audit=[dict(x) for x in c.execute('SELECT old_status,new_status,rationale FROM review_decisions WHERE evidence_id=?',(eid,))]
    assert any(x['old_status']=='corroborated' and x['new_status']=='candidate' for x in audit)
    diff=client.get('/api/cases/'+case+'/changes',params={
      'run_id':third['runId'],'against':second['runId']})
    assert diff.status_code==200,diff.text
    result=diff.json()
    assert result['comparedSameQueryScope']
    assert result['summary']=={'changed':1}
    assert result['items'][0]['previousSummary']
    assert result['items'][0]['change']=='changed'

def test_not_returned_is_not_misrepresented_as_deleted(client,auth,case,monkeypatch):
    state={'company':'A','empty':False}
    monkeypatch.setattr(main,'collect_one',adapter(state))
    one=client.post('/api/cases/'+case+'/research',headers=auth,json={'providers':['github']}).json()
    state['empty']=True
    two=client.post('/api/cases/'+case+'/research',headers=auth,json={'providers':['github']}).json()
    diff=client.get('/api/cases/'+case+'/changes',params={'run_id':two['runId'],'against':one['runId']})
    assert diff.status_code==200
    obj=diff.json()
    assert obj['summary']=={'not_returned':1}
    assert 'does NOT establish deletion' in obj['warning']
    assert len(client.get('/api/cases/'+case).json()['evidence'])==1

def test_existing_legacy_record_is_preserved_before_update(client,auth,case,monkeypatch):
    # Seed through the older ingestion route, then emulate the first V6 observation.
    with db.connect() as c:
        c.execute("""INSERT INTO evidence
        (id,case_id,provider,label,summary,source_url,source_ref,fetched_at,
         sha256,raw_json) VALUES (?,?,?,?,?,?,?,?,?,?)""",
         ('legacy00000000000000000001',case,'github','Previous public profile','Old employment details',
          'https://github.com/example-researcher','stable-profile-120','2026-10-20T10:00:00Z',
          'historical-sha','{"company":"Old Employer"}'))
    state={'company':'New Employer'}
    monkeypatch.setattr(main,'collect_one',adapter(state))
    response=client.post('/api/cases/'+case+'/research',headers=auth,json={'providers':['github']})
    assert response.status_code==200,response.text
    versions=client.get('/api/cases/'+case+'/evidence/legacy00000000000000000001/versions').json()['items']
    assert len(versions)==2
    assert any(v['disposition']=='historical' and v['summary']=='Old employment details' for v in versions)

def test_legacy_collect_endpoint_also_writes_versioned_runs(client,auth,case,monkeypatch):
    monkeypatch.setattr(main,'collect_one',adapter({'company':'Example Ltd'}))
    r=client.post('/api/cases/'+case+'/collect',headers=auth,json={'providers':['github']})
    assert r.status_code==200,r.text
    assert r.json()['results'][0]['new']==1
    runs=client.get('/api/cases/'+case+'/changes').json()['runs']
    assert len(runs)==1
    assert runs[0]['query_count']==1

def test_other_analyst_cannot_open_versions_or_compare_runs(client,auth,case,monkeypatch):
    monkeypatch.setattr(main,'collect_one',adapter({'company':'Example Ltd'}))
    client.post('/api/cases/'+case+'/research',headers=auth,json={'providers':['github']})
    eid=client.get('/api/cases/'+case).json()['evidence'][0]['id']
    result=client.post('/api/users',headers=auth,json={
        'username':'unrelateduser','password':'UniqueLongTestPassword123456','role':'analyst'})
    assert result.status_code==201
    client.post('/api/auth/logout',headers=auth)
    assert client.post('/api/auth/login',json={'username':'unrelateduser',
        'password':'UniqueLongTestPassword123456'}).status_code==200
    assert client.get('/api/cases/'+case+'/changes').status_code==404
    assert client.get('/api/cases/'+case+'/evidence/'+eid+'/versions').status_code==404

def test_comparison_rejects_nonexistent_run(client,auth,case):
    r=client.get('/api/cases/'+case+'/changes',params={'run_id':'nonexistent'})
    assert r.status_code==404
