"""P1-103 no sensitive evidence text in protected data inventory response."""
def test_risk_inventory_case_scoped_no_payloads(client,auth,case):
    phrase='PRIVATE_SYNTHETIC_CAPTURE_CONTENT_DO_NOT_EXPOSE'
    add=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
      'label':'Public lead','summary':phrase,
      'source_url':'https://example.org/inventory-test'})
    assert add.status_code==200,add.text
    res=client.get(f'/api/cases/{case}/data-protection-review')
    assert res.status_code==200,res.text
    assert res.json()['itemCountsOnly']['unreviewedSources']==1
    assert phrase not in res.text
    assert not res.json()['databaseEncryptionVerified']
    assert not res.json()['privacyComplianceCertified']
    assert client.get('/api/cases/missing-case/data-protection-review').status_code==404
