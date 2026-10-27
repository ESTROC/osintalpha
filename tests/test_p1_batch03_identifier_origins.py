"""Typed source identifiers must be verified against appropriate public host."""
def test_057_username_cannot_be_attributed_to_nonmatching_profile(client,auth,case):
    public=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
      'label':'Invented profile','summary':'Source claims profile',
      'source_url':'https://example.org/not-a-github-user'})
    assert public.status_code==200,public.text
    pid=client.post(f'/api/cases/{case}/candidates',headers=auth,json={
       'display_name':'Example Alias'}).json()['id']
    r=client.post(f'/api/cases/{case}/public-identifiers',headers=auth,json={
       'profile_id':pid,'evidence_id':public.json()['id'],
       'kind':'github_handle','value':'demo-profile',
       'source_url':'https://example.org/not-a-github-user'})
    assert r.status_code==422
    assert 'GitHub' in r.json()['detail']
