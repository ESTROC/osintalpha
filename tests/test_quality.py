"""Auditable identity signal evaluation using controlled synthetic analyst labels."""
import json
from app import db

def evidence_pair(case,i,left_handle,right_handle):
    ids=[f'profile-a-{i:03}',f'profile-b-{i:03}']
    with db.connect() as c:
        for eid,provider,handle in zip(ids,['github','stackoverflow'],[left_handle,right_handle]):
            raw=json.dumps({'login':handle,'name':'Synthetic Researcher','location':'Delhi'})
            c.execute("""INSERT INTO evidence
              (id,case_id,provider,label,summary,source_url,source_ref,fetched_at,sha256,raw_json)
              VALUES (?,?,?,?,?,?,?,?,?,?)""",
              (eid,case,provider,'Synthetic Researcher','Public username test candidate',
               'https://example.org/'+eid,eid,'2026-10-25T12:00:00Z','synthetic',raw))
    return ids

def label(client,auth,case,ids,decision):
    return client.post('/api/cases/'+case+'/identity-reviews',headers=auth,json={
      'left_id':ids[0],'right_id':ids[1],'decision':decision,
      'rationale':'Synthetic analyst label for testing contradictory public account identifiers only.'})

def test_internal_quality_confusion_matrix_is_transparent(client,auth,case):
    for i in range(20):
        same=i in (0,1,2,3,5)
        left='shared-'+str(i)
        right=left if same else 'separate-'+str(i)
        pair=evidence_pair(case,i,left,right)
        classification='possible_same_person' if i<5 else 'different_people'
        r=label(client,auth,case,pair,classification)
        assert r.status_code==201,r.text
    output=client.get('/api/cases/'+case+'/identity-quality')
    assert output.status_code==200,output.text
    obj=output.json()
    assert obj['latestLabelledPairs']==20
    assert obj['confusion']=={'tp':4,'fp':1,'fn':1,'tn':14}
    assert obj['precisionAgainstAnalystLabels']==0.8
    assert obj['recallAgainstAnalystLabels']==0.8
    assert obj['falseAlertRateAgainstAnalystLabels']==0.0667
    assert obj['sampleSufficientForInternalTrend']
    assert 'NOT validated true identity accuracy' in obj['limitation']
    # Multiple reviews of the same pair remain in history, latest counts once.
    newer=label(client,auth,case,['profile-a-000','profile-b-000'],'different_people')
    assert newer.status_code==201
    changed=client.get('/api/cases/'+case+'/identity-quality').json()
    assert changed['reviewEvents']==21 and changed['latestLabelledPairs']==20

def test_empty_samples_do_not_report_fabricated_accuracy(client,auth,case):
    metrics=client.get('/api/cases/'+case+'/identity-quality').json()
    assert metrics['latestLabelledPairs']==0
    assert not metrics['sampleSufficientForInternalTrend']
    assert metrics['precisionAgainstAnalystLabels'] is None
    assert metrics['recallAgainstAnalystLabels'] is None

def test_labels_reject_publications_self_pairs_and_other_case(client,auth,case):
    pair=evidence_pair(case,100,'sample-one','sample-two')
    own=label(client,auth,case,[pair[0],pair[0]],'different_people')
    assert own.status_code==422
    other=client.post('/api/cases',headers=auth,json={
      'title':'Other research case','subject_type':'person','query':'Other Researcher',
      'purpose':'Authorized public researcher account investigation','authority_confirmed':True})
    assert other.status_code==201
    cross=label(client,auth,other.json()['id'],pair,'different_people')
    assert cross.status_code==422
    with db.connect() as c:
        c.execute("""INSERT INTO evidence
           (id,case_id,provider,label,summary,source_url,source_ref,fetched_at,sha256,raw_json)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
           ('publication-record',case,'crossref','Publication record','Unverified namesake',
           'https://doi.org/10.1234/example','publication-record','2026-10-25T12:00:00Z',
           'test','{"DOI":"10.1234/example"}'))
    assert label(client,auth,case,[pair[0],'publication-record'],'different_people').status_code==422

def test_identity_quality_is_case_owner_scoped(client,auth,case):
    evidence_pair(case,50,'one','two')
    user=client.post('/api/users',headers=auth,json={
      'username':'otherqualityanalyst','password':'SomeVeryLongTestPassword4567890','role':'analyst'})
    assert user.status_code==201
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    assert client.post('/api/auth/login',json={
        'username':'otherqualityanalyst','password':'SomeVeryLongTestPassword4567890'}).status_code==200
    assert client.get('/api/cases/'+case+'/identity-quality').status_code==404
    assert label(client,auth,case,['profile-a-050','profile-b-050'],'different_people').status_code==404
