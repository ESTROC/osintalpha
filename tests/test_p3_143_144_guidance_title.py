"""P3-143/144 differentiate search states and preserve original questions on rename."""
from app import db
def test_specific_no_search_and_provider_failure_guidance(client,auth,case):
    u=client.get(f'/api/cases/{case}/outcome-guidance')
    assert u.status_code==200,u.text
    assert u.json()['state']=='never_searched'
    with db.connect() as c:
        user=c.execute('SELECT created_by FROM cases WHERE id=?',(case,)).fetchone()['created_by']
        c.execute('INSERT INTO research_queries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
          ('failed-query',case,user,'one-run','github','public scoped query','error',
           0,0,'Provider timed out','2026-10-29T00:00:00Z'))
    failed=client.get(f'/api/cases/{case}/outcome-guidance').json()
    assert failed['state']=='provider_failed'
    assert 'no-hit does not prove' not in failed['nextAction'].lower()
    assert not failed['identityVerified']

def test_title_can_change_without_changing_search_subject(client,auth,case):
    suggested=client.get(f'/api/cases/{case}/title-suggestion')
    assert suggested.status_code==200
    new_title='Person · Test Person · Academic review · 2026-10-29'
    r=client.patch(f'/api/cases/{case}/title',headers=auth,json={'title':new_title})
    assert r.status_code==200,r.text
    assert r.json()['originalQuestionPreserved']
    assert client.get(f'/api/cases/{case}').json()['case']['query']=='Test Person'
    assert client.get(f'/api/cases/{case}').json()['case']['title']==new_title
