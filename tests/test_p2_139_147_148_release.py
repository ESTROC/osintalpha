"""P2 139/147/148 release is fail-closed without a current approved exact-source review."""
def test_controlled_release_requires_review(client,auth,case):
    preview=client.get(f'/api/cases/{case}/controlled-export-preview')
    assert preview.status_code==200,preview.text
    assert preview.json()['preview']['reviewedQuoteCount']==0
    denied=client.get(f'/api/cases/{case}/controlled-report.html')
    assert denied.status_code==409
    approval=client.post(f'/api/cases/{case}/distribution-approval',headers=auth,json={
      'expected_preview_sha256':preview.json()['previewSha256'],
      'confirm_originals_reviewed':True,'confirm_exclusions_reviewed':True,
      'confirm_scope_authorized':True,
      'review_note':'Reviewed all original sources but no current exact quotation exists.'})
    assert approval.status_code==422
    m=client.get(f'/api/cases/{case}/methodology-appendix')
    assert m.status_code==200,m.text
    assert m.json()['originalQuestion']=='Test Person'
    assert not m.json()['independentlyAudited']

def test_explicit_confirmation_gate(client,auth,case):
    preview=client.get(f'/api/cases/{case}/controlled-export-preview').json()
    bad=client.post(f'/api/cases/{case}/distribution-approval',headers=auth,json={
      'expected_preview_sha256':preview['previewSha256'],
      'confirm_originals_reviewed':False,'confirm_exclusions_reviewed':True,
      'confirm_scope_authorized':True,
      'review_note':'The reviewer has not confirmed the content of all original citations.'})
    assert bad.status_code==422
