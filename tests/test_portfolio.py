"""V7.7 candidate portfolio and coarse map privacy regressions.

Only synthetic records and mocked external calls; no live person harvesting.
"""
import json
from types import SimpleNamespace

from app import db, portfolio, v5


def add_candidate(client, auth, case, *, provider='github', raw=None, source='https://github.com/case-test'):
    created = client.post('/api/cases/' + case + '/evidence', headers=auth, json={
        'label': 'Example Researcher', 'summary': 'Synthetic public developer profile candidate',
        'source_url': source})
    assert created.status_code == 200, created.text
    eid = created.json()['id']
    with db.connect() as conn:
        conn.execute('UPDATE evidence SET provider=?,raw_json=? WHERE id=?',
                     (provider, json.dumps(raw or {}), eid))
    return eid


def test_public_portfolio_does_not_merge_namesakes_or_confirm_public_photo(client, auth, case):
    eid = add_candidate(client, auth, case, raw={
        'display_name': 'Example Researcher', 'login': 'candidate-one',
        'company': 'Example University', 'location': 'Delhi, India',
        'avatar_url': 'https://avatars.githubusercontent.com/u/12345?v=4',
        'blog': 'https://portfolio.example.org'})
    second = add_candidate(client, auth, case, source='https://github.com/another-case-test',
                           raw={'display_name': 'Example Researcher', 'login': 'candidate-two'})
    r = client.get('/api/cases/' + case + '/public-portfolio')
    assert r.status_code == 200, r.text
    out = r.json()
    assert out['total'] == 2 and out['verifiedProfiles'] == 0
    assert {row['evidenceId'] for row in out['items']} == {eid, second}
    candidate = next(x for x in out['items'] if x['evidenceId'] == eid)
    assert not candidate['identityVerified']
    assert candidate['photoUrl'].startswith('https://avatars.githubusercontent.com/u/')
    assert candidate['publishedLocation'] == 'Delhi, India'


def test_profile_does_not_load_untrusted_external_photo_or_random_news(client, auth, case):
    add_candidate(client, auth, case, raw={
        'avatar_url': 'https://github.com.evil.example/u/2', 'login': 'candidate-one'})
    add_candidate(client, auth, case, provider='brave_web',
                  source='https://news.example.org/unrelated-article')
    add_candidate(client, auth, case, provider='brave_web',
                  source='https://www.linkedin.com/in/test-researcher')
    out = client.get('/api/cases/' + case + '/public-portfolio').json()
    assert out['total'] == 2
    assert all(not x['photoUrl'] for x in out['items'])
    assert any(x['platform'] == 'linkedin_lead' and not x['identityVerified']
               for x in out['items'])


def test_city_preview_requires_opt_in_and_rejects_addresses(client, auth, case):
    endpoint = '/api/cases/' + case + '/public-location-preview'
    assert client.post(endpoint, headers=auth, json={'consent': True}).status_code == 422
    client.put('/api/cases/' + case + '/context', headers=auth,
               json={'city': 'Flat 23 Main Road, Delhi'})
    assert client.post(endpoint, headers=auth, json={'consent': True}).status_code == 422
    client.put('/api/cases/' + case + '/context', headers=auth, json={'city': 'Delhi, India'})
    assert client.post(endpoint, headers=auth, json={'consent': False}).status_code == 422


def test_city_preview_is_approximate_and_only_queries_public_city(client, auth, case, monkeypatch):
    client.put('/api/cases/' + case + '/context', headers=auth, json={'city': 'Delhi, India'})
    portfolio._GEOCODE_CACHE.clear()
    monkeypatch.setattr(portfolio, '_GEOCODE_LAST', 0.0)
    calls = []
    class Resp:
        def raise_for_status(self): pass
        def json(self):
            return [{'lat': '28.6138954', 'lon': '77.2090057',
                     'display_name': 'New Delhi, Delhi, India'}]
    class MockClient:
        def __init__(self, **kwargs):
            assert kwargs['follow_redirects'] is False
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return Resp()
    monkeypatch.setattr(portfolio.httpx, 'AsyncClient', MockClient)
    endpoint = '/api/cases/' + case + '/public-location-preview'
    r = client.post(endpoint, headers=auth, json={'consent': True})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['lat'] == 28.61 and data['lon'] == 77.21
    assert 'NOT the current' in data['notice']
    assert calls[0][0] == 'https://nominatim.openstreetmap.org/search'
    assert calls[0][1]['params']['q'] == 'Delhi, India'
    assert len(calls) == 1
    assert client.post(endpoint, headers=auth, json={'consent': True}).status_code == 200
    assert len(calls) == 1


def test_discovery_queries_include_tightly_scoped_professional_sites():
    obj = {'subject_type': 'person', 'query': 'Example Researcher'}
    ctx = {'organization': 'Example University', 'city': 'Delhi', 'public_handle': 'candidate'}
    queries = v5.make_queries(obj, ctx, SimpleNamespace(query=None, depth=4))
    assert len(queries) == 4
    assert queries[0].startswith('Example Researcher Example University Delhi')
    assert any('site:linkedin.com/in/' in query for query in queries)
    assert any('site:github.com' in query for query in queries)
    assert all(len(query) <= 200 for query in queries)
