"""Conservative duplicate-source detection and case access tests."""
import json
from app.duplicates import detect,canonical_doi,canonical_url

def r(id,provider,label,url,raw=None):
    return {'id':id,'provider':provider,'label':label,'source_url':url,
            'raw_json':json.dumps(raw or {})}

def test_doi_and_url_duplicates_are_not_counted_as_independent_sources():
    rows=[
      r('a','crossref','Paper title','https://doi.org/10.1234/ABCDEF'),
      r('b','openalex','Same article','https://doi.org/10.1234/abcdef?utm_source=newsletter'),
      r('c','analyst','Paper repost','https://publisher.example.org/works/one',{'DOI':'10.1234/AbCdEf'})
    ]
    result=detect(rows)
    assert result['totalPairs']==3
    assert result['counts']['same_doi']==3
    assert all(x['notIndependent'] for x in result['pairs'])
    assert not any(x['identityVerified'] for x in result['pairs'])

def test_sources_with_matching_human_name_are_not_merged():
    rows=[
      r('a','github','Ayush Tripathi','https://github.com/first'),
      r('b','stackoverflow','Ayush Tripathi','https://stackoverflow.com/users/123'),
      r('c','openalex','Ayush Tripathi','https://openalex.org/A123')
    ]
    result=detect(rows)
    assert result['totalPairs']==0

def test_high_similarity_titles_are_only_human_review_suggestions():
    title='AI driven multi dimensional learning and career intelligence framework for research'
    rows=[
      r('a','crossref',title,'https://publisher.example.org/paper1'),
      r('b','openalex',title+' original','https://another.example.org/record42')
    ]
    result=detect(rows)
    assert result['counts']['similar_title']==1
    suggestion=result['pairs'][0]
    assert suggestion['rule']=='similar_title'
    assert not suggestion['notIndependent']
    assert not suggestion['identityVerified']

def test_tracking_parameters_do_not_create_fake_distinct_sources():
    a='https://www.example.org/public/page?utm_campaign=x&ref=keep'
    b='https://example.org/public/page?ref=keep&utm_source=y'
    assert canonical_url(a)==canonical_url(b)
    assert canonical_url('https://example.org/public/page?id=one')!=canonical_url('https://example.org/public/page?id=two')
    assert canonical_doi('https://doi.org/10.1234/ABC')=='10.1234/abc'

def test_duplicate_results_enforce_case_permissions(client,auth,case):
    api=client.get('/api/cases/'+case+'/duplicate-sources')
    assert api.status_code==200
    assert api.json()['totalPairs']==0
    assert api.json()['recordsExamined']==0
    assert client.get('/api/cases/'+case+'/duplicate-sources',params={'limit':0}).status_code==422
    r=client.post('/api/users',headers=auth,json={
      'username':'anotheranalyst','password':'SafeLengthyUnrelatedPassword12345678','role':'analyst'})
    assert r.status_code==201
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    assert client.post('/api/auth/login',json={
      'username':'anotheranalyst','password':'SafeLengthyUnrelatedPassword12345678'}).status_code==200
    assert client.get('/api/cases/'+case+'/duplicate-sources').status_code==404
