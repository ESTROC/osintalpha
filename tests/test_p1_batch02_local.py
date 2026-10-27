"""P1 039–043: sourced local candidates, registry limitations, language variants."""
from app.local_discovery import bounded_alias_queries,occupation_routes,REGISTRY_REFERENCE

def test_039_business_candidate_does_not_create_address_or_registration(client,auth):
    case=client.post('/api/cases',headers=auth,json={
        'title':'Registered regional company','subject_type':'organization',
        'query':'Example Regional Company','purpose':'Review public business records',
        'authority_confirmed':True}).json()['id']
    e=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'Example Regional Company','summary':'Public source mentions manufacturing',
        'source_url':'https://example.org/public-source'})
    assert e.status_code==200,e.text
    r=client.get(f'/api/cases/{case}/business-leads')
    assert r.status_code==200,r.text
    item=r.json()['items'][0]
    assert item['physicalAddress'] is None
    assert item['registrationId'] is None
    assert not item['officialRecordConfirmed']
    assert r.json()['licensedPoiApiIntegrated'] is False

def test_040_mca_gst_are_manual_reference_not_live_api():
    assert len(REGISTRY_REFERENCE)==2
    assert all(not x['verifiedIntegratedAPI'] for x in REGISTRY_REFERENCE)
    assert all(x['link'].startswith('https://') for x in REGISTRY_REFERENCE)

def test_041_042_explicit_sourced_transliteration_not_auto_asserted():
    a=[{'alias':'आयुष त्रिपाठी','alias_type':'transliteration',
        'source_url':'https://example.org/public-notice'},
       {'alias':'Other Person','alias_type':'alternative_name','source_url':''}]
    assert bounded_alias_queries('Ayush Tripathi',a,include=False)==[]
    assert bounded_alias_queries('Ayush Tripathi',a,include=True)==['आयुष त्रिपाठी']
    assert bounded_alias_queries('Ayush Tripathi',[{'alias':'Ayush Tripathi',
        'alias_type':'transliteration','source_url':'https://example.org'}],
        include=True)==[]

def test_043_trade_and_education_are_task_specific_not_licensed_integrations():
    trade=occupation_routes('Find public plumber service record in Delhi')
    school=occupation_routes('Published student university scholarship awards')
    assert trade[0]['lens']=='trade'
    assert any(x['lens']=='education' for x in school)
    assert all(not x['liveConnectorProvisioned'] for x in trade+school)

def test_039_person_case_does_not_infer_business_address(client,auth,case):
    r=client.get(f'/api/cases/{case}/business-leads')
    assert r.status_code==200
    assert r.json()['items']==[]
