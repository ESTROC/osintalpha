"""P1 069/070/071: attributed syndication and non-calibrated quality/recency."""
import json
from datetime import datetime,timezone,timedelta
from app.duplicates import detect
from app.source_quality import expiration,source_rubric

def test_069_syndicated_articles_are_not_counted_as_independent():
    raw=json.dumps({'syndicated_from':'https://wire.example.org/original-article'})
    sources=[{'id':'a','provider':'gdelt','label':'Published press account','source_url':'https://paper-a.org/x','raw_json':raw},
             {'id':'b','provider':'brave_web','label':'Another published press account','source_url':'https://paper-b.org/y','raw_json':raw}]
    result=detect(sources)
    assert any(x['rule']=='declared_syndication' and x['notIndependent'] for x in result['pairs'])
    assert all(not x['syndicationVerified'] for x in result['pairs'])

def test_070_source_review_is_not_a_truth_probability():
    now=datetime(2026,10,28,tzinfo=timezone.utc)
    r={'provider':'github','source_url':'https://github.com/actor',
       'fetched_at':'2026-10-27T00:00:00+00:00','status':'corroborated'}
    score=source_rubric(r,{'publisher_authentication':'publisher_website_checked'},True,now)
    assert score['rubricPoints']>0
    assert score['scoreIsProbability'] is False
    assert score['sourceTruthVerified'] is False
    assert score['identityVerified'] is False

def test_071_stale_sources_and_missing_dates_remain_unknown():
    now=datetime(2026,10,28,tzinfo=timezone.utc)
    assert expiration('gdelt','2026-10-20T00:00:00Z',now)['stale'] is True
    assert expiration('crossref','2026-10-20T00:00:00Z',now)['stale'] is False
    assert expiration('github','',now)['stale'] is None

def test_070_quality_endpoint_authorized_case(client,auth,case):
    result=client.get(f'/api/cases/{case}/source-quality')
    assert result.status_code==200,result.text
    assert not result.json()['independentSourceIndependenceVerified']
    assert client.get('/api/cases/wrong/source-quality').status_code==404
