"""P1 052: stale completed assessment cannot be signed as current."""
def test_052_cannot_sign_stale_evidence(client,auth,case):
    payload={'executive_summary':'This is an internal assessment containing only unverified synthetic source leads.',
      'assessment':'All source data in this case are synthetic and require independent factual checks.',
      'limitations':'No independently verified publisher ownership, account identity or audited claim accuracy.',
      'next_actions':'Inspect original publisher citations with a second reviewer.',
      'status':'researching'}
    result=client.put(f'/api/cases/{case}/assessment',headers=auth,json=payload)
    assert result.status_code==200,result.text
    source=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
       'label':'New document','summary':'Potential public reference',
       'source_url':'https://example.org/public'})
    assert source.status_code==200,source.text
    attempt=client.post(f'/api/cases/{case}/signoffs',headers=auth,json={
       'decision':'reviewed_with_limitations',
       'note':'The analyst wants to release a previously reviewed snapshot, now stale.'})
    assert attempt.status_code==409,attempt.text
    assert 're-reviewed' in attempt.json()['detail']
    assert client.put(f'/api/cases/{case}/assessment',headers=auth,json=payload).status_code==200
    allowed=client.post(f'/api/cases/{case}/signoffs',headers=auth,json={
       'decision':'reviewed_with_limitations',
       'note':'A reviewer must still check independent factual and identity evidence.'})
    assert allowed.status_code==201,allowed.text
