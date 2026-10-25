"""Attribute comparison does not confuse name matches with identity proof."""
import hashlib,json
from app import db
from app.identity import attributes,compare,rank_against_clues

def add_record(case,provider,label,raw,number=0,status='candidate'):
    digest=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()
    id=f'{provider[:8]}-{number:07}'
    with db.connect() as c:
        c.execute('''INSERT INTO evidence
            (id,case_id,provider,label,summary,source_url,source_ref,fetched_at,
             sha256,raw_json,status) VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
             (id,case,provider,label,'Synthetic public source candidate',
              'https://example.org/public/'+str(number),id,'2026-10-25T14:00:00Z',
              digest,json.dumps(raw),status))
    return id

def test_same_display_name_does_not_create_unjustified_link(client,auth,case):
    a=add_record(case,'github','Ayush Tripathi',{'display_name':'Ayush Tripathi',
        'login':'ayush-dev','location':'Delhi','company':'Development Firm'},1)
    b=add_record(case,'openalex','Ayush Tripathi',{'name':'Ayush Tripathi',
        'institutions':['Harvard University']},2)
    r=client.get('/api/cases/'+case+'/identity-analysis',params={'left':a,'right':b})
    assert r.status_code==200,r.text
    x=r.json()
    assert x['comparison']['identityVerified'] is False
    assert x['comparison']['signalLevel']=='no_link_signal'
    assert x['pairSuggestions']==[]
    assert any(v['field']=='organization' for v in x['comparison']['differing'])

def test_matching_public_handle_produces_review_suggestion_never_merge(client,auth,case):
    a=add_record(case,'github','First public account',{'display_name':'Example Person',
       'login':'same-handle','location':'Delhi','company':'Sample Office'},1)
    b=add_record(case,'stackoverflow','Second public account',{'display_name':'Example Person',
       'username':'same-handle','location':'Delhi','company':'Sample Office'},2)
    r=client.get('/api/cases/'+case+'/identity-analysis')
    assert r.status_code==200
    items=r.json()['pairSuggestions']
    assert len(items)==1
    assert not items[0]['identityVerified']
    details=client.get('/api/cases/'+case+'/identity-analysis',params={'left':a,'right':b}).json()
    assert details['comparison']['signalLevel']=='investigate_public_identifier'
    assert 'publicHandle' in [v['field'] for v in details['comparison']['matching']]
    assert details['comparison']['requiresHumanReview']
    with db.connect() as c:
        assert c.execute('SELECT count(*) n FROM candidate_profiles WHERE case_id=?',(case,)).fetchone()['n']==0

def test_context_match_is_explained_without_false_negative(client,auth,case):
    assert client.put('/api/cases/'+case+'/context',headers=auth,json={
      'city':'Delhi','organization':'ESTROC','profession':'software engineer',
      'public_handle':'public-identity'}).status_code==200
    a=add_record(case,'github','Public developer A',{'login':'public-identity',
       'company':'ESTROC','location':'Delhi'},1)
    b=add_record(case,'github','Public developer B',{'login':'another-identity',
       'company':'Another Organization','location':'Bengaluru'},2)
    c=add_record(case,'github','Public developer C',{'login':'third-account'},3)
    data=client.get('/api/cases/'+case+'/identity-analysis').json()['records']
    assert data[0]['recordId']==a
    assert data[0]['clues']['publicClueMatches']==3
    byid={x['recordId']:x for x in data}
    assert len(byid[c]['clues']['unknown'])==2
    assert not byid[c]['clues']['matched']
    assert byid[b]['clues']['different']

def test_comparison_rejects_other_case_records(client,auth,case):
    another=client.post('/api/cases',headers=auth,json={
      'title':'Authorized Other Case','subject_type':'person','query':'Second Public Subject',
      'purpose':'Authorized analysis of public professional work',
      'authority_confirmed':True}).json()['id']
    a=add_record(case,'github','Public A',{'login':'a'},1)
    b=add_record(another,'stackoverflow','Public B',{'login':'b'},2)
    r=client.get('/api/cases/'+case+'/identity-analysis',params={'left':a,'right':b})
    assert r.status_code==404
    assert client.get('/api/cases/'+case+'/identity-analysis',params={'left':a}).status_code==422
    assert client.get('/api/cases/'+case+'/identity-analysis',params={'left':a,'right':a}).status_code==422

def test_rejected_record_not_proposed_as_identity(client,auth,case):
    add_record(case,'github','Rejected Candidate',{'login':'shared-handle'},1,'rejected')
    add_record(case,'stackoverflow','Open Candidate',{'username':'shared-handle'},2)
    data=client.get('/api/cases/'+case+'/identity-analysis').json()
    assert not data['pairSuggestions']
