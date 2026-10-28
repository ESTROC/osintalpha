"""P1-090 only source-bound analyst-reviewed findings produce a confirmable draft."""
import hashlib
from app import db

def test_draft_without_current_quotes_cannot_be_approved(client,auth,case):
    r=client.get(f'/api/cases/{case}/reviewed-report-draft')
    assert r.status_code==200,r.text
    assert r.json()['sourceCount']==0
    assert not r.json()['automaticApproval']
    denied=client.post(f'/api/cases/{case}/reviewed-report-draft/accept',
         headers=auth,json={'review_token':r.json()['reviewToken'],'reviewer_confirmed':True})
    assert denied.status_code==422

def test_bound_source_claim_can_generate_pending_report(client,auth,case):
    e=client.post(f'/api/cases/{case}/evidence',headers=auth,
       json={'label':'Research bulletin','summary':'Synthetic source for research',
           'source_url':'https://example.org/public-notice'})
    assert e.status_code==200,e.text
    eid=e.json()['id']
    body='The organization announced its annual public technology event on October twenty eight.'
    digest=hashlib.sha256(body.encode()).hexdigest()
    with db.connect() as c:
        c.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
            ('report-cap',case,eid,'https://example.org/public-notice','text/plain',
             body,digest,'2026-10-28T00:00:00Z','captured',''))
    excerpt=client.post(f'/api/cases/{case}/excerpts',headers=auth,json={
        'evidence_id':eid,'capture_id':'report-cap',
        'quote_text':'The organization announced its annual public technology event',
        'interpretation':'Synthetic announcement about public event only.'})
    assert excerpt.status_code==201,excerpt.text
    claim=client.post(f'/api/cases/{case}/claims',headers=auth,json={
       'evidence_id':eid,'claim_text':'A public event announcement exists','stance':'supports'})
    assert claim.status_code==201,claim.text
    proof=client.post(f'/api/cases/{case}/claim-passages',headers=auth,json={
        'claim_id':claim.json()['id'],'excerpt_id':excerpt.json()['id']})
    assert proof.status_code==201,proof.text
    review=client.patch(f'/api/evidence/{eid}',headers=auth,json={
        'status':'corroborated','reviewer_notes':'Analyst checked the stored synthetic capture, not official fact confirmation.'})
    assert review.status_code==200,review.text
    prev=client.get(f'/api/cases/{case}/reviewed-report-draft').json()
    assert prev['sourceCount']==1
    assert prev['verifiedFacts']==0
    denied=client.post(f'/api/cases/{case}/reviewed-report-draft/accept',headers=auth,
        json={'review_token':prev['reviewToken'],'reviewer_confirmed':False})
    assert denied.status_code==422
    accepted=client.post(f'/api/cases/{case}/reviewed-report-draft/accept',headers=auth,
        json={'review_token':prev['reviewToken'],'reviewer_confirmed':True})
    assert accepted.status_code==201,accepted.text
    assert accepted.json()['status']=='awaiting_review'
    ass=client.get(f'/api/cases/{case}/assessment')
    assert ass.status_code==200
    assert ass.json()['status']=='awaiting_review'
