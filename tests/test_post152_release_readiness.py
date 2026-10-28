"""Post-152 no-go release status is private, conservative, and secret-free."""
def test_release_gate_is_not_regulatory_acceptance(client,auth,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','FAKE_SECRET_VALUE_NOT_LEAKED')
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','FAKE_SEARCH_SECRET_NOT_LEAKED')
    r=client.get('/api/admin/release-readiness')
    assert r.status_code==200,r.text
    data=r.json()
    assert data['productionApproved'] is False
    assert data['all152IndependentlyAccepted'] is False
    assert data['configuration']['databaseBackupVerified'] is False
    assert len(data['gates'])==10
    assert all(not x['independentlyCertified'] for x in data['gates'])
    assert all(x['state']!='approved' for x in data['gates'])
    assert r.headers.get('cache-control')=='no-store'
    assert 'FAKE_SECRET_VALUE_NOT_LEAKED' not in r.text
    assert 'FAKE_SEARCH_SECRET_NOT_LEAKED' not in r.text

def test_release_gate_requires_auth(client,auth):
    assert client.get('/api/admin/release-readiness').status_code==200
    r=client.post('/api/auth/logout',headers=auth)
    assert r.status_code==200,r.text
    assert client.get('/api/admin/release-readiness').status_code==401
