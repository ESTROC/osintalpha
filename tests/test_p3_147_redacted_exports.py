"""P3 147: preview hides chosen fields and approved export cannot bypass signer."""
from app.export_controls import redaction_build,RedactionRequest

def test_preview_suppresses_source_links_and_unreviewed_records(client,auth,case):
    ev=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
      'label':'SECRET_SUBJECT_LABEL','summary':'An unreviewed candidate',
      'source_url':'https://example.org/secret-link'})
    assert ev.status_code==200,ev.text
    params={'suppress_subject_title':True,'suppress_original_urls':True,
        'suppress_claim_text':True,'suppress_source_labels':True,'export_format':'json'}
    p=client.post(f'/api/cases/{case}/distribution/redaction-preview',headers=auth,json=params)
    assert p.status_code==200,p.text
    assert p.json()['sources']==[]
    assert not p.json()['approvedForDistribution']
    assert 'SECRET_SUBJECT_LABEL' not in p.text
    attempted=client.post(f'/api/cases/{case}/distribution/redacted-export',headers=auth,json=params)
    assert attempted.status_code==409

def test_redaction_logic_no_label_or_url_leak():
    data={'reviewedEvidence':[{'id':'src1','label':'CONFIDENTIAL_TITLE','status':'corroborated',
         'sha256':'a'*64,'fetched_at':'2026-01-01','source_url':'https://example.org/confidential'}],
         'sourceClaims':[{'id':'claim1','text':'CONFIDENTIAL_CLAIM','sourceId':'src1',
         'sourceUrl':'https://example.org/confidential','captureHashes':['b'*64]}],
         'limitations':'This is a synthetic limitation.','caseTitle':'CONFIDENTIAL_CASE'}
    item=redaction_build(data,RedactionRequest(suppress_claim_text=True))
    assert not any(token in str(item) for token in ('CONFIDENTIAL_TITLE','CONFIDENTIAL_CLAIM',
           'CONFIDENTIAL_CASE','https://example.org/confidential'))
    assert item['sources'][0]['hash']=='a'*64
