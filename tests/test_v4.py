"""End-to-end API regressions for the V4 analyst research workflow.

External APIs are mocked to avoid confusing CI with evidence of real-world source availability.
"""
from app import db
from app import main as core
from app.connectors import Evidence

def test_v4_schema_is_migrated(client,auth):
    with db.connect() as c:
        for table in ('research_queries','candidate_profiles','candidate_evidence','case_assessments'):
            assert c.execute('SELECT count(*) n FROM '+table).fetchone()['n']==0

def test_plan_uses_subject_clues(client,auth,case):
    body={'city':'Delhi','organization':'ESTROC','profession':'software engineer',
          'public_handle':'ayush_example'}
    assert client.put('/api/cases/'+case+'/context',headers=auth,json=body).status_code==200
    result=client.get('/api/cases/'+case+'/research-plan?depth=thorough')
    assert result.status_code==200,result.text
    queries=result.json()['queries']
    assert any(q['provider']=='github' and q['query']=='ayush_example' for q in queries)
    assert any(q['provider']=='gdelt' and 'ESTROC' in q['query'] for q in queries)
    assert len(queries)<=12

def test_bounded_research_persists_provider_queries(client,auth,case,monkeypatch):
    invocations=[]
    async def fake(provider,query,kind,client=None):
        invocations.append((provider,query))
        return [Evidence(query+' candidate','Public profile; no verified identity',
              'https://example.org/'+provider,provider+'-'+query,
              {'bio':'Research candidate','location':'Delhi'})]
    monkeypatch.setattr(core,'collect_one',fake)
    assert client.put('/api/cases/'+case+'/context',headers=auth,json={'organization':'ESTROC'}).status_code==200
    result=client.post('/api/cases/'+case+'/research',headers=auth,
                       json={'depth':'standard','providers':['github','gdelt']})
    assert result.status_code==200,result.text
    x=result.json()
    assert x['attempted']>=3 and x['returned']==len(invocations)
    history=client.get('/api/cases/'+case+'/research-history').json()['items']
    assert len(history)==len(invocations)
    assert any('ESTROC' in q['query_text'] for q in history)
    assert all(q['returned_count']==1 for q in history)
    assert x['new']==len(client.get('/api/cases/'+case).json()['evidence'])

def test_research_handles_provider_error_and_no_silent_empty(client,auth,case,monkeypatch):
    async def fake(provider,query,kind,client=None):
        if provider=='github':raise RuntimeError('provider quota exhausted')
        return []
    monkeypatch.setattr(core,'collect_one',fake)
    r=client.post('/api/cases/'+case+'/research',headers=auth,
                  json={'depth':'quick','providers':['github','stackoverflow']})
    assert r.status_code==200
    results=r.json()['queries']
    assert any(x['status']=='error' for x in results)
    assert any(x['status']=='empty' for x in results)
    assert r.json()['new']==0
    assert all('query' in x for x in results)

def seed_evidence(client,auth,case,label='Public developer profile'):
    return client.post('/api/cases/'+case+'/evidence',headers=auth,json={
      'label':label,'summary':'Sample publicly attributable candidate; identity unresolved',
      'source_url':'https://github.com/example'}).json()['id']

def test_candidate_groups_require_provenance(client,auth,case):
    evidence=seed_evidence(client,auth,case)
    created=client.post('/api/cases/'+case+'/candidates',headers=auth,json={
       'display_name':'Test Person (developer)','reason':'Public profile candidate'})
    assert created.status_code==201,created.text
    cid=created.json()['id']
    assert client.post('/api/cases/'+case+'/candidates/'+cid+'/sources',headers=auth,
                       json={'evidence_id':evidence,'rationale':'Public profile link'}).status_code==201
    x=client.get('/api/cases/'+case+'/candidates').json()['items'][0]
    assert x['classification']=='unresolved'
    assert x['sources'][0]['evidence_id']==evidence
    insufficient=client.patch('/api/cases/'+case+'/candidates/'+cid,headers=auth,
      json={'classification':'confirmed_by_analyst','reason':'yes'})
    assert insufficient.status_code==422
    reviewed=client.patch('/api/cases/'+case+'/candidates/'+cid,headers=auth,
      json={'classification':'excluded','reason':'Different public employer and location'})
    assert reviewed.status_code==200
    assert client.get('/api/cases/'+case+'/candidates').json()['items'][0]['classification']=='excluded'

def test_candidate_rejects_cross_case_evidence(client,auth,case):
    target=client.post('/api/cases',headers=auth,json={'title':'Other valid case','subject_type':'person',
      'query':'Other Person','purpose':'Authorized identity research of public example',
      'authority_confirmed':True}).json()['id']
    evidence=seed_evidence(client,auth,target)
    cid=client.post('/api/cases/'+case+'/candidates',headers=auth,
      json={'display_name':'Possible namesake'}).json()['id']
    r=client.post('/api/cases/'+case+'/candidates/'+cid+'/sources',headers=auth,
      json={'evidence_id':evidence})
    assert r.status_code==422

def test_bulk_review_requires_causal_notes_and_ownership(client,auth,case):
    a=seed_evidence(client,auth,case)
    no_reason=client.post('/api/cases/'+case+'/evidence/bulk-review',headers=auth,json={
      'evidence_ids':[a],'status':'rejected','notes':'no'})
    assert no_reason.status_code==422
    success=client.post('/api/cases/'+case+'/evidence/bulk-review',headers=auth,json={
      'evidence_ids':[a],'status':'rejected','notes':'Namesake associated with a different field'})
    assert success.status_code==200
    assert client.get('/api/cases/'+case).json()['evidence'][0]['status']=='rejected'

def test_assessment_with_claims_and_report(client,auth,case):
    evidence=seed_evidence(client,auth,case)
    link=client.post('/api/cases/'+case+'/claims',headers=auth,json={
      'evidence_id':evidence,
      'claim_text':'A developer profile with this display name was found.',
      'stance':'context'})
    assert link.status_code==201
    payload={'executive_summary':'Several records share a display name, but identity remains unresolved.',
             'assessment':'The available public source does not establish identity. Compare employers and handles.',
             'limitations':'No independent account ownership verification was performed.',
             'next_actions':'Check the original publisher and ask for an existing public handle.',
             'status':'completed'}
    saved=client.put('/api/cases/'+case+'/assessment',headers=auth,json=payload)
    assert saved.status_code==200,saved.text
    intel=client.get('/api/cases/'+case+'/intelligence')
    assert intel.status_code==200
    assert intel.json()['claims'][0]['stance']=='context'
    assert intel.json()['assessment']['status']=='completed'
    report=client.get('/api/cases/'+case+'/report-v4.html')
    assert report.status_code==200
    assert 'Several records share' in report.text
    assert 'A developer profile with this display name' in report.text
    assert 'No independent account ownership verification' in report.text
    pdf=client.get('/api/cases/'+case+'/report-v4.pdf')
    assert pdf.status_code==200,pdf.text[:200] if pdf.status_code!=200 else ''
    assert pdf.content.startswith(b'%PDF')

def test_completion_requires_substantive_assessment(client,auth,case):
    bad=client.put('/api/cases/'+case+'/assessment',headers=auth,json={
      'executive_summary':'No','assessment':'No','status':'completed'})
    assert bad.status_code==422
    assert client.get('/api/cases/'+case+'/assessment').json()['status']=='open'

def test_case_permissions_restrict_research_and_assessments(client,auth,case):
    client.post('/api/users',headers=auth,json={'username':'otheranalyst',
       'password':'AnEntirelyDifferentPassword123','role':'analyst'})
    client.post('/api/auth/logout',headers=auth)
    assert client.post('/api/auth/login',json={'username':'otheranalyst',
       'password':'AnEntirelyDifferentPassword123'}).status_code==200
    assert client.get('/api/cases/'+case+'/research-plan').status_code==404
    assert client.post('/api/cases/'+case+'/research',headers=auth,json={}).status_code==404
    assert client.get('/api/cases/'+case+'/candidates').status_code==404
    assert client.get('/api/cases/'+case+'/intelligence').status_code==404
    assert client.get('/api/cases/'+case+'/report-v4.html').status_code==404
