"""Public health endpoint exposes nonsecret revision only if platform provided it."""
def test_public_health_no_invented_sha(client,monkeypatch):
    monkeypatch.delenv('RENDER_GIT_COMMIT',raising=False)
    res=client.get('/api/health')
    assert res.status_code==200,res.text
    assert res.json()['ok']
    assert res.json()['revision'] is None

def test_public_health_revision_metadata_is_validated(client,monkeypatch):
    rev='f'*40
    monkeypatch.setenv('RENDER_GIT_COMMIT',rev)
    assert client.get('/api/health').json()['revision']==rev
    monkeypatch.setenv('RENDER_GIT_COMMIT','invalid-user-string')
    assert client.get('/api/health').json()['revision'] is None
