"""P3 145–146 cross-case authorization, opt-in comparison and batch-task safety."""
from app import db

def test_case_compare_only_authorized_stored_reviewed_claims(client,auth,case):
    created=client.post('/api/cases',headers=auth,json={
       'title':'Separate synthetic work','subject_type':'person','query':'Different Subject',
       'purpose':'Authorized public source comparison between two synthetic investigations',
       'authority_confirmed':True})
    assert created.status_code==201,created.text
    other=created.json()['id']
    out=client.get('/api/agency/reviewed-case-compare?left='+case+'&right='+other)
    assert out.status_code==200,out.text
    assert out.json()['left']['reviewedClaims']==[]
    assert not out.json()['identitiesMerged']
    assert client.get('/api/agency/reviewed-case-compare?left='+case+'&right=missing-case').status_code==404

def test_batch_review_preview_fails_safe_for_unknown_id(client,auth,case):
    p=client.post(f'/api/cases/{case}/tasks/batch-preview',headers=auth,json={
      'ids':['not-in-this-case'],'status':'blocked'})
    assert p.status_code==200,p.text
    assert p.json()['canApply'] is False
    assert p.json()['rejectedCount']==1
    assert p.json()['mutationsPerformed']==0
    denied=client.post(f'/api/cases/{case}/tasks/batch-preview',headers=auth,json={
      'ids':['not-in-this-case'],'status':'done'})
    assert denied.status_code==422
