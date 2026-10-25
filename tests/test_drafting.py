"""Source-grounded assessment drafts require valid captured quotations.

All model results are synthetic; these tests do not certify semantic entailment.
"""
import hashlib
from app import db,drafting

def source_quote(client,auth,case,*,rejected=False):
    ev=client.post('/api/cases/'+case+'/evidence',headers=auth,json={
      'label':'Public profile example','summary':'Public source candidate for drafting',
      'source_url':'https://github.com/example-person'})
    assert ev.status_code==200
    eid=ev.json()['id']
    cid='capture-review-1234567890'
    text='A published engineering profile describes building public Python applications and maintaining open source tools for educational demonstrations.'
    with db.connect() as conn:
        conn.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
            (cid,case,eid,'https://github.com/example-person','text/plain',text,
             hashlib.sha256(text.encode()).hexdigest(),
             '2026-10-25T12:00:00Z','captured',''))
    r=client.post('/api/cases/'+case+'/excerpts',headers=auth,json={
        'evidence_id':eid,'capture_id':cid,
        'quote_text':'building public Python applications and maintaining open source tools',
        'interpretation':'The public page claims these engineering activities, without independent identity verification.'})
    assert r.status_code==201,r.text
    if rejected:
        x=client.patch('/api/evidence/'+eid,headers=auth,json={
            'status':'rejected','reviewer_notes':'Name associated with an unrelated profile'})
        assert x.status_code==200
    return eid,cid,r.json()['id']

def test_draft_requires_actual_current_quotes(client,auth,case):
    r=client.post('/api/cases/'+case+'/assessment-draft',headers=auth,json={'provider':'local'})
    assert r.status_code==422

def test_local_ledger_is_source_linked_and_not_auto_saved(client,auth,case):
    eid,cid,qid=source_quote(client,auth,case)
    r=client.post('/api/cases/'+case+'/assessment-draft',headers=auth,json={'provider':'local'})
    assert r.status_code==200,r.text
    data=r.json()
    assert data['provider']=='source-ledger'
    assert data['saved'] is False
    assert data['quoteIds']==[qid]
    assert 'github.com/example-person' in data['draft']['assessment']
    assert 'Verbatim captured text:' in data['draft']['assessment']
    assert 'not been independently verified' in data['draft']['executive_summary']
    assert client.get('/api/cases/'+case+'/assessment').json()['status']=='open'

def test_rejected_and_stale_source_quote_excluded(client,auth,case):
    eid,cid,qid=source_quote(client,auth,case,rejected=True)
    r=client.post('/api/cases/'+case+'/assessment-draft',headers=auth,json={'provider':'local'})
    assert r.status_code==422

def test_changed_capture_is_rejected_for_draft(client,auth,case):
    eid,cid,qid=source_quote(client,auth,case)
    newer='New public profile changed substantially and old quotation disappeared.'
    with db.connect() as c:
        c.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
          ('newer-capture-2099',case,eid,'https://github.com/example-person','text/plain',newer,
           hashlib.sha256(newer.encode()).hexdigest(),
           '2026-10-26T12:00:00Z','captured',''))
    r=client.post('/api/cases/'+case+'/assessment-draft',headers=auth,json={'provider':'local'})
    assert r.status_code==422

def test_groq_draft_requires_case_optin_and_config(client,auth,case,monkeypatch):
    eid,cid,qid=source_quote(client,auth,case)
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    no=client.post('/api/cases/'+case+'/assessment-draft',headers=auth,json={'provider':'groq'})
    assert no.status_code==409
    monkeypatch.setenv('GROQ_API_KEY','fake-test-key')
    still=client.post('/api/cases/'+case+'/assessment-draft',headers=auth,json={'provider':'groq'})
    assert still.status_code==409
    assert client.put('/api/cases/'+case+'/ai-consent',headers=auth,json={'enabled':True}).status_code==200
    async def fake(case,records):
        assert records[0]['id']==qid
        return ({'executive_summary':'This source claims technical activities, without validated identity.',
                'assessment':'The exact cited passage discusses Python engineering activities but has not been independently authenticated.',
                'limitations':'Identity could not be established from one public page, and information may be incomplete.',
                'next_actions':'Corroborate through another independent source and verify the original public page.'},[qid])
    monkeypatch.setattr(drafting,'model_draft',fake)
    good=client.post('/api/cases/'+case+'/assessment-draft',headers=auth,json={'provider':'groq'})
    assert good.status_code==200,good.text
    assert good.json()['provider']=='groq-proposed, source-passages-attached'
    assert 'SOURCE PASSAGES FOR HUMAN VERIFICATION' in good.json()['draft']['assessment']
    assert not good.json()['saved']

def test_draft_respects_case_permissions(client,auth,case):
    source_quote(client,auth,case)
    r=client.post('/api/users',headers=auth,json={
        'username':'unrelated-reader','password':'LongUniquePassword12345678',
        'role':'analyst'})
    assert r.status_code==201
    client.post('/api/auth/logout',headers=auth)
    assert client.post('/api/auth/login',json={'username':'unrelated-reader',
        'password':'LongUniquePassword12345678'}).status_code==200
    assert client.post('/api/cases/'+case+'/assessment-draft',headers=auth,json={'provider':'local'}).status_code==404
