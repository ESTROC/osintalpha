"""P2 139: export approval is not inferred from source count or case owner."""
def test_unsigned_distribution_is_blocked(client,auth,case):
    preview=client.get(f'/api/cases/{case}/distribution/preview')
    assert preview.status_code==200,preview.text
    assert not preview.json()['readyForIndependentReview']
    for suffix in ('approved.json','approved.html'):
        res=client.get(f'/api/cases/{case}/distribution/{suffix}')
        assert res.status_code==409
    payload={'report_digest':preview.json()['currentDigest'],
             'material_claims_checked':True,'source_rights_checked':True,
             'sensitive_content_checked':False,'methodology_checked':True,
             'limitations_checked':True,
             'reviewer_note':'Synthetic validation of distribution approval checklist without actual review.'}
    bad=client.post(f'/api/cases/{case}/distribution/approve',headers=auth,json=payload)
    assert bad.status_code==422
    payload['sensitive_content_checked']=True
    no_current=client.post(f'/api/cases/{case}/distribution/approve',headers=auth,json=payload)
    assert no_current.status_code==422
