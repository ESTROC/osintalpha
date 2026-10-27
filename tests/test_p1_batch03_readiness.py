"""Evidence-quality monitoring is not independent identity or fact verification."""
from app import db

def test_049_050_051_zero_hits_do_not_justify_confident_answer(client,auth,case):
    r=client.get(f'/api/cases/{case}/decision-readiness')
    assert r.status_code==200,r.text
    p=r.json()
    assert p['sourceRecordsReviewed']==0
    assert p['independentlyVerifiedFactCount']==0
    assert p['calibratedConfidence'] is None
    assert p['objectiveCompleted'] is False
    assert 'No executed' in ' '.join(p['openQuestions'])

def test_052_saved_assessment_stales_when_new_evidence_arrives(client,auth,case):
    payload={'executive_summary':'Research work needs independent validation',
        'assessment':'Observed snippets are not verified source facts',
        'limitations':'This candidate query is incomplete','next_actions':'Source review',
        'status':'researching'}
    first=client.put(f'/api/cases/{case}/assessment',headers=auth,json=payload)
    assert first.status_code==200,first.text
    assert client.get(f'/api/cases/{case}/assessment').json()['sourceStateCurrent'] is True
    saved=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'New public notice','summary':'New indexed document',
        'source_url':'https://example.org/test-notice'})
    assert saved.status_code==200,saved.text
    after=client.get(f'/api/cases/{case}/assessment').json()
    assert after['sourceStateCurrent'] is False
    assert client.get(f'/api/cases/{case}/decision-readiness').json()['assessmentCurrentWithReviewedEvidence'] is False
    second=client.put(f'/api/cases/{case}/assessment',headers=auth,json=payload)
    assert second.status_code==200
    assert client.get(f'/api/cases/{case}/assessment').json()['sourceStateCurrent'] is True

def test_051_documented_query_still_cannot_certify_completeness(client,auth,case):
    with db.connect() as conn:
        owner=conn.execute('SELECT created_by FROM cases WHERE id=?',(case,)).fetchone()['created_by']
        conn.execute('INSERT INTO research_queries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            ('fake-run-051',case,owner,'demo-051','github','Test Person','empty',0,0,
             'Synthetic query no hits','2026-10-28T00:00:00Z'))
    result=client.get(f'/api/cases/{case}/decision-readiness')
    assert result.status_code==200,result.text
    assert not result.json()['objectiveCompleted']
