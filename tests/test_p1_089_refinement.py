"""P1-089 same-case analyst refinements preserve the original objective."""
def test_refine_known_candidate_without_new_case(client,auth,case):
    candidate=client.post(f'/api/cases/{case}/candidates',headers=auth,
       json={'display_name':'Alex Example','reason':'Separate source hypothesis'})
    assert candidate.status_code==201,candidate.text
    payload={'candidate_id':candidate.json()['id'],'clue_kind':'public_organization',
       'clue_value':'Open Research Lab','rationale':'Public conference lists this organization as possible affiliation',
       'consent':False}
    path=f'/api/cases/{case}/candidate-refinements'
    assert client.post(path,headers=auth,json=payload).status_code==422
    payload['consent']=True
    r=client.post(path,headers=auth,json=payload)
    assert r.status_code==201,r.text
    assert not r.json()['externalCallsMade']
    assert 'Alex Example' in r.json()['query']
    results=client.get(path)
    assert results.status_code==200
    assert results.json()['items'][0]['candidate_id']==candidate.json()['id']
    assert not results.json()['identityVerified']

def test_refine_cross_case_rejected(client,auth,case):
    body={'candidate_id':'candidate-outside-case','clue_kind':'public_city',
      'clue_value':'New Delhi','rationale':'Sourced approximate public city only','consent':True}
    assert client.post(f'/api/cases/{case}/candidate-refinements',headers=auth,json=body).status_code==422
