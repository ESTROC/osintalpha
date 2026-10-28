"""P1 075/076: excluded people and unreviewed raw hits do not dominate reports."""
from pathlib import Path

def test_075_counterevidence_appears_in_primary_overview():
    source=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert 'Counter-evidence and explicitly excluded namesakes' in source
    assert 'Excluded candidate hypothesis' in source
    assert 'No rejected or disputed source records documented' in source

def test_076_printable_report_prioritizes_claims_and_reviewed_sources(client,auth,case):
    e=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'Unreviewed source lead','summary':'Unverified listing, not a fact',
        'source_url':'https://example.org/list'})
    assert e.status_code==200,e.text
    html=client.get(f'/api/cases/{case}/report.html')
    assert html.status_code==200
    assert 'Reviewed source decisions' in html.text
    assert 'Unreviewed and rejected lead annex' in html.text
    assert html.text.index('Reviewed source decisions')<html.text.index('Unreviewed and rejected lead annex')
    as_json=client.get(f'/api/cases/{case}/report.json')
    assert as_json.status_code==200
    assert len(as_json.json()['candidateAndRejectedAnnex'])==1
    assert as_json.json()['reviewedEvidence']==[]
