"""Isolated synthetic 50-question analyst regression: no upstream APIs, no real people.

This verifies routing, permissions and case storage, NOT result accuracy,
provider uptime or browser UX. Every name and institution here is fictional.
"""
import pytest
from app import smart_search
from app.connectors import CATALOG

QUERY_SET = [
  "Find official website for Demo Hardware Works Ltd",
  "Public business registration for Sample Plumbing Services LLC",
  "Verify a synthetic tutoring service listing",
  "Are there official records of Example Community Trust",
  "Public information on Demo Student participation in robotics contest",
  "Local council public notice about Test Park restoration",
  "Public schedule of a municipal recycling event",
  "Does Fictional Campus have an official student association",
  "Public portfolio of Example Developer and projects",
  "Technical publications by Demo Research Author",
  "Review a public Github repository owned by Sample Developer",
  "Check public vulnerability advisory for example.org",
  "Passive DNS for example.org",
  "Passive information for 8.8.8.8",
  "Search for a published engineering competition roster",
  "Find public professional directory for Demo Architect",
  "Public cultural festival schedule in Testville",
  "Public transportation service outage reports",
  "City government planning consultation publication",
  "Public awards event results for Demo Team",
  "Official service catalog of Example Supplier Ltd",
  "Public legal identifier for Demo Manufacturing Pvt Ltd",
  "Locate public product safety recall notice",
  "Check public open source license for Demo Project",
  "Public press release about Example Robotics Club",
  "Find published details of university admission program",
  "Community volunteering event organizer public page",
  "Public library workshop calendar",
  "Local marketplace website of Example Repair Services",
  "Search public profile of Demo Electrical Contractor",
  "Published articles about coastal flood warnings",
  "Public weather station observation for Testtown",
  "Official maps of open hiking trails",
  "List public museums in Demo City",
  "Find available public event venue information",
  "Official address of a government office in Example City",
  "Public school sports results in Demo City",
  "Look up public professional license for Example Contractor",
  "Business contact web page of Demo Service Cooperative",
  "Find local food safety inspection portal",
  "Compare two public company annual reports",
  "Check availability of official municipal tender",
  "Official policy announcement about public transit",
  "A public academic paper by Test Researcher",
  "Published patent abstract for Sample Invention",
  "Open data about road incidents in Example County",
  "Review an official city council meeting transcript",
  "Public ecological monitoring data in Test Region",
  "Documentation for an open source computer vision library",
  "Find regulatory filing for a sample listed company"
]


def test_fifty_distinct_questions_cover_varied_public_topics():
    assert len(QUERY_SET)==50
    assert len(set(QUERY_SET))==50
    for question in QUERY_SET:
        route=smart_search.deterministic_route(question)
        assert route['subjectType'] in {'person','organization','domain','ip'}
        assert len(route['subject'])>=2
        allowed={c.id for c in CATALOG if route['subjectType'] in c.scope}
        assert all(p in allowed for p in route['providers']), question
        assert not route['aiPlanned']
        assert route['context']=={
            'city':'','organization':'','profession':'','public_handle':''},question


def test_fifty_questions_as_real_isolated_analyst_session(client,auth):
    owner=client.post('/api/cases',headers=auth,json={
        'title':'Admin-only synthetic case','subject_type':'person','query':'Admin Sample',
        'purpose':'Test admin-only private case separation','authority_confirmed':True})
    assert owner.status_code==201
    protected_case=owner.json()['id']
    created=client.post('/api/users',headers=auth,json={
        'username':'analyst.sandbox','password':'SyntheticOnlyNeverInProduction1234!',
        'role':'analyst'})
    assert created.status_code==201,created.text
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    signin=client.post('/api/auth/login',json={
        'username':'analyst.sandbox','password':'SyntheticOnlyNeverInProduction1234!'})
    assert signin.status_code==200
    assert signin.json()['user']['role']=='analyst'
    assert client.get('/api/cases/'+protected_case).status_code==404
    assert client.get('/api/users').status_code==403
    identifiers=set()
    for question in QUERY_SET:
        response=client.post('/api/search/start',headers={'X-OSINT-Alpha-Action':'1'},json={
            'question':question,'purpose':'Authorized synthetic analyst acceptance evaluation',
            'authority_confirmed':True,'ai_opt_in':False})
        assert response.status_code==201,(question,response.text)
        created_case=response.json()
        assert created_case['id'] not in identifiers
        identifiers.add(created_case['id'])
        assert created_case['plan']['aiPlanned'] is False
        fetched=client.get('/api/cases/'+created_case['id'])
        assert fetched.status_code==200
        assert fetched.json()['case']['ai_opt_in']==0
    assert len(identifiers)==50
    assert client.get('/api/cases/'+protected_case).status_code==404


def test_never_turn_plain_query_topic_into_asserted_employer_or_profession():
    for query in ('Sample Operator navy cyber security', 'Demo Worker medical research',
                  'Research about a tradesperson named Sample', 'Fictional Graduate startup'):
        plan=smart_search.deterministic_route(query)
        assert plan['context']['organization']==''
        assert plan['context']['profession']==''
