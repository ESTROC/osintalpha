"""P2 129/130 signed-bytes comparison and review-gated export tests."""
import hashlib
from app import db
def test_export_rejects_unreviewed_sources(client,auth,case):
    denied=client.get(f'/api/cases/{case}/reviewed-source-bundle')
    assert denied.status_code==409
    assert client.get(f'/api/cases/{case}/custody-access').status_code==200

def test_exact_quote_review_exports_checksum_and_detects_changes(client,auth,case):
    r=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'Synthetic board bulletin','summary':'Sample publication',
        'source_url':'https://example.org/board'})
    assert r.status_code==200,r.text
    eid=r.json()['id'];words='The synthetic organization held a public annual meeting.'
    with db.connect() as c:
        c.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
          ('custody-test-capture',case,eid,'https://example.org/board','text/plain',
           words,hashlib.sha256(words.encode()).hexdigest(),'2026-10-28T00:00:00Z','captured',''))
    excerpt=client.post(f'/api/cases/{case}/excerpts',headers=auth,json={
        'evidence_id':eid,'capture_id':'custody-test-capture',
        'quote_text':'The synthetic organization held a public annual meeting',
        'interpretation':'Synthetic meeting notice only.'})
    assert excerpt.status_code==201,excerpt.text
    claim=client.post(f'/api/cases/{case}/claims',headers=auth,json={
        'evidence_id':eid,'claim_text':'Public annual meeting notice was recorded','stance':'supports'})
    assert claim.status_code==201,claim.text
    p=client.post(f'/api/cases/{case}/claim-passages',headers=auth,json={
        'claim_id':claim.json()['id'],'excerpt_id':excerpt.json()['id']})
    assert p.status_code==201,p.text
    r=client.patch(f'/api/evidence/{eid}',headers=auth,json={
        'status':'corroborated','reviewer_notes':'Reviewed original synthetic bulletin capture.'})
    assert r.status_code==200,r.text
    bundle=client.get(f'/api/cases/{case}/reviewed-source-bundle')
    assert bundle.status_code==200,bundle.text
    obj=bundle.json();assert obj['manifest']['sourceCount']==1
    assert obj['signed'] is False and obj['manifest']['factsIndependentlyVerified'] is False
    ver=client.post(f'/api/cases/{case}/reviewed-source-bundle/verify',headers=auth,
       json={'manifest':obj['manifest'],'sha256':obj['sha256']})
    assert ver.status_code==200 and ver.json()['sha256Matches']
    tampered={**obj['manifest'],'sourceCount':5}
    ver=client.post(f'/api/cases/{case}/reviewed-source-bundle/verify',headers=auth,
       json={'manifest':tampered,'sha256':obj['sha256']})
    assert ver.status_code==200 and not ver.json()['sha256Matches']
