"""Investigation task workflow, access control and auditable completion tests."""
from app import db

def new_task(client,auth,case,**overrides):
    body={'title':'Verify public organization affiliation',
          'description':'Cross-check the employer against a first-party public website',
          'priority':'high','due_date':'2026-11-05',**overrides}
    return client.post('/api/cases/'+case+'/tasks',headers=auth,json=body)

def test_task_lifecycle_with_review_and_history(client,auth,case):
    r=new_task(client,auth,case)
    assert r.status_code==201,r.text
    tid=r.json()['id']
    listing=client.get('/api/cases/'+case+'/tasks')
    assert listing.status_code==200 and listing.json()['total']==1
    task=listing.json()['items'][0]
    assert task['title']=='Verify public organization affiliation'
    assert task['priority']=='high' and task['due_date']=='2026-11-05'
    not_yet=client.patch('/api/cases/'+case+'/tasks/'+tid,headers=auth,json={
        'status':'done','note':'Review complete, evidence checks recorded.'})
    assert not_yet.status_code==422
    progress=client.patch('/api/cases/'+case+'/tasks/'+tid,headers=auth,json={
        'status':'in_progress','note':'Examining original public company page.'})
    assert progress.status_code==200
    weak=client.patch('/api/cases/'+case+'/tasks/'+tid,headers=auth,json={
        'status':'done','note':'Finished.'})
    assert weak.status_code==422
    done=client.patch('/api/cases/'+case+'/tasks/'+tid,headers=auth,json={
        'status':'done','note':'Employer assertion checked against two distinct public records.'})
    assert done.status_code==200
    hist=client.get('/api/cases/'+case+'/tasks/'+tid+'/history')
    assert hist.status_code==200
    assert len(hist.json()['items'])==3
    assert hist.json()['items'][0]['new_status']=='done'
    assert client.get('/api/cases/'+case+'/tasks',params={'status':'done'}).json()['total']==1
    assert client.get('/api/cases/'+case+'/tasks',params={'status':'blocked'}).json()['total']==0

def test_task_dates_assignment_and_pagination(client,auth,case):
    users=client.get('/api/cases/'+case+'/task-assignees')
    assert users.status_code==200 and any(x['username']=='admin' for x in users.json()['items'])
    assert new_task(client,auth,case,due_date='2026-02-30').status_code==422
    assert new_task(client,auth,case,assigned_to='nonexistent').status_code==422
    for i in range(25):
        r=new_task(client,auth,case,title=f'Collect distinct public source {i:03}')
        assert r.status_code==201,r.text
    page1=client.get('/api/cases/'+case+'/tasks',params={'page_size':10,'page':1}).json()
    page3=client.get('/api/cases/'+case+'/tasks',params={'page_size':10,'page':3}).json()
    assert page1['total']==25 and page1['totalPages']==3
    assert len(page1['items'])==10 and len(page3['items'])==5
    assert not ({r['id'] for r in page1['items']} & {r['id'] for r in page3['items']})
    assert client.get('/api/cases/'+case+'/tasks',params={'page_size':101}).status_code==422

def test_cross_case_tasks_are_not_visible_to_other_analysts(client,auth,case):
    tid=new_task(client,auth,case).json()['id']
    r=client.post('/api/users',headers=auth,json={
        'username':'separateanalyst','password':'SomeOtherStrongPassword123456789','role':'analyst'})
    assert r.status_code==201
    admin=client.post('/api/auth/logout',headers=auth)
    assert admin.status_code==200
    login=client.post('/api/auth/login',json={
        'username':'separateanalyst','password':'SomeOtherStrongPassword123456789'})
    assert login.status_code==200
    assert client.get('/api/cases/'+case+'/tasks').status_code==404
    assert client.get('/api/cases/'+case+'/tasks/'+tid+'/history').status_code==404
    assert client.post('/api/cases/'+case+'/tasks',headers=auth,json={
        'title':'Illicit task'}).status_code==404
    assert client.patch('/api/cases/'+case+'/tasks/'+tid,headers=auth,json={
        'status':'blocked','note':'Unauthorized task action'}).status_code==404

def test_assignee_cannot_be_unrelated_user_without_case_access(client,auth,case):
    r=client.post('/api/users',headers=auth,json={
        'username':'noaccessanalyst','password':'PasswordThatIsStrongEnough123456','role':'analyst'})
    assert r.status_code==201
    with db.connect() as c:
        other=c.execute("SELECT id FROM users WHERE username='noaccessanalyst'").fetchone()['id']
    r=new_task(client,auth,case,assigned_to=other)
    assert r.status_code==422
    assert client.get('/api/cases/'+case+'/tasks').json()['total']==0

def test_tasks_disappear_when_case_deleted(client,auth,case):
    tid=new_task(client,auth,case).json()['id']
    assert client.delete('/api/cases/'+case,headers=auth).status_code==200
    with db.connect() as c:
        assert c.execute('SELECT count(*) n FROM investigation_tasks WHERE id=?',(tid,)).fetchone()['n']==0
        assert c.execute('SELECT count(*) n FROM investigation_task_events WHERE task_id=?',(tid,)).fetchone()['n']==0
