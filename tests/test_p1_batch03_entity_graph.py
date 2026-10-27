"""P1 053–058: typed identifier integrity and person-name non-merging."""
import pytest
from app.entity_graph import normalize,graph

def test_054_normalization_and_checksum():
    assert normalize('orcid','0000-0002-1825-0097')=='0000-0002-1825-0097'
    with pytest.raises(ValueError):normalize('orcid','0000-0002-1825-0098')
    assert normalize('github_handle','Demo-Org')=='demo-org'
    with pytest.raises(ValueError):normalize('github_handle','fake/handle')
    with pytest.raises(ValueError):normalize('public_org_registration','hi')
    with pytest.raises(ValueError):normalize('email','private@example.org')

def test_053_055_056_source_links_and_nonmerged_public_graph(client,auth,case):
    a=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
       'label':'Profile one','summary':'Unverified public developer profile',
       'source_url':'https://github.com/first-public-lead'})
    assert a.status_code==200,a.text
    id_a=a.json()['id']
    names=[]
    for n in ('Alex Example','Alex Example'):
        x=client.post(f'/api/cases/{case}/candidates',headers=auth,json={
           'display_name':n,'reason':'Synthetic candidate for namesake comparison'})
        assert x.status_code==201,x.text
        names.append(x.json()['id'])
    for pid in names:
        add=client.post(f'/api/cases/{case}/public-identifiers',headers=auth,json={
            'profile_id':pid,'evidence_id':id_a,
            'kind':'github_handle','value':'first-public-lead',
            'source_url':'https://github.com/first-public-lead'})
        assert add.status_code==201,add.text
        assert not add.json()['personIdentityVerified']
    result=client.get(f'/api/cases/{case}/candidate-graph')
    assert result.status_code==200,result.text
    data=result.json()
    assert len(data['candidates'])==2
    assert len(data['sharedIdentifierHypotheses'])==1
    assert data['sharedIdentifierHypotheses'][0]['autoMerge'] is False
    assert data['relationshipsVerified'] is False
    assert client.get('/api/cases/not-found/candidate-graph').status_code==404

def test_057_058_public_linkedin_not_official_employment_verification(client,auth,case):
    r=client.get(f'/api/cases/{case}/linkedin-index-notice')
    assert r.status_code==200,r.text
    assert not r.json()['linkedinMemberOAuthIntegrated']
    assert not r.json()['privateResumeDataAvailable']
