"""P1 074: no auto-assigned employer or person-level timeline without a literal quote."""
import hashlib
from app import db

def test_074_time_bound_affiliation_requires_candidate_and_exact_quote(client,auth,case):
    ev=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
       'label':'University synthetic announcement',
       'summary':'Published public activity roster',
       'source_url':'https://example.org/roster'})
    assert ev.status_code==200
    eid=ev.json()['id']
    person=client.post(f'/api/cases/{case}/candidates',headers=auth,json={
       'display_name':'Alex Researcher'}).json()['id']
    statement='The institution roster lists Alex Researcher as a volunteer from 2021 to 2023 in public projects.'
    checksum=hashlib.sha256(statement.encode()).hexdigest()
    with db.connect() as c:
        c.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
         ('historical-cap',case,eid,'https://example.org/roster','text/plain',
          statement,checksum,'2026-10-28T00:00:00Z','captured',''))
    quote=client.post(f'/api/cases/{case}/excerpts',headers=auth,json={
        'evidence_id':eid,'capture_id':'historical-cap',
        'quote_text':'The institution roster lists Alex Researcher as a volunteer from 2021 to 2023',
        'interpretation':'The page mentions a candidate with a public volunteer history.'})
    assert quote.status_code==201,quote.text
    body={'candidate_id':person,'evidence_id':eid,'excerpt_id':quote.json()['id'],
          'organization_name':'Sample University','role_title':'Volunteer',
          'start_date':'2021-01-01','end_date':'2023-12-31','date_precision':'year',
          'rationale':'Analyst interpretation of the synthetic saved public announcement; not official enrolment.'}
    saved=client.post(f'/api/cases/{case}/public-affiliations',headers=auth,json=body)
    assert saved.status_code==201,saved.text
    assert saved.json()['employmentVerified'] is False
    assert client.get(f'/api/cases/{case}/public-affiliations').json()['items'][0]['candidate_id']==person
    body['end_date']='2020-01-01'
    assert client.post(f'/api/cases/{case}/public-affiliations',headers=auth,json=body).status_code==422
