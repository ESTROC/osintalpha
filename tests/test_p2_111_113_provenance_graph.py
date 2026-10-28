"""P2 111-113: date provenance, no fabricated chronology or person mapping."""
import hashlib
from app import db

def _evidence(client,auth,case,label='Official public organization page'):
    r=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
      'label':label,'summary':'Public event synthetic record',
      'source_url':'https://example.org/public-event'})
    assert r.status_code==200,r.text
    return r.json()['id']

def test_event_dates_remain_distinct(client,auth,case):
    eid=_evidence(client,auth,case)
    original='The public institution hosted a synthetic event on 2019 January 12.'
    with db.connect() as c:
        c.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
           ('event-cap',case,eid,'https://example.org/public-event','text/plain',original,
            hashlib.sha256(original.encode()).hexdigest(),'2026-10-28T00:00:00Z','captured',''))
    body={'evidence_id':eid,'capture_id':'event-cap','exact_quote':original,
          'event_label':'Synthetic public event','observed_date':'2019-01-12',
          'published_date':'2019-01-13',
          'review_note':'Manual interpretation of original public quote only.'}
    ok=client.post(f'/api/cases/{case}/public-events',headers=auth,json=body)
    assert ok.status_code==201,ok.text
    chrono=client.get(f'/api/cases/{case}/chronology').json()['items'][0]
    assert chrono['eventDate']=='2019-01-12'
    assert chrono['publicationDate']=='2019-01-13'
    assert chrono['retrievalDate']!=chrono['eventDate']
    assert chrono['eventIndependentlyVerified'] is False
    bad=client.post(f'/api/cases/{case}/public-events',headers=auth,
       json={**body,'exact_quote':'This assertion is not in original captured text.'})
    assert bad.status_code==422

def test_person_case_rejects_precision_coordinates(client,auth,case):
    eid=_evidence(client,auth,case)
    req={'evidence_id':eid,'place_name':'Public laboratory','latitude':28.6,'longitude':77.2,
      'precision':'publisher_public_point','review_status':'reviewed_public_location',
      'annotation':'The official published institution location, not a human position.'}
    r=client.post(f'/api/cases/{case}/public-org-places',headers=auth,json=req)
    assert r.status_code==422
    assert client.get(f'/api/cases/{case}/public-org-places').json()['points']==[]

def test_org_graph_unrelated_remains_disconnected(client,auth,case):
    graph=client.get(f'/api/cases/{case}/organization-links')
    assert graph.status_code==200,graph.text
    assert graph.json()['edges']==[]
