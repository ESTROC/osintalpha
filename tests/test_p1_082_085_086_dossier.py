"""P1 082/085/086 answer-first case dossier and case-scoped claim drilldown."""
from app import db

def test_dossier_empty_case_reports_unavailable_not_false_bio(client,auth,case):
    res=client.get(f'/api/cases/{case}/dossier')
    assert res.status_code==200,res.text
    obj=res.json()
    assert obj['answer']['text'] is None
    assert obj['identityVerified'] is False
    assert obj['factsIndependentlyVerified'] is False
    assert obj['missingInformation']
    assert client.get('/api/cases/noncase/dossier').status_code==404

def test_086_source_sort_and_status_without_identity_probability(client,auth,case):
    for i in range(3):
        r=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
          'label':f'Public university bulletin {i}','summary':'Synthetic public record for analysis',
          'source_url':f'https://example.org/bulletin-{i}'})
        assert r.status_code==200,r.text
    res=client.get(f'/api/cases/{case}/dossier?sort=source&status=candidate&source_class=public_document_or_mention')
    assert res.status_code==200,res.text
    body=res.json()
    assert body['totalFilteredSourceResults']==3
    assert len(body['sourceResults'])==3
    assert all(x['rankingExplanation']['noCalibratedRelevanceProbability'] for x in body['sourceResults'])
    assert client.get(f'/api/cases/{case}/dossier?sort=unknown').status_code==422

def test_085_claim_drilldown_keeps_unverified_provenance(client,auth,case):
    e=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
      'label':'Public source','summary':'Unverified report',
      'source_url':'https://example.org/report'}).json()['id']
    claim=client.post(f'/api/cases/{case}/claims',headers=auth,json={
      'evidence_id':e,'claim_text':'A dated public record mentions an event.','stance':'supports'})
    assert claim.status_code==201,claim.text
    cid=claim.json()['id']
    r=client.get(f'/api/cases/{case}/claims/{cid}/explain')
    assert r.status_code==200,r.text
    assert r.json()['claimBindingState']=='missing_exact_quote'
    assert r.json()['materialClaimIndependentlyVerified'] is False
    assert client.get(f'/api/cases/{case}/claims/not-a-claim/explain').status_code==404
