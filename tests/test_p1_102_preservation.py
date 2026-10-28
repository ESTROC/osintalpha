"""P1 102 explicit administrator preservation decisions; hold blocks manual removal."""
def test_preservation_hold_enforced(client,auth,case):
    url=f'/api/cases/{case}/preservation'
    p=client.put(url,headers=auth,json={'review_in_days':30,'legal_hold':True,
     'rationale':'Preserve this synthetic record for evidence and policy review.'})
    assert p.status_code==200,p.text
    assert client.get(url).json()['policy']['legal_hold']==1
    assert client.delete(f'/api/cases/{case}',headers=auth).status_code==409
    assert client.get(f'/api/cases/{case}').status_code==200
    assert client.get('/api/admin/preservation/review-due').status_code==200

def test_invalid_hold_release_requires_review(client,auth,case):
    url=f'/api/cases/{case}/preservation'
    assert client.put(url,headers=auth,json={'review_in_days':30,'legal_hold':True,
        'rationale':'An authorization record for this synthetic hold.'}).status_code==200
    rejected=client.put(url,headers=auth,json={'review_in_days':30,
       'legal_hold':False,'rationale':'A short release reason does not suffice.'})
    assert rejected.status_code==422
    assert client.get(url).json()['policy']['legal_hold']==1
