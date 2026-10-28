"""P1 068: every report claim has an explicit current quotation gap or reference."""
import hashlib
from app import db

def _case_claim(client,auth,case):
    ev=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'Official synthetic notice','summary':'Published date',
        'source_url':'https://example.org/notice'}).json()['id']
    row=client.post(f'/api/cases/{case}/claims',headers=auth,json={
        'evidence_id':ev,'claim_text':'The public event occurred in late October','stance':'supports'})
    assert row.status_code==201,row.text
    return ev,row.json()['id']

def test_068_report_explicitly_marks_unbound_claim(client,auth,case):
    ev,claim=_case_claim(client,auth,case)
    result=client.get(f'/api/cases/{case}/claim-support-index')
    assert result.status_code==200,result.text
    item=result.json()['items'][0]
    assert item['claimBindingState']=='missing_exact_quote'
    assert result.json()['truthVerifiedClaims']==0
    report=client.get(f'/api/cases/{case}/report.json')
    assert report.status_code==200,report.text
    assert report.json()['claimSupport']['claimsMissingCurrentExactQuotes']==1
    html=client.get(f'/api/cases/{case}/report.html')
    assert html.status_code==200
    assert 'No exact quotation bound to this claim' in html.text

def test_068_approved_report_requires_current_exact_quote(client,auth,case):
    ev,claim=_case_claim(client,auth,case)
    assessment={'executive_summary':'Public notice review is provisional and may not be attributable to the named subject.',
      'assessment':'The case includes a manual public notice lead and no independently verified human identity.',
      'limitations':'No identity or source-author authentication was provided for this synthetic notice.',
      'next_actions':'Review source integrity and alternative public evidence.',
      'status':'researching'}
    assert client.put(f'/api/cases/{case}/assessment',headers=auth,json=assessment).status_code==200
    body={'decision':'reviewed_with_limitations',
          'note':'We recognize the synthetic record requires a source quote and independent review.'}
    r=client.post(f'/api/cases/{case}/signoffs',headers=auth,json=body)
    assert r.status_code==422,r.text
    assert 'quotation' in r.json()['detail']
    notice='The university public research showcase will occur on Wednesday November fifth at the main hall.'
    digest=hashlib.sha256(notice.encode()).hexdigest()
    with db.connect() as conn:
        conn.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
         ('capture-demo',case,ev,'https://example.org/notice','text/plain',
          notice,digest,'2026-10-28T00:00:00Z','captured',''))
    excerpt=client.post(f'/api/cases/{case}/excerpts',headers=auth,json={
        'evidence_id':ev,'capture_id':'capture-demo',
        'quote_text':'The university public research showcase will occur on Wednesday November fifth',
        'interpretation':'The public notice describes a future event date, not identity proof.'})
    assert excerpt.status_code==201,excerpt.text
    proof=client.post(f'/api/cases/{case}/claim-passages',headers=auth,json={
        'claim_id':claim,'excerpt_id':excerpt.json()['id']})
    assert proof.status_code==201,proof.text
    assert client.put(f'/api/cases/{case}/assessment',headers=auth,json=assessment).status_code==200
    updated=client.get(f'/api/cases/{case}/claim-support-index').json()
    assert updated['claimsWithCurrentExactQuotes']==1
    allowed=client.post(f'/api/cases/{case}/signoffs',headers=auth,json=body)
    assert allowed.status_code==201,allowed.text
