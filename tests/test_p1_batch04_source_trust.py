"""P1 059/060/062: human attribution cannot establish public identity facts."""
def test_060_source_type_is_not_truth(client,auth,case):
    e=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
      'label':'Synthetic university directory','summary':'Public page lead only',
      'source_url':'https://university.example.org/public-list'}).json()['id']
    payload={'source_kind':'official_institution_page','assertion_owner':'publisher_authored',
        'publisher_authentication':'not_checked','relation_to_subject':'possible_subject',
        'rationale':'This source has not been independently authenticated by the university.'}
    rejected=client.post(f'/api/cases/{case}/evidence/{e}/source-attribution',headers=auth,json=payload)
    assert rejected.status_code==422
    payload['publisher_authentication']='publisher_website_checked'
    okay=client.post(f'/api/cases/{case}/evidence/{e}/source-attribution',headers=auth,json=payload)
    assert okay.status_code==201,okay.text
    assert okay.json()['employmentOrEnrolmentVerified'] is False
    view=client.get(f'/api/cases/{case}/source-attribution').json()['items'][0]
    assert view['publisherAuthenticatedBySystem'] is False
    assert view['analystSourceAttribution']['source_kind']=='official_institution_page'

def test_059_manual_institution_check_is_not_official_api(client,auth,case):
    e=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'Example employer directory','summary':'Unverified public employer page',
        'source_url':'https://example.org/people'}).json()['id']
    data={'evidence_id':e,'institution_name':'Example University',
          'research_claim':'public_enrolment','review_note':'This is a manually recorded review of a public source, not a student credential check.',
          'official_page_reviewed':False}
    assert client.post(f'/api/cases/{case}/institution-check',headers=auth,json=data).status_code==422
    data['official_page_reviewed']=True
    result=client.post(f'/api/cases/{case}/institution-check',headers=auth,json=data)
    assert result.status_code==201,result.text
    assert result.json()['studentEnrolmentVerified'] is False

def test_062_conflict_review_cannot_cross_case(client,auth,case):
    e=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'Public memo','summary':'A source with a disputed claim',
        'source_url':'https://example.org/memo'}).json()['id']
    ids=[]
    for stance in ('supports','contradicts'):
        r=client.post(f'/api/cases/{case}/claims',headers=auth,json={
            'evidence_id':e,'claim_text':'Public event date','stance':stance})
        assert r.status_code==201,r.text
        ids.append(r.json()['id'])
    listed=client.get(f'/api/cases/{case}/claim-conflicts')
    assert listed.status_code==200
    assert len(listed.json()['potentialContradictions'])==1
    decision=client.post(f'/api/cases/{case}/claim-conflicts',headers=auth,json={
        'left_claim_id':ids[0],'right_claim_id':ids[1],
        'classification':'not_comparable','right_of_reply':'not_applicable',
        'review_note':'Synthetic examples may refer to different dates; no causal link can be inferred.'})
    assert decision.status_code==201,decision.text
    assert decision.json()['factVerified'] is False
    assert client.get('/api/cases/unknown/claim-conflicts').status_code==404
