"""Permission tests for explicit case collaboration."""
from app import db

def make_analyst(client,auth,username):
    r=client.post('/api/users',headers=auth,json={
       'username':username,'password':'LongDistinctPasswordForCaseCollaboration123',
       'role':'analyst'})
    assert r.status_code==201,r.text
    with db.connect() as c:
        return c.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone()['id']

def login(client,username):
    assert client.post('/api/auth/login',json={
        'username':username,'password':'LongDistinctPasswordForCaseCollaboration123'}).status_code==200

def test_case_owner_can_grant_and_revoke_existing_editor(client,auth,case):
    editor=make_analyst(client,auth,'caseeditor')
    unknown=client.post('/api/cases/'+case+'/members',headers=auth,json={'username':'missing-user'})
    assert unknown.status_code==422
    added=client.post('/api/cases/'+case+'/members',headers=auth,json={'username':'caseeditor'})
    assert added.status_code==201,added.text
    assert added.json()['userId']==editor
    duplicate=client.post('/api/cases/'+case+'/members',headers=auth,json={'username':'caseeditor'})
    assert duplicate.status_code==409
    owner_view=client.get('/api/cases/'+case+'/members').json()
    assert owner_view['canManage'] and owner_view['editors'][0]['username']=='caseeditor'
    # Account session switch; case now appears in the editor's complete registry.
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    login(client,'caseeditor')
    visible=client.get('/api/cases',params={'q':'Authorized Example Research'}).json()
    assert visible['total']==1
    assert visible['items'][0]['id']==case
    assert client.get('/api/cases/'+case).status_code==200
    assert client.get('/api/cases/'+case+'/members').json()['canManage'] is False
    assert client.post('/api/cases/'+case+'/members',headers=auth,json={'username':'admin'}).status_code==403
    assert client.delete('/api/cases/'+case,headers=auth).status_code==403
    task=client.post('/api/cases/'+case+'/tasks',headers=auth,json={
        'title':'Check corporate registration','assigned_to':editor})
    assert task.status_code==201,task.text
    # Switch to administrator to revoke membership.
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    assert client.post('/api/auth/login',json={
       'username':'admin','password':'AnIntentionallyLongTestPassword123'}).status_code==200
    revoked=client.delete('/api/cases/'+case+'/members/'+editor,headers=auth)
    assert revoked.status_code==200
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    login(client,'caseeditor')
    assert client.get('/api/cases/'+case).status_code==404
    assert client.get('/api/cases/'+case+'/members').status_code==404
    assert client.get('/api/cases',params={'q':'Authorized Example Research'}).json()['total']==0

def test_grant_scopes_to_single_case_and_assignment_requires_membership(client,auth,case):
    editor=make_analyst(client,auth,'caseeditor2')
    other=client.post('/api/cases',headers=auth,json={
      'title':'Private unrelated investigation','subject_type':'organization','query':'Example Another Ltd',
      'purpose':'Authorized independent public-source corporate research','authority_confirmed':True})
    assert other.status_code==201
    assert client.post('/api/cases/'+case+'/tasks',headers=auth,json={
      'title':'Check one claim','assigned_to':editor}).status_code==422
    assert client.post('/api/cases/'+case+'/members',headers=auth,json={'username':'caseeditor2'}).status_code==201
    assert client.post('/api/cases/'+case+'/tasks',headers=auth,json={
      'title':'Check public claim','assigned_to':editor}).status_code==201
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    login(client,'caseeditor2')
    assert client.get('/api/cases/'+other.json()['id']).status_code==404
    assert client.get('/api/cases',params={'q':'Private unrelated'}).json()['total']==0
    assert client.get('/api/cases/'+case+'/tasks').json()['total']==1

def test_membership_is_deleted_with_case(client,auth,case):
    uid=make_analyst(client,auth,'caseeditor3')
    assert client.post('/api/cases/'+case+'/members',headers=auth,json={'username':'caseeditor3'}).status_code==201
    assert client.delete('/api/cases/'+case,headers=auth).status_code==200
    with db.connect() as c:
        assert c.execute('SELECT count(*) n FROM case_members WHERE case_id=?',(case,)).fetchone()['n']==0
