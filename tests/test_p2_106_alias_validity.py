"""P2-106 two independently sourced aliases, dates and retirement."""
def test_two_sourced_aliases_reviewed_separately(client,auth,case):
    created=[]
    for alias,url in [('Former Org Name','https://example.org/history'),
                      ('Published Brand','https://example.org/brand')]:
        r=client.post(f'/api/cases/{case}/aliases',headers=auth,json={
          'alias':alias,'alias_type':'alternative_name','source_url':url,
          'rationale':'A distinct published source records this variant name.'})
        assert r.status_code==201,r.text
        created.append(r.json()['id'])
    for i,aid in enumerate(created):
        r=client.put(f'/api/cases/{case}/aliases/{aid}/validity',headers=auth,json={
          'review_state':'retired' if i else 'active_hypothesis',
          'valid_from':'2019-01-01','valid_until':'2021-12-31',
          'rationale':'A dated public reference requires separate attribution and review.'})
        assert r.status_code==200,r.text
    listed=client.get(f'/api/cases/{case}/aliases/validated')
    assert listed.status_code==200,listed.text
    items=listed.json()['items']
    assert len(items)==2
    assert {x['review_state'] for x in items}=={'retired','active_hypothesis'}
    assert not listed.json()['autoMerged']

def test_invalid_alias_date_order_rejected(client,auth,case):
    a=client.post(f'/api/cases/{case}/aliases',headers=auth,json={
        'alias':'Earlier Brand','alias_type':'brand','source_url':'https://example.org/brand',
        'rationale':'Published historical branding candidate.'})
    assert a.status_code==201
    bad=client.put(f'/api/cases/{case}/aliases/{a.json()["id"]}/validity',headers=auth,json={
        'review_state':'active_hypothesis','valid_from':'2026-01-01','valid_until':'2020-01-01',
        'rationale':'Deliberately contradictory date range.'})
    assert bad.status_code==422
