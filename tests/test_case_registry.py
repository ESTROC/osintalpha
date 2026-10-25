"""Closure tests for #87 case search and #88 complete paginated registry."""
from app import db

def seed_cases(case_client, count=267):
    with db.connect() as conn:
        admin=conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()['id']
        for i in range(count):
            cid=f"{i+7000:024x}"
            title=f"Research Subject {i:03}"
            if i==143: title="Literal 100% result _unusual"
            kind='organization' if i%7==0 else 'person'
            created=f"2026-10-25T12:{i//60:02}:{i%60:02}+00:00"
            conn.execute("""INSERT INTO cases
                (id,title,subject_type,query,purpose,authority_confirmed,ai_opt_in,created_by,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (cid,title,kind,f"Subject-{i:03}","Authorized test research for synthetic entity",1,0,admin,created))
            if i==143:
                conn.execute("""INSERT INTO case_context
                    (case_id,city,organization,profession,public_handle,updated_at)
                    VALUES (?,?,?,?,?,?)""",
                    (cid,'','','','','2026-10-25T12:00:00+00:00'))
            if i==31:
                conn.execute("""INSERT INTO case_assessments
                    (case_id,executive_summary,assessment,limitations,next_actions,status,updated_by,updated_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (cid,'Synthetic summary','Synthetic assessment','Test limitation','Check sources','completed',admin,created))
    return count

def test_case_registry_paginates_all_without_duplication(client,auth):
    count=seed_cases(client)
    found=[]
    for page in range(1,13):
        r=client.get('/api/cases',params={'page':page,'page_size':25})
        assert r.status_code==200,r.text
        body=r.json()
        assert body['total']==count
        assert body['totalPages']==11
        assert body['page']==page
        assert len(body['items'])==25 if page<=10 else len(body['items'])==17 if page==11 else len(body['items'])==0
        found.extend(item['id'] for item in body['items'])
    assert len(found)==count
    assert len(set(found))==count

def test_case_search_filters_literal_wildcards(client,auth):
    seed_cases(client)
    r=client.get('/api/cases',params={'q':'100% result _unusual'})
    assert r.status_code==200,r.text
    assert r.json()['total']==1
    assert r.json()['items'][0]['query']=='Subject-143'
    assert client.get('/api/cases',params={'q':'%'}).json()['total']==1
    assert client.get('/api/cases',params={'q':'_'}).json()['total']==1
    assert client.get('/api/cases',params={'q':'synthetic entity'}).json()['total']==267

def test_case_filter_sort_dates_and_validation(client,auth):
    seed_cases(client)
    results=client.get('/api/cases',params={'status':'completed','subject_type':'person'})
    assert results.status_code==200
    assert results.json()['total']==1
    assert results.json()['items'][0]['assessment_status']=='completed'
    kinds=client.get('/api/cases',params={'subject_type':'organization','page_size':100}).json()
    assert kinds['total']==39
    desc=client.get('/api/cases',params={'sort':'newest','page_size':3}).json()['items']
    asc=client.get('/api/cases',params={'sort':'oldest','page_size':3}).json()['items']
    assert desc[0]['title']=='Research Subject 266'
    assert asc[0]['title']=='Research Subject 000'
    before=client.get('/api/cases',params={'date_from':'2026-10-26'}).json()
    assert before['total']==0
    assert client.get('/api/cases',params={'date_from':'2026-11-10','date_to':'2026-10-10'}).status_code==422
    assert client.get('/api/cases',params={'date_from':'not-a-date'}).status_code==422
    assert client.get('/api/cases',params={'page_size':200}).status_code==422
    assert client.get('/api/cases',params={'sort':'untrusted;drop table cases'}).status_code==422

def test_nonadmin_cannot_see_or_count_other_users_cases(client,auth):
    seed_cases(client)
    created=client.post('/api/users',headers=auth,json={
        'username':'caseviewer','password':'AnotherLongStrongPasswordForOnlyTests',
        'role':'analyst'})
    assert created.status_code==201
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    assert client.post('/api/auth/login',json={
        'username':'caseviewer','password':'AnotherLongStrongPasswordForOnlyTests'}).status_code==200
    empty=client.get('/api/cases').json()
    assert empty['total']==0 and empty['items']==[]
    assert client.get('/api/cases',params={'owner':'admin'}).status_code==403
    own=client.post('/api/cases',headers=auth,json={
        'title':'Own analyst case','query':'Test identity','subject_type':'person',
        'purpose':'Authorized research into public records','authority_confirmed':True})
    assert own.status_code==201
    scoped=client.get('/api/cases',params={'q':'analyst','page_size':10}).json()
    assert scoped['total']==1
    assert scoped['items'][0]['title']=='Own analyst case'
    assert client.get('/api/cases',params={'q':'Research Subject'}).json()['total']==0
