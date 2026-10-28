"""P3-149 initial search date scope is preserved and validated before provider calls."""
def test_search_date_range_saved_in_plan(client,auth):
    body={'question':'public conference activities of Example Institute',
       'purpose':'Authorized historical public organization research',
       'authority_confirmed':True,'ai_opt_in':False,'subject_type':'organization',
       'date_from':'2020-01-01','date_to':'2020-12-31','freshness':'all'}
    result=client.post('/api/search/start',headers=auth,json=body)
    assert result.status_code==201,result.text
    scope=result.json()['plan']['searchTimeScope']
    assert scope['dateFrom']=='2020-01-01' and scope['dateTo']=='2020-12-31'
    assert not scope['structuredProviderDateFilterVerified']
    stored=client.get('/api/cases/'+result.json()['id']+'/search-plan')
    assert stored.json()['plan']['searchTimeScope']==scope

def test_date_range_rejects_inverted_or_partial(client,auth):
    body={'question':'Example Institute public announcements',
       'purpose':'Authorized public historical record search',
       'authority_confirmed':True,'subject_type':'organization',
       'date_from':'2024-06-01','date_to':'2020-01-01'}
    assert client.post('/api/search/start',headers=auth,json=body).status_code==422
    body['date_to']=None
    assert client.post('/api/search/start',headers=auth,json=body).status_code==422

def test_visible_initial_date_and_freshness_controls():
    from pathlib import Path
    js=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert 'id="smart-time-coverage"' in js
    assert 'name="date_from"' in js and 'name="date_to"' in js
    assert 'date_from:date_from||null,date_to:date_to||null' in js
