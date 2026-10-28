"""P3-144 and P3-148: case title changes preserve original search terms and saved method stages."""
from app import db

def test_title_update_retains_query_and_case_context(client,auth,case):
    before=client.get('/api/cases/'+case).json()['case']
    response=client.patch('/api/cases/'+case+'/title',headers=auth,
                          json={'title':'Synthetic research / historical coverage'})
    assert response.status_code==200,response.text
    after=client.get('/api/cases/'+case).json()['case']
    assert after['title']=='Synthetic research / historical coverage'
    assert after['query']==before['query'] and after['purpose']==before['purpose']

def test_saved_methodology_never_invents_source_coverage(client,auth,case):
    resp=client.get('/api/cases/'+case+'/methodology-appendix')
    assert resp.status_code==200,resp.text
    assert resp.json()['searchComplete'] is False
    assert resp.json()['recordedQueries']==[]
    assert resp.json()['originalQuestion']=='Test Person'
    with db.connect() as conn:
        owner=conn.execute('SELECT created_by FROM cases WHERE id=?',(case,)).fetchone()['created_by']
        conn.execute('INSERT INTO research_queries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            ('query-stage-test',case,owner,'run-synthetic','github','public record',
             'error',0,0,'Provider unavailable, not no public records','2026-10-28T12:00:00Z'))
    current=client.get('/api/cases/'+case+'/methodology-appendix').json()
    assert current['recordedQueries'][0]['status']=='error'
    assert len(current['recordedFailures'])==1
    assert current['queriedProviders']==['github']
    page=client.get('/api/cases/'+case+'/report.html')
    assert page.status_code==200,page.text
    assert 'Recorded research protocol and failures' in page.text
    assert 'DRAFT WORKING DOCUMENT' in page.text
