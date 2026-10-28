"""P2 134/138 synthetic truth-in-metrics and shared-origin provenance."""
import json
from app import db
def test_repeated_syndication_not_counted_twice(client,auth,case):
    for n in (1,2):
        e=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
          'label':f'Syndicated snippet {n}','summary':'Synthetic distinct index',
          'source_url':f'https://example.org/syndication/{n}'})
        assert e.status_code==200,e.text
        with db.connect() as conn:
            conn.execute('UPDATE evidence SET raw_json=? WHERE id=?',
                  (json.dumps({'canonical_url':'https://publisher.example.org/one-original'}),e.json()['id']))
    r=client.get(f'/api/cases/{case}/source-origin-review')
    assert r.status_code==200,r.text
    groups=r.json()['duplicateOriginGroups']
    assert len(groups)==1
    assert groups[0]['sourceCount']==2
    assert r.json()['distinctOriginKeys']==1
    assert r.json()['independentSourceCountCertified'] is None

def test_quality_metrics_do_not_invent_success(client,auth,case):
    r=client.get('/api/agency/review-timeliness')
    assert r.status_code==200,r.text
    data=r.json()
    assert data['casesInspected']>=1
    assert data['casesWithUsefulCorroboratedReview']==0
    assert data['firstUsefulReviewSecondsMedian'] is None
    assert data['targetSlaSeconds'] is None
    assert data['analystAccuracyMeasured'] is False
