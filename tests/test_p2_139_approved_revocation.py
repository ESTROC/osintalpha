"""P2 139 actual reviewed report approval: second reviewer required, changes invalidate."""
import hashlib
from fastapi.testclient import TestClient
from app.main import app
from app import db

def test_report_approval_revoked_after_evidence_changes(client,auth):
    cr=client.post('/api/users',headers=auth,json={
        'username':'sourceanalyst','password':'DistinctAnalystPassphrase2026!','role':'analyst'})
    assert cr.status_code==201,cr.text
    with TestClient(app) as analyst:
        assert analyst.post('/api/auth/login',json={
           'username':'sourceanalyst','password':'DistinctAnalystPassphrase2026!'}).status_code==200
        case=analyst.post('/api/cases',headers=auth,json={
            'title':'Organization synthetic review','subject_type':'organization',
            'query':'Example Institute','purpose':'Authorized analysis of a synthetic public source',
            'authority_confirmed':True})
        assert case.status_code==201,case.text
        case_id=case.json()['id']
        ev=analyst.post(f'/api/cases/{case_id}/evidence',headers=auth,json={
            'label':'Example public bulletin','summary':'Synthetic publication source',
            'source_url':'https://example.org/bulletin'})
        assert ev.status_code==200,ev.text
        eid=ev.json()['id']
        body='An example institution published a demonstration report for a public research review.'
        sha=hashlib.sha256(body.encode()).hexdigest()
        with db.connect() as conn:
            conn.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
                ('approved-test-capture',case_id,eid,'https://example.org/bulletin','text/plain',
                 body,sha,'2026-10-29T00:00:00Z','captured',''))
        excerpt=analyst.post(f'/api/cases/{case_id}/excerpts',headers=auth,json={
            'evidence_id':eid,'capture_id':'approved-test-capture',
            'quote_text':'An example institution published a demonstration report',
            'interpretation':'Synthetic claim from published public note.'})
        assert excerpt.status_code==201,excerpt.text
        claim=analyst.post(f'/api/cases/{case_id}/claims',headers=auth,json={
            'evidence_id':eid,'claim_text':'An institution released a research report.',
            'stance':'supports'})
        assert claim.status_code==201,claim.text
        proof=analyst.post(f'/api/cases/{case_id}/claim-passages',headers=auth,json={
            'claim_id':claim.json()['id'],'excerpt_id':excerpt.json()['id']})
        assert proof.status_code==201,proof.text
        status=analyst.patch(f'/api/evidence/{eid}',headers=auth,json={
            'status':'corroborated','reviewer_notes':'Original stored synthetic quote reviewed for text binding.'})
        assert status.status_code==200,status.text
        completed=analyst.put(f'/api/cases/{case_id}/assessment',headers=auth,json={
            'executive_summary':'Synthetic source reviewed. No identity or publisher truth verified.',
            'assessment':'This is a bounded public claim with a captured exact quotation.',
            'limitations':'Text quote presence does not establish that a legal entity acted.',
            'next_actions':'Independent source and rights review.',
            'status':'awaiting_review'})
        assert completed.status_code==200,completed.text
    signed=client.post(f'/api/cases/{case_id}/signoffs',headers=auth,json={
       'decision':'reviewed_with_limitations',
       'note':'Independent reviewer inspected current synthetic source and unresolved rights.'})
    assert signed.status_code==201,signed.text
    preview=client.get(f'/api/cases/{case_id}/distribution/preview')
    assert preview.status_code==200,preview.text
    assert preview.json()['readyForIndependentReview']
    approval={'report_digest':preview.json()['currentDigest'],
      'material_claims_checked':True,'source_rights_checked':True,
      'sensitive_content_checked':True,'methodology_checked':True,
      'limitations_checked':True,
      'reviewer_note':'Independent reviewer checked the stored synthetic claim and the cited source state, no legal truth certified.'}
    good=client.post(f'/api/cases/{case_id}/distribution/approve',headers=auth,json=approval)
    assert good.status_code==201,good.text
    live=client.get(f'/api/cases/{case_id}/distribution/approved.json')
    assert live.status_code==200,live.text
    assert live.json()['reportStatus']=='approved_for_distribution'
    update=client.patch(f'/api/evidence/{eid}',headers=auth,json={
        'status':'disputed','reviewer_notes':'Contradictory test source means approval must be revoked.'})
    assert update.status_code==200,update.text
    stale=client.get(f'/api/cases/{case_id}/distribution/approved.json')
    assert stale.status_code==409
