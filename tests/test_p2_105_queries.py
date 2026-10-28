"""P2 105 operator preview rejects malformed source scopes and preserves terms."""
def test_public_operator_preview(client,auth):
    r=client.post('/api/research/advanced-query-preview',headers=auth,json={
       'question':'research institute conference','subject_type':'organization',
       'exact_phrase':'annual report','include_domain':'example.org',
       'exclude_terms':['advertising']})
    assert r.status_code==200,r.text
    q=r.json()['providerQuery']
    assert '"annual report"' in q and 'site:example.org' in q and '-advertising' in q
    assert not r.json()['executeAutomatically']

def test_unsafe_query_operators_rejected(client,auth):
    r=client.post('/api/research/advanced-query-preview',headers=auth,json={
       'question':'public organisation','exact_phrase':'foo OR site:bad.com'})
    assert r.status_code==422
    r=client.post('/api/research/advanced-query-preview',headers=auth,json={
       'question':'public organisation','include_domain':'127.0.0.1'})
    assert r.status_code==422
