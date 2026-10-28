"""P1 067: link rot returns observed status, not invented disappearance."""
import pytest
from app.source_link_health import classify_http

@pytest.mark.parametrize('status,expected',[
 (200,'responding'),(404,'source_not_found_on_this_check'),
 (410,'source_not_found_on_this_check'),(403,'access_or_method_restricted'),
 (429,'access_or_method_restricted'),(302,'redirect_not_followed'),
 (503,'server_error_not_source_absence')])
def test_link_status_taxonomy(status,expected):
    assert classify_http(status)==expected

def test_disallowed_url_never_probed(client,auth,case):
    r=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'Untrusted arbitrary public url','summary':'Public arbitrary source',
        'source_url':'https://example.org/not-allowlisted'})
    eid=r.json()['id']
    response=client.post(f'/api/cases/{case}/evidence/{eid}/check-url',headers=auth)
    assert response.status_code==422
    check=client.get(f'/api/cases/{case}/evidence/{eid}/link-checks')
    assert check.status_code==200
    assert check.json()['items']==[]

def test_head_only_and_no_redirect_follow(client,auth,case,monkeypatch):
    from app import source_link_health
    calls=[]
    class FakeResponse:
        status_code=404
    class FakeClient:
        def __init__(self,*args,**kwargs):
            assert kwargs.get('follow_redirects') is False
            assert kwargs.get('trust_env') is False
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def head(self,url,headers=None):
            calls.append(url)
            return FakeResponse()
    monkeypatch.setattr(source_link_health.httpx,'AsyncClient',FakeClient)
    e=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
       'label':'Github public test page','summary':'Stored publisher page',
       'source_url':'https://github.com/example/example'}).json()['id']
    r=client.post(f'/api/cases/{case}/evidence/{e}/check-url',headers=auth)
    assert r.status_code==200,r.text
    assert calls==['https://github.com/example/example']
    assert r.json()['checkState']=='source_not_found_on_this_check'
    assert r.json()['sourceDeletedProven'] is False
