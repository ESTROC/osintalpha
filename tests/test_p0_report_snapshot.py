"""P0-022/023: saved citation snapshots are immutable and report-consistent."""
from app import db

def test_022_snapshot_survives_new_evidence_status(client,auth,case):
    evidence=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'Official example page','summary':'A public demo that needs review',
        'source_url':'https://example.org/demo'}).json()['id']
    response=client.post(f'/api/cases/{case}/chat',headers=auth,json={
        'question':'Show observed sources','provider':'local'})
    assert response.status_code==200,response.text
    report=client.get(f'/api/cases/{case}/report.json')
    assert report.status_code==200
    snap=report.json()['research']
    assert snap['snapshotVersion']==1
    assert snap['snapshotIntegrityOk'] is True
    assert snap['answer']==response.json()['answer']
    original=snap['snapshotSha256']
    assert client.patch(f'/api/evidence/{evidence}',headers=auth,json={
        'status':'disputed',
        'reviewer_notes':'Synthetic evidence provenance must be reviewed.'}).status_code==200
    after=client.get(f'/api/cases/{case}/report.json').json()['research']
    assert after['snapshotSha256']==original


def test_023_html_and_json_use_same_saved_answer(client,auth,case):
    response=client.post(f'/api/cases/{case}/chat',headers=auth,json={
        'question':'Which parts are unknown?','provider':'local'}).json()
    html=client.get(f'/api/cases/{case}/report.html')
    json_report=client.get(f'/api/cases/{case}/report.json')
    assert html.status_code==200
    assert json_report.status_code==200
    assert response['answer'][:30] in html.text
    assert json_report.json()['research']['answer']==response['answer']
    assert 'UNVERIFIED AI SYNTHESIS' in html.text


def test_022_snapshots_isolated_by_case(client,auth,case):
    r=client.post(f'/api/cases/{case}/chat',headers=auth,json={
        'question':'Document unknowns','provider':'local'})
    assert r.status_code==200
    with db.connect() as conn:
        assert conn.execute('SELECT count(*) n FROM research_response_snapshots WHERE case_id=?',
                             (case,)).fetchone()['n']==1
    assert client.get('/api/cases/nonexistent/report.json').status_code==404
