"""Additional P2-112/113/115 positive paths and source-review gates."""
def _org_case(client,auth):
    r=client.post('/api/cases',headers=auth,json={
       'title':'Synthetic public company research',
       'subject_type':'organization','query':'Example Institute',
       'purpose':'Authorized review of publicly published institutional data',
       'authority_confirmed':True})
    assert r.status_code==201,r.text
    return r.json()['id']

def _source(client,auth,case):
    e=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
      'label':'Published synthetic source','summary':'Synthetic organization page metadata',
      'source_url':'https://example.org/company-details'})
    assert e.status_code==200,e.text
    return e.json()['id']

def test_org_relationship_requires_review_and_dates(client,auth):
    case=_org_case(client,auth);eid=_source(client,auth,case)
    relation=client.post(f'/api/cases/{case}/relationships',headers=auth,json={
        'left_name':'Example Institute','right_name':'Example Partner',
        'relationship':'collaboration','evidence_id':eid,
        'rationale':'An independently reviewable synthetic organizational page claim.'})
    assert relation.status_code==201,relation.text
    rid=relation.json()['id']
    assert client.get(f'/api/cases/{case}/organization-links').json()['edges']==[]
    review=client.patch(f'/api/cases/{case}/relationships/{rid}',headers=auth,json={
       'review_state':'reviewed_public_record','note':'Human-reviewed synthetic candidate organizational claim; not a verified partnership.'})
    assert review.status_code==200,review.text
    body={'valid_from':'2020-01-01','valid_until':'2021-05-31',
          'contradiction_note':'No independent confirmation; potential historical namesakes.'}
    denied=client.put(f'/api/cases/{case}/organization-links/{rid}/dates',headers=auth,json=body)
    assert denied.status_code==422
    evidence_review=client.patch(f'/api/evidence/{eid}',headers=auth,json={
        'status':'corroborated','reviewer_notes':'Manual source review in synthetic test.'})
    assert evidence_review.status_code==200,evidence_review.text
    written=client.put(f'/api/cases/{case}/organization-links/{rid}/dates',headers=auth,json=body)
    assert written.status_code==200,written.text
    visible=client.get(f'/api/cases/{case}/organization-links').json()
    assert len(visible['edges'])==1
    assert visible['edges'][0]['valid_from']=='2020-01-01'
    assert not visible['legalRelationshipsVerified']

def test_public_place_withholds_disputed_coordinates(client,auth):
    case=_org_case(client,auth);eid=_source(client,auth,case)
    client.patch(f'/api/evidence/{eid}',headers=auth,json={
      'status':'corroborated','reviewer_notes':'Publisher source manually reviewed.'})
    body={'evidence_id':eid,'place_name':'Public Example Laboratory',
          'latitude':28.633,'longitude':77.209,'precision':'publisher_public_point',
          'publisher_date':'2020-01-01','review_status':'disputed_location',
          'annotation':'Two published addresses conflict; no person position may be inferred.'}
    result=client.post(f'/api/cases/{case}/public-org-places',headers=auth,json=body)
    assert result.status_code==201,result.text
    out=client.get(f'/api/cases/{case}/public-org-places').json()
    assert out['points']==[] and out['disputedWithheld']==1

def test_reviewed_satellite_catalog_metadata_not_raster(client,auth):
    case=_org_case(client,auth);eid=_source(client,auth,case)
    client.patch(f'/api/evidence/{eid}',headers=auth,json={
      'status':'corroborated','reviewer_notes':'Reviewed synthetic publisher metadata.'})
    body={'evidence_id':eid,'provider':'nasa_gibs',
      'official_catalog_url':'https://gibs.earthdata.nasa.gov/',
      'permission_url':'https://earthdata.nasa.gov/',
      'acquisition_date':'2025-10-01','ground_resolution_m':250,
      'crs':'EPSG:4326','bounding_box':[-120,30,-119,31],
      'review_note':'Synthetic official metadata reviewed for storage; no image rights or raster tested.',
      'rights_confirmed':True}
    r=client.post(f'/api/cases/{case}/licensed-satellite-references',headers=auth,json=body)
    assert r.status_code==201,r.text
    assert not r.json()['rasterDownloaded']
    listing=client.get(f'/api/cases/{case}/licensed-satellite-references').json()
    assert listing['items'][0]['acquisition_date']=='2025-10-01'
    assert not listing['hasRasterLayer']
