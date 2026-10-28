"""P3-145/146 compare authorized reviewed public sources and case-scoped partial task state."""
def test_cross_case_comparison_requires_both_access(client,auth,case):
    r=client.post('/api/cases',headers=auth,json={
        'title':'Second synthetic organization case','subject_type':'organization',
        'query':'Public Example Institute','purpose':'Public synthetic comparisons with explicit authorization',
        'authority_confirmed':True})
    assert r.status_code==201,r.text
    second=r.json()['id']
    compared=client.get(f'/api/agency/compare-reviewed?left={case}&right={second}')
    assert compared.status_code==200,compared.text
    assert compared.json()['left']['reviewedClaims']==[]
    assert not compared.json()['twoCasesRepresentSameSubjectVerified']
    assert client.get(f'/api/agency/compare-reviewed?left={case}&right=not-a-case').status_code==404
    assert client.get(f'/api/agency/compare-reviewed?left={case}&right={case}').status_code==422

def test_safe_batch_partial_errors_no_bulk_completion(client,auth,case):
    r=client.post(f'/api/cases/{case}/tasks',headers=auth,json={
      'title':'Review published source','description':'Synthetic public source review',
      'priority':'normal'})
    assert r.status_code==201,r.text
    tid=r.json()['id']
    url=f'/api/cases/{case}/tasks/safe-batch'
    payload={'ids':[tid,'not-a-task'],'status':'awaiting_review',
      'note':'Analyst may review this task but must close with individual source evidence.',
      'execute':False}
    preview=client.post(url,headers=auth,json=payload)
    assert preview.status_code==200,preview.text
    assert preview.json()['updatedCount']==0 and len(preview.json()['rejected'])==1
    payload['execute']=True
    updated=client.post(url,headers=auth,json=payload)
    assert updated.status_code==200,updated.text
    assert updated.json()['updatedCount']==1 and len(updated.json()['rejected'])==1
    assert client.post(url,headers=auth,json={**payload,'status':'done'}).status_code==422
    history=client.get(f'/api/cases/{case}/tasks/{tid}/history')
    assert history.status_code==200
    assert any(x['new_status']=='awaiting_review' for x in history.json()['items'])
