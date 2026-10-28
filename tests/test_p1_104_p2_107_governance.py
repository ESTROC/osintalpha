"""P1-104/P2-107: never invent commercial rights or national registry coverage."""
def test_default_provider_governance_is_unapproved(client,auth):
    out=client.get('/api/research/provider-governance')
    assert out.status_code==200,out.text
    assert out.json()['items']
    assert all(p['rightsStatus']=='not_reviewed' for p in out.json()['items'])
    assert all(p['coverageVerified'] is False for p in out.json()['items'])

def test_admin_review_rejects_unapproved_claimed_permissions(client,auth):
    body={'status':'restricted','permitted_uses':['store_excerpt'],
      'terms_url':'https://docs.github.com/en/site-policy/github-terms/github-terms-of-service',
      'reviewer_note':'Synthetic access review only; no independent legal approval or contractual license is claimed.'}
    a=client.put('/api/research/provider-governance/github',headers=auth,json=body)
    assert a.status_code==422
    body['permitted_uses']=[]
    a=client.put('/api/research/provider-governance/github',headers=auth,json=body)
    assert a.status_code==200,a.text
    assert a.json()['contractualPermissionExternallyVerified'] is False
    result=client.get('/api/research/provider-governance')
    assert next(x for x in result.json()['items'] if x['id']=='github')['rightsStatus']=='restricted'
