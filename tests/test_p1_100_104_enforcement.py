"""P1-100/104 fail-closed enterprise MFA policy and explicit provider restrictions."""
from app import db
from app.connectors import collect_one,AdapterError
import asyncio,pytest

def test_enterprise_auth_mode_refuses_password_only_login(client,monkeypatch):
    monkeypatch.setenv('OSINTALPHA_REQUIRE_MFA','1')
    r=client.post('/api/auth/login',json={
      'username':'admin','password':'AnIntentionallyLongTestPassword123'})
    assert r.status_code==503
    assert 'MFA' in r.text

def test_explicitly_restricted_provider_fails_before_request(client,auth):
    from app.main import actor_from_cookie
    r=client.put('/api/research/provider-governance/github',headers=auth,json={
       'status':'restricted','permitted_uses':[],
       'terms_url':'https://docs.github.com/en/site-policy/github-terms/github-terms-of-service',
       'reviewer_note':'Synthetic source restriction entered by administrator to test fail-closed behavior.'})
    assert r.status_code==200,r.text
    with pytest.raises(AdapterError,match='blocked'):
        asyncio.run(collect_one('github','public synthetic profile','person'))
