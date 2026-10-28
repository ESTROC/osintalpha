"""P1 080/081/088: preflight before case creation, no surprise person identification."""
from app.smart_search import preflight_search_question

def test_081_event_topic_is_tentative_not_a_person_verdict():
    p=preflight_search_question('Public conference keynote event in Delhi')
    assert p['externalRequestsMade'] is False
    assert p['caseCreated'] is False
    assert p['requiresHumanReview']
    assert p['typeConfidence']=='tentative_low'

def test_088_category_override_is_preserved_and_editable(client,auth):
    url='/api/search/preflight?question=Public%20technology%20conference%20in%20Delhi'
    p=client.get(url)
    assert p.status_code==200,p.text
    assert p.json()['requiresHumanReview']
    edited=client.get(url+'&subject_type=organization')
    assert edited.status_code==200,edited.text
    assert edited.json()['suggestedType']=='organization'
    assert edited.json()['typeConfidence']=='explicit'
    assert edited.json()['caseCreated'] is False

def test_080_search_requires_explicit_authorized_purpose(client,auth):
    r=client.post('/api/search/start',headers=auth,json={
      'question':'Example public business service','purpose':'Authorized public-source review',
      'authority_confirmed':False})
    assert r.status_code==422

def test_preflight_does_not_write_case(client,auth):
    from app import db
    with db.connect() as c:
        before=c.execute('SELECT count(*) n FROM cases').fetchone()['n']
    client.get('/api/search/preflight?question=Public%20festival%20announcement')
    with db.connect() as c:
        after=c.execute('SELECT count(*) n FROM cases').fetchone()['n']
    assert before==after
